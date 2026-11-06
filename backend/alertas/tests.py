"""Alertas de los lotes: reglas, generación automática y API.

    TiposAlertaTests          la migración de datos deja los tipos cargados
    PosturaBajaTests          se genera, se actualiza y se resuelve sola
    TransicionPorVencerTests  aviso de los últimos días de la transición
    MortandadAltaTests        descartes de gallinas por encima de lo esperado
    SinRecoleccionTests       lotes en producción sin recolecciones recientes
    ApiAlertasTests           listado, filtros y permisos
    ApiAlertasOperarioTests   el operario solo ve las alertas de sus galpones
"""

import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from descartes.models import Descarte, LineaDescarte
from galpones.models import Galpon, UsuarioDelGalpon
from lotes.models import Lote, PlanTransicion
from productos.models import Producto
from recolecciones.models import LineaRecoleccion, Recoleccion
from usuarios.models import Usuario

from .generacion import generar_alertas
from .models import Alerta, TipoAlerta
from . import reglas

PASSWORD = "Pass1234!"


# ── Datos de prueba ───────────────────────────────────────────────────────────

def crear_usuario(usuario, rol):
    u = Usuario(
        usuario=usuario,
        email=f"{usuario}@test.com",
        nombre="Ana",
        apellido=usuario.title(),
        dni=f"88{abs(hash(usuario)) % 10**6:06d}",
        rol=rol,
    )
    u.set_password(PASSWORD)
    u.save()
    return u


def cliente_de(usuario):
    client = APIClient()
    resp = client.post(
        "/api/auth/login/", {"usuario": usuario.usuario, "password": PASSWORD}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


def crear_galpon(nombre="Galpón 1"):
    return Galpon.objects.create(
        galpon=nombre, latitud="0", longitud="0", superficie="1", capacidad=5000
    )


def crear_lote(galpon, estado=Lote.ESTADO_PRODUCCION, gallinas=100, inicio_produccion=None):
    hoy = timezone.localdate()
    return Lote.objects.create(
        id_galpon=galpon,
        fecha_ingreso=hoy - datetime.timedelta(days=60),
        fecha_inicio_produccion=inicio_produccion,
        cantidad_inicial=gallinas,
        cantidad_actual=gallinas,
        estado=estado,
    )


def momento(dia, hora=10):
    """Las 10 de la mañana de ese día, en la zona horaria del proyecto."""
    return timezone.make_aware(datetime.datetime.combine(dia, datetime.time(hora, 0)))


def crear_recoleccion(lote, dia, huevos, producto, estado=Recoleccion.ESTADO_FINALIZADA):
    recoleccion = Recoleccion.objects.create(
        id_galpon=lote.id_galpon, id_lote=lote, fecha=momento(dia), estado=estado
    )
    LineaRecoleccion.objects.create(
        id_recoleccion=recoleccion,
        id_galpon=lote.id_galpon,
        id_producto=producto,
        cantidad=huevos,
    )
    return recoleccion


def crear_descarte_gallinas(lote, dia, cantidad, estado=Descarte.ESTADO_FINALIZADO):
    descarte = Descarte.objects.create(
        categoria=Descarte.CATEGORIA_GALPON,
        id_galpon=lote.id_galpon,
        fecha=momento(dia),
        estado=estado,
    )
    LineaDescarte.objects.create(
        id_descarte=descarte,
        id_galpon=lote.id_galpon,
        id_lote=lote,
        cantidad=cantidad,
        motivo="Mortandad",
    )
    return descarte


def crear_plan(lote, fecha_fin):
    valores = {f"{c}_semana{n}": 1 for n in range(1, 5) for c in ("agua", "alimento", "horas_luz")}
    return PlanTransicion.objects.create(
        id_lote=lote,
        fecha_inicio=fecha_fin - datetime.timedelta(days=28),
        fecha_fin=fecha_fin,
        **valores,
    )


def pendientes(clave=None):
    qs = Alerta.objects.filter(estado=Alerta.ESTADO_PENDIENTE)
    return qs.filter(id_tipo_alerta__clave=clave) if clave else qs


# ── Tipos ─────────────────────────────────────────────────────────────────────

class TiposAlertaTests(TestCase):
    def test_la_migracion_carga_los_cuatro_tipos(self):
        claves = set(TipoAlerta.objects.values_list("clave", flat=True))
        self.assertEqual(claves, {clave for clave, _nombre, _sev in reglas.TIPOS})

    def test_cada_tipo_tiene_su_severidad(self):
        tipo = TipoAlerta.objects.get(clave=reglas.POSTURA_BAJA)
        self.assertEqual(tipo.severidad, TipoAlerta.SEVERIDAD_ALTA)
        self.assertEqual(str(tipo), "Postura baja")


# ── Postura baja ──────────────────────────────────────────────────────────────

class PosturaBajaTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon, gallinas=100)
        self.producto = Producto.objects.create(producto="Huevo Nº1")

    def test_se_genera_cuando_la_postura_queda_por_debajo_del_minimo(self):
        crear_recoleccion(self.lote, self.hoy, 50, self.producto)  # 50%
        generar_alertas(self.hoy)
        alerta = pendientes(reglas.POSTURA_BAJA).get()
        self.assertEqual(alerta.id_lote, self.lote)
        self.assertIn("50,0% de postura", alerta.descripcion)
        self.assertIn(self.lote.codigo, alerta.descripcion)

    def test_no_se_genera_si_la_postura_llega_al_minimo(self):
        crear_recoleccion(self.lote, self.hoy, 70, self.producto)  # 70%
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.POSTURA_BAJA).exists())

    def test_las_recolecciones_pendientes_no_cuentan(self):
        crear_recoleccion(
            self.lote, self.hoy, 50, self.producto, estado=Recoleccion.ESTADO_PENDIENTE
        )
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.POSTURA_BAJA).exists())

    def test_se_mira_el_ultimo_dia_con_recoleccion(self):
        """Hoy todavía no se cargó nada: vale lo de ayer."""
        crear_recoleccion(self.lote, self.hoy - datetime.timedelta(days=1), 40, self.producto)
        generar_alertas(self.hoy)
        self.assertTrue(pendientes(reglas.POSTURA_BAJA).exists())

    def test_no_se_duplica_y_se_actualiza_la_descripcion(self):
        crear_recoleccion(self.lote, self.hoy - datetime.timedelta(days=1), 40, self.producto)
        generar_alertas(self.hoy)
        primera = pendientes(reglas.POSTURA_BAJA).get()

        crear_recoleccion(self.lote, self.hoy, 30, self.producto)
        generar_alertas(self.hoy)
        self.assertEqual(pendientes(reglas.POSTURA_BAJA).count(), 1)
        alerta = pendientes(reglas.POSTURA_BAJA).get()
        self.assertEqual(alerta.pk, primera.pk)
        self.assertIn("30,0% de postura", alerta.descripcion)

    def test_se_resuelve_sola_cuando_la_postura_se_recupera(self):
        crear_recoleccion(self.lote, self.hoy - datetime.timedelta(days=1), 40, self.producto)
        generar_alertas(self.hoy)
        crear_recoleccion(self.lote, self.hoy, 90, self.producto)
        generar_alertas(self.hoy)

        alerta = Alerta.objects.get(id_tipo_alerta__clave=reglas.POSTURA_BAJA)
        self.assertEqual(alerta.estado, Alerta.ESTADO_RESUELTA)
        self.assertIsNotNone(alerta.fecha_resolucion)

    def test_vuelve_a_generarse_si_la_situacion_se_repite(self):
        ayer = self.hoy - datetime.timedelta(days=1)
        crear_recoleccion(self.lote, ayer - datetime.timedelta(days=1), 40, self.producto)
        generar_alertas(self.hoy)
        crear_recoleccion(self.lote, ayer, 90, self.producto)
        generar_alertas(self.hoy)
        crear_recoleccion(self.lote, self.hoy, 20, self.producto)
        generar_alertas(self.hoy)

        self.assertEqual(Alerta.objects.filter(id_tipo_alerta__clave=reglas.POSTURA_BAJA).count(), 2)
        self.assertEqual(pendientes(reglas.POSTURA_BAJA).count(), 1)

    def test_los_lotes_en_transicion_no_se_evaluan(self):
        self.lote.estado = Lote.ESTADO_TRANSICION
        self.lote.save()
        crear_recoleccion(self.lote, self.hoy, 10, self.producto)
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.POSTURA_BAJA).exists())

    def test_generar_dos_veces_seguidas_no_cambia_nada(self):
        crear_recoleccion(self.lote, self.hoy, 50, self.producto)
        self.assertEqual(generar_alertas(self.hoy), (1, 0))
        self.assertEqual(generar_alertas(self.hoy), (0, 0))


# ── Transición por vencer ─────────────────────────────────────────────────────

class TransicionPorVencerTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon, estado=Lote.ESTADO_TRANSICION)

    def test_avisa_cuando_faltan_pocos_dias(self):
        crear_plan(self.lote, self.hoy + datetime.timedelta(days=2))
        generar_alertas(self.hoy)
        alerta = pendientes(reglas.TRANSICION_POR_VENCER).get()
        self.assertIn("termina en 2 días", alerta.descripcion)

    def test_manana_se_escribe_manana(self):
        crear_plan(self.lote, self.hoy + datetime.timedelta(days=1))
        generar_alertas(self.hoy)
        self.assertIn("termina mañana", pendientes(reglas.TRANSICION_POR_VENCER).get().descripcion)

    def test_no_avisa_si_falta_mucho(self):
        crear_plan(self.lote, self.hoy + datetime.timedelta(days=10))
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.TRANSICION_POR_VENCER).exists())

    def test_se_resuelve_cuando_el_lote_pasa_a_produccion(self):
        crear_plan(self.lote, self.hoy + datetime.timedelta(days=1))
        generar_alertas(self.hoy)
        self.assertTrue(pendientes(reglas.TRANSICION_POR_VENCER).exists())

        # Al día siguiente vence la transición: el lote pasa solo a producción.
        generar_alertas(self.hoy + datetime.timedelta(days=1))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.estado, Lote.ESTADO_PRODUCCION)
        self.assertFalse(pendientes(reglas.TRANSICION_POR_VENCER).exists())


# ── Mortandad alta ────────────────────────────────────────────────────────────

class MortandadAltaTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.galpon = crear_galpon()
        self.lote = crear_lote(self.galpon, gallinas=1000)

    def test_avisa_cuando_los_descartes_superan_el_umbral(self):
        crear_descarte_gallinas(self.lote, self.hoy, 15)  # 1,5% de 1000
        generar_alertas(self.hoy)
        alerta = pendientes(reglas.MORTANDAD_ALTA).get()
        self.assertIn("15 gallinas", alerta.descripcion)
        self.assertIn("1,5% del plantel", alerta.descripcion)

    def test_no_avisa_por_debajo_del_umbral(self):
        crear_descarte_gallinas(self.lote, self.hoy, 10)  # 1,0%
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.MORTANDAD_ALTA).exists())

    def test_suma_los_descartes_de_la_semana(self):
        for dias in range(0, 5):
            crear_descarte_gallinas(self.lote, self.hoy - datetime.timedelta(days=dias), 4)
        generar_alertas(self.hoy)
        self.assertTrue(pendientes(reglas.MORTANDAD_ALTA).exists())

    def test_los_descartes_viejos_no_cuentan(self):
        crear_descarte_gallinas(self.lote, self.hoy - datetime.timedelta(days=10), 50)
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.MORTANDAD_ALTA).exists())

    def test_los_descartes_pendientes_no_cuentan(self):
        crear_descarte_gallinas(self.lote, self.hoy, 50, estado=Descarte.ESTADO_PENDIENTE)
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.MORTANDAD_ALTA).exists())


# ── Sin recolecciones recientes ───────────────────────────────────────────────

class SinRecoleccionTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.galpon = crear_galpon()
        self.producto = Producto.objects.create(producto="Huevo Nº1")
        self.lote = crear_lote(
            self.galpon, inicio_produccion=self.hoy - datetime.timedelta(days=30)
        )

    def test_avisa_si_hace_dias_que_no_se_carga_nada(self):
        crear_recoleccion(self.lote, self.hoy - datetime.timedelta(days=5), 90, self.producto)
        generar_alertas(self.hoy)
        self.assertIn(
            "sin recolecciones finalizadas", pendientes(reglas.SIN_RECOLECCION).get().descripcion
        )

    def test_no_avisa_si_se_cargo_hace_poco(self):
        crear_recoleccion(self.lote, self.hoy - datetime.timedelta(days=1), 90, self.producto)
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.SIN_RECOLECCION).exists())

    def test_avisa_si_nunca_se_cargo_una_recoleccion(self):
        generar_alertas(self.hoy)
        self.assertIn(
            "todavía no tiene ninguna", pendientes(reglas.SIN_RECOLECCION).get().descripcion
        )

    def test_un_lote_recien_pasado_a_produccion_no_se_avisa(self):
        self.lote.fecha_inicio_produccion = self.hoy
        self.lote.save()
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.SIN_RECOLECCION).exists())

    def test_se_resuelve_al_cargar_una_recoleccion(self):
        generar_alertas(self.hoy)
        crear_recoleccion(self.lote, self.hoy, 90, self.producto)
        generar_alertas(self.hoy)
        self.assertFalse(pendientes(reglas.SIN_RECOLECCION).exists())


# ── API ───────────────────────────────────────────────────────────────────────

class ApiAlertasTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.admin = crear_usuario("admin_alertas", Usuario.ROL_ADMINISTRADOR)
        self.consulta = crear_usuario("consulta_alertas", Usuario.ROL_CONSULTA)
        self.galpon = crear_galpon()
        self.producto = Producto.objects.create(producto="Huevo Nº1")
        self.lote = crear_lote(self.galpon, gallinas=100)
        crear_recoleccion(self.lote, self.hoy, 20, self.producto)
        self.client = cliente_de(self.admin)

    def test_lista_las_alertas_generadas_al_consultar(self):
        resp = self.client.get("/api/alertas/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        fila = resp.data["results"][0]
        self.assertEqual(fila["clave"], reglas.POSTURA_BAJA)
        self.assertEqual(fila["tipo"], "Postura baja")
        self.assertEqual(fila["severidad"], "A")
        self.assertEqual(fila["estado_display"], "Pendiente")
        self.assertEqual(fila["lote"], self.lote.codigo)
        self.assertEqual(fila["galpon"], self.galpon.galpon)

    def test_consulta_tambien_las_ve(self):
        resp = cliente_de(self.consulta).get("/api/alertas/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)

    def test_sin_sesion_no_se_puede(self):
        self.assertEqual(APIClient().get("/api/alertas/").status_code, 401)

    def test_no_se_pueden_crear_ni_borrar(self):
        self.assertEqual(self.client.post("/api/alertas/", {}, format="json").status_code, 405)
        generar_alertas(self.hoy)
        alerta = Alerta.objects.get()
        self.assertEqual(self.client.delete(f"/api/alertas/{alerta.pk}/").status_code, 405)

    def test_filtro_por_estado(self):
        self.assertEqual(self.client.get("/api/alertas/?estado=P").data["count"], 1)
        self.assertEqual(self.client.get("/api/alertas/?estado=R").data["count"], 0)

    def test_estado_invalido_devuelve_400(self):
        self.assertEqual(self.client.get("/api/alertas/?estado=X").status_code, 400)

    def test_filtro_por_galpon_invalido_devuelve_400(self):
        self.assertEqual(self.client.get("/api/alertas/?id_galpon=abc").status_code, 400)

    def test_detalle(self):
        generar_alertas(self.hoy)
        alerta = Alerta.objects.get()
        resp = self.client.get(f"/api/alertas/{alerta.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id_alerta"], alerta.pk)


class ApiAlertasOperarioTests(TestCase):
    """El operario solo ve las alertas de los lotes de sus galpones (F-32)."""

    def setUp(self):
        self.hoy = timezone.localdate()
        self.operario = crear_usuario("operario_alertas", Usuario.ROL_OPERARIO)
        self.producto = Producto.objects.create(producto="Huevo Nº1")
        self.mio = crear_galpon("Galpón mío")
        self.ajeno = crear_galpon("Galpón ajeno")
        UsuarioDelGalpon.objects.create(id_usuario=self.operario, id_galpon=self.mio)
        self.lote_mio = crear_lote(self.mio, gallinas=100)
        self.lote_ajeno = crear_lote(self.ajeno, gallinas=100)
        crear_recoleccion(self.lote_mio, self.hoy, 20, self.producto)
        crear_recoleccion(self.lote_ajeno, self.hoy, 20, self.producto)
        self.client = cliente_de(self.operario)

    def test_solo_lista_las_de_sus_galpones(self):
        resp = self.client.get("/api/alertas/")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["id_galpon"], self.mio.pk)

    def test_una_alerta_ajena_devuelve_404(self):
        generar_alertas(self.hoy)
        ajena = Alerta.objects.get(id_lote=self.lote_ajeno)
        self.assertEqual(self.client.get(f"/api/alertas/{ajena.pk}/").status_code, 404)
