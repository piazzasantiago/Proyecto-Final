"""
Tests automatizados del módulo Productos.

Clases de tests:
    BuscarProductoTests      (6)  CU50 – listar, buscar, filtrar
    NuevoProductoTests        (4)  CU49 – crear
    ModificarProductoTests    (4)  CU52 – modificar
    BorrarProductoTests       (2)  CU53 – eliminar
    ActivarProductoTests      (4)  CU51 – activar
    DesactivarProductoTests   (4)  CU54 – desactivar
    PermisosProductosTests   (14)  matriz rol × operación (incluye activar/desactivar)

Total: 38 tests
"""

from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Usuario
from .models import Producto


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_producto(nombre="Huevo Nº1", estado=Producto.ESTADO_ACTIVO, **kwargs):
    defaults = dict(
        producto=nombre,
        descripcion="",
        estado=estado,
    )
    defaults.update(kwargs)
    return Producto.objects.create(**defaults)


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


def token_de(client, usuario_obj):
    """Obtiene JWT para el usuario y configura el cliente."""
    resp = client.post(
        "/api/auth/login/",
        {"usuario": usuario_obj.usuario, "password": "Pass1234!"},
        format="json",
    )
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


# ---------------------------------------------------------------------------
# CU50 – Buscar Producto
# ---------------------------------------------------------------------------

class BuscarProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin50", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.p1 = crear_producto("Huevo Nº1 (grande)")
        self.p2 = crear_producto("Huevo Nº2 (mediano)")
        self.p3 = crear_producto("Huevo Nº3 (pequeño)", estado=Producto.ESTADO_INACTIVO)

    def test_listar_devuelve_todos(self):
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 3)

    def test_busqueda_por_nombre(self):
        resp = self.client.get("/api/productos/?search=grande")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["producto"], "Huevo Nº1 (grande)")

    def test_filtro_estado_activo(self):
        resp = self.client.get("/api/productos/?estado=A")
        self.assertEqual(resp.data["count"], 2)

    def test_filtro_estado_inactivo(self):
        resp = self.client.get("/api/productos/?estado=I")
        self.assertEqual(resp.data["count"], 1)

    def test_sin_resultados(self):
        resp = self.client.get("/api/productos/?search=inexistente")
        self.assertEqual(resp.data["count"], 0)

    def test_detalle(self):
        resp = self.client.get(f"/api/productos/{self.p1.id_producto}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["producto"], "Huevo Nº1 (grande)")
        self.assertEqual(resp.data["estado_display"], "Activo")


# ---------------------------------------------------------------------------
# CU49 – Nuevo Producto
# ---------------------------------------------------------------------------

class NuevoProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin49", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)

    def test_crear_producto_exitoso(self):
        resp = self.client.post(
            "/api/productos/",
            {"producto": "Huevo Nº1 (grande)", "descripcion": "Huevos grandes"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_estado_por_defecto_activo(self):
        resp = self.client.post("/api/productos/", {"producto": "Huevo Nº2"}, format="json")
        self.assertEqual(resp.data["estado"], "A")

    def test_descripcion_opcional(self):
        resp = self.client.post("/api/productos/", {"producto": "Huevo Nº3"}, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_nombre_duplicado_error(self):
        crear_producto("Huevo Nº1")
        resp = self.client.post("/api/productos/", {"producto": "Huevo Nº1"}, format="json")
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# CU52 – Modificar Producto
# ---------------------------------------------------------------------------

class ModificarProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin52", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.producto = crear_producto("Huevo Nº1")

    def test_modificar_nombre(self):
        resp = self.client.patch(
            f"/api/productos/{self.producto.id_producto}/", {"producto": "Huevo Grande"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["producto"], "Huevo Grande")

    def test_modificacion_parcial_no_afecta_otros_campos(self):
        self.client.patch(
            f"/api/productos/{self.producto.id_producto}/", {"descripcion": "nueva"}, format="json"
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.producto, "Huevo Nº1")
        self.assertEqual(self.producto.descripcion, "nueva")

    def test_no_se_puede_cambiar_estado_via_patch(self):
        resp = self.client.patch(
            f"/api/productos/{self.producto.id_producto}/", {"estado": "I"}, format="json"
        )
        self.producto.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.producto.estado, Producto.ESTADO_ACTIVO)

    def test_modificar_producto_inexistente(self):
        resp = self.client.patch("/api/productos/9999/", {"producto": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU53 – Borrar Producto
# ---------------------------------------------------------------------------

class BorrarProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin53", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.producto = crear_producto()

    def test_borrar_producto(self):
        resp = self.client.delete(f"/api/productos/{self.producto.id_producto}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Producto.objects.filter(pk=self.producto.id_producto).exists())

    def test_borrar_producto_inexistente(self):
        resp = self.client.delete("/api/productos/9999/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU51 – Activar Producto
# ---------------------------------------------------------------------------

class ActivarProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin51", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.producto = crear_producto(estado=Producto.ESTADO_INACTIVO)

    def test_activar(self):
        resp = self.client.post(f"/api/productos/{self.producto.id_producto}/activar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "A")

    def test_activar_persiste_en_base(self):
        self.client.post(f"/api/productos/{self.producto.id_producto}/activar/")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.estado, Producto.ESTADO_ACTIVO)

    def test_activar_idempotencia_409(self):
        producto_activo = crear_producto("Otro", estado=Producto.ESTADO_ACTIVO)
        resp = self.client.post(f"/api/productos/{producto_activo.id_producto}/activar/")
        self.assertEqual(resp.status_code, 409)

    def test_activar_producto_inexistente(self):
        resp = self.client.post("/api/productos/9999/activar/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU54 – Desactivar Producto
# ---------------------------------------------------------------------------

class DesactivarProductoTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin54", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.producto = crear_producto(estado=Producto.ESTADO_ACTIVO)

    def test_desactivar(self):
        resp = self.client.post(f"/api/productos/{self.producto.id_producto}/desactivar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "I")

    def test_desactivar_persiste_en_base(self):
        self.client.post(f"/api/productos/{self.producto.id_producto}/desactivar/")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.estado, Producto.ESTADO_INACTIVO)

    def test_desactivar_idempotencia_409(self):
        producto_inactivo = crear_producto("Otro", estado=Producto.ESTADO_INACTIVO)
        resp = self.client.post(f"/api/productos/{producto_inactivo.id_producto}/desactivar/")
        self.assertEqual(resp.status_code, 409)

    def test_desactivar_producto_inexistente(self):
        resp = self.client.post("/api/productos/9999/desactivar/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Permisos: matriz rol × operación
# ---------------------------------------------------------------------------

class PermisosProductosTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_perm_prod", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_perm_prod", rol=Usuario.ROL_OPERARIO)
        self.consulta = crear_usuario("con_perm_prod", rol=Usuario.ROL_CONSULTA)
        self.producto = crear_producto()

    def _login(self, usuario_obj):
        token_de(self.client, usuario_obj)

    def _sin_token(self):
        self.client.credentials()

    # --- Administrador puede hacer todo ---
    def test_admin_puede_crear(self):
        self._login(self.admin)
        resp = self.client.post("/api/productos/", {"producto": "X"}, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_admin_puede_modificar(self):
        self._login(self.admin)
        resp = self.client.patch(
            f"/api/productos/{self.producto.id_producto}/", {"producto": "Y"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_admin_puede_eliminar(self):
        self._login(self.admin)
        resp = self.client.delete(f"/api/productos/{self.producto.id_producto}/")
        self.assertEqual(resp.status_code, 204)

    def test_admin_puede_listar(self):
        self._login(self.admin)
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, 200)

    # --- Operario solo puede leer ---
    def test_operario_puede_listar(self):
        self._login(self.operario)
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_no_puede_crear(self):
        self._login(self.operario)
        resp = self.client.post("/api/productos/", {"producto": "X"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_modificar(self):
        self._login(self.operario)
        resp = self.client.patch(
            f"/api/productos/{self.producto.id_producto}/", {"producto": "Y"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_eliminar(self):
        self._login(self.operario)
        resp = self.client.delete(f"/api/productos/{self.producto.id_producto}/")
        self.assertEqual(resp.status_code, 403)

    # --- Consulta solo puede leer ---
    def test_consulta_puede_listar(self):
        self._login(self.consulta)
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, 200)

    def test_consulta_no_puede_crear(self):
        self._login(self.consulta)
        resp = self.client.post("/api/productos/", {"producto": "X"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # --- Sin token ---
    def test_sin_token_no_puede_listar(self):
        self._sin_token()
        resp = self.client.get("/api/productos/")
        self.assertEqual(resp.status_code, 401)

    def test_sin_token_no_puede_crear(self):
        self._sin_token()
        resp = self.client.post("/api/productos/", {}, format="json")
        self.assertEqual(resp.status_code, 401)

    # --- Acciones activar/desactivar: solo Administrador ---
    def test_operario_no_puede_activar(self):
        self._login(self.operario)
        resp = self.client.post(f"/api/productos/{self.producto.id_producto}/activar/")
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_desactivar(self):
        self._login(self.operario)
        resp = self.client.post(f"/api/productos/{self.producto.id_producto}/desactivar/")
        self.assertEqual(resp.status_code, 403)
