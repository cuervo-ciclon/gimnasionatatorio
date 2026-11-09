

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Conecta la señal que crea el Socio al registrar un usuario.
        from . import signals  # noqa: F401