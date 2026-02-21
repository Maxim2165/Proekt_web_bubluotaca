# analytics/user_analytics.py

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Max, ExpressionWrapper, FloatField
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import render
import json

from books.models import Book, Favorite, DownloadLog, BookView, Genre, Author

@login_required
def profile_analytics(request):
    user = request.user

    # ----------------------------
    # БАЗОВЫЕ ДАННЫЕ
    # ----------------------------
    downloads = DownloadLog.objects.filter(user=user, status='success')
    views = BookView.objects.filter(user=user)

    total_downloads = downloads.count()  # сначала считаем
    favorites_count = Favorite.objects.filter(user=user).count()
    total_views = views.count()

    total_actions = total_downloads + favorites_count + total_views

    # 🔥 ДНИ АКТИВНОСТИ
    active_days = (
        downloads
            .values('created_at__date')
            .distinct()
            .count()
    )

    # Любимый автор (по количеству скачиваний книг этого автора)
    favorite_author = (
        downloads
            .values('book__authors__name', 'book__authors__slug')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
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
    user_genres = Genre.objects.annotate(
        user_downloads=Count('books__download_logs', filter=Q(books__download_logs__user=user), distinct=True),
        user_views=Count('books__view_logs', filter=Q(books__view_logs__user=user), distinct=True),
        user_favorites=Count('books__favorited_by', filter=Q(books__favorited_by__user=user), distinct=True),
    ).annotate(
        score=F('user_views') * 1 + F('user_favorites') * 2 + F('user_downloads') * 4
    ).filter(score__gt=0).order_by('-score')[:5]

    favorite_genres = [{'name': g.name, 'slug': g.slug, 'cnt': g.score} for g in user_genres]  # Для шаблона

    # ==================================================
    # 🎯 РЕКОМЕНДОВАННЫЕ КНИГИ
    # ==================================================
    # Глобальные максимумы (нужны для нормализации во всех случаях)
    books_global = Book.objects.filter(is_active=True).annotate(
        total_downloads=Count('download_logs__user', distinct=True),
        total_views=Count('view_logs', distinct=True),
        total_favorites=Count('favorited_by', distinct=True),
    ).filter(total_downloads__gte=3)

    max_views = books_global.aggregate(Max('total_views'))['total_views__max'] or 1
    max_downloads = books_global.aggregate(Max('total_downloads'))['total_downloads__max'] or 1
    max_favorites = books_global.aggregate(Max('total_favorites'))['total_favorites__max'] or 1

    if total_actions == 0:  # Cold start: глобальный ТОП
        recommended_books = books_global.annotate(
            views_norm=ExpressionWrapper(F('total_views') / max_views, output_field=FloatField()),
            downloads_norm=ExpressionWrapper(F('total_downloads') / max_downloads, output_field=FloatField()),
            favorites_norm=ExpressionWrapper(F('total_favorites') / max_favorites, output_field=FloatField()),
        ).annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 + F('favorites_norm') * 2 + F('downloads_norm') * 4,
                output_field=FloatField()
            )
        ).order_by('-score')[:3]

    elif total_downloads == 1:  # 1 скачанная: жанр этой + 1 глобальный топ-жанр
        downloaded_book = downloads.first().book
        user_genre_ids = list(downloaded_book.genres.values_list('id', flat=True))

        global_top_genre = Genre.objects.annotate(
            total_downloads=Count('books__download_logs__user', distinct=True),
            total_views=Count('books__view_logs', distinct=True),
            total_favorites=Count('books__favorited_by', distinct=True),
            books_count=Count('books', distinct=True)
        ).annotate(
            genre_score=ExpressionWrapper(
                (F('total_views') * 1.0 + F('total_favorites') * 2.0 + F('total_downloads') * 4.0) /
                (F('books_count') + 1),
                output_field=FloatField()
            )
        ).order_by('-genre_score').first()

        favorite_genre_ids = user_genre_ids[:]
        if global_top_genre:
            favorite_genre_ids.append(global_top_genre.id)

        downloaded_book_ids = downloads.values_list('book_id', flat=True).distinct()

        recommended_books = Book.objects.filter(
            is_active=True, genres__id__in=favorite_genre_ids
        ).exclude(
            id__in=downloaded_book_ids
        ).annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        ).annotate(
            views_norm=ExpressionWrapper(F('total_views') / max_views, output_field=FloatField()),
            downloads_norm=ExpressionWrapper(F('total_downloads') / max_downloads, output_field=FloatField()),
            favorites_norm=ExpressionWrapper(F('total_favorites') / max_favorites, output_field=FloatField()),
        ).annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 + F('favorites_norm') * 2 + F('downloads_norm') * 4,
                output_field=FloatField()
            )
        ).order_by('-score')[:3]

    else:  # Нормальный случай: топ-2 жанра пользователя
        top_user_genres = user_genres[:2]
        favorite_genre_ids = [g.id for g in top_user_genres]

        downloaded_book_ids = downloads.values_list('book_id', flat=True).distinct()

        recommended_books = Book.objects.filter(
            is_active=True, genres__id__in=favorite_genre_ids
        ).exclude(
            id__in=downloaded_book_ids
        ).annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        ).annotate(
            views_norm=ExpressionWrapper(F('total_views') / max_views, output_field=FloatField()),
            downloads_norm=ExpressionWrapper(F('total_downloads') / max_downloads, output_field=FloatField()),
            favorites_norm=ExpressionWrapper(F('total_favorites') / max_favorites, output_field=FloatField()),
        ).annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 + F('favorites_norm') * 2 + F('downloads_norm') * 4,
                output_field=FloatField()
            )
        ).order_by('-score')[:3]


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