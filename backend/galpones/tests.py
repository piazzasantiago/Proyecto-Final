"""
Tests automatizados del módulo Galpones.

Clases de tests:
    BuscarGalponTests       (6)  CU09 – listar, buscar, filtrar
    NuevoGalponTests        (9)  CU10 – crear
    ModificarGalponTests    (4)  CU11 – modificar
    BorrarGalponTests       (2)  CU12 – eliminar
    AltaGalponTests         (4)  CU13 – dar de alta
    BajaGalponTests         (4)  CU14 – dar de baja
    PermisosGalponesTests  (14)  matriz rol × operación
    UsuariosDelGalponTests (10)  asignación de operarios y filtrado por rol

Total: 52 tests
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from usuarios.models import Usuario
from .models import Galpon, UsuarioDelGalpon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_galpon(nombre="Galpón A", estado=Galpon.ESTADO_ACTIVO, **kwargs):
    defaults = dict(
        galpon=nombre,
        latitud="-26.808000",
        longitud="-65.217000",
        superficie="200.000000",
        capacidad=500,
        estado=estado,
        descripcion="",
    )
    defaults.update(kwargs)
    return Galpon.objects.create(**defaults)


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
# CU09 – Buscar Galpón
# ---------------------------------------------------------------------------

class BuscarGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin09", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.g1 = crear_galpon("Galpón Norte", descripcion="norte")
        self.g2 = crear_galpon("Galpón Sur", estado=Galpon.ESTADO_INACTIVO)

    def test_listar_devuelve_todos(self):
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)

    def test_busqueda_por_nombre(self):
        resp = self.client.get("/api/galpones/?search=Norte")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["galpon"], "Galpón Norte")

    def test_busqueda_por_descripcion(self):
        resp = self.client.get("/api/galpones/?search=norte")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_estado_activo(self):
        resp = self.client.get("/api/galpones/?estado=A")
        self.assertEqual(resp.data["count"], 1)

    def test_filtro_estado_inactivo(self):
        resp = self.client.get("/api/galpones/?estado=I")
        self.assertEqual(resp.data["count"], 1)

    def test_sin_resultados(self):
        resp = self.client.get("/api/galpones/?search=xxxxxxxxx")
        self.assertEqual(resp.data["count"], 0)


# ---------------------------------------------------------------------------
# CU10 – Nuevo Galpón
# ---------------------------------------------------------------------------

class NuevoGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin10", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)

    def _payload(self, **kwargs):
        base = dict(
            galpon="Galpón Test",
            latitud="-26.808",
            longitud="-65.217",
            superficie="300",
            capacidad=600,
            descripcion="",
        )
        base.update(kwargs)
        return base

    def test_crear_galpon_exitoso(self):
        resp = self.client.post("/api/galpones/", self._payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["galpon"], "Galpón Test")

    def test_estado_por_defecto_activo(self):
        resp = self.client.post("/api/galpones/", self._payload(), format="json")
        self.assertEqual(resp.data["estado"], "A")

    def test_estado_display_activo(self):
        resp = self.client.post("/api/galpones/", self._payload(), format="json")
        self.assertEqual(resp.data["estado_display"], "Activo")

    def test_descripcion_opcional(self):
        payload = self._payload()
        del payload["descripcion"]
        resp = self.client.post("/api/galpones/", payload, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_capacidad_cero_error(self):
        resp = self.client.post("/api/galpones/", self._payload(capacidad=0), format="json")
        self.assertEqual(resp.status_code, 400)

    def test_capacidad_negativa_error(self):
        resp = self.client.post("/api/galpones/", self._payload(capacidad=-1), format="json")
        self.assertEqual(resp.status_code, 400)

    def test_superficie_cero_error(self):
        resp = self.client.post("/api/galpones/", self._payload(superficie="0"), format="json")
        self.assertEqual(resp.status_code, 400)

    def test_superficie_negativa_error(self):
        resp = self.client.post("/api/galpones/", self._payload(superficie="-5"), format="json")
        self.assertEqual(resp.status_code, 400)

    def test_galpon_guardado_en_base(self):
        self.client.post("/api/galpones/", self._payload(), format="json")
        self.assertEqual(Galpon.objects.count(), 1)


# ---------------------------------------------------------------------------
# CU11 – Modificar Galpón
# ---------------------------------------------------------------------------

class ModificarGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin11", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()

    def test_modificar_nombre(self):
        resp = self.client.patch(
            f"/api/galpones/{self.galpon.id_galpon}/",
            {"galpon": "Nuevo Nombre"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["galpon"], "Nuevo Nombre")

    def test_capacidad_invalida_no_guarda(self):
        resp = self.client.patch(
            f"/api/galpones/{self.galpon.id_galpon}/",
            {"capacidad": 0},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_modificar_galpon_inexistente(self):
        resp = self.client.patch("/api/galpones/9999/", {"galpon": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_modificacion_parcial_no_afecta_otros_campos(self):
        resp = self.client.patch(
            f"/api/galpones/{self.galpon.id_galpon}/",
            {"descripcion": "nueva desc"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["galpon"], self.galpon.galpon)


# ---------------------------------------------------------------------------
# CU12 – Borrar Galpón
# ---------------------------------------------------------------------------

class BorrarGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin12", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon()

    def test_borrar_galpon(self):
        resp = self.client.delete(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Galpon.objects.filter(id_galpon=self.galpon.id_galpon).exists())

    def test_borrar_galpon_inexistente(self):
        resp = self.client.delete("/api/galpones/9999/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU13 – Dar de Alta Galpón
# ---------------------------------------------------------------------------

class AltaGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin13", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon(estado=Galpon.ESTADO_INACTIVO)

    def test_dar_de_alta(self):
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/alta/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "A")

    def test_alta_persiste_en_base(self):
        self.client.post(f"/api/galpones/{self.galpon.id_galpon}/alta/")
        self.galpon.refresh_from_db()
        self.assertEqual(self.galpon.estado, Galpon.ESTADO_ACTIVO)

    def test_alta_idempotencia_409(self):
        galpon_activo = crear_galpon("Galpón Activo", estado=Galpon.ESTADO_ACTIVO)
        resp = self.client.post(f"/api/galpones/{galpon_activo.id_galpon}/alta/")
        self.assertEqual(resp.status_code, 409)

    def test_alta_galpon_inexistente(self):
        resp = self.client.post("/api/galpones/9999/alta/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# CU14 – Dar de Baja Galpón
# ---------------------------------------------------------------------------

class BajaGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("admin14", rol=Usuario.ROL_ADMINISTRADOR)
        token_de(self.client, self.admin)
        self.galpon = crear_galpon(estado=Galpon.ESTADO_ACTIVO)

    def test_dar_de_baja(self):
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "I")

    def test_baja_persiste_en_base(self):
        self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.galpon.refresh_from_db()
        self.assertEqual(self.galpon.estado, Galpon.ESTADO_INACTIVO)

    def test_baja_idempotencia_409(self):
        galpon_inactivo = crear_galpon("Galpón Inactivo", estado=Galpon.ESTADO_INACTIVO)
        resp = self.client.post(f"/api/galpones/{galpon_inactivo.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 409)

    def test_baja_galpon_inexistente(self):
        resp = self.client.post("/api/galpones/9999/baja/")
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Permisos: matriz rol × operación
# ---------------------------------------------------------------------------

class PermisosGalponesTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_perm", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_perm", rol=Usuario.ROL_OPERARIO)
        self.consulta = crear_usuario("con_perm", rol=Usuario.ROL_CONSULTA)
        self.galpon = crear_galpon()

    def _login(self, usuario_obj):
        token_de(self.client, usuario_obj)

    def _sin_token(self):
        self.client.credentials()

    # --- Administrador puede hacer todo ---
    def test_admin_puede_crear(self):
        self._login(self.admin)
        resp = self.client.post(
            "/api/galpones/",
            {"galpon": "X", "latitud": "0", "longitud": "0", "superficie": "1", "capacidad": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_admin_puede_modificar(self):
        self._login(self.admin)
        resp = self.client.patch(f"/api/galpones/{self.galpon.id_galpon}/", {"galpon": "Y"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_admin_puede_eliminar(self):
        self._login(self.admin)
        resp = self.client.delete(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertEqual(resp.status_code, 204)

    def test_admin_puede_listar(self):
        self._login(self.admin)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)

    # --- Operario solo puede leer ---
    def test_operario_puede_listar(self):
        self._login(self.operario)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)

    def test_operario_no_puede_crear(self):
        self._login(self.operario)
        resp = self.client.post(
            "/api/galpones/",
            {"galpon": "X", "latitud": "0", "longitud": "0", "superficie": "1", "capacidad": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_modificar(self):
        self._login(self.operario)
        resp = self.client.patch(f"/api/galpones/{self.galpon.id_galpon}/", {"galpon": "Y"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_eliminar(self):
        self._login(self.operario)
        resp = self.client.delete(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertEqual(resp.status_code, 403)

    # --- Consulta solo puede leer ---
    def test_consulta_puede_listar(self):
        self._login(self.consulta)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)

    def test_consulta_no_puede_crear(self):
        self._login(self.consulta)
        resp = self.client.post(
            "/api/galpones/",
            {"galpon": "X", "latitud": "0", "longitud": "0", "superficie": "1", "capacidad": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_consulta_no_puede_modificar(self):
        self._login(self.consulta)
        resp = self.client.patch(f"/api/galpones/{self.galpon.id_galpon}/", {"galpon": "Y"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # --- Sin token ---
    def test_sin_token_no_puede_listar(self):
        self._sin_token()
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 401)

    def test_sin_token_no_puede_crear(self):
        self._sin_token()
        resp = self.client.post("/api/galpones/", {}, format="json")
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# UsuariosDelGalpon – asignación y filtrado por rol
# ---------------------------------------------------------------------------

class UsuariosDelGalponTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_udg", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario1 = crear_usuario("op1_udg", rol=Usuario.ROL_OPERARIO, dni="11111111")
        self.operario2 = crear_usuario("op2_udg", rol=Usuario.ROL_OPERARIO, dni="22222222")
        self.consulta = crear_usuario("con_udg", rol=Usuario.ROL_CONSULTA, dni="33333333")
        self.g1 = crear_galpon("Galpón 1")
        self.g2 = crear_galpon("Galpón 2")
        self.g3 = crear_galpon("Galpón 3")

    # --- Asignación desde el backend ---

    def test_crear_galpon_con_operarios(self):
        token_de(self.client, self.admin)
        resp = self.client.post(
            "/api/galpones/",
            {
                "galpon": "Nuevo",
                "latitud": "0",
                "longitud": "0",
                "superficie": "1",
                "capacidad": 1,
                "operarios_ids": [self.operario1.id_usuario],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(UsuarioDelGalpon.objects.filter(id_galpon__galpon="Nuevo").count(), 1)

    def test_modificar_galpon_actualiza_operarios(self):
        token_de(self.client, self.admin)
        # Asignamos operario1 primero
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        # Reemplazamos con operario2
        resp = self.client.patch(
            f"/api/galpones/{self.g1.id_galpon}/",
            {"operarios_ids": [self.operario2.id_usuario]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        asignados = list(UsuarioDelGalpon.objects.filter(id_galpon=self.g1).values_list("id_usuario_id", flat=True))
        self.assertNotIn(self.operario1.id_usuario, asignados)
        self.assertIn(self.operario2.id_usuario, asignados)

    def test_ids_invalidos_devuelven_400(self):
        token_de(self.client, self.admin)
        resp = self.client.patch(
            f"/api/galpones/{self.g1.id_galpon}/",
            {"operarios_ids": [9999]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_se_puede_asignar_usuario_administrador(self):
        token_de(self.client, self.admin)
        resp = self.client.patch(
            f"/api/galpones/{self.g1.id_galpon}/",
            {"operarios_ids": [self.admin.id_usuario]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    # --- Filtrado por rol en get_queryset ---

    def test_operario_ve_solo_sus_galpones(self):
        # operario1 asignado a g1 y g2, no a g3
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g2)
        token_de(self.client, self.operario1)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)
        ids = [g["id_galpon"] for g in resp.data["results"]]
        self.assertIn(self.g1.id_galpon, ids)
        self.assertIn(self.g2.id_galpon, ids)
        self.assertNotIn(self.g3.id_galpon, ids)

    def test_operario_sin_asignaciones_ve_lista_vacia(self):
        token_de(self.client, self.operario1)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)

    def test_administrador_ve_todos_los_galpones(self):
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        token_de(self.client, self.admin)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.data["count"], 3)

    def test_consulta_ve_todos_los_galpones(self):
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        token_de(self.client, self.consulta)
        resp = self.client.get("/api/galpones/")
        self.assertEqual(resp.data["count"], 3)

    def test_operario_no_puede_ver_galpon_no_asignado(self):
        # operario1 solo tiene g1; intentar acceder a g2 da 404
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        token_de(self.client, self.operario1)
        resp = self.client.get(f"/api/galpones/{self.g2.id_galpon}/")
        self.assertEqual(resp.status_code, 404)

    def test_operario_puede_ver_galpon_asignado(self):
        UsuarioDelGalpon.objects.create(id_usuario=self.operario1, id_galpon=self.g1)
        token_de(self.client, self.operario1)
        resp = self.client.get(f"/api/galpones/{self.g1.id_galpon}/")
        self.assertEqual(resp.status_code, 200)
