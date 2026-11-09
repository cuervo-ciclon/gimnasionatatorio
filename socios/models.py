"""Modelos: Socio, Cuota, RevisionMedica y Asistencia."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

NOMBRES_MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
MES_CHOICES = [(numero, nombre) for numero, nombre in enumerate(NOMBRES_MESES, start=1)]


class Socio(models.Model):
    """Perfil del socio. Se crea automáticamente al registrar un usuario (señal)."""

    class Plan(models.TextChoices):
        LIBRE = 'libre', 'Acceso libre'
        DIAS = 'dias', 'X días por semana'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='Usuario',
        on_delete=models.CASCADE,
        related_name='socio',
    )
    dni = models.CharField('DNI', max_length=20, unique=True, null=True, blank=True)
    telefono = models.CharField('Teléfono', max_length=30, blank=True)
    plan = models.CharField('Plan', max_length=10, choices=Plan.choices, default=Plan.LIBRE)
    dias_por_semana = models.PositiveSmallIntegerField(
        'Días por semana',
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text='Solo aplica si el plan es "X días por semana".',
    )
    activo = models.BooleanField('Activo', default=True)
    fecha_alta = models.DateTimeField('Fecha de alta', auto_now_add=True)

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = 'Socios'
        ordering = ['user__last_name', 'user__first_name', 'user__username']

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return self.user.get_full_name() or self.user.username

    @property
    def plan_texto(self):
        if self.plan == self.Plan.DIAS:
            return f'{self.dias_por_semana} días por semana'
        return 'Acceso libre'


class Cuota(models.Model):
    """Cuota mensual. Solo el admin la marca como pagada."""

    socio = models.ForeignKey(
        Socio, verbose_name='Socio', on_delete=models.CASCADE, related_name='cuotas'
    )
    anio = models.PositiveSmallIntegerField('Año')
    mes = models.PositiveSmallIntegerField('Mes', choices=MES_CHOICES)
    pagada = models.BooleanField('Pagada', default=False)
    fecha_pago = models.DateTimeField('Fecha de pago', null=True, blank=True)

    class Meta:
        verbose_name = 'Cuota'
        verbose_name_plural = 'Cuotas'
        ordering = ['-anio', '-mes']
        constraints = [
            models.UniqueConstraint(fields=['socio', 'anio', 'mes'], name='cuota_unica_por_periodo'),
        ]

    def __str__(self):
        return f'{self.socio} – {self.periodo}'

    @property
    def periodo(self):
        return f'{NOMBRES_MESES[self.mes - 1]} {self.anio}'

    def marcar_pagada(self):
        """Marca la cuota como pagada y registra fecha y hora automáticamente."""
        self.pagada = True
        self.fecha_pago = timezone.now()
        self.save(update_fields=['pagada', 'fecha_pago'])


class RevisionMedica(models.Model):
    """Aptitud física mensual. Solo el admin la marca como apto."""

    socio = models.ForeignKey(
        Socio, verbose_name='Socio', on_delete=models.CASCADE, related_name='revisiones'
    )
    anio = models.PositiveSmallIntegerField('Año')
    mes = models.PositiveSmallIntegerField('Mes', choices=MES_CHOICES)
    apto = models.BooleanField('Apto', default=False)
    fecha_revision = models.DateTimeField('Fecha de revisión', null=True, blank=True)

    class Meta:
        verbose_name = 'Revisión médica'
        verbose_name_plural = 'Revisiones médicas'
        ordering = ['-anio', '-mes']
        constraints = [
            models.UniqueConstraint(fields=['socio', 'anio', 'mes'], name='revision_unica_por_periodo'),
        ]

    def __str__(self):
        return f'{self.socio} – {self.periodo}'

    @property
    def periodo(self):
        return f'{NOMBRES_MESES[self.mes - 1]} {self.anio}'

    def marcar_apto(self):
        """Marca la revisión como apta y registra fecha y hora automáticamente."""
        self.apto = True
        self.fecha_revision = timezone.now()
        self.save(update_fields=['apto', 'fecha_revision'])


class Asistencia(models.Model):
    """Check-in al gimnasio, registrado desde el panel de recepción."""

    socio = models.ForeignKey(
        Socio, verbose_name='Socio', on_delete=models.CASCADE, related_name='asistencias'
    )
    fecha_hora = models.DateTimeField('Fecha y hora', auto_now_add=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha_hora']

    def __str__(self):
        return f'{self.socio} – {self.fecha_hora:%d/%m/%Y %H:%M}'