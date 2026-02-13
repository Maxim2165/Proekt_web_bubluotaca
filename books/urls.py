# books/urls.py
from django.urls import path
from . import views
from .views.catalog_views import catalog, genre_list, book_detail, genre_detail, author_detail, author_list, search
from .views.interaction_views import favorite_toggle, download_book
app_name = 'books'

urlpatterns = [
    # /catalog/  -> список книг
    path('', views.catalog, name='catalog'),
    # /catalog/<pk>/ -> детальная страница книги
    path('<int:pk>/', book_detail, name='detail'),
    path('<int:pk>/download/<str:fmt>/', download_book, name='download'),
    # Toggle favorite
    path('<int:pk>/favorite/', favorite_toggle, name='favorite_toggle'),
    path('authors/', author_list, name='author_list'),
    path('authors/<slug:slug>/', author_detail, name='author_detail'),
    path('genres/<slug:slug>/', genre_detail, name='genre_detail'),
    path('genres/', genre_list, name='genre_list'),
    path('search/', search, name='search'),
]
