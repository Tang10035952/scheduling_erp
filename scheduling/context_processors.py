from .models import SchedulingWindow


def worker_view_setting(request):
    if not request.user.is_authenticated:
        return {}
    latest = SchedulingWindow.objects.order_by("-created_at").first()
    allow_worker_view = latest.allow_worker_view if latest else False
    return {"allow_worker_view": allow_worker_view}
