"""Crea las cuotas y revisiones médicas del mes para todos los socios activos.

Programable el día 1 de cada mes (cron / Programador de tareas de Windows)
y también ejecutable a mano. La generación on-demand del sistema es el respaldo:
si el día que no se ejecutó, el primer check-in del socio crea lo que falte.
"""
from django.core.management.base import BaseCommand, CommandError

from socios.services import generar_cuotas_y_revisiones, mes_actual, nombre_mes


class Command(BaseCommand):
    help = (
        'Genera la cuota y la revisión médica del mes para todos los socios activos. '
        'Sin argumentos usa el mes en curso; también acepta --anio y --mes.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--anio', type=int, help='Año (ej.: 2027).')
        parser.add_argument('--mes', type=int, help='Mes (1 a 12).')

    def handle(self, *args, **options):
        anio = options['anio']
        mes = options['mes']
        if (anio is None) != (mes is None):
            raise CommandError('Pasá --anio y --mes juntos, o ninguno de los dos (usa el mes actual).')

        if anio is None:
            anio, mes = mes_actual()
        if not 1 <= mes <= 12:
            raise CommandError('El mes debe estar entre 1 y 12.')

        cuotas, revisiones = generar_cuotas_y_revisiones(anio=anio, mes=mes)
        self.stdout.write(
            self.style.SUCCESS(
                f'{cuotas} cuotas y {revisiones} revisiones creadas para {nombre_mes(mes)} {anio} '
                '(los registros ya existentes no se duplicaron).'
            )
        )