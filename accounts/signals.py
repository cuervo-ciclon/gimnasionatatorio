"""Cada usuario nuevo se convierte automáticamente en Socio."""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from socios.models import Socio


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_socio_de_usuario(sender, instance, created, **kwargs):
    if created:
        Socio.objects.get_or_create(user=instance)