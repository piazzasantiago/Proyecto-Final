"""
Carga datos de ejemplo en la base de AviGest para probar y mostrar el sistema.

Uso (desde la carpeta backend, con el entorno virtual activo):

    py poblar_datos.py                 # carga los datos (si la base esta vacia)
    py poblar_datos.py --limpiar       # borra los datos de negocio y los vuelve a cargar
    py poblar_datos.py --limpiar --si  # igual, sin pedir confirmacion
    py poblar_datos.py --dias 120      # historial mas largo (por defecto 90 dias)
    py poblar_datos.py --semilla 7     # otra variante de los mismos datos

Que genera (todo relativo a la fecha de hoy, asi que siempre queda "reciente"):

  * Usuarios de prueba: 1 administrador, 1 de consulta y 3 operarios.
  * 6 galpones (uno inactivo) y la asignacion de operarios.
  * 3 productos (huevos Nº1, Nº2 y Nº3) y 12 materias primas.
  * 7 proveedores (uno inactivo).
  * 5 lotes de gallinas en distintas etapas (finalizado, produccion y
    transicion), cada uno con su compra y su plan de transicion, mas UNA compra
    de lotes finalizada sin asignar (aparece el cartel rojo en Lotes).
  * Recoleccion diaria de los galpones en produccion.
  * Compras de materias primas periodicas, entradas a galpones, descartes
    (de galpon y de stock) y salidas de huevos.
  * Algunos registros PENDIENTES recientes y varias materias primas por debajo
    del stock minimo, para probar los estados y las alertas.

Las cantidades se calculan simulando el stock dia por dia, asi que el stock de
productos y de materias primas nunca queda negativo y las reglas del sistema
se respetan (un solo lote activo por galpon, lotes que salen de una compra
finalizada, etc.).

Los datos se escriben directamente en la base (no por la API), dentro de una
transaccion: si algo falla, no queda nada a medias.
"""

import argparse
import datetime as dt
import math
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
    ejemplo, un registro de hoy a una hora que todavia no llego) se lo
    adelanta a un rato antes de ahora.
    """
    naive = dt.datetime.combine(fecha, dt.time(hora, minuto))
    valor = timezone.make_aware(naive)
    limite = AHORA - dt.timedelta(minutes=20)
    return min(valor, limite)


def dec(valor, lugares=2):
    return Decimal(str(round(valor, lugares))).quantize(Decimal(10) ** -lugares)


def redondear_arriba(valor, paso):
    return int(math.ceil(valor / paso - 1e-9)) * paso


# ---------------------------------------------------------------------------
# Datos base
# ---------------------------------------------------------------------------

USUARIOS = [
    # usuario, nombre, apellido, dni, rol
    ("admin.demo", "Mariana", "Rojas", "90000001", Usuario.ROL_ADMINISTRADOR),
    ("consulta.demo", "Lucía", "Benítez", "90000002", Usuario.ROL_CONSULTA),
    ("operario1", "Juan", "Pérez", "90000003", Usuario.ROL_OPERARIO),
    ("operario2", "Marta", "Gómez", "90000004", Usuario.ROL_OPERARIO),
    ("operario3", "Diego", "Ledesma", "90000005", Usuario.ROL_OPERARIO),
]

GALPONES = [
    # clave, nombre, latitud, longitud, superficie, capacidad, estado, descripcion, operarios
    ("G1", "Galpón 1", "-26.808120", "-65.217340", "620.000000", 4000, "A",
     "Galpón de postura con comederos automáticos.", ["operario1"]),
    ("G2", "Galpón 2", "-26.808410", "-65.216910", "780.000000", 5000, "A",
     "Galpón de postura, el más grande de la granja.", ["operario1", "operario2"]),
    ("G3", "Galpón 3", "-26.808730", "-65.216480", "700.000000", 4500, "A",
     "Galpón de postura con ventilación cruzada.", ["operario2"]),
    ("G4", "Galpón 4", "-26.809010", "-65.216050", "450.000000", 3000, "A",
     "Galpón de recría y transición, con calefacción a gas.", ["operario3"]),
    ("G5", "Galpón 5", "-26.809290", "-65.215630", "600.000000", 4000, "A",
     "Galpón vacío, desinfectado y listo para recibir un lote.", ["operario3"]),
    ("G6", "Galpón 6", "-26.809580", "-65.215200", "380.000000", 2500, "I",
     "Galpón antiguo fuera de servicio por refacciones.", []),
]

PRODUCTOS = [
    # clave, nombre, descripcion, estado, stock_inicial, proporcion
    ("N1", "Huevo Nº1", "Huevo grande, 60 g o más.", "A", 300, 0.52),
    ("N2", "Huevo Nº2", "Huevo mediano, entre 50 y 60 g.", "A", 200, 0.33),
    ("N3", "Huevo Nº3", "Huevo chico, menos de 50 g.", "A", 150, 0.15),
    ("N4", "Huevo de campo (discontinuado)", "Línea que ya no se comercializa.", "I", 0, 0.0),
]

# clave, nombre, descripcion, unidad, estado, proveedor, precio, paso de compra
MATERIAS_PRIMAS = [
    ("BAL", "Balanceado postura", "Alimento balanceado para gallinas en producción.", "kg", "A", "P1", 540, 50),
    ("REC", "Balanceado recría", "Alimento para pollitas en transición.", "kg", "A", "P1", 590, 50),
    ("MAI", "Maíz molido", "Maíz molido para complementar la ración.", "kg", "A", "P1", 320, 50),
    ("SOJ", "Soja peleteada", "Fuente de proteína de la ración.", "kg", "A", "P1", 690, 25),
    ("CON", "Calcio (conchilla)", "Aporte de calcio para la calidad de la cáscara.", "kg", "A", "P3", 190, 25),
    ("CAL", "Cal viva", "Para desinfección de pisos y fosas.", "kg", "A", "P3", 160, 25),
    ("CAS", "Cáscara de arroz", "Cama para los galpones.", "kg", "A", "P3", 85, 100),
    ("VIT", "Vitaminas y minerales", "Premezcla vitamínica para el alimento.", "kg", "A", "P3", 4200, 1),
    ("DES", "Desinfectante (Virkon)", "Desinfectante de uso general.", "kg", "A", "P4", 18500, 1),
    ("VAC", "Vacuna Newcastle", "Vacuna contra la enfermedad de Newcastle.", "dosis", "A", "P4", 95, 500),
    ("GAS", "Gas envasado (10 kg)", "Garrafas para la calefacción de la recría.", "unid.", "A", "P5", 28000, 1),
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
]

# clave, galpon, ingreso (dias atras), vaciado (dias atras o None), aves, proveedor, precio por ave,
# postura base, observaciones
LOTES = [
    ("L1", "G1", 400, 70, 3000, "P2", 8200, 0.86, "Lote del ciclo anterior. Vaciado sanitario completado."),
    ("L2", "G1", 62, None, 2800, "P2", 9400, 0.93, "Pollitas de recría propia. Empezaron a poner hace poco."),
    ("L3", "G2", 260, None, 3500, "P6", 8900, 0.90, "Lote en plena producción."),
    ("L4", "G3", 130, None, 3200, "P6", 9100, 0.94, "Lote de alta postura."),
    ("L5", "G4", 18, None, 2600, "P2", 9600, 0.0, "En plan de transición."),
]
# Lote comprado y todavia sin asignar a un galpon: (aves, proveedor, precio, dias atras)
LOTE_PENDIENTE = (3000, "P2", 9800, 3)
LOTE_PENDIENTE_SIN_FINALIZAR = (2000, "P6", 9700, 1)

# Plan de transicion de referencia (agua L, alimento kg, horas de luz por semana)
PLAN = {
    "agua": [4.20, 4.80, 5.50, 6.10],
    "alimento": [18.00, 21.50, 25.00, 28.50],
    "luz": [10.00, 12.00, 14.00, 16.00],
}


def cuit_completo(base10):
    """Agrega el digito verificador al CUIT (misma regla que usa el sistema)."""
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(d) * p for d, p in zip(base10, pesos))
    v = 11 - suma % 11
    v = 0 if v == 11 else 9 if v == 10 else v
    return f"{base10}{v}"


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

def limpiar():
    """Borra los datos de negocio. Los usuarios no se tocan."""
    for modelo in (
        Descarte, Entrada, Salida, Recoleccion, Compra, Lote,
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
        self.inicio = dia(dias)  # primer dia del historial

        # lotes: lista de dicts con fechas reales
        self.lotes = []
        for clave, galpon, ing, vac, aves, prov, precio, postura, obs in LOTES:
            self.lotes.append(dict(
                clave=clave, galpon=galpon, ingreso=dia(ing),
                vaciado=dia(vac) if vac is not None else None,
                aves=aves, proveedor=prov, precio=precio, postura=postura, obs=obs,
                muertes=[],  # (fecha, cantidad) de descartes finalizados
            ))
        self.descartes = []       # dicts: categoria, galpon, fecha(date), hora, estado, lineas
        self.recolecciones = []   # dicts
        self.entradas = []
        self.salidas = []
        self.compras_mp = []
        self.demanda = defaultdict(lambda: defaultdict(float))  # mp -> fecha -> cantidad (finalizados)

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
        return lote["aves"] - muertas

    # -- 1. descartes de galpon (muertes de gallinas, huevos rotos) ---------
    def generar_descartes_galpon(self):
        r = self.rnd
        motivos_muerte = [
            "Muerte natural", "Enfermedad respiratoria", "Golpe de calor",
            "Aplastamiento en el nidal", "Prolapso", "Muerte súbita",
        ]
        for lote in self.lotes:
            d = max(self.inicio, lote["ingreso"]) + dt.timedelta(days=r.randint(0, 2))
            fin = HOY if lote["vaciado"] is None else lote["vaciado"] - dt.timedelta(days=1)
            while d <= fin:
                fase = self.fase(lote, d)
                if fase:
                    if fase == "T":
                        cantidad = r.randint(3, 8)
                    elif lote["clave"] == "L1":
                        cantidad = r.randint(3, 6)
                    else:
                        cantidad = r.randint(1, 4)
                    estado = Descarte.ESTADO_PENDIENTE if d >= HOY - dt.timedelta(days=1) else Descarte.ESTADO_FINALIZADO
                    lineas = [dict(lote=lote["clave"], cantidad=cantidad, motivo=r.choice(motivos_muerte))]
                    if fase == "P" and r.random() < 0.35:
                        lineas.append(dict(
                            producto=r.choice(["N2", "N3"]), cantidad=r.randint(20, 90),
                            motivo="Huevos rotos encontrados en el nidal",
                        ))
                    if r.random() < 0.05:
                        lineas.append(dict(
                            mp="CAS", cantidad=r.choice([30, 40, 60]),
                            motivo="Cama húmeda que hubo que retirar",
                        ))
                    self.descartes.append(dict(
                        categoria=Descarte.CATEGORIA_GALPON, galpon=lote["galpon"], fecha=d,
                        hora=(16, r.randint(0, 40)), estado=estado, lineas=lineas,
                        obs="", usuario=None,
                    ))
                    if estado == Descarte.ESTADO_FINALIZADO:
                        lote["muertes"].append((d, cantidad))
                d += dt.timedelta(days=r.randint(3, 6))

    # -- 2. recolecciones -----------------------------------------------------
    def generar_recolecciones(self):
        r = self.rnd
        prods = [(k, p) for k, _n, _d, estado, _s, p in PRODUCTOS if estado == "A"]
        d = self.inicio
        while d <= HOY:
            for galpon in ("G1", "G2", "G3", "G4", "G5"):
                lote = self.lote_en(galpon, d)
                if not lote or self.fase(lote, d) != "P":
                    continue
                dias_prod = (d - lote["ingreso"]).days - DIAS_TRANSICION
                rampa = min(1.0, 0.70 + 0.30 * (dias_prod / 21))
                postura = lote["postura"] * rampa + r.gauss(0, 0.018)
                postura = max(0.55, min(0.97, postura))
                total = int(round(self.vivas(lote, d) * postura))
                cant = {}
                restante = total
                for k, prop in prods[:-1]:
                    n = int(round(total * (prop + r.gauss(0, 0.015))))
                    cant[k] = max(n, 0)
                    restante -= cant[k]
                cant[prods[-1][0]] = max(restante, 0)
                self.recolecciones.append(dict(
                    galpon=galpon, lote=lote["clave"], fecha=d, hora=(11, r.randint(0, 40)),
                    estado=Recoleccion.ESTADO_PENDIENTE if d == HOY else Recoleccion.ESTADO_FINALIZADA,
                    cantidades=cant,
                    obs="" if r.random() > 0.06 else "Recolección parcial por lluvia.",
                ))
            d += dt.timedelta(days=1)

    # -- 3. entradas de materias primas a galpones ---------------------------
    def generar_entradas(self):
        r = self.rnd
        galpones_con_lote = ["G1", "G2", "G3", "G4", "G5"]
        d = self.inicio
        while d <= HOY:
            for idx, galpon in enumerate(galpones_con_lote):
                lote = self.lote_en(galpon, d)
                if not lote:
                    continue
                fase = self.fase(lote, d)
                aves = self.vivas(lote, d)
                lineas = {}
                dias_desde_inicio = (d - self.inicio).days
                if dias_desde_inicio % 2 == idx % 2:
                    if fase == "P":
                        lineas["BAL"] = aves * 0.23
                        lineas["MAI"] = aves * 0.06
                        lineas["SOJ"] = aves * 0.02
                        lineas["CON"] = aves * 0.012
                    else:
                        lineas["REC"] = aves * 0.16
                        lineas["MAI"] = aves * 0.03
                if d.weekday() == 0:
                    lineas["DES"] = 2.0
                if d == lote["ingreso"]:
                    lineas["CAS"] = r.choice([180, 200, 240])
                    lineas["DES"] = lineas.get("DES", 0) + 3.0
                edad = (d - lote["ingreso"]).days
                if edad in (10, 30):
                    lineas["VAC"] = aves
                if dias_desde_inicio % 30 == (idx * 6) % 30:
                    lineas["CAL"] = 25.0
                    lineas["VIT"] = 3.0 if fase == "P" else 1.5
                if galpon == "G4" and fase == "T" and edad % 7 == 3:
                    lineas["GAS"] = 1
                if not lineas:
                    continue
                estado = Entrada.ESTADO_PENDIENTE if d == HOY else Entrada.ESTADO_FINALIZADA
                lineas_ok = {}
                for mp, q in lineas.items():
                    unidad = next(m[3] for m in MATERIAS_PRIMAS if m[0] == mp)
                    if unidad in ("unid.", "dosis"):
                        q = int(round(q))
                    else:
                        q = round(q, 1) if q < 20 else round(q / 5) * 5
                    if q > 0:
                        lineas_ok[mp] = q
                self.entradas.append(dict(
                    galpon=galpon, fecha=d, hora=(7, 15 + idx * 5), estado=estado,
                    lineas=lineas_ok, obs="",
                ))
                if estado == Entrada.ESTADO_FINALIZADA:
                    for mp, q in lineas_ok.items():
                        self.demanda[mp][d] += q
            d += dt.timedelta(days=1)

    # -- 4. descartes de stock de materias primas ---------------------------
    def generar_descartes_stock_mp(self):
        casos = [
            (self.inicio + dt.timedelta(days=22), "VIT", 2, "Vitaminas vencidas"),
            (self.inicio + dt.timedelta(days=47), "BAL", 60, "Bolsas de balanceado húmedas por filtración"),
            (self.inicio + dt.timedelta(days=71), "MAI", 80, "Maíz con hongos"),
        ]
        for fecha, mp, cantidad, motivo in casos:
            if fecha >= HOY - dt.timedelta(days=1):
                continue
            self.descartes.append(dict(
                categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=fecha, hora=(15, 10),
                estado=Descarte.ESTADO_FINALIZADO,
                lineas=[dict(mp=mp, cantidad=cantidad, motivo=motivo)], obs="", usuario=None,
            ))
            self.demanda[mp][fecha] += cantidad

    # -- 5. productos: descartes de stock y salidas, simulando el stock -----
    def simular_productos(self):
        r = self.rnd
        stock = {k: s for k, _n, _d, estado, s, _p in PRODUCTOS}
        por_dia = defaultdict(lambda: defaultdict(int))
        for rec in self.recolecciones:
            if rec["estado"] == Recoleccion.ESTADO_FINALIZADA:
                for k, c in rec["cantidades"].items():
                    por_dia[rec["fecha"]][k] += c
        reserva = {"N1": 400, "N2": 300, "N3": 200}
        d = self.inicio
        n = 0
        while d <= HOY:
            # 10:00 salida (martes y viernes), vende lo acumulado menos una reserva
            if d.weekday() in (1, 4) and d < HOY:
                lineas = {}
                for k in ("N1", "N2", "N3"):
                    vender = int((stock[k] - reserva[k] - r.randint(0, 150)) // 30) * 30
                    if vender >= 600:
                        lineas[k] = vender
                if lineas:
                    for k, q in lineas.items():
                        stock[k] -= q
                    self.salidas.append(dict(
                        fecha=d, hora=(10, r.choice([0, 10, 20, 30])),
                        estado=Salida.ESTADO_FINALIZADA, lineas=lineas,
                        obs=r.choice(["", "", "Retiró el camión de reparto.", "Entrega a mayorista."]),
                    ))
            # 11:00 recoleccion
            if d < HOY:
                for k, c in por_dia[d].items():
                    stock[k] += c
            # 14:00 descarte de stock de huevos (rotura), cada ~11 dias
            if d < HOY - dt.timedelta(days=1) and (d - self.inicio).days % 11 == 5:
                k = r.choice(["N1", "N2", "N3"])
                cantidad = r.randint(15, 60)
                if stock[k] >= cantidad + 100:
                    stock[k] -= cantidad
                    self.descartes.append(dict(
                        categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=d, hora=(14, 0),
                        estado=Descarte.ESTADO_FINALIZADO,
                        lineas=[dict(producto=k, cantidad=cantidad, motivo="Huevos quebrados en el depósito")],
                        obs="", usuario=None,
                    ))
            d += dt.timedelta(days=1)
            n += 1
        # Un descarte de stock pendiente y una salida pendiente, recientes y con stock suficiente.
        k = "N3" if stock["N3"] >= 160 else None
        if k:
            self.descartes.append(dict(
                categoria=Descarte.CATEGORIA_STOCK, galpon=None, fecha=HOY, hora=(9, 30),
                estado=Descarte.ESTADO_PENDIENTE,
                lineas=[dict(producto=k, cantidad=60, motivo="Huevos con cáscara fisurada")],
                obs="", usuario=None,
            ))
        pend = {k: int((stock[k] * 0.4) // 30) * 30 for k in ("N1", "N2")}
        pend = {k: q for k, q in pend.items() if q >= 300}
        if pend:
            self.salidas.append(dict(
                fecha=HOY, hora=(9, 0), estado=Salida.ESTADO_PENDIENTE, lineas=pend,
                obs="Pedido para el viernes, a confirmar con el cliente.",
            ))
        self.stock_final_productos = stock

    # -- 6. compras de materias primas ---------------------------------------
    def generar_compras_mp(self):
        r = self.rnd
        corte = HOY - dt.timedelta(days=3)  # ultimo pedido finalizado
        # demanda promedio diaria de los ultimos 14 dias, para cubrir los dias que vienen
        ref = defaultdict(float)
        for mp, fechas in self.demanda.items():
            ref[mp] = sum(q for f, q in fechas.items() if f > HOY - dt.timedelta(days=15)) / 14
        self.consumo_diario = ref

        def demanda(mp, d0, d1):
            total = 0.0
            f = d0
            while f < d1:
                if f <= HOY:
                    total += self.demanda[mp].get(f, 0.0)
                else:
                    total += ref[mp]
                f += dt.timedelta(days=1)
            return total

        pasos = {m[0]: m[7] for m in MATERIAS_PRIMAS}
        precios = {m[0]: m[6] for m in MATERIAS_PRIMAS}
        self.stock_inicial_mp = {}
        self.compras_mp = []
        self.compras_mp_total = defaultdict(float)
        facturas = {}
        for clave_p, _nombre, _cuit, _dir, _mail, _tel, estado, ciclo in PROVEEDORES:
            mps = [m[0] for m in MATERIAS_PRIMAS if m[5] == clave_p and m[4] == "A"]
            if not mps or ciclo == 0 or estado != "A":
                continue
            offset = r.randint(0, 5)
            fechas = []
            f = self.inicio + dt.timedelta(days=offset)
            while f <= corte:
                fechas.append(f)
                f += dt.timedelta(days=ciclo + r.choice([-1, 0, 0, 1]))
            facturas[clave_p] = r.randint(1200, 4800)
            for mp in mps:
                primero = fechas[0]
                self.stock_inicial_mp[mp] = redondear_arriba(
                    demanda(mp, self.inicio, primero) * 1.1, pasos[mp]
                ) + pasos[mp]
            for i, fecha in enumerate(fechas):
                hasta = fechas[i + 1] if i + 1 < len(fechas) else HOY + dt.timedelta(days=ciclo // 2 + 1)
                lineas = {}
                for mp in mps:
                    q = redondear_arriba(demanda(mp, fecha, hasta) * 1.08, pasos[mp])
                    if q > 0:
                        deriva = 1 + 0.004 * i
                        lineas[mp] = (q, round(precios[mp] * deriva, 2))
                        self.compras_mp_total[mp] += q
                if not lineas:
                    continue
                facturas[clave_p] += r.randint(1, 9)
                self.compras_mp.append(dict(
                    proveedor=clave_p, fecha=fecha, estado=Compra.ESTADO_FINALIZADA,
                    tipo=Compra.TIPO_CUENTA_CORRIENTE if clave_p in ("P1", "P3") and r.random() < 0.6 else Compra.TIPO_CONTADO,
                    nro=f"{r.randint(1, 4):04d}-{facturas[clave_p]:08d}", lineas=lineas,
                    obs="",
                ))
        for mp, _n, _d, _u, estado, *_ in [(m[0], m[1], m[2], m[3], m[4]) for m in MATERIAS_PRIMAS]:
            self.stock_inicial_mp.setdefault(mp, 120 if estado == "I" else pasos[mp] * 2)
        # Pedidos recientes todavia pendientes: no suman stock hasta finalizarse.
        self.compras_mp.append(dict(
            proveedor="P1", fecha=HOY - dt.timedelta(days=1), estado=Compra.ESTADO_PENDIENTE,
            tipo=Compra.TIPO_CUENTA_CORRIENTE, nro=f"0001-{facturas['P1'] + 20:08d}",
            lineas={"BAL": (3000, 560.0), "SOJ": (500, 710.0)}, obs="Pendiente de control de recepción.",
        ))
        self.compras_mp.append(dict(
            proveedor="P3", fecha=HOY - dt.timedelta(days=2), estado=Compra.ESTADO_PENDIENTE,
            tipo=Compra.TIPO_CONTADO, nro=f"0002-{facturas['P3'] + 20:08d}",
            lineas={"CON": (400, 195.0), "VIT": (20, 4300.0)}, obs="",
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
        primas quedan por debajo del minimo (para probar las alertas) y el
        resto holgadas.
        """
        bajas = {"BAL", "CON", "VAC", "GAS"}
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
    for usuario, nombre, apellido, dni, rol in USUARIOS:
        existente = Usuario.objects.filter(usuario=usuario).first()
        if existente:
            usuarios[usuario] = existente
            continue
        usuarios[usuario] = Usuario.objects.create_user(
            usuario=usuario, email=f"{usuario}@avigest.test", password=PASSWORD,
            nombre=nombre, apellido=apellido, dni=dni, rol=rol,
        )
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
        fecha_compra = l["ingreso"] - dt.timedelta(days=7)
        compra = Compra.objects.create(
            id_proveedor=proveedores[l["proveedor"]], id_usuario=admin,
            categoria=Compra.CATEGORIA_LOTES, tipo=Compra.TIPO_CUENTA_CORRIENTE,
            nro_factura=f"0003-{r.randint(100, 900):08d}", fecha=fecha_compra,
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
            # La producción arranca cuando termina la transición.
            fecha_inicio_produccion=None if estado == Lote.ESTADO_TRANSICION else plan_fin,
            fecha_vaciado=l["vaciado"], cantidad_inicial=l["aves"],
            cantidad_actual=l["aves"] - muertas, estado=estado, observaciones=l["obs"],
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
    for (aves, prov, precio, hace), estado, nro in (
        (LOTE_PENDIENTE, Compra.ESTADO_FINALIZADA, f"0003-{r.randint(1000, 1900):08d}"),
        (LOTE_PENDIENTE_SIN_FINALIZAR, Compra.ESTADO_PENDIENTE, f"0004-{r.randint(1000, 1900):08d}"),
    ):
        compra = Compra.objects.create(
            id_proveedor=proveedores[prov], id_usuario=admin, categoria=Compra.CATEGORIA_LOTES,
            tipo=Compra.TIPO_CONTADO, nro_factura=nro, fecha=dia(hace), estado=estado,
            observaciones="Pollitas listas para el próximo ciclo." if estado == Compra.ESTADO_FINALIZADA else "A confirmar fecha de entrega.",
        )
        LineaCompra.objects.create(id_compra=compra, cantidad=dec(aves), precio_unitario=dec(precio))

    # ---- Compras de materias primas --------------------------------------
    for c in plan.compras_mp:
        compra = Compra.objects.create(
            id_proveedor=proveedores[c["proveedor"]], id_usuario=admin,
            categoria=Compra.CATEGORIA_MATERIAS_PRIMAS, tipo=c["tipo"],
            nro_factura=c["nro"], fecha=c["fecha"], estado=c["estado"], observaciones=c["obs"],
        )
        for mp, (cantidad, precio) in c["lineas"].items():
            LineaCompra.objects.create(
                id_compra=compra, id_materia_prima=mps[mp],
                cantidad=dec(cantidad), precio_unitario=dec(precio),
            )

    # ---- Recolecciones ----------------------------------------------------
    for rec in plan.recolecciones:
        cab = Recoleccion.objects.create(
            id_galpon=galpones[rec["galpon"]], id_lote=lotes[rec["lote"]],
            id_usuario=operario_de[rec["galpon"]], fecha=momento(rec["fecha"], *rec["hora"]),
            estado=rec["estado"], observaciones=rec["obs"],
        )
        LineaRecoleccion.objects.bulk_create([
            LineaRecoleccion(
                id_recoleccion=cab, id_galpon=galpones[rec["galpon"]],
                id_producto=productos[k], cantidad=c,
            )
            for k, c in rec["cantidades"].items() if c > 0
        ])

    # ---- Entradas -----------------------------------------------------------
    for e in plan.entradas:
        cab = Entrada.objects.create(
            id_galpon=galpones[e["galpon"]], id_usuario=operario_de[e["galpon"]],
            fecha=momento(e["fecha"], *e["hora"]), estado=e["estado"], observaciones=e["obs"],
        )
        LineaEntrada.objects.bulk_create([
            LineaEntrada(id_entrada=cab, id_materia_prima=mps[mp], cantidad=dec(q))
            for mp, q in e["lineas"].items()
        ])

    # ---- Descartes -----------------------------------------------------------
    for de in plan.descartes:
        galpon = galpones[de["galpon"]] if de["galpon"] else None
        usuario = operario_de[de["galpon"]] if de["galpon"] else usuarios["operario1"]
        cab = Descarte.objects.create(
            categoria=de["categoria"], id_galpon=galpon, id_usuario=usuario,
            fecha=momento(de["fecha"], *de["hora"]), estado=de["estado"], observaciones=de["obs"],
        )
        LineaDescarte.objects.bulk_create([
            LineaDescarte(
                id_descarte=cab, id_galpon=galpon, cantidad=dec(l["cantidad"]), motivo=l["motivo"],
                id_lote=lotes[l["lote"]] if "lote" in l else None,
                id_producto=productos[l["producto"]] if "producto" in l else None,
                id_materia_prima=mps[l["mp"]] if "mp" in l else None,
            )
            for l in de["lineas"]
        ])

    # ---- Salidas -------------------------------------------------------------
    quien = [admin, usuarios["operario1"], usuarios["operario2"]]
    for i, s in enumerate(plan.salidas):
        cab = Salida.objects.create(
            id_usuario=quien[i % len(quien)], fecha=momento(s["fecha"], *s["hora"]),
            estado=s["estado"], observaciones=s["obs"],
        )
        LineaSalida.objects.bulk_create([
            LineaSalida(id_salida=cab, id_producto=productos[k], cantidad=q)
            for k, q in s["lineas"].items()
        ])

    return usuarios_creados


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

def resumen(usuarios_creados):
    print()
    print("Datos cargados:")
    filas = [
        ("Galpones", Galpon), ("Lotes", Lote), ("Productos", Producto),
        ("Materias primas", MateriaPrima), ("Proveedores", Proveedor),
        ("Compras", Compra), ("Recolecciones", Recoleccion), ("Entradas", Entrada),
        ("Descartes", Descarte), ("Salidas", Salida),
    ]
    for nombre, modelo in filas:
        print(f"  {nombre:<16} {modelo.objects.count():>5}")
    pendientes = LineaCompra.objects.filter(
        id_compra__categoria=Compra.CATEGORIA_LOTES,
        id_compra__estado=Compra.ESTADO_FINALIZADA, id_lote__isnull=True,
    ).count()
    print(f"  Lotes comprados sin asignar a un galpon: {pendientes}")
    print()
    print(f"Usuarios de prueba (clave: {PASSWORD}):")
    for usuario, nombre, apellido, _dni, rol in USUARIOS:
        print(f"  {usuario:<15} {dict(Usuario.ROL_CHOICES)[rol]:<14} {nombre} {apellido}")
    if not usuarios_creados:
        print("  (ya existian; no se modificaron)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Carga datos de ejemplo en la base de AviGest.")
    ap.add_argument("--limpiar", action="store_true",
                    help="borra antes los datos de negocio (los usuarios no se tocan)")
    ap.add_argument("--si", action="store_true", help="no pedir confirmacion")
    ap.add_argument("--dias", type=int, default=90, help="dias de historial (30 a 365, por defecto 90)")
    ap.add_argument("--semilla", type=int, default=2026, help="semilla de los numeros al azar")
    args = ap.parse_args()

    if not 30 <= args.dias <= 365:
        ap.error("--dias tiene que estar entre 30 y 365")

    if hay_datos() and not args.limpiar:
        print("La base ya tiene datos. Para borrarlos y volver a cargar usa:  py poblar_datos.py --limpiar")
        sys.exit(1)
    if args.limpiar and hay_datos() and not args.si:
        resp = input(
            "Se van a BORRAR galpones, lotes, productos, materias primas, proveedores, compras,\n"
            "recolecciones, entradas, descartes y salidas. Los usuarios no se tocan.\n"
            "Escribi 'si' para continuar: "
        )
        if resp.strip().lower() not in ("si", "sí", "s"):
            print("Cancelado.")
            sys.exit(0)

    plan = Plan(args.dias, args.semilla)
    plan.construir()
    with transaction.atomic():
        if args.limpiar:
            limpiar()
        usuarios_creados = escribir(plan)
    resumen(usuarios_creados)


if __name__ == "__main__":
    main()
