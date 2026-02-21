import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from books.models import Book, DownloadLog, BookView, Favorite

class Command(BaseCommand):
    help = "Генерирует тестовые данные: скачивания, просмотры, избранные для случайных книг"

    def handle(self, *args, **options):
        # Берем пользователя (первый или создаем)
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='testuser', password='testpass')

        # Берем случайные 10 книг
        books = list(Book.objects.filter(is_active=True).order_by('?')[:10])
        if len(books) < 10:
            self.stdout.write(self.style.ERROR("Недостаточно книг в БД!"))
            return

        now = timezone.now()
        formats = ['pdf', 'epub', 'fb2']

        # Генерируем данные
        for i in range(15):  # 15 скачиваний
            book = random.choice(books)
            DownloadLog.objects.create(
                user=user,
                book=book,
                file_format=random.choice(formats),
                status='success',
                created_at=now - timedelta(days=random.randint(0, 30))
            )

        for i in range(20):  # 20 просмотров (больше, чтобы сбалансировано)
            book = random.choice(books)
            BookView.objects.create(
                user=user,
                book=book,
                created_at=now - timedelta(days=random.randint(0, 30))
            )

        for i in range(10):  # 10 избранных
            book = random.choice(books)
            Favorite.objects.get_or_create(  # Чтобы не дублировать
                user=user,
                book=book,
                defaults={'created_at': now - timedelta(days=random.randint(0, 30))}
            )

        self.stdout.write(self.style.SUCCESS(f"Сгенерировано: 15 скачиваний, 20 просмотров, 10 избранных для {len(books)} книг"))