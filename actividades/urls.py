from django.urls import path

from . import views

app_name = 'actividades'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inscribir/', views.inscribir, name='inscribir'),
]