"""
Tests del módulo Descartes (CU15 a CU19).

Un descarte tiene una categoría:
  - Galpón (G): estadístico; solo las líneas de gallinas (lote) descuentan del lote.
  - Stock  (S): sin galpón; descuenta stock de productos y de materias primas.

Clases:
  - BuscarDescarteTests          CU15: listado y filtros (fechas, categoría, estado)
  - NuevoDescarteGalponTests     CU16: crear descartes de galpón
  - NuevoDescarteStockTests      CU16: crear descartes de stock
  - FinalizarDescarteTests       CU17: finalizar → de solo lectura
  - FinalizarStockTests          CU17: el stock de productos y materias primas baja
  - ModificarDescarteTests       CU18: editar descarte pendiente
  - EliminarDescarteTests        CU19: borrar descarte
  - LineasDescarteTests          validaciones de líneas
  - PermisosDescarteTests        matriz rol × operación
  - DescarteLoteTests            descarte de gallinas → decrementa cantidad_actual del lote
"""

import datetime
from datetime import timezone
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from galpones.models import Galpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from productos.models import Producto
from recolecciones.models import LineaRecoleccion, Recoleccion
from usuarios.models import Usuario

from .models import Descarte, LineaDescarte


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


def make_galpon(**kwargs):
    defaults = dict(
        galpon="Galpón 1", capacidad=1000, superficie=200,
        latitud=-26.8, longitud=-65.2,
    )
    defaults.update(kwargs)
    return Galpon.objects.create(**defaults)


def make_lote(galpon, **kwargs):
    defaults = dict(
        id_galpon=galpon,
        fecha_ingreso="2026-01-01",
        cantidad_inicial=500,
        cantidad_actual=500,
        estado=Lote.ESTADO_PRODUCCION,
    )
    defaults.update(kwargs)
    return Lote.objects.create(**defaults)


def make_materia_prima(**kwargs):
    defaults = dict(
        materia_prima="Balanceado", unidad="kg",
        stock_minimo=10, stock_inicial=100,
    )
    defaults.update(kwargs)
    return MateriaPrima.objects.create(**defaults)


def make_producto(**kwargs):
    defaults = dict(producto="Huevo Nº1", stock_inicial=50)
    defaults.update(kwargs)
    return Producto.objects.create(**defaults)


def fecha(dia, hora=10):
    """Datetime aware (UTC) del día indicado de agosto de 2026."""
    return datetime.datetime(2026, 8, dia, hora, 0, tzinfo=timezone.utc)


def make_descarte(galpon=None, categoria=Descarte.CATEGORIA_GALPON, **kwargs):
    """Crea un descarte directo en la base. Los de stock no llevan galpón."""
    if categoria == Descarte.CATEGORIA_STOCK:
        galpon = None
    defaults = dict(
        categoria=categoria, id_galpon=galpon, fecha=fecha(9), observaciones="",
    )
    defaults.update(kwargs)
    return Descarte.objects.create(**defaults)


def add_linea(descarte, cantidad=5, motivo="test", **item):
    """Agrega una línea (id_materia_prima / id_producto / id_lote) al descarte."""
    return LineaDescarte.objects.create(
        id_descarte=descarte, id_galpon=descarte.id_galpon,
        cantidad=cantidad, motivo=motivo, **item,
    )


def auth(client, user):
    r = client.post(
        "/api/auth/login/",
        {"usuario": user.usuario, "password": "pass1234"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def payload_galpon(galpon, lineas, **kwargs):
    base = dict(
        categoria="G", id_galpon=galpon.pk,
        fecha="2026-08-09T10:00:00Z", observaciones="test", lineas=lineas,
    )
    base.update(kwargs)
    return base


def payload_stock(lineas, **kwargs):
    base = dict(
        categoria="S", fecha="2026-08-09T10:00:00Z", observaciones="", lineas=lineas,
    )
    base.update(kwargs)
    return base


# ── BuscarDescarteTests ────────────────────────────────────────────────────────

class BuscarDescarteTests(TestCase):
    """
    4 descartes:
      d1  G  galpón 1  Pendiente  9/ago
      d2  G  galpón 2  Pendiente  10/ago
      d3  G  galpón 1  Finalizado 12/ago
      d4  S  (sin galpón) Pendiente 10/ago
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g1 = make_galpon(galpon="G1")
        self.g2 = make_galpon(galpon="G2")
        self.mp = make_materia_prima()
        self.prod = make_producto()
        self.d1 = make_descarte(self.g1, fecha=fecha(9))
        self.d2 = make_descarte(self.g2, fecha=fecha(10))
        self.d3 = make_descarte(self.g1, fecha=fecha(12), estado=Descarte.ESTADO_FINALIZADO)
        self.d4 = make_descarte(categoria=Descarte.CATEGORIA_STOCK, fecha=fecha(10))
        for d in (self.d1, self.d2, self.d3):
            add_linea(d, id_materia_prima=self.mp)
        add_linea(self.d4, id_producto=self.prod)
        auth(self.client, self.admin)

    def _ids(self, r):
        return {d["id_descarte"] for d in r.data["results"]}

    def test_lista_todos(self):
        r = self.client.get("/api/descartes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["count"], 4)

    def test_filtro_por_categoria_galpon(self):
        r = self.client.get("/api/descartes/?categoria=G")
        self.assertEqual(self._ids(r), {self.d1.pk, self.d2.pk, self.d3.pk})

    def test_filtro_por_categoria_stock(self):
        r = self.client.get("/api/descartes/?categoria=S")
        self.assertEqual(self._ids(r), {self.d4.pk})

    def test_filtro_por_estado_pendiente(self):
        r = self.client.get("/api/descartes/?estado=P")
        self.assertEqual(self._ids(r), {self.d1.pk, self.d2.pk, self.d4.pk})

    def test_filtro_por_estado_finalizado(self):
        r = self.client.get("/api/descartes/?estado=F")
        self.assertEqual(self._ids(r), {self.d3.pk})

    def test_filtro_por_galpon(self):
        r = self.client.get(f"/api/descartes/?id_galpon={self.g1.pk}")
        self.assertEqual(self._ids(r), {self.d1.pk, self.d3.pk})

    def test_filtro_fecha_desde(self):
        r = self.client.get("/api/descartes/?fecha_desde=2026-08-10")
        self.assertEqual(self._ids(r), {self.d2.pk, self.d3.pk, self.d4.pk})

    def test_filtro_fecha_hasta(self):
        r = self.client.get("/api/descartes/?fecha_hasta=2026-08-10")
        self.assertEqual(self._ids(r), {self.d1.pk, self.d2.pk, self.d4.pk})

    def test_filtro_rango_de_fechas_inclusivo(self):
        r = self.client.get("/api/descartes/?fecha_desde=2026-08-10&fecha_hasta=2026-08-10")
        self.assertEqual(self._ids(r), {self.d2.pk, self.d4.pk})

    def test_rango_invertido_no_devuelve_nada(self):
        r = self.client.get("/api/descartes/?fecha_desde=2026-08-12&fecha_hasta=2026-08-09")
        self.assertEqual(r.data["count"], 0)

    def test_fecha_invalida_400(self):
        r = self.client.get("/api/descartes/?fecha_desde=no-es-fecha")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filtros_combinados(self):
        r = self.client.get("/api/descartes/?categoria=G&estado=P&fecha_desde=2026-08-10")
        self.assertEqual(self._ids(r), {self.d2.pk})

    def test_respuesta_incluye_items_count(self):
        r = self.client.get("/api/descartes/")
        self.assertIn("items_count", r.data["results"][0])

    def test_descarte_de_stock_no_tiene_galpon(self):
        r = self.client.get(f"/api/descartes/{self.d4.pk}/")
        self.assertEqual(r.data["categoria"], "S")
        self.assertEqual(r.data["categoria_display"], "Stock")
        self.assertIsNone(r.data["galpon"])
        self.assertIsNone(r.data["id_galpon"])


# ── NuevoDescarteGalponTests ───────────────────────────────────────────────────

class NuevoDescarteGalponTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.prod = make_producto()
        self.lote = make_lote(self.g)
        auth(self.client, self.admin)

    def _post(self, lineas, **kwargs):
        return self.client.post(
            "/api/descartes/", payload_galpon(self.g, lineas, **kwargs), format="json"
        )

    def test_crea_con_linea_materia_prima(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "5.00", "motivo": "podrido"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["categoria"], "G")
        self.assertEqual(r.data["lineas"][0]["tipo"], "materia_prima")

    def test_crea_con_linea_producto(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "10", "motivo": "rotos"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["lineas"][0]["tipo"], "producto")

    def test_crea_con_linea_lote(self):
        r = self._post([{"id_lote": self.lote.pk, "cantidad": "3", "motivo": "muerte natural"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["lineas"][0]["tipo"], "lote")

    def test_materia_prima_admite_decimales(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "2.50", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_estado_inicial_pendiente(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}])
        self.assertEqual(r.data["estado"], "P")

    def test_registra_el_usuario_que_lo_cargo(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["usuario"]["id_usuario"], self.admin.pk)
        self.assertEqual(r.data["usuario"]["usuario"], self.admin.usuario)
        self.assertEqual(Descarte.objects.get(pk=r.data["id_descarte"]).id_usuario, self.admin)

    def test_ignora_el_usuario_enviado_por_el_cliente(self):
        otro = make_operario()
        r = self._post(
            [{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}],
            id_usuario=otro.pk,
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["usuario"]["id_usuario"], self.admin.pk)

    def test_error_sin_lineas(self):
        r = self._post([])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_linea_sin_item(self):
        r = self._post([{"cantidad": "5", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_linea_dos_items(self):
        r = self._post([{
            "id_materia_prima": self.mp.pk, "id_producto": self.prod.pk,
            "cantidad": "5", "motivo": "x",
        }])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_cantidad_cero(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "0.00", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_sin_galpon(self):
        data = payload_galpon(self.g, [{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}])
        del data["id_galpon"]
        r = self.client.post("/api/descartes/", data, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_galpon", r.data)

    def test_error_galpon_inactivo(self):
        inactivo = make_galpon(galpon="Inactivo", estado=Galpon.ESTADO_INACTIVO)
        r = self.client.post("/api/descartes/", payload_galpon(
            inactivo, [{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}]
        ), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_sin_categoria(self):
        data = payload_galpon(self.g, [{"id_materia_prima": self.mp.pk, "cantidad": "1", "motivo": "x"}])
        del data["categoria"]
        r = self.client.post("/api/descartes/", data, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("categoria", r.data)

    def test_id_galpon_propagado_a_lineas(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "5", "motivo": "x"}])
        linea = LineaDescarte.objects.get(id_descarte=r.data["id_descarte"])
        self.assertEqual(linea.id_galpon_id, self.g.pk)

    def test_lote_de_otro_galpon_rechazado(self):
        otro = make_lote(make_galpon(galpon="Galpón 2"))
        r = self._post([{"id_lote": otro.pk, "cantidad": "1", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lote_finalizado_rechazado(self):
        viejo = make_lote(self.g, estado=Lote.ESTADO_FINALIZADO)
        r = self._post([{"id_lote": viejo.pk, "cantidad": "1", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gallinas_mas_que_las_del_lote_rechazado(self):
        r = self._post([{"id_lote": self.lote.pk, "cantidad": "501", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gallinas_con_decimales_rechazado(self):
        r = self._post([{"id_lote": self.lote.pk, "cantidad": "1.5", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_producto_con_decimales_rechazado(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "1.5", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_valida_stock_en_descartes_de_galpon(self):
        """Los descartes de galpón son estadísticos: pueden superar el stock."""
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "9999", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)


# ── NuevoDescarteStockTests ────────────────────────────────────────────────────

class NuevoDescarteStockTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima(stock_inicial=100)
        self.prod = make_producto(stock_inicial=50)
        self.lote = make_lote(self.g)
        auth(self.client, self.admin)

    def _post(self, lineas, **kwargs):
        return self.client.post("/api/descartes/", payload_stock(lineas, **kwargs), format="json")

    def test_crea_con_producto(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "10", "motivo": "vencidos"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["categoria"], "S")
        self.assertIsNone(r.data["galpon"])
        self.assertEqual(r.data["estado"], "P")

    def test_crea_con_materia_prima(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "5.50", "motivo": "humedad"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_lineas_sin_galpon(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "1", "motivo": "x"}])
        linea = LineaDescarte.objects.get(id_descarte=r.data["id_descarte"])
        self.assertIsNone(linea.id_galpon_id)

    def test_con_galpon_rechazado(self):
        r = self._post(
            [{"id_producto": self.prod.pk, "cantidad": "1", "motivo": "x"}],
            id_galpon=self.g.pk,
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_galpon", r.data)

    def test_con_lote_rechazado(self):
        r = self._post([{"id_lote": self.lote.pk, "cantidad": "1", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_producto_mas_que_el_stock_rechazado(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "51", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lineas", r.data)

    def test_materia_prima_mas_que_el_stock_rechazado(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "100.01", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cantidad_igual_al_stock_permitida(self):
        r = self._post([{"id_producto": self.prod.pk, "cantidad": "50", "motivo": "x"}])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_lineas_del_mismo_item_se_suman(self):
        r = self._post([
            {"id_producto": self.prod.pk, "cantidad": "30", "motivo": "a"},
            {"id_producto": self.prod.pk, "cantidad": "30", "motivo": "b"},
        ])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_error_sin_lineas(self):
        r = self._post([])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ── FinalizarDescarteTests ─────────────────────────────────────────────────────

class FinalizarDescarteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.d = make_descarte(self.g)
        add_linea(self.d, id_materia_prima=self.mp)
        auth(self.client, self.admin)

    def test_finaliza_pendiente(self):
        r = self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["estado"], "F")

    def test_finalizado_persiste(self):
        self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.d.refresh_from_db()
        self.assertEqual(self.d.estado, Descarte.ESTADO_FINALIZADO)

    def test_idempotencia_409(self):
        self.d.estado = Descarte.ESTADO_FINALIZADO
        self.d.save()
        r = self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_no_editable_tras_finalizar(self):
        self.d.estado = Descarte.ESTADO_FINALIZADO
        self.d.save()
        r = self.client.patch(
            f"/api/descartes/{self.d.pk}/",
            {"observaciones": "nuevo", "lineas": [
                {"id_materia_prima": self.mp.pk, "cantidad": "1.00", "motivo": "x"}
            ]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ── FinalizarStockTests ────────────────────────────────────────────────────────

class FinalizarStockTests(TestCase):
    """Un descarte de stock finalizado baja el stock actual; uno de galpón, no."""

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima(stock_inicial=100)
        self.prod = make_producto(stock_inicial=50)
        auth(self.client, self.admin)

    def _stock_producto(self):
        return self.client.get(f"/api/productos/{self.prod.pk}/").data["stock_actual"]

    def _stock_mp(self):
        return Decimal(self.client.get(f"/api/materias-primas/{self.mp.pk}/").data["stock_actual"])

    def _descarte_stock(self, cantidad=10, **item):
        d = make_descarte(categoria=Descarte.CATEGORIA_STOCK)
        add_linea(d, cantidad=cantidad, **item)
        return d

    def _finalizar(self, d):
        return self.client.post(f"/api/descartes/{d.pk}/finalizar/")

    def test_finalizar_baja_stock_de_producto(self):
        d = self._descarte_stock(10, id_producto=self.prod)
        self.assertEqual(self._stock_producto(), 50)
        self.assertEqual(self._finalizar(d).status_code, status.HTTP_200_OK)
        self.assertEqual(self._stock_producto(), 40)

    def test_finalizar_baja_stock_de_materia_prima(self):
        d = self._descarte_stock("12.50", id_materia_prima=self.mp)
        self.assertEqual(self._stock_mp(), Decimal("100"))
        self.assertEqual(self._finalizar(d).status_code, status.HTTP_200_OK)
        self.assertEqual(self._stock_mp(), Decimal("87.50"))

    def test_pendiente_no_baja_el_stock(self):
        self._descarte_stock(10, id_producto=self.prod)
        self._descarte_stock(10, id_materia_prima=self.mp)
        self.assertEqual(self._stock_producto(), 50)
        self.assertEqual(self._stock_mp(), Decimal("100"))

    def test_expone_stock_descartado(self):
        d = self._descarte_stock(10, id_producto=self.prod)
        self._finalizar(d)
        r = self.client.get(f"/api/productos/{self.prod.pk}/")
        self.assertEqual(r.data["stock_descartado"], 10)
        d2 = self._descarte_stock("4.00", id_materia_prima=self.mp)
        self._finalizar(d2)
        r = self.client.get(f"/api/materias-primas/{self.mp.pk}/")
        self.assertEqual(Decimal(r.data["stock_descartado"]), Decimal("4"))

    def test_stock_insuficiente_al_finalizar(self):
        """Dos descartes pendientes que juntos superan el stock: el segundo falla."""
        a = self._descarte_stock(30, id_producto=self.prod)
        b = self._descarte_stock(30, id_producto=self.prod)
        self.assertEqual(self._finalizar(a).status_code, status.HTTP_200_OK)
        r = self._finalizar(b)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        b.refresh_from_db()
        self.assertEqual(b.estado, Descarte.ESTADO_PENDIENTE)
        self.assertEqual(self._stock_producto(), 20)

    def test_descarte_de_galpon_no_baja_el_stock(self):
        """Huevos rotos o alimento podrido dentro del galpón: solo estadística."""
        d = make_descarte(self.g)
        add_linea(d, cantidad=10, id_producto=self.prod)
        add_linea(d, cantidad="5.00", id_materia_prima=self.mp)
        self.assertEqual(self._finalizar(d).status_code, status.HTTP_200_OK)
        self.assertEqual(self._stock_producto(), 50)
        self.assertEqual(self._stock_mp(), Decimal("100"))

    def test_listado_de_productos_no_infla_las_sumas(self):
        """
        Hay una recolección finalizada y dos descartes finalizados del mismo
        producto: el listado (que anota ambos totales) debe dar 50 + 20 - 12.
        """
        lote = make_lote(self.g)
        rec = Recoleccion.objects.create(
            id_galpon=self.g, id_lote=lote, fecha=fecha(9),
            estado=Recoleccion.ESTADO_FINALIZADA,
        )
        LineaRecoleccion.objects.create(
            id_recoleccion=rec, id_galpon=self.g, id_producto=self.prod, cantidad=20,
        )
        for cantidad in (5, 7):
            self._finalizar(self._descarte_stock(cantidad, id_producto=self.prod))
        r = self.client.get("/api/productos/")
        item = next(p for p in r.data["results"] if p["id_producto"] == self.prod.pk)
        self.assertEqual(item["stock_recolectado"], 20)
        self.assertEqual(item["stock_descartado"], 12)
        self.assertEqual(item["stock_actual"], 58)

    def test_listado_de_materias_primas(self):
        self._finalizar(self._descarte_stock("30.00", id_materia_prima=self.mp))
        r = self.client.get("/api/materias-primas/")
        item = next(m for m in r.data["results"] if m["id_materia_prima"] == self.mp.pk)
        self.assertEqual(Decimal(item["stock_actual"]), Decimal("70"))


# ── ModificarDescarteTests ─────────────────────────────────────────────────────

class ModificarDescarteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.mp2 = make_materia_prima(materia_prima="Vitaminas", unidad="g")
        self.prod = make_producto()
        self.d = make_descarte(self.g, observaciones="original")
        add_linea(self.d, id_materia_prima=self.mp)
        auth(self.client, self.admin)

    def test_modifica_observaciones(self):
        r = self.client.patch(
            f"/api/descartes/{self.d.pk}/",
            {"observaciones": "actualizado", "lineas": [
                {"id_materia_prima": self.mp.pk, "cantidad": "5.00", "motivo": "test"}
            ]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["observaciones"], "actualizado")

    def test_reemplaza_lineas(self):
        r = self.client.patch(
            f"/api/descartes/{self.d.pk}/",
            {"observaciones": "original", "lineas": [
                {"id_materia_prima": self.mp2.pk, "cantidad": "2.00", "motivo": "nuevo"}
            ]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["lineas"]), 1)
        self.assertEqual(r.data["lineas"][0]["id_materia_prima"], self.mp2.pk)

    def test_modificar_no_cambia_quien_lo_cargo(self):
        self.d.id_usuario = self.admin
        self.d.save(update_fields=["id_usuario"])
        otro = make_operario()
        auth(self.client, otro)
        r = self.client.patch(
            f"/api/descartes/{self.d.pk}/", {"observaciones": "editado por otro"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["usuario"]["id_usuario"], self.admin.pk)

    def test_no_cambia_la_categoria(self):
        r = self.client.patch(f"/api/descartes/{self.d.pk}/", {"categoria": "S"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.d.refresh_from_db()
        self.assertEqual(self.d.categoria, Descarte.CATEGORIA_GALPON)

    def test_modifica_descarte_de_stock(self):
        d = make_descarte(categoria=Descarte.CATEGORIA_STOCK)
        add_linea(d, cantidad=5, id_producto=self.prod)
        r = self.client.patch(
            f"/api/descartes/{d.pk}/",
            {"lineas": [{"id_producto": self.prod.pk, "cantidad": "8", "motivo": "otro"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["lineas"][0]["motivo"], "otro")

    def test_modificar_stock_valida_el_stock(self):
        d = make_descarte(categoria=Descarte.CATEGORIA_STOCK)
        add_linea(d, cantidad=5, id_producto=self.prod)
        r = self.client.patch(
            f"/api/descartes/{d.pk}/",
            {"lineas": [{"id_producto": self.prod.pk, "cantidad": "999", "motivo": "x"}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inexistente_404(self):
        r = self.client.patch("/api/descartes/9999/", {"observaciones": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


# ── EliminarDescarteTests ──────────────────────────────────────────────────────

class EliminarDescarteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.d = make_descarte(self.g)
        add_linea(self.d, id_materia_prima=self.mp)
        auth(self.client, self.admin)

    def test_elimina(self):
        r = self.client.delete(f"/api/descartes/{self.d.pk}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Descarte.objects.filter(pk=self.d.pk).exists())

    def test_lineas_en_cascada(self):
        pk = self.d.pk
        self.client.delete(f"/api/descartes/{pk}/")
        self.assertFalse(LineaDescarte.objects.filter(id_descarte_id=pk).exists())

    def test_no_elimina_finalizado(self):
        self.d.estado = Descarte.ESTADO_FINALIZADO
        self.d.save()
        r = self.client.delete(f"/api/descartes/{self.d.pk}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Descarte.objects.filter(pk=self.d.pk).exists())

    def test_elimina_descarte_de_stock_pendiente(self):
        d = make_descarte(categoria=Descarte.CATEGORIA_STOCK)
        add_linea(d, id_materia_prima=self.mp)
        r = self.client.delete(f"/api/descartes/{d.pk}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_inexistente_404(self):
        r = self.client.delete("/api/descartes/9999/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


# ── LineasDescarteTests ────────────────────────────────────────────────────────

class LineasDescarteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.prod = make_producto()
        self.lote = make_lote(self.g)
        auth(self.client, self.admin)

    def _post(self, lineas):
        return self.client.post("/api/descartes/", payload_galpon(self.g, lineas), format="json")

    def test_tres_tipos_en_un_descarte(self):
        r = self._post([
            {"id_materia_prima": self.mp.pk, "cantidad": "5.00", "motivo": "a"},
            {"id_producto": self.prod.pk, "cantidad": "3", "motivo": "b"},
            {"id_lote": self.lote.pk, "cantidad": "2", "motivo": "c"},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(r.data["lineas"]), 3)

    def test_cantidad_negativa_rechazada(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "-1.00", "motivo": "a"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_motivo_obligatorio(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "1.00"}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nombre_legible_en_respuesta(self):
        r = self._post([{"id_materia_prima": self.mp.pk, "cantidad": "5.00", "motivo": "test"}])
        linea = r.data["lineas"][0]
        self.assertEqual(linea["materia_prima_nombre"], "Balanceado")
        self.assertEqual(linea["materia_prima_unidad"], "kg")
        self.assertIsNone(linea["producto_nombre"])
        self.assertIsNone(linea["lote_codigo"])


# ── PermisosDescarteTests ──────────────────────────────────────────────────────

class PermisosDescarteTests(TestCase):
    """
    Matriz del README: Administrador y Operario tienen CRUD completo en
    Descartes; Consulta solo lectura.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.operario = make_operario()
        self.consulta = make_consulta()
        self.g = make_galpon()
        self.mp = make_materia_prima()
        self.d = make_descarte(self.g)
        add_linea(self.d, id_materia_prima=self.mp)

    def _payload(self):
        return payload_galpon(
            self.g, [{"id_materia_prima": self.mp.pk, "cantidad": "1.00", "motivo": "x"}]
        )

    def test_sin_token_401(self):
        r = self.client.get("/api/descartes/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_puede_listar(self):
        auth(self.client, self.admin)
        r = self.client.get("/api/descartes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_operario_puede_listar(self):
        auth(self.client, self.operario)
        r = self.client.get("/api/descartes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_consulta_puede_listar(self):
        auth(self.client, self.consulta)
        r = self.client.get("/api/descartes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_operario_puede_crear(self):
        auth(self.client, self.operario)
        r = self.client.post("/api/descartes/", self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_operario_puede_crear_descarte_de_stock(self):
        auth(self.client, self.operario)
        r = self.client.post("/api/descartes/", payload_stock(
            [{"id_materia_prima": self.mp.pk, "cantidad": "1.00", "motivo": "x"}]
        ), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_consulta_no_puede_crear(self):
        auth(self.client, self.consulta)
        r = self.client.post("/api/descartes/", self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_operario_puede_eliminar(self):
        auth(self.client, self.operario)
        r = self.client.delete(f"/api/descartes/{self.d.pk}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_consulta_no_puede_eliminar(self):
        auth(self.client, self.consulta)
        r = self.client.delete(f"/api/descartes/{self.d.pk}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_consulta_no_puede_finalizar(self):
        auth(self.client, self.consulta)
        r = self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_puede_finalizar(self):
        auth(self.client, self.admin)
        r = self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_operario_puede_finalizar(self):
        auth(self.client, self.operario)
        r = self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_operario_puede_modificar(self):
        auth(self.client, self.operario)
        r = self.client.patch(
            f"/api/descartes/{self.d.pk}/",
            {"observaciones": "x", "lineas": [
                {"id_materia_prima": self.mp.pk, "cantidad": "1.00", "motivo": "x"}
            ]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_consulta_no_puede_modificar(self):
        auth(self.client, self.consulta)
        r = self.client.patch(f"/api/descartes/{self.d.pk}/", {"observaciones": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


# ── DescarteLoteTests ──────────────────────────────────────────────────────────

class DescarteLoteTests(TestCase):
    """
    Al finalizar un descarte de galpón con líneas de gallinas (lote),
    la cantidad_actual del lote se decrementa.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.g = make_galpon()
        self.lote = make_lote(self.g, cantidad_inicial=500, cantidad_actual=500)
        self.d = make_descarte(self.g)
        add_linea(self.d, cantidad=10, motivo="muerte natural", id_lote=self.lote)
        auth(self.client, self.admin)

    def test_finalizar_decrementa_cantidad_actual(self):
        self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 490)

    def test_finalizar_no_baja_de_cero(self):
        self.lote.cantidad_actual = 5
        self.lote.save()
        self.client.post(f"/api/descartes/{self.d.pk}/finalizar/")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 0)

    def test_descarte_pendiente_no_modifica_lote(self):
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 500)

    def test_descarte_de_stock_no_toca_lotes(self):
        prod = make_producto()
        d = make_descarte(categoria=Descarte.CATEGORIA_STOCK)
        add_linea(d, cantidad=5, id_producto=prod)
        self.client.post(f"/api/descartes/{d.pk}/finalizar/")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 500)
