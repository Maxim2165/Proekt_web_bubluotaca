# books/views.py
# -*- coding: utf-8 -*-
"""
Views для приложения books:
- catalog         : список книг с поиском и пагинацией
- book_detail     : страница книги (увеличение просмотров и флаг избранного)
- download_book   : скачивание файла книги с логированием (только для авторизованных)
- favorite_toggle : переключение избранного (добавить/удалить) (только POST)
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.db import transaction

from .models import Book, DownloadLog, Favorite, Author, Genre
from django.db.models.functions import Lower
from .models import Author
from django.utils import timezone
from datetime import timedelta


# ---------------------------------------
# Catalog view — список книг с поиском
# ---------------------------------------
def catalog(request):
    """
    Каталог книг с поиском, фильтрами и пагинацией
    """

    selected_genres = request.GET.getlist('genres')
    selected_authors = request.GET.getlist('authors')

    books = Book.objects.filter(is_active=True).prefetch_related('authors', 'genres')

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
# Book detail view — подробная карточка
# ---------------------------------------
def book_detail(request, pk):
    """
    Отображение карточки книги.
    Увеличиваем views_count атомарно (F()).
    Добавляем флаг is_favorited для текущего пользователя.
    """
    book = get_object_or_404(
        Book.objects.prefetch_related('authors', 'genres'),
        pk=pk,
        is_active=True
    )

    session_key = f'book_view_{book.pk}'
    last_view_time = request.session.get(session_key)

    now = timezone.now()
    VIEW_TIMEOUT = timedelta(minutes=10)

    if not last_view_time or now - timezone.datetime.fromisoformat(last_view_time) > VIEW_TIMEOUT:
        Book.objects.filter(pk=book.pk).update(
            views_count=F('views_count') + 1
        )
        request.session[session_key] = now.isoformat()
        book.refresh_from_db(fields=['views_count'])

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user,
            book=book
        ).exists()

    return render(request, 'books/detail.html', {
        'book': book,
        'is_favorited': is_favorited,
    })

# ---------------------------------------
# Download view — скачивание с логированием
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
    ).prefetch_related('authors', 'genres').distinct()

    context = {
        "genre": genre,
        "books": books,
    }

    return render(request, "books/genre_detail.html", context)

# ---------------------------------------
# Download view — скачивание с логированием
# ---------------------------------------
@login_required  # скачивание только для авторизованных
def download_book(request, pk, fmt):
    """
    Логика скачивания:
      - проверяем, что формат доступен для книги
      - создаём DownloadLog (в транзакции) и увеличиваем downloads_count атомарно
      - возвращаем FileResponse для скачивания
    fmt: 'pdf', 'epub', 'fb2'
    """
    # Поддерживаем GET (классический) или POST — но чаще оставляем GET для скачивания
    # Здесь примем GET — и всё равно защищаем @login_required и CSRF для POST-форм (если будет)
    book = get_object_or_404(Book, pk=pk, is_active=True)

    fmt = fmt.lower()
    if fmt == 'pdf' and book.file_pdf:
        file_field = book.file_pdf
    elif fmt == 'epub' and book.file_epub:
        file_field = book.file_epub
    elif fmt == 'fb2' and book.file_fb2:
        file_field = book.file_fb2
    else:
        # формат недоступен — 404
        raise Http404("Запрошенный формат недоступен для этой книги.")

    # Попробуем открыть и вернуть файл в транзакции вместе с логированием
    # Важно: создаём лог и обновляем счётчик в одной атомарной операции
    try:
        with transaction.atomic():
            # Создаём запись лога скачивания
            DownloadLog.objects.create(
                user=request.user,
                book=book,
                file_format=fmt,
                file_size=file_field.size if hasattr(file_field, 'size') else None,
                status='success'
            )
            # Атомарно увеличиваем downloads_count
            Book.objects.filter(pk=book.pk).update(downloads_count=F('downloads_count') + 1)

        # Отдаём файл клиенту
        return FileResponse(file_field.open('rb'), as_attachment=True, filename=file_field.name.split('/')[-1])
    except FileNotFoundError:
        # Если файл на диске отсутствует — возвращаем 404
        raise Http404("Файл не найден.")


# ---------------------------------------
# favorite_toggle: добавляем/удаляем избранное (POST)
# ---------------------------------------
@login_required
def favorite_toggle(request, pk):
    """
    Переключает состояние избранного для текущего пользователя и книги pk.
    Принимает только POST-запросы.
    После переключения редиректит на 'next' (если передан) или на detail книги.
    """
    # Принимаем только POST (форма в шаблоне должна использовать POST)
    if request.method != 'POST':
        return HttpResponseForbidden("Только POST-запросы разрешены.")

    # Получаем книгу или 404
    book = get_object_or_404(Book, pk=pk, is_active=True)

    # Создаём объект Favorite, если его не было; если был — удаляем (toggle)
    fav, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if not created:
        # Уже был — удаляем
        fav.delete()
    # подготовим редирект — возвращаем на next если указан
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('books:detail', pk=book.pk)

def author_detail(request, slug):
    """
    Страница автора:
    - информация об авторе
    - список всех его книг
    """
    author = get_object_or_404(Author, slug=slug)
    books = author.books.filter(is_active=True).prefetch_related('authors', 'genres')

    context = {
        'author': author,
        'books': books,
    }
    return render(request, 'books/author_detail.html', context)

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


def search(request):
    """
    Единый поиск по сайту:
    - книги
    - авторы
    - жанры

    Поиск регистронезависимый.
    Используются подготовленные *_search поля.
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

