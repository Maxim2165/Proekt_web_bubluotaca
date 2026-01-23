# books/urls.py
from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # /catalog/  -> список книг
    path('', views.catalog, name='catalog'),
    # /catalog/<pk>/ -> детальная страница книги
    path('<int:pk>/', views.book_detail, name='detail'),
    path('<int:pk>/download/<str:fmt>/', views.download_book, name='download'),
    # Toggle favorite
    path('<int:pk>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('authors/', views.author_list, name='author_list'),
    path('authors/<slug:slug>/', views.author_detail, name='author_detail'),
    path('genres/<slug:slug>/', views.genre_detail, name='genre_detail'),
    path('genres/', views.genre_list, name='genre_list'),

]
