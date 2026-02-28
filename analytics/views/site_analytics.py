from django.shortcuts import render
from django.db.models import Count, Q, F, Max, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import Cast, Log
from books.models import Book, Author, Genre, DownloadLog, BookView, Favorite
import math
from django.db.models import Value
from django.db.models.functions import Ln, Sqrt
def dashboard(request):
    """
    Страница аналитики сайта (Обзор)
    """

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    # =========================
    # БЛОК 1. KPI
    # =========================

    total_books = Book.objects.filter(is_active=True).count()
    total_authors = Author.objects.count()

    total_views = BookView.objects.count()
    total_downloads = DownloadLog.objects.filter(status='success').values('user', 'book').distinct().count()  # Суммируем уникальные пары (пользователь + книга)
    # =========================
    # БЛОК 2. КНИГА НЕДЕЛИ (ТОЛЬКО ЗА 7 ДНЕЙ)
    # =========================

    weekly_books = (
        Book.objects
            .filter(is_active=True)
            .annotate(
            weekly_downloads=Count(
                'download_logs__user',
                filter=Q(download_logs__created_at__gte=week_ago),
                distinct=True
            ),
            weekly_views=Count(
                'view_logs',
                filter=Q(view_logs__created_at__gte=week_ago),
                distinct=True
            ),
            weekly_favorites=Count(  # Новый: подсчёт избранного за неделю
                'favorited_by',
                filter=Q(favorited_by__created_at__gte=week_ago),
                distinct=True
            ),
        )
            .annotate(
            total_downloads=Count('download_logs__user', distinct=True)
        )
            .annotate(
            score=F('weekly_views') * 1 +  # Вес 1 для просмотров
                  F('weekly_favorites') * 2 +  # Вес 2 для избранного (новый)
                  F('weekly_downloads') * 4  # Вес 4 для скачиваний
        )
            .order_by('-score', '-weekly_downloads')
    )

    best_book = weekly_books.first()

    # =========================
    # НОВЫЙ БЛОК: КНИГА, ВЫБРАННАЯ ЧИТАТЕЛЯМИ (по общему числу избранного)
    # =========================
    readers_choice_qs = (
        Book.objects
            .filter(is_active=True)
            .annotate(
            total_favorites=Count('favorited_by', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_downloads=Count('download_logs__user', distinct=True),
        )
        .filter(total_favorites__gte=2)
            .order_by('-total_favorites', '-created_at')
    )

    first = readers_choice_qs.first()
    readers_choice = first if first and first.total_favorites > 0 else None

    # =========================
    # БЛОК 3. ОБЩИЙ ТОП-5 КНИГ (С НОРМАЛИЗАЦИЕЙ)
    # =========================

    books_all = (
        Book.objects
            .filter(is_active=True)
            .annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        )
    )

    # Сначала считаем max по ВСЕМ книгам
    max_views = books_all.aggregate(Max('total_views'))['total_views__max'] or 1
    max_downloads = books_all.aggregate(Max('total_downloads'))['total_downloads__max'] or 1
    max_favorites = books_all.aggregate(Max('total_favorites'))['total_favorites__max'] or 1

    # Теперь фильтр
    books_filtered = books_all.filter(total_downloads__gte=3)

    # Нормализованный score
    top_books = (
        books_filtered
            .annotate(
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
        )
            .annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 +
                F('favorites_norm') * 2 +
                F('downloads_norm') * 4,
                output_field=FloatField()
            )
        )
            .order_by('-score')[:5]
    )

    best_book_overall = top_books[0] if top_books else None
    # =========================
    # БЛОК 4. ТОП-5 ЖАНРОВ (СРЕДНИЙ SCORE КНИГ)
    # =========================

    genres_all = (
        Genre.objects
            .annotate(
            total_downloads=Count('books__download_logs__user', distinct=True),
            total_views=Count('books__view_logs', distinct=True),
            total_favorites=Count('books__favorited_by', distinct=True),
            books_count=Count('books', distinct=True)  # Возвращаем books_count
        )
    )

    max_g_views = genres_all.aggregate(Max('total_views'))['total_views__max'] or 1
    max_g_downloads = genres_all.aggregate(Max('total_downloads'))['total_downloads__max'] or 1
    max_g_favorites = genres_all.aggregate(Max('total_favorites'))['total_favorites__max'] or 1

    top_genres = (
        genres_all
            .annotate(
            views_norm=ExpressionWrapper(
                Ln(F('total_views') + 1) / Ln(max_g_views + 1),
                output_field=FloatField()
            ),
            downloads_norm=ExpressionWrapper(
                Ln(F('total_downloads') + 1) / Ln(max_g_downloads + 1),
                output_field=FloatField()
            ),
            favorites_norm=ExpressionWrapper(
                Ln(F('total_favorites') + 1) / Ln(max_g_favorites + 1),
                output_field=FloatField()
            ),
        )
            .annotate(
            genre_score=ExpressionWrapper(
                (F('views_norm') * 1 +
                 F('favorites_norm') * 2 +
                 F('downloads_norm') * 4)
                / Sqrt(Cast(F('books_count'), FloatField())),
                output_field=FloatField()
            )
        )
            .order_by('-genre_score')[:5]
    )

    context = {
        'total_books': total_books,
        'total_authors': total_authors,
        'total_views': total_views,
        'total_downloads': total_downloads,
        'book_of_week': best_book,
        'top_books': top_books,
        'best_book_overall': best_book_overall,
        'top_genres': top_genres,
        'readers_choice': readers_choice,
    }

    return render(request, 'analytics/dashboard.html', context)