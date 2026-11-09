"""Admin de Django para Socios, Cuotas, Revisiones y Asistencias."""
from django.contrib import admin

from .models import Asistencia, Cuota, RevisionMedica, Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'dni', 'telefono', 'plan', 'dias_por_semana', 'activo', 'fecha_alta')
    list_filter = ('activo', 'plan')
    search_fields = ('dni', 'user__username', 'user__first_name', 'user__last_name')
    list_editable = ('activo',)


@admin.action(description='Marcar cuotas seleccionadas como pagadas')
def _marcar_pagadas(modeladmin, request, queryset):
    for cuota in queryset.filter(pagada=False):
        cuota.marcar_pagada()


@admin.register(Cuota)
class CuotaAdmin(admin.ModelAdmin):
    list_display = ('socio', 'anio', 'mes', 'pagada', 'fecha_pago')
    list_filter = ('anio', 'mes', 'pagada')  # Ej.: cuotas impagas de un mes dado
    search_fields = ('socio__dni', 'socio__user__first_name', 'socio__user__last_name')
    actions = [_marcar_pagadas]


@admin.action(description='Marcar revisiones seleccionadas como aptas')
def _marcar_aptas(modeladmin, request, queryset):
    for revision in queryset.filter(apto=False):
        revision.marcar_apto()


@admin.register(RevisionMedica)
class RevisionMedicaAdmin(admin.ModelAdmin):
    list_display = ('socio', 'anio', 'mes', 'apto', 'fecha_revision')
    list_filter = ('anio', 'mes', 'apto')  # Ej.: revisiones pendientes de un mes dado
    search_fields = ('socio__dni', 'socio__user__first_name', 'socio__user__last_name')
    actions = [_marcar_aptas]


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('socio', 'fecha_hora')
    list_filter = ('socio',)
    date_hierarchy = 'fecha_hora'  # Navegación por fecha
    search_fields = ('socio__dni', 'socio__user__first_name', 'socio__user__last_name')