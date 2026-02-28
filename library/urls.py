from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),         # главная, about
    path('auth/', include('users.urls')),    # логин/регистрация
    path('catalog/', include('books.urls')), # каталог/книга
    path('analytics/', include('analytics.urls')),


]

# чтобы отдавать media в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
