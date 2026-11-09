from django import forms


class CheckinRapidoForm(forms.Form):
    dni = forms.CharField(
        label='DNI',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'DNI del socio',
            'autofocus': 'autofocus',
            'inputmode': 'numeric',
        }),
    )


class BuscarSocioForm(forms.Form):
    q = forms.CharField(
        label='Buscar',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'DNI, nombre o apellido...',
        }),
    )