"""
Tests automatizados del módulo Lotes.

Clases de tests:
    BuscarLoteTests             (6)  CU42 – listar, buscar, filtrar por estado y galpón
    NuevoLoteTests             (12)  CU43 – crear lote con plan de transición (exige una compra de lotes)
    ModificarLoteTests          (5)  CU44 – modificar lote y plan de transición
    BorrarLoteTests             (3)  CU45 – eliminar
    IniciarProduccionTests      (5)  CU46 – Transición → Producción
    VaciarTests                 (5)  CU48 – vaciado sanitario → Finalizado
    PermisosLotesTests         (12)  matriz rol × operación
    FiltradoPorRolTests         (5)  operario ve solo lotes de sus galpones asignados

Total: 53 tests
"""

import datetime
import itertools

from django.test import TestCase
from rest_framework.test import APIClient

from compras.models import Compra, LineaCompra
from galpones.models import Galpon, UsuarioDelGalpon
from proveedores.models import Proveedor
from usuarios.models import Usuario
from .models import Lote, PlanTransicion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_usuario(usuario="testuser", rol=Usuario.ROL_ADMINISTRADOR, estado=Usuario.ESTADO_ACTIVO, **kwargs):
    defaults = dict(
        usuario=usuario,
        email=f"{usuario}@test.com",
        nombre="Test",
        apellido="User",
        dni=f"99{usuario[:6].ljust(6, '0')}",
        rol=rol,
        estado=estado,
    )
    defaults.update(kwargs)
    u = Usuario(**defaults)
    u.set_password("Pass1234!")
    u.save()
    return u


def crear_galpon(nombre="Galpón A", estado=Galpon.ESTADO_ACTIVO):
    return Galpon.objects.create(
        galpon=nombre,
        latitud="-26.808000",
        longitud="-65.217000",
        superficie="200.000000",
        capacidad=500,
        estado=estado,
    )


def token_de(client, usuario_obj):
    resp = client.post(
        "/api/auth/login/",
        {"usuario": usuario_obj.usuario, "password": "Pass1234!"},
        format="json",
    )
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


_nro_factura = itertools.count(1)


def crear_lote_comprado(cantidad=2500, finalizada=True, categoria=Compra.CATEGORIA_LOTES):
    """
    Crea una compra con una línea y devuelve la línea. Por defecto es una compra
    de lotes finalizada: un lote esperando que lo asignen a un galpón.
    """
    proveedor, _ = Proveedor.objects.get_or_create(nombre="Granja Madre S.A.")
    compra = Compra.objects.create(
        id_proveedor=proveedor,
        categoria=categoria,
        nro_factura=f"0001-{next(_nro_factura):08d}",
        fecha=datetime.date(2026, 1, 10),
        estado=Compra.ESTADO_FINALIZADA if finalizada else Compra.ESTADO_PENDIENTE,
    )
    return LineaCompra.objects.create(
        id_compra=compra, cantidad=cantidad, precio_unitario="1500.00"
    )


def payload_lote(galpon, linea=None, **kwargs):
    """
    Payload mínimo válido para crear un lote. Si no se pasa la línea de compra,
    crea una compra de lotes finalizada para asignar.
    """
    if linea is None:
        linea = crear_lote_comprado()
    base = dict(
        id_galpon_id=galpon.id_galpon,
        id_linea_compra=linea.pk,
        fecha_ingreso="2026-01-18",
        observaciones="",
        plan_transicion=dict(
            agua_semana1="4.20",
            alimento_semana1="18.00",
            horas_luz_semana1="10.00",
            agua_semana2="4.80",
            alimento_semana2="21.50",
            horas_luz_semana2="12.00",
            agua_semana3="5.50",
            alimento_semana3="25.00",
            horas_luz_semana3="14.00",
            agua_semana4="6.10",
            alimento_semana4="28.50",
            horas_luz_semana4="16.00",
        ),
    )
    base.update(kwargs)
    return base


def crear_lote(galpon, estado=Lote.ESTADO_TRANSICION, fecha_ingreso=None):
    """Crea un lote con su plan de transición directamente en la base."""
    if fecha_ingreso is None:
        fecha_ingreso = datetime.date(2026, 1, 18)
    lote = Lote.objects.create(
        id_galpon=galpon,
        fecha_ingreso=fecha_ingreso,
        cantidad_inicial=2500,
        cantidad_actual=2500,
        estado=estado,
    )
    PlanTransicion.objects.create(
        id_lote=lote,
        estado=PlanTransicion.ESTADO_EN_CURSO,
        fecha_inicio=fecha_ingreso,
        fecha_fin=fecha_ingreso + datetime.timedelta(days=28),
        agua_semana1="4.20", alimento_semana1="18.00", horas_luz_semana1="10.00",
        agua_semana2="4.80", alimento_semana2="21.50", horas_luz_semana2="12.00",
        agua_semana3="5.50", alimento_semana3="25.00", horas_luz_semana3="14.00",
        agua_semana4="6.10", alimento_semana4="28.50", horas_luz_semana4="16.00",
    )
    return lote


# ---------------------------------------------------------------------------
# CU42 – Buscar Lote
# ---------------------------------------------------------------------------

class BuscarLoteTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin42", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.l1 = crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        self.l2 = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION,
                             fecha_ingreso=datetime.date(2025, 6, 1))
        self.l3 = crear_lote(self.galpon, estado=Lote.ESTADO_FINALIZADO,
                             fecha_ingreso=datetime.date(2025, 1, 1))

    def test_listar_devuelve_todos(self):
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 3)

    def test_filtro_estado_transicion(self):
        resp = self.client.get("/api/lotes/?estado=T")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_estado_produccion(self):
        resp = self.client.get("/api/lotes/?estado=P")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_estado_finalizado(self):
        resp = self.client.get("/api/lotes/?estado=F")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_por_galpon(self):
        otro_galpon = crear_galpon("Galpón B")
        crear_lote(otro_galpon)
        resp = self.client.get(f"/api/lotes/?id_galpon={self.galpon.id_galpon}")
        self.assertEqual(resp.data["count"], 3)

    def test_detalle_incluye_plan_transicion(self):
        resp = self.client.get(f"/api/lotes/{self.l1.id_lote}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("plan_transicion", resp.data)
        self.assertEqual(str(resp.data["plan_transicion"]["agua_semana1"]), "4.20")


# ---------------------------------------------------------------------------
# CU43 – Nuevo Lote
# ---------------------------------------------------------------------------

class NuevoLoteTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin43", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()

    def test_crear_lote_exitoso(self):
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.status_code, 201)

    def test_estado_inicial_transicion(self):
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.data["estado"], Lote.ESTADO_TRANSICION)

    def test_cantidad_actual_igual_a_inicial(self):
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.data["cantidad_actual"], resp.data["cantidad_inicial"])

    def test_plan_transicion_creado(self):
        self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(PlanTransicion.objects.count(), 1)

    def test_fecha_fin_plan_es_28_dias_despues(self):
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        plan = resp.data["plan_transicion"]
        fecha_inicio = datetime.date.fromisoformat(plan["fecha_inicio"])
        fecha_fin = datetime.date.fromisoformat(plan["fecha_fin"])
        self.assertEqual((fecha_fin - fecha_inicio).days, 28)

    def test_cantidad_inicial_sale_de_la_compra(self):
        """Lo que mande el cliente en cantidad_inicial se ignora."""
        linea = crear_lote_comprado(cantidad=1800)
        resp = self.client.post(
            "/api/lotes/",
            payload_lote(self.galpon, linea, cantidad_inicial=99),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["cantidad_inicial"], 1800)
        self.assertEqual(resp.data["cantidad_actual"], 1800)

    def test_sin_lote_comprado_error(self):
        payload = payload_lote(self.galpon)
        del payload["id_linea_compra"]
        resp = self.client.post("/api/lotes/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_linea_compra", resp.data)
        self.assertEqual(Lote.objects.count(), 0)

    def test_lote_comprado_vincula_la_linea(self):
        linea = crear_lote_comprado()
        resp = self.client.post(
            "/api/lotes/", payload_lote(self.galpon, linea), format="json"
        )
        self.assertEqual(resp.status_code, 201)
        linea.refresh_from_db()
        self.assertEqual(linea.id_lote_id, resp.data["id_lote"])
        self.assertEqual(resp.data["compra"]["nro_factura"], linea.id_compra.nro_factura)

    def test_lote_comprado_no_disponible_error(self):
        """Compra pendiente, de materias primas o ya asignada: no se puede asignar."""
        otro = crear_galpon("Galpón B")
        for linea in (
            crear_lote_comprado(finalizada=False),
            crear_lote_comprado(categoria=Compra.CATEGORIA_MATERIAS_PRIMAS),
        ):
            resp = self.client.post(
                "/api/lotes/", payload_lote(self.galpon, linea), format="json"
            )
            self.assertEqual(resp.status_code, 400)
        linea = crear_lote_comprado()
        ok = self.client.post("/api/lotes/", payload_lote(self.galpon, linea), format="json")
        self.assertEqual(ok.status_code, 201)
        repetido = self.client.post("/api/lotes/", payload_lote(otro, linea), format="json")
        self.assertEqual(repetido.status_code, 400)
        self.assertIn("ya fue asignado", str(repetido.data["id_linea_compra"]))

    def test_galpon_inactivo_no_aceptado(self):
        galpon_inactivo = crear_galpon("Inactivo", estado=Galpon.ESTADO_INACTIVO)
        resp = self.client.post(
            "/api/lotes/", payload_lote(galpon_inactivo), format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_fecha_vaciado_nula_al_crear(self):
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertIsNone(resp.data["fecha_vaciado"])

    def test_galpon_ocupado_rechaza_nuevo_lote(self):
        """Un galpón con lote activo (T o P) no puede recibir otro lote."""
        # Crear un lote activo en el mismo galpón
        crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# CU44 – Modificar Lote
# ---------------------------------------------------------------------------

class ModificarLoteTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin44", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)

    def test_modificar_observaciones(self):
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/",
            {"observaciones": "nueva observación"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["observaciones"], "nueva observación")

    def test_modificar_plan_transicion(self):
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/",
            {"plan_transicion": {"agua_semana1": "9.99"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.data["plan_transicion"]["agua_semana1"]), "9.99")

    def test_modificacion_parcial_no_afecta_otros_campos(self):
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/",
            {"observaciones": "x"},
            format="json",
        )
        self.assertEqual(resp.data["cantidad_inicial"], self.lote.cantidad_inicial)

    def test_no_se_puede_cambiar_estado_via_patch(self):
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/",
            {"estado": Lote.ESTADO_PRODUCCION},
            format="json",
        )
        # El campo estado es read_only: el patch no lo modifica
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.estado, Lote.ESTADO_TRANSICION)

    def test_modificar_lote_inexistente(self):
        resp = self.client.patch("/api/lotes/9999/", {"observaciones": "x"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU45 – Borrar Lote
# ---------------------------------------------------------------------------

class BorrarLoteTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin45", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)

    def test_borrar_lote(self):
        resp = self.client.delete(f"/api/lotes/{self.lote.id_lote}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Lote.objects.filter(id_lote=self.lote.id_lote).exists())

    def test_borrar_lote_elimina_plan(self):
        id_lote = self.lote.id_lote
        self.client.delete(f"/api/lotes/{id_lote}/")
        self.assertFalse(PlanTransicion.objects.filter(id_lote_id=id_lote).exists())

    def test_borrar_lote_inexistente(self):
        resp = self.client.delete("/api/lotes/9999/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU46 – Iniciar Producción (Transición → Producción)
# ---------------------------------------------------------------------------

class IniciarProduccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin46", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)

    def test_iniciar_produccion_exitoso(self):
        resp = self.client.post(f"/api/lotes/{self.lote.id_lote}/iniciar-produccion/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], Lote.ESTADO_PRODUCCION)

    def test_iniciar_produccion_persiste_en_base(self):
        self.client.post(f"/api/lotes/{self.lote.id_lote}/iniciar-produccion/")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.estado, Lote.ESTADO_PRODUCCION)

    def test_plan_queda_finalizado(self):
        self.client.post(f"/api/lotes/{self.lote.id_lote}/iniciar-produccion/")
        plan = PlanTransicion.objects.get(id_lote=self.lote)
        self.assertEqual(plan.estado, PlanTransicion.ESTADO_FINALIZADO)

    def test_lote_ya_en_produccion_devuelve_409(self):
        lote_prod = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        resp = self.client.post(f"/api/lotes/{lote_prod.id_lote}/iniciar-produccion/")
        self.assertEqual(resp.status_code, 409)

    def test_lote_finalizado_no_puede_iniciar_produccion(self):
        lote_fin = crear_lote(self.galpon, estado=Lote.ESTADO_FINALIZADO)
        resp = self.client.post(f"/api/lotes/{lote_fin.id_lote}/iniciar-produccion/")
        self.assertEqual(resp.status_code, 409)


# ---------------------------------------------------------------------------
# CU48 – Vaciado sanitario (→ Finalizado)
# ---------------------------------------------------------------------------

class VaciarTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin48", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()

    def test_vaciar_desde_produccion(self):
        lote = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        resp = self.client.post(f"/api/lotes/{lote.id_lote}/vaciar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], Lote.ESTADO_FINALIZADO)

    def test_vaciar_registra_fecha_vaciado(self):
        lote = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        self.client.post(f"/api/lotes/{lote.id_lote}/vaciar/")
        lote.refresh_from_db()
        self.assertEqual(lote.fecha_vaciado, datetime.date.today())

    def test_vaciar_desde_transicion(self):
        lote = crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        resp = self.client.post(f"/api/lotes/{lote.id_lote}/vaciar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], Lote.ESTADO_FINALIZADO)

    def test_vaciar_lote_ya_finalizado_409(self):
        lote = crear_lote(self.galpon, estado=Lote.ESTADO_FINALIZADO)
        resp = self.client.post(f"/api/lotes/{lote.id_lote}/vaciar/")
        self.assertEqual(resp.status_code, 409)

    def test_vaciar_lote_inexistente(self):
        resp = self.client.post("/api/lotes/9999/vaciar/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Permisos: matriz rol × operación
# ---------------------------------------------------------------------------

class PermisosLotesTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_perm", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_perm", rol=Usuario.ROL_OPERARIO)
        self.consulta = crear_usuario("con_perm", rol=Usuario.ROL_CONSULTA)
        self.galpon = crear_galpon()
        # galpon2 se usa en test_admin_puede_crear: el galpon principal
        # ya tiene self.lote activo (estado T), por lo que un segundo lote
        # en el mismo galpón sería rechazado por la validación de ocupación.
        self.galpon2 = crear_galpon("Galpón B")
        # El operario está asignado al galpón para poder ver los lotes
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.galpon)
        self.lote = crear_lote(self.galpon)

    def _login(self, usuario_obj):
        token_de(self.client, usuario_obj)

    # --- Administrador puede hacer todo ---
    def test_admin_puede_listar(self):
        self._login(self.admin)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_puede_crear(self):
        self._login(self.admin)
        # galpon2 está libre (sin lotes activos); galpon ya tiene self.lote en T
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon2), format="json")
        self.assertEqual(resp.status_code, 201)

    def test_admin_puede_modificar(self):
        self._login(self.admin)
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/", {"observaciones": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_admin_puede_eliminar(self):
        self._login(self.admin)
        resp = self.client.delete(f"/api/lotes/{self.lote.id_lote}/")
        self.assertEqual(resp.status_code, 204)

    # --- Operario solo puede leer ---
    def test_operario_puede_listar(self):
        self._login(self.operario)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_no_puede_crear(self):
        self._login(self.operario)
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_modificar(self):
        self._login(self.operario)
        resp = self.client.patch(
            f"/api/lotes/{self.lote.id_lote}/", {"observaciones": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_vaciar(self):
        self._login(self.operario)
        resp = self.client.post(f"/api/lotes/{self.lote.id_lote}/vaciar/")
        self.assertEqual(resp.status_code, 403)

    # --- Consulta solo puede leer ---
    def test_consulta_puede_listar(self):
        self._login(self.consulta)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.status_code, 200)

    def test_consulta_no_puede_crear(self):
        self._login(self.consulta)
        resp = self.client.post("/api/lotes/", payload_lote(self.galpon), format="json")
        self.assertEqual(resp.status_code, 403)

    # --- Sin token ---
    def test_sin_token_no_puede_listar(self):
        self.client.credentials()
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.status_code, 401)

    def test_sin_token_no_puede_crear(self):
        self.client.credentials()
        resp = self.client.post("/api/lotes/", {}, format="json")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Filtrado por rol en get_queryset
# ---------------------------------------------------------------------------

class FiltradoPorRolTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_rol", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_rol", rol=Usuario.ROL_OPERARIO)
        self.consulta = crear_usuario("con_rol", rol=Usuario.ROL_CONSULTA)
        self.g1 = crear_galpon("Galpón 1")
        self.g2 = crear_galpon("Galpón 2")
        # operario solo asignado a g1
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.g1)
        self.lote_g1 = crear_lote(self.g1)
        self.lote_g2 = crear_lote(self.g2)

    def test_operario_ve_solo_lotes_de_sus_galpones(self):
        token_de(self.client, self.operario)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["id_lote"], self.lote_g1.id_lote)

    def test_operario_no_puede_ver_lote_de_galpon_no_asignado(self):
        token_de(self.client, self.operario)
        resp = self.client.get(f"/api/lotes/{self.lote_g2.id_lote}/")
        self.assertEqual(resp.status_code, 404)

    def test_operario_sin_galpones_ve_lista_vacia(self):
        operario_sin = crear_usuario("op_sin", rol=Usuario.ROL_OPERARIO, dni="55555555")
        token_de(self.client, operario_sin)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.data["count"], 0)

    def test_administrador_ve_todos_los_lotes(self):
        token_de(self.client, self.admin)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.data["count"], 2)

    def test_consulta_ve_todos_los_lotes(self):
        token_de(self.client, self.consulta)
        resp = self.client.get("/api/lotes/")
        self.assertEqual(resp.data["count"], 2)
