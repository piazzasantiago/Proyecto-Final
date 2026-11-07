"""
Tests del cálculo de stock de productos (productos/stock.py).

Clases de tests:
    AnotarStockTests             (5)  la fórmula stock_inicial + recolectado − descartado − salidas
                                      y que el queryset no use GROUP BY
    ListadoProductosStockTests   (1)  el listado de la API devuelve ese mismo stock

El stock se calcula en la base de datos para todo el listado. Estos tests fijan
dos cosas: que los números sean correctos (solo cuentan los registros
finalizados) y que las tres sumas sean subconsultas. Con un JOIN + GROUP BY el
listado de productos y el panel se volvían lentos a medida que crecía el
historial de recolecciones.

Total: 6 tests
"""

import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from descartes.models import Descarte, LineaDescarte
from galpones.models import Galpon
from recolecciones.models import LineaRecoleccion, Recoleccion
from salidas.models import LineaSalida, Salida
from usuarios.models import Usuario

from .models import Producto
from .stock import anotar_stock, stock_actual
from .tests import crear_usuario, token_de


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ahora():
    return timezone.now() - datetime.timedelta(hours=1)


def crear_galpon():
    return Galpon.objects.create(
        galpon="Galpón stock", latitud="0", longitud="0", superficie="1", capacidad=5000
    )


def recolectar(galpon, producto, cantidad, estado=Recoleccion.ESTADO_FINALIZADA):
    recoleccion = Recoleccion.objects.create(id_galpon=galpon, fecha=ahora(), estado=estado)
    LineaRecoleccion.objects.create(
        id_recoleccion=recoleccion, id_galpon=galpon, id_producto=producto, cantidad=cantidad
    )


def descartar(producto, cantidad, estado=Descarte.ESTADO_FINALIZADO,
              categoria=Descarte.CATEGORIA_STOCK):
    descarte = Descarte.objects.create(categoria=categoria, fecha=ahora(), estado=estado)
    LineaDescarte.objects.create(
        id_descarte=descarte, id_producto=producto, cantidad=Decimal(cantidad), motivo="Rotos"
    )


def sacar(producto, cantidad, estado=Salida.ESTADO_FINALIZADA):
    salida = Salida.objects.create(fecha=ahora(), estado=estado)
    LineaSalida.objects.create(id_salida=salida, id_producto=producto, cantidad=cantidad)


def por_nombre():
    return {p.producto: p for p in anotar_stock()}


# ---------------------------------------------------------------------------
# anotar_stock()
# ---------------------------------------------------------------------------

class AnotarStockTests(TestCase):

    def setUp(self):
        self.galpon = crear_galpon()
        self.a = Producto.objects.create(producto="Huevo A", stock_inicial=100)
        self.b = Producto.objects.create(producto="Huevo B", stock_inicial=7)

    def test_producto_sin_movimientos_queda_en_su_stock_inicial(self):
        p = por_nombre()["Huevo B"]
        self.assertEqual(p.stock_recolectado, 0)
        self.assertEqual(int(p.stock_descartado), 0)
        self.assertEqual(p.stock_salidas, 0)
        self.assertEqual(stock_actual(p), 7)

    def test_formula_con_todos_los_movimientos(self):
        recolectar(self.galpon, self.a, 30)
        recolectar(self.galpon, self.a, 20)
        descartar(self.a, 5)
        sacar(self.a, 10)
        p = por_nombre()["Huevo A"]
        self.assertEqual(p.stock_recolectado, 50)
        self.assertEqual(int(p.stock_descartado), 5)
        self.assertEqual(p.stock_salidas, 10)
        self.assertEqual(stock_actual(p), 100 + 50 - 5 - 10)

    def test_los_registros_pendientes_no_cuentan(self):
        recolectar(self.galpon, self.a, 40, estado=Recoleccion.ESTADO_PENDIENTE)
        descartar(self.a, 7, estado=Descarte.ESTADO_PENDIENTE)
        sacar(self.a, 3, estado=Salida.ESTADO_PENDIENTE)
        self.assertEqual(stock_actual(por_nombre()["Huevo A"]), 100)

    def test_cada_producto_suma_solo_lo_suyo_y_no_se_multiplican_las_filas(self):
        # Varias recolecciones, descartes y salidas de A, y movimientos de B:
        # ninguna suma debe repetirse por el cruce con las otras tablas.
        for _ in range(4):
            recolectar(self.galpon, self.a, 10)
            descartar(self.a, 1)
            sacar(self.a, 2)
        recolectar(self.galpon, self.b, 5)
        productos = por_nombre()
        self.assertEqual(stock_actual(productos["Huevo A"]), 100 + 40 - 4 - 8)
        self.assertEqual(stock_actual(productos["Huevo B"]), 7 + 5)

    def test_el_queryset_no_agrupa(self):
        # Las sumas son subconsultas. Si alguien vuelve a un JOIN con Sum, el
        # queryset pasa a tener GROUP BY y el listado se vuelve lento con el
        # historial completo.
        self.assertIsNone(anotar_stock().query.group_by)


class ListadoProductosStockTests(TestCase):
    """El listado de la API devuelve el mismo stock que anotar_stock()."""

    def test_stock_actual_en_el_listado(self):
        galpon = crear_galpon()
        producto = Producto.objects.create(producto="Huevo A", stock_inicial=100)
        recolectar(galpon, producto, 50)
        descartar(producto, 5)
        sacar(producto, 10)
        client = APIClient()
        token_de(client, crear_usuario("adminstk", rol=Usuario.ROL_ADMINISTRADOR))
        resp = client.get("/api/productos/")
        self.assertEqual(resp.status_code, 200)
        fila = resp.data["results"][0]
        self.assertEqual(fila["stock_recolectado"], 50)
        self.assertEqual(fila["stock_actual"], 135)
