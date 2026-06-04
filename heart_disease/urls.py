# pyrefly: ignore [missing-import]
from django.urls import path
# pyrefly: ignore [missing-import]
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('',              views.index,           name='index'),
    path('dashboard/',    views.dashboard,        name='dashboard'),
    path('training/',     views.train_page_view,  name='train_page'),
    path('train/',        views.train_model,      name='train_model'),
    path('predict/',      views.predict_view,     name='predict'),
    path('history/',      views.history_view,     name='history'),
    path('about/',        views.about,            name='about'),
    path('api/dataset/',  views.dataset_info_api, name='dataset_info_api'),
    path('training/result/<int:id>/', views.training_result_view, name='training_result'),
    path('delete-model/<int:id>/', views.delete_model,     name='delete_model'),
    path('history/delete/<int:id>/', views.delete_history, name='delete_history'),
    
    path('manage-users/', views.manage_users_view, name='manage_users'),
    path('manage-users/delete/<int:id>/', views.delete_user, name='delete_user'),
    path('manage-users/toggle-admin/<int:id>/', views.toggle_admin, name='toggle_admin'),

    # Dataset Management
    path('dataset/', views.dataset_management_view, name='dataset_management'),
    path('dataset/upload/', views.upload_dataset_view, name='upload_dataset'),
    path('dataset/delete/', views.delete_dataset_view, name='delete_dataset'),

    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='heart_disease/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]
