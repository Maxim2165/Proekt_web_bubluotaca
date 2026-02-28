# books/admin.py
from django.contrib import admin
from .models import Genre, Author, Book, Favorite, DownloadLog, BookView


# -----------------------------------------
# Genre
# -----------------------------------------
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_filter = ('name',)

# -----------------------------------------
# Author
# -----------------------------------------
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name',)
    search_fields = ('name',)


# -----------------------------------------
# Book
# ИСПРАВЛЕНО:
# -----------------------------------------
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}

    list_display = (
        'title',
        'display_authors',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
        'genres',
        'authors',
    )

    search_fields = (
        'title',
        'title_search',
        'authors__name',
    )

    filter_horizontal = ('authors', 'genres')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('authors')  # ← Оптимизация

    def display_authors(self, obj):
        return ", ".join(a.name for a in obj.authors.all())
    display_authors.short_description = 'Authors'


# -----------------------------------------
# Favorite
# -----------------------------------------
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'book__title')
    list_filter = ('created_at', 'user')

# -----------------------------------------
# DownloadLog
# -----------------------------------------
@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'book',
        'file_format',
        'file_size',
        'status',
        'created_at',
    )
    search_fields = ('user__username', 'book__title')
    list_filter = ('file_format', 'status')


# -----------------------------------------
# BookView (НОВАЯ регистрация)
# -----------------------------------------
@admin.register(BookView)
class BookViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'book__title')
    list_filter = ('created_at', 'user')

