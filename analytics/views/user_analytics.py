# analytics/user_analytics.py

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q, Max, ExpressionWrapper, FloatField
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import render
import json
import math
from django.db.models import Value
from django.db.models.functions import Ln
from books.models import Book, Favorite, DownloadLog, BookView, Genre, Author
from django.db.models.functions import TruncDate
from datetime import date

@login_required
def profile_analytics(request):
    user = request.user

    # ----------------------------
    # БАЗОВЫЕ ДАННЫЕ
    # ----------------------------
    downloads = DownloadLog.objects.filter(user=user, status='success')
    views = BookView.objects.filter(user=user)

    total_downloads = downloads.values('book').distinct().count()
    favorites_count = Favorite.objects.filter(user=user).count()
    total_views = views.count()

    total_actions = total_downloads + favorites_count + total_views

    # 🔥 ДНИ АКТИВНОСТИ
    days = set()

    # 1. Дни просмотров
    days.update(
        BookView.objects.filter(user=user)
            .values_list(TruncDate('created_at'), flat=True)
    )

    # 2. Дни скачиваний (только успешные)
    days.update(
        DownloadLog.objects.filter(user=user, status='success')
            .values_list(TruncDate('created_at'), flat=True)
    )

    # 3. Дни добавления в избранное
    days.update(
        Favorite.objects.filter(user=user)
            .values_list(TruncDate('created_at'), flat=True)
    )
    active_days = len(days)

    # Любимый автор (по количеству скачиваний книг этого автора)
    favorite_author = (
        downloads
            .values('book__authors__name', 'book__authors__slug')
            .annotate(cnt=Count('book', distinct=True))  # Изменено: Count уникальных книг (book), а не логов (id)
            .order_by('-cnt')
            .first()
    )

    # ==================================================
    # 📚 ЛЮБИМЫЕ ФОРМАТЫ КНИГ (корректно)
    # ==================================================

    format_qs = (
        downloads
            .values('file_format')
            .annotate(cnt=Count('book', distinct=True))  # Изменено: Count уникальных книг (book) по формату
    )

    formats_map = {'pdf': 0, 'epub': 0, 'fb2': 0}
    for item in format_qs:
        formats_map[item['file_format']] = item['cnt']


    # ----------------------------
    # ТОП-5 ЖАНРОВ ПОЛЬЗОВАТЕЛЯ
    # ----------------------------
    user_genres = Genre.objects.annotate(
        user_downloads=Count('books__download_logs__book', filter=Q(books__download_logs__user=user), distinct=True),
        # Изменено: Count уникальных книг (book) для скачиваний
        user_views=Count('books__view_logs__book', filter=Q(books__view_logs__user=user), distinct=True),
        # Аналогично для просмотров
        user_favorites=Count('books__favorited_by__book', filter=Q(books__favorited_by__user=user), distinct=True),
        # Для избранного (Favorite уже unique, но distinct на всякий)
    ).annotate(
        score=F('user_views') * 1 + F('user_favorites') * 3 + F('user_downloads') * 6
    ).filter(score__gt=0).order_by('-score', '-user_downloads', '-user_favorites', '-user_views')[:5]

    favorite_genres = [{'name': g.name, 'slug': g.slug, 'cnt': g.score, 'views': g.user_views, 'downloads': g.user_downloads, 'favorites': g.user_favorites} for g in user_genres]  # Добавили views, downloads, favorites для шаблона


    # ==================================================
    # 🎯 РЕКОМЕНДОВАННЫЕ КНИГИ (НОВАЯ ЛОГИКА)
    # ==================================================
    # ----------------------------
    # Глобальная статистика
    # ----------------------------
    books_global = Book.objects.filter(is_active=True).annotate(
        total_downloads=Count(
            'download_logs__user',
            filter=Q(download_logs__status='success'),
            distinct=True
        ),
        total_views=Count('view_logs', distinct=True),
        total_favorites=Count('favorited_by', distinct=True),
    )

    max_views = books_global.aggregate(Max('total_views'))['total_views__max'] or 1
    max_downloads = books_global.aggregate(Max('total_downloads'))['total_downloads__max'] or 1
    max_favorites = books_global.aggregate(Max('total_favorites'))['total_favorites__max'] or 1


    # ----------------------------
    # Функция аннотации с нормализацией
    # ----------------------------
    def annotate_with_score(queryset):
        return queryset.annotate(
            views_norm=ExpressionWrapper(
                Ln(F('total_views') + 1) / Ln(max_views + 1),
                output_field=FloatField()
            ),
            downloads_norm=ExpressionWrapper(
                Ln(F('total_downloads') + 1) / Ln(max_downloads + 1),
                output_field=FloatField()
            ),
            favorites_norm=ExpressionWrapper(
                Ln(F('total_favorites') + 1) / Ln(max_favorites + 1),
                output_field=FloatField()
            ),
            unique_downloads=Count('download_logs__user', filter=Q(download_logs__status='success'), distinct=True),
        ).annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 +
                F('favorites_norm') * 3 +
                F('downloads_norm') * 6,
                output_field=FloatField()
            )
        ).order_by('-score')

    # ----------------------------
    # Исключаем уже скачанные книги
    # ----------------------------
    downloaded_book_ids = downloads.values_list('book_id', flat=True).distinct()
    # ==================================================
    # РЕЖИМ 1 — ХОЛОДНЫЙ СТАРТ
    # ==================================================

    if total_actions == 0:

        recommended_books = annotate_with_score(
            books_global
        )[:3]
    # ==================================================
    # РЕЖИМ 2 — МЯГКАЯ ПЕРСОНАЛИЗАЦИЯ
    # ==================================================
    elif total_actions < 8:
        top_user_genre = user_genres.first()

        personal_books = Book.objects.filter(
            is_active=True,
            genres=top_user_genre
        ).exclude(
            id__in=downloaded_book_ids
        ).annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        )

        personal_books = annotate_with_score(personal_books)[:2]

        global_books = annotate_with_score(
            books_global.exclude(id__in=downloaded_book_ids)
        )[:2]
        # объединяем без дубликатов
        recommended_books = list(personal_books)

        for book in global_books:
            if book not in recommended_books:
                recommended_books.append(book)

        recommended_books = recommended_books[:3]

    # ==================================================
    # РЕЖИМ 3 — ПОЛНАЯ ПЕРСОНАЛИЗАЦИЯ
    # ==================================================
    else:
        top_user_genres = user_genres[:2]

        recommended_books = Book.objects.filter(
            is_active=True,
            genres__in=top_user_genres
        ).distinct() \
            .exclude(
            id__in=downloaded_book_ids
        ).annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        )
        recommended_books = annotate_with_score(recommended_books)[:3]



    context = {
        'total_downloads': total_downloads,
        'favorites_count': favorites_count,
        'active_days': active_days,
        'favorite_genres': favorite_genres,
        'recommended_books': recommended_books,
        'favorite_author': favorite_author,
        'formats_map': formats_map,
    }

    return render(request, 'analytics/profile_analytics.html', context)