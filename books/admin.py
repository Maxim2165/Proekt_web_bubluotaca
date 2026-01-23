# books/admin.py
from django.contrib import admin
from .models import Genre, Author, Book, Favorite, DownloadLog

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_authors', 'published_date', 'downloads_count', 'is_active')
    list_filter = ('is_active', 'genres')
    search_fields = ('title', 'isbn', 'authors__name')
    filter_horizontal = ('authors', 'genres')  # удобный вид в админке для M2M
    readonly_fields = ('downloads_count', 'views_count')

    def display_authors(self, obj):
        return ", ".join(a.name for a in obj.authors.all())
    display_authors.short_description = 'Authors'

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    search_fields = ('user__username', 'book__title')

@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'file_format', 'file_size', 'status', 'created_at')
    search_fields = ('user__username', 'book__title')
    list_filter = ('file_format', 'status')
