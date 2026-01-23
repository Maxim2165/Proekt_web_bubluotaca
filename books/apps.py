# books/apps.py
from django.apps import AppConfig

class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'

    def ready(self):
        # Импортируем модуль signals, чтобы декораторы @receiver
        # зарегистрировали обработчики при старте приложения.
        import books.signals  # noqa: F401
