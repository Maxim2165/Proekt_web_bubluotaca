# users/views.py
"""
Views для регистрации/входа/выхода и профиля.
Здесь:
- register: регистрация
- logout_view: выход
- profile: профиль пользователя
- profile_edit: редактирование профиля
- profile_analytics: аналитика пользователя
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
from django.db.models import Count, F
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from datetime import timedelta
import json

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


# ============================
# 🔥 АНАЛИТИКА ПОЛЬЗОВАТЕЛЯ
# ============================
@login_required
def profile_analytics(request):
    user = request.user

    # ----------------------------
    # БАЗОВЫЕ ДАННЫЕ
    # ----------------------------
    downloads = DownloadLog.objects.filter(user=user)

    total_downloads = downloads.count()
    favorites_count = Favorite.objects.filter(user=user).count()

    # 🔥 ДНИ АКТИВНОСТИ
    active_days = (
        downloads
            .values('created_at__date')
            .distinct()
            .count()
    )

    # ==================================================
    # 📚 ЛЮБИМЫЕ ФОРМАТЫ КНИГ (корректно)
    # ==================================================

    format_qs = (
        downloads
            .filter(status='success')
            .values('file_format')
            .annotate(cnt=Count('id'))
    )

    formats_map = {
        'pdf': 0,
        'epub': 0,
        'fb2': 0,
    }

    for item in format_qs:
        if item['file_format'] in formats_map:
            formats_map[item['file_format']] = item['cnt']

    # ==================================================
    # 📈 МОЯ ДИНАМИКА ЧТЕНИЯ (по месяцам)
    # ==================================================

    six_months_ago = now() - timedelta(days=180)

    reading_dynamics_qs = (
        downloads
            .filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(cnt=Count('id'))
            .order_by('month')
    )

    reading_months = []
    reading_counts = []

    for item in reading_dynamics_qs:
        reading_months.append(item['month'].strftime('%m.%Y'))
        reading_counts.append(item['cnt'])

    reading_months_json = json.dumps(reading_months)
    reading_counts_json = json.dumps(reading_counts)


    # ----------------------------
    # ТОП-5 ЖАНРОВ ПОЛЬЗОВАТЕЛЯ
    # ----------------------------
    favorite_genres = (
        downloads
            .filter(book__genres__isnull=False)
            .values(
            'book__genres__slug',
            'book__genres__name'
        )
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:5]
    )

    # ==================================================
    # 🎯 РЕКОМЕНДОВАННЫЕ КНИГИ
    # ==================================================

    # 1. Жанры, которые интересны пользователю
    favorite_genre_ids = (
        downloads
        .values_list('book__genres__id', flat=True)
        .distinct()
    )

    # 2. Книги, которые пользователь уже скачал
    downloaded_book_ids = (
        downloads
        .values_list('book_id', flat=True)
        .distinct()
    )

    # 3. Кандидаты на рекомендацию
    recommended_books = (
        Book.objects
            .filter(
            is_active=True,
            genres__in=favorite_genre_ids
        )
            .exclude(id__in=downloaded_book_ids)
            .annotate(
            popularity_score=(
                    Count('download_logs', distinct=True) * 0.6 +
                    F('views_count') * 0.3 +
                    Count('genres', distinct=True) * 0.1
            )
        )
            .order_by('-popularity_score')
            .distinct()[:3]
    )

    # ==================================================
    # Любимый автор
    # ==================================================
    favorite_author = (
        downloads
            .filter(book__authors__isnull=False)
            .values(
            'book__authors__name',
            'book__authors__slug'
        )
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
    )

    # ----------------------------
    # КОНТЕКСТ
    # ----------------------------
    context = {
        'total_downloads': total_downloads,
        'favorites_count': favorites_count,
        'active_days': active_days,
        'favorite_genres': favorite_genres,
        'recommended_books': recommended_books,
        'favorite_author': favorite_author,
        'reading_months': reading_months_json,
        'reading_counts': reading_counts_json,
        'formats_map': formats_map,
    }

    return render(request, 'users/profile_analytics.html', context)
