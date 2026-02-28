# books/models.py
from django.db import models
from django.contrib.auth import get_user_model

# Получаем модель пользователя (обычно auth.User)
User = get_user_model()

# -----------------------------------------
# Genre — жанр книги (Фантастика, Роман и т.д.)
# -----------------------------------------
class Genre(models.Model):
    name = models.CharField(max_length=120, unique=True)
    name_search = models.CharField(max_length=120, db_index=True)

    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name_search = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -----------------------------------------
# Author — автор книги (отдельная сущность)
# -----------------------------------------
class Author(models.Model):
    name = models.CharField(max_length=255)
    name_search = models.CharField(max_length=255, db_index=True)

    slug = models.SlugField(max_length=255, unique=True)
    bio = models.TextField(blank=True)

    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    death_date = models.DateField(null=True, blank=True, verbose_name="Дата смерти")

    photo = models.ImageField(upload_to='authors/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name_search = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -----------------------------------------
# Book — основная модель книги
# ИЗМЕНЕНО
# -----------------------------------------
class Book(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    title_search = models.CharField(max_length=255, db_index=True)

    slug = models.SlugField(max_length=255, unique=True)

    description = models.TextField(blank=True)

    authors = models.ManyToManyField(
        Author,
        related_name='books',
        blank=True
    )

    genres = models.ManyToManyField(
        Genre,
        related_name='books',
        blank=True
    )

    cover = models.ImageField(upload_to='covers/', null=True, blank=True)

    file_pdf = models.FileField(upload_to='books/pdf/', null=True, blank=True)
    file_epub = models.FileField(upload_to='books/epub/', null=True, blank=True)
    file_fb2 = models.FileField(upload_to='books/fb2/', null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title_search']),
        ]

    def save(self, *args, **kwargs):
        self.title_search = self.title.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# -----------------------------------------
# Favorite — избранное: какая книга у какого пользователя
# ИЗМЕНЕНО
# -----------------------------------------
class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'book'])]
    def __str__(self):
        return f'{self.user} → {self.book}'


# -----------------------------------------
# DownloadLog — запись о скачивании (лог)
# -----------------------------------------
class DownloadLog(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('epub', 'EPUB'),
        ('fb2', 'FB2'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='download_logs'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='download_logs'
    )
    file_format = models.CharField(
        max_length=8,
        choices=FORMAT_CHOICES
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='success'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['book', 'created_at']),
        ]
    def __str__(self):
        return f'{self.user} → {self.book} ({self.file_format})'

# -----------------------------------------
# BookView — НОВАЯ таблица
# Журнал просмотров книги
# -----------------------------------------
class BookView(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='book_views'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='view_logs'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['book', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_key', 'created_at'])
        ]
    def __str__(self):
        if self.user:
            return f'View: {self.user} → {self.book}'
        return f'View: Anonymous({self.session_key}) → {self.book}'