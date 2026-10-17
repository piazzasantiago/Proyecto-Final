"""
Tests del módulo Salidas de productos.

Una salida saca productos (huevos) de la granja, por ejemplo cuando un camión
se lleva los destinados a la venta:
  - Pendiente (P): editable y borrable, no toca el stock.
  - Finalizada (F): de solo lectura; descuenta de cada producto la cantidad de
    sus líneas.

Clases:
  - BuscarSalidaTests           listado y filtros (fechas, estado, producto)
  - NuevaSalidaTests            crear con líneas y validaciones
  - FechaSalidaTests            la fecha no puede ser futura
  - ModificarSalidaTests        editar salida pendiente
  - BorrarSalidaTests           borrar salida
  - FinalizarSalidaTests        finalizar y verificar stock
  - StockProductoSalidaTests    el stock de Productos resta las salidas finalizadas
  - PermisosSalidaTests         matriz rol × operación
"""

import datetime
from datetime import timezone as dt_timezone

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from descartes.models import Descarte, LineaDescarte
from galpones.models import Galpon
from productos.models import Producto
from recolecciones.models import LineaRecoleccion, Recoleccion
from usuarios.models import Usuario

from .models import LineaSalida, Salida


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_usuario(usuario, rol, dni):
    u = Usuario(
        usuario=usuario, email=f"{usuario}@test.com",
        nombre="Test", apellido=usuario.capitalize(), dni=dni, rol=rol,
    )
    u.set_password("pass1234")
    u.save()
    return u


def make_admin():
    return make_usuario("admin", Usuario.ROL_ADMINISTRADOR, "11111111")


def make_operario():
    return make_usuario("operario", Usuario.ROL_OPERARIO, "22222222")


def make_consulta():
    return make_usuario("consulta", Usuario.ROL_CONSULTA, "33333333")


def make_galpon(nombre="Galpón 1", **kwargs):
    defaults = dict(
        galpon=nombre, capacidad=1000, superficie=200,
        latitud=-26.8, longitud=-65.2,
    )
    defaults.update(kwargs)
    return Galpon.objects.create(**defaults)


def make_producto(nombre="Huevo Nº1", stock_inicial=1000, **kwargs):
    defaults = dict(producto=nombre, stock_inicial=stock_inicial)
    defaults.update(kwargs)
    return Producto.objects.create(**defaults)


def fecha(dia, hora=10):
    """Datetime aware (UTC) del día indicado de agosto de 2026."""
    return datetime.datetime(2026, 8, dia, hora, 0, tzinfo=dt_timezone.utc)


def make_salida(estado=Salida.ESTADO_PENDIENTE, dia=9, **kwargs):
    defaults = dict(fecha=fecha(dia), estado=estado, observaciones="")
    defaults.update(kwargs)
    return Salida.objects.create(**defaults)


def add_linea(salida, producto, cantidad=5):
    return LineaSalida.objects.create(
        id_salida=salida, id_producto=producto, cantidad=cantidad
    )


def auth(client, user):
    r = client.post(
        "/api/auth/login/",
        {"usuario": user.usuario, "password": "pass1234"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def payload(lineas, **kwargs):
    base = dict(fecha="2026-08-09T10:00:00Z", observaciones="test", lineas=lineas)
    base.update(kwargs)
    return base


def linea(producto, cantidad=5):
    return {"id_producto": producto.pk, "cantidad": cantidad}


# ── Buscar ────────────────────────────────────────────────────────────────────

class BuscarSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_consulta())
        self.p1 = make_producto("Huevo Nº1")
        self.p2 = make_producto("Huevo Nº2")
        self.s1 = make_salida(dia=5)
        add_linea(self.s1, self.p1)
        self.s2 = make_salida(estado=Salida.ESTADO_FINALIZADA, dia=10)
        add_linea(self.s2, self.p2)
        add_linea(self.s2, self.p1)

    def ids(self, **params):
        resp = self.client.get("/api/salidas/", params)
        self.assertEqual(resp.status_code, 200)
        return {s["id_salida"] for s in resp.data["results"]}

    def test_listar(self):
        self.assertEqual(self.ids(), {self.s1.pk, self.s2.pk})

    def test_orden_de_la_mas_reciente_a_la_mas_antigua(self):
        resp = self.client.get("/api/salidas/")
        self.assertEqual(
            [s["id_salida"] for s in resp.data["results"]], [self.s2.pk, self.s1.pk]
        )

    def test_filtrar_por_estado(self):
        self.assertEqual(self.ids(estado="F"), {self.s2.pk})
        self.assertEqual(self.ids(estado="P"), {self.s1.pk})

    def test_filtrar_por_producto_sin_duplicar(self):
        self.assertEqual(self.ids(id_producto=self.p1.pk), {self.s1.pk, self.s2.pk})
        self.assertEqual(self.ids(id_producto=self.p2.pk), {self.s2.pk})

    def test_filtro_fecha_desde_y_hasta_inclusivos(self):
        self.assertEqual(self.ids(fecha_desde="2026-08-10"), {self.s2.pk})
        self.assertEqual(self.ids(fecha_hasta="2026-08-05"), {self.s1.pk})
        self.assertEqual(
            self.ids(fecha_desde="2026-08-05", fecha_hasta="2026-08-10"),
            {self.s1.pk, self.s2.pk},
        )

    def test_rango_invertido_no_devuelve_nada(self):
        self.assertEqual(self.ids(fecha_desde="2026-08-10", fecha_hasta="2026-08-05"), set())

    def test_fecha_invalida_400(self):
        resp = self.client.get("/api/salidas/", {"fecha_desde": "no-es-fecha"})
        self.assertEqual(resp.status_code, 400)

    def test_filtros_combinados(self):
        self.assertEqual(
            self.ids(estado="F", id_producto=self.p1.pk, fecha_desde="2026-08-10"),
            {self.s2.pk},
        )
        self.assertEqual(self.ids(estado="P", id_producto=self.p2.pk), set())

    def test_detalle_con_lineas_y_conteo(self):
        resp = self.client.get(f"/api/salidas/{self.s2.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["items_count"], 2)
        self.assertEqual(len(resp.data["lineas"]), 2)
        self.assertEqual(resp.data["estado_display"], "Finalizada")
        nombres = {l["producto_nombre"] for l in resp.data["lineas"]}
        self.assertEqual(nombres, {"Huevo Nº1", "Huevo Nº2"})

    def test_detalle_inexistente_404(self):
        self.assertEqual(self.client.get("/api/salidas/9999/").status_code, 404)


# ── Nueva ─────────────────────────────────────────────────────────────────────

class NuevaSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        auth(self.client, self.admin)
        self.p = make_producto("Huevo Nº1", stock_inicial=1000)
        self.p2 = make_producto("Huevo Nº2", stock_inicial=500)

    def post(self, lineas, **kwargs):
        return self.client.post("/api/salidas/", payload(lineas, **kwargs), format="json")

    def test_crear_exitoso(self):
        resp = self.post([linea(self.p, 200), linea(self.p2, 50)])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["estado"], "P")
        self.assertEqual(len(resp.data["lineas"]), 2)
        self.assertEqual(Salida.objects.get().lineas.count(), 2)

    def test_registra_el_usuario_que_la_cargo(self):
        resp = self.post([linea(self.p)])
        self.assertEqual(resp.data["usuario"]["usuario"], "admin")
        self.assertEqual(Salida.objects.get().id_usuario, self.admin)

    def test_el_usuario_y_el_estado_no_se_toman_del_cliente(self):
        otro = make_operario()
        resp = self.post([linea(self.p)], id_usuario=otro.pk, estado="F")
        self.assertEqual(resp.data["usuario"]["usuario"], "admin")
        self.assertEqual(resp.data["estado"], "P")

    def test_no_toca_el_stock_hasta_finalizar(self):
        self.post([linea(self.p, 200)])
        resp = self.client.get(f"/api/productos/{self.p.pk}/")
        self.assertEqual(resp.data["stock_actual"], 1000)

    def test_sin_lineas(self):
        resp = self.post([])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("lineas", resp.data)

    def test_producto_repetido(self):
        resp = self.post([linea(self.p, 5), linea(self.p, 5)])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("repetido", str(resp.data["lineas"]))

    def test_producto_inactivo_rechazado(self):
        Producto.objects.filter(pk=self.p.pk).update(estado=Producto.ESTADO_INACTIVO)
        resp = self.post([linea(self.p)])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("inactivo", str(resp.data["lineas"]))

    def test_producto_inexistente(self):
        resp = self.client.post(
            "/api/salidas/",
            payload([{"id_producto": 9999, "cantidad": 1}]),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_linea_sin_producto(self):
        resp = self.client.post(
            "/api/salidas/", payload([{"cantidad": 1}]), format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_cantidad_cero_negativa_decimal_o_sin_numero(self):
        for cantidad in [0, -3, "abc", "1.5"]:
            resp = self.post([linea(self.p, cantidad)])
            self.assertEqual(resp.status_code, 400, cantidad)

    def test_cantidad_enorme_es_400_y_no_500(self):
        resp = self.post([linea(self.p, 99999999999999)])
        self.assertEqual(resp.status_code, 400)

    def test_cantidad_sobre_el_tope_rechazada(self):
        Producto.objects.filter(pk=self.p.pk).update(stock_inicial=5_000_000)
        self.assertEqual(self.post([linea(self.p, 1_000_001)]).status_code, 400)
        self.assertEqual(self.post([linea(self.p, 1_000_000)]).status_code, 201)

    def test_stock_insuficiente_al_crear(self):
        resp = self.post([linea(self.p, 1001)])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Stock insuficiente", str(resp.data["lineas"]))
        self.assertIn("despachar", str(resp.data["lineas"]))
        self.assertIn("hay 1000", str(resp.data["lineas"]))

    def test_cantidad_igual_al_stock_es_valida(self):
        self.assertEqual(self.post([linea(self.p, 1000)]).status_code, 201)

    def test_observaciones_500_validas_y_501_rechazadas(self):
        self.assertEqual(self.post([linea(self.p)], observaciones="a" * 500).status_code, 201)
        resp = self.post([linea(self.p2)], observaciones="a" * 501,
                         fecha="2026-08-10T10:00:00Z")
        self.assertEqual(resp.status_code, 400)

    def test_observaciones_opcionales(self):
        resp = self.client.post(
            "/api/salidas/",
            dict(fecha="2026-08-09T10:00:00Z", lineas=[linea(self.p)]),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)


class FechaSalidaTests(TestCase):
    """La fecha de la salida no puede ser posterior al momento actual."""

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_producto()

    def crear(self, momento):
        return self.client.post(
            "/api/salidas/",
            payload([linea(self.p, 1)], fecha=momento.isoformat()),
            format="json",
        )

    def test_fecha_de_manana_rechazada(self):
        resp = self.crear(timezone.now() + datetime.timedelta(days=1))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("fecha", resp.data)

    def test_hora_futura_del_mismo_dia_rechazada(self):
        self.assertEqual(self.crear(timezone.now() + datetime.timedelta(hours=1)).status_code, 400)

    def test_fecha_pasada_valida(self):
        self.assertEqual(self.crear(timezone.now() - datetime.timedelta(days=1)).status_code, 201)

    def test_fecha_obligatoria(self):
        resp = self.client.post(
            "/api/salidas/", dict(lineas=[linea(self.p, 1)]), format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("fecha", resp.data)

    def test_no_se_puede_editar_a_fecha_futura(self):
        creada = self.crear(timezone.now() - datetime.timedelta(days=1))
        resp = self.client.patch(
            f"/api/salidas/{creada.data['id_salida']}/",
            {"fecha": (timezone.now() + datetime.timedelta(days=1)).isoformat()},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


# ── Modificar ─────────────────────────────────────────────────────────────────

class ModificarSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        auth(self.client, self.admin)
        self.p = make_producto("Huevo Nº1", stock_inicial=1000)
        self.p2 = make_producto("Huevo Nº2", stock_inicial=500)
        self.s = make_salida()
        add_linea(self.s, self.p, 100)
        self.url = f"/api/salidas/{self.s.pk}/"

    def test_editar_observaciones_conserva_lineas(self):
        resp = self.client.patch(self.url, {"observaciones": "nueva"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.s.refresh_from_db()
        self.assertEqual(self.s.observaciones, "nueva")
        self.assertEqual(self.s.lineas.count(), 1)

    def test_modificar_cantidad_de_una_linea(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.p, 300)]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.s.lineas.get().cantidad, 300)

    def test_agregar_y_quitar_lineas(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.p2, 40)]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([l.id_producto_id for l in self.s.lineas.all()], [self.p2.pk])

    def test_no_puede_quedar_sin_lineas(self):
        resp = self.client.patch(self.url, {"lineas": []}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.s.lineas.count(), 1)

    def test_producto_repetido_al_editar(self):
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.p, 1), linea(self.p, 2)]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_stock_insuficiente_al_editar(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.p, 5000)]}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.s.lineas.get().cantidad, 100)

    def test_conserva_producto_desactivado(self):
        Producto.objects.filter(pk=self.p.pk).update(estado=Producto.ESTADO_INACTIVO)
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.p, 200), linea(self.p2, 1)]}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_no_agrega_producto_inactivo_nuevo(self):
        Producto.objects.filter(pk=self.p2.pk).update(estado=Producto.ESTADO_INACTIVO)
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.p, 100), linea(self.p2, 1)]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_el_estado_y_el_usuario_no_se_editan(self):
        otro = make_operario()
        resp = self.client.patch(self.url, {"estado": "F", "id_usuario": otro.pk}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.s.refresh_from_db()
        self.assertEqual(self.s.estado, Salida.ESTADO_PENDIENTE)
        self.assertIsNone(self.s.id_usuario)

    def test_modificar_no_cambia_quien_la_cargo(self):
        self.s.id_usuario = self.admin
        self.s.save(update_fields=["id_usuario"])
        otro = make_operario()
        auth(self.client, otro)
        resp = self.client.patch(self.url, {"observaciones": "editada por otro"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["usuario"]["id_usuario"], self.admin.pk)

    def test_salida_finalizada_no_se_edita(self):
        Salida.objects.filter(pk=self.s.pk).update(estado=Salida.ESTADO_FINALIZADA)
        resp = self.client.patch(self.url, {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Salida finalizada. No se puede editar.", str(resp.data))

    def test_inexistente_404(self):
        resp = self.client.patch("/api/salidas/9999/", {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ── Borrar ────────────────────────────────────────────────────────────────────

class BorrarSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_producto()

    def test_borrar_pendiente_y_sus_lineas(self):
        s = make_salida()
        add_linea(s, self.p)
        resp = self.client.delete(f"/api/salidas/{s.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Salida.objects.filter(pk=s.pk).exists())
        self.assertFalse(LineaSalida.objects.filter(id_salida_id=s.pk).exists())

    def test_finalizada_no_se_borra(self):
        s = make_salida(estado=Salida.ESTADO_FINALIZADA)
        add_linea(s, self.p)
        resp = self.client.delete(f"/api/salidas/{s.pk}/")
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Salida.objects.filter(pk=s.pk).exists())

    def test_inexistente_404(self):
        self.assertEqual(self.client.delete("/api/salidas/9999/").status_code, 404)


# ── Finalizar ─────────────────────────────────────────────────────────────────

class FinalizarSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_producto("Huevo Nº1", stock_inicial=1000)
        self.s = make_salida()
        add_linea(self.s, self.p, 300)

    def finalizar(self, salida=None):
        salida = salida or self.s
        return self.client.post(f"/api/salidas/{salida.pk}/finalizar/")

    def stock(self, producto=None):
        producto = producto or self.p
        return self.client.get(f"/api/productos/{producto.pk}/").data["stock_actual"]

    def test_finalizar_exitoso(self):
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "F")
        self.assertEqual(resp.data["estado_display"], "Finalizada")

    def test_persiste_en_la_base(self):
        self.finalizar()
        self.s.refresh_from_db()
        self.assertEqual(self.s.estado, Salida.ESTADO_FINALIZADA)

    def test_baja_el_stock_del_producto(self):
        self.assertEqual(self.stock(), 1000)
        self.finalizar()
        self.assertEqual(self.stock(), 700)

    def test_doble_finalizacion_es_409_y_no_descuenta_dos_veces(self):
        self.finalizar()
        self.assertEqual(self.finalizar().status_code, 409)
        self.assertEqual(self.stock(), 700)

    def test_stock_insuficiente_al_finalizar_no_cambia_nada(self):
        # Entre la carga y la finalización otra salida consumió el stock.
        otra = make_salida(dia=10)
        add_linea(otra, self.p, 800)
        self.assertEqual(self.finalizar(otra).status_code, 200)
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Stock insuficiente", str(resp.data))
        self.s.refresh_from_db()
        self.assertEqual(self.s.estado, Salida.ESTADO_PENDIENTE)
        self.assertEqual(self.stock(), 200)

    def test_con_varias_lineas_basta_una_sin_stock(self):
        p2 = make_producto("Huevo Nº2", stock_inicial=10)
        add_linea(self.s, p2, 50)
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Huevo Nº2", str(resp.data))
        self.assertEqual(self.stock(), 1000)

    def test_descuenta_cada_producto(self):
        p2 = make_producto("Huevo Nº2", stock_inicial=100)
        add_linea(self.s, p2, 25)
        self.finalizar()
        self.assertEqual(self.stock(p2), 75)

    def test_salida_finalizada_no_se_modifica(self):
        self.finalizar()
        resp = self.client.patch(f"/api/salidas/{self.s.pk}/", {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_inexistente_404(self):
        self.assertEqual(self.client.post("/api/salidas/9999/finalizar/").status_code, 404)


# ── Stock de productos ────────────────────────────────────────────────────────

class StockProductoSalidaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.p = make_producto("Huevo Nº1", stock_inicial=1000)

    def datos(self, producto=None):
        producto = producto or self.p
        return self.client.get(f"/api/productos/{producto.pk}/").data

    def recoleccion(self, cantidad, producto=None, estado=Recoleccion.ESTADO_FINALIZADA, dia=9):
        rec = Recoleccion.objects.create(
            id_galpon=self.g, fecha=fecha(dia), estado=estado,
        )
        LineaRecoleccion.objects.create(
            id_recoleccion=rec, id_galpon=self.g,
            id_producto=producto or self.p, cantidad=cantidad,
        )
        return rec

    def descarte_stock(self, cantidad, estado=Descarte.ESTADO_FINALIZADO):
        d = Descarte.objects.create(
            categoria=Descarte.CATEGORIA_STOCK, fecha=fecha(9), estado=estado
        )
        LineaDescarte.objects.create(
            id_descarte=d, id_producto=self.p, cantidad=cantidad, motivo="rotos"
        )
        return d

    def test_sin_salidas_el_stock_es_el_inicial(self):
        d = self.datos()
        self.assertEqual(d["stock_salidas"], 0)
        self.assertEqual(d["stock_actual"], 1000)

    def test_las_pendientes_no_restan(self):
        s = make_salida()
        add_linea(s, self.p, 400)
        self.assertEqual(self.datos()["stock_actual"], 1000)

    def test_las_finalizadas_restan_y_se_ven_en_stock_salidas(self):
        s = make_salida(estado=Salida.ESTADO_FINALIZADA)
        add_linea(s, self.p, 400)
        d = self.datos()
        self.assertEqual(d["stock_salidas"], 400)
        self.assertEqual(d["stock_actual"], 600)

    def test_suma_varias_salidas_finalizadas(self):
        for dia, cant in [(5, 100), (6, 150)]:
            s = make_salida(estado=Salida.ESTADO_FINALIZADA, dia=dia)
            add_linea(s, self.p, cant)
        self.assertEqual(self.datos()["stock_salidas"], 250)

    def test_separa_por_producto(self):
        p2 = make_producto("Huevo Nº2", stock_inicial=300)
        s = make_salida(estado=Salida.ESTADO_FINALIZADA)
        add_linea(s, self.p, 100)
        add_linea(s, p2, 20)
        self.assertEqual(self.datos()["stock_actual"], 900)
        self.assertEqual(self.datos(p2)["stock_actual"], 280)

    def test_la_formula_completa(self):
        # inicial 1000 + recolectado 500 − descartado 30 − salidas 400
        self.recoleccion(500)
        self.descarte_stock(30)
        s = make_salida(estado=Salida.ESTADO_FINALIZADA)
        add_linea(s, self.p, 400)
        d = self.datos()
        self.assertEqual(d["stock_recolectado"], 500)
        self.assertEqual(d["stock_descartado"], 30)
        self.assertEqual(d["stock_salidas"], 400)
        self.assertEqual(d["stock_actual"], 1070)

    def test_el_listado_no_infla_las_sumas(self):
        # Varias recolecciones y varias salidas del mismo producto: si las
        # sumas se hicieran con JOIN, cada una multiplicaría a la otra.
        self.recoleccion(100, dia=5)
        self.recoleccion(200, dia=6)
        for dia, cant in [(7, 30), (8, 20)]:
            s = make_salida(estado=Salida.ESTADO_FINALIZADA, dia=dia)
            add_linea(s, self.p, cant)
        resp = self.client.get("/api/productos/")
        fila = next(p for p in resp.data["results"] if p["id_producto"] == self.p.pk)
        self.assertEqual(fila["stock_recolectado"], 300)
        self.assertEqual(fila["stock_salidas"], 50)
        self.assertEqual(fila["stock_actual"], 1250)

    def test_una_salida_ya_no_puede_superar_lo_que_dejo_un_descarte(self):
        self.descarte_stock(900)
        resp = self.client.post(
            "/api/salidas/", payload([linea(self.p, 200)]), format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hay 100", str(resp.data))

    def test_un_descarte_de_stock_ya_no_puede_superar_lo_que_dejo_una_salida(self):
        s = make_salida(estado=Salida.ESTADO_FINALIZADA)
        add_linea(s, self.p, 900)
        resp = self.client.post(
            "/api/descartes/",
            dict(
                categoria="S", fecha="2026-08-09T10:00:00Z",
                lineas=[{"id_producto": self.p.pk, "cantidad": "200", "motivo": "x"}],
            ),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hay 100", str(resp.data))

    def test_un_descarte_de_galpon_no_cambia_lo_que_hay_para_sacar(self):
        d = Descarte.objects.create(
            categoria=Descarte.CATEGORIA_GALPON, id_galpon=self.g,
            fecha=fecha(9), estado=Descarte.ESTADO_FINALIZADO,
        )
        LineaDescarte.objects.create(
            id_descarte=d, id_galpon=self.g, id_producto=self.p, cantidad=500, motivo="rotos"
        )
        resp = self.client.post(
            "/api/salidas/", payload([linea(self.p, 1000)]), format="json"
        )
        self.assertEqual(resp.status_code, 201)


# ── Permisos ──────────────────────────────────────────────────────────────────

class PermisosSalidaTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.operario = make_operario()
        self.consulta = make_consulta()
        self.p = make_producto()
        self.s = make_salida()
        add_linea(self.s, self.p, 10)

    def cliente(self, usuario=None):
        c = APIClient()
        if usuario:
            auth(c, usuario)
        return c

    def test_sin_token_401(self):
        c = self.cliente()
        self.assertEqual(c.get("/api/salidas/").status_code, 401)
        self.assertEqual(
            c.post("/api/salidas/", payload([linea(self.p)]), format="json").status_code, 401
        )

    def test_todos_los_roles_pueden_listar_y_ver_el_detalle(self):
        for u in (self.admin, self.operario, self.consulta):
            c = self.cliente(u)
            self.assertEqual(c.get("/api/salidas/").status_code, 200, u.usuario)
            self.assertEqual(c.get(f"/api/salidas/{self.s.pk}/").status_code, 200, u.usuario)

    def test_administrador_y_operario_pueden_crear(self):
        for u in (self.admin, self.operario):
            resp = self.cliente(u).post(
                "/api/salidas/", payload([linea(self.p, 1)]), format="json"
            )
            self.assertEqual(resp.status_code, 201, u.usuario)

    def test_administrador_y_operario_pueden_modificar(self):
        for u in (self.admin, self.operario):
            resp = self.cliente(u).patch(
                f"/api/salidas/{self.s.pk}/", {"observaciones": u.usuario}, format="json"
            )
            self.assertEqual(resp.status_code, 200, u.usuario)

    def test_administrador_y_operario_pueden_finalizar(self):
        for u in (self.admin, self.operario):
            s = make_salida()
            add_linea(s, self.p, 1)
            resp = self.cliente(u).post(f"/api/salidas/{s.pk}/finalizar/")
            self.assertEqual(resp.status_code, 200, u.usuario)

    def test_administrador_y_operario_pueden_eliminar(self):
        for u in (self.admin, self.operario):
            s = make_salida()
            add_linea(s, self.p, 1)
            resp = self.cliente(u).delete(f"/api/salidas/{s.pk}/")
            self.assertEqual(resp.status_code, 204, u.usuario)

    def test_consulta_solo_lee(self):
        c = self.cliente(self.consulta)
        self.assertEqual(
            c.post("/api/salidas/", payload([linea(self.p, 1)]), format="json").status_code, 403
        )
        self.assertEqual(
            c.patch(f"/api/salidas/{self.s.pk}/", {"observaciones": "x"}, format="json").status_code,
            403,
        )
        self.assertEqual(c.post(f"/api/salidas/{self.s.pk}/finalizar/").status_code, 403)
        self.assertEqual(c.delete(f"/api/salidas/{self.s.pk}/").status_code, 403)
        self.s.refresh_from_db()
        self.assertEqual(self.s.estado, Salida.ESTADO_PENDIENTE)
        self.assertEqual(self.s.observaciones, "")
