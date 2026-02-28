# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='users/login.html',
            redirect_authenticated_user=True  # ← Добавляем здесь
        ),
        name='login'
    ),

    path('logout/', views.logout_view, name='logout'),

    # Регистрация
    path('register/', views.register, name='register'),

    # Профиль и редактирование профиля
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
