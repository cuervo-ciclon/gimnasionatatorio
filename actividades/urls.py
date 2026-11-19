from django.urls import path

from . import views

app_name = 'actividades'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('inscribir/', views.inscribir, name='inscribir'),
    path("recuperos/<int:recupero_id>/asignar/", views.asignar_recupero, name="asignar_recupero"),
]