"""Vistas del staff: gestión de actividades e inscripciones mensuales."""
import calendar
import datetime
from datetime import date
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test

from socios.models import Socio
from socios.services import nombre_mes
from socios.views import staff_required

from .models import Actividad, DiaSemana, InscripcionMes, Recupero, Reserva
from .services import inscribir_socio, renovar_mes


@staff_required
def dashboard(request):
    """Listado de inscripciones del mes + formulario de inscripción + renovar mes."""
    hoy = timezone.localdate()
    anio, mes = hoy.year, hoy.month
    inscripciones = (
        InscripcionMes.objects.filter(anio=anio, mes=mes)
        .select_related('socio__user', 'actividad')
        .prefetch_related('dias', 'reservas')
    )

    if request.method == 'POST' and 'renovar' in request.POST:
        renovadas, _, errores = renovar_mes(anio, mes)
        for r in renovadas:
            messages.success(request, f'Renovada: {r.socio} → {r.actividad} ({r.reservas.count()} reservas).')
        for error in errores:
            messages.error(request, error)
        if not renovadas and not errores:
            messages.info(request, 'No había inscripciones pendientes de renovar.')
        return redirect('actividades:dashboard')

    # IDs ya renovados para el mes próximo (badge "Ya renovado")
    mes_siguiente, anio_siguiente = (mes + 1, anio) if mes < 12 else (1, anio + 1)
    ya_renovadas = set(
        InscripcionMes.objects.filter(anio=anio_siguiente, mes=mes_siguiente).values_list(
            'socio_id', 'actividad_id'
        )
    )
    for ins in inscripciones:
        ins.renovada = (ins.socio_id, ins.actividad_id) in ya_renovadas

    contexto = {
        'periodo': f'{nombre_mes(mes)} {anio}',
        'actividades': Actividad.objects.all(),
        'dias': DiaSemana.objects.all(),
        'socios': Socio.objects.filter(activo=True).select_related('user'),
        'inscripciones': inscripciones,
        'planes': InscripcionMes.Plan.choices,
    }
    return render(request, 'actividades/dashboard.html', contexto)


@staff_required
@require_POST
def inscribir(request):
    """El admin inscribe a un socio: elige plan y días; valida cupo y genera reservas."""
    hoy = timezone.localdate()
    try:
        socio = Socio.objects.get(pk=request.POST['socio'])
        actividad = Actividad.objects.get(pk=request.POST['actividad'])
        plan = int(request.POST['plan'])
        dias = [int(n) for n in request.POST.getlist('dias')]
    except (KeyError, ValueError, Socio.DoesNotExist, Actividad.DoesNotExist):
        messages.error(request, 'Datos incompletos o inválidos.')
        return redirect('actividades:dashboard')

   
    _, nivel, mensaje = inscribir_socio(socio, actividad, hoy.year, hoy.month, plan, dias)
    if nivel == 'ok':
        messages.success(request, mensaje)
    elif nivel == 'warn':
        messages.warning(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect('actividades:dashboard')

def cupos_disponibles(actividad, fecha):
    """Lugares libres en la actividad para una fecha (inscriptos fijos + recuperos)."""
    if not actividad.dias.filter(numero=fecha.weekday()).exists():
        return 0  # ese día la actividad no se dicta
    usados = Reserva.objects.filter(inscripcion__actividad=actividad, fecha=fecha).count()
    ocupados = Recupero.objects.filter(
        inscripcion__actividad=actividad,
        fecha_recupero=fecha,
        estado=Recupero.Estado.USADO,
    ).count()
    return max(actividad.cupo_maximo - usados - ocupados, 0)


def _fechas_con_lugar(actividad):
    """Fechas del mes actual de esa actividad con lugar libre."""
    hoy = timezone.localdate()
    fin = date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])
    fechas = []
    d = hoy
    while d <= fin:
        if actividad.dias.filter(numero=d.weekday()).exists() and cupos_disponibles(actividad, d) > 0:
            fechas.append(d)
        d += datetime.timedelta(days=1)
    return fechas


@staff_required
def asignar_recupero(request, recupero_id):
    """El admin elige la clase donde el socio recupera la que faltó."""
    recupero = get_object_or_404(Recupero, id=recupero_id)
    actividad = recupero.inscripcion.actividad

    if request.method == "POST":
        fecha_str = request.POST.get("fecha_recupero")
        try:
            fecha = datetime.date.fromisoformat(fecha_str)
        except (TypeError, ValueError):
            messages.error(request, "Fecha inválida.")
            return redirect("actividades:dashboard")

        if cupos_disponibles(actividad, fecha) <= 0:
            messages.error(request, f"Sin lugares en {actividad} el {fecha:%d/%m}. Elegí otra fecha.")
            return redirect("actividades:asignar_recupero", recupero_id)

        recupero.fecha_recupero = fecha
        recupero.estado = Recupero.Estado.USADO
        recupero.save()
        messages.success(
            request,
            f"Recupero asignado: {recupero.inscripcion.socio} → {actividad} el {fecha:%d/%m}.",
        )
        return redirect("actividades:dashboard")

    return render(request, "actividades/asignar_recupero.html", {
        "recupero": recupero,
        "fechas_posibles": _fechas_con_lugar(actividad),
        "actividad": actividad,
    })