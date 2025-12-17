# scheduling/urls.py (修正後)
from django.urls import path
from . import views

app_name = 'scheduling'
urlpatterns = [
    # 總班表日曆頁面 (店長專用)
    path('list/', views.scheduling_list, name='list'),
    
    # 獲取日曆數據的 API
    path('data/', views.scheduling_data, name='data'),
    
    path("available-workers/<str:date_str>/", views.get_available_workers, name="available_workers"),
    path("calc-intersection/", views.calc_intersection, name="calc_intersection"),
    path("create-shift/", views.create_shift_from_availability, name="create_shift"),
    
    path("shift/delete/", views.delete_shift, name="shift_delete"),
    path("shift/update/", views.update_shift, name="shift_update"),


    # 匯出 Excel 報表
    path('export/excel/', views.export_excel_view, name='export_excel'),
]