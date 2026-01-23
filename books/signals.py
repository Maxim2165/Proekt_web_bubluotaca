# books/signals.py
import os
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Book

# Утилита: удалить файл в MEDIA_ROOT по относительному пути
def delete_file_if_exists(path):
    # Если путь пустой — ничего не делаем
    if not path:
        return
    # Собираем полный путь к файлу
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    # Если файл существует и это файл — удаляем
    if os.path.exists(full_path) and os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except Exception:
            # В dev-режиме можно логировать исключение; здесь делаем "тихое" удаление
            pass

@receiver(pre_save, sender=Book)
def delete_old_file_on_change(sender, instance, **kwargs):
    """
    При обновлении Book: если меняется один из file_* полей
    — удалить старый файл с диска.
    - triggered before save()
    """
    # Если создаём новый объект (нет PK) — нечего удалять
    if not instance.pk:
        return
    try:
        old = Book.objects.get(pk=instance.pk)
    except Book.DoesNotExist:
        return

    # Список полей с файлами, которые отслеживаем
    file_fields = ['file_pdf', 'file_epub', 'file_fb2', 'cover']
    for field in file_fields:
        old_file = getattr(old, field)
        new_file = getattr(instance, field)
        # Если старый файл есть и он отличается от нового — удаляем старый
        if old_file and old_file != new_file:
            delete_file_if_exists(old_file.name)

@receiver(post_delete, sender=Book)
def delete_files_on_delete(sender, instance, **kwargs):
    """
    При удалении Book удаляем все файлы, связанные с ним.
    - triggered after delete()
    """
    file_fields = ['file_pdf', 'file_epub', 'file_fb2', 'cover']
    for field in file_fields:
        f = getattr(instance, field)
        if f:
            delete_file_if_exists(f.name)
