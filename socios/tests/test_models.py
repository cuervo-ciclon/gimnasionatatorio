"""Tests de modelos: señales, unicidades y marcado automático de fechas."""
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from socios.models import Asistencia, Cuota, RevisionMedica, Socio
from socios.services import asegurar_cuota, asegurar_revision, mes_actual


class SocioTests(TestCase):
    def test_usuario_nuevo_obtiene_socio_por_senal(self):
        user = User.objects.create_user(username='ana', password='clave12345')
        self.assertTrue(Socio.objects.filter(user=user).exists())
        self.assertTrue(user.socio.activo)

    def test_dni_unico(self):
        u1 = User.objects.create_user(username='a1', password='clave12345')
        u2 = User.objects.create_user(username='a2', password='clave12345')
        u1.socio.dni = '30111222'
        u1.socio.save()
        u2.socio.dni = '30111222'
        with self.assertRaises(IntegrityError):
            u2.socio.save()

    def test_solo_socios_activos_generan_registros_al_guardar(self):
        user = User.objects.create_user(username='baja', password='clave12345')
        socio = user.socio
        anio, mes = mes_actual()
        self.assertTrue(Cuota.objects.filter(socio=socio, anio=anio, mes=mes).exists())
        socio.activo = False
        socio.save()
        # Al reactivarse se vuelven a asegurar (sin duplicar).
        socio.activo = True
        socio.save()
        self.assertEqual(Cuota.objects.filter(socio=socio, anio=anio, mes=mes).count(), 1)


class CuotaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juan', password='clave12345')
        self.socio = self.user.socio

    def test_cuota_unica_por_periodo(self):
        Cuota.objects.create(socio=self.socio, anio=2026, mes=11)
        with self.assertRaises(IntegrityError):
            Cuota.objects.create(socio=self.socio, anio=2026, mes=11)

    def test_marcar_pagada_completa_fecha_pago(self):
        cuota = Cuota.objects.create(socio=self.socio, anio=2026, mes=11)
        self.assertFalse(cuota.pagada)
        self.assertIsNone(cuota.fecha_pago)
        cuota.marcar_pagada()
        cuota.refresh_from_db()
        self.assertTrue(cuota.pagada)
        self.assertIsNotNone(cuota.fecha_pago)

    def test_periodo_texto(self):
        cuota = Cuota.objects.create(socio=self.socio, anio=2026, mes=12)
        self.assertEqual(cuota.periodo, 'Diciembre 2026')


class RevisionMedicaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pepa', password='clave12345')
        self.socio = self.user.socio

    def test_revision_unica_por_periodo(self):
        RevisionMedica.objects.create(socio=self.socio, anio=2026, mes=11)
        with self.assertRaises(IntegrityError):
            RevisionMedica.objects.create(socio=self.socio, anio=2026, mes=11)

    def test_marcar_apto_completa_fecha_revision(self):
        revision = RevisionMedica.objects.create(socio=self.socio, anio=2026, mes=11)
        revision.marcar_apto()
        revision.refresh_from_db()
        self.assertTrue(revision.apto)
        self.assertIsNotNone(revision.fecha_revision)


class AsistenciaTests(TestCase):
    def test_str_y_orden(self):
        user = User.objects.create_user(username='lu', password='clave12345')
        Asistencia.objects.create(socio=user.socio)
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertIn('lu', str(user.socio))