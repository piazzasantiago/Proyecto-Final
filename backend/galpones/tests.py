"""
Tests automatizados del módulo Galpones.

Clases de tests:
    BuscarGalponTests       (6)  CU09 – listar, buscar, filtrar
    NuevoGalponTests        (9)  CU10 – crear
    ModificarGalponTests    (4)  CU11 – modificar
    BorrarGalponTests       (4)  CU12 – eliminar (409 si tiene registros asociados, F-19)
    AltaGalponTests         (4)  CU13 – dar de alta
    BajaGalponTests         (9)  CU14 – dar de baja (incluye bloqueo si el
                                  galpón tiene un lote activo)
    PermisosGalponesTests  (18)  matriz rol × operación (incluye alta/baja)
    UsuariosDelGalponTests (10)  asignación de operarios y filtrado por rol
    OperariosInactivosTests (8)  operario dado de baja: se conserva la
                                  asignación pero no se lista, y no se pisa
                                  al editar el galpón
    GalponesLibresTests     (6)  F-10 – ?libre=true: sin lote en curso

Total: 78 tests
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

import datetime

from usuarios.models import Usuario
from lotes.models import Lote
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


def crear_lote(galpon, estado=Lote.ESTADO_TRANSICION):
    """Crea un lote asociado a un galpón, sin plan de transición (no lo necesitan estos tests)."""
    return Lote.objects.create(
        id_galpon=galpon,
        fecha_ingreso=datetime.date(2026, 1, 18),
        cantidad_inicial=2500,
        cantidad_actual=2500,
        estado=estado,
    )


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

    def test_borrar_galpon_con_lotes_devuelve_409(self):
        """F-19: con registros asociados no se borra y se explica por qué."""
        crear_lote(self.galpon)
        resp = self.client.delete(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("lotes", resp.json()["detail"])
        self.assertIn("baja", resp.json()["detail"])
        self.assertTrue(Galpon.objects.filter(id_galpon=self.galpon.id_galpon).exists())

    def test_borrar_galpon_con_lote_finalizado_tambien_devuelve_409(self):
        crear_lote(self.galpon, estado=Lote.ESTADO_FINALIZADO)
        resp = self.client.delete(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertEqual(resp.status_code, 409)


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

    def test_no_se_puede_dar_de_baja_con_lote_en_transicion(self):
        crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 409)

    def test_no_se_puede_dar_de_baja_con_lote_en_produccion(self):
        crear_lote(self.galpon, estado=Lote.ESTADO_PRODUCCION)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 409)

    def test_mensaje_de_error_incluye_codigo_y_estado_del_lote(self):
        lote = crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertIn(lote.codigo, resp.data["detail"])
        self.assertIn("Transición", resp.data["detail"])

    def test_no_se_modifica_estado_en_bd_si_hay_lote_activo(self):
        crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)
        self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.galpon.refresh_from_db()
        self.assertEqual(self.galpon.estado, Galpon.ESTADO_ACTIVO)

    def test_se_puede_dar_de_baja_con_lote_finalizado(self):
        crear_lote(self.galpon, estado=Lote.ESTADO_FINALIZADO)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 200)



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

    # --- Acciones alta/baja: solo Administrador ---
    def test_operario_no_puede_dar_de_alta(self):
        self._login(self.operario)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/alta/")
        self.assertEqual(resp.status_code, 403)

    def test_operario_no_puede_dar_de_baja(self):
        self._login(self.operario)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 403)

    def test_consulta_no_puede_dar_de_alta(self):
        self._login(self.consulta)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/alta/")
        self.assertEqual(resp.status_code, 403)

    def test_consulta_no_puede_dar_de_baja(self):
        self._login(self.consulta)
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/baja/")
        self.assertEqual(resp.status_code, 403)

    def test_sin_token_no_puede_dar_de_alta(self):
        self._sin_token()
        resp = self.client.post(f"/api/galpones/{self.galpon.id_galpon}/alta/")
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


# ---------------------------------------------------------------------------
# Operarios inactivos: se conserva la asignación, pero no se lista ni se
# pisa al editar el galpón (ver GalponSerializer.get_operarios y
# _sincronizar_operarios).
# ---------------------------------------------------------------------------

class OperariosInactivosTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario("adm_oi", rol=Usuario.ROL_ADMINISTRADOR)
        self.operario = crear_usuario("op_oi", rol=Usuario.ROL_OPERARIO, dni="44444444")
        self.galpon = crear_galpon("Galpón OI")
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.galpon)
        token_de(self.client, self.admin)

    def test_operario_activo_aparece_en_detalle(self):
        resp = self.client.get(f"/api/galpones/{self.galpon.id_galpon}/")
        ids = [o["id_usuario"] for o in resp.data["operarios"]]
        self.assertIn(self.operario.id_usuario, ids)

    def test_operario_inactivo_no_aparece_en_detalle(self):
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        resp = self.client.get(f"/api/galpones/{self.galpon.id_galpon}/")
        ids = [o["id_usuario"] for o in resp.data["operarios"]]
        self.assertNotIn(self.operario.id_usuario, ids)

    def test_asignacion_persiste_en_bd_tras_baja_de_operario(self):
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        self.client.get(f"/api/galpones/{self.galpon.id_galpon}/")
        self.assertTrue(
            UsuarioDelGalpon.objects.filter(id_usuario=self.operario, id_galpon=self.galpon).exists()
        )

    def test_operario_reactivado_reaparece_en_detalle(self):
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        self.operario.estado = Usuario.ESTADO_ACTIVO
        self.operario.save()
        resp = self.client.get(f"/api/galpones/{self.galpon.id_galpon}/")
        ids = [o["id_usuario"] for o in resp.data["operarios"]]
        self.assertIn(self.operario.id_usuario, ids)

    def test_no_se_puede_asignar_operario_inactivo(self):
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        otro_galpon = crear_galpon("Galpón OI 2")
        resp = self.client.patch(
            f"/api/galpones/{otro_galpon.id_galpon}/",
            {"operarios_ids": [self.operario.id_usuario]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_editar_galpon_no_borra_asignacion_de_operario_inactivo(self):
        """
        Regresión: guardar el formulario de edición sin tocar el selector de
        operarios (que solo ofrece operarios activos) no debe borrar la
        asignación de un operario que fue dado de baja.
        """
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        resp = self.client.patch(
            f"/api/galpones/{self.galpon.id_galpon}/",
            {"galpon": "Galpón OI (editado)", "operarios_ids": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            UsuarioDelGalpon.objects.filter(id_usuario=self.operario, id_galpon=self.galpon).exists()
        )

    def test_sincronizar_operarios_reemplaza_solo_activos(self):
        """
        Al reemplazar la lista de operarios activos con una nueva, un
        operario inactivo ya asignado no se ve afectado por el reemplazo.
        """
        operario_activo = crear_usuario("op_oi_2", rol=Usuario.ROL_OPERARIO, dni="55555555")
        self.operario.estado = Usuario.ESTADO_INACTIVO
        self.operario.save()
        resp = self.client.patch(
            f"/api/galpones/{self.galpon.id_galpon}/",
            {"operarios_ids": [operario_activo.id_usuario]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        asignados = set(
            UsuarioDelGalpon.objects.filter(id_galpon=self.galpon).values_list("id_usuario_id", flat=True)
        )
        self.assertEqual(asignados, {self.operario.id_usuario, operario_activo.id_usuario})

    def test_operario_filtra_por_estado_dentro_de_sus_galpones(self):
        galpon_inactivo = crear_galpon("Galpón OI Inactivo", estado=Galpon.ESTADO_INACTIVO)
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=galpon_inactivo)
        token_de(self.client, self.operario)

        resp_activos = self.client.get("/api/galpones/", {"estado": "A"})
        ids_activos = [g["id_galpon"] for g in resp_activos.data["results"]]
        self.assertIn(self.galpon.id_galpon, ids_activos)
        self.assertNotIn(galpon_inactivo.id_galpon, ids_activos)

        resp_inactivos = self.client.get("/api/galpones/", {"estado": "I"})
        ids_inactivos = [g["id_galpon"] for g in resp_inactivos.data["results"]]
        self.assertIn(galpon_inactivo.id_galpon, ids_inactivos)
        self.assertNotIn(self.galpon.id_galpon, ids_inactivos)


# ---------------------------------------------------------------------------
# F-10 – Galpones libres (sin lote en Transición ni Producción)
# ---------------------------------------------------------------------------

class GalponesLibresTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        token_de(self.client, crear_usuario("admin10", rol=Usuario.ROL_ADMINISTRADOR))
        self.vacio = crear_galpon("Vacío")
        self.en_transicion = crear_galpon("En transición")
        crear_lote(self.en_transicion, Lote.ESTADO_TRANSICION)
        self.en_produccion = crear_galpon("En producción")
        crear_lote(self.en_produccion, Lote.ESTADO_PRODUCCION)
        self.con_lote_finalizado = crear_galpon("Con lote finalizado")
        crear_lote(self.con_lote_finalizado, Lote.ESTADO_FINALIZADO)

    def ids(self, **params):
        resp = self.client.get("/api/galpones/", params)
        self.assertEqual(resp.status_code, 200, resp.data)
        return {g["id_galpon"] for g in resp.data["results"]}

    def test_sin_filtro_lista_todos(self):
        self.assertEqual(len(self.ids()), 4)

    def test_libre_excluye_los_ocupados(self):
        ids = self.ids(libre="true")
        self.assertNotIn(self.en_transicion.id_galpon, ids)
        self.assertNotIn(self.en_produccion.id_galpon, ids)

    def test_libre_incluye_vacios_y_con_lote_finalizado(self):
        ids = self.ids(libre="true")
        self.assertIn(self.vacio.id_galpon, ids)
        self.assertIn(self.con_lote_finalizado.id_galpon, ids)

    def test_libre_se_combina_con_estado_activo(self):
        inactivo = crear_galpon("Inactivo vacío", estado=Galpon.ESTADO_INACTIVO)
        ids = self.ids(libre="true", estado="A")
        self.assertNotIn(inactivo.id_galpon, ids)
        self.assertIn(self.vacio.id_galpon, ids)

    def test_libre_false_no_filtra(self):
        self.assertEqual(len(self.ids(libre="false")), 4)

    def test_libre_no_duplica_galpones_con_varios_lotes_finalizados(self):
        crear_lote(self.con_lote_finalizado, Lote.ESTADO_FINALIZADO)
        resp = self.client.get("/api/galpones/", {"libre": "true", "page_size": 100})
        ids = [g["id_galpon"] for g in resp.data["results"]]
        self.assertEqual(len(ids), len(set(ids)))
