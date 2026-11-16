"""Modelos: DiaSemana, Actividad, InscripcionMes (plan mensual) y Reserva."""
from django.core.exceptions import ValidationError
from django.db import models

from socios.models import MES_CHOICES, Socio


class DiaSemana(models.Model):
    """Día de la semana: 0=Lunes ... 6=Domingo. Se carga por migración de datos."""

    numero = models.PositiveSmallIntegerField('Número', unique=True)
    nombre = models.CharField('Nombre', max_length=20)

    class Meta:
        verbose_name = 'Día de semana'
        verbose_name_plural = 'Días de semana'
        ordering = ['numero']

    def __str__(self):
        return self.nombre


class Actividad(models.Model):
    """Actividad del gimnasio. Solo el staff la crea y edita."""

    nombre = models.CharField('Nombre', max_length=100, unique=True)
    descripcion = models.TextField('Descripción', blank=True)
    cupo_maximo = models.PositiveSmallIntegerField(
        'Máximo', default=15,
        help_text='Cupo por cada día de la semana, por mes.',
    )
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class InscripcionMes(models.Model):
    """Plan mensual de un socio en una actividad (días de la semana elegidos)."""

    class Plan(models.IntegerChoices):
        UN_DIA = 1, '1 día'
        DOS_DIAS = 2, '2 días'
        TRES_DIAS = 3, '3 días'
        SEMANA_COMPLETA = 7, 'Semana completa'

    socio = models.ForeignKey(
        Socio, verbose_name='Socio', on_delete=models.CASCADE, related_name='inscripciones'
    )
    actividad = models.ForeignKey(
        Actividad, verbose_name='Actividad', on_delete=models.CASCADE, related_name='inscripciones'
    )
    anio = models.PositiveSmallIntegerField('Año')
    mes = models.PositiveSmallIntegerField('Mes', choices=MES_CHOICES)
    plan = models.PositiveSmallIntegerField('Plan', choices=Plan.choices)
    dias = models.ManyToManyField(DiaSemana, verbose_name='Días', related_name='inscripciones')
    creada = models.DateTimeField('Creada', auto_now_add=True)

    class Meta:
        verbose_name = 'Inscripción mensual'
        verbose_name_plural = 'Inscripciones mensuales'
        ordering = ['-anio', '-mes', 'actividad__nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['socio', 'actividad', 'anio', 'mes'],
                name='inscripcion_unica_por_periodo',
            ),
        ]

    def __str__(self):
        return f'{self.socio} → {self.actividad} ({self.mes}/{self.anio})'

    def clean(self):
        """La cantidad de días marcados debe coincidir con el plan."""
        if self.pk and self.dias.count() != self.plan:
            raise ValidationError('La cantidad de días elegidos debe coincidir con el plan.')


class Reserva(models.Model):
    """Una fecha concreta reservada a partir de una inscripción mensual."""

    class Estado(models.TextChoices):
        RESERVADA = 'reservada', 'Reservada'
        PRESENTE = 'presente', 'Presente'
        AUSENTE = 'ausente', 'Ausente'

    inscripcion = models.ForeignKey(
        InscripcionMes, verbose_name='Inscripción', on_delete=models.CASCADE, related_name='reservas'
    )
    fecha = models.DateField('Fecha')
    estado = models.CharField('Estado', max_length=10, choices=Estado.choices, default=Estado.RESERVADA)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['fecha']
        constraints = [
            models.UniqueConstraint(fields=['inscripcion', 'fecha'], name='reserva_unica_por_fecha'),
        ]

    def __str__(self):
        return f'{self.inscripcion.actividad} – {self.fecha:%d/%m/%Y} – {self.inscripcion.socio}'