# books/views/interaction_views.py
"""
Функции взаимодействия пользователя: избранное, скачивание
"""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, HttpResponseForbidden, FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.db.models import F
from ..models import Book, Favorite, DownloadLog
from django.utils import timezone



@login_required
def favorite_toggle(request, pk):
    """
    Переключает состояние избранного для текущего пользователя и книги pk.
    Принимает только POST-запросы.
    После переключения редиректит на 'next' (если передан) или на detail книги.
    """
    if request.method != 'POST':
        return HttpResponseForbidden("Только POST-запросы разрешены.")

    book = get_object_or_404(Book, pk=pk, is_active=True)

    fav, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if not created:
        fav.delete()

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('books:detail', pk=book.pk)

@login_required
def download_book(request, pk, fmt):
    """
    Логика скачивания:
      - проверяем формат
      - создаём DownloadLog
      - возвращаем FileResponse
    """

    book = get_object_or_404(Book, pk=pk, is_active=True)

    fmt = fmt.lower()
    if fmt == 'pdf' and book.file_pdf:
        file_field = book.file_pdf
    elif fmt == 'epub' and book.file_epub:
        file_field = book.file_epub
    elif fmt == 'fb2' and book.file_fb2:
        file_field = book.file_fb2
    else:
        raise Http404("Запрошенный формат недоступен для этой книги.")

    try:
        with transaction.atomic():
            DownloadLog.objects.create(
                user=request.user,
                book=book,
                file_format=fmt,
                file_size=file_field.size if hasattr(file_field, 'size') else None,
                status='success'
            )

        return FileResponse(
            file_field.open('rb'),
            as_attachment=True,
            filename=file_field.name.split('/')[-1]
        )

    except FileNotFoundError:
        raise Http404("Файл не найден.")