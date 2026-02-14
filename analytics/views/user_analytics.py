# analytics/user_analytics.py

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import render
import json

from books.models import Book, Favorite, DownloadLog, BookView

@login_required
def profile_analytics(request):
    user = request.user

    # ----------------------------
    # БАЗОВЫЕ ДАННЫЕ
    # ----------------------------
    downloads = DownloadLog.objects.filter(user=user, status='success')
    views = BookView.objects.filter(user=user)

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
        .values('file_format')
        .annotate(cnt=Count('id'))
    )

    formats_map = {'pdf': 0, 'epub': 0, 'fb2': 0}
    for item in format_qs:
        formats_map[item['file_format']] = item['cnt']


    # ==================================================
    # 📈 МОЯ ДИНАМИКА ЧТЕНИЯ (по месяцам)
    # ==================================================

    six_months_ago = now() - timedelta(days=180)

    reading_qs = (
        downloads
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(cnt=Count('id'))
        .order_by('month')
    )

    reading_months = [x['month'].strftime('%m.%Y') for x in reading_qs]
    reading_counts = [x['cnt'] for x in reading_qs]


    # ----------------------------
    # ТОП-5 ЖАНРОВ ПОЛЬЗОВАТЕЛЯ
    # ----------------------------
    favorite_genres = (
        downloads
        .values('book__genres__slug', 'book__genres__name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:5]
    )

    # ==================================================
    # 🎯 РЕКОМЕНДОВАННЫЕ КНИГИ
    # ==================================================
    favorite_genre_ids = downloads.values_list('book__genres__id', flat=True).distinct()
    downloaded_book_ids = downloads.values_list('book_id', flat=True).distinct()

    recommended_books = (
        Book.objects
            .filter(is_active=True, genres__in=favorite_genre_ids)
            .exclude(id__in=downloaded_book_ids)
            .annotate(
            total_downloads=Count('download_logs', distinct=True),
            total_views=Count('view_logs', distinct=True),
            genres_count=Count('genres', distinct=True)
        )
            .annotate(
            popularity_score=(
                    F('total_downloads') * 0.6 +
                    F('total_views') * 0.3 +
                    F('genres_count') * 0.1
            )
        )
            .order_by('-popularity_score')[:3]
    )

#любимый автор
    favorite_author = (
        downloads
            .values('book__authors__name', 'book__authors__slug')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
    )


    context = {
        'total_downloads': total_downloads,
        'favorites_count': favorites_count,
        'active_days': active_days,
        'favorite_genres': favorite_genres,
        'recommended_books': recommended_books,
        'favorite_author': favorite_author,
        'reading_months': json.dumps(reading_months),
        'reading_counts': json.dumps(reading_counts),
        'formats_map': formats_map,
    }

    return render(request, 'analytics/profile_analytics.html', context)