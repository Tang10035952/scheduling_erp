# availability/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from datetime import date, datetime, timedelta
from .models import WorkAvailability, FillRangeSetting
from users.models import UserProfile

def is_manager(user):
    try:
        return user.is_authenticated and user.userprofile.is_manager()
    except UserProfile.DoesNotExist:
        return False


@login_required
def availability_home(request):
    """
    員工與店長進入的主入口
    - 店長 → 員工列表（manager_dashboard.html）
    - 員工 → 可上班意願 Dashboard（home.html）
    """
    profile = get_object_or_404(UserProfile, user=request.user)

    # === 店長視角 ===
    if profile.is_manager():
        employees = UserProfile.objects.filter(role='worker').select_related('user')
        return render(request, 'availability/manager_dashboard.html', {
            'employees': employees,
        })

    # === 員工視角 ===
    # 不做填寫功能，改成跳轉連結（符合新設計）
    return render(request, 'availability/home.html', {
        'employee': profile,
    })

@user_passes_test(is_manager)
def employee_calendar_view(request, employee_id):
    """
    店長點某位員工 → 看到該員工的可上班行事曆（前端會用 FullCalendar 呼叫 data API）
    """
    employee = get_object_or_404(UserProfile, id=employee_id, role='worker')
    return render(request, 'availability/employee_calendar.html', {
        'employee': employee,
    })


@user_passes_test(is_manager)
def employee_calendar_data(request, employee_id):
    availabilities = WorkAvailability.objects.filter(employee_id=employee_id)

    events = []

    for av in availabilities:
        start_dt = datetime.combine(av.date, av.start_time)
        end_dt = datetime.combine(av.date, av.end_time)

        # ⭐ 在這裡定義 start_str / end_str
        start_str = av.start_time.strftime("%H:%M")
        end_str = av.end_time.strftime("%H:%M")

        events.append({
            "title": f"{av.employee.user.get_full_name()} {start_str}-{end_str}",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "backgroundColor": "#64B5F6",  # 你之後可改成員工個別色
            "borderColor": "#64B5F6",
        })

    return JsonResponse(events, safe=False)


@login_required
def delete_availability(request, availability_id):
    """
    允許：
    - 該員工自己刪除自己的意願
    - 或店長幫忙刪除
    """
    availability = get_object_or_404(WorkAvailability, id=availability_id)
    profile = get_object_or_404(UserProfile, user=request.user)

    if availability.employee != profile and not profile.is_manager():
        return HttpResponseForbidden("你沒有權限刪除此記錄")

    availability.delete()
    # 回到員工主頁（若是店長刪的，也跳到 availability:home）
    return redirect('availability:home')

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def get_default_week_range():
    today = date.today()
    start = today - timedelta(days=today.weekday())  # 本週一
    end = start + timedelta(days=6)                  # 本週日
    return start, end

@login_required
def fill_availability(request):
    employee = request.user.userprofile  # 使用登入者
    # 若店長有設定 → 使用店長設定
    setting = FillRangeSetting.objects.first()
    if setting:
        start_date = setting.start_date
        end_date = setting.end_date
    else:
        # ✨ 沒設定 → 預設本週
        start_date, end_date = get_default_week_range()

    if request.method == "POST":
        for d in daterange(start_date, end_date):
            key = d.strftime("%Y-%m-%d")

            avail = request.POST.get(f"avail-{key}")
            start_t = request.POST.get(f"start-{key}")
            end_t   = request.POST.get(f"end-{key}")

            obj, _ = WorkAvailability.objects.get_or_create(
                employee=employee,
                date=d
            )

            if avail == "yes":
                obj.available = True
                obj.start_time = start_t
                obj.end_time = end_t
            else:
                obj.available = False
                obj.start_time = None
                obj.end_time = None

            obj.save()

        return redirect("availability:fill")

    context = {
        "dates": list(daterange(start_date, end_date)),  # ← 必須回傳
        "employee": employee,
    }
    return render(request, "availability/fill.html", context)

@login_required
def employee_calendar_view_self(request):
    employee = request.user.userprofile
    return render(request, "availability/calendar.html", {
        "employee": employee,
    })
