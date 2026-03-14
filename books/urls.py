# books/urls.py
from django.urls import path
from . import views
from .views.catalog_views import catalog, genre_list, book_detail, genre_detail, author_detail, author_list, search
from .views.interaction_views import favorite_toggle, download_book
app_name = 'books'

urlpatterns = [
    # /catalog/  -> список книг
    path('', views.catalog, name='catalog'),

# Поиск — ДО детальной книги!
    path('search/', search, name='search'),

# Списки жанров и авторов — ДО детальной книги!
    path('genres/', genre_list, name='genre_list'),
    path('authors/', author_list, name='author_list'),

# Детали жанра и автора — ДО детальной книги!
    path('genres/<slug:slug>/', genre_detail, name='genre_detail'),
    path('authors/<slug:slug>/', author_detail, name='author_detail'),

    # /catalog/<pk>/ -> детальная страница книги
    path('<slug:slug>/', book_detail, name='detail'),
    # Скачивание и избранное
    path('<int:pk>/download/<str:fmt>/', download_book, name='download'),
    path('<int:pk>/favorite/', favorite_toggle, name='favorite_toggle'),
]
