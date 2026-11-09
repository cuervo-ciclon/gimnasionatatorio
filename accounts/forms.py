"""Formularios de autenticación y registro."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from socios.models import Socio


class LoginForm(AuthenticationForm):
    """Login con estilo Bootstrap (la landing usa Bootstrap 5 alpha)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password'].widget.attrs['class'] = 'form-control'


class RegistroForm(UserCreationForm):
    """Registro público: crea el User; la señal crea el Socio y acá se completan sus datos.

    El socio queda activo y con la cuota y revisión médica del mes vigente
    generadas automáticamente (señal post_save de Socio).
    """

    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellido', max_length=150)
    email = forms.EmailField(label='Email')
    dni = forms.CharField(label='DNI', max_length=20)
    telefono = forms.CharField(label='Teléfono', max_length=30, required=False)
    plan = forms.ChoiceField(label='Plan', choices=Socio.Plan.choices)
    dias_por_semana = forms.IntegerField(label='Días por semana', min_value=1, max_value=7, initial=3)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            css = 'form-control'
            if isinstance(campo.widget, forms.Select):
                css = 'form-select'
            campo.widget.attrs.setdefault('class', css)

    def clean_dni(self):
        dni = self.cleaned_data['dni'].strip()
        if Socio.objects.filter(dni=dni).exists():
            raise forms.ValidationError('Ya existe un socio registrado con ese DNI.')
        return dni

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            socio = user.socio  # creado por la señal post_save del usuario
            socio.dni = self.cleaned_data['dni'].strip()
            socio.telefono = self.cleaned_data.get('telefono', '')
            socio.plan = self.cleaned_data['plan']
            socio.dias_por_semana = self.cleaned_data['dias_por_semana']
            socio.save()  # dispara la generación de cuota/revisión del mes vigente
        return user