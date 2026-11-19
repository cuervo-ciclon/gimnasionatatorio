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

class Horario(models.Model):
    """Franja horaria de una actividad, ej: 19:30 - 20:30."""
    etiqueta = models.CharField(max_length=30, unique=True)  # ej: "19:30 - 20:30"

    class Meta:
        ordering = ["etiqueta"]

    def __str__(self):
        return self.etiqueta
class Actividad(models.Model):
    nombre = models.CharField(max_length=100)
    horario = models.ForeignKey(
        Horario, on_delete=models.PROTECT, null=True, blank=True,
        related_name="actividades",
    )
    dias = models.ManyToManyField(DiaSemana, blank=True, related_name="actividades")
    descripcion = models.TextField(blank=True)
    cupo_maximo = models.PositiveIntegerField(default=20, verbose_name="Cupo")   # cupo por día/sesión
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre", "horario__etiqueta"]

    def __str__(self):
        if self.horario:
            return f"{self.nombre} ({self.horario})"
        return self.nombre

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.horario:
            return
        repetidos = Actividad.objects.filter(
            nombre=self.nombre, horario=self.horario
        ).exclude(pk=self.pk)
        for otra in repetidos:
            dias_otra = set(otra.dias.values_list("numero", flat=True))
            dias_mios = set(d.numero for d in self.dias.all())
            pisados = dias_otra & dias_mios
            if pisados:
                nombres = ", ".join(
                    d.nombre for d in otra.dias.all() if d.numero in pisados
                )
                raise ValidationError(
                    f"Ya existe '{self.nombre}' los {nombres} en el horario {self.horario}. "
                    f"Elegí otros días u otro horario."
                )

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

class Recupero(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "P", "Pendiente"
        USADO = "U", "Usado"
        VENCIDO = "V", "Vencido"
        CANCELADO = "C", "Cancelado"

    inscripcion = models.ForeignKey(InscripcionMes, on_delete=models.CASCADE, related_name="recuperos")
    fecha_fallada = models.DateField()                 # la clase que no asistió
    fecha_recupero = models.DateField(null=True, blank=True)  # la clase donde recupera
    estado = models.CharField(max_length=1, choices=Estado.choices, default=Estado.PENDIENTE)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Recupero de {self.inscripcion.socio} – faltó {self.fecha_fallada} ({self.get_estado_display()})"