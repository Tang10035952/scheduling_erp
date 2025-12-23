from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'
urlpatterns = [
    path('login/', views.RoleLoginView.as_view(template_name='users/login.html'), name='login'),
    path('register/', views.register_worker, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('post-login/', views.post_login, name='post_login'),
    path('create-worker/', views.create_worker, name='create_worker'),
    path('create-worker/add/', views.worker_create, name='worker_create'),
    path('create-worker/<int:profile_id>/', views.worker_detail, name='worker_detail'),
    path('create-worker/<int:profile_id>/upload/', views.upload_worker_document, name='worker_upload'),
    path('create-worker/<int:profile_id>/delete-document/', views.delete_worker_document, name='worker_delete_document'),
    path('create-worker/reorder/', views.reorder_workers, name='reorder_workers'),
    path('create-worker/delete/', views.delete_worker, name='delete_worker'),
    # Admin 負責建立 User 和 UserProfile
]
