"""Vistas de accounts: registro y logout (login/reset usan vistas nativas)."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render

from .forms import RegistroForm


class Salir(auth_views.LogoutView):
    """Logout que acepta GET y POST (el navbar de la landing usa un enlace)."""

    http_method_names = ['get', 'post', 'options']


def registro(request):
    """Alta de socio: crea el usuario y su perfil automáticamente."""
    if request.user.is_authenticated:
        return redirect('socios:panel')

    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            f'¡Bienvenido/a, {user.first_name or user.username}! Tu cuenta de socio ya está activa.',
        )
        return redirect('socios:panel')

    return render(request, 'accounts/registro.html', {'form': form})