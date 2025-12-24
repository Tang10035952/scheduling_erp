from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import os
import secrets
import string

from .forms import (
    WorkerCreationForm,
    ManagerWorkerCreateForm,
    ManagerWorkerUpdateForm,
    TempPasswordResetForm,
)
from .models import UserProfile, WorkerDocument
from scheduling.models import SchedulingWindow


def is_manager(user):
    try:
        return user.is_authenticated and user.userprofile.is_manager()
    except UserProfile.DoesNotExist:
        return False


def is_store_manager(user):
    try:
        return user.is_authenticated and user.userprofile.is_store_manager()
    except UserProfile.DoesNotExist:
        return False


MANAGED_ROLES = ("worker", "supervisor")


def get_allow_worker_register():
    latest = SchedulingWindow.objects.order_by("-created_at").first()
    return latest.allow_worker_register if latest else False


@login_required
def post_login(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect("users:login")

    if profile.must_reset_password:
        messages.info(request, "請先使用臨時密碼重設密碼。")
        return redirect("users:password_change")

    if profile.is_manager():
        return redirect("scheduling:timeline")

    return redirect("scheduling:worker_schedule")


def _profile_missing_required_info(profile):
    return profile.missing_required_info()


class RoleLoginView(LoginView):
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["allow_worker_register"] = get_allow_worker_register()
        return context

    def get_success_url(self):
        return reverse_lazy("users:post_login")


class ForcedPasswordChangeView(PasswordChangeView):
    template_name = "users/password_change.html"
    success_url = reverse_lazy("users:post_login")

    def form_valid(self, form):
        response = super().form_valid(form)
        try:
            profile = self.request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = None
        if profile and profile.must_reset_password:
            profile.must_reset_password = False
            profile.save(update_fields=["must_reset_password"])
        messages.success(self.request, "密碼已更新。")
        return response


def reset_password_with_temp(request):
    if request.user.is_authenticated:
        return redirect("users:password_change")

    if request.method == "POST":
        form = TempPasswordResetForm(request.POST)
        if form.is_valid():
            user = form.user
            user.set_password(form.cleaned_data["new_password1"])
            user.save(update_fields=["password"])
            try:
                profile = user.userprofile
            except UserProfile.DoesNotExist:
                profile = None
            if profile and profile.must_reset_password:
                profile.must_reset_password = False
                profile.save(update_fields=["must_reset_password"])
            messages.success(request, "密碼已更新，請使用新密碼登入。")
            return redirect("users:login")
    else:
        form = TempPasswordResetForm()

    return render(request, "users/password_reset_temp.html", {"form": form})


def register_worker(request):
    if request.user.is_authenticated:
        return redirect("users:post_login")

    allow_worker_register = get_allow_worker_register()
    if request.method == "POST":
        if not allow_worker_register:
            messages.error(request, "目前未開放員工註冊。")
            return redirect("users:login")
        form = WorkerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                role="worker",
                name=form.cleaned_data.get("name", ""),
                sort_order=(UserProfile.objects.filter(role__in=MANAGED_ROLES).count() + 1),
            )
            messages.success(request, "註冊成功，請使用帳號登入。")
            return redirect("users:login")
    else:
        form = WorkerCreationForm()

    return render(
        request,
        "users/register.html",
        {"form": form, "allow_worker_register": allow_worker_register},
    )


@login_required
@user_passes_test(is_store_manager)
def create_worker(request):
    workers = (
        UserProfile.objects.filter(role__in=MANAGED_ROLES)
        .select_related("user")
        .order_by("sort_order", "name", "user__username")
    )
    worker_rows = []
    for worker in workers:
        missing_info = worker.missing_required_info()
        age = worker.age()
        worker_rows.append(
            {
                "profile": worker,
                "username": worker.user.username,
                "display_name": worker.name,
                "real_name": worker.real_name,
                "age": age if age is not None else "-",
                "missing_info": missing_info,
                "role_label": worker.get_role_display(),
            }
        )

    return render(
        request,
        "users/create_worker.html",
        {
            "workers": worker_rows,
        },
    )


@login_required
@user_passes_test(is_store_manager)
@require_POST
@csrf_exempt
def reorder_workers(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "資料格式錯誤"}, status=400)

    ordered_ids = payload.get("ordered_ids", [])
    if not isinstance(ordered_ids, list) or not ordered_ids:
        return JsonResponse({"ok": False, "error": "缺少排序資料"}, status=400)

    workers = list(UserProfile.objects.filter(role__in=MANAGED_ROLES, id__in=ordered_ids))
    if len(workers) != len(ordered_ids):
        return JsonResponse({"ok": False, "error": "資料不完整，請重新整理"}, status=400)

    id_to_profile = {w.id: w for w in workers}
    updates = []
    for idx, worker_id in enumerate(ordered_ids, start=1):
        profile = id_to_profile.get(worker_id)
        if profile.sort_order != idx:
            profile.sort_order = idx
            updates.append(profile)

    if updates:
        UserProfile.objects.bulk_update(updates, ["sort_order"])

    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_store_manager)
@require_POST
def delete_worker(request):
    profile_id = request.POST.get("profile_id")
    if not profile_id:
        messages.error(request, "缺少員工資料。")
        return redirect("users:create_worker")

    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).select_related("user").first()
    if not profile:
        messages.error(request, "找不到員工資料。")
        return redirect("users:create_worker")

    profile.user.delete()
    messages.success(request, "員工資料已刪除。")
    return redirect("users:create_worker")


IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/heic-sequence",
    "image/heif-sequence",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def _is_allowed_image_upload(file_obj):
    content_type = (file_obj.content_type or "").lower()
    if content_type in IMAGE_CONTENT_TYPES:
        return True
    if content_type in {"application/octet-stream", ""}:
        name = (file_obj.name or "").lower()
        return os.path.splitext(name)[1] in IMAGE_EXTENSIONS
    return False


def _is_allowed_upload(file_obj, allow_pdf=False):
    if _is_allowed_image_upload(file_obj):
        return True
    if allow_pdf and (file_obj.content_type or "").lower() == "application/pdf":
        return True
    return False


def _save_worker_document(profile, file_obj, category):
    if not file_obj:
        return
    existing = WorkerDocument.objects.filter(profile=profile, category=category)
    for doc in existing:
        if doc.file:
            doc.file.delete(save=False)
    existing.delete()
    WorkerDocument.objects.create(profile=profile, category=category, file=file_obj)


@login_required
@user_passes_test(is_store_manager)
def worker_create(request):
    if request.method == "POST":
        form = ManagerWorkerCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = False
            user.is_superuser = False
            user.first_name = ""
            user.last_name = ""
            user.save()
            profile = UserProfile.objects.create(
                user=user,
                role=form.cleaned_data.get("role") or "worker",
                name=form.cleaned_data["display_name"].strip(),
                real_name=form.cleaned_data["real_name"].strip(),
                gender=form.cleaned_data["gender"],
                birthday=form.cleaned_data["birthday"],
                id_number=form.cleaned_data["id_number"].strip(),
                marital_status=form.cleaned_data["marital_status"],
                education=form.cleaned_data["education"],
                education_other=form.cleaned_data.get("education_other", "").strip(),
                contact_address=form.cleaned_data["contact_address"].strip(),
                registered_address=form.cleaned_data["registered_address"].strip(),
                mobile_phone=form.cleaned_data["mobile_phone"].strip(),
                emergency_contact_name=form.cleaned_data["emergency_contact_name"].strip(),
                emergency_contact_relation=form.cleaned_data["emergency_contact_relation"].strip(),
                emergency_contact_phone=form.cleaned_data["emergency_contact_phone"].strip(),
                work_experience=form.cleaned_data["work_experience"].strip(),
                sort_order=(UserProfile.objects.filter(role__in=MANAGED_ROLES).count() + 1),
            )

            _save_worker_document(profile, request.FILES.get("id_card_front"), "id_card_front")
            _save_worker_document(profile, request.FILES.get("id_card_back"), "id_card_back")
            _save_worker_document(profile, request.FILES.get("driver_license_file"), "driver_license")
            _save_worker_document(profile, request.FILES.get("bankbook_file"), "bankbook")

            messages.success(request, "員工資料已建立。")
            return redirect("users:worker_detail", profile_id=profile.id)
    else:
        form = ManagerWorkerCreateForm()

    return render(
        request,
        "users/worker_detail.html",
        {
            "form": form,
            "is_create": True,
            "is_manager_view": True,
        },
    )


@login_required
@user_passes_test(is_store_manager)
def worker_detail(request, profile_id):
    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).select_related("user").first()
    if not profile:
        messages.error(request, "找不到員工資料。")
        return redirect("users:create_worker")

    if request.method == "POST":
        form = ManagerWorkerUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            role = form.cleaned_data.get("role")
            if role:
                profile.role = role
            profile.name = form.cleaned_data["display_name"].strip()
            profile.real_name = form.cleaned_data["real_name"].strip()
            profile.gender = form.cleaned_data["gender"]
            profile.birthday = form.cleaned_data["birthday"]
            profile.id_number = form.cleaned_data["id_number"].strip()
            profile.marital_status = form.cleaned_data["marital_status"]
            profile.education = form.cleaned_data["education"]
            profile.education_other = form.cleaned_data.get("education_other", "").strip()
            profile.contact_address = form.cleaned_data["contact_address"].strip()
            profile.registered_address = form.cleaned_data["registered_address"].strip()
            profile.mobile_phone = form.cleaned_data["mobile_phone"].strip()
            profile.emergency_contact_name = form.cleaned_data["emergency_contact_name"].strip()
            profile.emergency_contact_relation = form.cleaned_data["emergency_contact_relation"].strip()
            profile.emergency_contact_phone = form.cleaned_data["emergency_contact_phone"].strip()
            profile.work_experience = form.cleaned_data["work_experience"].strip()
            profile.save()

            _save_worker_document(profile, request.FILES.get("id_card_front"), "id_card_front")
            _save_worker_document(profile, request.FILES.get("id_card_back"), "id_card_back")
            _save_worker_document(profile, request.FILES.get("driver_license_file"), "driver_license")
            _save_worker_document(profile, request.FILES.get("bankbook_file"), "bankbook")

            messages.success(request, "員工資料已更新。")
            return redirect("users:worker_detail", profile_id=profile.id)
    else:
        form = ManagerWorkerUpdateForm(
            initial={
                "display_name": profile.name,
                "role": profile.role,
                "real_name": profile.real_name,
                "gender": profile.gender,
                "birthday": profile.birthday,
                "id_number": profile.id_number,
                "marital_status": profile.marital_status,
                "education": "其他" if profile.education == "Other" else profile.education,
                "education_other": profile.education_other,
                "contact_address": profile.contact_address,
                "registered_address": profile.registered_address,
                "mobile_phone": profile.mobile_phone,
                "emergency_contact_name": profile.emergency_contact_name,
                "emergency_contact_relation": profile.emergency_contact_relation,
                "emergency_contact_phone": profile.emergency_contact_phone,
                "work_experience": profile.work_experience,
            }
        )

    documents = {
        "id_card_front": _document_if_exists(
            profile.documents.filter(category="id_card_front").first()
        ),
        "id_card_back": _document_if_exists(
            profile.documents.filter(category="id_card_back").first()
        ),
        "driver_license": _document_if_exists(
            profile.documents.filter(category="driver_license").first()
        ),
        "bankbook": _document_if_exists(
            profile.documents.filter(category="bankbook").first()
        ),
    }

    return render(
        request,
        "users/worker_detail.html",
        {
            "form": form,
            "profile": profile,
            "documents": documents,
            "is_create": False,
            "is_manager_view": True,
            "upload_url": f"/users/create-worker/{profile.id}/upload/",
            "delete_url": f"/users/create-worker/{profile.id}/delete-document/",
        },
    )


@login_required
def worker_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect("users:login")

    if profile.is_manager():
        return redirect("users:create_worker")

    if request.method == "POST":
        form = ManagerWorkerUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            profile.name = form.cleaned_data["display_name"].strip()
            profile.real_name = form.cleaned_data["real_name"].strip()
            profile.gender = form.cleaned_data["gender"]
            profile.birthday = form.cleaned_data["birthday"]
            profile.id_number = form.cleaned_data["id_number"].strip()
            profile.marital_status = form.cleaned_data["marital_status"]
            profile.education = form.cleaned_data["education"]
            profile.education_other = form.cleaned_data.get("education_other", "").strip()
            profile.contact_address = form.cleaned_data["contact_address"].strip()
            profile.registered_address = form.cleaned_data["registered_address"].strip()
            profile.mobile_phone = form.cleaned_data["mobile_phone"].strip()
            profile.emergency_contact_name = form.cleaned_data["emergency_contact_name"].strip()
            profile.emergency_contact_relation = form.cleaned_data["emergency_contact_relation"].strip()
            profile.emergency_contact_phone = form.cleaned_data["emergency_contact_phone"].strip()
            profile.work_experience = form.cleaned_data["work_experience"].strip()
            profile.save()

            _save_worker_document(profile, request.FILES.get("id_card_front"), "id_card_front")
            _save_worker_document(profile, request.FILES.get("id_card_back"), "id_card_back")
            _save_worker_document(profile, request.FILES.get("driver_license_file"), "driver_license")
            _save_worker_document(profile, request.FILES.get("bankbook_file"), "bankbook")

            messages.success(request, "基本資料已更新。")
            return redirect("users:worker_profile")
    else:
        form = ManagerWorkerUpdateForm(
            initial={
                "display_name": profile.name,
                "role": profile.role,
                "real_name": profile.real_name,
                "gender": profile.gender,
                "birthday": profile.birthday,
                "id_number": profile.id_number,
                "marital_status": profile.marital_status,
                "education": "其他" if profile.education == "Other" else profile.education,
                "education_other": profile.education_other,
                "contact_address": profile.contact_address,
                "registered_address": profile.registered_address,
                "mobile_phone": profile.mobile_phone,
                "emergency_contact_name": profile.emergency_contact_name,
                "emergency_contact_relation": profile.emergency_contact_relation,
                "emergency_contact_phone": profile.emergency_contact_phone,
                "work_experience": profile.work_experience,
            }
        )

    documents = {
        "id_card_front": _document_if_exists(
            profile.documents.filter(category="id_card_front").first()
        ),
        "id_card_back": _document_if_exists(
            profile.documents.filter(category="id_card_back").first()
        ),
        "driver_license": _document_if_exists(
            profile.documents.filter(category="driver_license").first()
        ),
        "bankbook": _document_if_exists(
            profile.documents.filter(category="bankbook").first()
        ),
    }

    show_profile_warning = _profile_missing_required_info(profile)

    return render(
        request,
        "users/worker_detail.html",
        {
            "form": form,
            "profile": profile,
            "documents": documents,
            "is_create": False,
            "is_manager_view": False,
            "upload_url": "/users/profile/upload/",
            "delete_url": "/users/profile/delete-document/",
            "show_profile_warning": show_profile_warning,
        },
    )


@login_required
@user_passes_test(is_store_manager)
def upload_worker_document(request, profile_id):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method not allowed"}, status=405)

    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    category = request.POST.get("category")
    file_obj = request.FILES.get("file")
    if not category or not file_obj:
        return JsonResponse({"ok": False, "error": "缺少檔案或類別"}, status=400)

    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook"}
    if category not in allowed_categories:
        return JsonResponse({"ok": False, "error": "檔案類別錯誤"}, status=400)

    if category in {"id_card_front", "id_card_back"}:
        if not _is_allowed_image_upload(file_obj):
            return JsonResponse({"ok": False, "error": "身分證檔案需為 JPG/PNG/HEIC"}, status=400)
    else:
        if not _is_allowed_upload(file_obj, allow_pdf=True):
            return JsonResponse({"ok": False, "error": "檔案格式需為 JPG/PNG/HEIC/PDF"}, status=400)
    if file_obj.size > 10 * 1024 * 1024:
        return JsonResponse({"ok": False, "error": "檔案大小不可超過 10MB"}, status=400)


    _save_worker_document(profile, file_obj, category)
    document = profile.documents.filter(category=category).first()
    if not document:
        return JsonResponse({"ok": False, "error": "檔案儲存失敗"}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "file_url": document.file.url,
            "file_name": document.file.name,
        }
    )


@login_required
@require_POST
def upload_worker_document_self(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    if profile.is_manager():
        return JsonResponse({"ok": False, "error": "權限不足"}, status=403)

    category = request.POST.get("category")
    file_obj = request.FILES.get("file")
    if not category or not file_obj:
        return JsonResponse({"ok": False, "error": "缺少檔案或類別"}, status=400)

    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook"}
    if category not in allowed_categories:
        return JsonResponse({"ok": False, "error": "檔案類別錯誤"}, status=400)

    if category in {"id_card_front", "id_card_back"}:
        if not _is_allowed_image_upload(file_obj):
            return JsonResponse({"ok": False, "error": "身分證檔案需為 JPG/PNG/HEIC"}, status=400)
    else:
        if not _is_allowed_upload(file_obj, allow_pdf=True):
            return JsonResponse({"ok": False, "error": "檔案格式需為 JPG/PNG/HEIC/PDF"}, status=400)
    if file_obj.size > 10 * 1024 * 1024:
        return JsonResponse({"ok": False, "error": "檔案大小不可超過 10MB"}, status=400)

    _save_worker_document(profile, file_obj, category)
    document = profile.documents.filter(category=category).first()
    if not document:
        return JsonResponse({"ok": False, "error": "檔案儲存失敗"}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "file_url": document.file.url,
            "file_name": document.file.name,
        }
    )


@login_required
@user_passes_test(is_store_manager)
@require_POST
def delete_worker_document(request, profile_id):
    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    category = request.POST.get("category")
    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook"}
    if category not in allowed_categories:
        return JsonResponse({"ok": False, "error": "檔案類別錯誤"}, status=400)

    document = profile.documents.filter(category=category).first()
    if not document:
        return JsonResponse({"ok": True})

    if document.file:
        document.file.delete(save=False)
    document.delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def delete_worker_document_self(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    if profile.is_manager():
        return JsonResponse({"ok": False, "error": "權限不足"}, status=403)

    category = request.POST.get("category")
    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook"}
    if category not in allowed_categories:
        return JsonResponse({"ok": False, "error": "檔案類別錯誤"}, status=400)

    document = profile.documents.filter(category=category).first()
    if not document:
        return JsonResponse({"ok": True})

    if document.file:
        document.file.delete(save=False)
    document.delete()
    return JsonResponse({"ok": True})


@login_required
@user_passes_test(is_store_manager)
@require_POST
def reset_worker_password(request, profile_id):
    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).select_related("user").first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    temp_password = "".join(secrets.choice(string.digits) for _ in range(6))
    profile.user.set_password(temp_password)
    profile.user.save(update_fields=["password"])
    profile.must_reset_password = True
    profile.save(update_fields=["must_reset_password"])
    return JsonResponse({"ok": True, "temp_password": temp_password})


def _document_if_exists(doc):
    if not doc or not doc.file:
        return None
    if not default_storage.exists(doc.file.name):
        return None
    return doc
