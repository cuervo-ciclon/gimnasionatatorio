# Corpo Natatorio y Gimnasio – Backend Django 6

Backend para la landing del gimnasio natatorio: socios, cuotas mensuales,
revisiones médicas mensuales, control de asistencia con avisos y paneles
(admin y socio). La landing se mantiene intacta: `convertir_template.py`
la convierte en templates de Django con `{% static %}`.

## Requisitos

- Python 3.14
- Django 6 (última estable)
- Entorno virtual (`.venv`) dentro del proyecto

## Instalación (desde cero)

1. Crear el entorno e instalar dependencias:

       cd gimnasionatatorio
       python -m venv .venv
       # Windows:
       .venv\Scripts\activate
       # Linux/Mac:
       source .venv/bin/activate
       pip install -r requirements.txt

2. Copiar la landing original en `original/`:

       original/index.html      <- tu landing actual, sin cambios
       original/assets/          <- css/, js/, img/ (cuando los tengas)

3. Generar los templates de Django (no toca el diseño):

       python convertir_template.py

   Esto crea `pagina/templates/base.html`,
   `pagina/templates/pagina/index.html` y copia `original/assets/`
   a `pagina/static/assets/`. Re-ejecutar cada vez que cambies la landing
   o agregues css/js/img.

4. Migraciones y superusuario:

       python manage.py makemigrations socios
       python manage.py migrate
       python manage.py createsuperuser

5. Correr:

       python manage.py runserver

   Landing: http://localhost:8000/ | Admin Django: /admin/ |
   Login socios: /cuentas/login/ | Panel admin: /socios/admin/

6. Tests:

       python manage.py test

## Configuración

Settings separados por entorno, valores sensibles en `.env`
(copiar `.env.example` a `.env`):

- `gimnasionatatorio/settings/base.py`: común (SQLite, es-ar,
  America/Buenos_Aires, whitenoise, python-decouple)
- `gimnasionatatorio/settings/dev.py`: DEBUG=True (default en manage.py)
- `gimnasionatatorio/settings/production.py`: DEBUG=False, whitenoise
  comprimido, MySQL opcional, SMTP opcional, headers de seguridad

Usar producción: `python manage.py runserver --settings=gimnasionatatorio.settings.production`
o `DJANGO_SETTINGS_MODULE=gimnasionatatorio.settings.production`.

## Generación mensual de cuotas y revisiones

Mecanismo doble:

1. Command programable (día 1 de cada mes):

       python manage.py crear_cuotas_y_revisiones
       # o período explícito:
       python manage.py crear_cuotas_y_revisiones --anio 2027 --mes 1

2. Respaldo on-demand: si el command no corrió, el primer check-in del
   socio (y el alta/re-activación del socio) crean la cuota y la revisión
   del mes vigente. Nunca falta el registro.

Es idempotente: correrlo varias veces no duplica nada (constraints
únicos socio+anio+mes) ni pisa pagos/aptos ya marcados.

### Programar el command mensual

**Linux (cron):**

       crontab -e
       # Día 1 de cada mes, 06:00:
       0 6 1 * * cd /ruta/gimnasionatatorio && .venv/bin/python manage.py crear_cuotas_y_revisiones

**Windows (Programador de tareas):**

1. Abrir "Programador de tareas" → "Crear tarea básica".
2. Nombre: "Cuotas Corpo". Trigger: "Mensual", día 1, 06:00.
3. Acción: "Iniciar programa":
   - Programa: `C:\ruta\gimnasionatatorio\.venv\Scripts\python.exe`
   - Argumentos: `manage.py crear_cuotas_y_revisiones`
   - Iniciar en: `C:\ruta\gimnasionatatorio`

O por consola:

       schtasks /create /tn "Cuotas Corpo" /tr "C:\ruta\.venv\Scripts\python.exe C:\ruta\manage.py crear_cuotas_y_revisiones" /sc monthly /d 1 /st 06:00

## Migrar de SQLite a MySQL (producción)

1. Instalar el driver (descomentar `mysqlclient` en requirements.txt):

       pip install mysqlclient

2. Crear la base (utf8mb4):

       CREATE DATABASE gimnasionatatorio CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

3. Respaldar los datos actuales (con SQLite activo):

       python manage.py dumpdata --natural-foreign --natural-primary -o backup.json

4. En `.env` activar MySQL:

       USE_MYSQL=True
       MYSQL_DB=gimnasionatatorio
       MYSQL_USER=gimnasio
       MYSQL_PASSWORD=...
       MYSQL_HOST=127.0.0.1
       MYSQL_PORT=3306

5. Migrar y restaurar:

       python manage.py migrate --settings=gimnasionatatorio.settings.production
       python manage.py loaddata backup.json --settings=gimnasionatatorio.settings.production

## Agregar Django REST Framework más adelante (app móvil)

Sin API por ahora. Cuando toque:

1. Descomentar en requirements.txt:

       djangorestframework
       djangorestframework-simplejwt

2. En settings/base.py INSTALLED_APPS agregar:

       'rest_framework',
       'rest_framework_simplejwt',

3. Configurar:

       REST_FRAMEWORK = {
           'DEFAULT_AUTHENTICATION_CLASSES': (
               'rest_framework_simplejwt.authentication.JWTAuthentication',
           ),
       }
       from datetime import timedelta
       SIMPLE_JWT = {
           'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
           'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
       }

4. Exponer endpoints en un urls.py (ej.: socios/ → estado de cuota,
   revisión y asistencias del usuario autenticado) con ViewSets de
   DRF. Los templates actuales no se tocan.

## Despliegue (whitenoise, DEBUG=False)

1. `.env`: DEBUG=False, ALLOWED_HOSTS=tudominio.com, SECRET_KEY fuerte,
   SSL_REDIRECT=True si hay HTTPS.
2. Estáticos:

       python manage.py collectstatic --settings=gimnasionatatorio.settings.production

3. whitenoise sirve estáticos desde `staticfiles/` sin nginx ni CDN.
4. Recuperación de contraseña: configurar SMTP en `.env`
   (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD).
   En desarrollo los emails aparecen por consola.

## Decisiones y notas

- Cada User nuevo obtiene su Socio por señal post_save; el registro y el
  alta manual completan DNI/teléfono/plan. Los superusuarios no generan
  cuotas/revisiones (no son socios).
- Los avisos del check-in (cuota impaga, revisión sin apto, exceso de
  plan) INFORMAN a recepción pero NO bloquean el ingreso, según lo pedido.
- Semana = lunes a domingo; varias visitas el mismo día cuentan como 1 día
  para el plan "X días por semana".
- Sin comprobantes, imágenes ni integración de pagos: el pago se registra
  por fuera y el admin marca "pagada" con un click.
- El navbar generado agrega los enlaces "Ingresar / Asociate / Mi Panel /
  Admin / Salir" según la sesión; el resto de la landing queda idéntico.
- Detalle del HTML original: hay una letra "f" suelta después del preloader
  (`</div>f`, línea ~48 del index original). No la toca el converter para
  mantener el diseño exactamente igual; conviene sacar-la a mano en
  original/index.html.