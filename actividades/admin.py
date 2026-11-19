import datetime
import calendar
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Actividad, DiaSemana, Horario, InscripcionMes, Reserva, Recupero


def _inscriptos(actividad, dia_numero):
    """Cuántos socios tienen lugar ese día de la semana en la actividad (mes actual)."""
    hoy = datetime.date.today()
    return InscripcionMes.objects.filter(
        actividad=actividad, anio=hoy.year, mes=hoy.month, dias__numero=dia_numero
    ).count()


# --- columnas fijas y finales de la tabla de actividades ---
COLUMNAS_FIJAS = ("nombre", "col_horario", "cupo_maximo")
COLUMNA_TOTAL = ("resumen_cupo", "activa")

METODOS_POR_DIA = {
    0: "col_lunes", 1: "col_martes", 2: "col_miercoles", 3: "col_jueves",
    4: "col_viernes", 5: "col_sabado", 6: "col_domingo",
}


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_filter = ("activa",)
    search_fields = ("nombre",)
    filter_horizontal = ("dias",)
    fields = ("nombre", "horario", "dias", "descripcion", "cupo_maximo", "activa")

    def get_list_display(self, request):
        """Columnas de días según lo que exista en la tabla DiaSemana."""
        dias_existentes = list(DiaSemana.objects.values_list("numero", flat=True))
        columnas_dias = tuple(
            METODOS_POR_DIA[n] for n in sorted(dias_existentes) if n in METODOS_POR_DIA
        )
        return COLUMNAS_FIJAS + columnas_dias + COLUMNA_TOTAL

    # --- columnas fijas ---
    @admin.display(description="Horario", ordering="horario__etiqueta")
    def col_horario(self, obj):
        return obj.horario.etiqueta if obj.horario else "—"

    @admin.display(description="Días de la actividad")
    def ver_dias(self, obj):
        return ", ".join(d.nombre for d in obj.dias.all()) or "—"
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for reserva in form.instance.reservas.all():
            if reserva.estado == "ausente":
                Recupero.objects.get_or_create(
                    inscripcion=form.instance, fecha_fallada=reserva.fecha
                )

    # --- columnas por día (solo se muestran si el día existe en DiaSemana) ---
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
        # ¿la actividad se dicta ese día?
        if not obj.dias.filter(numero=dia_numero).exists():
            return format_html(
                '<span class="badge" style="background-color:#6c757d; color:white">🚫 {}</span>',
                "-",
            )
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

    # --- estado general del cupo ---
    @admin.display(description="Estado del cupo")
    def resumen_cupo(self, obj):
        dias_de_la_actividad = list(obj.dias.values_list("numero", flat=True))
        counts = [_inscriptos(obj, n) for n in dias_de_la_actividad]
        libres_por_dia = [max(obj.cupo_maximo - c, 0) for c in counts]
        total_libres = sum(libres_por_dia)
        hay_dia_lleno = any(c >= obj.cupo_maximo for c in counts)

        if not dias_de_la_actividad:
            color, texto = "#6c757d", "⚠️ Sin días asignados"
        elif hay_dia_lleno:
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


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ("etiqueta",)


@admin.register(DiaSemana)
class DiaSemanaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    list_editable = ("nombre",)


class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0
class InscripcionMesAdminForm(forms.ModelForm):
    class Meta:
        model = InscripcionMes
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("plan")
        dias = cleaned.get("dias")          # 👈 acá están los días MARCADOS
        n_dias = dias.count() if dias is not None else 0

        if plan and n_dias != plan:
            raise forms.ValidationError(
                f"Elegiste el plan de {plan} día(s) por semana "
                f"pero marcaste {n_dias}. Tiene que coincidir."
            )
        return cleaned

@admin.register(InscripcionMes)
class InscripcionMesAdmin(admin.ModelAdmin):
    form = InscripcionMesAdminForm     # 👈 conectar el formulario
    list_display = ("socio", "actividad", "anio", "mes", "plan", "ver_dias")
    list_filter = ("actividad", "plan", "mes")
    filter_horizontal = ("dias",)
    search_fields = ("socio__usuario__username", "socio__dni")
    inlines = [ReservaInline]

    @admin.display(description="Días")
    def ver_dias(self, obj):
        return ", ".join(d.nombre for d in obj.dias.all()) or "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # regenerar reservas del mes con los días actuales
        obj.reservas.all().delete()
        _, dias_del_mes = calendar.monthrange(obj.anio, obj.mes)
        from datetime import date
        dias_actuales = set(d.numero for d in obj.dias.all())
        for dia in range(1, dias_del_mes + 1):
            fecha = date(obj.anio, obj.mes, dia)
            if fecha.weekday() in dias_actuales:
                Reserva.objects.get_or_create(inscripcion=obj, fecha=fecha)

@admin.register(Recupero)
class RecuperoAdmin(admin.ModelAdmin):
    list_display = ("socio", "actividad", "fecha_fallada", "fecha_recupero", "estado", "creado")
    list_filter = ("estado",)
    search_fields = ("inscripcion__socio__usuario__username", "inscripcion__socio__dni")

    @admin.display(description="Socio")
    def socio(self, obj):
        return obj.inscripcion.socio

    @admin.display(description="Actividad")
    def actividad(self, obj):
        return obj.inscripcion.actividad