"""Configuración base común a dev y producción."""
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent 

SECRET_KEY = config('SECRET_KEY', default='clave-de-desarrollo-cambiar-en-produccion')

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Apps del proyecto
    'pagina',
    'accounts',
    'socios',
    'actividades',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.BloquearAdminParaSocios',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gimnasionatatorio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gimnasionatatorio.wsgi.application'

# Base de datos: SQLite en desarrollo. MySQL en producción (ver settings/production.py).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Diccionario MySQL reutilizable desde production.py (.env: USE_MYSQL=True).
DB_MYSQL = {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': config('MYSQL_DB', default='gimnasionatatorio'),
    'USER': config('MYSQL_USER', default='gimnasio'),
    'PASSWORD': config('MYSQL_PASSWORD', default=''),
    'HOST': config('MYSQL_HOST', default='127.0.0.1'),
    'PORT': config('MYSQL_PORT', default='3306'),
    'OPTIONS': {'charset': 'utf8mb4'},
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# Estáticos (landing) + whitenoise.
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "pagina/static/"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Autenticación.
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:post_login'
LOGOUT_REDIRECT_URL = 'pagina:inicio'

# Los mensajes de tipo ERROR usan la clase alert-danger de Bootstrap.
from django.contrib.messages import constants as mensajes  # noqa: E402

MESSAGE_TAGS = {mensajes.ERROR: 'danger'}

# Email: por consola en desarrollo (los mails de recuperación aparecen en la terminal).
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')


# --- Jazzmin: skin del panel /admin/ ---
JAZZMIN_SETTINGS = {
    "site_title": "Corpo – Administración",
    "site_header": "Corpo Natatorio y Gimnasio",
    "site_brand": "Corpo Admin",
    "site_logo": "assets/img/logo/icono.png",   # tu logo, relativo a static
    "site_logo_classes": "img-circle",
    "welcome_sign": "Gestión del gimnasio natatorio",
    "changeform_format": "horizontal_tabs",
    "user_avatar": None,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "brand_small_text": False,
    "accent": "accent-primary",   # probá accent-success / accent-danger
    "navbar": "navbar-dark",
    "no_navbar_border": True,
}

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver', '://pythonanywhere.com']