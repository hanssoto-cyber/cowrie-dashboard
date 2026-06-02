from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('attacks/', views.attacks, name='attacks'),
    path('stats/', views.stats, name='stats'),
    path('api/stats/', views.api_stats, name='api_stats'),
]