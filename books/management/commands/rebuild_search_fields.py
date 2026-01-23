from django.core.management.base import BaseCommand
from books.models import Book, Author, Genre


class Command(BaseCommand):
    help = "Пересобирает search-поля (title_search, name_search) для книг, авторов и жанров"

    def handle(self, *args, **options):
        self.stdout.write("🔄 Обновление search-полей...")

        # -------- BOOKS --------
        books_updated = 0
        for book in Book.objects.all():
            book.title_search = book.title.lower().strip()
            book.save(update_fields=["title_search"])
            books_updated += 1

        # -------- AUTHORS --------
        authors_updated = 0
        for author in Author.objects.all():
            author.name_search = author.name.lower().strip()
            author.save(update_fields=["name_search"])
            authors_updated += 1

        # -------- GENRES --------
        genres_updated = 0
        for genre in Genre.objects.all():
            genre.name_search = genre.name.lower().strip()
            genre.save(update_fields=["name_search"])
            genres_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Готово:\n"
            f"   Книг обновлено: {books_updated}\n"
            f"   Авторов обновлено: {authors_updated}\n"
            f"   Жанров обновлено: {genres_updated}"
        ))
