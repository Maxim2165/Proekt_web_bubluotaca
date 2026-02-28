from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Max, FloatField, ExpressionWrapper, Q
from django.contrib.auth.models import User
from books.models import Book, Genre, DownloadLog, BookView, Favorite

class Command(BaseCommand):
    help = "Тестирует топ-5 книг: добавляет тестовые данные и выводит расчёт"

    def handle(self, *args, **options):
        self.stdout.write("Добавляем/обновляем тестовые данные...")

        # Пользователи — 10 штук для большего max
        users = []
        for i in range(1, 11):
            user, _ = User.objects.get_or_create(username=f'testuser{i}')
            users.append(user)

        # Жанр
        genre, _ = Genre.objects.get_or_create(name='Тестовый жанр')

        # Книги
        books_data = [
            {'title': 'Test Book 1', 'slug': 'test-book-1'},
            {'title': 'Test Book 2', 'slug': 'test-book-2'},
            {'title': 'Test Book 3', 'slug': 'test-book-3'},
            {'title': 'Test Book 4', 'slug': 'test-book-4'},
        ]
        books = []
        for data in books_data:
            book, _ = Book.objects.get_or_create(slug=data['slug'], defaults={'title': data['title'], 'is_active': True})
            book.genres.add(genre)
            books.append(book)

        book1, book2, book3, book4 = books

        # Очистка
        BookView.objects.filter(book__in=books).delete()
        DownloadLog.objects.filter(book__in=books).delete()
        Favorite.objects.filter(book__in=books).delete()

        now = timezone.now()
        one_week_ago = now - timedelta(days=3)

        # Book1: много views, средние dl/fav
        for i in range(10):
            BookView.objects.create(user=users[i % 10], book=book1, created_at=one_week_ago + timedelta(hours=i))
        for i in range(5):
            DownloadLog.objects.create(user=users[i], book=book1, file_format='pdf', status='success', created_at=one_week_ago + timedelta(hours=i))
        for i in range(3):
            Favorite.objects.get_or_create(user=users[i], book=book1, defaults={'created_at': one_week_ago + timedelta(hours=i)})

        # Book2: много fav и views
        for i in range(20):
            BookView.objects.create(user=users[i % 10], book=book2, created_at=one_week_ago + timedelta(hours=i))
        for i in range(4):
            DownloadLog.objects.create(user=users[i], book=book2, file_format='pdf', status='success', created_at=one_week_ago + timedelta(hours=i))
        for i in range(10):
            Favorite.objects.get_or_create(user=users[i % 10], book=book2, defaults={'created_at': one_week_ago + timedelta(hours=i)})

        # Book3: мало dl
        for i in range(5):
            BookView.objects.create(user=users[i % 5], book=book3, created_at=one_week_ago + timedelta(hours=i))
        for i in range(2):
            DownloadLog.objects.create(user=users[i], book=book3, file_format='pdf', status='success', created_at=one_week_ago + timedelta(hours=i))

        # Book4: много dl
        for i in range(15):
            BookView.objects.create(user=users[i % 10], book=book4, created_at=one_week_ago + timedelta(hours=i))
        for i in range(8):
            DownloadLog.objects.create(user=users[i % 10], book=book4, file_format='pdf', status='success', created_at=one_week_ago + timedelta(hours=i))
        for i in range(4):
            Favorite.objects.get_or_create(user=users[i], book=book4, defaults={'created_at': one_week_ago + timedelta(hours=i)})

        self.stdout.write(self.style.SUCCESS("Данные добавлены. Расчёт топ-5 книг..."))

        # Расчёт (как в твоём views)
        books_with_counts = (
            Book.objects
                .filter(is_active=True)
                .annotate(
                total_downloads=Count('download_logs__user', distinct=True),
                total_views=Count('view_logs__user', distinct=True),  # Исправлено: уникальные пользователи для views
                total_favorites=Count('favorited_by', distinct=True),
            )
        )

        books_with_counts = books_with_counts.filter(total_downloads__gte=3)

        max_views = books_with_counts.aggregate(max_v=Max('total_views'))['max_v'] or 1
        max_downloads = books_with_counts.aggregate(max_d=Max('total_downloads'))['max_d'] or 1
        max_favorites = books_with_counts.aggregate(max_f=Max('total_favorites'))['max_f'] or 1

        top_books = (
            books_with_counts
                .annotate(
                views_norm=ExpressionWrapper(F('total_views') / max_views, output_field=FloatField()),
                downloads_norm=ExpressionWrapper(F('total_downloads') / max_downloads, output_field=FloatField()),
                favorites_norm=ExpressionWrapper(F('total_favorites') / max_favorites, output_field=FloatField()),
            )
                .annotate(
                score=ExpressionWrapper(
                    F('views_norm') * 1 + F('favorites_norm') * 2 + F('downloads_norm') * 4,
                    output_field=FloatField()
                )
            )
                .order_by('-score')[:5]
        )

        # Вывод
        self.stdout.write(f"Max: views={max_views}, dl={max_downloads}, fav={max_favorites}")
        for book in top_books:
            self.stdout.write(f"{book.title} score={book.score:.2f} views_norm={book.views_norm:.2f} dl_norm={book.downloads_norm:.2f} fav_norm={book.favorites_norm:.2f}")