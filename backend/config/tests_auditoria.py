"""Auditoría de los registros (F-23): ModeloAuditable y su visibilidad por rol.

    CreacionTests     alta: quién y cuándo, y datos existentes
    EdicionTests      edición, baja/alta y cambios sin usuario
    FinalizacionTests el estado pasa a finalizado
    VisibilidadTests  la auditoría la ven Administrador y Consulta, no el Operario
    ContextoTests     el usuario de una petición no se arrastra a la siguiente
"""
import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from config.auditoria import _usuario_actual, usuario_actual
from galpones.models import Galpon, UsuarioDelGalpon
from lotes.models import Lote
from productos.models import Producto
from usuarios.models import Usuario

PASSWORD = "Pass1234!"


def crear_usuario(usuario, rol=Usuario.ROL_ADMINISTRADOR, **kwargs):
    u = Usuario(
        usuario=usuario, email=f"{usuario}@test.com", nombre="Ana", apellido=usuario.title(),
        dni=f"88{abs(hash(usuario)) % 10**6:06d}", rol=rol, **kwargs,
    )
    u.set_password(PASSWORD)
    u.save()
    return u


def cliente_de(usuario):
    client = APIClient()
    resp = client.post("/api/auth/login/", {"usuario": usuario.usuario, "password": PASSWORD}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


DATOS_GALPON = {
    "galpon": "Galpón Auditado", "latitud": "-26.808000", "longitud": "-65.217000",
    "superficie": "200", "capacidad": 500,
}


class CreacionTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_aud")
        self.client = cliente_de(self.admin)

    def test_alta_registra_quien_y_cuando(self):
        resp = self.client.post("/api/galpones/", DATOS_GALPON, format="json")
        self.assertEqual(resp.status_code, 201)
        galpon = Galpon.objects.get(pk=resp.data["id_galpon"])
        self.assertEqual(galpon.creado_por, self.admin)
        self.assertIsNotNone(galpon.fecha_creacion)
        self.assertIsNone(galpon.editado_por)
        self.assertIsNone(galpon.fecha_editado)
        self.assertIsNone(galpon.fecha_finalizado)

    def test_la_respuesta_incluye_la_auditoria(self):
        resp = self.client.post("/api/galpones/", DATOS_GALPON, format="json")
        auditoria = resp.data["auditoria"]
        self.assertEqual(auditoria["creado"]["por"]["usuario"], "admin_aud")
        self.assertEqual(auditoria["creado"]["por"]["nombre"], "Ana Admin_Aud")
        self.assertIsNotNone(auditoria["creado"]["fecha"])
        self.assertIsNone(auditoria["editado"]["por"])
        self.assertIsNone(auditoria["finalizado"]["fecha"])

    def test_alta_de_usuario_registra_al_administrador(self):
        resp = self.client.post(
            "/api/usuarios/",
            {"nombre": "Luis", "apellido": "Perez", "usuario": "luis_p", "email": "luis@test.com",
             "dni": "12345678", "rol": "O", "password": PASSWORD, "password_confirm": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Usuario.objects.get(usuario="luis_p").creado_por, self.admin)

    def test_registro_anterior_a_la_auditoria_se_muestra_sin_datos(self):
        galpon = Galpon.objects.create(galpon="Viejo", latitud="0", longitud="0", superficie="1", capacidad=1)
        Galpon.objects.filter(pk=galpon.pk).update(creado_por=None, fecha_creacion=None)
        resp = self.client.get(f"/api/galpones/{galpon.pk}/")
        self.assertIsNone(resp.data["auditoria"]["creado"]["fecha"])
        self.assertIsNone(resp.data["auditoria"]["creado"]["por"])


class EdicionTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_ed")
        self.otro = crear_usuario("otro_ed")
        self.galpon = Galpon.objects.create(**{**DATOS_GALPON, "capacidad": 500, "latitud": "0", "longitud": "0"})

    def test_edicion_registra_quien_edito(self):
        resp = cliente_de(self.otro).patch(f"/api/galpones/{self.galpon.pk}/", {"galpon": "Nuevo"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.galpon.refresh_from_db()
        self.assertEqual(self.galpon.editado_por, self.otro)
        self.assertIsNotNone(self.galpon.fecha_editado)

    def test_baja_cuenta_como_edicion_y_no_como_finalizado(self):
        resp = cliente_de(self.admin).post(f"/api/galpones/{self.galpon.pk}/baja/")
        self.assertEqual(resp.status_code, 200)
        self.galpon.refresh_from_db()
        self.assertEqual(self.galpon.editado_por, self.admin)
        self.assertIsNone(self.galpon.fecha_finalizado)

    def test_cambio_sin_usuario_guarda_la_fecha_y_queda_como_sistema(self):
        self.galpon.descripcion = "cambio automático"
        self.galpon.save()
        self.galpon.refresh_from_db()
        self.assertIsNone(self.galpon.editado_por)
        self.assertIsNotNone(self.galpon.fecha_editado)

    def test_login_no_cuenta_como_edicion(self):
        cliente_de(self.admin)  # el login actualiza last_login
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.fecha_editado)

    def test_save_con_update_fields_guarda_la_auditoria(self):
        producto = Producto.objects.create(producto="Huevo X")
        producto.estado = Producto.ESTADO_INACTIVO
        producto.save(update_fields=["estado"])
        producto.refresh_from_db()
        self.assertIsNotNone(producto.fecha_editado)


class FinalizacionTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_fin")
        self.galpon = Galpon.objects.create(galpon="G", latitud="0", longitud="0", superficie="1", capacidad=5000)
        self.lote = Lote.objects.create(
            id_galpon=self.galpon, fecha_ingreso=datetime.date(2026, 1, 1),
            cantidad_inicial=100, cantidad_actual=100, estado=Lote.ESTADO_PRODUCCION,
        )
        self.token = _usuario_actual.set(self.admin)

    def tearDown(self):
        _usuario_actual.reset(self.token)

    def test_pasar_a_finalizado_registra_quien_y_cuando(self):
        lote = Lote.objects.get(pk=self.lote.pk)
        lote.estado = Lote.ESTADO_FINALIZADO
        lote.save()
        lote.refresh_from_db()
        self.assertEqual(lote.finalizado_por, self.admin)
        self.assertIsNotNone(lote.fecha_finalizado)
        self.assertIsNone(lote.fecha_editado)

    def test_editar_un_registro_ya_finalizado_no_pisa_la_finalizacion(self):
        lote = Lote.objects.get(pk=self.lote.pk)
        lote.estado = Lote.ESTADO_FINALIZADO
        lote.save()
        fecha = Lote.objects.get(pk=lote.pk).fecha_finalizado
        lote = Lote.objects.get(pk=lote.pk)
        lote.cantidad_actual = 90
        lote.save()
        lote.refresh_from_db()
        self.assertEqual(lote.fecha_finalizado, fecha)
        self.assertIsNotNone(lote.fecha_editado)

    def test_cambios_que_no_finalizan_cuentan_como_edicion(self):
        lote = Lote.objects.get(pk=self.lote.pk)
        lote.cantidad_actual = 80
        lote.save()
        lote.refresh_from_db()
        self.assertEqual(lote.editado_por, self.admin)
        self.assertIsNone(lote.fecha_finalizado)

    def test_un_modelo_sin_estado_finalizado_nunca_lo_registra(self):
        self.galpon.estado = Galpon.ESTADO_INACTIVO
        self.galpon.save()
        self.galpon.refresh_from_db()
        self.assertIsNone(self.galpon.fecha_finalizado)


class VisibilidadTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_vis")
        self.consulta = crear_usuario("consulta_vis", rol=Usuario.ROL_CONSULTA)
        self.operario = crear_usuario("operario_vis", rol=Usuario.ROL_OPERARIO)
        self.galpon = Galpon.objects.create(galpon="G", latitud="0", longitud="0", superficie="1", capacidad=1)
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.galpon)

    def _detalle(self, usuario):
        return cliente_de(usuario).get(f"/api/galpones/{self.galpon.pk}/")

    def test_administrador_ve_la_auditoria(self):
        self.assertIn("auditoria", self._detalle(self.admin).data)

    def test_consulta_ve_la_auditoria(self):
        self.assertIn("auditoria", self._detalle(self.consulta).data)

    def test_operario_no_la_ve(self):
        resp = self._detalle(self.operario)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("auditoria", resp.data)

    def test_el_listado_tambien_incluye_la_auditoria(self):
        resp = cliente_de(self.admin).get("/api/galpones/")
        self.assertIn("auditoria", resp.data["results"][0])

    def test_los_listados_no_hacen_una_consulta_por_fila(self):
        from proveedores.models import Proveedor

        def crear(n):
            for i in range(n):
                Proveedor.objects.create(
                    nombre=f"Prov {Proveedor.objects.count()}", creado_por=self.admin, editado_por=self.consulta,
                )

        client = cliente_de(self.admin)
        crear(3)
        with CaptureQueriesContext(connection) as pocas:
            client.get("/api/proveedores/?page_size=50")
        crear(9)
        with CaptureQueriesContext(connection) as muchas:
            resp = client.get("/api/proveedores/?page_size=50")
        self.assertEqual(len(resp.data["results"]), 12)
        self.assertEqual(len(pocas), len(muchas))


class ContextoTests(TestCase):
    def test_el_usuario_se_limpia_aunque_la_vista_falle(self):
        from unittest.mock import patch

        admin = crear_usuario("admin_err")
        client = cliente_de(admin)
        with patch("galpones.views.GalponViewSet.list", side_effect=RuntimeError("falla")):
            with self.assertRaises(RuntimeError):
                client.get("/api/galpones/")
        self.assertIsNone(usuario_actual())

    def test_el_usuario_no_se_arrastra_a_la_peticion_siguiente(self):
        admin = crear_usuario("admin_ctx")
        cliente_de(admin).get("/api/galpones/")
        self.assertIsNone(usuario_actual())
