from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.utils import timezone
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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import UserProfile, WorkerDocument, SalarySlip
from scheduling.models import SchedulingWindow, Shift, Store


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


MANAGED_ROLES = ("worker", "supervisor", "manager")


def get_allow_worker_register():
    latest = SchedulingWindow.objects.order_by("-created_at").first()
    return latest.allow_worker_register if latest else False


def _parse_year_month(request, source="GET"):
    data = request.GET if source == "GET" else request.POST
    today = timezone.localdate()
    year_month = (data.get("year_month") or "").strip()
    if year_month:
        try:
            year_str, month_str = year_month.split("-")
            year = int(year_str)
            month = int(month_str)
            if 1 <= month <= 12:
                return year, month
        except (ValueError, AttributeError):
            pass
    year = data.get("year")
    month = data.get("month")
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(month)
    except (TypeError, ValueError):
        month = today.month
    if month < 1 or month > 12:
        month = today.month
    return year, month


def _parse_decimal(value, label):
    raw = (value or "").strip()
    if not raw:
        return Decimal("0")
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} 格式錯誤")


def _parse_pay_type(value, label):
    raw = (value or "").strip()
    if raw in {"hourly", "salaried"}:
        return raw
    raise ValueError(f"{label} 格式錯誤")


def _salary_has_value_query():
    fields = [
        "base_salary",
        "overtime_salary",
        "work_hours",
        "overtime_hours",
        "base_pay",
        "overtime_pay",
        "insurance_transfer",
        "performance_bonus",
        "labor_insurance",
        "extra_health_insurance",
        "responsibility_bonus",
        "perfect_attendance",
        "total_salary",
    ]
    query = Q()
    for field in fields:
        query |= ~Q(**{field: 0})
    return query


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
    role_order = Case(
        When(role="manager", then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    workers = (
        UserProfile.objects.filter(role__in=MANAGED_ROLES)
        .exclude(Q(name="系統管理員") | Q(user__username="系統管理員"))
        .annotate(role_order=role_order)
        .select_related("user")
        .order_by("role_order", "sort_order", "name", "user__username")
    )
    worker_rows = []
    stores = list(Store.objects.all())
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
                "mobile_phone": worker.mobile_phone,
                "missing_info": missing_info,
                "role_label": worker.get_role_display(),
                "employment_status": worker.employment_status,
                "employment_status_label": worker.get_employment_status_display(),
                "pay_type": worker.pay_type,
                "pay_type_label": worker.get_pay_type_display(),
                "primary_store_id": worker.primary_store_id,
                "primary_store_name": worker.primary_store.name if worker.primary_store else "",
            }
        )

    return render(
        request,
        "users/create_worker.html",
        {
            "workers": worker_rows,
            "stores": stores,
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


@login_required
@user_passes_test(is_store_manager)
@require_POST
def update_worker_employment_status(request, profile_id):
    status = request.POST.get("employment_status")
    if status not in {"active", "inactive"}:
        return JsonResponse({"ok": False, "error": "狀態錯誤"}, status=400)

    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    if profile.employment_status != status:
        profile.employment_status = status
        profile.save(update_fields=["employment_status"])

    return JsonResponse(
        {
            "ok": True,
            "employment_status": profile.employment_status,
            "employment_status_label": profile.get_employment_status_display(),
        }
    )


@login_required
@user_passes_test(is_store_manager)
@require_POST
def update_worker_pay_type(request, profile_id):
    pay_type = request.POST.get("pay_type")
    if pay_type not in {"hourly", "salaried"}:
        return JsonResponse({"ok": False, "error": "薪資類型錯誤"}, status=400)

    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    if profile.pay_type != pay_type:
        profile.pay_type = pay_type
        profile.save(update_fields=["pay_type"])

    return JsonResponse(
        {
            "ok": True,
            "pay_type": profile.pay_type,
            "pay_type_label": profile.get_pay_type_display(),
        }
    )


@login_required
@user_passes_test(is_store_manager)
@require_POST
def update_worker_primary_store(request, profile_id):
    store_id = request.POST.get("primary_store")
    if not store_id:
        return JsonResponse({"ok": False, "error": "請選擇店別"}, status=400)
    try:
        store_id = int(store_id)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "店別格式錯誤"}, status=400)

    store = Store.objects.filter(id=store_id).first()
    if not store:
        return JsonResponse({"ok": False, "error": "店別不存在"}, status=404)

    profile = UserProfile.objects.filter(id=profile_id, role__in=MANAGED_ROLES).first()
    if not profile:
        return JsonResponse({"ok": False, "error": "找不到員工資料"}, status=404)

    if profile.primary_store_id != store.id:
        profile.primary_store = store
        profile.save(update_fields=["primary_store"])

    return JsonResponse({"ok": True, "primary_store_id": store.id, "primary_store_name": store.name})


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
            display_name = (form.cleaned_data.get("display_name") or "").strip() or user.username
            profile = UserProfile.objects.create(
                user=user,
                role=form.cleaned_data.get("role") or "worker",
                pay_type=form.cleaned_data.get("pay_type") or "hourly",
                name=display_name,
                real_name=(form.cleaned_data.get("real_name") or "").strip(),
                gender=form.cleaned_data.get("gender") or "",
                birthday=form.cleaned_data.get("birthday"),
                id_number=(form.cleaned_data.get("id_number") or "").strip(),
                marital_status=form.cleaned_data.get("marital_status") or "",
                education=form.cleaned_data.get("education") or "",
                education_other=(form.cleaned_data.get("education_other") or "").strip(),
                contact_address=(form.cleaned_data.get("contact_address") or "").strip(),
                registered_address=(form.cleaned_data.get("registered_address") or "").strip(),
                mobile_phone=(form.cleaned_data.get("mobile_phone") or "").strip(),
                emergency_contact_name=(form.cleaned_data.get("emergency_contact_name") or "").strip(),
                emergency_contact_relation=(form.cleaned_data.get("emergency_contact_relation") or "").strip(),
                emergency_contact_phone=(form.cleaned_data.get("emergency_contact_phone") or "").strip(),
                work_experience=(form.cleaned_data.get("work_experience") or "").strip(),
                sort_order=(UserProfile.objects.filter(role__in=MANAGED_ROLES).count() + 1),
                primary_store=form.cleaned_data.get("primary_store"),
            )

            _save_worker_document(profile, request.FILES.get("id_card_front"), "id_card_front")
            _save_worker_document(profile, request.FILES.get("id_card_back"), "id_card_back")
            _save_worker_document(profile, request.FILES.get("driver_license_file"), "driver_license")
            _save_worker_document(profile, request.FILES.get("bankbook_file"), "bankbook")
            _save_worker_document(profile, request.FILES.get("other_file"), "other")

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
        form = ManagerWorkerUpdateForm(request.POST, request.FILES, require_store=False)
        if form.is_valid():
            role = form.cleaned_data.get("role")
            if role:
                profile.role = role
            pay_type = form.cleaned_data.get("pay_type")
            if pay_type:
                profile.pay_type = pay_type
            primary_store = form.cleaned_data.get("primary_store")
            if primary_store:
                profile.primary_store = primary_store
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
            _save_worker_document(profile, request.FILES.get("other_file"), "other")

            messages.success(request, "員工資料已更新。")
            return redirect("users:worker_detail", profile_id=profile.id)
    else:
        form = ManagerWorkerUpdateForm(
            initial={
                "display_name": profile.name,
                "role": profile.role,
                "pay_type": profile.pay_type,
                "primary_store": profile.primary_store,
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
            },
            require_store=False,
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
        "other": _document_if_exists(
            profile.documents.filter(category="other").first()
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
            profile.primary_store = form.cleaned_data.get("primary_store")
            profile.save()

            _save_worker_document(profile, request.FILES.get("id_card_front"), "id_card_front")
            _save_worker_document(profile, request.FILES.get("id_card_back"), "id_card_back")
            _save_worker_document(profile, request.FILES.get("driver_license_file"), "driver_license")
            _save_worker_document(profile, request.FILES.get("bankbook_file"), "bankbook")
            _save_worker_document(profile, request.FILES.get("other_file"), "other")

            messages.success(request, "基本資料已更新。")
            return redirect("users:worker_profile")
    else:
        form = ManagerWorkerUpdateForm(
            initial={
                "display_name": profile.name,
                "role": profile.role,
                "pay_type": profile.pay_type,
                "primary_store": profile.primary_store,
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
        "other": _document_if_exists(
            profile.documents.filter(category="other").first()
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

    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook", "other"}
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

    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook", "other"}
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
    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook", "other"}
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
    allowed_categories = {"id_card_front", "id_card_back", "driver_license", "bankbook", "other"}
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


@login_required
@user_passes_test(is_store_manager)
def salary_manage(request):
    today = timezone.localdate()
    year, month = _parse_year_month(request, source="POST" if request.method == "POST" else "GET")
    store_value = (request.POST.get("store") if request.method == "POST" else request.GET.get("store")) or "all"
    store_value = store_value.strip() or "all"
    employee_ids = (
        Shift.objects.filter(date__year=year, date__month=month)
        .values_list("employee_id", flat=True)
        .distinct()
    )
    profiles_qs = UserProfile.objects.filter(id__in=employee_ids)
    if store_value != "all":
        try:
            store_id = int(store_value)
        except (TypeError, ValueError):
            store_id = None
        if store_id and Store.objects.filter(id=store_id).exists():
            profiles_qs = profiles_qs.filter(primary_store_id=store_id)
        else:
            store_value = "all"

    profiles = (
        profiles_qs.select_related("user", "primary_store")
        .annotate(
            self_order=Case(
                When(id=request.user.userprofile.id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            pay_order=Case(
                When(pay_type="salaried", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("self_order", "pay_order", "sort_order", "name", "user__username")
    )
    slips = SalarySlip.objects.filter(profile__in=profiles, year=year, month=month)
    slip_by_profile = {slip.profile_id: slip for slip in slips}
    total_salary_sum = sum((slip.total_salary or Decimal("0")) for slip in slips)
    fields = [
        ("pay_type", "薪資方式"),
        ("base_salary", "底薪"),
        ("overtime_salary", "加班薪資"),
        ("work_hours", "上班時數"),
        ("overtime_hours", "加班時數"),
        ("base_pay", "底薪薪資(A)"),
        ("overtime_pay", "加班薪資(B)"),
        ("insurance_transfer", "保險+轉帳(C)"),
        ("performance_bonus", "業績獎金(D)"),
        ("labor_insurance", "勞建保(E)"),
        ("extra_health_insurance", "多扣兩個月健保(F)"),
        ("responsibility_bonus", "責任獎金(G)"),
        ("perfect_attendance", "全勤(H)"),
        ("total_salary", "總薪資"),
    ]

    numeric_fields = [field for field in fields if field[0] != "pay_type"]

    if request.method == "POST":
        errors = []
        pending = []
        for profile in profiles:
            values = {}
            for field_name, label in numeric_fields:
                try:
                    value = _parse_decimal(
                        request.POST.get(f"slip-{profile.id}-{field_name}"),
                        label,
                    )
                except ValueError as exc:
                    errors.append(f"{profile.display_name()}：{exc}")
                    value = None
                values[field_name] = value
            try:
                pay_type_value = _parse_pay_type(
                    request.POST.get(f"slip-{profile.id}-pay_type"),
                    "薪資方式",
                )
            except ValueError as exc:
                errors.append(f"{profile.display_name()}：{exc}")
                pay_type_value = profile.pay_type
            values["pay_type"] = pay_type_value

            pending.append((profile, values))

        if not errors:
            for profile, values in pending:
                if values.get("pay_type") == "hourly":
                    base_salary = values.get("base_salary")
                    work_hours = values.get("work_hours")
                    if base_salary is not None and work_hours is not None:
                        values["base_pay"] = (base_salary * work_hours).quantize(
                            Decimal("1"),
                            rounding=ROUND_HALF_UP,
                        )
                    else:
                        values["base_pay"] = None
                existing = slip_by_profile.get(profile.id)

                if existing:
                    for field_name, _ in fields:
                        setattr(existing, field_name, values[field_name])
                    existing.save(update_fields=[f[0] for f in fields] + ["updated_at"])
                else:
                    SalarySlip.objects.create(profile=profile, year=year, month=month, **values)

        if errors:
            messages.error(request, "、".join(errors))
        else:
            messages.success(request, "薪資資料已更新。")

        slips = SalarySlip.objects.filter(profile_id__in=employee_ids, year=year, month=month)
        slip_by_profile = {slip.profile_id: slip for slip in slips}

    roc_year = year - 1911 if year >= 1912 else year
    roc_label = f"{roc_year}年{month}月"
    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    rows = []
    for profile in profiles:
        slip = slip_by_profile.get(profile.id)
        row_pay_type = slip.pay_type if slip and slip.pay_type else profile.pay_type
        rows.append({"profile": profile, "slip": slip, "pay_type": row_pay_type})
    rows = sorted(
        rows,
        key=lambda row: (
            0 if row["profile"].id == request.user.userprofile.id else 1,
            0 if row["pay_type"] == "salaried" else 1,
            row["profile"].sort_order,
            row["profile"].name,
            row["profile"].user.username,
        ),
    )
    salaried_rows = [row for row in rows if row["pay_type"] == "salaried"]
    hourly_rows = [row for row in rows if row["pay_type"] != "salaried"]
    total_count = len(rows)

    return render(
        request,
        "users/salary_manage.html",
        {
            "rows": rows,
            "salaried_rows": salaried_rows,
            "hourly_rows": hourly_rows,
            "total_count": total_count,
            "fields": fields,
            "year": year,
            "month": month,
            "roc_label": roc_label,
            "year_month": f"{year:04d}-{month:02d}",
            "prev_year_month": f"{prev_year:04d}-{prev_month:02d}",
            "next_year_month": f"{next_year:04d}-{next_month:02d}",
            "today_str": today.strftime("%Y-%m-%d"),
            "stores": Store.objects.all(),
            "selected_store": store_value,
            "total_salary_sum": total_salary_sum,
            "pay_type_choices": UserProfile.PAY_TYPES,
        },
    )


@login_required
def salary_list(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect("users:login")

    slips = (
        SalarySlip.objects.filter(profile=profile)
        .filter(_salary_has_value_query())
        .order_by("-year", "-month", "id")
    )
    return render(
        request,
        "users/salary_list.html",
        {
            "profile": profile,
            "slips": slips,
        },
    )


@login_required
def salary_detail(request, slip_id):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect("users:login")

    slip = SalarySlip.objects.filter(id=slip_id, profile=profile).select_related("profile__user").first()
    if not slip:
        messages.error(request, "找不到薪資單。")
        return redirect("users:salary_list")
    if not SalarySlip.objects.filter(id=slip_id).filter(_salary_has_value_query()).exists():
        return redirect("users:salary_list")

    year = slip.year
    month = slip.month
    roc_year = year - 1911 if year >= 1912 else year

    return render(
        request,
        "users/salary_detail.html",
        {
            "profile": profile,
            "slip": slip,
            "roc_year": roc_year,
            "month": month,
        },
    )


@login_required
@user_passes_test(is_store_manager)
def update_salary_pay_type(request):
    if request.method != "POST":
        return JsonResponse({"error": "invalid_method"}, status=405)

    profile_id = request.POST.get("profile_id")
    if not profile_id:
        return JsonResponse({"error": "missing_profile"}, status=400)
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_profile"}, status=400)
    profile = UserProfile.objects.filter(id=profile_id).first()
    if not profile:
        return JsonResponse({"error": "profile_not_found"}, status=404)

    year, month = _parse_year_month(request, source="POST")
    try:
        pay_type = _parse_pay_type(request.POST.get("pay_type"), "薪資方式")
    except ValueError:
        return JsonResponse({"error": "invalid_pay_type"}, status=400)

    SalarySlip.objects.update_or_create(
        profile=profile,
        year=year,
        month=month,
        defaults={"pay_type": pay_type},
    )
    return JsonResponse({"ok": True, "pay_type": pay_type})


def _document_if_exists(doc):
    if not doc or not doc.file:
        return None
    if not default_storage.exists(doc.file.name):
        return None
    return doc
