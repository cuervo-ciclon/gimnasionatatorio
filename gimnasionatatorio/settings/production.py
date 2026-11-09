"""Producción: DEBUG=False, whitenoise con hashes, MySQL opcional, SMTP opcional."""
from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = config('DEBUG', default=False, cast=bool)

# --- Base de datos: activar MySQL desde .env (USE_MYSQL=True) ---
if config('USE_MYSQL', default=False, cast=bool):
    DATABASES = {'default': DB_MYSQL}  # noqa: F405

# --- Estáticos: whitenoise comprimido con hashes (requiere collectstatic) ---
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# --- Cabeceras de seguridad ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

if config('SSL_REDIRECT', default=False, cast=bool):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Email SMTP (recuperación de contraseña) ---
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)