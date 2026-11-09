"""Reglas de negocio: generación mensual, generación on-demand y check-in."""
from datetime import timedelta

from django.utils import timezone

from .models import Asistencia, Cuota, NOMBRES_MESES, RevisionMedica, Socio


def ahora_local():
    """Hora actual en la zona horaria local (America/Buenos_Aires)."""
    return timezone.localtime(timezone.now())


def mes_actual():
    """(anio, mes) vigentes según la hora local."""
    actual = ahora_local()
    return actual.year, actual.month


def nombre_mes(numero):
    return NOMBRES_MESES[numero - 1]


def asegurar_cuota(socio, anio, mes):
    """Devuelve la cuota del período, creándola si no existe (creación on-demand)."""
    cuota, _ = Cuota.objects.get_or_create(socio=socio, anio=anio, mes=mes)
    return cuota


def asegurar_revision(socio, anio, mes):
    """Devuelve la revisión médica del período, creándola si no existe (on-demand)."""
    revision, _ = RevisionMedica.objects.get_or_create(socio=socio, anio=anio, mes=mes)
    return revision


def generar_cuotas_y_revisiones(anio=None, mes=None):
    """Crea cuota y revisión del período para todos los socios ACTIVOS.

    Es idempotente: los registros existentes no se duplican ni se modifican
    (constraints únicos socio+anio+mes). La usa el management command
    `crear_cuotas_y_revisiones`. Devuelve (cuotas_creadas, revisiones_creadas).
    """
    if anio is None or mes is None:
        anio, mes = mes_actual()

    cuotas_creadas = revisiones_creadas = 0
    for socio in Socio.objects.filter(activo=True):
        _, creada = Cuota.objects.get_or_create(socio=socio, anio=anio, mes=mes)
        cuotas_creadas += int(creada)
        _, creada = RevisionMedica.objects.get_or_create(socio=socio, anio=anio, mes=mes)
        revisiones_creadas += int(creada)
    return cuotas_creadas, revisiones_creadas


def rango_semana(momento):
    """(lunes, domingo) de la semana a la que pertenece `momento`."""
    lunes = momento.date() - timedelta(days=momento.weekday())
    return lunes, lunes + timedelta(days=6)


def dias_usados_en_semana(socio, momento=None):
    """Cantidad de días distintos con asistencia en la semana en curso."""
    momento = momento or ahora_local()
    desde, hasta = rango_semana(momento)
    dias = Asistencia.objects.filter(
        socio=socio,
        fecha_hora__date__gte=desde,
        fecha_hora__date__lte=hasta,
    ).dates('fecha_hora', 'day')
    return len(dias)


def hacer_checkin(socio, momento=None):
    """Registra el ingreso y devuelve (asistencia, avisos).

    Los avisos INFORMAN a recepción pero NO bloquean el ingreso:
      a) cuota del mes impaga,
      b) revisión médica del mes sin apto vigente,
      c) plan "X días por semana": días de la semana en curso superados
         (se cuenta el día de hoy como 1; varias visitas el mismo día cuentan 1).

    Si la cuota o la revisión del mes aún no existen, se crean on-demand
    en ese mismo momento y después se aplican los avisos.
    """
    momento = momento or ahora_local()
    anio, mes = momento.year, momento.month

    # Creación on-demand de los registros del mes en curso.
    cuota = asegurar_cuota(socio, anio, mes)
    revision = asegurar_revision(socio, anio, mes)

    asistencia = Asistencia.objects.create(socio=socio)

    avisos = []
    if not cuota.pagada:
        avisos.append('CUOTA IMPAGA: la cuota del mes está pendiente de pago.')
    if not revision.apto:
        avisos.append('SIN REVISIÓN MÉDICA VIGENTE: no tiene el apto médico del mes.')
    if socio.plan == Socio.Plan.DIAS:
        dias = dias_usados_en_semana(socio, momento)
        if dias > socio.dias_por_semana:
            avisos.append(
                f'EXCESO DE PLAN: usó {dias} días esta semana y su plan permite {socio.dias_por_semana}.'
            )
    return asistencia, avisos