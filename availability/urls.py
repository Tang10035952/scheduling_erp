from django.urls import path
from . import views

app_name = 'availability'
urlpatterns = [
    # 員工和店長的主頁入口
    path('', views.availability_home, name='home'), 
    path('fill/', views.fill_availability, name='fill'),
    path('calendar/', views.employee_calendar_view_self, name='calendar_self'),
    # 店長查看特定員工意願的日曆數據 (JSON)
    path('employee/<int:employee_id>/data/', views.employee_calendar_data, name='calendar_data'),
    # 店長查看特定員工意願的日曆畫面
    path('employee/<int:employee_id>/', views.employee_calendar_view, name='calendar_view'),
    # 刪除意願的路由 (使用 ID 捕獲)
    path('delete/<int:availability_id>/', views.delete_availability, name='delete'),
]