# scheduling/urls.py (修正後)
from django.urls import path
from . import views

app_name = 'scheduling'
urlpatterns = [
    # 總班表日曆頁面 (店長專用) -> 轉到員工班表
    path('list/', views.scheduling_list, name='list'),
    # 員工班表頁面 (店長專用)
    path('timeline/', views.scheduling_timeline, name='timeline'),
    path('window/', views.manage_window, name='manage_window'),
    path('my-availability/', views.worker_schedule, name='worker_schedule'),
    
    path("shift/create/", views.create_shift, name="shift_create"),
    path("shift/delete/", views.delete_shift, name="shift_delete"),
    path("shift/update/", views.update_shift, name="shift_update"),
    path("availability/create/", views.create_availability, name="availability_create"),
    path("availability/delete/", views.delete_availability, name="availability_delete"),
    path("availability/update/", views.update_availability, name="availability_update"),
    path("shift/worker/update/", views.update_worker_shift, name="worker_shift_update"),
    path("shift/worker/delete/", views.delete_worker_shift, name="worker_shift_delete"),
    path("shift/worker/create/", views.create_worker_shift, name="worker_shift_create"),


    # 匯出 Excel 報表
    path('export/excel/', views.export_excel_view, name='export_excel'),
]
