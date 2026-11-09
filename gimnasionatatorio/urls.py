"""URLs principales del proyecto."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Corpo – Administración'
admin.site.site_title = 'Corpo – Administración'
admin.site.index_title = 'Gestión del gimnasio natatorio'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pagina.urls')),
    path('cuentas/', include('accounts.urls')),
    path('socios/', include('socios.urls')),
]