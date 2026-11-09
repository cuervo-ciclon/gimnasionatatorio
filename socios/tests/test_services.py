"""Tests de generación mensual y on-demand de cuotas y revisiones."""
from django.contrib.auth.models import User
from django.test import TestCase

from socios.models import Cuota, RevisionMedica
from socios.services import asegurar_cuota, asegurar_revision, generar_cuotas_y_revisiones


class GeneracionMensualTests(TestCase):
    def setUp(self):
        self.activo = User.objects.create_user(username='activo', password='clave12345').socio
        self.inactivo = User.objects.create_user(username='inactivo', password='clave12345').socio
        self.inactivo.activo = False
        self.inactivo.save()

    def test_genera_solo_para_socios_activos(self):
        cuotas, revisiones = generar_cuotas_y_revisiones(anio=2027, mes=1)
        self.assertEqual(cuotas, 1)
        self.assertEqual(revisiones, 1)
        self.assertTrue(Cuota.objects.filter(socio=self.activo, anio=2027, mes=1).exists())
        self.assertFalse(Cuota.objects.filter(socio=self.inactivo, anio=2027, mes=1).exists())

    def test_es_idempotente(self):
        generar_cuotas_y_revisiones(anio=2027, mes=1)
        cuotas, revisiones = generar_cuotas_y_revisiones(anio=2027, mes=1)
        self.assertEqual((cuotas, revisiones), (0, 0))
        self.assertEqual(Cuota.objects.filter(anio=2027, mes=1).count(), 1)
        self.assertEqual(RevisionMedica.objects.filter(anio=2027, mes=1).count(), 1)

    def test_no_pisa_registros_ya_pagados_o_aptos(self):
        cuota = asegurar_cuota(self.activo, 2027, mes=1)
        cuota.marcar_pagada()
        generar_cuotas_y_revisiones(anio=2027, mes=1)
        cuota.refresh_from_db()
        self.assertTrue(cuota.pagada)

    def test_usa_mes_actual_si_no_recibe_argumentos(self):
        from socios.services import mes_actual
        generar_cuotas_y_revisiones()
        anio, mes = mes_actual()
        self.assertTrue(Cuota.objects.filter(socio=self.activo, anio=anio, mes=mes).exists())