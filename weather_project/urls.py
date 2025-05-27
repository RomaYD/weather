from django.contrib import admin
from django.urls import path
from weather import views

urlpatterns = [
    path('', views.index, name='index'),
    path('get_weather/', views.get_weather, name='get_weather'),
    path('city-autocomplete/', views.city_autocomplete, name='city-autocomplete'),
]