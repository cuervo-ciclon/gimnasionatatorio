"""Alta (o re-activación) de un socio: genera cuota y revisión del mes vigente."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Socio
from .services import asegurar_cuota, asegurar_revision, mes_actual


@receiver(post_save, sender=Socio)
def generar_registros_del_mes(sender, instance, created, **kwargs):
    if instance.activo and not instance.user.is_superuser:
        anio, mes = mes_actual()
        asegurar_cuota(instance, anio, mes)
        asegurar_revision(instance, anio, mes)