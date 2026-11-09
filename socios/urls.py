from django.urls import path

from . import views

app_name = 'socios'

urlpatterns = [
    # Panel del socio
    path('panel/', views.panel_socio, name='panel'),

    # Panel admin (staff)
    path('admin/', views.dashboard, name='dashboard'),
    path('admin/checkin/', views.checkin_rapido, name='checkin_rapido'),
    path('admin/checkin/<int:pk>/', views.checkin_socio, name='checkin_socio'),
    path('admin/recepcion/', views.recepcion, name='recepcion'),
    path('admin/cuota/<int:pk>/marcar-pagada/', views.marcar_cuota_pagada, name='marcar_cuota_pagada'),
    path('admin/revision/<int:pk>/marcar-apto/', views.marcar_revision_apta, name='marcar_revision_apta'),
    path('admin/socios/', views.socio_lista, name='socio_lista'),
    path('admin/socios/nuevo/', views.socio_alta, name='socio_alta'),
    path('admin/socio/<int:pk>/', views.socio_detalle, name='socio_detalle'),
    path('admin/socio/<int:pk>/toggle-activo/', views.toggle_activo, name='toggle_activo'),
]