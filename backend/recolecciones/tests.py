"""
Tests automatizados del módulo Recolecciones.

Clases de tests:
    BuscarRecoleccionTests        (5)  listar, filtrar, detalle
    CrearRecoleccionTests         (9)  CU-REC-CREATE – crear recolección con líneas
    EditarRecoleccionTests        (6)  CU-REC-EDIT – editar recolección pendiente
    BorrarRecoleccionTests        (4)  CU-REC-DEL – eliminar
    FinalizarRecoleccionTests     (5)  CU-REC-FIN – finalizar recolección
    PermisosRecoleccionTests     (10)  matriz rol × operación
    LoteFKTests                   (3)  Opción B: id_lote FK en Recoleccion

Total: 42 tests
"""

import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from galpones.models import Galpon, UsuarioDelGalpon
from lotes.models import Lote, PlanTransicion
from productos.models import Producto
from usuarios.models import Usuario

from .models import LineaRecoleccion, Recoleccion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_usuario(usuario="testuser", rol=Usuario.ROL_ADMINISTRADOR,
                  estado=Usuario.ESTADO_ACTIVO, **kwargs):
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


def crear_lote(galpon, estado=Lote.ESTADO_PRODUCCION, fecha_ingreso=None):
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
    plan_estado = (
        PlanTransicion.ESTADO_FINALIZADO
        if estado == Lote.ESTADO_PRODUCCION or estado == Lote.ESTADO_FINALIZADO
        else PlanTransicion.ESTADO_EN_CURSO
    )
    PlanTransicion.objects.create(
        id_lote=lote,
        estado=plan_estado,
        fecha_inicio=fecha_ingreso,
        fecha_fin=fecha_ingreso + datetime.timedelta(days=28),
        agua_semana1="4.20", alimento_semana1="18.00", horas_luz_semana1="10.00",
        agua_semana2="4.80", alimento_semana2="21.50", horas_luz_semana2="12.00",
        agua_semana3="5.50", alimento_semana3="25.00", horas_luz_semana3="14.00",
        agua_semana4="6.10", alimento_semana4="28.50", horas_luz_semana4="16.00",
    )
    return lote


def crear_producto(nombre="Huevo AA", estado=Producto.ESTADO_ACTIVO):
    return Producto.objects.create(
        producto=nombre,
        descripcion="Test",
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


def payload_recoleccion(galpon, producto, **kwargs):
    """Payload mínimo válido para crear una recolección."""
    base = dict(
        id_galpon_id=galpon.id_galpon,
        fecha="2026-06-15T08:00:00",
        observaciones="",
        lineas=[
            {"id_producto_id": producto.id_producto, "cantidad": 100},
        ],
    )
    base.update(kwargs)
    return base


def crear_recoleccion(galpon, lote, producto, estado=Recoleccion.ESTADO_PENDIENTE):
    """Crea una recolección con una línea directamente en la base."""
    rec = Recoleccion.objects.create(
        id_galpon=galpon,
        id_lote=lote,
        fecha=datetime.datetime(2026, 6, 15, 8, 0),
        estado=estado,
    )
    LineaRecoleccion.objects.create(
        id_recoleccion=rec,
        id_galpon=galpon,
        id_producto=producto,
        cantidad=100,
    )
    return rec


# ---------------------------------------------------------------------------
# Buscar recolecciones
# ---------------------------------------------------------------------------

class BuscarRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_buscar")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)
        self.producto = crear_producto()
        self.rec1 = crear_recoleccion(self.galpon, self.lote, self.producto)
        self.rec2 = crear_recoleccion(
            self.galpon, self.lote, self.producto, estado=Recoleccion.ESTADO_FINALIZADA
        )

    def test_listar_devuelve_todas(self):
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_filtro_por_estado_pendiente(self):
        resp = self.client.get("/api/recolecciones/?estado=P")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_por_estado_finalizada(self):
        resp = self.client.get("/api/recolecciones/?estado=F")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_por_galpon(self):
        galpon2 = crear_galpon("Galpón B")
        lote2 = crear_lote(galpon2)
        crear_recoleccion(galpon2, lote2, self.producto)
        resp = self.client.get(f"/api/recolecciones/?id_galpon={self.galpon.id_galpon}")
        self.assertEqual(resp.data["count"], 2)

    def test_detalle_incluye_lineas_y_lote(self):
        resp = self.client.get(f"/api/recolecciones/{self.rec1.id_recoleccion}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("lineas", resp.data)
        self.assertEqual(len(resp.data["lineas"]), 1)
        self.assertIn("lote", resp.data)
        self.assertIsNotNone(resp.data["lote"])


# ---------------------------------------------------------------------------
# Crear recolección
# ---------------------------------------------------------------------------

class CrearRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_crear")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        self.producto = crear_producto()

    def test_crear_exitoso(self):
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_estado_inicial_pendiente(self):
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.data["estado"], Recoleccion.ESTADO_PENDIENTE)

    def test_lote_asignado_automaticamente(self):
        """Al crear, id_lote debe quedar seteado con el lote activo del galpón."""
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIsNotNone(resp.data["lote"])
        self.assertEqual(resp.data["lote"]["id_lote"], self.lote.id_lote)

    def test_linea_creada(self):
        self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(LineaRecoleccion.objects.count(), 1)

    def test_galpon_sin_lote_activo_devuelve_400(self):
        """Si el galpón no tiene lote activo (T o P) la API devuelve 400."""
        galpon_vacio = crear_galpon("Sin Lote")
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(galpon_vacio, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_galpon_con_lote_finalizado_devuelve_400(self):
        """Un galpón cuyo único lote está en estado F tampoco es válido."""
        galpon2 = crear_galpon("Solo Finalizado")
        crear_lote(galpon2, estado=Lote.ESTADO_FINALIZADO)
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(galpon2, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_sin_lineas_devuelve_400(self):
        payload = payload_recoleccion(self.galpon, self.producto)
        payload["lineas"] = []
        resp = self.client.post("/api/recolecciones/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_producto_duplicado_en_lineas_devuelve_400(self):
        payload = payload_recoleccion(self.galpon, self.producto)
        payload["lineas"].append({"id_producto_id": self.producto.id_producto, "cantidad": 50})
        resp = self.client.post("/api/recolecciones/", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_producto_inactivo_rechazado(self):
        prod_inactivo = crear_producto("Huevo B", estado=Producto.ESTADO_INACTIVO)
        payload = payload_recoleccion(self.galpon, prod_inactivo)
        resp = self.client.post("/api/recolecciones/", payload, format="json")
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Editar recolección
# ---------------------------------------------------------------------------

class EditarRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_editar")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)
        self.producto = crear_producto()
        self.rec = crear_recoleccion(self.galpon, self.lote, self.producto)

    def test_editar_observaciones(self):
        resp = self.client.patch(
            f"/api/recolecciones/{self.rec.id_recoleccion}/",
            {"observaciones": "nueva obs"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["observaciones"], "nueva obs")

    def test_editar_lineas_reemplaza_las_existentes(self):
        prod2 = crear_producto("Huevo B")
        resp = self.client.patch(
            f"/api/recolecciones/{self.rec.id_recoleccion}/",
            {"lineas": [{"id_producto_id": prod2.id_producto, "cantidad": 200}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(LineaRecoleccion.objects.filter(
            id_recoleccion=self.rec
        ).count(), 1)
        self.assertEqual(
            LineaRecoleccion.objects.get(id_recoleccion=self.rec).id_producto_id,
            prod2.id_producto,
        )

    def test_no_se_puede_editar_estado_via_patch(self):
        resp = self.client.patch(
            f"/api/recolecciones/{self.rec.id_recoleccion}/",
            {"estado": Recoleccion.ESTADO_FINALIZADA},
            format="json",
        )
        self.rec.refresh_from_db()
        self.assertEqual(self.rec.estado, Recoleccion.ESTADO_PENDIENTE)

    def test_editar_recoleccion_finalizada_devuelve_400(self):
        """No se pueden editar las líneas de una recolección finalizada."""
        rec_final = crear_recoleccion(
            self.galpon, self.lote, self.producto,
            estado=Recoleccion.ESTADO_FINALIZADA,
        )
        resp = self.client.patch(
            f"/api/recolecciones/{rec_final.id_recoleccion}/",
            {"observaciones": "intento edición"},
            format="json",
        )
        # Las reglas de negocio (solo lectura para finalizadas) se validan en la vista
        self.assertEqual(resp.status_code, 400)

    def test_editar_inexistente(self):
        resp = self.client.patch("/api/recolecciones/9999/", {}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_producto_duplicado_en_edicion_devuelve_400(self):
        resp = self.client.patch(
            f"/api/recolecciones/{self.rec.id_recoleccion}/",
            {
                "lineas": [
                    {"id_producto_id": self.producto.id_producto, "cantidad": 10},
                    {"id_producto_id": self.producto.id_producto, "cantidad": 20},
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Borrar recolección
# ---------------------------------------------------------------------------

class BorrarRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_borrar")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)
        self.producto = crear_producto()

    def test_borrar_exitoso(self):
        rec = crear_recoleccion(self.galpon, self.lote, self.producto)
        resp = self.client.delete(f"/api/recolecciones/{rec.id_recoleccion}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Recoleccion.objects.filter(pk=rec.id_recoleccion).exists())

    def test_borrar_elimina_lineas(self):
        rec = crear_recoleccion(self.galpon, self.lote, self.producto)
        id_rec = rec.id_recoleccion
        self.client.delete(f"/api/recolecciones/{id_rec}/")
        self.assertFalse(LineaRecoleccion.objects.filter(id_recoleccion_id=id_rec).exists())

    def test_borrar_finalizada_permitido_para_admin(self):
        rec = crear_recoleccion(
            self.galpon, self.lote, self.producto,
            estado=Recoleccion.ESTADO_FINALIZADA,
        )
        resp = self.client.delete(f"/api/recolecciones/{rec.id_recoleccion}/")
        self.assertEqual(resp.status_code, 204)

    def test_borrar_inexistente(self):
        resp = self.client.delete("/api/recolecciones/9999/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Finalizar recolección
# ---------------------------------------------------------------------------

class FinalizarRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_fin")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon)
        self.producto = crear_producto()

    def test_finalizar_exitoso(self):
        rec = crear_recoleccion(self.galpon, self.lote, self.producto)
        resp = self.client.post(f"/api/recolecciones/{rec.id_recoleccion}/finalizar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], Recoleccion.ESTADO_FINALIZADA)

    def test_finalizar_persiste_en_base(self):
        rec = crear_recoleccion(self.galpon, self.lote, self.producto)
        self.client.post(f"/api/recolecciones/{rec.id_recoleccion}/finalizar/")
        rec.refresh_from_db()
        self.assertEqual(rec.estado, Recoleccion.ESTADO_FINALIZADA)

    def test_finalizar_recoleccion_ya_finalizada_devuelve_400(self):
        rec = crear_recoleccion(
            self.galpon, self.lote, self.producto,
            estado=Recoleccion.ESTADO_FINALIZADA,
        )
        resp = self.client.post(f"/api/recolecciones/{rec.id_recoleccion}/finalizar/")
        self.assertEqual(resp.status_code, 400)

    def test_finalizar_inexistente(self):
        resp = self.client.post("/api/recolecciones/9999/finalizar/")
        self.assertEqual(resp.status_code, 404)

    def test_respuesta_incluye_lote(self):
        rec = crear_recoleccion(self.galpon, self.lote, self.producto)
        resp = self.client.post(f"/api/recolecciones/{rec.id_recoleccion}/finalizar/")
        self.assertIn("lote", resp.data)
        self.assertEqual(resp.data["lote"]["id_lote"], self.lote.id_lote)


# ---------------------------------------------------------------------------
# Permisos: matriz rol × operación
# ---------------------------------------------------------------------------

class PermisosRecoleccionTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_perm_rec")
        self.operario = crear_usuario("op_perm_rec", rol=Usuario.ROL_OPERARIO,
                                     dni="98765432")
        self.consulta = crear_usuario("con_perm_rec", rol=Usuario.ROL_CONSULTA,
                                     dni="11111111")
        self.galpon = crear_galpon()
        UsuarioDelGalpon.objects.create(
            id_usuario=self.operario, id_galpon=self.galpon
        )
        self.lote = crear_lote(self.galpon)
        self.producto = crear_producto()
        self.rec = crear_recoleccion(self.galpon, self.lote, self.producto)

    def _login(self, u):
        token_de(self.client, u)

    # --- Lectura: todos pueden ---
    def test_admin_puede_listar(self):
        self._login(self.admin)
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_puede_listar(self):
        self._login(self.operario)
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 200)

    def test_consulta_puede_listar(self):
        self._login(self.consulta)
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 200)

    # --- Crear: admin y operario ---
    def test_admin_puede_crear(self):
        self._login(self.admin)
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_operario_puede_crear(self):
        self._login(self.operario)
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_consulta_no_puede_crear(self):
        self._login(self.consulta)
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    # --- Eliminar: solo admin ---
    def test_admin_puede_eliminar(self):
        self._login(self.admin)
        resp = self.client.delete(f"/api/recolecciones/{self.rec.id_recoleccion}/")
        self.assertEqual(resp.status_code, 204)

    def test_operario_no_puede_eliminar(self):
        self._login(self.operario)
        resp = self.client.delete(f"/api/recolecciones/{self.rec.id_recoleccion}/")
        self.assertEqual(resp.status_code, 403)

    # --- Sin token ---
    def test_sin_token_no_puede_listar(self):
        self.client.credentials()
        resp = self.client.get("/api/recolecciones/")
        self.assertEqual(resp.status_code, 401)

    def test_sin_token_no_puede_crear(self):
        self.client.credentials()
        resp = self.client.post("/api/recolecciones/", {}, format="json")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Opción B: FK id_lote en Recoleccion
# ---------------------------------------------------------------------------

class LoteFKTests(TestCase):
    """
    Verifica que el lote se almacena en la recolección al momento de crearla
    (FK Opción B) y que el historial permanece intacto si el lote del galpón
    cambia posteriormente.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin_lote_fk")
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()
        self.lote_original = crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        self.producto = crear_producto()

    def test_lote_se_guarda_en_recoleccion(self):
        """El campo id_lote de la recolección apunta al lote activo del galpón."""
        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        rec = Recoleccion.objects.get(pk=resp.data["id_recoleccion"])
        self.assertEqual(rec.id_lote_id, self.lote_original.id_lote)

    def test_lote_en_recoleccion_no_cambia_al_vaciar_galpon(self):
        """
        Si se vacía el lote del galpón (→ Finalizado) y se crea un nuevo lote,
        la recolección anterior sigue mostrando el lote original.
        """
        # Crear recolección con el lote original
        rec = crear_recoleccion(self.galpon, self.lote_original, self.producto)

        # Vaciar el lote original (→ Finalizado)
        self.lote_original.estado = Lote.ESTADO_FINALIZADO
        self.lote_original.fecha_vaciado = datetime.date.today()
        self.lote_original.save()

        # Crear un nuevo lote en el mismo galpón
        nuevo_lote = crear_lote(
            self.galpon,
            estado=Lote.ESTADO_PRODUCCION,
            fecha_ingreso=datetime.date.today(),
        )

        # La recolección aún debe apuntar al lote original
        resp = self.client.get(f"/api/recolecciones/{rec.id_recoleccion}/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data["lote"])
        self.assertEqual(resp.data["lote"]["id_lote"], self.lote_original.id_lote)

    def test_galpon_sin_lote_activo_devuelve_400(self):
        """Galpón cuyo único lote está Finalizado → 400 al crear recolección."""
        self.lote_original.estado = Lote.ESTADO_FINALIZADO
        self.lote_original.fecha_vaciado = datetime.date.today()
        self.lote_original.save()

        resp = self.client.post(
            "/api/recolecciones/",
            payload_recoleccion(self.galpon, self.producto),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
