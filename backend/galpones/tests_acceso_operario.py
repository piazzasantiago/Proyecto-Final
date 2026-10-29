"""Operarios: solo ven y trabajan con los registros de sus galpones asignados (F-32).

    RecoleccionesOperarioTests  listado, detalle, acciones y alta de recolecciones
    EntradasOperarioTests       listado, detalle, acciones y alta de entradas
    DescartesOperarioTests      descartes de galpón y de stock
    OtrosRolesTests             Administrador y Consulta siguen viendo todo
"""
import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from descartes.models import Descarte
from entradas.models import Entrada, LineaEntrada
from galpones.models import Galpon, UsuarioDelGalpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from productos.models import Producto
from recolecciones.models import LineaRecoleccion, Recoleccion
from usuarios.models import Usuario

PASSWORD = "Pass1234!"
FECHA = datetime.datetime(2026, 8, 9, 10, 0, tzinfo=datetime.timezone.utc)


def crear_usuario(usuario, rol):
    u = Usuario(
        usuario=usuario, email=f"{usuario}@test.com", nombre="Ana", apellido=usuario.title(),
        dni=f"77{abs(hash(usuario)) % 10**6:06d}", rol=rol,
    )
    u.set_password(PASSWORD)
    u.save()
    return u


def cliente_de(usuario):
    client = APIClient()
    resp = client.post("/api/auth/login/", {"usuario": usuario.usuario, "password": PASSWORD}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


def crear_galpon(nombre):
    return Galpon.objects.create(
        galpon=nombre, latitud="0", longitud="0", superficie="1", capacidad=5000,
    )


def crear_lote(galpon):
    return Lote.objects.create(
        id_galpon=galpon, fecha_ingreso=datetime.date(2026, 1, 1),
        cantidad_inicial=500, cantidad_actual=500, estado=Lote.ESTADO_PRODUCCION,
    )


class Escenario(TestCase):
    """Operario asignado al galpón 5; también existen los galpones 2 y 3."""

    def setUp(self):
        self.admin = crear_usuario("admin_f32", Usuario.ROL_ADMINISTRADOR)
        self.consulta = crear_usuario("consulta_f32", Usuario.ROL_CONSULTA)
        self.operario = crear_usuario("operario_f32", Usuario.ROL_OPERARIO)
        self.otro_operario = crear_usuario("otro_f32", Usuario.ROL_OPERARIO)
        self.g2, self.g3, self.g5 = crear_galpon("Galpón 2"), crear_galpon("Galpón 3"), crear_galpon("Galpón 5")
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.g5)
        UsuarioDelGalpon.objects.create(id_usuario=self.otro_operario, id_galpon=self.g2)
        self.lotes = {g.pk: crear_lote(g) for g in (self.g2, self.g3, self.g5)}
        self.producto = Producto.objects.create(producto="Huevo F32")
        self.materia = MateriaPrima.objects.create(
            materia_prima="Maíz F32", unidad="kg", stock_minimo=1, stock_inicial=1000,
        )
        self.client = cliente_de(self.operario)

    def ids(self, resp, clave):
        return {r[clave] for r in resp.data["results"]}


class RecoleccionesOperarioTests(Escenario):
    def setUp(self):
        super().setUp()
        self.rec = {}
        for g in (self.g2, self.g3, self.g5):
            r = Recoleccion.objects.create(id_galpon=g, id_lote=self.lotes[g.pk], fecha=FECHA)
            LineaRecoleccion.objects.create(id_recoleccion=r, id_galpon=g, id_producto=self.producto, cantidad=10)
            self.rec[g.pk] = r

    def test_lista_solo_las_de_su_galpon(self):
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.ids(resp, "id_recoleccion"), {self.rec[self.g5.pk].pk})
        self.assertEqual(resp.data["count"], 1)

    def test_filtrar_por_un_galpon_ajeno_no_devuelve_nada(self):
        resp = self.client.get(f"/api/recolecciones/?id_galpon={self.g2.pk}")
        self.assertEqual(resp.data["count"], 0)

    def test_detalle_de_un_galpon_ajeno_da_404(self):
        self.assertEqual(self.client.get(f"/api/recolecciones/{self.rec[self.g2.pk].pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/recolecciones/{self.rec[self.g5.pk].pk}/").status_code, 200)

    def test_no_puede_editar_finalizar_ni_borrar_las_ajenas(self):
        pk = self.rec[self.g3.pk].pk
        self.assertEqual(self.client.patch(f"/api/recolecciones/{pk}/", {"observaciones": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.post(f"/api/recolecciones/{pk}/finalizar/").status_code, 404)
        self.assertTrue(Recoleccion.objects.filter(pk=pk, estado=Recoleccion.ESTADO_PENDIENTE).exists())

    def test_puede_finalizar_las_de_su_galpon(self):
        pk = self.rec[self.g5.pk].pk
        self.assertEqual(self.client.post(f"/api/recolecciones/{pk}/finalizar/").status_code, 200)

    def _payload(self, galpon):
        return {
            "id_galpon_id": galpon.pk, "fecha": "2026-06-15T08:00:00", "observaciones": "",
            "lineas": [{"id_producto_id": self.producto.pk, "cantidad": 100}],
        }

    def test_no_puede_crear_en_un_galpon_ajeno(self):
        resp = self.client.post("/api/recolecciones/", self._payload(self.g3), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_galpon_id", resp.data)
        self.assertFalse(Recoleccion.objects.filter(id_galpon=self.g3, fecha__date="2026-06-15").exists())

    def test_puede_crear_en_su_galpon(self):
        resp = self.client.post("/api/recolecciones/", self._payload(self.g5), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_un_operario_sin_galpones_no_ve_nada(self):
        sin = crear_usuario("sin_f32", Usuario.ROL_OPERARIO)
        resp = cliente_de(sin).get("/api/recolecciones/")
        self.assertEqual(resp.data["count"], 0)

    def test_la_asignacion_es_por_operario(self):
        resp = cliente_de(self.otro_operario).get("/api/recolecciones/")
        self.assertEqual(self.ids(resp, "id_recoleccion"), {self.rec[self.g2.pk].pk})


class EntradasOperarioTests(Escenario):
    def setUp(self):
        super().setUp()
        self.ent = {}
        for g in (self.g2, self.g3, self.g5):
            e = Entrada.objects.create(id_galpon=g, fecha=FECHA, observaciones="")
            LineaEntrada.objects.create(id_entrada=e, id_materia_prima=self.materia, cantidad=5)
            self.ent[g.pk] = e

    def test_lista_solo_las_de_su_galpon(self):
        resp = self.client.get("/api/entradas/")
        self.assertEqual(self.ids(resp, "id_entrada"), {self.ent[self.g5.pk].pk})

    def test_detalle_y_acciones_de_un_galpon_ajeno_dan_404(self):
        pk = self.ent[self.g2.pk].pk
        self.assertEqual(self.client.get(f"/api/entradas/{pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/entradas/{pk}/finalizar/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/entradas/{pk}/").status_code, 404)
        self.assertTrue(Entrada.objects.filter(pk=pk).exists())

    def _payload(self, galpon):
        return {
            "id_galpon": galpon.pk, "fecha": "2026-08-09T10:00:00Z", "observaciones": "",
            "lineas": [{"id_materia_prima": self.materia.pk, "cantidad": "5"}],
        }

    def test_no_puede_crear_en_un_galpon_ajeno(self):
        resp = self.client.post("/api/entradas/", self._payload(self.g3), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_galpon", resp.data)

    def test_puede_crear_en_su_galpon(self):
        resp = self.client.post("/api/entradas/", self._payload(self.g5), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)


class DescartesOperarioTests(Escenario):
    def setUp(self):
        super().setUp()
        self.desc = {
            g.pk: Descarte.objects.create(categoria="G", id_galpon=g, fecha=FECHA, observaciones="")
            for g in (self.g2, self.g3, self.g5)
        }
        self.de_stock = Descarte.objects.create(categoria="S", fecha=FECHA, observaciones="")

    def test_ve_los_de_su_galpon_y_los_de_stock(self):
        resp = self.client.get("/api/descartes/")
        self.assertEqual(self.ids(resp, "id_descarte"), {self.desc[self.g5.pk].pk, self.de_stock.pk})

    def test_detalle_de_un_galpon_ajeno_da_404(self):
        self.assertEqual(self.client.get(f"/api/descartes/{self.desc[self.g2.pk].pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/descartes/{self.de_stock.pk}/").status_code, 200)

    def test_no_puede_crear_un_descarte_de_galpon_ajeno(self):
        payload = {
            "categoria": "G", "id_galpon": self.g3.pk, "fecha": "2026-08-09T10:00:00Z", "observaciones": "",
            "lineas": [{"id_lote": self.lotes[self.g3.pk].pk, "cantidad": 1, "motivo": "x"}],
        }
        resp = self.client.post("/api/descartes/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_galpon", resp.data)


class OtrosRolesTests(Escenario):
    def setUp(self):
        super().setUp()
        for g in (self.g2, self.g3, self.g5):
            Recoleccion.objects.create(id_galpon=g, id_lote=self.lotes[g.pk], fecha=FECHA)
            Entrada.objects.create(id_galpon=g, fecha=FECHA, observaciones="")
            Descarte.objects.create(categoria="G", id_galpon=g, fecha=FECHA, observaciones="")

    def test_administrador_y_consulta_ven_todo(self):
        for usuario in (self.admin, self.consulta):
            client = cliente_de(usuario)
            for url in ("/api/recolecciones/", "/api/entradas/", "/api/descartes/"):
                self.assertEqual(client.get(url).data["count"], 3, (usuario.rol, url))
