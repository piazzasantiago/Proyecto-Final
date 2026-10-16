"""
Tests del módulo Entradas a galpones (CU33 a CU41).

Una entrada saca insumos del stock de materias primas y los pasa a un galpón:
  - Pendiente (P): editable y borrable, no toca el stock.
  - Finalizada (F): de solo lectura; descuenta de cada materia prima la cantidad
    de sus líneas.

Clases:
  - BuscarEntradaTests            CU33: listado y filtros (fechas, estado, galpón, materia prima)
  - NuevaEntradaTests             CU35 y CU39: crear con líneas y validaciones
  - FechaEntradaTests             la fecha no puede ser futura
  - ModificarEntradaTests         CU36, CU40 y CU41: editar entrada pendiente
  - BorrarEntradaTests            CU34: borrar entrada
  - FinalizarEntradaTests         CU37: finalizar y verificar stock
  - StockMateriaPrimaEntradaTests el stock de Materias Primas resta las entradas finalizadas
  - ExistenciasGalponTests        existencia estimada de materias primas por galpón
  - PermisosEntradaTests          matriz rol × operación
"""

import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from descartes.models import Descarte, LineaDescarte
from galpones.models import Galpon, UsuarioDelGalpon
from materias_primas.models import MateriaPrima
from usuarios.models import Usuario

from .models import Entrada, LineaEntrada


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


def make_mp(nombre="Balanceado", stock_inicial=100, **kwargs):
    defaults = dict(materia_prima=nombre, unidad="kg", stock_minimo=10, stock_inicial=stock_inicial)
    defaults.update(kwargs)
    return MateriaPrima.objects.create(**defaults)


def fecha(dia, hora=10):
    """Datetime aware (UTC) del día indicado de agosto de 2026."""
    return datetime.datetime(2026, 8, dia, hora, 0, tzinfo=dt_timezone.utc)


def make_entrada(galpon, estado=Entrada.ESTADO_PENDIENTE, dia=9, **kwargs):
    defaults = dict(id_galpon=galpon, fecha=fecha(dia), estado=estado, observaciones="")
    defaults.update(kwargs)
    return Entrada.objects.create(**defaults)


def add_linea(entrada, mp, cantidad=5):
    return LineaEntrada.objects.create(id_entrada=entrada, id_materia_prima=mp, cantidad=cantidad)


def auth(client, user):
    r = client.post(
        "/api/auth/login/",
        {"usuario": user.usuario, "password": "pass1234"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def payload(galpon, lineas, **kwargs):
    base = dict(
        id_galpon=galpon.pk, fecha="2026-08-09T10:00:00Z",
        observaciones="test", lineas=lineas,
    )
    base.update(kwargs)
    return base


def linea(mp, cantidad="5"):
    return {"id_materia_prima": mp.pk, "cantidad": str(cantidad)}


# ── CU33 Buscar ───────────────────────────────────────────────────────────────

class BuscarEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_consulta())
        self.g1 = make_galpon("Galpón 1")
        self.g2 = make_galpon("Galpón 2")
        self.mp1 = make_mp("Balanceado")
        self.mp2 = make_mp("Vacuna")
        self.e1 = make_entrada(self.g1, dia=5)
        add_linea(self.e1, self.mp1)
        self.e2 = make_entrada(self.g2, estado=Entrada.ESTADO_FINALIZADA, dia=10)
        add_linea(self.e2, self.mp2)
        add_linea(self.e2, self.mp1)

    def ids(self, **params):
        resp = self.client.get("/api/entradas/", params)
        self.assertEqual(resp.status_code, 200)
        return {e["id_entrada"] for e in resp.data["results"]}

    def test_listar(self):
        self.assertEqual(self.ids(), {self.e1.pk, self.e2.pk})

    def test_filtrar_por_galpon(self):
        self.assertEqual(self.ids(id_galpon=self.g1.pk), {self.e1.pk})

    def test_filtrar_por_estado(self):
        self.assertEqual(self.ids(estado="F"), {self.e2.pk})
        self.assertEqual(self.ids(estado="P"), {self.e1.pk})

    def test_filtrar_por_materia_prima_sin_duplicar(self):
        self.assertEqual(self.ids(id_materia_prima=self.mp1.pk), {self.e1.pk, self.e2.pk})
        self.assertEqual(self.ids(id_materia_prima=self.mp2.pk), {self.e2.pk})

    def test_filtro_fecha_desde_y_hasta_inclusivos(self):
        self.assertEqual(self.ids(fecha_desde="2026-08-10"), {self.e2.pk})
        self.assertEqual(self.ids(fecha_hasta="2026-08-05"), {self.e1.pk})
        self.assertEqual(self.ids(fecha_desde="2026-08-05", fecha_hasta="2026-08-10"),
                         {self.e1.pk, self.e2.pk})

    def test_fecha_invalida_400(self):
        resp = self.client.get("/api/entradas/", {"fecha_desde": "no-es-fecha"})
        self.assertEqual(resp.status_code, 400)

    def test_detalle_con_lineas_y_conteo(self):
        resp = self.client.get(f"/api/entradas/{self.e2.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["items_count"], 2)
        self.assertEqual(len(resp.data["lineas"]), 2)
        self.assertEqual(resp.data["galpon"]["galpon"], "Galpón 2")
        self.assertEqual(resp.data["estado_display"], "Finalizada")
        nombres = {l["materia_prima_nombre"] for l in resp.data["lineas"]}
        self.assertEqual(nombres, {"Balanceado", "Vacuna"})

    def test_detalle_inexistente_404(self):
        self.assertEqual(self.client.get("/api/entradas/9999/").status_code, 404)


# ── CU35 / CU39 Nueva ─────────────────────────────────────────────────────────

class NuevaEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        auth(self.client, self.admin)
        self.g = make_galpon()
        self.mp = make_mp("Balanceado", stock_inicial=100)
        self.mp2 = make_mp("Vacuna", stock_inicial=50)

    def post(self, lineas, **kwargs):
        return self.client.post("/api/entradas/", payload(self.g, lineas, **kwargs), format="json")

    def test_crear_exitoso(self):
        resp = self.post([linea(self.mp, "20"), linea(self.mp2, "5.5")])
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["estado"], "P")
        self.assertEqual(len(resp.data["lineas"]), 2)
        self.assertEqual(Entrada.objects.get().lineas.count(), 2)

    def test_registra_el_usuario_que_la_cargo(self):
        resp = self.post([linea(self.mp)])
        self.assertEqual(resp.data["usuario"]["usuario"], "admin")

    def test_el_usuario_no_se_toma_del_cliente(self):
        otro = make_operario()
        resp = self.post([linea(self.mp)], id_usuario=otro.pk, estado="F")
        self.assertEqual(resp.data["usuario"]["usuario"], "admin")
        self.assertEqual(resp.data["estado"], "P")

    def test_no_toca_el_stock_hasta_finalizar(self):
        self.post([linea(self.mp, "20")])
        resp = self.client.get(f"/api/materias-primas/{self.mp.pk}/")
        self.assertEqual(Decimal(str(resp.data["stock_actual"])), Decimal("100"))

    def test_galpon_obligatorio(self):
        resp = self.client.post(
            "/api/entradas/",
            dict(fecha="2026-08-09T10:00:00Z", lineas=[linea(self.mp)]),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_galpon", resp.data)

    def test_galpon_inactivo_rechazado(self):
        Galpon.objects.filter(pk=self.g.pk).update(estado=Galpon.ESTADO_INACTIVO)
        self.assertEqual(self.post([linea(self.mp)]).status_code, 400)

    def test_sin_lineas(self):
        resp = self.post([])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("lineas", resp.data)

    def test_materia_prima_repetida(self):
        resp = self.post([linea(self.mp, "5"), linea(self.mp, "5")])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("repetida", str(resp.data["lineas"]))

    def test_materia_prima_inactiva_rechazada(self):
        MateriaPrima.objects.filter(pk=self.mp.pk).update(estado=MateriaPrima.ESTADO_INACTIVO)
        resp = self.post([linea(self.mp)])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("inactiva", str(resp.data["lineas"]))

    def test_materia_prima_inexistente(self):
        resp = self.client.post(
            "/api/entradas/",
            payload(self.g, [{"id_materia_prima": 9999, "cantidad": "1"}]),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cantidad_cero_negativa_o_sin_numero(self):
        for cantidad in ["0", "-3", "abc"]:
            resp = self.post([linea(self.mp, cantidad)])
            self.assertEqual(resp.status_code, 400, cantidad)

    def test_cantidad_con_dos_decimales_valida_y_tres_rechazada(self):
        self.assertEqual(self.post([linea(self.mp, "1.25")]).status_code, 201)
        resp = self.post([linea(self.mp2, "1.255")], fecha="2026-08-10T10:00:00Z")
        self.assertEqual(resp.status_code, 400)

    def test_cantidad_enorme_es_400_y_no_500(self):
        resp = self.post([linea(self.mp, "99999999999999")])
        self.assertEqual(resp.status_code, 400)

    def test_stock_insuficiente_al_crear(self):
        resp = self.post([linea(self.mp, "100.01")])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Stock insuficiente", str(resp.data["lineas"]))
        self.assertIn("ingresar", str(resp.data["lineas"]))

    def test_cantidad_igual_al_stock_es_valida(self):
        self.assertEqual(self.post([linea(self.mp, "100")]).status_code, 201)

    def test_observaciones_500_validas_y_501_rechazadas(self):
        self.assertEqual(self.post([linea(self.mp)], observaciones="a" * 500).status_code, 201)
        resp = self.post([linea(self.mp2)], observaciones="a" * 501,
                         fecha="2026-08-10T10:00:00Z")
        self.assertEqual(resp.status_code, 400)

    def test_observaciones_opcionales(self):
        resp = self.client.post(
            "/api/entradas/",
            dict(id_galpon=self.g.pk, fecha="2026-08-09T10:00:00Z", lineas=[linea(self.mp)]),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)


class FechaEntradaTests(TestCase):
    """La fecha de la entrada no puede ser posterior al momento actual."""

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.mp = make_mp()

    def crear(self, momento):
        return self.client.post(
            "/api/entradas/",
            payload(self.g, [linea(self.mp, "1")], fecha=momento.isoformat()),
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

    def test_no_se_puede_editar_a_fecha_futura(self):
        creada = self.crear(timezone.now() - datetime.timedelta(days=1))
        resp = self.client.patch(
            f"/api/entradas/{creada.data['id_entrada']}/",
            {"fecha": (timezone.now() + datetime.timedelta(days=1)).isoformat()},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


# ── CU36 / CU40 / CU41 Modificar ──────────────────────────────────────────────

class ModificarEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.mp = make_mp("Balanceado", stock_inicial=100)
        self.mp2 = make_mp("Vacuna", stock_inicial=50)
        self.e = make_entrada(self.g)
        add_linea(self.e, self.mp, 10)
        self.url = f"/api/entradas/{self.e.pk}/"

    def test_editar_observaciones_conserva_lineas(self):
        resp = self.client.patch(self.url, {"observaciones": "nueva"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.e.refresh_from_db()
        self.assertEqual(self.e.observaciones, "nueva")
        self.assertEqual(self.e.lineas.count(), 1)

    def test_modificar_cantidad_de_una_linea(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.mp, "30")]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.e.lineas.get().cantidad, Decimal("30"))

    def test_agregar_y_quitar_lineas(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.mp2, "4")]}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([l.id_materia_prima_id for l in self.e.lineas.all()], [self.mp2.pk])

    def test_no_puede_quedar_sin_lineas(self):
        resp = self.client.patch(self.url, {"lineas": []}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.e.lineas.count(), 1)

    def test_materia_prima_repetida_al_editar(self):
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.mp, "1"), linea(self.mp, "2")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_stock_insuficiente_al_editar(self):
        resp = self.client.patch(self.url, {"lineas": [linea(self.mp, "500")]}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_conserva_materia_prima_dada_de_baja(self):
        MateriaPrima.objects.filter(pk=self.mp.pk).update(estado=MateriaPrima.ESTADO_INACTIVO)
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.mp, "20"), linea(self.mp2, "1")]}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_no_agrega_materia_prima_inactiva_nueva(self):
        MateriaPrima.objects.filter(pk=self.mp2.pk).update(estado=MateriaPrima.ESTADO_INACTIVO)
        resp = self.client.patch(
            self.url, {"lineas": [linea(self.mp, "10"), linea(self.mp2, "1")]}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_el_galpon_no_se_cambia(self):
        otro = make_galpon("Galpón 2")
        resp = self.client.patch(self.url, {"id_galpon": otro.pk}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_galpon", resp.data)

    def test_reenviar_el_mismo_galpon_es_valido(self):
        resp = self.client.patch(self.url, {"id_galpon": self.g.pk}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_el_estado_y_el_usuario_no_se_editan(self):
        otro = make_operario()
        resp = self.client.patch(self.url, {"estado": "F", "id_usuario": otro.pk}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, Entrada.ESTADO_PENDIENTE)
        self.assertIsNone(self.e.id_usuario)

    def test_entrada_finalizada_no_se_edita(self):
        Entrada.objects.filter(pk=self.e.pk).update(estado=Entrada.ESTADO_FINALIZADA)
        resp = self.client.patch(self.url, {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Entrada finalizada. No se puede editar.", str(resp.data))

    def test_inexistente_404(self):
        resp = self.client.patch("/api/entradas/9999/", {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ── CU34 Borrar ───────────────────────────────────────────────────────────────

class BorrarEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.mp = make_mp()

    def test_borrar_pendiente_y_sus_lineas(self):
        e = make_entrada(self.g)
        add_linea(e, self.mp)
        resp = self.client.delete(f"/api/entradas/{e.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Entrada.objects.filter(pk=e.pk).exists())
        self.assertFalse(LineaEntrada.objects.filter(id_entrada_id=e.pk).exists())

    def test_finalizada_no_se_borra(self):
        e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA)
        add_linea(e, self.mp)
        resp = self.client.delete(f"/api/entradas/{e.pk}/")
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Entrada.objects.filter(pk=e.pk).exists())

    def test_inexistente_404(self):
        self.assertEqual(self.client.delete("/api/entradas/9999/").status_code, 404)


# ── CU37 Finalizar ────────────────────────────────────────────────────────────

class FinalizarEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.mp = make_mp("Balanceado", stock_inicial=100)
        self.e = make_entrada(self.g)
        add_linea(self.e, self.mp, 30)

    def finalizar(self, entrada=None):
        entrada = entrada or self.e
        return self.client.post(f"/api/entradas/{entrada.pk}/finalizar/")

    def stock(self, mp=None):
        mp = mp or self.mp
        data = self.client.get(f"/api/materias-primas/{mp.pk}/").data
        return Decimal(str(data["stock_actual"]))

    def test_finalizar_exitoso(self):
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "F")
        self.assertEqual(resp.data["estado_display"], "Finalizada")

    def test_persiste_en_la_base(self):
        self.finalizar()
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, Entrada.ESTADO_FINALIZADA)

    def test_baja_el_stock_de_la_materia_prima(self):
        self.assertEqual(self.stock(), Decimal("100"))
        self.finalizar()
        self.assertEqual(self.stock(), Decimal("70"))

    def test_doble_finalizacion_es_409_y_no_descuenta_dos_veces(self):
        self.finalizar()
        self.assertEqual(self.finalizar().status_code, 409)
        self.assertEqual(self.stock(), Decimal("70"))

    def test_stock_insuficiente_al_finalizar_no_cambia_nada(self):
        # Entre la carga y la finalización otra entrada consumió el stock.
        otra = make_entrada(self.g, dia=10)
        add_linea(otra, self.mp, 80)
        self.assertEqual(self.finalizar(otra).status_code, 200)
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Stock insuficiente", str(resp.data))
        self.e.refresh_from_db()
        self.assertEqual(self.e.estado, Entrada.ESTADO_PENDIENTE)
        self.assertEqual(self.stock(), Decimal("20"))

    def test_con_varias_lineas_basta_una_sin_stock(self):
        mp2 = make_mp("Vacuna", stock_inicial=1)
        add_linea(self.e, mp2, 5)
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Vacuna", str(resp.data))
        self.assertEqual(self.stock(), Decimal("100"))

    def test_descuenta_cada_materia_prima(self):
        mp2 = make_mp("Vacuna", stock_inicial=10)
        add_linea(self.e, mp2, 2.5)
        self.finalizar()
        self.assertEqual(self.stock(mp2), Decimal("7.5"))

    def test_entrada_finalizada_no_se_modifica(self):
        self.finalizar()
        resp = self.client.patch(f"/api/entradas/{self.e.pk}/", {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_inexistente_404(self):
        self.assertEqual(self.client.post("/api/entradas/9999/finalizar/").status_code, 404)


# ── Stock de materias primas ──────────────────────────────────────────────────

class StockMateriaPrimaEntradaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.g = make_galpon()
        self.mp = make_mp("Balanceado", stock_inicial=100)

    def datos(self):
        return self.client.get(f"/api/materias-primas/{self.mp.pk}/").data

    def descarte_stock(self, cantidad, estado=Descarte.ESTADO_FINALIZADO):
        d = Descarte.objects.create(
            categoria=Descarte.CATEGORIA_STOCK, fecha=fecha(9), estado=estado
        )
        LineaDescarte.objects.create(
            id_descarte=d, id_materia_prima=self.mp, cantidad=cantidad, motivo="vencido"
        )
        return d

    def test_sin_entradas_el_stock_es_el_inicial(self):
        d = self.datos()
        self.assertEqual(Decimal(str(d["stock_entradas"])), Decimal("0"))
        self.assertEqual(Decimal(str(d["stock_actual"])), Decimal("100"))

    def test_las_pendientes_no_restan(self):
        e = make_entrada(self.g)
        add_linea(e, self.mp, 40)
        self.assertEqual(Decimal(str(self.datos()["stock_actual"])), Decimal("100"))

    def test_las_finalizadas_restan_y_se_ven_en_stock_entradas(self):
        e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA)
        add_linea(e, self.mp, 40)
        d = self.datos()
        self.assertEqual(Decimal(str(d["stock_entradas"])), Decimal("40"))
        self.assertEqual(Decimal(str(d["stock_actual"])), Decimal("60"))

    def test_resta_entradas_y_descartes_juntos(self):
        e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA)
        add_linea(e, self.mp, 40)
        self.descarte_stock(10)
        self.assertEqual(Decimal(str(self.datos()["stock_actual"])), Decimal("50"))

    def test_suma_varias_entradas_finalizadas(self):
        for dia, cant in [(5, 10), (6, 15)]:
            e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA, dia=dia)
            add_linea(e, self.mp, cant)
        self.assertEqual(Decimal(str(self.datos()["stock_entradas"])), Decimal("25"))

    def test_el_listado_trae_el_stock_calculado(self):
        e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA)
        add_linea(e, self.mp, 40)
        resp = self.client.get("/api/materias-primas/")
        fila = next(m for m in resp.data["results"] if m["id_materia_prima"] == self.mp.pk)
        self.assertEqual(Decimal(str(fila["stock_actual"])), Decimal("60"))

    def test_un_descarte_de_stock_ya_no_puede_superar_lo_que_quedo(self):
        e = make_entrada(self.g, estado=Entrada.ESTADO_FINALIZADA)
        add_linea(e, self.mp, 90)
        resp = self.client.post(
            "/api/descartes/",
            dict(
                categoria="S", fecha="2026-08-09T10:00:00Z",
                lineas=[{"id_materia_prima": self.mp.pk, "cantidad": "20", "motivo": "x"}],
            ),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hay 10", str(resp.data))

    def test_una_entrada_ya_no_puede_superar_lo_que_dejo_un_descarte(self):
        self.descarte_stock(70)
        resp = self.client.post(
            "/api/entradas/", payload(self.g, [linea(self.mp, "40")]), format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("hay 30", str(resp.data))


# ── Existencias por galpón ────────────────────────────────────────────────────

class ExistenciasGalponTests(TestCase):
    """GET /api/galpones/{id}/existencias/: ingresado − descartado en el galpón."""

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        auth(self.client, self.admin)
        self.g = make_galpon("Galpón 1")
        self.otro = make_galpon("Galpón 2")
        self.mp = make_mp("Balanceado", stock_inicial=1000)
        self.mp2 = make_mp("Vacuna", stock_inicial=1000, unidad="u")

    def url(self, galpon=None):
        return f"/api/galpones/{(galpon or self.g).pk}/existencias/"

    def entrada(self, mp, cantidad, galpon=None, estado=Entrada.ESTADO_FINALIZADA, dia=9):
        e = make_entrada(galpon or self.g, estado=estado, dia=dia)
        add_linea(e, mp, cantidad)
        return e

    def descarte(self, mp, cantidad, galpon=None, categoria=Descarte.CATEGORIA_GALPON,
                 estado=Descarte.ESTADO_FINALIZADO):
        galpon = galpon or self.g
        d = Descarte.objects.create(
            categoria=categoria, fecha=fecha(9), estado=estado,
            id_galpon=galpon if categoria == Descarte.CATEGORIA_GALPON else None,
        )
        LineaDescarte.objects.create(
            id_descarte=d, id_galpon=d.id_galpon, id_materia_prima=mp,
            cantidad=cantidad, motivo="se pudrió",
        )
        return d

    def fila(self, resp, mp):
        return next(f for f in resp.data if f["id_materia_prima"] == mp.pk)

    def test_sin_movimientos_lista_vacia(self):
        resp = self.client.get(self.url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_suma_las_entradas_finalizadas(self):
        self.entrada(self.mp, 40, dia=5)
        self.entrada(self.mp, 25, dia=6)
        fila = self.fila(self.client.get(self.url()), self.mp)
        self.assertEqual(Decimal(fila["ingresado"]), Decimal("65"))
        self.assertEqual(Decimal(fila["descartado"]), Decimal("0"))
        self.assertEqual(Decimal(fila["existencia_estimada"]), Decimal("65"))
        self.assertEqual(fila["materia_prima"], "Balanceado")
        self.assertEqual(fila["unidad"], "kg")

    def test_las_entradas_pendientes_no_cuentan(self):
        self.entrada(self.mp, 40, estado=Entrada.ESTADO_PENDIENTE)
        self.assertEqual(self.client.get(self.url()).data, [])

    def test_el_descarte_de_galpon_finalizado_resta(self):
        self.entrada(self.mp, 40)
        self.descarte(self.mp, 5)
        fila = self.fila(self.client.get(self.url()), self.mp)
        self.assertEqual(Decimal(fila["descartado"]), Decimal("5"))
        self.assertEqual(Decimal(fila["existencia_estimada"]), Decimal("35"))

    def test_no_resta_descartes_pendientes_de_stock_ni_de_otro_galpon(self):
        self.entrada(self.mp, 40)
        self.descarte(self.mp, 3, estado=Descarte.ESTADO_PENDIENTE)
        self.descarte(self.mp, 4, categoria=Descarte.CATEGORIA_STOCK)
        self.descarte(self.mp, 6, galpon=self.otro)
        fila = self.fila(self.client.get(self.url()), self.mp)
        self.assertEqual(Decimal(fila["existencia_estimada"]), Decimal("40"))

    def test_nunca_es_negativa(self):
        self.entrada(self.mp, 10)
        self.descarte(self.mp, 25)
        fila = self.fila(self.client.get(self.url()), self.mp)
        self.assertEqual(Decimal(fila["existencia_estimada"]), Decimal("0"))
        self.assertEqual(Decimal(fila["descartado"]), Decimal("25"))

    def test_separa_por_galpon_y_por_materia_prima(self):
        self.entrada(self.mp, 40)
        self.entrada(self.mp2, 7)
        self.entrada(self.mp, 99, galpon=self.otro)
        resp = self.client.get(self.url())
        self.assertEqual([f["materia_prima"] for f in resp.data], ["Balanceado", "Vacuna"])
        self.assertEqual(Decimal(self.fila(resp, self.mp)["ingresado"]), Decimal("40"))
        resp2 = self.client.get(self.url(self.otro))
        self.assertEqual(Decimal(self.fila(resp2, self.mp)["ingresado"]), Decimal("99"))

    def test_no_altera_el_stock_general_de_la_materia_prima(self):
        self.entrada(self.mp, 40)
        self.descarte(self.mp, 5)
        datos = self.client.get(f"/api/materias-primas/{self.mp.pk}/").data
        self.assertEqual(Decimal(str(datos["stock_actual"])), Decimal("960"))

    def test_galpon_inexistente_404(self):
        self.assertEqual(self.client.get("/api/galpones/9999/existencias/").status_code, 404)

    def test_todos_los_roles_pueden_verlo_y_sin_token_401(self):
        self.entrada(self.mp, 40)
        for usuario in (make_operario(), make_consulta()):
            c = APIClient()
            auth(c, usuario)
            if usuario.rol == Usuario.ROL_OPERARIO:
                # El operario solo ve los galpones que tiene asignados.
                self.assertEqual(c.get(self.url()).status_code, 404)
                UsuarioDelGalpon.objects.create(id_galpon=self.g, id_usuario=usuario)
            self.assertEqual(c.get(self.url()).status_code, 200, usuario.usuario)
        self.assertEqual(APIClient().get(self.url()).status_code, 401)


# ── Permisos ──────────────────────────────────────────────────────────────────

class PermisosEntradaTests(TestCase):

    def setUp(self):
        self.g = make_galpon()
        self.mp = make_mp()
        self.admin = make_admin()
        self.operario = make_operario()
        self.consulta = make_consulta()
        self.e = make_entrada(self.g)
        add_linea(self.e, self.mp, 5)

    def cliente(self, usuario=None):
        c = APIClient()
        if usuario:
            auth(c, usuario)
        return c

    def crear(self, c):
        return c.post("/api/entradas/", payload(self.g, [linea(self.mp, "1")]), format="json")

    def test_administrador_y_operario_hacen_todo(self):
        for usuario in (self.admin, self.operario):
            c = self.cliente(usuario)
            self.assertEqual(c.get("/api/entradas/").status_code, 200)
            self.assertEqual(self.crear(c).status_code, 201, usuario.usuario)
            nueva = Entrada.objects.latest("id_entrada")
            self.assertEqual(
                c.patch(f"/api/entradas/{nueva.pk}/", {"observaciones": "x"}, format="json").status_code, 200
            )
            self.assertEqual(c.post(f"/api/entradas/{nueva.pk}/finalizar/").status_code, 200)
            pendiente = make_entrada(self.g, dia=11)
            add_linea(pendiente, self.mp, 1)
            self.assertEqual(c.delete(f"/api/entradas/{pendiente.pk}/").status_code, 204)

    def test_consulta_solo_lee(self):
        c = self.cliente(self.consulta)
        self.assertEqual(c.get("/api/entradas/").status_code, 200)
        self.assertEqual(c.get(f"/api/entradas/{self.e.pk}/").status_code, 200)
        self.assertEqual(self.crear(c).status_code, 403)
        self.assertEqual(
            c.patch(f"/api/entradas/{self.e.pk}/", {"observaciones": "x"}, format="json").status_code, 403
        )
        self.assertEqual(c.post(f"/api/entradas/{self.e.pk}/finalizar/").status_code, 403)
        self.assertEqual(c.delete(f"/api/entradas/{self.e.pk}/").status_code, 403)

    def test_sin_token_401(self):
        c = self.cliente()
        self.assertEqual(c.get("/api/entradas/").status_code, 401)
        self.assertEqual(self.crear(c).status_code, 401)
        self.assertEqual(c.delete(f"/api/entradas/{self.e.pk}/").status_code, 401)
