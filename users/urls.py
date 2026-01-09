from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'
urlpatterns = [
    path('login/', views.RoleLoginView.as_view(template_name='users/login.html'), name='login'),
    path('register/', views.register_worker, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('post-login/', views.post_login, name='post_login'),
    path('password/reset/', views.reset_password_with_temp, name='password_reset_temp'),
    path('password/change/', views.ForcedPasswordChangeView.as_view(), name='password_change'),
    path('profile/', views.worker_profile, name='worker_profile'),
    path('profile/upload/', views.upload_worker_document_self, name='worker_upload_self'),
    path('profile/delete-document/', views.delete_worker_document_self, name='worker_delete_document_self'),
    path('salary/manage/', views.salary_manage, name='salary_manage'),
    path('salary/', views.salary_list, name='salary_list'),
    path('salary/<int:slip_id>/', views.salary_detail, name='salary_detail'),
    path('create-worker/', views.create_worker, name='create_worker'),
    path('create-worker/add/', views.worker_create, name='worker_create'),
    path('create-worker/<int:profile_id>/', views.worker_detail, name='worker_detail'),
    path('create-worker/<int:profile_id>/upload/', views.upload_worker_document, name='worker_upload'),
    path('create-worker/<int:profile_id>/employment-status/', views.update_worker_employment_status, name='worker_employment_status'),
    path('create-worker/<int:profile_id>/pay-type/', views.update_worker_pay_type, name='worker_pay_type'),
    path('create-worker/<int:profile_id>/primary-store/', views.update_worker_primary_store, name='worker_primary_store'),
    path('create-worker/<int:profile_id>/reset-password/', views.reset_worker_password, name='worker_reset_password'),
    path('create-worker/<int:profile_id>/delete-document/', views.delete_worker_document, name='worker_delete_document'),
    path('create-worker/reorder/', views.reorder_workers, name='reorder_workers'),
    path('create-worker/delete/', views.delete_worker, name='delete_worker'),
    # Admin 負責建立 User 和 UserProfile
]
