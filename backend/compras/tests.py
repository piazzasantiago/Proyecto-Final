"""
Tests automatizados del módulo Compras.

Clases de tests:
    ListarCompraTests         (9)  listar, buscar por Nº de comprobante y filtrar
    NuevaCompraTests        (20)  crear compras de materias primas y de lotes,
                                   comprobante autoincremental, formas de pago
    ModificarBorrarTests      (8)  editar y eliminar solo mientras está pendiente
    AtomicidadTests           (3)  alta y edición en una sola transacción
    ProximoComprobanteTests   (6)  número con el que se guardaría la próxima compra
    FinalizarCompraTests      (6)  finalizar e impacto en el stock de materias primas
    LotesPendientesTests      (6)  lotes comprados esperando galpón
    RelacionesTests           (3)  protección de proveedores y materias primas con compras
    PermisosComprasTests      (7)  matriz rol × operación

Total: 68 tests
"""

import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from descartes.stock import stock_actual_materia_prima
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from proveedores.models import Proveedor
from usuarios.models import Usuario

from .models import Compra, LineaCompra

HOY = datetime.date.today()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_usuario(usuario="admin1", rol=Usuario.ROL_ADMINISTRADOR):
    u = Usuario(
        usuario=usuario,
        email=f"{usuario}@test.com",
        nombre="Test",
        apellido="User",
        dni=f"88{usuario[:6].ljust(6, '0')}",
        rol=rol,
        estado=Usuario.ESTADO_ACTIVO,
    )
    u.set_password("Pass1234!")
    u.save()
    return u


def autenticar(client, usuario):
    resp = client.post(
        "/api/auth/login/",
        {"usuario": usuario.usuario, "password": "Pass1234!"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")


def crear_proveedor(nombre="Distribuidora Norte", estado=Proveedor.ESTADO_ACTIVO):
    return Proveedor.objects.create(
        nombre=nombre, email="ventas@norte.com", telefono="3815551234", estado=estado
    )


def crear_materia_prima(nombre="Maíz", stock_inicial=0, estado=MateriaPrima.ESTADO_ACTIVO):
    return MateriaPrima.objects.create(
        materia_prima=nombre, unidad="kg", stock_inicial=stock_inicial, estado=estado
    )


def payload_mp(proveedor, mp, **kwargs):
    base = dict(
        id_proveedor=proveedor.pk,
        categoria="M",
        tipo="C",
        fecha=str(HOY),
        observaciones="",
        lineas=[dict(id_materia_prima=mp.pk, cantidad="100.00", precio_unitario="250.50")],
    )
    base.update(kwargs)
    return base


def payload_lotes(proveedor, **kwargs):
    base = dict(
        id_proveedor=proveedor.pk,
        categoria="L",
        tipo="X",
        fecha=str(HOY),
        lineas=[dict(cantidad="2500", precio_unitario="1500.00")],
    )
    base.update(kwargs)
    return base


def crear_compra(proveedor, categoria="M", estado="P",
                 mp=None, cantidad="100", fecha=None, usuario=None):
    compra = Compra.objects.create(
        id_proveedor=proveedor,
        id_usuario=usuario,
        categoria=categoria,
        fecha=fecha or HOY,
        estado=estado,
    )
    LineaCompra.objects.create(
        id_compra=compra,
        id_materia_prima=mp if categoria == "M" else None,
        cantidad=cantidad,
        precio_unitario="10.00",
    )
    return compra


class BaseApiTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario()
        self.client = APIClient()
        autenticar(self.client, self.admin)
        self.proveedor = crear_proveedor()
        self.mp = crear_materia_prima()


# ---------------------------------------------------------------------------
# Listar / buscar
# ---------------------------------------------------------------------------

class ListarCompraTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.otro = crear_proveedor("Granja Sur")
        self.c1 = crear_compra(self.proveedor, mp=self.mp, fecha=datetime.date(2026, 1, 5))
        self.c2 = crear_compra(self.otro, categoria="L", estado="F", fecha=datetime.date(2026, 2, 10))

    def ids(self, query=""):
        resp = self.client.get(f"/api/compras/{query}")
        self.assertEqual(resp.status_code, 200)
        datos = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        return {c["id_compra"] for c in datos}

    def test_lista_todas(self):
        self.assertEqual(self.ids(), {self.c1.pk, self.c2.pk})

    def test_busca_por_numero_de_comprobante(self):
        self.assertEqual(self.ids(f"?search={self.c2.nro_comprobante}"), {self.c2.pk})
        self.assertEqual(self.ids(f"?search={self.c1.pk}"), {self.c1.pk})

    def test_busqueda_sin_digitos_no_devuelve_nada(self):
        self.assertEqual(self.ids("?search=abc"), set())

    def test_filtra_por_categoria(self):
        self.assertEqual(self.ids("?categoria=L"), {self.c2.pk})

    def test_filtra_por_estado(self):
        self.assertEqual(self.ids("?estado=P"), {self.c1.pk})

    def test_filtra_por_proveedor(self):
        self.assertEqual(self.ids(f"?id_proveedor={self.otro.pk}"), {self.c2.pk})

    def test_filtra_por_materia_prima(self):
        otra_mp = crear_materia_prima("Soja")
        c3 = crear_compra(self.otro, mp=otra_mp, fecha=datetime.date(2026, 3, 1))
        self.assertEqual(self.ids(f"?id_materia_prima={self.mp.pk}"), {self.c1.pk})
        self.assertEqual(self.ids(f"?id_materia_prima={otra_mp.pk}"), {c3.pk})

    def test_filtro_por_materia_prima_no_repite_compras(self):
        # Dos líneas de la misma materia prima en una compra: aparece una sola vez.
        LineaCompra.objects.create(
            id_compra=self.c1, id_materia_prima=self.mp, cantidad="5", precio_unitario="10.00"
        )
        resp = self.client.get(f"/api/compras/?id_materia_prima={self.mp.pk}")
        self.assertEqual(resp.data["count"], 1)

    def test_recientes_de_un_proveedor_limitadas_y_ordenadas(self):
        # Lo que usa el detalle del proveedor: las últimas N, la más nueva primero.
        for dia in range(1, 6):
            crear_compra(self.proveedor, mp=self.mp, fecha=datetime.date(2026, 4, dia))
        resp = self.client.get(f"/api/compras/?id_proveedor={self.proveedor.pk}&page_size=4")
        self.assertEqual(resp.data["count"], 6)
        fechas = [c["fecha"] for c in resp.data["results"]]
        self.assertEqual(len(fechas), 4)
        self.assertEqual(fechas, sorted(fechas, reverse=True))
        self.assertEqual(fechas[0], "2026-04-05")

    def test_filtra_por_fecha_desde_y_hasta(self):
        self.assertEqual(self.ids("?fecha_desde=2026-02-01"), {self.c2.pk})
        self.assertEqual(self.ids("?fecha_hasta=2026-01-31"), {self.c1.pk})
        self.assertEqual(
            self.ids("?fecha_desde=2026-01-01&fecha_hasta=2026-12-31"), {self.c1.pk, self.c2.pk}
        )

    def test_detalle_incluye_lineas_y_total(self):
        resp = self.client.get(f"/api/compras/{self.c1.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["lineas"]), 1)
        self.assertEqual(Decimal(str(resp.data["total"])), Decimal("1000.00"))
        self.assertEqual(resp.data["proveedor"]["nombre"], "Distribuidora Norte")

    def test_orden_mas_reciente_primero(self):
        resp = self.client.get("/api/compras/")
        datos = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(datos[0]["id_compra"], self.c2.pk)


# ---------------------------------------------------------------------------
# Alta
# ---------------------------------------------------------------------------

class NuevaCompraTests(BaseApiTests):
    def post(self, payload):
        return self.client.post("/api/compras/", payload, format="json")

    def test_crea_compra_de_materia_prima(self):
        resp = self.post(payload_mp(self.proveedor, self.mp))
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["estado"], "P")
        self.assertEqual(resp.data["categoria"], "M")
        self.assertEqual(Decimal(str(resp.data["total"])), Decimal("25050.00"))

    def test_el_usuario_sale_del_token_y_el_estado_es_pendiente(self):
        resp = self.post(payload_mp(self.proveedor, self.mp, estado="F", id_usuario=999))
        self.assertEqual(resp.status_code, 201, resp.data)
        compra = Compra.objects.get(pk=resp.data["id_compra"])
        self.assertEqual(compra.id_usuario, self.admin)
        self.assertEqual(compra.estado, Compra.ESTADO_PENDIENTE)

    def test_crea_compra_de_lotes(self):
        resp = self.post(payload_lotes(self.proveedor))
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["categoria"], "L")
        self.assertIsNone(resp.data["lineas"][0]["id_materia_prima"])

    def test_el_comprobante_lo_genera_el_sistema(self):
        resp = self.post(payload_mp(self.proveedor, self.mp))
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["nro_comprobante"], f"{resp.data['id_compra']:08d}")
        self.assertNotIn("nro_factura", resp.data)

    def test_el_comprobante_no_se_puede_enviar(self):
        resp = self.post(payload_mp(self.proveedor, self.mp, nro_comprobante="99999999"))
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertNotEqual(resp.data["nro_comprobante"], "99999999")

    def test_los_comprobantes_son_correlativos(self):
        primera = self.post(payload_mp(self.proveedor, self.mp))
        segunda = self.post(payload_mp(self.proveedor, self.mp))
        self.assertEqual(
            int(segunda.data["nro_comprobante"]), int(primera.data["nro_comprobante"]) + 1
        )

    def test_dos_compras_iguales_del_mismo_proveedor_son_validas(self):
        # Ya no hay número de factura cargado a mano que pueda repetirse.
        self.assertEqual(self.post(payload_mp(self.proveedor, self.mp)).status_code, 201)
        self.assertEqual(self.post(payload_mp(self.proveedor, self.mp)).status_code, 201)

    def test_formas_de_pago_disponibles(self):
        esperadas = {"C": "Contado", "X": "Cuenta corriente", "D": "Débito", "R": "Crédito", "O": "Otro"}
        for codigo, nombre in esperadas.items():
            with self.subTest(tipo=codigo):
                resp = self.post(payload_mp(self.proveedor, self.mp, tipo=codigo))
                self.assertEqual(resp.status_code, 201, resp.data)
                self.assertEqual(resp.data["tipo"], codigo)
                self.assertEqual(resp.data["tipo_display"], nombre)

    def test_forma_de_pago_invalida_rechazada(self):
        resp = self.post(payload_mp(self.proveedor, self.mp, tipo="Z"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("tipo", resp.data)

    def test_forma_de_pago_se_puede_cambiar_al_editar(self):
        compra = crear_compra(self.proveedor, mp=self.mp)
        resp = self.client.patch(f"/api/compras/{compra.pk}/", {"tipo": "R"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        compra.refresh_from_db()
        self.assertEqual(compra.tipo, Compra.TIPO_CREDITO)

    def test_proveedor_inactivo_rechazado(self):
        inactivo = crear_proveedor("Inactivo", estado=Proveedor.ESTADO_INACTIVO)
        resp = self.post(payload_mp(inactivo, self.mp))
        self.assertEqual(resp.status_code, 400)

    def test_fecha_futura_rechazada(self):
        futura = str(HOY + datetime.timedelta(days=3))
        resp = self.post(payload_mp(self.proveedor, self.mp, fecha=futura))
        self.assertEqual(resp.status_code, 400)

    def test_sin_lineas_rechazado(self):
        resp = self.post(payload_mp(self.proveedor, self.mp, lineas=[]))
        self.assertEqual(resp.status_code, 400)

    def test_materia_prima_repetida_rechazada(self):
        linea = dict(id_materia_prima=self.mp.pk, cantidad="5", precio_unitario="10")
        resp = self.post(payload_mp(self.proveedor, self.mp, lineas=[linea, dict(linea)]))
        self.assertEqual(resp.status_code, 400)

    def test_materia_prima_inactiva_rechazada(self):
        inactiva = crear_materia_prima("Soja", estado=MateriaPrima.ESTADO_INACTIVO)
        resp = self.post(payload_mp(self.proveedor, inactiva))
        self.assertEqual(resp.status_code, 400)

    def test_linea_de_materia_prima_sin_materia_prima(self):
        resp = self.post(payload_mp(
            self.proveedor, self.mp, lineas=[dict(cantidad="5", precio_unitario="10")]
        ))
        self.assertEqual(resp.status_code, 400)

    def test_cantidad_y_precio_deben_ser_positivos(self):
        for linea in (
            dict(id_materia_prima=self.mp.pk, cantidad="0", precio_unitario="10"),
            dict(id_materia_prima=self.mp.pk, cantidad="5", precio_unitario="0"),
        ):
            resp = self.post(payload_mp(self.proveedor, self.mp, lineas=[linea]))
            self.assertEqual(resp.status_code, 400)

    def test_lotes_con_aves_no_enteras_rechazado(self):
        resp = self.post(payload_lotes(
            self.proveedor, lineas=[dict(cantidad="10.5", precio_unitario="100")]
        ))
        self.assertEqual(resp.status_code, 400)

    def test_lotes_con_materia_prima_rechazado(self):
        resp = self.post(payload_lotes(
            self.proveedor,
            lineas=[dict(id_materia_prima=self.mp.pk, cantidad="10", precio_unitario="100")],
        ))
        self.assertEqual(resp.status_code, 400)

    def test_categoria_invalida(self):
        resp = self.post(payload_mp(self.proveedor, self.mp, categoria="Z"))
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Modificar / borrar
# ---------------------------------------------------------------------------

class ModificarBorrarTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.compra = crear_compra(self.proveedor, mp=self.mp)
        self.finalizada = crear_compra(self.proveedor, estado="F", mp=self.mp)

    def test_edita_compra_pendiente(self):
        payload = payload_mp(
            self.proveedor, self.mp,
            lineas=[dict(id_materia_prima=self.mp.pk, cantidad="7", precio_unitario="3")],
        )
        resp = self.client.put(f"/api/compras/{self.compra.pk}/", payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.compra.refresh_from_db()
        self.assertEqual(self.compra.lineas.get().cantidad, Decimal("7"))

    def test_edicion_parcial_reemplaza_solo_lo_enviado(self):
        resp = self.client.patch(
            f"/api/compras/{self.compra.pk}/", {"observaciones": "Entrega parcial"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(self.compra.lineas.count(), 1)

    def test_no_edita_compra_finalizada(self):
        resp = self.client.patch(
            f"/api/compras/{self.finalizada.pk}/", {"observaciones": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_el_comprobante_no_se_edita(self):
        original = self.compra.nro_comprobante
        resp = self.client.patch(
            f"/api/compras/{self.compra.pk}/", {"nro_comprobante": "12345678"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["nro_comprobante"], original)

    def test_no_cambia_la_categoria(self):
        resp = self.client.patch(
            f"/api/compras/{self.compra.pk}/", {"categoria": "L"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_elimina_compra_pendiente(self):
        resp = self.client.delete(f"/api/compras/{self.compra.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Compra.objects.filter(pk=self.compra.pk).exists())
        self.assertFalse(LineaCompra.objects.filter(id_compra=self.compra.pk).exists())

    def test_no_elimina_compra_finalizada(self):
        resp = self.client.delete(f"/api/compras/{self.finalizada.pk}/")
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Compra.objects.filter(pk=self.finalizada.pk).exists())

    def test_compra_inexistente(self):
        self.assertEqual(self.client.delete("/api/compras/9999/").status_code, 404)


# ---------------------------------------------------------------------------
# Atomicidad: cabecera y líneas se guardan juntas o no se guardan
# ---------------------------------------------------------------------------

class AtomicidadTests(BaseApiTests):
    def _falla_en_la_segunda_linea(self):
        """Parche de LineaCompra.objects.create: la primera línea se crea y la segunda falla."""
        original = LineaCompra.objects.create
        llamadas = []

        def create(**kwargs):
            llamadas.append(kwargs)
            if len(llamadas) == 2:
                raise RuntimeError("falla simulada a mitad de camino")
            return original(**kwargs)

        return patch.object(LineaCompra.objects, "create", side_effect=create)

    def _dos_lineas(self):
        otra = crear_materia_prima("Soja")
        return [
            dict(id_materia_prima=self.mp.pk, cantidad="10", precio_unitario="5"),
            dict(id_materia_prima=otra.pk, cantidad="20", precio_unitario="8"),
        ]

    def test_si_falla_el_alta_no_queda_compra_ni_lineas(self):
        with self._falla_en_la_segunda_linea():
            with self.assertRaises(RuntimeError):
                self.client.post(
                    "/api/compras/",
                    payload_mp(self.proveedor, self.mp, lineas=self._dos_lineas()),
                    format="json",
                )
        self.assertEqual(Compra.objects.count(), 0)
        self.assertEqual(LineaCompra.objects.count(), 0)

    def test_si_falla_la_edicion_se_conservan_las_lineas_originales(self):
        compra = crear_compra(self.proveedor, mp=self.mp, cantidad="100")
        with self._falla_en_la_segunda_linea():
            with self.assertRaises(RuntimeError):
                self.client.patch(
                    f"/api/compras/{compra.pk}/",
                    {"observaciones": "cambio", "lineas": self._dos_lineas()},
                    format="json",
                )
        compra.refresh_from_db()
        self.assertEqual(compra.observaciones, "")
        self.assertEqual(compra.lineas.count(), 1)
        self.assertEqual(compra.lineas.get().cantidad, Decimal("100"))

    def test_alta_exitosa_guarda_cabecera_y_lineas(self):
        resp = self.client.post(
            "/api/compras/",
            payload_mp(self.proveedor, self.mp, lineas=self._dos_lineas()),
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Compra.objects.get(pk=resp.data["id_compra"]).lineas.count(), 2)


# ---------------------------------------------------------------------------
# Próximo número de comprobante (lo muestra el formulario de alta)
# ---------------------------------------------------------------------------

class ProximoComprobanteTests(BaseApiTests):
    URL = "/api/compras/proximo-comprobante/"

    def proximo(self):
        resp = self.client.get(self.URL)
        self.assertEqual(resp.status_code, 200, resp.data)
        return resp.data["nro_comprobante"]

    def test_es_un_numero_de_ocho_digitos(self):
        self.assertRegex(self.proximo(), r"^\d{8}$")

    def test_coincide_con_el_de_la_compra_que_se_guarda(self):
        esperado = self.proximo()
        resp = self.client.post("/api/compras/", payload_mp(self.proveedor, self.mp), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["nro_comprobante"], esperado)

    def test_avanza_con_cada_compra(self):
        primero = int(self.proximo())
        crear_compra(self.proveedor, mp=self.mp)
        self.assertEqual(int(self.proximo()), primero + 1)

    def test_el_numero_de_una_compra_borrada_no_se_reutiliza(self):
        compra = crear_compra(self.proveedor, mp=self.mp)
        borrada = compra.nro_comprobante
        compra.delete()
        self.assertGreater(int(self.proximo()), int(borrada))
        resp = self.client.post("/api/compras/", payload_mp(self.proveedor, self.mp), format="json")
        self.assertNotEqual(resp.data["nro_comprobante"], borrada)

    def test_consulta_puede_verlo_y_operario_no(self):
        consulta = APIClient()
        autenticar(consulta, crear_usuario("cons1", Usuario.ROL_CONSULTA))
        self.assertEqual(consulta.get(self.URL).status_code, 200)
        operario = APIClient()
        autenticar(operario, crear_usuario("oper1", Usuario.ROL_OPERARIO))
        self.assertEqual(operario.get(self.URL).status_code, 403)

    def test_sin_token_401(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)


# ---------------------------------------------------------------------------
# Finalizar y stock
# ---------------------------------------------------------------------------

class FinalizarCompraTests(BaseApiTests):
    def stock(self):
        self.mp.refresh_from_db()
        return self.client.get(f"/api/materias-primas/{self.mp.pk}/").data

    def test_finalizar_pasa_a_finalizada(self):
        compra = crear_compra(self.proveedor, mp=self.mp)
        resp = self.client.post(f"/api/compras/{compra.pk}/finalizar/")
        self.assertEqual(resp.status_code, 200, resp.data)
        compra.refresh_from_db()
        self.assertEqual(compra.estado, Compra.ESTADO_FINALIZADA)

    def test_finalizar_dos_veces_da_409(self):
        compra = crear_compra(self.proveedor, mp=self.mp)
        self.client.post(f"/api/compras/{compra.pk}/finalizar/")
        resp = self.client.post(f"/api/compras/{compra.pk}/finalizar/")
        self.assertEqual(resp.status_code, 409)

    def test_compra_pendiente_no_suma_stock(self):
        crear_compra(self.proveedor, mp=self.mp, cantidad="40")
        self.assertEqual(Decimal(str(self.stock()["stock_actual"])), Decimal("0"))

    def test_compra_finalizada_suma_stock(self):
        self.mp.stock_inicial = Decimal("10")
        self.mp.save()
        compra = crear_compra(self.proveedor, mp=self.mp, cantidad="40")
        self.client.post(f"/api/compras/{compra.pk}/finalizar/")
        datos = self.stock()
        self.assertEqual(Decimal(str(datos["stock_compras"])), Decimal("40"))
        self.assertEqual(Decimal(str(datos["stock_actual"])), Decimal("50"))

    def test_stock_actual_calculado_incluye_compras(self):
        crear_compra(self.proveedor, mp=self.mp, cantidad="25", estado="F")
        self.assertEqual(stock_actual_materia_prima(self.mp), Decimal("25"))

    def test_compra_de_lotes_no_suma_stock_de_materias_primas(self):
        crear_compra(self.proveedor, categoria="L", estado="F", cantidad="3000")
        self.assertEqual(Decimal(str(self.stock()["stock_actual"])), Decimal("0"))


# ---------------------------------------------------------------------------
# Lotes pendientes de asignar
# ---------------------------------------------------------------------------

class LotesPendientesTests(BaseApiTests):
    def test_vacio_sin_compras_de_lotes(self):
        resp = self.client.get("/api/compras/lotes-pendientes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])

    def test_compra_de_lotes_pendiente_no_aparece(self):
        crear_compra(self.proveedor, categoria="L", cantidad="2500")
        self.assertEqual(self.client.get("/api/compras/lotes-pendientes/").data, [])

    def test_compra_finalizada_de_lotes_aparece(self):
        compra = crear_compra(self.proveedor, categoria="L", estado="F", cantidad="2500")
        datos = self.client.get("/api/compras/lotes-pendientes/").data
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["id_compra"], compra.pk)
        self.assertEqual(datos[0]["cantidad"], 2500)
        self.assertEqual(datos[0]["proveedor_nombre"], "Distribuidora Norte")

    def test_compra_de_materias_primas_no_aparece(self):
        crear_compra(self.proveedor, mp=self.mp, estado="F")
        self.assertEqual(self.client.get("/api/compras/lotes-pendientes/").data, [])

    def test_lote_ya_asignado_no_aparece(self):
        compra = crear_compra(self.proveedor, categoria="L", estado="F")
        linea = compra.lineas.get()
        lote = Lote.objects.create(
            id_galpon=_galpon(), fecha_ingreso=HOY, cantidad_inicial=100, cantidad_actual=100
        )
        linea.id_lote = lote
        linea.save()
        self.assertEqual(self.client.get("/api/compras/lotes-pendientes/").data, [])

    def test_si_se_borra_el_lote_vuelve_a_quedar_pendiente(self):
        compra = crear_compra(self.proveedor, categoria="L", estado="F")
        linea = compra.lineas.get()
        lote = Lote.objects.create(
            id_galpon=_galpon(), fecha_ingreso=HOY, cantidad_inicial=100, cantidad_actual=100
        )
        linea.id_lote = lote
        linea.save()
        lote.delete()
        self.assertEqual(len(self.client.get("/api/compras/lotes-pendientes/").data), 1)


def _galpon():
    from galpones.models import Galpon

    return Galpon.objects.create(
        galpon="Galpón T", latitud="-26.808000", longitud="-65.217000",
        superficie="200.000000", capacidad=500, estado=Galpon.ESTADO_ACTIVO,
    )


# ---------------------------------------------------------------------------
# Relaciones
# ---------------------------------------------------------------------------

class RelacionesTests(BaseApiTests):
    def test_proveedor_con_compras_no_se_elimina(self):
        crear_compra(self.proveedor, mp=self.mp)
        resp = self.client.delete(f"/api/proveedores/{self.proveedor.pk}/")
        self.assertEqual(resp.status_code, 409)

    def test_materia_prima_con_compras_no_se_elimina(self):
        crear_compra(self.proveedor, mp=self.mp)
        resp = self.client.delete(f"/api/materias-primas/{self.mp.pk}/")
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(MateriaPrima.objects.filter(pk=self.mp.pk).exists())

    def test_materia_prima_sin_compras_se_elimina(self):
        resp = self.client.delete(f"/api/materias-primas/{self.mp.pk}/")
        self.assertEqual(resp.status_code, 204)


# ---------------------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------------------

class PermisosComprasTests(TestCase):
    def setUp(self):
        self.proveedor = crear_proveedor()
        self.mp = crear_materia_prima()
        self.compra = crear_compra(self.proveedor, mp=self.mp)

    def cliente(self, rol):
        client = APIClient()
        autenticar(client, crear_usuario(f"u{rol}", rol))
        return client

    def test_sin_token_401(self):
        self.assertEqual(APIClient().get("/api/compras/").status_code, 401)

    def test_administrador_crea(self):
        resp = self.cliente(Usuario.ROL_ADMINISTRADOR).post(
            "/api/compras/", payload_mp(self.proveedor, self.mp),
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_consulta_lee(self):
        client = self.cliente(Usuario.ROL_CONSULTA)
        self.assertEqual(client.get("/api/compras/").status_code, 200)
        self.assertEqual(client.get(f"/api/compras/{self.compra.pk}/").status_code, 200)

    def test_consulta_no_escribe(self):
        client = self.cliente(Usuario.ROL_CONSULTA)
        self.assertEqual(
            client.post("/api/compras/", payload_mp(self.proveedor, self.mp), format="json").status_code, 403
        )
        self.assertEqual(
            client.patch(f"/api/compras/{self.compra.pk}/", {"observaciones": "x"}, format="json").status_code, 403
        )
        self.assertEqual(client.delete(f"/api/compras/{self.compra.pk}/").status_code, 403)
        self.assertEqual(client.post(f"/api/compras/{self.compra.pk}/finalizar/").status_code, 403)

    def test_operario_no_ve_compras(self):
        client = self.cliente(Usuario.ROL_OPERARIO)
        self.assertEqual(client.get("/api/compras/").status_code, 403)
        self.assertEqual(client.get(f"/api/compras/{self.compra.pk}/").status_code, 403)

    def test_operario_puede_consultar_lotes_pendientes(self):
        resp = self.cliente(Usuario.ROL_OPERARIO).get("/api/compras/lotes-pendientes/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_no_crea_ni_borra(self):
        client = self.cliente(Usuario.ROL_OPERARIO)
        self.assertEqual(
            client.post("/api/compras/", payload_mp(self.proveedor, self.mp), format="json").status_code, 403
        )
        self.assertEqual(client.delete(f"/api/compras/{self.compra.pk}/").status_code, 403)
