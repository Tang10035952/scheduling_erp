# scheduling/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from django.utils.timezone import localtime, now

from availability.models import WorkAvailability
from users.models import UserProfile
from .models import Shift

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from .utils import intersection_time
from django.views.decorators.csrf import csrf_exempt

import json

def is_manager(user):
    try:
        return user.is_authenticated and user.userprofile.is_manager()
    except UserProfile.DoesNotExist:
        return False


@login_required
@user_passes_test(is_manager)
def scheduling_list(request):
    """
    總班表頁面：
    - 前端會用 FullCalendar 顯示 Shift
    - 只讀：店長先用 Django admin 建立幾筆 Shift 測試
    """
    return render(request, 'scheduling/list.html')


@login_required
@user_passes_test(is_manager)
def scheduling_data(request):
    events = []

    # ========= 1) 員工可上班意願（淡色） =========
    avs = WorkAvailability.objects.filter(available=True).select_related("employee__user")

    for av in avs:
        start_dt = datetime.combine(av.date, av.start_time)
        end_dt = datetime.combine(av.date, av.end_time)

        events.append({
            "id": f"av-{av.id}",
            "title": f"{av.employee.user.get_full_name()}（意願）",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "backgroundColor": "#ADD8E6",  # 淺藍 → 淡色
            "borderColor": "#87CEEB",
            "type": "shift",
        })

    # ========= 2) 最終班表（深色） =========
    shifts = Shift.objects.select_related("employee__user")

    for s in shifts:
        start_dt = datetime.combine(s.date, s.start_time)
        end_dt = datetime.combine(s.date, s.end_time)

        events.append({
            "id": f"shift-{s.id}",
            "title": f"{s.employee.user.get_full_name()}（正式）",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "backgroundColor": "#1E88E5",  # 深藍 → 強調
            "borderColor": "#1565C0",
            "type": "shift",
        })

    return JsonResponse(events, safe=False)



@login_required
@user_passes_test(is_manager)
def export_excel_view(request):
    """
    匯出目前所有 Shift 為 Excel。
    """
    shifts = Shift.objects.select_related('employee__user').all().order_by('date', 'start_time')

    wb = Workbook()
    ws = wb.active
    ws.title = "班表"

    # 標題列
    headers = ["日期", "員工姓名", "開始時間", "結束時間", "是否發佈"]
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center")

    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.font = header_font
        cell.alignment = center
        cell.fill = header_fill

    # 資料列
    row_num = 2
    for s in shifts:
        start_dt = datetime.combine(s.date, s.start_time)
        end_dt = datetime.combine(s.date, s.end_time)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        ws.cell(row=row_num, column=1, value=s.date.strftime("%Y-%m-%d"))
        ws.cell(row=row_num, column=2, value=s.employee.user.get_full_name() or s.employee.user.username)
        ws.cell(row=row_num, column=3, value=s.start_time.strftime("%H:%M"))
        ws.cell(row=row_num, column=4, value=s.end_time.strftime("%H:%M"))
        ws.cell(row=row_num, column=5, value="是" if s.is_published else "否")

        row_num += 1

    # 欄寬自動調整
    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2

    # 回應
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename_time = localtime(now()).strftime("%Y%m%d_%H%M%S")
    response['Content-Disposition'] = f'attachment; filename="shift_report_{filename_time}.xlsx"'

    wb.save(response)
    return response

def get_available_workers(request, date_str):
    # FullCalendar 會傳 2025-12-11T09:30:00+08:00
    # 我們只取前 10 碼作為日期：2025-12-11
    clean_date = date_str[:10]

    date = datetime.strptime(clean_date, "%Y-%m-%d").date()

    av_qs = WorkAvailability.objects.filter(date=date, available=True).select_related("employee__user")

    workers = []
    for av in av_qs:
        workers.append({
            "id": av.employee.id,
            "name": av.employee.user.get_full_name(),
            "start": av.start_time.strftime("%H:%M"),
            "end": av.end_time.strftime("%H:%M"),
        })

    return JsonResponse(workers, safe=False)


@csrf_exempt
def calc_intersection(request):
    payload = json.loads(request.body)
    ranges = payload["ranges"]  # [["09:00","15:00"], ["12:00","18:00"]...]

    time_ranges = [
        (
            datetime.strptime(start, "%H:%M").time(),
            datetime.strptime(end, "%H:%M").time(),
        )
        for start, end in ranges
    ]

    s, e = intersection_time(time_ranges)

    if not s:
        return JsonResponse({"start": None, "end": None})

    return JsonResponse({
        "start": s.strftime("%H:%M"),
        "end": e.strftime("%H:%M")
    })

@csrf_exempt
def create_shift_from_availability(request):
    data = json.loads(request.body)

    clean_date = data["date"][:10]
    date = datetime.strptime(clean_date, "%Y-%m-%d").date()

    start = datetime.strptime(data["start"], "%H:%M").time()
    end = datetime.strptime(data["end"], "%H:%M").time()

    employee_ids = data["employees"]

    created = []
    skipped = []

    for eid in employee_ids:

        # 不重複建立 Shift
        exists = Shift.objects.filter(
            employee_id=eid,
            date=date,
            start_time=start,
            end_time=end
        ).exists()

        if exists:
            skipped.append(eid)
            continue

        # 建立正式班表
        Shift.objects.create(
            employee_id=eid,
            date=date,
            start_time=start,
            end_time=end,
            is_published=True
        )

        created.append(eid)

        # 🔥 移除該時段的意願表（避免意願 + 正式班表重疊）
        WorkAvailability.objects.filter(
            employee_id=eid,
            date=date,
            start_time=start,
            end_time=end,
            available=True
        ).delete()

    return JsonResponse({"ok": True, "created": created, "skipped": skipped})

@csrf_exempt
def delete_shift(request):
    data = json.loads(request.body)
    shift_id = data.get("id")

    Shift.objects.filter(id=shift_id).delete()
    return JsonResponse({"ok": True})

@csrf_exempt
def update_shift(request):
    data = json.loads(request.body)

    shift = Shift.objects.get(id=data["id"])
    shift.start_time = datetime.strptime(data["start"], "%H:%M").time()
    shift.end_time = datetime.strptime(data["end"], "%H:%M").time()
    shift.save()

    return JsonResponse({"ok": True})
