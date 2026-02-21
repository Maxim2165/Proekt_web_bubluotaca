from django.core.management.base import BaseCommand
from django.db.models import Count, Q, F, Max, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from books.models import Book, Author, Genre, DownloadLog, BookView, Favorite

class Command(BaseCommand):
    help = "Тестирует аналитические функции: выводит KPI, книгу недели, топ книг, читателей, жанры"

    def handle(self, *args, **options):
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        # KPI
        total_books = Book.objects.filter(is_active=True).count()
        total_authors = Author.objects.count()
        total_views = BookView.objects.count()
        total_downloads = DownloadLog.objects.filter(status='success').count()
        self.stdout.write(self.style.SUCCESS(f"KPI: Книг={total_books}, Авторов={total_authors}, Просмотров={total_views}, Скачиваний={total_downloads}"))

        # Книга недели
        weekly_books = (
            Book.objects.filter(is_active=True)
            .annotate(
                weekly_downloads=Count('download_logs', filter=Q(download_logs__created_at__gte=week_ago), distinct=True),
                weekly_views=Count('view_logs', filter=Q(view_logs__created_at__gte=week_ago), distinct=True),
                weekly_favorites=Count('favorited_by', filter=Q(favorited_by__created_at__gte=week_ago), distinct=True),
            )
            .annotate(score=F('weekly_views') * 1 + F('weekly_favorites') * 2 + F('weekly_downloads') * 4)
            .order_by('-score')
        )
        best_book = weekly_books.first()
        if best_book:
            self.stdout.write(self.style.SUCCESS(f"Книга недели: {best_book.title} (score={best_book.score}, views={best_book.weekly_views}, fav={best_book.weekly_favorites}, dl={best_book.weekly_downloads})"))
        else:
            self.stdout.write("Нет книги недели")

        # ТОП-5 книг
        books_with_counts = Book.objects.filter(is_active=True).annotate(
            total_downloads=Count('download_logs', distinct=True),
            total_views=Count('view_logs', distinct=True),
            total_favorites=Count('favorited_by', distinct=True),
        ).filter(total_downloads__gte=3)

        max_views = books_with_counts.aggregate(max_v=Max('total_views'))['max_v'] or 1
        max_downloads = books_with_counts.aggregate(max_d=Max('total_downloads'))['max_d'] or 1
        max_favorites = books_with_counts.aggregate(max_f=Max('total_favorites'))['max_f'] or 1

        top_books = books_with_counts.annotate(
            views_norm=F('total_views') / max_views,
            downloads_norm=F('total_downloads') / max_downloads,
            favorites_norm=F('total_favorites') / max_favorites,
        ).annotate(
            score=F('views_norm') * 1 + F('favorites_norm') * 2 + F('downloads_norm') * 4
        ).order_by('-score')[:5]

        self.stdout.write(self.style.SUCCESS("ТОП-5 книг:"))
        for i, book in enumerate(top_books, 1):
            self.stdout.write(f"{i}. {book.title} (score={book.score:.2f}, views={book.total_views}, fav={book.total_favorites}, dl={book.total_downloads})")

        # Книга читателей
        readers_choice = Book.objects.filter(is_active=True).annotate(
            total_favorites=Count('favorited_by', distinct=True)
        ).order_by('-total_favorites').first()
        if readers_choice:
            self.stdout.write(self.style.SUCCESS(f"Книга читателей: {readers_choice.title} (fav={readers_choice.total_favorites})"))
        else:
            self.stdout.write("Нет книги читателей")

        # ТОП-5 жанров
        top_genres = Genre.objects.annotate(
            total_downloads=Count('books__download_logs', distinct=True),
            total_views=Count('books__view_logs', distinct=True),
            total_favorites=Count('books__favorited_by', distinct=True),
            books_count=Count('books', distinct=True)
        ).annotate(
            genre_score=(F('total_views') * 1 + F('total_favorites') * 2 + F('total_downloads') * 4) / (F('books_count') + 1)
        ).order_by('-genre_score')[:5]

        self.stdout.write(self.style.SUCCESS("ТОП-5 жанров:"))
        for i, genre in enumerate(top_genres, 1):
            self.stdout.write(f"{i}. {genre.name} (score={genre.genre_score:.2f}, books={genre.books_count}, views={genre.total_views}, fav={genre.total_favorites}, dl={genre.total_downloads})")