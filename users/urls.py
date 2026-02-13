# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # Встроенный LoginView рендерит наш шаблон и обрабатывает ?next=...
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),

    # Наш кастомный logout (принимает POST и читает hidden 'next')
    path('logout/', views.logout_view, name='logout'),

    # Регистрация
    path('register/', views.register, name='register'),

    # Профиль и редактирование профиля
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
