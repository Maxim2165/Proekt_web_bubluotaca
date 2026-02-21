# books/views/catalog_views.py
"""
Функции просмотра каталога: списки, детали, поиск
"""

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, F, Count
from django.db.models.functions import Lower
from ..models import Book, Author, Genre, Favorite, BookView
from django.utils import timezone
from datetime import timedelta

# ---------------------------------------
# catalog — список книг с поиском
# ---------------------------------------
def catalog(request):
    """
    Каталог книг с поиском, фильтрами и пагинацией
    """
    selected_genres = request.GET.getlist('genres')
    selected_authors = request.GET.getlist('authors')

    books = Book.objects.filter(is_active=True).prefetch_related('authors', 'genres').annotate(
        unique_downloads=Count('download_logs__user', distinct=True)
    )

    # ===== ФИЛЬТРАЦИЯ КНИГ =====
    if selected_genres:
        books = books.filter(genres__slug__in=selected_genres)

    if selected_authors:
        books = books.filter(authors__slug__in=selected_authors)

    books = books.distinct()

    # ===== ДОСТУПНЫЕ АВТОРЫ =====
    if selected_genres:
        available_authors = Author.objects.filter(
            books__genres__slug__in=selected_genres,
            books__is_active=True
        ).distinct()
    else:
        available_authors = Author.objects.all()

    # ===== ДОСТУПНЫЕ ЖАНРЫ =====
    if selected_authors:
        available_genres = Genre.objects.filter(
            books__authors__slug__in=selected_authors,
            books__is_active=True
        ).distinct()
    else:
        available_genres = Genre.objects.all()

    # ===== СОРТИРОВКА =====
    sort = request.GET.get('sort', 'title')
    if sort == 'new':
        books = books.order_by('-created_at')
    else:
        books = books.order_by('title')

    paginator = Paginator(books, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    selected_genre_objects = Genre.objects.filter(slug__in=selected_genres)
    selected_author_objects = Author.objects.filter(slug__in=selected_authors)

    context = {
        'page_obj': page_obj,
        'genres': Genre.objects.order_by('name'),
        'authors': Author.objects.order_by('name'),
        'selected_genres': selected_genres,
        'selected_authors': selected_authors,
        'selected_genre_objects': selected_genre_objects,
        'selected_author_objects': selected_author_objects,
        'available_genres': available_genres,
        'available_authors': available_authors,
        'sort': sort,
    }

    return render(request, 'books/catalog.html', context)

# ---------------------------------------
# genre_list — Список всех жанров
# ---------------------------------------
def genre_list(request):
    """
    Список всех жанров
    """
    genres = Genre.objects.all()

    return render(
        request,
        'books/genre_list.html',
        {'genres': genres}
    )

# ---------------------------------------
# book_detail — подробная карточка
# ---------------------------------------
def book_detail(request, pk):
    """
    Отображение карточки книги.
    Создаём запись в BookView.
    Добавляем флаг is_favorited.
    """

    book = get_object_or_404(
        Book.objects.prefetch_related('authors', 'genres'),
        pk=pk,
        is_active=True
    )

    # --- ЛОГИКА ПРОСМОТРА ---
    VIEW_TIMEOUT = timedelta(minutes=6)
    now = timezone.now()
    threshold = now - VIEW_TIMEOUT

    if request.user.is_authenticated:
        recent_view = BookView.objects.filter(
            user=request.user,
            book=book,
            created_at__gte=threshold
        ).exists()

        if not recent_view:
            BookView.objects.create(
                user=request.user,
                book=book
            )

    else:
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        recent_view = BookView.objects.filter(
            session_key=session_key,
            book=book,
            created_at__gte=threshold
        ).exists()

        if not recent_view:
            BookView.objects.create(
                session_key=session_key,
                book=book
            )

    # --- ФЛАГ ИЗБРАННОГО ---
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user,
            book=book
        ).exists()

    # --- ПОДСЧЁТ СТАТИСТИКИ ---
    view_count = book.view_logs.count()
    download_count = book.download_logs.filter(status='success').values('user').distinct().count()

    return render(request, 'books/detail.html', {
        'book': book,
        'is_favorited': is_favorited,
        'view_count': view_count,
        'download_count': download_count,
    })

# ---------------------------------------
# genre_detail — страница жанра
# ---------------------------------------
def genre_detail(request, slug):
    """
    Страница жанра:
    - информация о жанре
    - список книг данного жанра
    """
    genre = get_object_or_404(Genre, slug=slug)

    books = Book.objects.filter(
        genres=genre,
        is_active=True
    ).prefetch_related('authors', 'genres').distinct().annotate(
        unique_downloads=Count('download_logs__user', distinct=True)
    )

    context = {
        "genre": genre,
        "books": books,
    }

    return render(request, "books/genre_detail.html", context)

# ---------------------------------------
# author_detail — страница автора
# ---------------------------------------
def author_detail(request, slug):
    """
    Страница автора:
    - информация об авторе
    - список всех его книг
    """
    author = get_object_or_404(Author, slug=slug)
    books = author.books.filter(is_active=True).prefetch_related('authors', 'genres').annotate(
        unique_downloads=Count('download_logs__user', distinct=True)
    )

    context = {
        'author': author,
        'books': books,
    }

    return render(request, 'books/author_detail.html', context)

# ---------------------------------------
# author_list — Список всех авторов
# ---------------------------------------
def author_list(request):
    """
    Список всех авторов (алфавитный порядок)
    """
    authors = Author.objects.all().prefetch_related('books')

    return render(
        request,
        'books/author_list.html',
        {'authors': authors}
    )

# ---------------------------------------
# search — единый поиск
# ---------------------------------------
def search(request):
    """
    Единый поиск по сайту:
    - книги
    - авторы
    - жанры
    """
    query = request.GET.get('q', '').strip().lower()

    books = []
    authors = []
    genres = []

    if query:
        books = (
            Book.objects
                .filter(is_active=True)
                .filter(title_search__icontains=query)
                .prefetch_related('authors', 'genres')
                .distinct()
                .annotate(
                unique_downloads=Count('download_logs__user', distinct=True)
            )
        )

        authors = (
            Author.objects
            .filter(name_search__icontains=query)
            .distinct()
        )

        genres = (
            Genre.objects
            .filter(name_search__icontains=query)
            .distinct()
        )

    context = {
        'query': query,
        'books': books,
        'authors': authors,
        'genres': genres,
    }

    return render(request, 'books/search_results.html', context)