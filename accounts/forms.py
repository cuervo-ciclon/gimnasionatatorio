"""Formularios de autenticación y registro."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class LoginForm(AuthenticationForm):
    """Login con estilo Bootstrap (la landing usa Bootstrap 5 alpha)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs['class'] = 'form-control'


class RegistroForm(UserCreationForm):
    """Registro público: SOLO email + contraseña + confirmación.

    Crea el User con username = email; la señal post_save crea el Socio.
    DNI, teléfono y plan quedan pendientes: se completan en recepción
    cuando el socio se presenta por primera vez.
    """

    email = forms.EmailField(label='Email', max_length=254)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)          # password1 y password2 vienen de UserCreationForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Orden final: email, contraseña, repetir contraseña
        self.order_fields(['email', 'password1', 'password2'])
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username=email).exists() or \
           User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese email.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email'].strip().lower()  # username = email
        user.email = user.username
        user.is_staff = False       # nunca staff por registro
        user.is_superuser = False   # nunca superusuario por registro
        if commit:
            user.save()             # la señal post_save crea el Socio vacío
        return user