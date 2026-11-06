"""
Carga un juego de datos GRANDE y variado en la base de AviGest.

Es el hermano mayor de poblar_datos.py: la misma idea (simular la granja dia
por dia y recien despues escribir todo en una transaccion), pero con mas de
todo, para ver como se comporta el sistema con volumen real: paginacion de
varias paginas, graficos con un ano de historia, informes largos y el panel
principal con sus alertas.

Uso (desde la carpeta backend, con el entorno virtual activo):

    py poblar_datos_v2.py                 # carga los datos (si la base esta vacia)
    py poblar_datos_v2.py --limpiar       # borra los datos de negocio y los vuelve a cargar
    py poblar_datos_v2.py --limpiar --si  # igual, sin pedir confirmacion
    py poblar_datos_v2.py --dias 180      # historial mas corto (por defecto 365 dias)
    py poblar_datos_v2.py --semilla 7     # otra variante de los mismos datos

Que genera (todo relativo a la fecha de hoy, asi que siempre queda "reciente"):

  * 11 usuarios: 1 administrador, 2 de consulta, 7 operarios y 1 operario dado
    de baja.
  * 12 galpones (2 inactivos y 1 activo pero vacio) con sus operarios asignados.
  * 5 productos (4 activos y 1 discontinuado) y 22 materias primas.
  * 12 proveedores (2 inactivos).
  * 16 lotes a lo largo de dos anos: finalizados, en produccion y en
    transicion, cada uno con su compra y su plan. Mas dos compras de lotes sin
    asignar a un galpon.
  * Un ano de recolecciones diarias, entradas a galpones, descartes de galpon y
    de stock, salidas de huevos y compras periodicas a cada proveedor.
  * Situaciones preparadas para que el panel muestre las cuatro alertas: un
    lote viejo con la postura por debajo del minimo, un brote de mortandad, una
    transicion que vence en dos dias y un galpon que dejo de cargar
    recolecciones. Ademas se dejan algunas alertas ya resueltas, como si el
    sistema hubiera estado corriendo todo el ano.
  * Registros PENDIENTES recientes en todas las secciones y varias materias
    primas por debajo del stock minimo.

Las cantidades se calculan simulando el stock dia por dia, asi que el stock de
productos y de materias primas nunca queda negativo y se respetan las reglas
del sistema (un solo lote activo por galpon, lotes que salen de una compra
finalizada, solo los registros finalizados mueven el stock).
"""

import argparse
import datetime as dt
import os
import random
import sys
from collections import defaultdict
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from alertas.generacion import generar_alertas  # noqa: E402
from alertas.models import Alerta, TipoAlerta  # noqa: E402
from compras.models import Compra, LineaCompra  # noqa: E402
from descartes.models import Descarte, LineaDescarte  # noqa: E402
from entradas.models import Entrada, LineaEntrada  # noqa: E402
from galpones.models import Galpon, UsuarioDelGalpon  # noqa: E402
from lotes.models import Lote, PlanTransicion  # noqa: E402
from materias_primas.models import MateriaPrima  # noqa: E402
from productos.models import Producto  # noqa: E402
from proveedores.models import Proveedor  # noqa: E402
from recolecciones.models import LineaRecoleccion, Recoleccion  # noqa: E402
from salidas.models import LineaSalida, Salida  # noqa: E402
from usuarios.models import Usuario  # noqa: E402

PASSWORD = "AviGest2026!"
DIAS_TRANSICION = 28

HOY = timezone.localdate()
AHORA = timezone.localtime()


def dia(n):
    """Fecha de hace n dias."""
    return HOY - dt.timedelta(days=n)


def momento(fecha, hora, minuto=0):
    """
    Fecha y hora (con zona horaria) de un dia. Si caeria en el futuro (por
    ejemplo, un registro de hoy a una hora que todavia no llego) se lo adelanta
    a un rato antes de ahora.
    """
    naive = dt.datetime.combine(fecha, dt.time(hora, minuto))
    valor = timezone.make_aware(naive)
    return min(valor, AHORA - dt.timedelta(minutes=20))


def dec(valor, lugares=2):
    return Decimal(str(round(valor, lugares))).quantize(Decimal(10) ** -lugares)


def redondear_arriba(valor, paso):
    """El múltiplo de `paso` inmediatamente superior (asi se compra por bolsa)."""
    if paso <= 0:
        return valor
    return int(-(-valor // paso) * paso)


# ---------------------------------------------------------------------------
# Datos base
# ---------------------------------------------------------------------------

# usuario, nombre, apellido, dni, rol, estado
USUARIOS = [
    ("admin.demo", "Mariana", "Rojas", "90000001", Usuario.ROL_ADMINISTRADOR, "A"),
    ("consulta.demo", "Lucía", "Benítez", "90000002", Usuario.ROL_CONSULTA, "A"),
    ("consulta.tutor", "Enzo", "Carrizo", "90000011", Usuario.ROL_CONSULTA, "A"),
    ("operario1", "Juan", "Pérez", "90000003", Usuario.ROL_OPERARIO, "A"),
    ("operario2", "Marta", "Gómez", "90000004", Usuario.ROL_OPERARIO, "A"),
    ("operario3", "Diego", "Ledesma", "90000005", Usuario.ROL_OPERARIO, "A"),
    ("operario4", "Sofía", "Juárez", "90000006", Usuario.ROL_OPERARIO, "A"),
    ("operario5", "Ramiro", "Sosa", "90000007", Usuario.ROL_OPERARIO, "A"),
    ("operario6", "Carla", "Medina", "90000008", Usuario.ROL_OPERARIO, "A"),
    ("operario7", "Nicolás", "Herrera", "90000009", Usuario.ROL_OPERARIO, "A"),
    ("operario.baja", "Pablo", "Quiroga", "90000010", Usuario.ROL_OPERARIO, "I"),
]

# clave, nombre, latitud, longitud, superficie, capacidad, estado, descripcion, operarios
GALPONES = [
    ("G1", "Galpón 1", "-26.808120", "-65.217340", "620.000000", 4000, "A",
     "Galpón de postura con comederos automáticos.", ["operario1", "operario4"]),
    ("G2", "Galpón 2", "-26.808410", "-65.216910", "780.000000", 5000, "A",
     "Galpón de postura, el más grande de la granja.", ["operario1", "operario2"]),
    ("G3", "Galpón 3", "-26.808730", "-65.216480", "700.000000", 4500, "A",
     "Galpón de postura con ventilación cruzada.", ["operario2"]),
    ("G4", "Galpón 4", "-26.809010", "-65.216050", "450.000000", 3200, "A",
     "Galpón de recría y transición, con calefacción a gas.", ["operario3"]),
    ("G5", "Galpón 5", "-26.809290", "-65.215630", "600.000000", 4000, "A",
     "Galpón de postura, el más alejado del acceso.", ["operario3", "operario5"]),
    ("G6", "Galpón 6", "-26.809580", "-65.215200", "660.000000", 4200, "A",
     "Galpón de postura reformado el año pasado.", ["operario4"]),
    ("G7", "Galpón 7", "-26.809860", "-65.214770", "500.000000", 3500, "A",
     "Galpón de recría, con piso de cemento alisado.", ["operario5", "operario6"]),
    ("G8", "Galpón 8", "-26.810140", "-65.214340", "720.000000", 4600, "A",
     "Galpón de postura con nidales metálicos.", ["operario6"]),
    ("G9", "Galpón 9", "-26.810420", "-65.213910", "540.000000", 3600, "A",
     "Galpón de postura, el más nuevo.", ["operario7"]),
    ("G10", "Galpón 10", "-26.810700", "-65.213480", "480.000000", 3000, "A",
     "Galpón vacío, desinfectado y listo para recibir un lote.", ["operario7"]),
    ("G11", "Galpón 11", "-26.810980", "-65.213050", "380.000000", 2500, "I",
     "Galpón antiguo fuera de servicio por refacciones.", []),
    ("G12", "Galpón 12", "-26.811260", "-65.212620", "300.000000", 2000, "I",
     "Depósito reconvertido; sin habilitación para aves.", []),
]

# clave, nombre, descripcion, estado, stock_inicial, proporcion de la recoleccion
PRODUCTOS = [
    ("N0", "Huevo Jumbo", "Huevo extra grande, 73 g o más.", "A", 120, 0.06),
    ("N1", "Huevo Nº1", "Huevo grande, 60 g o más.", "A", 900, 0.46),
    ("N2", "Huevo Nº2", "Huevo mediano, entre 50 y 60 g.", "A", 700, 0.34),
    ("N3", "Huevo Nº3", "Huevo chico, menos de 50 g.", "A", 400, 0.14),
    ("N4", "Huevo de campo (discontinuado)", "Línea que ya no se comercializa.", "I", 0, 0.0),
]

# clave, nombre, descripcion, unidad, estado, proveedor, precio, paso de compra
MATERIAS_PRIMAS = [
    ("BAL", "Balanceado postura", "Alimento balanceado para gallinas en producción.", "kg", "A", "P1", 540, 50),
    ("REC", "Balanceado recría", "Alimento para pollitas en transición.", "kg", "A", "P1", 590, 50),
    ("INI", "Balanceado iniciador", "Alimento de las primeras semanas de vida.", "kg", "A", "P1", 640, 50),
    ("MAI", "Maíz molido", "Maíz molido para complementar la ración.", "kg", "A", "P1", 320, 50),
    ("SOJ", "Soja peleteada", "Fuente de proteína de la ración.", "kg", "A", "P8", 690, 25),
    ("AFR", "Afrechillo de trigo", "Aporta fibra a la ración.", "kg", "A", "P8", 280, 50),
    ("CON", "Calcio (conchilla)", "Aporte de calcio para la calidad de la cáscara.", "kg", "A", "P3", 190, 25),
    ("FOS", "Fosfato bicálcico", "Mineral para el desarrollo óseo.", "kg", "A", "P3", 850, 25),
    ("SAL", "Sal gruesa", "Complemento mineral de la ración.", "kg", "A", "P3", 120, 25),
    ("CAL", "Cal viva", "Para desinfección de pisos y fosas.", "kg", "A", "P3", 160, 25),
    ("CAS", "Cáscara de arroz", "Cama para los galpones.", "kg", "A", "P9", 85, 100),
    ("VIR", "Viruta de madera", "Cama alternativa para la recría.", "kg", "A", "P9", 110, 100),
    ("VIT", "Vitaminas y minerales", "Premezcla vitamínica para el alimento.", "kg", "A", "P3", 4200, 1),
    ("DES", "Desinfectante (Virkon)", "Desinfectante de uso general.", "kg", "A", "P4", 18500, 1),
    ("DET", "Detergente alcalino", "Limpieza de comederos y bebederos.", "l", "A", "P4", 7600, 5),
    ("VAC", "Vacuna Newcastle", "Vacuna contra la enfermedad de Newcastle.", "dosis", "A", "P4", 95, 500),
    ("VBR", "Vacuna Bronquitis", "Vacuna contra la bronquitis infecciosa.", "dosis", "A", "P4", 110, 500),
    ("ANT", "Antiparasitario", "Tratamiento antiparasitario del plantel.", "dosis", "A", "P4", 140, 250),
    ("GAS", "Gas envasado (10 kg)", "Garrafas para la calefacción de la recría.", "unid.", "A", "P5", 28000, 1),
    ("MAP", "Maples de cartón (30 huevos)", "Maples para el armado de cajones.", "unid.", "A", "P10", 180, 500),
    ("CAJ", "Cajones de cartón", "Cajones para la venta por mayor.", "unid.", "A", "P10", 950, 100),
    ("HAR", "Harina de pescado", "Ya no se usa en la ración.", "kg", "I", "P1", 980, 25),
]

# clave, nombre, cuit (sin digito verificador), direccion, email, telefono, estado, ciclo de pedido (dias)
PROVEEDORES = [
    ("P1", "Alimentos del Norte S.R.L.", "3071234567", "Ruta 9 km 1308, San Miguel de Tucumán",
     "ventas@alimentosdelnorte.com.ar", "3814551020", "A", 14),
    ("P2", "Granja Los Sauces S.A.", "3069876543", "Ruta 38 km 12, Famaillá, Tucumán",
     "comercial@granjalossauces.com.ar", "3863420011", "A", 0),
    ("P3", "Agropecuaria Tucumán S.A.", "3070112233", "Av. Belgrano 1450, San Miguel de Tucumán",
     "pedidos@agrotucuman.com.ar", "3814220987", "A", 21),
    ("P4", "Veterinaria Del Sur", "3065544332", "Alberdi 322, Concepción, Tucumán",
     "info@veterinariadelsur.com.ar", "3865431234", "A", 28),
    ("P5", "Gas del Valle S.R.L.", "3072223335", "Av. Mate de Luna 2100, San Miguel de Tucumán",
     "garrafas@gasdelvalle.com.ar", "3814300555", "A", 28),
    ("P6", "Avícola La Pampa S.A.", "3061239874", "Ruta 34 km 880, Rafaela, Santa Fe",
     "ventas@avicolalapampa.com.ar", "3492445566", "A", 0),
    ("P7", "Molino Viejo S.R.L.", "3068887776", "San Martín 95, Monteros, Tucumán",
     "contacto@molinoviejo.com.ar", "3863415500", "I", 0),
    ("P8", "Oleaginosas del Centro S.A.", "3064455667", "Ruta 157 km 4, Cruz Alta, Tucumán",
     "ventas@oleaginosasdelcentro.com.ar", "3814778899", "A", 21),
    ("P9", "Arrocera del Este S.R.L.", "3063332221", "Ruta 302 km 9, Banda del Río Salí, Tucumán",
     "administracion@arroceradeleste.com.ar", "3814661122", "A", 35),
    ("P10", "Envases Norte S.A.", "3067778889", "Parque Industrial, Lules, Tucumán",
     "pedidos@envasesnorte.com.ar", "3814990011", "A", 28),
    ("P11", "Transporte Avícola Díaz", "3062221119", "Lavalle 780, Tafí Viejo, Tucumán",
     "logistica@transportediaz.com.ar", "3815112233", "A", 0),
    ("P12", "Insumos Rurales del Norte", "3066665554", "Ruta 9 km 1290, Tucumán",
     "ventas@insumosrurales.com.ar", "3814334455", "I", 0),
]

# Lotes de gallinas. `ingreso` y `vaciado` son "hace cuántos días"; `postura` es
# la postura de referencia del lote en su pico. `mortandad` multiplica las bajas
# diarias (1.0 es lo normal). `pausa` son los días del final sin recolecciones.
LOTES = [
    # --- ciclos cerrados de hace dos años (quedan fuera del rango por defecto)
    dict(clave="L01", galpon="G1", ingreso=790, vaciado=420, aves=2800, prov="P2", precio=6200,
         postura=0.88, obs="Primer ciclo del galpón después de la ampliación."),
    dict(clave="L02", galpon="G2", ingreso=800, vaciado=430, aves=3400, prov="P6", precio=6100,
         postura=0.90, obs="Lote de buen rendimiento. Ciclo cerrado sin novedades."),
    dict(clave="L03", galpon="G5", ingreso=780, vaciado=400, aves=3000, prov="P2", precio=6300,
         postura=0.86, obs="Ciclo anterior. Vaciado sanitario completo."),
    # --- ciclos cerrados dentro del último año
    dict(clave="L04", galpon="G1", ingreso=410, vaciado=62, aves=3200, prov="P2", precio=7900,
         postura=0.89, obs="Ciclo cerrado. El galpón se desinfectó antes del lote nuevo."),
    dict(clave="L05", galpon="G7", ingreso=415, vaciado=35, aves=3100, prov="P6", precio=8100,
         postura=0.87, obs="Ciclo cerrado. Buen cierre de postura."),
    dict(clave="L06", galpon="G9", ingreso=430, vaciado=22, aves=3000, prov="P2", precio=8000,
         postura=0.85, obs="Ciclo cerrado antes de lo previsto por caída de postura."),
    dict(clave="L07", galpon="G2", ingreso=420, vaciado=112, aves=3600, prov="P6", precio=8200,
         postura=0.91, obs="Ciclo cerrado. El mejor rendimiento del año."),
    # --- lotes en producción
    dict(clave="L08", galpon="G3", ingreso=352, aves=3700, prov="P6", precio=8400,
         postura=0.76, obs="Lote veterano de bajo rendimiento: la postura ya no levanta "
                           "y se está evaluando el vaciado."),
    dict(clave="L09", galpon="G5", ingreso=306, aves=3500, prov="P2", precio=8600,
         postura=0.90, pausa=6,
         obs="El operario a cargo está de licencia; quedaron recolecciones sin cargar."),
    dict(clave="L10", galpon="G6", ingreso=248, aves=3800, prov="P6", precio=8800,
         postura=0.92, obs="Lote en plena producción."),
    dict(clave="L11", galpon="G4", ingreso=190, aves=2900, prov="P2", precio=9000,
         postura=0.91, obs="Lote en producción, alojado en el galpón de recría."),
    dict(clave="L12", galpon="G8", ingreso=124, aves=4100, prov="P6", precio=9200,
         postura=0.93, mortandad=1.0, brote=(5, 70),
         obs="Brote respiratorio esta semana; se está tratando con el veterinario."),
    dict(clave="L13", galpon="G2", ingreso=104, aves=4300, prov="P2", precio=9300,
         postura=0.92, obs="Lote nuevo del galpón más grande."),
    dict(clave="L14", galpon="G1", ingreso=54, aves=3300, prov="P6", precio=9500,
         postura=0.93, obs="Pollitas de recría propia. Empezaron a poner hace poco."),
    # --- lotes en transición
    dict(clave="L15", galpon="G7", ingreso=26, aves=3000, prov="P2", precio=9600, postura=0.0,
         obs="En las últimas semanas del plan de transición."),
    dict(clave="L16", galpon="G9", ingreso=12, aves=3100, prov="P6", precio=9700, postura=0.0,
         obs="Recién ingresado. En plan de transición."),
]

# Lotes ya comprados y todavia sin asignar a un galpon: (aves, proveedor, precio, dias atras, estado)
LOTES_COMPRADOS = [
    (3000, "P2", 9800, 4, Compra.ESTADO_FINALIZADA),
    (2600, "P6", 9900, 9, Compra.ESTADO_FINALIZADA),
    (2000, "P6", 9750, 1, Compra.ESTADO_PENDIENTE),
]

# Plan de transicion de referencia (agua L, alimento kg, horas de luz por semana)
PLAN = {
    "agua": [4.20, 4.80, 5.50, 6.10],
    "alimento": [18.00, 21.50, 25.00, 28.50],
    "luz": [10.00, 12.00, 14.00, 16.00],
}

MOTIVOS_MUERTE = [
    "Muerte natural", "Enfermedad respiratoria", "Golpe de calor",
    "Aplastamiento en el nidal", "Prolapso", "Muerte súbita",
    "Descarte por bajo peso", "Picaje",
]

OBS_SALIDA = [
    "", "", "", "Retiró el camión de reparto.", "Entrega a mayorista.",
    "Pedido del supermercado del centro.", "Venta a distribuidor de Famaillá.",
]


def cuit_completo(base10):
    """Agrega el digito verificador al CUIT (misma regla que usa el sistema)."""
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(d) * p for d, p in zip(base10, pesos))
    v = 11 - suma % 11
    v = 0 if v == 11 else 9 if v == 10 else v
    return f"{base10}{v}"


def claves_activas(tabla, posicion_estado):
    return [fila[0] for fila in tabla if fila[posicion_estado] == "A"]


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

def limpiar():
    """Borra los datos de negocio. Los usuarios y los tipos de alerta no se tocan."""
    for modelo in (
        Alerta, Descarte, Entrada, Salida, Recoleccion, Compra, Lote,
        Galpon, Producto, MateriaPrima, Proveedor,
    ):
        modelo.objects.all().delete()


def hay_datos():
    return any(
        m.objects.exists()
        for m in (Galpon, Lote, Producto, MateriaPrima, Proveedor, Compra, Recoleccion)
    )


# ---------------------------------------------------------------------------
# Simulacion (todo en memoria; despues se escribe)
# ---------------------------------------------------------------------------

class Plan:
    """Todos los registros que se van a crear, calculados antes de tocar la base."""

    def __init__(self, dias, semilla):
        self.rnd = random.Random(semilla)
        self.inicio = dia(dias)

        self.galpones_activos = claves_activas(GALPONES, 6)
        self.productos_activos = [p[0] for p in PRODUCTOS if p[3] == "A"]
        self.proporciones = {p[0]: p[5] for p in PRODUCTOS}

        self.lotes = []
        for l in LOTES:
            self.lotes.append(dict(
                clave=l["clave"], galpon=l["galpon"], ingreso=dia(l["ingreso"]),
                vaciado=dia(l["vaciado"]) if l.get("vaciado") is not None else None,
                aves=l["aves"], proveedor=l["prov"], precio=l["precio"],
                postura=l["postura"], obs=l["obs"],
                mortandad=l.get("mortandad", 1.0), brote=l.get("brote"),
                pausa=l.get("pausa", 0),
                muertes=[],
            ))

        self.descartes = []
        self.recolecciones = []
        self.entradas = []
        self.salidas = []
        self.compras_mp = []
        self.demanda = defaultdict(lambda: defaultdict(float))

    # -- utilidades ---------------------------------------------------------

    def fase(self, lote, d):
        """None si el lote no esta activo ese dia; 'T' transicion; 'P' produccion."""
        if d < lote["ingreso"]:
            return None
        if lote["vaciado"] is not None and d >= lote["vaciado"]:
            return None
        if (d - lote["ingreso"]).days < DIAS_TRANSICION:
            return "T"
        return "P"

    def lote_en(self, galpon, d):
        for lote in self.lotes:
            if lote["galpon"] == galpon and self.fase(lote, d):
                return lote
        return None

    def vivas(self, lote, d):
        muertas = sum(c for f, c in lote["muertes"] if f <= d)
        return max(lote["aves"] - muertas, 1)

    def postura_del_dia(self, lote, d):
        """
        Curva de postura: sube durante las tres primeras semanas de produccion,
        se sostiene unos meses y despues cae de a poco, como en la realidad.
        """
        dias_prod = (d - lote["ingreso"]).days - DIAS_TRANSICION
        if dias_prod < 21:
            rampa = 0.62 + 0.38 * (dias_prod / 21)
        else:
            rampa = 1.0
        caida = max(0.0, (dias_prod - 150) / 1400)
        valor = lote["postura"] * rampa * (1 - caida) + self.rnd.gauss(0, 0.015)
        return max(0.40, min(0.97, valor))

    # -- 1. descartes de galpon (muertes de gallinas, huevos rotos) ---------

    def generar_descartes_galpon(self):
        r = self.rnd
        menores = self.productos_activos[-2:]
        for lote in self.lotes:
            d = max(self.inicio, lote["ingreso"]) + dt.timedelta(days=r.randint(0, 2))
            fin = HOY if lote["vaciado"] is None else lote["vaciado"] - dt.timedelta(days=1)
            while d <= fin:
                fase = self.fase(lote, d)
                if fase:
                    base = r.randint(3, 9) if fase == "T" else r.randint(1, 5)
                    cantidad = max(1, int(round(base * lote["mortandad"])))
                    estado = (
                        Descarte.ESTADO_PENDIENTE
                        if d >= HOY - dt.timedelta(days=1)
                        else Descarte.ESTADO_FINALIZADO
                    )
                    lineas = [dict(lote=lote["clave"], cantidad=cantidad, motivo=r.choice(MOTIVOS_MUERTE))]
                    if fase == "P" and r.random() < 0.35:
                        lineas.append(dict(
                            producto=r.choice(menores), cantidad=r.randint(20, 110),
                            motivo="Huevos rotos encontrados en el nidal",
                        ))
                    if r.random() < 0.05:
                        lineas.append(dict(
                            mp=r.choice(["CAS", "VIR"]), cantidad=r.choice([30, 40, 60]),
                            motivo="Cama húmeda que hubo que retirar",
                        ))
                    self.descartes.append(dict(
                        categoria=Descarte.CATEGORIA_GALPON, galpon=lote["galpon"], fecha=d,
                        hora=(16, r.randint(0, 40)), estado=estado, lineas=lineas, obs="",
                    ))
                    if estado == Descarte.ESTADO_FINALIZADO:
                        lote["muertes"].append((d, cantidad))
                d += dt.timedelta(days=r.randint(3, 6))

            # Brote puntual: varias bajas seguidas en los ultimos dias.
            if lote["brote"]:
                desde, total = lote["brote"]
                por_dia = max(1, total // desde)
                for i in range(desde):
                    f = dia(desde - i)
                    if self.fase(lote, f) is None or f >= HOY - dt.timedelta(days=1):
                        continue
                    cantidad = por_dia + r.randint(-3, 3)
                    self.descartes.append(dict(
                        categoria=Descarte.CATEGORIA_GALPON, galpon=lote["galpon"], fecha=f,
                        hora=(17, 30), estado=Descarte.ESTADO_FINALIZADO,
                        lineas=[dict(lote=lote["clave"], cantidad=cantidad,
                                     motivo="Enfermedad respiratoria")],
                        obs="Brote respiratorio: se aisló el galpón y se avisó al veterinario.",
                    ))
                    lote["muertes"].append((f, cantidad))

    # -- 2. recolecciones -----------------------------------------------------

    def generar_recolecciones(self):
        r = self.rnd
        activos = self.productos_activos
        d = self.inicio
        while d <= HOY:
            for galpon in self.galpones_activos:
                lote = self.lote_en(galpon, d)
                if not lote or self.fase(lote, d) != "P":
                    continue
                # Un lote puede quedar varios dias sin que nadie cargue la recoleccion.
                if lote["pausa"] and d > HOY - dt.timedelta(days=lote["pausa"]):
                    continue
                postura = self.postura_del_dia(lote, d)
                total = int(round(self.vivas(lote, d) * postura))
                cant = {}
                restante = total
                for clave in activos[:-1]:
                    n = int(round(total * max(0.0, self.proporciones[clave] + r.gauss(0, 0.012))))
                    cant[clave] = max(n, 0)
                    restante -= cant[clave]
                cant[activos[-1]] = max(restante, 0)
                self.recolecciones.append(dict(
                    galpon=galpon, lote=lote["clave"], fecha=d, hora=(11, r.randint(0, 40)),
                    estado=Recoleccion.ESTADO_PENDIENTE if d == HOY else Recoleccion.ESTADO_FINALIZADA,
                    cantidades=cant,
                    obs="" if r.random() > 0.06 else r.choice([
                        "Recolección parcial por lluvia.",
                        "Se recolectó más tarde por corte de luz.",
                    ]),
                ))
            d += dt.timedelta(days=1)

        # A esta hora del dia ya se cargaron casi todas las recolecciones: solo
        # la del ultimo galpon queda pendiente de finalizar. Si quedaran todas
        # pendientes, el panel mostraria el dia en cero.
        de_hoy = [rec for rec in self.recolecciones if rec["fecha"] == HOY]
        for rec in de_hoy[:-1]:
            rec["estado"] = Recoleccion.ESTADO_FINALIZADA

    # -- 3. entradas de materias primas a galpones ---------------------------

    def generar_entradas(self):
        r = self.rnd
        unidades = {m[0]: m[3] for m in MATERIAS_PRIMAS}
        d = self.inicio
        while d <= HOY:
            for idx, galpon in enumerate(self.galpones_activos):
                lote = self.lote_en(galpon, d)
                if not lote:
                    continue
                fase = self.fase(lote, d)
                aves = self.vivas(lote, d)
                edad = (d - lote["ingreso"]).days
                lineas = {}
                dias_desde_inicio = (d - self.inicio).days
                if dias_desde_inicio % 2 == idx % 2:
                    if fase == "P":
                        lineas["BAL"] = aves * 0.23
                        lineas["MAI"] = aves * 0.06
                        lineas["SOJ"] = aves * 0.02
                        lineas["CON"] = aves * 0.012
                        lineas["AFR"] = aves * 0.01
                    elif edad < 14:
                        lineas["INI"] = aves * 0.09
                    else:
                        lineas["REC"] = aves * 0.16
                        lineas["MAI"] = aves * 0.03
                if d.weekday() == 0:
                    lineas["DES"] = 2.0
                    lineas["DET"] = 5.0
                if d == lote["ingreso"]:
                    lineas["CAS"] = r.choice([180, 200, 240])
                    lineas["VIR"] = r.choice([100, 120])
                    lineas["DES"] = lineas.get("DES", 0) + 3.0
                if edad in (10, 30):
                    lineas["VAC"] = aves
                if edad in (18, 45):
                    lineas["VBR"] = aves
                if edad in (60, 180, 300):
                    lineas["ANT"] = aves
                if dias_desde_inicio % 30 == (idx * 3) % 30:
                    lineas["CAL"] = 25.0
                    lineas["VIT"] = 3.0 if fase == "P" else 1.5
                    lineas["FOS"] = 25.0
                    lineas["SAL"] = 25.0
                if fase == "T" and edad % 7 == 3:
                    lineas["GAS"] = 1
                if not lineas:
                    continue
                estado = Entrada.ESTADO_PENDIENTE if d == HOY else Entrada.ESTADO_FINALIZADA
                lineas_ok = {}
                for mp, q in lineas.items():
                    if unidades[mp] in ("unid.", "dosis"):
                        q = int(round(q))
                    else:
                        q = round(q, 1) if q < 20 else round(q / 5) * 5
                    if q > 0:
                        lineas_ok[mp] = q
                self.entradas.append(dict(
                    galpon=galpon, fecha=d, hora=(7, 5 + idx * 4), estado=estado,
                    lineas=lineas_ok, obs="",
                ))
                if estado == Entrada.ESTADO_FINALIZADA:
                    for mp, q in lineas_ok.items():
                        self.demanda[mp][d] += q
            d += dt.timedelta(days=1)

    # -- 4. consumo de envases y descartes de stock de materias primas -------

    def generar_consumo_envases(self):
        """
        Los maples y cajones no entran a un galpón: se gastan al armar los
        pedidos. Se modelan como descartes de stock, que es lo que los saca del
        depósito.
        """
        r = self.rnd
        d = self.inicio + dt.timedelta(days=3)
        while d < HOY - dt.timedelta(days=1):
            maples = r.choice([300, 400, 500])
            cajones = r.choice([40, 60, 80])
            self.descartes.append(dict(
                categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=d, hora=(18, 10),
                estado=Descarte.ESTADO_FINALIZADO,
                lineas=[
                    dict(mp="MAP", cantidad=maples, motivo="Maples usados en los pedidos de la semana"),
                    dict(mp="CAJ", cantidad=cajones, motivo="Cajones usados en los pedidos de la semana"),
                ],
                obs="",
            ))
            self.demanda["MAP"][d] += maples
            self.demanda["CAJ"][d] += cajones
            d += dt.timedelta(days=7)

    def generar_descartes_stock_mp(self):
        r = self.rnd
        casos = [
            ("VIT", 2, "Vitaminas vencidas"),
            ("BAL", 60, "Bolsas de balanceado húmedas por filtración"),
            ("MAI", 80, "Maíz con hongos"),
            ("CAS", 150, "Cáscara mojada por una gotera del depósito"),
            ("DET", 5, "Bidón perdido por rotura del envase"),
            ("SOJ", 50, "Bolsas rotas durante la descarga"),
        ]
        d = self.inicio + dt.timedelta(days=20)
        for mp, cantidad, motivo in casos:
            if d >= HOY - dt.timedelta(days=1):
                break
            self.descartes.append(dict(
                categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=d, hora=(15, 10),
                estado=Descarte.ESTADO_FINALIZADO,
                lineas=[dict(mp=mp, cantidad=cantidad, motivo=motivo)], obs="",
            ))
            self.demanda[mp][d] += cantidad
            d += dt.timedelta(days=r.randint(40, 70))

    # -- 5. productos: descartes de stock y salidas, simulando el stock -----

    def simular_productos(self):
        r = self.rnd
        activos = self.productos_activos
        stock = {p[0]: p[4] for p in PRODUCTOS}
        por_dia = defaultdict(lambda: defaultdict(int))
        for rec in self.recolecciones:
            if rec["estado"] == Recoleccion.ESTADO_FINALIZADA:
                for k, c in rec["cantidades"].items():
                    por_dia[rec["fecha"]][k] += c
        # Reserva que no se vende: unos dias de produccion de cada tamaño.
        reserva = {k: max(150, int(2200 * self.proporciones[k])) for k in activos}

        d = self.inicio
        while d <= HOY:
            # Salidas: lunes, miercoles y viernes.
            if d.weekday() in (0, 2, 4) and d < HOY:
                lineas = {}
                for k in activos:
                    vender = int((stock[k] - reserva[k] - r.randint(0, 150)) // 30) * 30
                    if vender >= 300:
                        lineas[k] = vender
                if lineas:
                    for k, q in lineas.items():
                        stock[k] -= q
                    self.salidas.append(dict(
                        fecha=d, hora=(10, r.choice([0, 10, 20, 30])),
                        estado=Salida.ESTADO_FINALIZADA, lineas=lineas,
                        obs=r.choice(OBS_SALIDA),
                    ))
            if d < HOY:
                for k, c in por_dia[d].items():
                    stock[k] += c
            # Descarte de stock de huevos (rotura en el deposito), cada ~9 dias.
            if d < HOY - dt.timedelta(days=1) and (d - self.inicio).days % 9 == 5:
                k = r.choice(activos)
                cantidad = r.randint(15, 70)
                if stock[k] >= cantidad + 100:
                    stock[k] -= cantidad
                    self.descartes.append(dict(
                        categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=d, hora=(14, 0),
                        estado=Descarte.ESTADO_FINALIZADO,
                        lineas=[dict(producto=k, cantidad=cantidad,
                                     motivo="Huevos quebrados en el depósito")],
                        obs="",
                    ))
            d += dt.timedelta(days=1)

        # Pendientes recientes: no mueven el stock hasta que se finalicen.
        k = next((x for x in activos if stock[x] >= 200), None)
        if k:
            self.descartes.append(dict(
                categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=HOY, hora=(9, 30),
                estado=Descarte.ESTADO_PENDIENTE,
                lineas=[dict(producto=k, cantidad=60, motivo="Huevos con cáscara fisurada")],
                obs="",
            ))
        for hace, obs in ((0, "Pedido para mañana, a confirmar con el cliente."),
                          (1, "Falta el remito firmado.")):
            pend = {k: int((stock[k] * 0.3) // 30) * 30 for k in activos}
            pend = {k: q for k, q in pend.items() if q >= 300}
            if pend:
                self.salidas.append(dict(
                    fecha=dia(hace), hora=(9, 0), estado=Salida.ESTADO_PENDIENTE,
                    lineas=pend, obs=obs,
                ))
        self.stock_final_productos = stock

    # -- 6. compras de materias primas ---------------------------------------

    def generar_compras_mp(self):
        r = self.rnd
        corte = HOY - dt.timedelta(days=3)
        ref = defaultdict(float)
        for mp, fechas in self.demanda.items():
            ref[mp] = sum(q for f, q in fechas.items() if f > HOY - dt.timedelta(days=15)) / 14
        self.consumo_diario = ref

        def demanda(mp, d0, d1):
            total = 0.0
            f = d0
            while f < d1:
                total += self.demanda[mp].get(f, 0.0) if f <= HOY else ref[mp]
                f += dt.timedelta(days=1)
            return total

        pasos = {m[0]: m[7] for m in MATERIAS_PRIMAS}
        precios = {m[0]: m[6] for m in MATERIAS_PRIMAS}
        self.stock_inicial_mp = {}
        self.compras_mp = []
        for clave_p, _nombre, _cuit, _dir, _mail, _tel, estado, ciclo in PROVEEDORES:
            mps = [m[0] for m in MATERIAS_PRIMAS if m[5] == clave_p and m[4] == "A"]
            if not mps or ciclo == 0 or estado != "A":
                continue
            fechas = []
            f = self.inicio + dt.timedelta(days=r.randint(0, 5))
            while f <= corte:
                fechas.append(f)
                f += dt.timedelta(days=ciclo + r.choice([-2, -1, 0, 0, 1, 2]))
            for mp in mps:
                self.stock_inicial_mp[mp] = redondear_arriba(
                    demanda(mp, self.inicio, fechas[0]) * 1.1, pasos[mp]
                ) + pasos[mp]
            for i, fecha in enumerate(fechas):
                hasta = fechas[i + 1] if i + 1 < len(fechas) else HOY + dt.timedelta(days=ciclo // 2 + 1)
                lineas = {}
                for mp in mps:
                    q = redondear_arriba(demanda(mp, fecha, hasta) * 1.08, pasos[mp])
                    if q > 0:
                        lineas[mp] = (q, round(precios[mp] * (1 + 0.004 * i), 2))
                if not lineas:
                    continue
                self.compras_mp.append(dict(
                    proveedor=clave_p, fecha=fecha, estado=Compra.ESTADO_FINALIZADA,
                    tipo=r.choice([
                        Compra.TIPO_CONTADO, Compra.TIPO_CONTADO,
                        Compra.TIPO_CUENTA_CORRIENTE, Compra.TIPO_DEBITO, Compra.TIPO_CREDITO,
                    ]),
                    lineas=lineas, obs="",
                ))
        for m in MATERIAS_PRIMAS:
            self.stock_inicial_mp.setdefault(m[0], 120 if m[4] == "I" else pasos[m[0]] * 2)

        # Pedidos recientes todavia pendientes: no suman stock hasta finalizarse.
        pendientes = [
            ("P1", 1, Compra.TIPO_CUENTA_CORRIENTE, {"BAL": (5000, 575.0), "MAI": (1500, 335.0)},
             "Pendiente de control de recepción."),
            ("P3", 2, Compra.TIPO_CONTADO, {"CON": (600, 198.0), "VIT": (25, 4350.0)}, ""),
            ("P10", 2, Compra.TIPO_DEBITO, {"MAP": (3000, 188.0), "CAJ": (300, 980.0)},
             "Llega el jueves."),
            ("P4", 3, Compra.TIPO_CREDITO, {"VAC": (4000, 99.0), "DES": (4, 19200.0)}, ""),
        ]
        for proveedor, hace, tipo, lineas, obs in pendientes:
            self.compras_mp.append(dict(
                proveedor=proveedor, fecha=dia(hace), estado=Compra.ESTADO_PENDIENTE,
                tipo=tipo, lineas=lineas, obs=obs,
            ))

    # -- 7. verificacion del stock de materias primas -----------------------

    def verificar_stock_mp(self):
        eventos = defaultdict(list)
        for mp, fechas in self.demanda.items():
            for f, q in fechas.items():
                eventos[mp].append((f, 1, -q))
        for c in self.compras_mp:
            if c["estado"] == Compra.ESTADO_FINALIZADA:
                for mp, (q, _p) in c["lineas"].items():
                    eventos[mp].append((c["fecha"], 0, q))
        self.stock_final_mp = {}
        for mp, lista in eventos.items():
            saldo = self.stock_inicial_mp[mp]
            for f, _orden, delta in sorted(lista):
                saldo += delta
                if saldo < -1e-6:
                    raise RuntimeError(f"El stock simulado de {mp} queda negativo el {f}: {saldo:.1f}")
            self.stock_final_mp[mp] = saldo
        for m in MATERIAS_PRIMAS:
            self.stock_final_mp.setdefault(m[0], self.stock_inicial_mp[m[0]])

    def stock_minimos(self):
        """
        Stock minimo = alrededor de una semana de consumo. Algunas materias
        primas quedan por debajo del minimo (para ver el aviso) y el resto
        holgadas.
        """
        bajas = {"BAL", "CON", "VAC", "GAS", "MAP", "DET"}
        pasos = {m[0]: m[7] for m in MATERIAS_PRIMAS}
        minimos = {}
        for mp, final in self.stock_final_mp.items():
            base = redondear_arriba(self.consumo_diario.get(mp, 0) * 7, pasos[mp])
            if mp in bajas:
                minimo = max(base, redondear_arriba(final * 1.3, pasos[mp]))
            else:
                minimo = min(base, redondear_arriba(final * 0.6, pasos[mp]))
            minimos[mp] = max(minimo, pasos[mp])
        return minimos

    def construir(self):
        self.generar_descartes_galpon()
        self.generar_recolecciones()
        self.generar_entradas()
        self.generar_consumo_envases()
        self.generar_descartes_stock_mp()
        self.simular_productos()
        self.generar_compras_mp()
        self.verificar_stock_mp()


# ---------------------------------------------------------------------------
# Escritura en la base
# ---------------------------------------------------------------------------

def crear_usuarios():
    usuarios = {}
    creados = 0
    for usuario, nombre, apellido, dni, rol, estado in USUARIOS:
        existente = Usuario.objects.filter(usuario=usuario).first()
        if existente:
            usuarios[usuario] = existente
            continue
        u = Usuario.objects.create_user(
            usuario=usuario, email=f"{usuario}@avigest.test", password=PASSWORD,
            nombre=nombre, apellido=apellido, dni=dni, rol=rol,
        )
        if estado != "A":
            u.estado = estado
            u.save(update_fields=["estado"])
        usuarios[usuario] = u
        creados += 1
    return usuarios, creados


def escribir(plan):
    usuarios, usuarios_creados = crear_usuarios()
    admin = usuarios["admin.demo"]
    operario_de = {}

    galpones = {}
    for clave, nombre, lat, lon, sup, cap, estado, desc, operarios in GALPONES:
        galpones[clave] = Galpon.objects.create(
            galpon=nombre, latitud=lat, longitud=lon, superficie=sup, capacidad=cap,
            estado=estado, descripcion=desc,
        )
        for u in operarios:
            UsuarioDelGalpon.objects.create(id_usuario=usuarios[u], id_galpon=galpones[clave])
        operario_de[clave] = usuarios[operarios[0]] if operarios else admin

    productos = {}
    for clave, nombre, desc, estado, stock, _prop in PRODUCTOS:
        productos[clave] = Producto.objects.create(
            producto=nombre, descripcion=desc, estado=estado, stock_inicial=stock
        )

    minimos = plan.stock_minimos()
    mps = {}
    for clave, nombre, desc, unidad, estado, _prov, _precio, _paso in MATERIAS_PRIMAS:
        mps[clave] = MateriaPrima.objects.create(
            materia_prima=nombre, descripcion=desc, unidad=unidad, estado=estado,
            stock_minimo=dec(minimos[clave]), stock_inicial=dec(plan.stock_inicial_mp[clave]),
        )

    proveedores = {}
    for clave, nombre, base, direccion, email, telefono, estado, _ciclo in PROVEEDORES:
        proveedores[clave] = Proveedor.objects.create(
            nombre=nombre, cuit=cuit_completo(base), direccion=direccion, email=email,
            telefono=telefono, estado=estado,
        )

    # ---- Lotes (cada uno sale de una compra de lotes finalizada) ----------
    lotes = {}
    r = plan.rnd
    for l in plan.lotes:
        compra = Compra.objects.create(
            id_proveedor=proveedores[l["proveedor"]], id_usuario=admin,
            categoria=Compra.CATEGORIA_LOTES, tipo=Compra.TIPO_CUENTA_CORRIENTE,
            fecha=l["ingreso"] - dt.timedelta(days=7),
            estado=Compra.ESTADO_FINALIZADA, observaciones="Pollitas de recría.",
        )
        muertas = sum(c for _f, c in l["muertes"])
        if l["vaciado"] is not None:
            estado = Lote.ESTADO_FINALIZADO
        elif (HOY - l["ingreso"]).days >= DIAS_TRANSICION:
            estado = Lote.ESTADO_PRODUCCION
        else:
            estado = Lote.ESTADO_TRANSICION
        plan_fin = l["ingreso"] + dt.timedelta(days=DIAS_TRANSICION)
        lote = Lote.objects.create(
            id_galpon=galpones[l["galpon"]], fecha_ingreso=l["ingreso"],
            fecha_inicio_produccion=None if estado == Lote.ESTADO_TRANSICION else plan_fin,
            fecha_vaciado=l["vaciado"], cantidad_inicial=l["aves"],
            cantidad_actual=max(l["aves"] - muertas, 0), estado=estado, observaciones=l["obs"],
        )
        escala = 0.9 + r.random() * 0.2
        PlanTransicion.objects.create(
            id_lote=lote,
            estado=PlanTransicion.ESTADO_FINALIZADO if plan_fin <= HOY else PlanTransicion.ESTADO_EN_CURSO,
            fecha_inicio=l["ingreso"], fecha_fin=plan_fin,
            **{
                f"{campo}_semana{i + 1}": dec(PLAN[clave][i] * (1 if clave == "luz" else escala))
                for clave, campo in (("agua", "agua"), ("alimento", "alimento"), ("luz", "horas_luz"))
                for i in range(4)
            },
        )
        LineaCompra.objects.create(
            id_compra=compra, id_lote=lote, cantidad=dec(l["aves"]), precio_unitario=dec(l["precio"]),
        )
        lotes[l["clave"]] = lote

    # Lotes comprados que todavia no se asignaron a un galpon.
    for aves, prov, precio, hace, estado in LOTES_COMPRADOS:
        compra = Compra.objects.create(
            id_proveedor=proveedores[prov], id_usuario=admin, categoria=Compra.CATEGORIA_LOTES,
            tipo=Compra.TIPO_CONTADO, fecha=dia(hace), estado=estado,
            observaciones=("Pollitas listas para el próximo ciclo."
                           if estado == Compra.ESTADO_FINALIZADA else "A confirmar fecha de entrega."),
        )
        LineaCompra.objects.create(id_compra=compra, cantidad=dec(aves), precio_unitario=dec(precio))

    # ---- Compras de materias primas --------------------------------------
    lineas_compra = []
    for c in plan.compras_mp:
        compra = Compra.objects.create(
            id_proveedor=proveedores[c["proveedor"]], id_usuario=admin,
            categoria=Compra.CATEGORIA_MATERIAS_PRIMAS, tipo=c["tipo"],
            fecha=c["fecha"], estado=c["estado"], observaciones=c["obs"],
        )
        for mp, (cantidad, precio) in c["lineas"].items():
            lineas_compra.append(LineaCompra(
                id_compra=compra, id_materia_prima=mps[mp],
                cantidad=dec(cantidad), precio_unitario=dec(precio),
            ))
    LineaCompra.objects.bulk_create(lineas_compra, batch_size=500)

    # ---- Recolecciones ----------------------------------------------------
    lineas_rec = []
    for rec in plan.recolecciones:
        cab = Recoleccion.objects.create(
            id_galpon=galpones[rec["galpon"]], id_lote=lotes[rec["lote"]],
            id_usuario=operario_de[rec["galpon"]], fecha=momento(rec["fecha"], *rec["hora"]),
            estado=rec["estado"], observaciones=rec["obs"],
        )
        lineas_rec.extend(
            LineaRecoleccion(
                id_recoleccion=cab, id_galpon=galpones[rec["galpon"]],
                id_producto=productos[k], cantidad=c,
            )
            for k, c in rec["cantidades"].items() if c > 0
        )
    LineaRecoleccion.objects.bulk_create(lineas_rec, batch_size=1000)

    # ---- Entradas ---------------------------------------------------------
    lineas_ent = []
    for e in plan.entradas:
        cab = Entrada.objects.create(
            id_galpon=galpones[e["galpon"]], id_usuario=operario_de[e["galpon"]],
            fecha=momento(e["fecha"], *e["hora"]), estado=e["estado"], observaciones=e["obs"],
        )
        lineas_ent.extend(
            LineaEntrada(id_entrada=cab, id_materia_prima=mps[mp], cantidad=dec(q))
            for mp, q in e["lineas"].items()
        )
    LineaEntrada.objects.bulk_create(lineas_ent, batch_size=1000)

    # ---- Descartes --------------------------------------------------------
    lineas_des = []
    for de in plan.descartes:
        galpon = galpones[de["galpon"]] if de["galpon"] else None
        usuario = operario_de[de["galpon"]] if de["galpon"] else usuarios["operario1"]
        cab = Descarte.objects.create(
            categoria=de["categoria"], id_galpon=galpon, id_usuario=usuario,
            fecha=momento(de["fecha"], *de["hora"]), estado=de["estado"], observaciones=de["obs"],
        )
        lineas_des.extend(
            LineaDescarte(
                id_descarte=cab, id_galpon=galpon, cantidad=dec(l["cantidad"]), motivo=l["motivo"],
                id_lote=lotes[l["lote"]] if "lote" in l else None,
                id_producto=productos[l["producto"]] if "producto" in l else None,
                id_materia_prima=mps[l["mp"]] if "mp" in l else None,
            )
            for l in de["lineas"]
        )
    LineaDescarte.objects.bulk_create(lineas_des, batch_size=1000)

    # ---- Salidas ----------------------------------------------------------
    quien = [admin, usuarios["operario1"], usuarios["operario2"], usuarios["operario6"]]
    lineas_sal = []
    for i, s in enumerate(plan.salidas):
        cab = Salida.objects.create(
            id_usuario=quien[i % len(quien)], fecha=momento(s["fecha"], *s["hora"]),
            estado=s["estado"], observaciones=s["obs"],
        )
        lineas_sal.extend(
            LineaSalida(id_salida=cab, id_producto=productos[k], cantidad=q)
            for k, q in s["lineas"].items()
        )
    LineaSalida.objects.bulk_create(lineas_sal, batch_size=1000)

    return usuarios_creados, lotes


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

def preparar_alertas(lotes):
    """
    Deja la tabla de alertas como si el sistema hubiera estado corriendo.

    Las pendientes las genera el propio sistema con sus reglas (nada se
    inventa). A eso se le suman algunas ya resueltas, con fecha, para que el
    panel muestre también el historial reciente.
    """
    generar_alertas()
    tipos = {t.clave: t for t in TipoAlerta.objects.all()}
    resueltas = [
        ("postura_baja", "L10", 21, 15, "{lote} · {galpon} — 66,4% de postura el {fecha} "
                                        "(el mínimo esperado es 70%)."),
        ("mortandad_alta", "L13", 48, 41, "{lote} · {galpon} — 52 gallinas descartadas en la última "
                                          "semana (1,2% del plantel inicial; el máximo esperado es 1,0%)."),
        ("sin_recoleccion", "L11", 12, 9, "{lote} · {galpon} — sin recolecciones finalizadas "
                                          "desde el {fecha}."),
        ("postura_baja", "L08", 70, 58, "{lote} · {galpon} — 68,9% de postura el {fecha} "
                                        "(el mínimo esperado es 70%)."),
    ]
    creadas = 0
    for clave, lote_clave, generada, resuelta, texto in resueltas:
        tipo = tipos.get(clave)
        lote = lotes.get(lote_clave)
        if tipo is None or lote is None:
            continue
        descripcion = texto.format(
            lote=f"Lote {lote.codigo}", galpon=lote.id_galpon.galpon,
            fecha=dia(generada).strftime("%d/%m"),
        )
        Alerta.objects.create(
            id_lote=lote, id_tipo_alerta=tipo, descripcion=descripcion[:255],
            estado=Alerta.ESTADO_RESUELTA,
            fecha_generacion=momento(dia(generada), 8, 0),
            fecha_resolucion=momento(dia(resuelta), 8, 0),
        )
        creadas += 1
    return creadas


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

def resumen(usuarios_creados, alertas_resueltas):
    print()
    print("Datos cargados:")
    filas = [
        ("Galpones", Galpon), ("Lotes", Lote), ("Productos", Producto),
        ("Materias primas", MateriaPrima), ("Proveedores", Proveedor),
        ("Compras", Compra), ("Recolecciones", Recoleccion), ("Entradas", Entrada),
        ("Descartes", Descarte), ("Salidas", Salida), ("Alertas", Alerta),
    ]
    for nombre, modelo in filas:
        print(f"  {nombre:<16} {modelo.objects.count():>6}")
    lineas = (
        LineaCompra.objects.count() + LineaRecoleccion.objects.count()
        + LineaEntrada.objects.count() + LineaDescarte.objects.count()
        + LineaSalida.objects.count()
    )
    print(f"  {'Líneas de detalle':<16} {lineas:>6}")
    print()
    por_estado = {e: Lote.objects.filter(estado=e).count() for e, _ in Lote.ESTADO_CHOICES}
    print("  Lotes por etapa:  " + "   ".join(
        f"{dict(Lote.ESTADO_CHOICES)[e]}: {n}" for e, n in por_estado.items()
    ))
    pendientes = LineaCompra.objects.filter(
        id_compra__categoria=Compra.CATEGORIA_LOTES,
        id_compra__estado=Compra.ESTADO_FINALIZADA, id_lote__isnull=True,
    ).count()
    print(f"  Lotes comprados sin asignar a un galpon: {pendientes}")
    activas = Alerta.objects.filter(estado=Alerta.ESTADO_PENDIENTE)
    print(f"  Alertas activas: {activas.count()} (y {alertas_resueltas} resueltas de ejemplo)")
    for a in activas.select_related("id_tipo_alerta", "id_lote"):
        print(f"    - {a.id_tipo_alerta.nombre}: {a.descripcion}")
    bajo_minimo = sum(
        1 for mp in MateriaPrima.objects.all()
        if mp.estado == "A" and _stock_mp(mp) < mp.stock_minimo
    )
    print(f"  Materias primas por debajo del stock minimo: {bajo_minimo}")
    print()
    print(f"Usuarios de prueba (clave: {PASSWORD}):")
    for usuario, nombre, apellido, _dni, rol, estado in USUARIOS:
        marca = "" if estado == "A" else "  (dado de baja)"
        print(f"  {usuario:<16} {dict(Usuario.ROL_CHOICES)[rol]:<14} {nombre} {apellido}{marca}")
    if not usuarios_creados:
        print("  (ya existian; no se modificaron)")


def _stock_mp(mp):
    """Stock actual de una materia prima, con la misma formula que la API."""
    from descartes.stock import stock_actual_materia_prima

    return stock_actual_materia_prima(mp)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="Carga un juego de datos grande y variado en la base de AviGest."
    )
    ap.add_argument("--limpiar", action="store_true",
                    help="borra antes los datos de negocio (los usuarios no se tocan)")
    ap.add_argument("--si", action="store_true", help="no pedir confirmacion")
    ap.add_argument("--dias", type=int, default=365,
                    help="dias de historial (60 a 500, por defecto 365)")
    ap.add_argument("--semilla", type=int, default=2026, help="semilla de los numeros al azar")
    args = ap.parse_args()

    if not 60 <= args.dias <= 500:
        ap.error("--dias tiene que estar entre 60 y 500")

    if hay_datos() and not args.limpiar:
        print("La base ya tiene datos. Para borrarlos y volver a cargar usa:"
              "  py poblar_datos_v2.py --limpiar")
        sys.exit(1)
    if args.limpiar and hay_datos() and not args.si:
        resp = input(
            "Se van a BORRAR galpones, lotes, productos, materias primas, proveedores, compras,\n"
            "recolecciones, entradas, descartes, salidas y alertas. Los usuarios no se tocan.\n"
            "Escribi 'si' para continuar: "
        )
        if resp.strip().lower() not in ("si", "sí", "s"):
            print("Cancelado.")
            sys.exit(0)

    print("Simulando la granja dia por dia...")
    plan = Plan(args.dias, args.semilla)
    plan.construir()
    print(f"Escribiendo {len(plan.recolecciones)} recolecciones, {len(plan.entradas)} entradas, "
          f"{len(plan.descartes)} descartes, {len(plan.salidas)} salidas y "
          f"{len(plan.compras_mp)} compras...")
    with transaction.atomic():
        if args.limpiar:
            limpiar()
        usuarios_creados, lotes = escribir(plan)
        alertas_resueltas = preparar_alertas(lotes)
    resumen(usuarios_creados, alertas_resueltas)


if __name__ == "__main__":
    main()
