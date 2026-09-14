"""
Tests de autenticación y gestión de usuarios.

Django crea una base de datos de test temporaria, corre todos los tests, y la
elimina al terminar. No toca la base de desarrollo.

Cada método `test_*` es un test independiente: arranca con la base vacía y
no depende del orden de ejecución.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Usuario


def crear_usuario(usuario="jperez", email="j@granja.com", password="admin1234",
                  nombre="Juan", apellido="Perez", dni="30123456",
                  rol=Usuario.ROL_ADMINISTRADOR, estado=Usuario.ESTADO_ACTIVO):
    return Usuario.objects.create_user(
        usuario=usuario, email=email, password=password,
        nombre=nombre, apellido=apellido, dni=dni, rol=rol, estado=estado,
    )


def token_de(client, usuario, password):
    r = client.post(reverse("login"),
                    {"usuario": usuario, "password": password}, format="json")
    return r.data.get("access")


class LoginTests(TestCase):
    """CU01 — Iniciar Sesión."""

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario()

    def test_login_con_usuario_correcto(self):
        r = self.client.post(reverse("login"),
                             {"usuario": "jperez", "password": "admin1234"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        self.assertIn("usuario", r.data)

    def test_login_con_email(self):
        r = self.client.post(reverse("login"),
                             {"usuario": "j@granja.com", "password": "admin1234"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_login_no_expone_password(self):
        r = self.client.post(reverse("login"),
                             {"usuario": "jperez", "password": "admin1234"}, format="json")
        self.assertNotIn("password", r.data.get("usuario", {}))

    def test_clave_incorrecta_devuelve_401(self):
        r = self.client.post(reverse("login"),
                             {"usuario": "jperez", "password": "mal"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_inexistente_devuelve_401(self):
        r = self.client.post(reverse("login"),
                             {"usuario": "noexiste", "password": "x"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mismo_mensaje_en_credenciales_invalidas(self):
        r1 = self.client.post(reverse("login"),
                              {"usuario": "noexiste", "password": "x"}, format="json")
        r2 = self.client.post(reverse("login"),
                              {"usuario": "jperez", "password": "mal"}, format="json")
        self.assertEqual(r1.data["detail"], r2.data["detail"])

    def test_usuario_inactivo_no_puede_entrar(self):
        crear_usuario("cgomez", "c@g.com", "op1234", "Carlos", "Gomez", "32145870",
                      Usuario.ROL_OPERARIO, Usuario.ESTADO_INACTIVO)
        r = self.client.post(reverse("login"),
                             {"usuario": "cgomez", "password": "op1234"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class MeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        crear_usuario()

    def test_me_con_token_valido(self):
        tok = token_de(self.client, "jperez", "admin1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        r = self.client.get(reverse("me"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["usuario"], "jperez")

    def test_me_sin_token_devuelve_401(self):
        r = self.client.get(reverse("me"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_token_invalido_devuelve_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token.falso.inventado")
        r = self.client.get(reverse("me"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class PermisosPorRolTests(TestCase):
    """Matriz rol x operación."""

    def setUp(self):
        self.client = APIClient()
        crear_usuario("admin", "a@g.com", "admin1234",
                      "Admin", "Admin", "11111111", Usuario.ROL_ADMINISTRADOR)
        crear_usuario("operario", "o@g.com", "op1234",
                      "Op", "Op", "22222222", Usuario.ROL_OPERARIO)
        crear_usuario("consulta", "c@g.com", "co1234",
                      "Co", "Co", "33333333", Usuario.ROL_CONSULTA)

    def _auth(self, usuario, password):
        tok = token_de(self.client, usuario, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")

    def test_admin_puede_listar_usuarios(self):
        self._auth("admin", "admin1234")
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 200)

    def test_operario_no_puede_listar_usuarios(self):
        self._auth("operario", "op1234")
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 403)

    def test_consulta_no_puede_listar_usuarios(self):
        self._auth("consulta", "co1234")
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 403)

    def test_sin_token_no_puede_ver_usuarios(self):
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 401)

    def test_todos_los_roles_pueden_ver_galpones(self):
        for u, p in [("admin", "admin1234"), ("operario", "op1234"), ("consulta", "co1234")]:
            self._auth(u, p)
            r = self.client.get("/api/galpones/")
            self.assertEqual(r.status_code, 200, msg=f"{u} debería ver galpones")

    def test_sin_token_no_puede_ver_galpones(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/galpones/").status_code, 401)

    def test_operario_no_puede_crear_galpon(self):
        self._auth("operario", "op1234")
        datos = {"galpon": "G", "capacidad": 100, "superficie": "50.00",
                 "latitud": "-26.80", "longitud": "-65.21"}
        self.assertEqual(self.client.post("/api/galpones/", datos, format="json").status_code, 403)

    def test_consulta_no_puede_crear_galpon(self):
        self._auth("consulta", "co1234")
        datos = {"galpon": "G", "capacidad": 100, "superficie": "50.00",
                 "latitud": "-26.80", "longitud": "-65.21"}
        self.assertEqual(self.client.post("/api/galpones/", datos, format="json").status_code, 403)


class ABMUsuariosTests(TestCase):
    """CU03 a CU08."""

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_usuario()
        tok = token_de(self.client, "jperez", "admin1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok}")
        self.datos_nuevo = {
            "nombre": "Ana", "apellido": "Ruiz", "usuario": "aruiz",
            "email": "ana@granja.com", "dni": "31456789",
            "rol": "O", "password": "operaria1234",
        }

    def test_listar_usuarios(self):
        r = self.client.get("/api/usuarios/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)

    def test_buscar_por_texto(self):
        crear_usuario("cgomez", "c@g.com", "op1234", "Carlos", "Gomez", "32145870", "O")
        r = self.client.get("/api/usuarios/?search=gomez")
        self.assertEqual(r.data["count"], 1)

    def test_filtrar_por_rol(self):
        crear_usuario("cgomez", "c@g.com", "op1234", "Carlos", "Gomez", "32145870", "O")
        self.assertEqual(self.client.get("/api/usuarios/?rol=O").data["count"], 1)

    def test_crear_usuario(self):
        r = self.client.post("/api/usuarios/", self.datos_nuevo, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["usuario"], "aruiz")
        self.assertNotIn("password", r.data)

    def test_password_se_hashea_y_funciona(self):
        self.client.post("/api/usuarios/", self.datos_nuevo, format="json")
        self.assertIsNotNone(token_de(APIClient(), "aruiz", "operaria1234"))

    def test_usuario_duplicado_devuelve_400(self):
        self.client.post("/api/usuarios/", self.datos_nuevo, format="json")
        r = self.client.post("/api/usuarios/", self.datos_nuevo, format="json")
        self.assertEqual(r.status_code, 400)

    def test_password_corta_devuelve_400(self):
        datos = dict(self.datos_nuevo, usuario="x", email="x@g.com", dni="99", password="corta")
        self.assertEqual(self.client.post("/api/usuarios/", datos, format="json").status_code, 400)

    def test_modificar_usuario(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        r = self.client.patch(f"/api/usuarios/{uid}/", {"nombre": "Ana María"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["nombre"], "Ana María")
        self.assertEqual(r.data["apellido"], "Ruiz")  # no se tocó

    def test_dar_de_baja(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        r = self.client.post(f"/api/usuarios/{uid}/baja/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["estado"], "I")

    def test_usuario_en_baja_no_puede_entrar(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        self.client.post(f"/api/usuarios/{uid}/baja/")
        self.assertIsNone(token_de(APIClient(), "aruiz", "operaria1234"))

    def test_baja_dos_veces_devuelve_409(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        self.client.post(f"/api/usuarios/{uid}/baja/")
        self.assertEqual(self.client.post(f"/api/usuarios/{uid}/baja/").status_code, 409)

    def test_dar_de_alta(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        self.client.post(f"/api/usuarios/{uid}/baja/")
        r = self.client.post(f"/api/usuarios/{uid}/alta/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["estado"], "A")

    def test_no_puede_darse_de_baja_a_si_mismo(self):
        r = self.client.post(f"/api/usuarios/{self.admin.pk}/baja/")
        self.assertEqual(r.status_code, 400)

    def test_restablecer_password(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        r = self.client.post(f"/api/usuarios/{uid}/restablecer-password/",
                             {"password_nueva": "nueva_clave_123"}, format="json")
        self.assertEqual(r.status_code, 204)
        self.assertIsNone(token_de(APIClient(), "aruiz", "operaria1234"))  # vieja no sirve
        self.assertIsNotNone(token_de(APIClient(), "aruiz", "nueva_clave_123"))  # nueva sí

    def test_borrar_usuario(self):
        uid = self.client.post("/api/usuarios/", self.datos_nuevo, format="json").data["id_usuario"]
        self.assertEqual(self.client.delete(f"/api/usuarios/{uid}/").status_code, 204)
        self.assertFalse(Usuario.objects.filter(pk=uid).exists())

    def test_no_puede_borrarse_a_si_mismo(self):
        r = self.client.delete(f"/api/usuarios/{self.admin.pk}/")
        self.assertEqual(r.status_code, 400)
