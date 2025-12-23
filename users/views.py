from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from .forms import WorkerCreationForm
from .models import UserProfile


def is_manager(user):
    try:
        return user.is_authenticated and user.userprofile.is_manager()
    except UserProfile.DoesNotExist:
        return False


@login_required
def post_login(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return redirect("users:login")

    if profile.is_manager():
        return redirect("scheduling:timeline")

    return redirect("scheduling:worker_schedule")


class RoleLoginView(LoginView):
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("users:post_login")


@login_required
@user_passes_test(is_manager)
def create_worker(request):
    if request.method == "POST":
        update_profile_id = request.POST.get("update_profile_id")
        if update_profile_id:
            name = request.POST.get("name", "").strip()
            updated = UserProfile.objects.filter(id=update_profile_id, role="worker").update(
                name=name,
            )
            if updated:
                messages.success(request, "員工資料已更新。")
            else:
                messages.error(request, "找不到員工資料。")
            return redirect("users:create_worker")

        form = WorkerCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                role="worker",
                name=form.cleaned_data.get("name", ""),
                sort_order=(UserProfile.objects.filter(role="worker").count() + 1),
            )
            messages.success(request, "員工帳號已建立，可以通知對方使用。")
            return redirect("users:create_worker")
    else:
        form = WorkerCreationForm()

    workers = (
        UserProfile.objects.filter(role="worker")
        .select_related("user")
        .order_by("sort_order", "name", "user__username")
    )

    return render(
        request,
        "users/create_worker.html",
        {
            "form": form,
            "workers": workers,
        },
    )


@login_required
@user_passes_test(is_manager)
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

    workers = list(UserProfile.objects.filter(role="worker", id__in=ordered_ids))
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
@user_passes_test(is_manager)
@require_POST
def delete_worker(request):
    profile_id = request.POST.get("profile_id")
    if not profile_id:
        messages.error(request, "缺少員工資料。")
        return redirect("users:create_worker")

    profile = UserProfile.objects.filter(id=profile_id, role="worker").select_related("user").first()
    if not profile:
        messages.error(request, "找不到員工資料。")
        return redirect("users:create_worker")

    profile.user.delete()
    messages.success(request, "員工資料已刪除。")
    return redirect("users:create_worker")
