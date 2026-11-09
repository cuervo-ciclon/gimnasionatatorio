#!/usr/bin/env python3
"""
Convierte la landing original en templates de Django SIN tocar el diseño.

Uso:
    1) Poné tu landing original en:  original/index.html
       (y, cuando la tengas, la carpeta original/assets/ con css/, js/ e img/)
    2) Ejecutá:  python convertir_template.py

Genera:
    pagina/templates/base.html          (head + navbar + footer + scripts + bloques Django)
    pagina/templates/pagina/index.html (todas las secciones, con {% static %})
    pagina/static/assets/              (copia de original/assets/)

Podés re-ejecutarlo cada vez que actualices la landing o agregues css/js/img.
"""
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / 'original' / 'index.html'
ORIGINAL_ASSETS = BASE / 'original' / 'assets'
TEMPLATES_DIR = BASE / 'pagina' / 'templates'
STATIC_DST = BASE / 'pagina' / 'static' / 'assets'

HEADER_END = '<!-- ========================= header end ========================= -->'
FOOTER_START = '<!-- ========================= footer start ========================= -->'

# Items de nav según sesión (se insertan después de "Contacto").
NAV_USUARIO = """
                            {# ==== Enlaces según sesión ==== #}
                            {% if user.is_authenticated %}
                            <li class="nav-item">
                                <a class="page-scroll" href="{% url 'socios:panel' %}">Mi Panel</a>
                            </li>
                            {% if user.is_staff %}
                            <li class="nav-item">
                                <a class="page-scroll" href="{% url 'socios:dashboard' %}">Admin</a>
                            </li>
                            {% endif %}
                            <li class="nav-item">
                                <a class="page-scroll" href="{% url 'accounts:logout' %}">Salir</a>
                            </li>
                            {% else %}
                            <li class="nav-item">
                                <a class="page-scroll" href="{% url 'accounts:login' %}">Ingresar</a>
                            </li>
                            <li class="nav-item">
                                <a class="page-scroll" href="{% url 'accounts:registro' %}">Asociate</a>
                            </li>
                            {% endif %}
"""

# Mensajes de django.contrib.messages, inyectados debajo del header.
MENSAJES = """
    {# ==== Mensajes (django.contrib.messages) ==== #}
    {% if messages %}
    <div class="container mt-3">
        {% for message in messages %}
        <div class="alert alert-{{ message.tags|default:'info' }} mb-2" role="alert">{{ message }}</div>
        {% endfor %}
    </div>
    {% endif %}
"""

ASSET_RE = re.compile(r'''((?:src|href|srcset|data-src)\s*=\s*["'])assets/([^"']+)''')
BG_RE = re.compile(r"""url\(\s*['"]?assets/([^'")\s]+)['"]?\s*\)""")
TITLE_RE = re.compile(r'<title>.*?</title>', re.DOTALL)
INDEX_HREF_RE = re.compile(r'''href\s*=\s*["']index\.html["']''')


def convertir_html(html: str) -> str:
    """Reescribe las referencias a assets/ usando {% static %}."""
    html = ASSET_RE.sub(lambda m: f"{m.group(1)}{{% static 'assets/{m.group(2)}' %}}", html)
    html = BG_RE.sub(lambda m: f"url('{{% static 'assets/{m.group(1)}' %}}')", html)
    html = TITLE_RE.sub(
        "<title>{% block title %}Corpo Natatorio y Gimnasio{% endblock %}</title>", html
    )
    html = INDEX_HREF_RE.sub("href=\"{% url 'pagina:inicio' %}\"", html)
    return html


def main():
    if not ORIGINAL.exists():
        sys.exit(
            f"[ERROR] No encontré {ORIGINAL}.\n"
            "        Copiá tu index.html original dentro de la carpeta original/ y volvé a ejecutar."
        )
    html = ORIGINAL.read_text(encoding='utf-8')

    if HEADER_END not in html or FOOTER_START not in html:
        sys.exit('[ERROR] No encontré los marcadores de header/footer en el HTML original.')
    if '{{' in html or '{%' in html:
        print('[AVISO] El HTML original contiene sintaxis de template Django ({{ o {%}); revisalo.')

    html = convertir_html(html)

    i = html.index(HEADER_END) + len(HEADER_END)
    f = html.index(FOOTER_START)

    base = (
        html[:i]
        + MENSAJES
        + "\n    {% block content %}{% endblock content %}\n\n    "
        + html[f:]
    )
    middle = html[i:f]

    # Enlaces de usuario en el navbar (después de "Contacto").
    base, n = re.subn(
        r'(<a class="page-scroll" href="#contact">Contacto</a>\s*</li>)',
        lambda m: m.group(1) + '\n' + NAV_USUARIO,
        base,
        count=1,
    )
    if n == 0:
        print('[AVISO] No pude insertar los enlaces Mi Panel/Ingresar en el navbar.')

    # Bloques para que otras páginas agreguen CSS/JS propios.
    base = base.replace('</head>', '    {% block extra_css %}{% endblock %}\n</head>', 1)
    base = base.replace('</body>', '    {% block extra_js %}{% endblock %}\n</body>', 1)
    base = '{% load static %}\n' + base

    index = (
        "{% extends 'base.html' %}\n"
        "{% load static %}\n"
        '{% block content %}\n' + middle + '\n{% endblock content %}\n'
    )

    (TEMPLATES_DIR / 'pagina').mkdir(parents=True, exist_ok=True)
    (TEMPLATES_DIR / 'base.html').write_text(base, encoding='utf-8')
    (TEMPLATES_DIR / 'pagina' / 'index.html').write_text(index, encoding='utf-8')

    if ORIGINAL_ASSETS.exists():
        STATIC_DST.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ORIGINAL_ASSETS, STATIC_DST, dirs_exist_ok=True)
        print(f'[OK] assets copiados en {STATIC_DST}')
    else:
        STATIC_DST.mkdir(parents=True, exist_ok=True)
        print('[AVISO] No encontré original/assets/: agregá css/, js/ e img/ ahí y re-ejecutá.')

    print(f'[OK] Generados:\n     {TEMPLATES_DIR / "base.html"}\n     {TEMPLATES_DIR / "pagina" / "index.html"}')


if __name__ == '__main__':
    main()