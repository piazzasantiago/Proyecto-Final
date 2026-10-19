"""
Tests del módulo Informes (CU85 a CU89).

Los informes solo leen datos de otros módulos, así que cada test arma sus
registros directamente con el ORM. Solo cuentan los registros finalizados.

Datos de base (agosto de 2026):
  · Galpón 1 con el lote L1 (1000 gallinas) y Galpón 2 con el lote L2 (500).
  · Recolecciones finalizadas: L1 900 huevos el día 3 y 800 el día 4; L2 400
    el día 3. Una recolección pendiente del día 5 que no debe contar.
  · Descarte finalizado de 100 gallinas de L1 el día 4 (L1 queda en 900 desde
    ese día), uno de 5 kg de materia prima el día 6 y uno de stock de 20
    productos el día 7. Un descarte pendiente que no debe contar.

Clases:
  - ParametrosInformeTests      fechas, filtros y formato
  - InformeProduccionTests      CU85
  - InformeLotesTests           CU86
  - InformeMateriasPrimasTests  CU87
  - InformeDescartesTests       CU88
  - IndicadoresTests            CU89
  - ExportacionInformesTests    Excel y PDF
  - PermisosInformesTests       matriz rol × informe
"""

import datetime
from datetime import timezone as dt_timezone
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from compras.models import Compra, LineaCompra
from descartes.models import Descarte, LineaDescarte
from entradas.models import Entrada, LineaEntrada
from galpones.models import Galpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from productos.models import Producto
from proveedores.models import Proveedor
from recolecciones.models import LineaRecoleccion, Recoleccion
from usuarios.models import Usuario

PERIODO = {"fecha_desde": "2026-08-01", "fecha_hasta": "2026-08-10"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_usuario(usuario, rol, dni):
    u = Usuario(
        usuario=usuario, email=f"{usuario}@test.com",
        nombre="Test", apellido=usuario.capitalize(), dni=dni, rol=rol,
    )
    u.set_password("pass1234")
    u.save()
    return u


def auth(client, user):
    r = client.post("/api/auth/login/", {"usuario": user.usuario, "password": "pass1234"}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


def fecha(dia, hora=10):
    return datetime.datetime(2026, 8, dia, hora, 0, tzinfo=dt_timezone.utc)


def make_galpon(nombre):
    return Galpon.objects.create(galpon=nombre, capacidad=2000, superficie=200, latitud=-26.8, longitud=-65.2)


def make_lote(galpon, inicial, actual=None, estado=Lote.ESTADO_PRODUCCION, **kwargs):
    return Lote.objects.create(
        id_galpon=galpon, fecha_ingreso=kwargs.pop("fecha_ingreso", datetime.date(2026, 1, 1)),
        cantidad_inicial=inicial, cantidad_actual=inicial if actual is None else actual,
        estado=estado, **kwargs,
    )


def make_recoleccion(galpon, lote, producto, cantidad, dia, estado=Recoleccion.ESTADO_FINALIZADA):
    r = Recoleccion.objects.create(id_galpon=galpon, id_lote=lote, fecha=fecha(dia), estado=estado)
    LineaRecoleccion.objects.create(id_recoleccion=r, id_galpon=galpon, id_producto=producto, cantidad=cantidad)
    return r


def make_descarte(dia, estado=Descarte.ESTADO_FINALIZADO, galpon=None, categoria=Descarte.CATEGORIA_GALPON):
    return Descarte.objects.create(categoria=categoria, id_galpon=galpon, fecha=fecha(dia), estado=estado)


class DatosBase(TestCase):
    """Escenario común a casi todos los tests."""

    def setUp(self):
        self.client = APIClient()
        self.admin = make_usuario("admin", Usuario.ROL_ADMINISTRADOR, "11111111")
        auth(self.client, self.admin)

        self.g1 = make_galpon("Galpón 1")
        self.g2 = make_galpon("Galpón 2")
        self.l1 = make_lote(self.g1, 1000, actual=900)
        self.l2 = make_lote(self.g2, 500)
        self.huevo = Producto.objects.create(producto="Huevo N°1", descripcion="")
        self.mp = MateriaPrima.objects.create(materia_prima="Balanceado", unidad="kg", stock_minimo=10, stock_inicial=100)

        make_recoleccion(self.g1, self.l1, self.huevo, 900, 3)
        make_recoleccion(self.g1, self.l1, self.huevo, 800, 4)
        make_recoleccion(self.g2, self.l2, self.huevo, 400, 3)
        make_recoleccion(self.g1, self.l1, self.huevo, 999, 5, estado=Recoleccion.ESTADO_PENDIENTE)

        d = make_descarte(4, galpon=self.g1)
        LineaDescarte.objects.create(id_descarte=d, id_galpon=self.g1, id_lote=self.l1, cantidad=100, motivo="Enfermedad")
        d = make_descarte(6, galpon=self.g1)
        LineaDescarte.objects.create(id_descarte=d, id_galpon=self.g1, id_materia_prima=self.mp, cantidad=5, motivo="Humedad")
        d = make_descarte(7, categoria=Descarte.CATEGORIA_STOCK)
        LineaDescarte.objects.create(id_descarte=d, id_producto=self.huevo, cantidad=20, motivo="Rotos")
        d = make_descarte(8, estado=Descarte.ESTADO_PENDIENTE, galpon=self.g1)
        LineaDescarte.objects.create(id_descarte=d, id_galpon=self.g1, id_lote=self.l1, cantidad=50, motivo="Pendiente")

    def get(self, ruta, **params):
        return self.client.get(f"/api/informes/{ruta}/", params)


# ── Parámetros ────────────────────────────────────────────────────────────────

class ParametrosInformeTests(DatosBase):

    def test_sin_fechas_usa_los_ultimos_30_dias(self):
        resp = self.get("produccion")
        self.assertEqual(resp.status_code, 200)
        desde = datetime.date.fromisoformat(resp.data["periodo"]["desde"])
        hasta = datetime.date.fromisoformat(resp.data["periodo"]["hasta"])
        self.assertEqual((hasta - desde).days, 29)

    def test_fecha_invalida(self):
        for ruta in ["produccion", "materias-primas", "descartes", "indicadores"]:
            resp = self.get(ruta, fecha_desde="01/08/2026")
            self.assertEqual(resp.status_code, 400, ruta)
            self.assertIn("fecha_desde", resp.data)

    def test_desde_posterior_a_hasta(self):
        resp = self.get("produccion", fecha_desde="2026-08-10", fecha_hasta="2026-08-01")
        self.assertEqual(resp.status_code, 400)

    def test_periodo_demasiado_largo(self):
        resp = self.get("produccion", fecha_desde="2025-01-01", fecha_hasta="2026-08-01")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("366", str(resp.data["fecha_desde"]))

    def test_galpon_inexistente(self):
        for ruta in ["produccion", "lotes", "descartes", "indicadores"]:
            self.assertEqual(self.get(ruta, id_galpon=9999, **PERIODO).status_code, 400, ruta)
        self.assertEqual(self.get("produccion", id_galpon="abc", **PERIODO).status_code, 400)

    def test_materia_prima_inexistente(self):
        self.assertEqual(self.get("materias-primas", id_materia_prima=9999, **PERIODO).status_code, 400)

    def test_formato_invalido(self):
        self.assertEqual(self.get("produccion", formato="doc", **PERIODO).status_code, 400)


# ── CU85 Producción ───────────────────────────────────────────────────────────

class InformeProduccionTests(DatosBase):

    def filas(self, **params):
        resp = self.get("produccion", **{**PERIODO, **params})
        self.assertEqual(resp.status_code, 200)
        return {f["galpon"]: f for f in resp.data["filas"]}, resp.data

    def test_filas_por_galpon_y_lote(self):
        filas, _ = self.filas()
        f1 = filas["Galpón 1"]
        self.assertEqual(f1["lote"], self.l1.codigo)
        self.assertEqual(f1["huevos_total"], 1700)   # la pendiente del día 5 no cuenta
        self.assertEqual(f1["dias_con_registro"], 2)
        self.assertEqual(f1["promedio_diario"], 850.0)
        f2 = filas["Galpón 2"]
        self.assertEqual(f2["huevos_total"], 400)
        self.assertEqual(f2["dias_con_registro"], 1)

    def test_postura_usa_las_gallinas_de_cada_dia(self):
        filas, _ = self.filas()
        # día 3: 900/1000 = 90 %; día 4: 800/900 (se descartaron 100 gallinas) = 88,9 %.
        self.assertEqual(filas["Galpón 1"]["postura_promedio"], 89.4)
        self.assertEqual(filas["Galpón 2"]["postura_promedio"], 80.0)

    def test_totales(self):
        _, data = self.filas()
        t = data["totales"]
        self.assertEqual(t["huevos_total"], 2100)
        self.assertEqual(t["dias_con_registro"], 2)
        self.assertEqual(t["promedio_diario"], 1050.0)
        # día 3: 1300/1500 = 86,7 %; día 4: 800/900 = 88,9 % → promedio 87,8 %.
        self.assertEqual(t["postura_promedio"], 87.8)

    def test_filtrar_por_galpon(self):
        filas, data = self.filas(id_galpon=self.g2.pk)
        self.assertEqual(list(filas), ["Galpón 2"])
        self.assertEqual(data["totales"]["huevos_total"], 400)

    def test_el_rango_acota_los_dias(self):
        filas, _ = self.filas(fecha_desde="2026-08-04", fecha_hasta="2026-08-04")
        self.assertEqual(list(filas), ["Galpón 1"])
        self.assertEqual(filas["Galpón 1"]["huevos_total"], 800)
        self.assertEqual(filas["Galpón 1"]["postura_promedio"], 88.9)

    def test_sin_datos(self):
        filas, data = self.filas(fecha_desde="2026-07-01", fecha_hasta="2026-07-10")
        self.assertEqual(filas, {})
        self.assertEqual(data["totales"]["huevos_total"], 0)
        self.assertIsNone(data["totales"]["postura_promedio"])

    def test_estructura_para_la_pantalla(self):
        _, data = self.filas()
        self.assertEqual(data["titulo"], "Informe de producción")
        self.assertEqual(data["columnas"][0]["clave"], "galpon")
        self.assertEqual([list(f) for f in data["filtros"]], [["Galpón", "Todos"]])


# ── CU86 Lotes ────────────────────────────────────────────────────────────────

class InformeLotesTests(DatosBase):

    def setUp(self):
        super().setUp()
        self.l3 = make_lote(
            self.g1, 800, actual=760, estado=Lote.ESTADO_FINALIZADO,
            fecha_ingreso=datetime.date(2025, 1, 1), fecha_vaciado=datetime.date(2025, 1, 31),
        )

    def filas(self, **params):
        resp = self.get("lotes", **params)
        self.assertEqual(resp.status_code, 200)
        return {f["lote"]: f for f in resp.data["filas"]}, resp.data

    def test_lista_todos_los_lotes(self):
        filas, _ = self.filas()
        self.assertEqual(set(filas), {self.l1.codigo, self.l2.codigo, self.l3.codigo})

    def test_edad_y_mortandad(self):
        filas, _ = self.filas()
        f1 = filas[self.l1.codigo]
        self.assertEqual(f1["etapa"], "Producción")
        self.assertEqual(f1["mortandad"], 100)
        self.assertEqual(f1["mortandad_pct"], 10.0)
        self.assertEqual(f1["galpon"], "Galpón 1")
        # Un lote vaciado deja de envejecer en la fecha de vaciado.
        f3 = filas[self.l3.codigo]
        self.assertEqual(f3["edad_dias"], 30)
        self.assertEqual(f3["edad_semanas"], 4)
        self.assertEqual(f3["mortandad"], 40)

    def test_edad_de_un_lote_activo_llega_hasta_hoy(self):
        from django.utils import timezone
        filas, _ = self.filas()
        esperado = (timezone.localdate() - datetime.date(2026, 1, 1)).days
        self.assertEqual(filas[self.l2.codigo]["edad_dias"], esperado)

    def test_filtros(self):
        filas, _ = self.filas(estado="F")
        self.assertEqual(set(filas), {self.l3.codigo})
        filas, _ = self.filas(id_galpon=self.g2.pk)
        self.assertEqual(set(filas), {self.l2.codigo})
        filas, _ = self.filas(estado="P", id_galpon=self.g1.pk)
        self.assertEqual(set(filas), {self.l1.codigo})

    def test_estado_invalido(self):
        self.assertEqual(self.get("lotes", estado="X").status_code, 400)

    def test_totales(self):
        _, data = self.filas()
        self.assertEqual(data["totales"]["cantidad_inicial"], 2300)
        self.assertEqual(data["totales"]["mortandad"], 140)


# ── CU87 Materias primas ──────────────────────────────────────────────────────

class InformeMateriasPrimasTests(DatosBase):

    def setUp(self):
        super().setUp()
        e = Entrada.objects.create(id_galpon=self.g1, fecha=fecha(3), estado=Entrada.ESTADO_FINALIZADA)
        LineaEntrada.objects.create(id_entrada=e, id_materia_prima=self.mp, cantidad=30)
        e = Entrada.objects.create(id_galpon=self.g1, fecha=fecha(4), estado=Entrada.ESTADO_PENDIENTE)
        LineaEntrada.objects.create(id_entrada=e, id_materia_prima=self.mp, cantidad=999)
        prov = Proveedor.objects.create(nombre="Agro Sur", email="a@b.com", telefono="381-455-0102")
        c = Compra.objects.create(
            id_proveedor=prov, categoria=Compra.CATEGORIA_MATERIAS_PRIMAS, nro_factura="0001-00000001",
            fecha=datetime.date(2026, 8, 2), estado=Compra.ESTADO_FINALIZADA,
        )
        LineaCompra.objects.create(id_compra=c, id_materia_prima=self.mp, cantidad=50, precio_unitario=10)
        # Descarte de stock de 5 kg (el de galpón del escenario base no resta stock).
        d = make_descarte(7, categoria=Descarte.CATEGORIA_STOCK)
        LineaDescarte.objects.create(id_descarte=d, id_materia_prima=self.mp, cantidad=5, motivo="Vencido")

    def fila(self, **params):
        resp = self.get("materias-primas", **{**PERIODO, **params})
        self.assertEqual(resp.status_code, 200)
        return {f["materia_prima"]: f for f in resp.data["filas"]}["Balanceado"]

    def test_consumido_comprado_descartado_y_stock(self):
        f = self.fila()
        self.assertEqual(f["consumido"], 30.0)    # la entrada pendiente no cuenta
        self.assertEqual(f["comprado"], 50.0)
        self.assertEqual(f["descartado"], 5.0)
        self.assertEqual(f["stock_actual"], 115.0)   # 100 + 50 − 5 − 30
        self.assertEqual(f["unidad"], "kg")
        self.assertFalse(f["bajo_minimo"])

    def test_el_rango_acota_los_movimientos_pero_no_el_stock(self):
        f = self.fila(fecha_desde="2026-08-05", fecha_hasta="2026-08-10")
        self.assertEqual(f["consumido"], 0.0)
        self.assertEqual(f["comprado"], 0.0)
        self.assertEqual(f["descartado"], 5.0)
        self.assertEqual(f["stock_actual"], 115.0)

    def test_bajo_el_minimo(self):
        MateriaPrima.objects.filter(pk=self.mp.pk).update(stock_minimo=500)
        self.assertTrue(self.fila()["bajo_minimo"])

    def test_filtrar_por_materia_prima(self):
        otra = MateriaPrima.objects.create(materia_prima="Vacuna", unidad="dosis", stock_minimo=1, stock_inicial=10)
        resp = self.get("materias-primas", id_materia_prima=otra.pk, **PERIODO)
        self.assertEqual([f["materia_prima"] for f in resp.data["filas"]], ["Vacuna"])

    def test_incluye_materias_primas_sin_movimientos(self):
        MateriaPrima.objects.create(materia_prima="Vacuna", unidad="dosis", stock_minimo=1, stock_inicial=10)
        resp = self.get("materias-primas", **PERIODO)
        self.assertEqual([f["materia_prima"] for f in resp.data["filas"]], ["Balanceado", "Vacuna"])


# ── CU88 Descartes ────────────────────────────────────────────────────────────

class InformeDescartesTests(DatosBase):

    def filas(self, **params):
        resp = self.get("descartes", **{**PERIODO, **params})
        self.assertEqual(resp.status_code, 200)
        return resp.data["filas"], resp.data

    def test_lista_solo_finalizados_del_mas_reciente_al_mas_antiguo(self):
        filas, _ = self.filas()
        self.assertEqual([f["fecha"] for f in filas], ["2026-08-07", "2026-08-06", "2026-08-04"])

    def test_detalle_de_cada_tipo(self):
        filas, _ = self.filas()
        por_tipo = {f["tipo"]: f for f in filas}
        g = por_tipo["Gallinas"]
        self.assertEqual((g["galpon"], g["item"], g["cantidad"], g["unidad"], g["motivo"]),
                         ("Galpón 1", self.l1.codigo, 100.0, "gallinas", "Enfermedad"))
        m = por_tipo["Materia prima"]
        self.assertEqual((m["item"], m["cantidad"], m["unidad"], m["origen"]), ("Balanceado", 5.0, "kg", "Galpón"))
        p = por_tipo["Producto"]
        self.assertEqual((p["item"], p["galpon"], p["origen"]), ("Huevo N°1", "—", "Stock"))

    def test_filtrar_por_tipo(self):
        for tipo, esperado in [("G", "Gallinas"), ("M", "Materia prima"), ("P", "Producto")]:
            filas, _ = self.filas(tipo=tipo)
            self.assertEqual([f["tipo"] for f in filas], [esperado])

    def test_filtrar_por_galpon(self):
        filas, _ = self.filas(id_galpon=self.g1.pk)
        self.assertEqual({f["tipo"] for f in filas}, {"Gallinas", "Materia prima"})
        filas, _ = self.filas(id_galpon=self.g2.pk)
        self.assertEqual(filas, [])

    def test_rango(self):
        filas, _ = self.filas(fecha_desde="2026-08-05", fecha_hasta="2026-08-06")
        self.assertEqual([f["tipo"] for f in filas], ["Materia prima"])

    def test_resumen_y_total(self):
        _, data = self.filas()
        self.assertEqual(data["resumen"], {"Gallinas": 1, "Materia prima": 1, "Producto": 1})
        self.assertEqual(data["totales"]["cantidad"], 3)

    def test_tipo_invalido(self):
        self.assertEqual(self.get("descartes", tipo="X", **PERIODO).status_code, 400)

    def test_sin_datos(self):
        filas, data = self.filas(fecha_desde="2026-07-01", fecha_hasta="2026-07-10")
        self.assertEqual(filas, [])
        self.assertIsNone(data["totales"])


# ── CU89 Indicadores ──────────────────────────────────────────────────────────

class IndicadoresTests(DatosBase):

    def serie(self, **params):
        resp = self.get("indicadores", **{**PERIODO, **params})
        self.assertEqual(resp.status_code, 200)
        return {p["fecha"]: p["valor"] for p in resp.data["serie"]}, resp.data

    def test_la_serie_trae_todos_los_dias_del_periodo(self):
        serie, data = self.serie()
        self.assertEqual(len(serie), 10)
        self.assertEqual(data["unidad"], "%")

    def test_postura_diaria(self):
        serie, data = self.serie(indicador="postura")
        self.assertEqual(serie["2026-08-03"], 86.7)
        self.assertEqual(serie["2026-08-04"], 88.9)
        self.assertIsNone(serie["2026-08-05"])    # solo hay una recolección pendiente
        self.assertIsNone(serie["2026-08-01"])
        self.assertEqual(data["promedio"], 87.8)

    def test_postura_por_galpon(self):
        serie, _ = self.serie(indicador="postura", id_galpon=self.g2.pk)
        self.assertEqual(serie["2026-08-03"], 80.0)
        self.assertIsNone(serie["2026-08-04"])

    def test_mortandad(self):
        serie, data = self.serie(indicador="mortandad")
        self.assertEqual(serie["2026-08-04"], 100)
        self.assertEqual(serie["2026-08-03"], 0)
        self.assertEqual(serie["2026-08-08"], 0)     # el descarte pendiente no cuenta
        self.assertEqual(data["total"], 100.0)
        self.assertEqual(data["unidad"], "gallinas")

    def test_mortandad_por_galpon(self):
        serie, _ = self.serie(indicador="mortandad", id_galpon=self.g2.pk)
        self.assertEqual(sum(serie.values()), 0)

    def test_consumo_de_una_materia_prima(self):
        e = Entrada.objects.create(id_galpon=self.g1, fecha=fecha(3), estado=Entrada.ESTADO_FINALIZADA)
        LineaEntrada.objects.create(id_entrada=e, id_materia_prima=self.mp, cantidad=30)
        e = Entrada.objects.create(id_galpon=self.g2, fecha=fecha(3), estado=Entrada.ESTADO_FINALIZADA)
        LineaEntrada.objects.create(id_entrada=e, id_materia_prima=self.mp, cantidad=12)
        serie, data = self.serie(indicador="consumo", id_materia_prima=self.mp.pk)
        self.assertEqual(serie["2026-08-03"], 42.0)
        self.assertEqual(data["unidad"], "kg")
        serie, _ = self.serie(indicador="consumo", id_materia_prima=self.mp.pk, id_galpon=self.g2.pk)
        self.assertEqual(serie["2026-08-03"], 12.0)

    def test_consumo_exige_la_materia_prima(self):
        resp = self.get("indicadores", indicador="consumo", **PERIODO)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("id_materia_prima", resp.data)

    def test_indicador_invalido(self):
        self.assertEqual(self.get("indicadores", indicador="x", **PERIODO).status_code, 400)

    def test_resumen(self):
        _, data = self.serie()
        self.assertEqual(data["resumen"], {
            "huevos_producidos": 2100,
            "postura_promedio": 87.8,
            "mortandad_total": 100,
            "descartes_registrados": 3,
        })


# ── Exportación ───────────────────────────────────────────────────────────────

class ExportacionInformesTests(DatosBase):

    RUTAS = ["produccion", "lotes", "materias-primas", "descartes", "indicadores"]

    def test_excel_de_cada_informe(self):
        for ruta in self.RUTAS:
            resp = self.get(ruta, formato="xlsx", **PERIODO)
            self.assertEqual(resp.status_code, 200, ruta)
            self.assertIn("spreadsheetml", resp["Content-Type"])
            self.assertIn(".xlsx", resp["Content-Disposition"])
            wb = load_workbook(BytesIO(resp.content))
            self.assertTrue(wb.active["A1"].value, ruta)

    def test_contenido_del_excel_de_produccion(self):
        resp = self.get("produccion", formato="xlsx", **PERIODO)
        ws = load_workbook(BytesIO(resp.content)).active
        self.assertEqual(ws["A1"].value, "Informe de producción")
        self.assertIn("Período: 01/08/2026 al 10/08/2026", ws["A2"].value)
        self.assertEqual([c.value for c in ws[5]][:3], ["Galpón", "Lote", "Huevos producidos"])
        self.assertEqual(ws["A6"].value, "Galpón 1")
        self.assertEqual(ws["C6"].value, 1700)
        self.assertEqual(ws["A8"].value, "Total")     # fila de totales
        self.assertEqual(ws["C8"].value, 2100)

    def test_pdf_de_cada_informe(self):
        for ruta in self.RUTAS:
            resp = self.get(ruta, formato="pdf", **PERIODO)
            self.assertEqual(resp.status_code, 200, ruta)
            self.assertEqual(resp["Content-Type"], "application/pdf")
            self.assertTrue(resp.content.startswith(b"%PDF"), ruta)
            self.assertIn(".pdf", resp["Content-Disposition"])

    def test_pdf_sin_datos(self):
        resp = self.get("descartes", formato="pdf", fecha_desde="2026-07-01", fecha_hasta="2026-07-10")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_nombre_del_archivo(self):
        resp = self.get("produccion", formato="xlsx", **PERIODO)
        self.assertIn("informe-produccion-2026-08-01_2026-08-10.xlsx", resp["Content-Disposition"])
        resp = self.get("lotes", formato="pdf")
        self.assertIn("informe-lotes.pdf", resp["Content-Disposition"])

    def test_la_exportacion_respeta_los_filtros(self):
        resp = self.get("produccion", formato="xlsx", id_galpon=self.g2.pk, **PERIODO)
        ws = load_workbook(BytesIO(resp.content)).active
        self.assertIn("Galpón: Galpón 2", ws["A2"].value)
        self.assertEqual(ws["A6"].value, "Galpón 2")
        self.assertEqual(ws["A7"].value, "Total")

    def test_nombres_con_caracteres_especiales_en_el_pdf(self):
        MateriaPrima.objects.create(materia_prima="Maíz & <soja> ñandú", unidad="kg", stock_minimo=1, stock_inicial=1)
        resp = self.get("materias-primas", formato="pdf", **PERIODO)
        self.assertEqual(resp.status_code, 200)


# ── Permisos ──────────────────────────────────────────────────────────────────

class PermisosInformesTests(DatosBase):

    RUTAS = ExportacionInformesTests.RUTAS

    def cliente(self, usuario=None):
        c = APIClient()
        if usuario:
            auth(c, usuario)
        return c

    def test_administrador_y_consulta_ven_todos_los_informes(self):
        consulta = make_usuario("consulta", Usuario.ROL_CONSULTA, "33333333")
        for usuario in (self.admin, consulta):
            c = self.cliente(usuario)
            for ruta in self.RUTAS:
                self.assertEqual(c.get(f"/api/informes/{ruta}/", PERIODO).status_code, 200, (usuario.usuario, ruta))
                resp = c.get(f"/api/informes/{ruta}/", {**PERIODO, "formato": "pdf"})
                self.assertEqual(resp.status_code, 200, (usuario.usuario, ruta))

    def test_operario_sin_acceso(self):
        c = self.cliente(make_usuario("operario", Usuario.ROL_OPERARIO, "22222222"))
        for ruta in self.RUTAS:
            self.assertEqual(c.get(f"/api/informes/{ruta}/", PERIODO).status_code, 403, ruta)
            self.assertEqual(c.get(f"/api/informes/{ruta}/", {**PERIODO, "formato": "xlsx"}).status_code, 403, ruta)

    def test_sin_token_401(self):
        c = self.cliente()
        for ruta in self.RUTAS:
            self.assertEqual(c.get(f"/api/informes/{ruta}/", PERIODO).status_code, 401, ruta)

    def test_solo_lectura(self):
        for ruta in self.RUTAS:
            self.assertEqual(self.client.post(f"/api/informes/{ruta}/", {}, format="json").status_code, 405, ruta)
