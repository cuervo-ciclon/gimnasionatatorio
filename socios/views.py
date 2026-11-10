"""Vistas: panel del socio, dashboard admin, recepción y acciones del staff."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.forms import RegistroForm
from .forms import BuscarSocioForm, CheckinRapidoForm
from .models import Asistencia, Cuota, RevisionMedica, Socio
from .services import hacer_checkin, mes_actual, nombre_mes

def staff_required(view):
    """Solo personal (is_staff). Un socio logueado va a SU panel, no al login."""
    @login_required(login_url='accounts:login')
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.warning(request, 'Esa sección es solo para el personal.')
            return redirect('socios:panel')
        return view(request, *args, **kwargs)
    return wrapper


def _next_seguro(request, fallback):
    """Redirige a `next` solo si es una URL interna del propio sitio."""
    siguiente = request.POST.get('next') or request.GET.get('next')
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return siguiente
    return fallback


# ------------------------------------------------------------------
# Panel del SOCIO
# ------------------------------------------------------------------
@login_required
def panel_socio(request):
    """Estado de cuota y revisión del mes + historial de asistencias (solo lectura)."""
    socio = getattr(request.user, 'socio', None)
    if socio is None:
        messages.info(request, 'Tu usuario no tiene perfil de socio.')
        return redirect('pagina:inicio')

    anio, mes = mes_actual()
    contexto = {
        'socio': socio,
        'periodo': f'{nombre_mes(mes)} {anio}',
        'cuota': socio.cuotas.filter(anio=anio, mes=mes).first(),
        'revision': socio.revisiones.filter(anio=anio, mes=mes).first(),
        'asistencias': socio.asistencias.all()[:30],
        'cuotas': socio.cuotas.all()[:12],
    }
    return render(request, 'socios/panel_socio.html', contexto)


# ------------------------------------------------------------------
# Panel ADMIN (staff)
# ------------------------------------------------------------------
@staff_required
def dashboard(request):
    """Resumen del mes + check-in rápido por DNI."""
    anio, mes = mes_actual()
    cuotas_mes = Cuota.objects.filter(anio=anio, mes=mes).select_related('socio__user')
    impagas = cuotas_mes.filter(pagada=False)
    revisiones_pendientes = RevisionMedica.objects.filter(
        anio=anio, mes=mes, apto=False
    ).select_related('socio__user')
    asistencias_hoy = Asistencia.objects.filter(
        fecha_hora__date=timezone.localdate()
    ).select_related('socio__user')

    contexto = {
        'periodo': f'{nombre_mes(mes)} {anio}',
        'stats': {
            'socios_activos': Socio.objects.filter(activo=True).count(),
            'cuotas_impagas': impagas.count(),
            'cuotas_cobradas': cuotas_mes.filter(pagada=True).count(),
            'revisiones_pendientes': revisiones_pendientes.count(),
            'asistencias_hoy': asistencias_hoy.count(),
        },
        'form_checkin': CheckinRapidoForm(),
        'impagas': impagas[:20],
        'revisiones_pendientes': revisiones_pendientes[:20],
        'asistencias_hoy': asistencias_hoy[:20],
    }
    return render(request, 'socios/dashboard.html', contexto)


@staff_required
@require_POST
def checkin_rapido(request):
    """Check-in del dashboard: busca por DNI y registra el ingreso con avisos."""
    form = CheckinRapidoForm(request.POST)
    if form.is_valid():
        dni = form.cleaned_data['dni'].strip()
        socio = Socio.objects.filter(dni=dni).select_related('user').first()
        if socio is None:
            messages.error(request, f'No se encontró un socio con DNI {dni}.')
        elif not socio.activo:
            messages.warning(request, f'{socio} está dado de baja. No se registró el ingreso.')
        else:
            _, avisos = hacer_checkin(socio)
            messages.success(request, f'Check-in de {socio} registrado.')
            for aviso in avisos:
                messages.warning(request, aviso)
    return redirect(_next_seguro(request, 'socios:dashboard'))


@staff_required
@require_POST
def checkin_socio(request, pk):
    """Check-in desde la recepción (socio ya identificado)."""
    socio = get_object_or_404(Socio, pk=pk)
    if not socio.activo:
        messages.warning(request, f'{socio} está dado de baja. No se registró el ingreso.')
        return redirect(_next_seguro(request, 'socios:recepcion'))
    _, avisos = hacer_checkin(socio)
    messages.success(request, f'Check-in de {socio} registrado.')
    for aviso in avisos:
        messages.warning(request, aviso)
    return redirect(_next_seguro(request, 'socios:recepcion'))


@staff_required
def recepcion(request):
    """Búsqueda de socios por DNI o nombre + check-in y avisos."""
    form = BuscarSocioForm(request.GET or None)
    consulta = (request.GET.get('q') or '').strip()
    anio, mes = mes_actual()

    resultados = []
    if consulta:
        socios = (
            Socio.objects.filter(activo=True)
            .filter(
                Q(dni__icontains=consulta)
                | Q(user__first_name__icontains=consulta)
                | Q(user__last_name__icontains=consulta)
                | Q(user__username__icontains=consulta)
            )
            .select_related('user')[:25]
        )
        for socio in socios:
            resultados.append({
                'socio': socio,
                'cuota': socio.cuotas.filter(anio=anio, mes=mes).first(),
                'revision': socio.revisiones.filter(anio=anio, mes=mes).first(),
            })

    return render(request, 'socios/recepcion.html', {
        'form': form,
        'consulta': consulta,
        'resultados': resultados,
        'periodo': f'{nombre_mes(mes)} {anio}',
    })


# ------------------------------------------------------------------
# Acciones del staff: cuotas y revisiones
# ------------------------------------------------------------------
@staff_required
@require_POST
def marcar_cuota_pagada(request, pk):
    """Solo el staff puede marcar la cuota como pagada (un click)."""
    cuota = get_object_or_404(Cuota.objects.select_related('socio__user'), pk=pk)
    if cuota.pagada:
        messages.info(request, f'La cuota de {cuota.socio} ya estaba pagada.')
    else:
        cuota.marcar_pagada()
        messages.success(request, f'Cuota de {cuota.socio} ({cuota.periodo}) marcada como pagada.')
    return redirect(_next_seguro(request, 'socios:dashboard'))


@staff_required
@require_POST
def marcar_revision_apta(request, pk):
    """Solo el staff puede marcar la revisión médica como apta (un click)."""
    revision = get_object_or_404(RevisionMedica.objects.select_related('socio__user'), pk=pk)
    if revision.apto:
        messages.info(request, f'La revisión de {revision.socio} ya estaba marcada como apta.')
    else:
        revision.marcar_apto()
        messages.success(
            request, f'Revisión de {revision.socio} ({revision.periodo}) marcada como apta.'
        )
    return redirect(_next_seguro(request, 'socios:dashboard'))


# ------------------------------------------------------------------
# Gestión de socios (staff)
# ------------------------------------------------------------------
@staff_required
def socio_lista(request):
    """Listado de socios con alta/baja (toggle de activo)."""
    consulta = (request.GET.get('q') or '').strip()
    socios = Socio.objects.select_related('user')
    if consulta:
        socios = socios.filter(
            Q(dni__icontains=consulta)
            | Q(user__first_name__icontains=consulta)
            | Q(user__last_name__icontains=consulta)
            | Q(user__username__icontains=consulta)
        )
    pagina = Paginator(socios, 25).get_page(request.GET.get('page'))
    return render(request, 'socios/socio_lista.html', {'pagina': pagina, 'consulta': consulta})


@staff_required
def socio_alta(request):
    """Alta de socio desde el panel (crea usuario + perfil + registros del mes)."""
    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Socio {user.socio} dado de alta correctamente.')
        return redirect('socios:socio_detalle', pk=user.socio.pk)
    return render(request, 'socios/socio_form.html', {'form': form})


@staff_required
def socio_detalle(request, pk):
    """Ficha del socio: cuotas, revisiones y historial completo de asistencias."""
    socio = get_object_or_404(Socio.objects.select_related('user'), pk=pk)
    anio, mes = mes_actual()
    return render(request, 'socios/socio_detalle.html', {
        'socio': socio,
        'periodo': f'{nombre_mes(mes)} {anio}',
        'cuota': socio.cuotas.filter(anio=anio, mes=mes).first(),
        'revision': socio.revisiones.filter(anio=anio, mes=mes).first(),
        'cuotas': socio.cuotas.all()[:24],
        'revisiones': socio.revisiones.all()[:24],
        'asistencias': socio.asistencias.all()[:60],
    })


@staff_required
@require_POST
def toggle_activo(request, pk):
    """Alta/baja de socio: alterna `activo` (la baja NO borra historial)."""
    socio = get_object_or_404(Socio.objects.select_related('user'), pk=pk)
    socio.activo = not socio.activo
    socio.save()
    if socio.activo:
        messages.success(request, f'{socio} fue dado de alta (cuota y revisión del mes generadas).')
    else:
        messages.warning(request, f'{socio} fue dado de baja.')
    return redirect(_next_seguro(request, 'socios:socio_detalle'))