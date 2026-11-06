"""
Tests del módulo Proveedores (CU70 a CU75).

Un proveedor vende materias primas y lotes de gallinas a la granja. Solo el
Administrador lo gestiona; el rol Consulta puede verlo y el Operario no tiene
acceso a la sección.

Clases:
  - BuscarProveedorTests      CU70: listar, buscar por texto, filtrar por estado, ordenar
  - NuevoProveedorTests       CU71: crear y validaciones (nombre, CUIT, email, teléfono, dirección)
  - ModificarProveedorTests   CU72: editar y validaciones al editar
  - BorrarProveedorTests      CU73: borrar, y 409 si tiene registros asociados
  - AltaBajaProveedorTests    CU74 y CU75: dar de alta y de baja
  - SimilaresProveedorTests   ayuda del formulario: nombres iguales o parecidos
  - CuitProveedorTests        validación del CUIT (dígito verificador, formato, unicidad)
  - PermisosProveedorTests    matriz rol × operación
"""

from unittest import mock

from django.db.models import ProtectedError
from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Usuario

from .models import Proveedor
from .serializers import cuit_valido, formatear_cuit


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


def auth(client, user):
    r = client.post(
        "/api/auth/login/",
        {"usuario": user.usuario, "password": "pass1234"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def make_proveedor(nombre="Agro Sur", **kwargs):
    defaults = dict(
        email="ventas@agrosur.com", telefono="381-455-0102",
        direccion="Ruta 9 Km 1301, Tucumán",
    )
    defaults.update(kwargs)
    return Proveedor.objects.create(nombre=nombre, **defaults)


def datos(**kwargs):
    base = dict(
        nombre="Granja San José", email="contacto@granjasanjose.com",
        telefono="381-460-2233", direccion="Av. Roca 1200",
    )
    base.update(kwargs)
    return base


# CUITs con dígito verificador correcto.
CUIT_OK = "20123456786"
CUIT_OK_2 = "30500010912"


# ── CU70 Buscar ───────────────────────────────────────────────────────────────

class BuscarProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p1 = make_proveedor("Agro Sur", cuit=CUIT_OK)
        self.p2 = make_proveedor(
            "Granja San José", email="contacto@granjasanjose.com",
            telefono="381-460-2233", direccion="",
        )
        self.p3 = make_proveedor(
            "Insumos Norte", email="info@insumosnorte.com", telefono="381-480-1122",
            direccion="Calle 5 N° 120", estado=Proveedor.ESTADO_INACTIVO,
        )

    def nombres(self, **params):
        resp = self.client.get("/api/proveedores/", params)
        self.assertEqual(resp.status_code, 200)
        return [p["nombre"] for p in resp.data["results"]]

    def test_listar_ordenado_por_nombre(self):
        self.assertEqual(self.nombres(), ["Agro Sur", "Granja San José", "Insumos Norte"])

    def test_filtrar_por_estado(self):
        self.assertEqual(self.nombres(estado="A"), ["Agro Sur", "Granja San José"])
        self.assertEqual(self.nombres(estado="I"), ["Insumos Norte"])

    def test_buscar_por_nombre_email_telefono_direccion_y_cuit(self):
        self.assertEqual(self.nombres(search="granja"), ["Granja San José"])
        self.assertEqual(self.nombres(search="insumosnorte.com"), ["Insumos Norte"])
        self.assertEqual(self.nombres(search="455-0102"), ["Agro Sur"])
        self.assertEqual(self.nombres(search="Ruta 9"), ["Agro Sur"])
        self.assertEqual(self.nombres(search=CUIT_OK), ["Agro Sur"])

    def test_buscar_sin_resultados(self):
        self.assertEqual(self.nombres(search="inexistente"), [])

    def test_buscar_combinado_con_estado(self):
        self.assertEqual(self.nombres(search="o", estado="I"), ["Insumos Norte"])

    def test_orden_descendente(self):
        self.assertEqual(self.nombres(ordering="-nombre")[0], "Insumos Norte")

    def test_detalle(self):
        resp = self.client.get(f"/api/proveedores/{self.p1.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["nombre"], "Agro Sur")
        self.assertEqual(resp.data["estado_display"], "Activo")
        self.assertEqual(resp.data["cuit_formateado"], "20-12345678-6")

    def test_cuit_formateado_vacio_si_no_tiene(self):
        resp = self.client.get(f"/api/proveedores/{self.p2.pk}/")
        self.assertEqual(resp.data["cuit"], "")
        self.assertEqual(resp.data["cuit_formateado"], "")

    def test_detalle_inexistente_404(self):
        self.assertEqual(self.client.get("/api/proveedores/9999/").status_code, 404)


# ── CU71 Nuevo ────────────────────────────────────────────────────────────────

class NuevoProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())

    def post(self, **kwargs):
        return self.client.post("/api/proveedores/", datos(**kwargs), format="json")

    def test_crear_exitoso_queda_activo(self):
        resp = self.post()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["estado"], "A")
        self.assertEqual(Proveedor.objects.count(), 1)

    def test_el_estado_no_lo_define_el_cliente(self):
        resp = self.post(estado="I")
        self.assertEqual(resp.data["estado"], "A")

    def test_direccion_y_cuit_son_opcionales(self):
        resp = self.client.post(
            "/api/proveedores/",
            dict(nombre="Sin extras", email="a@b.com", telefono="381 400 1000"),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["direccion"], "")
        self.assertEqual(resp.data["cuit"], "")

    def test_nombre_obligatorio(self):
        resp = self.client.post(
            "/api/proveedores/", dict(email="a@b.com", telefono="381 400 1000"), format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("nombre", resp.data)

    def test_nombre_en_blanco_rechazado(self):
        self.assertEqual(self.post(nombre="   ").status_code, 400)

    def test_nombre_demasiado_largo(self):
        self.assertEqual(self.post(nombre="a" * 101).status_code, 400)
        self.assertEqual(self.post(nombre="a" * 100).status_code, 201)

    def test_los_espacios_de_mas_se_colapsan(self):
        resp = self.post(nombre="  Agro    Sur  ")
        self.assertEqual(resp.data["nombre"], "Agro Sur")

    def test_nombre_repetido_aunque_cambie_mayusculas_o_tildes(self):
        self.assertEqual(self.post(nombre="Álamo Hnos").status_code, 201)
        for variante in ["Álamo Hnos", "alamo hnos", "ALAMO HNOS", "  Alamo   hnos "]:
            resp = self.post(nombre=variante, email="otro@x.com")
            self.assertEqual(resp.status_code, 400, variante)
            self.assertIn("Ya existe un proveedor", str(resp.data["nombre"]))

    def test_email_obligatorio_y_con_formato_valido(self):
        resp = self.client.post(
            "/api/proveedores/", dict(nombre="X", telefono="381 400 1000"), format="json"
        )
        self.assertIn("email", resp.data)
        for malo in ["sin-arroba", "a@", "@b.com", "a b@c.com"]:
            self.assertEqual(self.post(email=malo).status_code, 400, malo)

    def test_email_se_guarda_en_minusculas(self):
        resp = self.post(email="  Ventas@AgroSur.COM ")
        self.assertEqual(resp.data["email"], "ventas@agrosur.com")

    def test_telefono_obligatorio(self):
        resp = self.client.post(
            "/api/proveedores/", dict(nombre="X", email="a@b.com"), format="json"
        )
        self.assertIn("telefono", resp.data)

    def test_telefono_formatos_validos(self):
        for i, tel in enumerate(["381-455-0102", "+54 9 381 455 0102", "(0381) 455-0102", "0381 15 455-0102", "(011) 4555-1234", "3814550102"]):
            self.assertEqual(self.post(nombre=f"P{i}", telefono=tel).status_code, 201, tel)

    def test_telefono_invalido(self):
        for malo in ["abc", "12345", "381-ABC-0102", "!!!!!!!", "12 34", "4550102", "0000000", "0000000000", "1111111111", "381-455-01", "381-455-01022", "081-455-0102", "+54 9 181 455 0102"]:
            self.assertEqual(self.post(telefono=malo).status_code, 400, malo)

    def test_telefono_internacional_valido(self):
        for i, tel in enumerate(["+598 99 123 456", "+1 (415) 555-2671", "+34 612 345 678", "+55 11 91234-5678", "+56 9 8765 4321"]):
            self.assertEqual(self.post(nombre=f"Ext{i}", telefono=tel).status_code, 201, tel)

    def test_telefono_internacional_invalido(self):
        # Sin + el número se trata como argentino; con + y otro país solo se controla lo básico.
        for malo in ["+598", "+1234567", "+1111111111","+0 612 345 678", "+34 612 345 678 901 234", "+34 612 abc 678"]:
            self.assertEqual(self.post(telefono=malo).status_code, 400, malo)
        self.assertEqual(self.post(telefono="598 99 123 456").status_code, 400)

    def test_telefono_con_codigo_54_sigue_validandose_como_argentino(self):
        self.assertEqual(self.post(nombre="Arg", telefono="+54 9 381 455 0102").status_code, 201)
        self.assertEqual(self.post(nombre="Arg2", telefono="+54 9 181 455 0102").status_code, 400)

    def test_nombre_sin_letras_o_demasiado_corto(self):
        for malo in [".", "..", "-", "1", "a", "123", "__", "?!"]:
            self.assertEqual(self.post(nombre=malo).status_code, 400, malo)
        for bueno in ["Ab", "3M", "Agro 2000"]:
            Proveedor.objects.all().delete()
            self.assertEqual(self.post(nombre=bueno).status_code, 201, bueno)

    def test_direccion_sin_contenido_rechazada(self):
        for malo in [".", "--", "a1"]:
            self.assertEqual(self.post(direccion=malo).status_code, 400, malo)
        self.assertEqual(self.post(direccion="Av. Roca 1200").status_code, 201)

    def test_telefono_demasiado_largo(self):
        self.assertEqual(self.post(telefono="1" * 46).status_code, 400)

    def test_direccion_demasiado_larga(self):
        self.assertEqual(self.post(direccion="a" * 151).status_code, 400)
        self.assertEqual(self.post(direccion="a" * 150).status_code, 201)


# ── CU72 Modificar ────────────────────────────────────────────────────────────

class ModificarProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_proveedor("Agro Sur", cuit=CUIT_OK)
        self.otro = make_proveedor("Granja San José", email="g@x.com", cuit=CUIT_OK_2)
        self.url = f"/api/proveedores/{self.p.pk}/"

    def test_modificar_un_campo_conserva_el_resto(self):
        resp = self.client.patch(self.url, {"telefono": "381-999-0000"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.telefono, "381-999-0000")
        self.assertEqual(self.p.nombre, "Agro Sur")
        self.assertEqual(self.p.cuit, CUIT_OK)

    def test_reenviar_el_mismo_nombre_o_cuit_es_valido(self):
        resp = self.client.patch(
            self.url, {"nombre": "agro sur", "cuit": "20-12345678-6"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["nombre"], "agro sur")

    def test_no_puede_tomar_el_nombre_de_otro(self):
        resp = self.client.patch(self.url, {"nombre": "granja san jose"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("nombre", resp.data)

    def test_no_puede_tomar_el_cuit_de_otro(self):
        resp = self.client.patch(self.url, {"cuit": CUIT_OK_2}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cuit", resp.data)

    def test_borrar_el_cuit(self):
        resp = self.client.patch(self.url, {"cuit": ""}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.cuit, "")

    def test_borrar_la_direccion(self):
        resp = self.client.patch(self.url, {"direccion": ""}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_el_estado_no_se_cambia_por_patch(self):
        resp = self.client.patch(self.url, {"estado": "I"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual(self.p.estado, Proveedor.ESTADO_ACTIVO)

    def test_validaciones_al_editar(self):
        self.assertEqual(self.client.patch(self.url, {"email": "mal"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"telefono": "abc"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"nombre": ""}, format="json").status_code, 400)

    def test_se_puede_editar_un_proveedor_inactivo(self):
        Proveedor.objects.filter(pk=self.p.pk).update(estado=Proveedor.ESTADO_INACTIVO)
        resp = self.client.patch(self.url, {"direccion": "Nueva 123"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_inexistente_404(self):
        resp = self.client.patch("/api/proveedores/9999/", {"telefono": "381 400 1000"}, format="json")
        self.assertEqual(resp.status_code, 404)


# ── CU73 Borrar ───────────────────────────────────────────────────────────────

class BorrarProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_proveedor()

    def test_borrar(self):
        resp = self.client.delete(f"/api/proveedores/{self.p.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Proveedor.objects.filter(pk=self.p.pk).exists())

    def test_con_registros_asociados_es_409_y_no_500(self):
        # Todavía no existe el módulo Compras: se simula la restricción PROTECT
        # que impondrán sus registros.
        with mock.patch.object(
            Proveedor, "delete", side_effect=ProtectedError("protegido", set())
        ):
            resp = self.client.delete(f"/api/proveedores/{self.p.pk}/")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("Dalo de baja", resp.data["detail"])
        self.assertTrue(Proveedor.objects.filter(pk=self.p.pk).exists())

    def test_inexistente_404(self):
        self.assertEqual(self.client.delete("/api/proveedores/9999/").status_code, 404)


# ── CU74 / CU75 Alta y baja ───────────────────────────────────────────────────

class AltaBajaProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p = make_proveedor()

    def test_baja(self):
        resp = self.client.post(f"/api/proveedores/{self.p.pk}/baja/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "I")
        self.assertEqual(resp.data["estado_display"], "Inactivo")
        self.p.refresh_from_db()
        self.assertEqual(self.p.estado, Proveedor.ESTADO_INACTIVO)

    def test_baja_de_un_inactivo_es_409(self):
        Proveedor.objects.filter(pk=self.p.pk).update(estado=Proveedor.ESTADO_INACTIVO)
        resp = self.client.post(f"/api/proveedores/{self.p.pk}/baja/")
        self.assertEqual(resp.status_code, 409)

    def test_alta(self):
        Proveedor.objects.filter(pk=self.p.pk).update(estado=Proveedor.ESTADO_INACTIVO)
        resp = self.client.post(f"/api/proveedores/{self.p.pk}/alta/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["estado"], "A")

    def test_alta_de_un_activo_es_409(self):
        resp = self.client.post(f"/api/proveedores/{self.p.pk}/alta/")
        self.assertEqual(resp.status_code, 409)

    def test_baja_y_alta_conservan_los_datos(self):
        self.client.post(f"/api/proveedores/{self.p.pk}/baja/")
        self.client.post(f"/api/proveedores/{self.p.pk}/alta/")
        self.p.refresh_from_db()
        self.assertEqual(self.p.nombre, "Agro Sur")
        self.assertEqual(self.p.email, "ventas@agrosur.com")

    def test_inexistente_404(self):
        self.assertEqual(self.client.post("/api/proveedores/9999/baja/").status_code, 404)
        self.assertEqual(self.client.post("/api/proveedores/9999/alta/").status_code, 404)

    def test_un_nombre_de_proveedor_dado_de_baja_sigue_ocupado(self):
        self.client.post(f"/api/proveedores/{self.p.pk}/baja/")
        resp = self.client.post("/api/proveedores/", datos(nombre="agro sur"), format="json")
        self.assertEqual(resp.status_code, 400)


# ── Similares ─────────────────────────────────────────────────────────────────

class SimilaresProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())
        self.p1 = make_proveedor("Avícola del Valle", email="v@x.com")
        self.p2 = make_proveedor("Agro Sur")
        self.p3 = make_proveedor("Agro Sur Norte", email="n@x.com", estado=Proveedor.ESTADO_INACTIVO)

    def buscar(self, **params):
        resp = self.client.get("/api/proveedores/similares/", params)
        self.assertEqual(resp.status_code, 200)
        return resp.data

    def test_nombre_vacio_no_devuelve_nada(self):
        self.assertEqual(self.buscar(nombre=""), [])
        self.assertEqual(self.buscar(), [])

    def test_exacta_ignora_mayusculas_y_tildes(self):
        r = self.buscar(nombre="avicola DEL valle")
        self.assertEqual(len(r), 1)
        self.assertTrue(r[0]["exacta"])
        self.assertEqual(r[0]["nombre"], "Avícola del Valle")

    def test_parecidos_y_exacta_primero(self):
        r = self.buscar(nombre="agro sur")
        self.assertEqual([x["nombre"] for x in r], ["Agro Sur", "Agro Sur Norte"])
        self.assertTrue(r[0]["exacta"])
        self.assertFalse(r[1]["exacta"])
        self.assertEqual(r[1]["estado"], "I")

    def test_excluir_al_editar_el_propio(self):
        r = self.buscar(nombre="agro sur", excluir=self.p2.pk)
        self.assertEqual([x["nombre"] for x in r], ["Agro Sur Norte"])

    def test_sin_coincidencias(self):
        self.assertEqual(self.buscar(nombre="zzzz"), [])


# ── CUIT ──────────────────────────────────────────────────────────────────────

class CuitProveedorTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        auth(self.client, make_admin())

    def post(self, cuit, nombre="Con CUIT"):
        return self.client.post("/api/proveedores/", datos(nombre=nombre, cuit=cuit), format="json")

    def test_funciones_auxiliares(self):
        self.assertTrue(cuit_valido(CUIT_OK))
        self.assertTrue(cuit_valido(CUIT_OK_2))
        self.assertFalse(cuit_valido("20123456787"))
        self.assertFalse(cuit_valido("123"))
        self.assertFalse(cuit_valido("abcdefghijk"))
        self.assertEqual(formatear_cuit(CUIT_OK), "20-12345678-6")
        self.assertEqual(formatear_cuit("123"), "123")

    def test_acepta_con_y_sin_guiones_y_guarda_solo_digitos(self):
        for i, formato in enumerate([CUIT_OK, "20-12345678-6", " 20 12345678 6 "]):
            Proveedor.objects.all().delete()
            resp = self.post(formato, nombre=f"P{i}")
            self.assertEqual(resp.status_code, 201, formato)
            self.assertEqual(resp.data["cuit"], CUIT_OK)

    def test_digito_verificador_incorrecto(self):
        resp = self.post("20123456787")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("dígito verificador", str(resp.data["cuit"]))

    def test_largo_incorrecto_o_con_letras(self):
        for malo in ["2012345678", "201234567866", "20-1234567A-6", "abc"]:
            self.assertEqual(self.post(malo).status_code, 400, malo)

    def test_cuit_repetido(self):
        self.post(CUIT_OK, nombre="Uno")
        resp = self.post("20-12345678-6", nombre="Dos")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Ya existe un proveedor con ese CUIT", str(resp.data["cuit"]))

    def test_varios_proveedores_sin_cuit_no_chocan(self):
        self.assertEqual(self.post("", nombre="Uno").status_code, 201)
        self.assertEqual(self.post("", nombre="Dos").status_code, 201)


# ── Permisos ──────────────────────────────────────────────────────────────────

class PermisosProveedorTests(TestCase):

    def setUp(self):
        self.admin = make_admin()
        self.operario = make_operario()
        self.consulta = make_consulta()
        self.p = make_proveedor()

    def cliente(self, usuario=None):
        c = APIClient()
        if usuario:
            auth(c, usuario)
        return c

    def test_administrador_hace_todo(self):
        c = self.cliente(self.admin)
        self.assertEqual(c.get("/api/proveedores/").status_code, 200)
        self.assertEqual(c.get(f"/api/proveedores/{self.p.pk}/").status_code, 200)
        self.assertEqual(c.get("/api/proveedores/similares/?nombre=a").status_code, 200)
        self.assertEqual(c.post("/api/proveedores/", datos(), format="json").status_code, 201)
        self.assertEqual(
            c.patch(f"/api/proveedores/{self.p.pk}/", {"telefono": "381 400 1000"}, format="json").status_code, 200
        )
        self.assertEqual(c.post(f"/api/proveedores/{self.p.pk}/baja/").status_code, 200)
        self.assertEqual(c.post(f"/api/proveedores/{self.p.pk}/alta/").status_code, 200)
        self.assertEqual(c.delete(f"/api/proveedores/{self.p.pk}/").status_code, 204)

    def test_consulta_solo_lee(self):
        c = self.cliente(self.consulta)
        self.assertEqual(c.get("/api/proveedores/").status_code, 200)
        self.assertEqual(c.get(f"/api/proveedores/{self.p.pk}/").status_code, 200)
        self.assertEqual(c.get("/api/proveedores/similares/?nombre=a").status_code, 200)
        self.assertEqual(c.post("/api/proveedores/", datos(), format="json").status_code, 403)
        self.assertEqual(
            c.patch(f"/api/proveedores/{self.p.pk}/", {"telefono": "381 400 1000"}, format="json").status_code, 403
        )
        self.assertEqual(c.post(f"/api/proveedores/{self.p.pk}/baja/").status_code, 403)
        self.assertEqual(c.post(f"/api/proveedores/{self.p.pk}/alta/").status_code, 403)
        self.assertEqual(c.delete(f"/api/proveedores/{self.p.pk}/").status_code, 403)
        self.assertTrue(Proveedor.objects.filter(pk=self.p.pk).exists())

    def test_operario_no_tiene_acceso_ni_de_lectura(self):
        c = self.cliente(self.operario)
        self.assertEqual(c.get("/api/proveedores/").status_code, 403)
        self.assertEqual(c.get(f"/api/proveedores/{self.p.pk}/").status_code, 403)
        self.assertEqual(c.get("/api/proveedores/similares/?nombre=a").status_code, 403)
        self.assertEqual(c.post("/api/proveedores/", datos(), format="json").status_code, 403)
        self.assertEqual(c.delete(f"/api/proveedores/{self.p.pk}/").status_code, 403)

    def test_sin_token_401(self):
        c = self.cliente()
        self.assertEqual(c.get("/api/proveedores/").status_code, 401)
        self.assertEqual(c.post("/api/proveedores/", datos(), format="json").status_code, 401)
        self.assertEqual(c.delete(f"/api/proveedores/{self.p.pk}/").status_code, 401)
