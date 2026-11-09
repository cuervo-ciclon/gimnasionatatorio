from django.apps import AppConfig


class SociosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'socios'

    def ready(self):
        # Genera cuota y revisión del mes al dar de alta / reactivar un socio.
        from . import signals  # noqa: F401