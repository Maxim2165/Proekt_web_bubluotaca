from django.urls import path
from .views import site_analytics
from analytics.views.user_analytics import profile_analytics
from . import views
app_name = 'analytics'

urlpatterns = [
    path('', site_analytics.dashboard, name='dashboard'),
    path('profile/analytics/', profile_analytics, name='profile_analytics'),
]
