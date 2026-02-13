from django.shortcuts import render
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta

from books.models import Book, Author, Genre, DownloadLog


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

    total_views = (
        Book.objects
        .filter(is_active=True)
        .aggregate(total=Sum('views_count'))
    )['total'] or 0

    total_downloads = DownloadLog.objects.count()

    # =========================
    # БЛОК 2. КНИГА НЕДЕЛИ (ТОЛЬКО ЗА 7 ДНЕЙ)
    # =========================

    books = Book.objects.filter(is_active=True).prefetch_related('authors')

    best_book = None
    best_score = -1
    best_book_stats = {}

    for book in books:
        weekly_downloads = DownloadLog.objects.filter(
            book=book,
            created_at__gte=week_ago
        ).count()

        if weekly_downloads == 0:
            continue

        views = book.views_count
        total_dl = book.downloads_count

        score = (
            weekly_downloads * 1.5 +
            views * 0.2 +
            total_dl * 0.1
        )

        if score > best_score:
            best_score = score
            best_book = book
            best_book_stats = {
                'weekly_downloads': weekly_downloads,
                'views': views,
                'total_downloads': total_dl,
                'score': round(score, 2),
            }

    # =========================
    # БЛОК 3. ТОП-5 КНИГ
    # =========================

    books_qs = (
        Book.objects
        .filter(is_active=True)
        .annotate(
            weekly_downloads_count=Count(
                'download_logs',
                filter=Q(download_logs__created_at__gte=week_ago),
                distinct=True
            )
        )
    )

    books_with_scores = []
    for book in books_qs:
        score = (
            book.weekly_downloads_count * 1.0 +
            book.downloads_count * 0.3 +
            book.views_count * 0.2
        )
        book.complex_score = score
        books_with_scores.append(book)

    top_books = sorted(
        books_with_scores,
        key=lambda x: x.complex_score,
        reverse=True
    )[:5]

    # Книга признанная читателями (топ-1 за всё время)
    best_book_overall = top_books[0] if top_books else None
    best_overall_stats = {}
    if best_book_overall:
        best_overall_stats = {
            'views': best_book_overall.views_count,
            'total_downloads': best_book_overall.downloads_count,
            'weekly_downloads': best_book_overall.weekly_downloads_count,
        }

    # =========================
    # БЛОК 4. ТОП-5 ЖАНРОВ
    # =========================

    genres_qs = (
        Genre.objects
        .annotate(
            total_downloads=Sum('books__downloads_count', filter=Q(books__is_active=True)),
            total_views=Sum('books__views_count', filter=Q(books__is_active=True)),
            books_count=Count('books', filter=Q(books__is_active=True), distinct=True),
            avg_downloads_per_book=Avg('books__downloads_count', filter=Q(books__is_active=True))
        )
        .filter(books_count__gt=0)
    )

    genres_with_scores = []
    for genre in genres_qs:
        td = genre.total_downloads or 0
        tv = genre.total_views or 0
        avg = genre.avg_downloads_per_book or 0

        genre.genre_score = (
            td * 0.5 +
            tv * 0.3 +
            avg * 0.2
        )

        genres_with_scores.append(genre)

    top_genres = sorted(
        genres_with_scores,
        key=lambda x: x.genre_score,
        reverse=True
    )[:5]

    context = {
        'total_books': total_books,
        'total_authors': total_authors,
        'total_views': total_views,
        'total_downloads': total_downloads,

        'book_of_week': best_book,
        'book_of_week_stats': best_book_stats,

        'top_books': top_books,
        'top_genres': top_genres,

        'best_book_overall': best_book_overall,
        'best_overall_stats': best_overall_stats,
    }

    return render(request, 'analytics/dashboard.html', context)
