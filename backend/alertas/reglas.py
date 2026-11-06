"""
Reglas que generan las alertas de los lotes.

Cada regla mira la información que ya cargaron los demás módulos y responde una
sola pregunta: «¿qué lotes están hoy en esta situación?». Devuelve
``{id_lote: descripción}``; de pasar eso a filas de la tabla Alertas se ocupa
alertas/generacion.py.

Solo cuentan los registros FINALIZADOS (recolecciones y descartes): los
pendientes todavía no hicieron efecto, igual que en los informes y en el stock.

Los umbrales están arriba, juntos y con nombre, para poder ajustarlos en un
solo lugar cuando la granja los revise.
"""

import datetime
from collections import defaultdict

from django.db.models import Max, Sum
from django.utils import timezone

from descartes.models import Descarte, LineaDescarte
from informes.calculos import Gallinas, huevos_por_lote_y_dia, postura_del_dia
from lotes.models import Lote, PlanTransicion
from recolecciones.models import Recoleccion

# ── Umbrales ──────────────────────────────────────────────────────────────────

#: Postura mínima esperada en un día (%). Por debajo se avisa.
POSTURA_MINIMA = 70.0

#: Días hacia atrás que se miran para encontrar el último día con recolección.
DIAS_VENTANA_POSTURA = 7

#: Con cuántos días de anticipación se avisa que la transición está por vencer.
DIAS_AVISO_TRANSICION = 3

#: Porcentaje del plantel inicial que, descartado en una semana, se considera
#: una mortandad alta.
MORTANDAD_SEMANAL_MAXIMA = 1.0

#: Días sin recolección finalizada que se toleran en un lote en producción.
DIAS_SIN_RECOLECCION = 3

# ── Claves de los tipos de alerta (ver la migración de datos 0002) ───────────

POSTURA_BAJA = "postura_baja"
TRANSICION_POR_VENCER = "transicion_por_vencer"
MORTANDAD_ALTA = "mortandad_alta"
SIN_RECOLECCION = "sin_recoleccion"

#: Tipos que crea la migración de datos: clave, nombre y severidad.
TIPOS = [
    (POSTURA_BAJA, "Postura baja", "A"),
    (MORTANDAD_ALTA, "Mortandad alta", "A"),
    (TRANSICION_POR_VENCER, "Plan de transición por vencer", "M"),
    (SIN_RECOLECCION, "Sin recolecciones recientes", "M"),
]


# ── Ayudas ────────────────────────────────────────────────────────────────────

def _encabezado(lote):
    """«Lote L-2026-005 · Galpón 3», el comienzo de toda descripción."""
    return f"Lote {lote.codigo} · {lote.id_galpon.galpon}"


def _numero(valor, decimales=1):
    """Número con coma decimal, como se escribe en español."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def _dias(cantidad):
    return "1 día" if cantidad == 1 else f"{cantidad} días"


def _lotes(estado):
    return Lote.objects.filter(estado=estado).select_related("id_galpon")


# ── Reglas ────────────────────────────────────────────────────────────────────

def postura_baja(hoy):
    """
    Lotes en producción cuyo último día con recolección quedó por debajo de la
    postura mínima. Se mira el último día con datos (y no estrictamente hoy)
    porque a la mañana todavía no hay recolecciones cargadas y el lote no
    tendría por qué dejar de estar en alerta.
    """
    lotes = {l.pk: l for l in _lotes(Lote.ESTADO_PRODUCCION)}
    if not lotes:
        return {}

    desde = hoy - datetime.timedelta(days=DIAS_VENTANA_POSTURA - 1)
    huevos = huevos_por_lote_y_dia(desde, hoy)
    por_lote = defaultdict(dict)
    for (id_lote, _id_galpon, dia), cantidad in huevos.items():
        if id_lote in lotes:
            por_lote[id_lote][dia] = por_lote[id_lote].get(dia, 0) + cantidad

    gallinas = Gallinas(por_lote.keys())
    situaciones = {}
    for id_lote, dias in por_lote.items():
        dia = max(dias)
        valor = postura_del_dia(dias[dia], gallinas.en(id_lote, dia))
        if valor is None or valor >= POSTURA_MINIMA:
            continue
        situaciones[id_lote] = (
            f"{_encabezado(lotes[id_lote])} — {_numero(valor)}% de postura "
            f"el {dia:%d/%m} (el mínimo esperado es {_numero(POSTURA_MINIMA, 0)}%)."
        )
    return situaciones


def transicion_por_vencer(hoy):
    """
    Lotes en transición a los que les quedan pocos días de plan. Al vencer, el
    sistema los pasa solo a producción (lotes/transiciones.py): el aviso sirve
    para llegar preparado a ese día.
    """
    limite = hoy + datetime.timedelta(days=DIAS_AVISO_TRANSICION)
    lotes = _lotes(Lote.ESTADO_TRANSICION).filter(
        plan_transicion__estado=PlanTransicion.ESTADO_EN_CURSO,
        plan_transicion__fecha_fin__gt=hoy,
        plan_transicion__fecha_fin__lte=limite,
    ).select_related("plan_transicion")

    situaciones = {}
    for lote in lotes:
        fin = lote.plan_transicion.fecha_fin
        faltan = (fin - hoy).days
        cuando = "mañana" if faltan == 1 else f"en {_dias(faltan)}"
        situaciones[lote.pk] = (
            f"{_encabezado(lote)} — la transición termina {cuando} ({fin:%d/%m/%Y}) "
            "y el lote pasa a producción."
        )
    return situaciones


def mortandad_alta(hoy):
    """
    Lotes cuyos descartes de gallinas de la última semana superan el porcentaje
    esperado del plantel inicial.
    """
    lotes = {
        l.pk: l
        for l in Lote.objects.filter(
            estado__in=[Lote.ESTADO_TRANSICION, Lote.ESTADO_PRODUCCION]
        ).select_related("id_galpon")
    }
    if not lotes:
        return {}

    desde = hoy - datetime.timedelta(days=6)
    filas = (
        LineaDescarte.objects.filter(
            id_lote__in=list(lotes),
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            id_descarte__fecha__date__gte=desde,
            id_descarte__fecha__date__lte=hoy,
        )
        .values("id_lote")
        .annotate(total=Sum("cantidad"))
    )

    situaciones = {}
    for fila in filas:
        lote = lotes[fila["id_lote"]]
        if not lote.cantidad_inicial:
            continue
        descartadas = int(fila["total"] or 0)
        porcentaje = descartadas / lote.cantidad_inicial * 100
        if porcentaje <= MORTANDAD_SEMANAL_MAXIMA:
            continue
        situaciones[lote.pk] = (
            f"{_encabezado(lote)} — {descartadas} gallinas descartadas en la última "
            f"semana ({_numero(porcentaje)}% del plantel inicial; el máximo esperado "
            f"es {_numero(MORTANDAD_SEMANAL_MAXIMA)}%)."
        )
    return situaciones


def sin_recoleccion(hoy):
    """
    Lotes en producción que hace varios días no tienen una recolección
    finalizada. Un lote recién pasado a producción no se avisa hasta que
    transcurre ese mismo plazo.
    """
    limite = hoy - datetime.timedelta(days=DIAS_SIN_RECOLECCION)
    lotes = {
        l.pk: l
        for l in _lotes(Lote.ESTADO_PRODUCCION).filter(
            fecha_inicio_produccion__isnull=False,
            fecha_inicio_produccion__lt=limite,
        )
    }
    if not lotes:
        return {}

    ultimas = {
        fila["id_lote"]: fila["ultima"]
        for fila in Recoleccion.objects.filter(
            id_lote__in=list(lotes), estado=Recoleccion.ESTADO_FINALIZADA
        )
        .values("id_lote")
        .annotate(ultima=Max("fecha"))
    }

    situaciones = {}
    for id_lote, lote in lotes.items():
        ultima = ultimas.get(id_lote)
        dia = timezone.localtime(ultima).date() if ultima else None
        if dia is not None and dia >= limite:
            continue
        detalle = (
            f"sin recolecciones finalizadas desde el {dia:%d/%m}"
            if dia
            else "todavía no tiene ninguna recolección finalizada"
        )
        situaciones[id_lote] = f"{_encabezado(lote)} — {detalle}."
    return situaciones


# ── Evaluación completa ───────────────────────────────────────────────────────

def evaluar(hoy):
    """{clave del tipo: {id_lote: descripción}} con las situaciones de hoy."""
    return {
        POSTURA_BAJA: postura_baja(hoy),
        MORTANDAD_ALTA: mortandad_alta(hoy),
        TRANSICION_POR_VENCER: transicion_por_vencer(hoy),
        SIN_RECOLECCION: sin_recoleccion(hoy),
    }
