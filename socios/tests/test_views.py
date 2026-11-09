"""Tests de permisos de vistas, registro y flujo de check-in."""
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from socios.models import Asistencia, Cuota, RevisionMedica, Socio
from socios.services import asegurar_cuota, mes_actual

CLAVE = 'Clave#12345'


class PermisosTests(TestCase):
    def setUp(self):
        self.socio_user = User.objects.create_user(
            username='socio1', password=CLAVE, first_name='Sofia', last_name='Gomez'
        )
        self.socio_user.socio.dni = '30500111'
        self.socio_user.socio.save()

    def test_panel_anonimo_redirige_a_login(self):
        respuesta = self.client.get(reverse('socios:panel'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('accounts:login'), respuesta.url)

    def test_dashboard_anonimo_redirige_a_login(self):
        respuesta = self.client.get(reverse('socios:dashboard'))
        self.assertEqual(respuesta.status_code, 302)

    def test_dashboard_de_socio_comun_redirige_a_su_panel(self):
        self.client.login(username='socio1', password=CLAVE)
        respuesta = self.client.get(reverse('socios:dashboard'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, reverse('socios:panel'))

    def test_socio_no_puede_marcar_cuota_como_pagada(self):
        cuota = asegurar_cuota(self.socio_user.socio, *mes_actual())
        self.client.login(username='socio1', password=CLAVE)
        respuesta = self.client.post(reverse('socios:marcar_cuota_pagada', args=[cuota.pk]))
        cuota.refresh_from_db()
        self.assertFalse(cuota.pagada)
        self.assertEqual(respuesta.status_code, 302)

    def test_socio_no_puede_marcar_revision_como_apta(self):
        revision = RevisionMedica.objects.create(
            socio=self.socio_user.socio, anio=2030, mes=5
        )
        self.client.login(username='socio1', password=CLAVE)
        self.client.post(reverse('socios:marcar_revision_apta', args=[revision.pk]))
        revision.refresh_from_db()
        self.assertFalse(revision.apto)

    def test_staff_marca_cuota_como_pagada(self):
        staff = User.objects.create_user(username='staff1', password=CLAVE, is_staff=True)
        cuota = asegurar_cuota(self.socio_user.socio, *mes_actual())
        self.client.login(username='staff1', password=CLAVE)
        respuesta = self.client.post(
            reverse('socios:marcar_cuota_pagada', args=[cuota.pk]),
            {'next': reverse('socios:dashboard')},
        )
        cuota.refresh_from_db()
        self.assertTrue(cuota.pagada)
        self.assertIsNotNone(cuota.fecha_pago)
        self.assertEqual(respuesta.status_code, 302)

    def test_staff_ve_su_dashboard(self):
        User.objects.create_user(username='staff2', password=CLAVE, is_staff=True)
        self.client.login(username='staff2', password=CLAVE)
        respuesta = self.client.get(reverse('socios:dashboard'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Check-in rápido')


class PanelSocioTests(TestCase):
    def test_panel_muestra_cuota_y_revision_del_mes(self):
        user = User.objects.create_user(username='nadia', password=CLAVE)
        user.socio.dni = '27888999'
        user.socio.save()
        anio, mes = mes_actual()
        self.client.login(username='nadia', password=CLAVE)
        respuesta = self.client.get(reverse('socios:panel'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'PENDIENTE')  # cuota y revisión sin pagar/marcar
        self.assertTrue(
            Cuota.objects.filter(socio=user.socio, anio=anio, mes=mes).exists()
        )


class RegistroTests(TestCase):
    def test_registro_crea_usuario_socio_y_cuota_del_mes(self):
        datos = {
            'username': 'nuevo_socio',
            'first_name': 'Nuevo',
            'last_name': 'Socio',
            'email': 'nuevo@example.com',
            'dni': '32000111',
            'telefono': '2215551234',
            'plan': 'dias',
            'dias_por_semana': '3',
            'password1': CLAVE,
            'password2': CLAVE,
        }
        respuesta = self.client.post(reverse('accounts:registro'), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, reverse('socios:panel'))

        user = User.objects.get(username='nuevo_socio')
        socio = user.socio
        self.assertEqual(socio.dni, '32000111')
        self.assertEqual(socio.plan, 'dias')
        anio, mes = mes_actual()
        self.assertTrue(Cuota.objects.filter(socio=socio, anio=anio, mes=mes).exists())

    def test_registro_dni_duplicado_rechazado(self):
        User.objects.create_user(username='dup', password=CLAVE).socio  # señal
        Socio.objects.filter(user__username='dup').update(dni='111')
        datos = {
            'username': 'otro',
            'first_name': 'Otro',
            'last_name': 'Socio',
            'email': 'otro@example.com',
            'dni': '111',
            'telefono': '',
            'plan': 'libre',
            'dias_por_semana': '3',
            'password1': CLAVE,
            'password2': CLAVE,
        }
        respuesta = self.client.post(reverse('accounts:registro'), datos)
        self.assertEqual(respuesta.status_code, 200)  # vuelve al form con error
        self.assertFalse(User.objects.filter(username='otro').exists())


class CheckinViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='caro', password=CLAVE)
        self.user.socio.dni = '33444555'
        self.user.socio.save()
        User.objects.create_user(username='recepcion', password=CLAVE, is_staff=True)

    def test_checkin_rapido_por_dni(self):
        self.client.login(username='recepcion', password=CLAVE)
        respuesta = self.client.post(
            reverse('socios:checkin_rapido'), {'dni': '33444555'}, follow=True
        )
        self.assertEqual(Asistencia.objects.filter(socio=self.user.socio).count(), 1)
        self.assertContains(respuesta, 'Check-in')

    def test_checkin_rapido_dni_inexistente(self):
        self.client.login(username='recepcion', password=CLAVE)
        respuesta = self.client.post(
            reverse('socios:checkin_rapido'), {'dni': '99999999'}, follow=True
        )
        self.assertContains(respuesta, 'No se encontró')

    def test_recepcion_busca_por_nombre(self):
        self.client.login(username='recepcion', password=CLAVE)
        respuesta = self.client.get(reverse('socios:recepcion'), {'q': 'caro'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'caro')


class CommandTests(TestCase):
    def test_command_crea_y_no_duplica(self):
        User.objects.create_user(username='uno', password=CLAVE)
        User.objects.create_user(username='dos', password=CLAVE)
        call_command('crear_cuotas_y_revisiones', anio=2031, mes=3)
        self.assertEqual(Cuota.objects.filter(anio=2031, mes=3).count(), 2)
        call_command('crear_cuotas_y_revisiones', anio=2031, mes=3)
        self.assertEqual(Cuota.objects.filter(anio=2031, mes=3).count(), 2)