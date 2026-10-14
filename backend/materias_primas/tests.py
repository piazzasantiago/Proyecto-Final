"""
Tests automatizados del módulo Materias Primas.

Clases de tests:
    BuscarMateriaPrimaTests      (6)  CU55 – listar, buscar, filtrar
    NuevaMateriaPrimaTests       (6)  CU56 – crear
    ModificarMateriaPrimaTests   (5)  CU57 – modificar
    BorrarMateriaPrimaTests      (2)  CU58 – eliminar
    ActivarMateriaPrimaTests     (4)  CU59 – dar de alta
    DesactivarMateriaPrimaTests  (4)  CU60 – dar de baja
    PermisosMateriaPrimaTests   (12)  matriz rol × operación
    StockMateriaPrimaTests       (5)  stock_minimo, stock_inicial, stock_actual

Total: 44 tests
"""

from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Usuario
from .models import MateriaPrima


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_materia_prima(nombre="Alimento balanceado", estado=MateriaPrima.ESTADO_ACTIVO, **kwargs):
    defaults = dict(
        materia_prima=nombre,
        descripcion="",
        unidad="kg",
        stock_minimo=100,
        stock_inicial=0,
        estado=estado,
    )
    defaults.update(kwargs)
    return MateriaPrima.objects.create(**defaults)


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
    resp = client.post(
        "/api/auth/login/",
        {"usuario": usuario_obj.usuario, "password": "Pass1234!"},
        format="json",
    )
    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


# ---------------------------------------------------------------------------
# CU55 – Buscar Materia Prima
# ---------------------------------------------------------------------------

class BuscarMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin55", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp1 = crear_materia_prima("Alimento balanceado - iniciador")
        self.mp2 = crear_materia_prima("Alimento balanceado - postura")
        self.mp3 = crear_materia_prima("Desinfectante", estado=MateriaPrima.ESTADO_INACTIVO)

    def test_listar_devuelve_todos(self):
        resp = self.client.get("/api/materias-primas/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 3)

    def test_busqueda_por_nombre(self):
        resp = self.client.get("/api/materias-primas/?search=iniciador")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["materia_prima"], "Alimento balanceado - iniciador")

    def test_filtro_estado_activo(self):
        resp = self.client.get("/api/materias-primas/?estado=A")
        self.assertEqual(resp.data["count"], 2)

    def test_filtro_estado_inactivo(self):
        resp = self.client.get("/api/materias-primas/?estado=I")
        self.assertEqual(resp.data["count"], 1)

    def test_sin_resultados(self):
        resp = self.client.get("/api/materias-primas/?search=inexistente")
        self.assertEqual(resp.data["count"], 0)

    def test_detalle(self):
        resp = self.client.get(f"/api/materias-primas/{self.mp1.id_materia_prima}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["materia_prima"], "Alimento balanceado - iniciador")
        self.assertEqual(resp.data["estado_display"], "Activo")


# ---------------------------------------------------------------------------
# CU56 – Nueva Materia Prima
# ---------------------------------------------------------------------------

class NuevaMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin56", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)

    def test_crear_exitoso(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Maíz", "unidad": "kg", "stock_minimo": "300.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_estado_por_defecto_activo(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Vacuna", "unidad": "dosis"},
            format="json",
        )
        self.assertEqual(resp.data["estado"], "A")

    def test_descripcion_opcional(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Cal agrícola"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_nombre_duplicado_error(self):
        crear_materia_prima("Maíz")
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Maíz"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_stock_por_defecto_cero(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Nidales"},
            format="json",
        )
        self.assertEqual(float(resp.data["stock_minimo"]), 0)
        self.assertEqual(float(resp.data["stock_inicial"]), 0)
        self.assertEqual(float(resp.data["stock_actual"]), 0)

    def test_crear_con_unidad_personalizada(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Desinfectante", "unidad": "L", "stock_minimo": "20.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["unidad"], "L")


# ---------------------------------------------------------------------------
# CU57 – Modificar Materia Prima
# ---------------------------------------------------------------------------

class ModificarMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin57", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp = crear_materia_prima("Alimento balanceado")

    def test_modificar_nombre(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"materia_prima": "Alimento balanceado - iniciador"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["materia_prima"], "Alimento balanceado - iniciador")

    def test_modificar_stock_minimo(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"stock_minimo": "250.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(float(resp.data["stock_minimo"]), 250.0)

    def test_modificacion_parcial_no_afecta_otros_campos(self):
        self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"descripcion": "nueva descripción"},
            format="json",
        )
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.materia_prima, "Alimento balanceado")
        self.assertEqual(self.mp.descripcion, "nueva descripción")

    def test_no_se_puede_cambiar_estado_via_patch(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"estado": "I"},
            format="json",
        )
        self.mp.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.mp.estado, MateriaPrima.ESTADO_ACTIVO)

    def test_modificar_inexistente(self):
        resp = self.client.patch("/api/materias-primas/9999/", {"materia_prima": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU58 – Borrar Materia Prima
# ---------------------------------------------------------------------------

class BorrarMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin58", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp = crear_materia_prima()

    def test_borrar_materia_prima(self):
        resp = self.client.delete(f"/api/materias-primas/{self.mp.id_materia_prima}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(MateriaPrima.objects.filter(pk=self.mp.id_materia_prima).exists())

    def test_borrar_inexistente(self):
        resp = self.client.delete("/api/materias-primas/9999/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU59 – Dar de Alta Materia Prima
# ---------------------------------------------------------------------------

class ActivarMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin59", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp = crear_materia_prima(estado=MateriaPrima.ESTADO_INACTIVO)

    def test_activar(self):
        resp = self.client.post(f"/api/materias-primas/{self.mp.id_materia_prima}/activar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "A")

    def test_activar_persiste_en_base(self):
        self.client.post(f"/api/materias-primas/{self.mp.id_materia_prima}/activar/")
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.estado, MateriaPrima.ESTADO_ACTIVO)

    def test_activar_idempotencia_409(self):
        mp_activa = crear_materia_prima("Otra activa", estado=MateriaPrima.ESTADO_ACTIVO)
        resp = self.client.post(f"/api/materias-primas/{mp_activa.id_materia_prima}/activar/")
        self.assertEqual(resp.status_code, 409)

    def test_activar_inexistente(self):
        resp = self.client.post("/api/materias-primas/9999/activar/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU60 – Dar de Baja Materia Prima
# ---------------------------------------------------------------------------

class DesactivarMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin60", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp = crear_materia_prima(estado=MateriaPrima.ESTADO_ACTIVO)

    def test_desactivar(self):
        resp = self.client.post(f"/api/materias-primas/{self.mp.id_materia_prima}/desactivar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "I")

    def test_desactivar_persiste_en_base(self):
        self.client.post(f"/api/materias-primas/{self.mp.id_materia_prima}/desactivar/")
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.estado, MateriaPrima.ESTADO_INACTIVO)

    def test_desactivar_idempotencia_409(self):
        mp_inactiva = crear_materia_prima("Otra inactiva", estado=MateriaPrima.ESTADO_INACTIVO)
        resp = self.client.post(f"/api/materias-primas/{mp_inactiva.id_materia_prima}/desactivar/")
        self.assertEqual(resp.status_code, 409)

    def test_desactivar_inexistente(self):
        resp = self.client.post("/api/materias-primas/9999/desactivar/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Permisos: matriz rol × operación
# ---------------------------------------------------------------------------

class PermisosMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_perm_mp", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_perm_mp", rol=Usuario.ROL_OPERARIO)
        self.consulta = crear_usuario("con_perm_mp", rol=Usuario.ROL_CONSULTA)
        self.mp = crear_materia_prima()

    def _login(self, usuario_obj):
        token_de(self.client, usuario_obj)

    def _sin_token(self):
        self.client.credentials()

    # --- Administrador puede hacer todo ---
    def test_admin_puede_crear(self):
        self._login(self.admin)
        resp = self.client.post(
            "/api/materias-primas/", {"materia_prima": "Nueva"}, format="json"
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_puede_modificar(self):
        self._login(self.admin)
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"materia_prima": "Modificada"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_admin_puede_eliminar(self):
        self._login(self.admin)
        resp = self.client.delete(f"/api/materias-primas/{self.mp.id_materia_prima}/")
        self.assertEqual(resp.status_code, 204)

    def test_admin_puede_listar(self):
        self._login(self.admin)
        resp = self.client.get("/api/materias-primas/")
        self.assertEqual(resp.status_code, 200)

    # --- Operario solo puede leer ---
    def test_operario_puede_listar(self):
        self._login(self.operario)
        resp = self.client.get("/api/materias-primas/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_no_puede_crear(self):
        self._login(self.operario)
        resp = self.client.post(
            "/api/materias-primas/", {"materia_prima": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_modificar(self):
        self._login(self.operario)
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"materia_prima": "Y"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_eliminar(self):
        self._login(self.operario)
        resp = self.client.delete(f"/api/materias-primas/{self.mp.id_materia_prima}/")
        self.assertEqual(resp.status_code, 403)

    # --- Consulta solo puede leer ---
    def test_consulta_puede_listar(self):
        self._login(self.consulta)
        resp = self.client.get("/api/materias-primas/")
        self.assertEqual(resp.status_code, 200)

    def test_consulta_no_puede_crear(self):
        self._login(self.consulta)
        resp = self.client.post(
            "/api/materias-primas/", {"materia_prima": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    # --- Sin token ---
    def test_sin_token_no_puede_listar(self):
        self._sin_token()
        resp = self.client.get("/api/materias-primas/")
        self.assertEqual(resp.status_code, 401)

    def test_sin_token_no_puede_crear(self):
        self._sin_token()
        resp = self.client.post("/api/materias-primas/", {}, format="json")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Stock: stock_minimo, stock_inicial, stock_actual (calculado)
# ---------------------------------------------------------------------------

class StockMateriaPrimaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adminstock_mp", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.mp = crear_materia_prima("Alimento base")

    def test_crear_con_stock_inicial(self):
        resp = self.client.post(
            "/api/materias-primas/",
            {"materia_prima": "Maíz", "stock_inicial": "500.00", "unidad": "kg"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(float(resp.data["stock_inicial"]), 500.0)
        self.assertEqual(float(resp.data["stock_actual"]), 500.0)

    def test_modificar_stock_inicial_via_patch(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"stock_inicial": "80.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(float(resp.data["stock_inicial"]), 80.0)
        self.mp.refresh_from_db()
        self.assertEqual(float(self.mp.stock_inicial), 80.0)

    def test_stock_negativo_rechazado(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"stock_inicial": "-5.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.mp.refresh_from_db()
        self.assertEqual(float(self.mp.stock_inicial), 0)

    def test_stock_minimo_negativo_rechazado(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"stock_minimo": "-10.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_stock_actual_es_de_solo_lectura(self):
        resp = self.client.patch(
            f"/api/materias-primas/{self.mp.id_materia_prima}/",
            {"stock_actual": "999.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(float(resp.data["stock_actual"]), 0)
        self.mp.refresh_from_db()
        self.assertEqual(float(self.mp.stock_inicial), 0)
