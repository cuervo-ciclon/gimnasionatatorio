import datetime

from django.contrib import admin
from django.utils.html import format_html

from .models import Actividad, InscripcionMes, DiaSemana, Reserva


def _inscriptos(actividad, dia_numero):
    hoy = datetime.date.today()
    return InscripcionMes.objects.filter(
        actividad=actividad, anio=hoy.year, mes=hoy.month, dias__numero=dia_numero
    ).count()


# columnas fijas
COLUMNAS_FIJAS = ("nombre", "cupo_maximo")
COLUMNA_TOTAL = ("resumen_cupo", "activa")

# mapeo numero de día → nombre de método
METODOS_POR_DIA = {
    0: "col_lunes", 1: "col_martes", 2: "col_miercoles", 3: "col_jueves",
    4: "col_viernes", 5: "col_sabado", 6: "col_domingo",
}


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_filter = ("activa",)
    search_fields = ("nombre",)

    def get_list_display(self, request):
        """Columnas de días según lo que exista en la tabla DiaSemana."""
        dias_existentes = list(DiaSemana.objects.values_list("numero", flat=True))
        columnas_dias = tuple(METODOS_POR_DIA[n] for n in sorted(dias_existentes) if n in METODOS_POR_DIA)
        return COLUMNAS_FIJAS + columnas_dias + COLUMNA_TOTAL

    # --- columnas por día (solo se muestran si el día existe) ---
    @admin.display(description="Lun")
    def col_lunes(self, obj):
        return self._badge_dia(obj, 0)

    @admin.display(description="Mar")
    def col_martes(self, obj):
        return self._badge_dia(obj, 1)

    @admin.display(description="Mié")
    def col_miercoles(self, obj):
        return self._badge_dia(obj, 2)

    @admin.display(description="Jue")
    def col_jueves(self, obj):
        return self._badge_dia(obj, 3)

    @admin.display(description="Vie")
    def col_viernes(self, obj):
        return self._badge_dia(obj, 4)

    @admin.display(description="Sáb")
    def col_sabado(self, obj):
        return self._badge_dia(obj, 5)

    @admin.display(description="Dom")
    def col_domingo(self, obj):
        return self._badge_dia(obj, 6)

    def _badge_dia(self, obj, dia_numero):
        count = _inscriptos(obj, dia_numero)
        libres = obj.cupo_maximo - count
        if count >= obj.cupo_maximo:
            color = "#dc3545"      # rojo: completo
        elif 0 < libres <= 3:
            color = "#ffc107"      # amarillo: quedan pocos
        else:
            color = ""
        if color:
            return format_html(
                '<span class="badge" style="background-color:{}; color:{}">{} / {}</span>',
                color,
                "#212529" if color == "#ffc107" else "white",
                count, obj.cupo_maximo,
            )
        return format_html("{} / {}", count, obj.cupo_maximo)

    @admin.display(description="Estado del cupo")
    def resumen_cupo(self, obj):
        dias_existentes = list(DiaSemana.objects.values_list("numero", flat=True))
        counts = [_inscriptos(obj, n) for n in dias_existentes]
        libres_por_dia = [max(obj.cupo_maximo - c, 0) for c in counts]
        total_libres = sum(libres_por_dia)
        hay_dia_lleno = any(c >= obj.cupo_maximo for c in counts)
        total_cupo = obj.cupo_maximo * len(dias_existentes) if dias_existentes else 1

        if hay_dia_lleno:
            color, texto = "#dc3545", f"🔴 Completo · {total_libres} total"
        elif total_libres <= 3:
            color, texto = "#ffc107", f"⚠️ Quedan {total_libres}"
        else:
            color, texto = "#198754", f"✅ {total_libres} Libres"

        return format_html(
            '<span class="badge" style="background-color:{}; color:{}">{}</span>',
            color,
            "#212529" if color == "#ffc107" else "white",
            texto,
        )

class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0


@admin.register(InscripcionMes)
class InscripcionMesAdmin(admin.ModelAdmin):
    list_display = ("socio", "actividad", "anio", "mes", "plan", "ver_dias")
    list_filter = ("actividad", "plan", "mes")
    search_fields = ("socio__usuario__username", "socio__dni")
    inlines = [ReservaInline]

    @admin.display(description="Días")
    def ver_dias(self, obj):
        return ", ".join(d.nombre for d in obj.dias.all())


@admin.register(DiaSemana)
class DiaSemanaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    list_editable = ("nombre",)   # editar el nombre directo desde la lista