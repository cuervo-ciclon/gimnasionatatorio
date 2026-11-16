"""Reglas de negocio: cupo por día, generación de reservas y renovación de mes."""
import calendar
from datetime import date

from .models import DiaSemana, InscripcionMes, Reserva


def lugares_restantes(actividad, anio, mes, dia_numero):
    """Cupo disponible para un día de la semana en ese mes."""
    ocupados = (
        InscripcionMes.objects.filter(actividad=actividad, anio=anio, mes=mes)
        .filter(dias__numero=dia_numero)
        .count()
    )
    return actividad.cupo_maximo - ocupados


def generar_reservas(inscripcion):
    """Crea una Reserva por cada fecha real del mes que caiga en los días elegidos."""
    dias_elegidos = set(inscripcion.dias.values_list('numero', flat=True))
    _, ultimo = calendar.monthrange(inscripcion.anio, inscripcion.mes)
    creadas = 0
    for dia in range(1, ultimo + 1):
        fecha = date(inscripcion.anio, inscripcion.mes, dia)
        if fecha.weekday() in dias_elegidos:
            _, creada = Reserva.objects.get_or_create(inscripcion=inscripcion, fecha=fecha)
            creadas += 1 if creada else 0
    return creadas


def inscribir_socio(socio, actividad, anio, mes, plan, dias_numeros):
    """
    Valida cupo en CADA día elegido y crea la inscripción + reservas.
    Devuelve (inscripcion | None, nivel, mensaje) con nivel en {'ok', 'warn', 'error'}.
    """
    if not actividad.activa:
        return None, 'error', '🔴 La actividad no está activa.'
    if len(dias_numeros) != plan:
        return None, 'error', '🔴 La cantidad de días elegidos no coincide con el plan.'

    sin_cupo, quedan_pocos = [], []
    for numero in dias_numeros:
        restantes = lugares_restantes(actividad, anio, mes, numero)
        nombre_dia = DiaSemana.objects.get(numero=numero).nombre
        if restantes <= 0:
            sin_cupo.append(nombre_dia)
        elif restantes <= 3:
            quedan_pocos.append((nombre_dia, restantes))

    if sin_cupo:
        return None, 'error', f'🔴 Sin cupo ese día, elegí otros días: {", ".join(sin_cupo)}.'

    inscripcion = InscripcionMes.objects.create(
        socio=socio, actividad=actividad, anio=anio, mes=mes, plan=plan,
    )
    inscripcion.dias.set(DiaSemana.objects.filter(numero__in=dias_numeros))
    generar_reservas(inscripcion)

    if quedan_pocos:
        detalle = ', '.join(f'{d} (quedan {n})' for d, n in quedan_pocos)
        return inscripcion, 'warn', f'⚠️ Socio inscripto. Quedan pocos lugares: {detalle}.'
    return inscripcion, 'ok', '✅ Socio inscripto correctamente.'


def renovar_mes(anio, mes):
    """
    Renueva todas las inscripciones del mes anterior al (anio, mes) indicado.
    Devuelve (renovadas, ya_renovadas, errores).
    """
    mes_anterior, anio_anterior = (mes - 1, anio) if mes > 1 else (12, anio - 1)
    renovadas, ya_renovadas, errores = [], [], []
    inscripciones = InscripcionMes.objects.filter(
        anio=anio_anterior, mes=mes_anterior
    ).select_related('socio', 'actividad').prefetch_related('dias')

    for ins in inscripciones:
        if InscripcionMes.objects.filter(
            socio=ins.socio, actividad=ins.actividad, anio=anio, mes=mes
        ).exists():
            ya_renovadas.append(ins)
            continue
        dias = list(ins.dias.values_list('numero', flat=True))
        nueva, _, error = inscribir_socio(ins.socio, ins.actividad, anio, mes, ins.plan, dias)
        if nueva:
            renovadas.append(nueva)
        else:
            errores.append(f'{ins.socio} → {ins.actividad}: {error}')
    return renovadas, ya_renovadas, errores