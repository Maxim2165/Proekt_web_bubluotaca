from django.shortcuts import render
from django.db.models import Count, Q, F, Max, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta

from books.models import Book, Author, Genre, DownloadLog, BookView, Favorite


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
    total_downloads = DownloadLog.objects.filter(status='success').values('user').distinct().count()

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
            .order_by('-score')
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
            total_views=Count('view_logs', distinct=True),  # ← добавили
            total_downloads=Count('download_logs__user', distinct=True),
        )
            .order_by('-total_favorites', '-created_at')
    )

    first = readers_choice_qs.first()
    readers_choice = first if first and first.total_favorites > 0 else None

    # =========================
    # БЛОК 3. ОБЩИЙ ТОП-5 КНИГ (С НОРМАЛИЗАЦИЕЙ)
    # =========================

    books_with_counts = (
        Book.objects
            .filter(is_active=True)
            .annotate(
            total_downloads=Count('download_logs__user', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),  # Новый: общее избранное
        )
    )

    # Минимальный порог (как в плане: минимум 3 скачивания)
    books_with_counts = books_with_counts.filter(total_downloads__gte=3)

    # Получаем максимумы для нормализации (добавили max_favs)
    max_views = books_with_counts.aggregate(
        max_v=Max('total_views')
    )['max_v'] or 1

    max_downloads = books_with_counts.aggregate(
        max_d=Max('total_downloads')
    )['max_d'] or 1

    max_favorites = books_with_counts.aggregate(  # Новый: max для favorites
        max_f=Max('total_favorites')
    )['max_f'] or 1

    # Нормализованный score (добавили favs_norm * 2)
    top_books = (
        books_with_counts
            .annotate(
            views_norm=ExpressionWrapper(
                F('total_views') / max_views,
                output_field=FloatField()
            ),
            downloads_norm=ExpressionWrapper(
                F('total_downloads') / max_downloads,
                output_field=FloatField()
            ),
            favorites_norm=ExpressionWrapper(  # Новый: нормализация favorites
                F('total_favorites') / max_favorites,
                output_field=FloatField()
            ),
        )
            .annotate(
            score=ExpressionWrapper(
                F('views_norm') * 1 +  # Вес 1
                F('favorites_norm') * 2 +  # Вес 2 (новый)
                F('downloads_norm') * 4,  # Вес 4
                output_field=FloatField()
            )
        )
            .order_by('-score')[:5]
    )

    best_book_overall = top_books[0] if top_books else None
    # =========================
    # БЛОК 4. ТОП-5 ЖАНРОВ (СРЕДНИЙ SCORE КНИГ)
    # =========================

    top_genres = (
        Genre.objects
            .annotate(
            total_downloads=Count('books__download_logs__user', distinct=True),
            total_views=Count('books__view_logs', distinct=True),
            total_favorites=Count('books__favorited_by', distinct=True),  # Новый: избранное по книгам жанра
            books_count=Count('books', distinct=True)
        )
            .annotate(
            genre_score=ExpressionWrapper(
                (F('total_views') * 1 +  # Вес 1
                 F('total_favorites') * 2 +  # Вес 2 (новый)
                 F('total_downloads') * 4) /  # Вес 4
                (F('books_count') + 1),  # +1 чтобы избежать деления на 0; средний по плану
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