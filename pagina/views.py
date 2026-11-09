from django.shortcuts import render


def inicio(request):

    """Landing page (template generado por convertir_template.py)."""
    return render(request, 'pagina/index.html')