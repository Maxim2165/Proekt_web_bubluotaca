# books/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from books.models import Book, Author
from books.models import Genre
User = get_user_model()


class PublicPagesTest(TestCase):
    """
    Базовые smoke-тесты:
    проверяем, что ключевые страницы открываются
    """

    def setUp(self):
        # Создаём автора
        self.author = Author.objects.create(
            name="Тестовый Автор",
            slug="test-author"
        )

        # Создаём книгу
        self.book = Book.objects.create(
            title="Тестовая книга",
            description="Описание книги",
            is_active=True
        )
        self.book.authors.add(self.author)

    def test_catalog_page_opens(self):
        """Каталог открывается"""
        url = reverse("books:catalog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_book_detail_page_opens(self):
        """Страница книги открывается"""
        url = reverse("books:detail", args=[self.book.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_home_page_opens(self):
        """Главная страница открывается"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

class ExtraPagesTest(TestCase):
    """
    Дополнительные проверки страниц
    """

    def test_404_page(self):
        """Несуществующая страница возвращает 404"""
        response = self.client.get("/page-not-exists/")
        self.assertEqual(response.status_code, 404)




class GenrePagesTest(TestCase):
    """
    Проверяем страницы жанров:
    - список всех жанров
    - детальная страница жанра
    """

    def setUp(self):
        # Создаём жанр
        self.genre = Genre.objects.create(name="Фантастика", slug="fantastika")
        # Создаём книгу
        self.book = Book.objects.create(title="Книга жанра", description="Описание", is_active=True)
        self.book.genres.add(self.genre)

    def test_genre_list_page_opens(self):
        """Список всех жанров открывается"""
        url = reverse("books:genre_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Фантастика")

    def test_genre_detail_page_opens(self):
        """Детальная страница жанра открывается и показывает книги"""
        url = reverse("books:genre_detail", args=[self.genre.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)
