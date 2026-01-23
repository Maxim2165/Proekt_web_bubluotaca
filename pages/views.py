# pages/views.py
from django.shortcuts import render
from books.models import Book


def home(request):
    """
    Главная страница сайта
    """

    # 🔹 Книги для фоновой анимации (рандом)
    background_books = (
        Book.objects
        .filter(is_active=True, cover__isnull=False)
        .order_by('?').distinct()[:15]
    )

    context = {
        'background_books': background_books,
    }

    return render(request, 'pages/home.html', context)


def about(request):
    return render(request, 'pages/about.html')

def terms(request):
    return render(request, 'pages/terms.html')

def privacy(request):
    return render(request, 'pages/privacy.html')
