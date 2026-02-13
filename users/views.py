# users/site_analytics.py
"""
Views для регистрации/входа/выхода и профиля.
Здесь:
- register: регистрация
- logout_view: выход
- profile: профиль пользователя
- profile_edit: редактирование профиля
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.conf import settings
from django.db.models import Count

from books.models import Book, Favorite, DownloadLog
from .forms import CustomUserCreationForm, UserUpdateForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Регистрация прошла успешно. Пожалуйста, войдите в систему.')
            return redirect('users:login')
        else:
            messages.error(request, 'Пожалуйста исправьте ошибки в форме регистрации.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})


def logout_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    next_url = request.POST.get('next') or settings.LOGOUT_REDIRECT_URL
    auth_logout(request)
    return redirect(next_url)


@login_required
def profile(request):
    """
    Профиль пользователя:
    - избранное
    - последние скачивания
    """
    user = request.user

    favorites_qs = (
        Favorite.objects
        .filter(user=user)
        .select_related('book')
        .order_by('-created_at')
    )
    favorite_books = [f.book for f in favorites_qs]

    downloads_qs = (
        DownloadLog.objects
        .filter(user=user)
        .select_related('book')
        .order_by('-created_at')[:10]
    )

    context = {
        'user': user,
        'favorite_books': favorite_books,
        'downloads': downloads_qs,
    }
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные профиля успешно обновлены.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Пожалуйста исправьте ошибки в форме.')
    else:
        form = UserUpdateForm(instance=request.user)
    return render(request, 'users/profile_edit.html', {'form': form})


