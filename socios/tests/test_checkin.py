"""Tests de las reglas del check-in (avisos sin bloqueo, creación on-demand)."""
from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from socios.models import Asistencia, Cuota, RevisionMedica, Socio
from socios.services import hacer_checkin

LUNES = timezone.make_aware(datetime(2026, 11, 9, 10, 0))
MARTES = timezone.make_aware(datetime(2026, 11, 10, 10, 0))
MIERCOLES = timezone.make_aware(datetime(2026, 11, 11, 10, 0))


class CheckinTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sofi', password='clave12345')
        self.socio = self.user.socio
        # Limpiamos lo generado por las señales para controlar el escenario.
        Cuota.objects.all().delete()
        RevisionMedica.objects.all().delete()
        Asistencia.objects.all().delete()

    def _asistencia_en(self, momento):
        asistencia = Asistencia.objects.create(socio=self.socio)
        # auto_now_add no permite setear la fecha al crear; se actualiza aparte.
        Asistencia.objects.filter(pk=asistencia.pk).update(fecha_hora=momento)

    def _texto_avisos(self, avisos):
        return ' '.join(avisos).lower()

    def test_crea_cuota_y_revision_on_demand_y_avisa(self):
        self.assertEqual(Cuota.objects.count(), 0)
        _, avisos = hacer_checkin(self.socio, momento=LUNES)
        self.assertTrue(Cuota.objects.filter(socio=self.socio, anio=2026, mes=11).exists())
        self.assertTrue(RevisionMedica.objects.filter(socio=self.socio, anio=2026, mes=11).exists())
        self.assertEqual(self.socio.asistencias.count(), 1)
        texto = self._texto_avisos(avisos)
        self.assertIn('cuota impaga', texto)
        self.assertIn('revisión médica', texto)

    def test_sin_avisos_si_cuota_pagada_y_revision_apta(self):
        hacer_checkin(self.socio, momento=LUNES)
        self.socio.cuotas.get(anio=2026, mes=11).marcar_pagada()
        self.socio.revisiones.get(anio=2026, mes=11).marcar_apto()
        _, avisos = hacer_checkin(self.socio, momento=MARTES)
        self.assertEqual(avisos, [])

    def test_plan_dias_avisa_exceso(self):
        self.socio.plan = Socio.Plan.DIAS
        self.socio.dias_por_semana = 2
        self.socio.save()
        self._asistencia_en(LUNES)
        self._asistencia_en(MARTES)
        _, avisos = hacer_checkin(self.socio, momento=MIERCOLES)
        self.assertIn('exceso de plan', self._texto_avisos(avisos))

    def test_plan_dias_no_avisa_dentro_del_limite(self):
        self.socio.plan = Socio.Plan.DIAS
        self.socio.dias_por_semana = 3
        self.socio.save()
        self._asistencia_en(LUNES)
        self._asistencia_en(MARTES)
        _, avisos = hacer_checkin(self.socio, momento=MIERCOLES)
        self.assertNotIn('exceso de plan', self._texto_avisos(avisos))

    def test_varias_visitas_mismo_dia_cuentan_uno(self):
        self.socio.plan = Socio.Plan.DIAS
        self.socio.dias_por_semana = 1
        self.socio.save()
        hacer_checkin(self.socio, momento=LUNES)
        _, avisos = hacer_checkin(self.socio, momento=MIERCOLES.replace(hour=18))
        # Lunes (1 día) + miércoles (1 día) = 2 días > plan de 1 → aviso.
        self.assertIn('exceso de plan', self._texto_avisos(avisos))
        # Pero dos check-ins el mismo día siguen contando 1 solo día:
        hacer_checkin(self.socio, momento=LUNES.replace(hour=20))
        from socios.services import dias_usados_en_semana
        self.assertEqual(dias_usados_en_semana(self.socio, LUNES.replace(hour=20)), 2)