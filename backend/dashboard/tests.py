"""Panel principal: /api/dashboard/resumen/.

    ResumenVacioTests      una granja sin movimientos no rompe la pantalla
    ResumenTests           indicadores, producción, stock y alertas
    ResumenOperarioTests   el operario solo ve lo de sus galpones asignados
    PermisosTests          hace falta sesión iniciada
"""

import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from alertas.tests import (
    cliente_de,
    crear_galpon,
    crear_lote,
    crear_recoleccion,
    crear_usuario,
    momento,
)
from galpones.models import Galpon, UsuarioDelGalpon
from lotes.models import Lote
from productos.models import Producto
from recolecciones.models import Recoleccion
from salidas.models import LineaSalida, Salida
from usuarios.models import Usuario

URL = "/api/dashboard/resumen/"


class ResumenVacioTests(TestCase):
    def setUp(self):
        self.client = cliente_de(crear_usuario("admin_dash_vacio", Usuario.ROL_ADMINISTRADOR))

    def test_responde_con_todo_en_cero(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["fecha"], timezone.localdate().isoformat())
        self.assertEqual(datos["huevos_hoy"], 0)
        self.assertIsNone(datos["postura_hoy"])
        self.assertIsNone(datos["variacion_huevos"])
        self.assertEqual(datos["galpones_activos"], 0)
        self.assertEqual(datos["alertas_pendientes"], 0)
        self.assertEqual(datos["alertas"], [])
        self.assertEqual(datos["stock_productos"], {"total": 0, "items": []})

    def test_la_produccion_trae_una_semana_de_dias(self):
        produccion = self.client.get(URL).data["produccion"]
        self.assertEqual(len(produccion), 7)
        self.assertEqual(produccion[-1]["fecha"], timezone.localdate().isoformat())
        self.assertEqual({dia["huevos"] for dia in produccion}, {0})


class ResumenTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.ayer = self.hoy - datetime.timedelta(days=1)
        self.admin = crear_usuario("admin_dash", Usuario.ROL_ADMINISTRADOR)
        self.galpon = crear_galpon("Galpón 1")
        self.vacio = crear_galpon("Galpón 2")
        self.inactivo = crear_galpon("Galpón 3")
        self.inactivo.estado = Galpon.ESTADO_INACTIVO
        self.inactivo.save()
        self.lote = crear_lote(self.galpon, gallinas=100)
        self.producto = Producto.objects.create(producto="Huevo Nº1", stock_inicial=1000)
        crear_recoleccion(self.lote, self.ayer, 80, self.producto)
        crear_recoleccion(self.lote, self.hoy, 90, self.producto)
        self.client = cliente_de(self.admin)

    def test_huevos_de_hoy_y_variacion_contra_ayer(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["huevos_hoy"], 90)
        self.assertEqual(datos["huevos_ayer"], 80)
        self.assertEqual(datos["variacion_huevos"], 12.5)

    def test_postura_del_dia_y_variacion_en_puntos(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["postura_hoy"], 90.0)
        self.assertEqual(datos["postura_ayer"], 80.0)
        self.assertEqual(datos["variacion_postura"], 10.0)

    def test_galpones_en_produccion_sobre_los_activos(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["galpones_activos"], 2)  # el inactivo no cuenta
        self.assertEqual(datos["galpones_en_produccion"], 1)

    def test_la_produccion_del_grafico_tiene_los_dos_dias(self):
        produccion = self.client.get(URL).data["produccion"]
        por_fecha = {dia["fecha"]: dia["huevos"] for dia in produccion}
        self.assertEqual(por_fecha[self.hoy.isoformat()], 90)
        self.assertEqual(por_fecha[self.ayer.isoformat()], 80)

    def test_las_recolecciones_pendientes_no_suman(self):
        crear_recoleccion(
            self.lote, self.hoy, 500, self.producto, estado=Recoleccion.ESTADO_PENDIENTE
        )
        self.assertEqual(self.client.get(URL).data["huevos_hoy"], 90)

    def test_stock_de_productos_con_su_porcentaje(self):
        otro = Producto.objects.create(producto="Huevo Nº2", stock_inicial=500)
        datos = self.client.get(URL).data["stock_productos"]
        # Nº1: 1000 iniciales + 170 recolectados; Nº2: 500.
        self.assertEqual(datos["total"], 1670)
        por_nombre = {item["producto"]: item for item in datos["items"]}
        self.assertEqual(por_nombre["Huevo Nº1"]["stock"], 1170)
        self.assertEqual(por_nombre[otro.producto]["stock"], 500)
        self.assertEqual(por_nombre["Huevo Nº1"]["porcentaje"], 70.1)

    def test_el_stock_descuenta_las_salidas_finalizadas(self):
        salida = Salida.objects.create(fecha=momento(self.hoy), estado=Salida.ESTADO_FINALIZADA)
        LineaSalida.objects.create(id_salida=salida, id_producto=self.producto, cantidad=170)
        self.assertEqual(self.client.get(URL).data["stock_productos"]["total"], 1000)

    def test_un_producto_inactivo_sin_stock_no_aparece(self):
        Producto.objects.create(producto="Huevo viejo", estado=Producto.ESTADO_INACTIVO)
        nombres = {i["producto"] for i in self.client.get(URL).data["stock_productos"]["items"]}
        self.assertNotIn("Huevo viejo", nombres)

    def test_un_producto_inactivo_con_stock_sigue_apareciendo(self):
        Producto.objects.create(
            producto="Huevo viejo", estado=Producto.ESTADO_INACTIVO, stock_inicial=30
        )
        items = self.client.get(URL).data["stock_productos"]["items"]
        self.assertIn("Huevo viejo", {i["producto"] for i in items})

    def test_trae_las_alertas_y_cuantas_quedan_pendientes(self):
        # Con 10.000 gallinas, los 90 huevos de hoy son una postura bajísima:
        # la alerta se genera al pedir el resumen.
        self.lote.cantidad_inicial = 10000
        self.lote.save()

        datos = self.client.get(URL).data
        self.assertEqual(datos["alertas_pendientes"], 1)
        alerta = datos["alertas"][0]
        self.assertEqual(alerta["clave"], "postura_baja")
        self.assertEqual(alerta["estado"], "P")
        self.assertIn(self.lote.codigo, alerta["descripcion"])


class ResumenOperarioTests(TestCase):
    """Lo que ve el operario queda limitado a sus galpones asignados (F-32)."""

    def setUp(self):
        self.hoy = timezone.localdate()
        self.operario = crear_usuario("operario_dash", Usuario.ROL_OPERARIO)
        self.mio = crear_galpon("Galpón mío")
        self.ajeno = crear_galpon("Galpón ajeno")
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.mio)
        self.lote_mio = crear_lote(self.mio, gallinas=100)
        self.lote_ajeno = crear_lote(self.ajeno, gallinas=100)
        self.producto = Producto.objects.create(producto="Huevo Nº1", stock_inicial=100)
        crear_recoleccion(self.lote_mio, self.hoy, 90, self.producto)
        crear_recoleccion(self.lote_ajeno, self.hoy, 20, self.producto)
        self.client = cliente_de(self.operario)

    def test_solo_cuenta_los_huevos_de_sus_galpones(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["huevos_hoy"], 90)
        self.assertEqual(datos["postura_hoy"], 90.0)

    def test_solo_cuenta_sus_galpones(self):
        datos = self.client.get(URL).data
        self.assertEqual(datos["galpones_activos"], 1)
        self.assertEqual(datos["galpones_en_produccion"], 1)

    def test_solo_ve_las_alertas_de_sus_galpones(self):
        datos = self.client.get(URL).data
        # La postura baja la tiene el lote ajeno (20 de 100 gallinas).
        self.assertEqual(datos["alertas_pendientes"], 0)
        self.assertEqual(datos["alertas"], [])

    def test_el_stock_de_productos_es_el_de_toda_la_granja(self):
        datos = self.client.get(URL).data["stock_productos"]
        self.assertEqual(datos["total"], 210)  # 100 iniciales + 90 + 20


class PermisosTests(TestCase):
    def test_sin_sesion_no_se_puede(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)

    def test_los_tres_roles_pueden_entrar(self):
        for nombre, rol in (
            ("admin_perm_dash", Usuario.ROL_ADMINISTRADOR),
            ("operario_perm_dash", Usuario.ROL_OPERARIO),
            ("consulta_perm_dash", Usuario.ROL_CONSULTA),
        ):
            with self.subTest(rol=rol):
                self.assertEqual(cliente_de(crear_usuario(nombre, rol)).get(URL).status_code, 200)
