"""
Cálculos de los informes (CU85 a CU89).

Los informes no tienen modelos propios: leen lo que ya cargaron los demás
módulos. Solo cuentan los registros FINALIZADOS (recolecciones, descartes,
entradas y compras): los pendientes todavía no hicieron efecto.

Definiciones:
    · Postura de un día = huevos recolectados / gallinas del lote ese día × 100.
    · Gallinas de un lote en un día = cantidad inicial − gallinas descartadas
      (en descartes finalizados) hasta ese día inclusive.
    · Consumo de una materia prima = lo que se envió a los galpones en entradas
      finalizadas (el sistema no registra el consumo diario real).
    · Mortandad = gallinas descartadas.
"""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from compras.models import Compra, LineaCompra
from descartes.models import Descarte, LineaDescarte
from descartes.stock import stock_actual_materia_prima
from entradas.models import Entrada, LineaEntrada
from galpones.models import Galpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from recolecciones.models import LineaRecoleccion, Recoleccion

# Tope del rango de fechas: evita informes gigantes por error de tipeo.
MAX_DIAS = 366
DEFAULT_DIAS = 30


# ── Parámetros ────────────────────────────────────────────────────────────────

def _fecha(params, nombre):
    texto = params.get(nombre)
    if not texto:
        return None
    try:
        return datetime.date.fromisoformat(texto)
    except ValueError:
        raise ValidationError({nombre: "Fecha inválida. Usá el formato AAAA-MM-DD."})


def parsear_periodo(params):
    """(desde, hasta) del pedido. Por defecto, los últimos 30 días."""
    hasta = _fecha(params, "fecha_hasta") or timezone.localdate()
    desde = _fecha(params, "fecha_desde") or hasta - datetime.timedelta(days=DEFAULT_DIAS - 1)
    if desde > hasta:
        raise ValidationError({"fecha_desde": "La fecha desde no puede ser posterior a la fecha hasta."})
    if (hasta - desde).days + 1 > MAX_DIAS:
        raise ValidationError({"fecha_desde": f"El período no puede superar {MAX_DIAS} días."})
    return desde, hasta


def parsear_objetivo(params):
    """Valor objetivo opcional (número no negativo) para dibujarlo en el gráfico."""
    texto = params.get("objetivo")
    if texto in (None, ""):
        return None
    try:
        valor = float(str(texto).replace(",", "."))
    except ValueError:
        raise ValidationError({"objetivo": "El valor objetivo debe ser un número."})
    if valor < 0 or valor != valor or valor in (float("inf"),):
        raise ValidationError({"objetivo": "El valor objetivo debe ser un número mayor o igual a cero."})
    return valor


def parsear_id(params, nombre, modelo, etiqueta):
    """Valor opcional de un filtro por id; devuelve la instancia o None."""
    valor = params.get(nombre)
    if valor in (None, ""):
        return None
    try:
        return modelo.objects.get(pk=int(valor))
    except (ValueError, modelo.DoesNotExist):
        raise ValidationError({nombre: f"{etiqueta} inexistente."})


def _dia(dt):
    return timezone.localtime(dt).date()


def _redondear(valor, decimales=1):
    if valor is None:
        return None
    return round(float(valor), decimales)


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def dias_del_periodo(desde, hasta):
    return [desde + datetime.timedelta(days=i) for i in range((hasta - desde).days + 1)]


# ── Datos base ────────────────────────────────────────────────────────────────

def _huevos_por_lote_y_dia(desde, hasta, id_galpon=None):
    """{(id_lote, id_galpon, día): huevos} de recolecciones finalizadas."""
    qs = LineaRecoleccion.objects.filter(
        id_recoleccion__estado=Recoleccion.ESTADO_FINALIZADA,
        id_recoleccion__fecha__date__gte=desde,
        id_recoleccion__fecha__date__lte=hasta,
    )
    if id_galpon is not None:
        qs = qs.filter(id_recoleccion__id_galpon=id_galpon)
    huevos = defaultdict(int)
    for id_lote, galpon, fecha, cantidad in qs.values_list(
        "id_recoleccion__id_lote", "id_recoleccion__id_galpon", "id_recoleccion__fecha", "cantidad"
    ):
        huevos[(id_lote, galpon, _dia(fecha))] += cantidad
    return huevos


def _gallinas_descartadas(ids_lotes, hasta=None):
    """{id_lote: [(día, cantidad), ...]} ordenado por día."""
    qs = LineaDescarte.objects.filter(
        id_descarte__estado=Descarte.ESTADO_FINALIZADO,
        id_lote__in=ids_lotes,
    )
    por_lote = defaultdict(list)
    for id_lote, fecha, cantidad in qs.values_list("id_lote", "id_descarte__fecha", "cantidad"):
        por_lote[id_lote].append((_dia(fecha), int(cantidad)))
    for lista in por_lote.values():
        lista.sort()
    return por_lote


class _Gallinas:
    """Cantidad de gallinas de cada lote en cada día."""

    def __init__(self, ids_lotes):
        ids = [i for i in ids_lotes if i is not None]
        self.inicial = dict(Lote.objects.filter(pk__in=ids).values_list("pk", "cantidad_inicial"))
        self.descartes = _gallinas_descartadas(ids)

    def en(self, id_lote, dia):
        if id_lote not in self.inicial:
            return None
        descartadas = sum(c for d, c in self.descartes.get(id_lote, []) if d <= dia)
        return max(self.inicial[id_lote] - descartadas, 0)


def _postura(huevos, gallinas):
    if not gallinas:
        return None
    return huevos / gallinas * 100


def serie_postura(desde, hasta, id_galpon=None):
    """
    [{fecha, valor}] con la postura de cada día (huevos del día / gallinas de
    los lotes que tuvieron recolección ese día). valor = None si no hubo.
    """
    huevos = _huevos_por_lote_y_dia(desde, hasta, id_galpon)
    gallinas = _Gallinas(k[0] for k in huevos)
    huevos_dia = defaultdict(int)
    gallinas_dia = defaultdict(int)
    for (id_lote, _g, dia), cantidad in huevos.items():
        g = gallinas.en(id_lote, dia)
        huevos_dia[dia] += cantidad
        if g:
            gallinas_dia[dia] += g
    return [
        {"fecha": d.isoformat(), "valor": _redondear(_postura(huevos_dia[d], gallinas_dia[d])) if d in huevos_dia else None}
        for d in dias_del_periodo(desde, hasta)
    ]


# ── CU85 Informe de producción ────────────────────────────────────────────────

def informe_produccion(desde, hasta, galpon=None):
    id_galpon = galpon.pk if galpon else None
    huevos = _huevos_por_lote_y_dia(desde, hasta, id_galpon)
    gallinas = _Gallinas(k[0] for k in huevos)

    por_lote = defaultdict(lambda: {"huevos": 0, "dias": set(), "posturas": []})
    for (id_lote, id_g, dia), cantidad in huevos.items():
        fila = por_lote[(id_lote, id_g)]
        fila["huevos"] += cantidad
        fila["dias"].add(dia)
        g = gallinas.en(id_lote, dia)
        fila["posturas"].append(_postura(cantidad, g))

    galpones = dict(Galpon.objects.values_list("pk", "galpon"))
    lotes = {l.pk: l for l in Lote.objects.filter(pk__in=[k[0] for k in por_lote if k[0]])}

    filas = []
    for (id_lote, id_g), datos in por_lote.items():
        dias = len(datos["dias"])
        filas.append({
            "id_galpon": id_g,
            "galpon": galpones.get(id_g, "—"),
            "id_lote": id_lote,
            "lote": lotes[id_lote].codigo if id_lote in lotes else "—",
            "huevos_total": datos["huevos"],
            "dias_con_registro": dias,
            "promedio_diario": _redondear(datos["huevos"] / dias) if dias else None,
            "postura_promedio": _redondear(_promedio(datos["posturas"])),
        })
    filas.sort(key=lambda f: (f["galpon"], f["lote"]))

    serie = serie_postura(desde, hasta, id_galpon)
    total_huevos = sum(f["huevos_total"] for f in filas)
    dias_total = len({d for (_l, _g, d) in huevos})
    totales = {
        "galpon": "Total",
        "huevos_total": total_huevos,
        "dias_con_registro": dias_total,
        "promedio_diario": _redondear(total_huevos / dias_total) if dias_total else None,
        "postura_promedio": _redondear(_promedio(p["valor"] for p in serie)),
    }
    return {
        "titulo": "Informe de producción",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "filtros": [("Galpón", galpon.galpon if galpon else "Todos")],
        "columnas": [
            {"clave": "galpon", "titulo": "Galpón", "tipo": "texto"},
            {"clave": "lote", "titulo": "Lote", "tipo": "texto"},
            {"clave": "huevos_total", "titulo": "Huevos producidos", "tipo": "entero"},
            {"clave": "dias_con_registro", "titulo": "Días con registro", "tipo": "entero"},
            {"clave": "promedio_diario", "titulo": "Promedio diario", "tipo": "decimal"},
            {"clave": "postura_promedio", "titulo": "Postura promedio (%)", "tipo": "decimal"},
        ],
        "filas": filas,
        "totales": totales,
    }


# ── CU86 Informe de lotes ─────────────────────────────────────────────────────

def informe_lotes(estado=None, galpon=None):
    hoy = timezone.localdate()
    qs = Lote.objects.select_related("id_galpon").order_by("id_galpon__galpon", "-fecha_ingreso")
    if estado:
        qs = qs.filter(estado=estado)
    if galpon is not None:
        qs = qs.filter(id_galpon=galpon)

    lotes = list(qs)
    # Mortandad de un lote = sus gallinas descartadas (descartes finalizados).
    bajas_por_lote = defaultdict(int)
    for id_lote, cantidad in LineaDescarte.objects.filter(
        id_descarte__estado=Descarte.ESTADO_FINALIZADO,
        id_lote__in=[l.pk for l in lotes],
    ).values_list("id_lote", "cantidad"):
        bajas_por_lote[id_lote] += int(cantidad)

    filas = []
    for lote in lotes:
        fin = lote.fecha_vaciado or hoy
        dias = max((fin - lote.fecha_ingreso).days, 0)
        bajas = bajas_por_lote.get(lote.pk, 0)
        filas.append({
            "id_lote": lote.pk,
            "lote": lote.codigo,
            "galpon": lote.id_galpon.galpon,
            "etapa": lote.get_estado_display(),
            "fecha_ingreso": lote.fecha_ingreso.isoformat(),
            "fecha_vaciado": lote.fecha_vaciado.isoformat() if lote.fecha_vaciado else None,
            "edad_dias": dias,
            "edad_semanas": dias // 7,
            "cantidad_inicial": lote.cantidad_inicial,
            "cantidad_actual": lote.cantidad_actual,
            "mortandad": bajas,
            "mortandad_pct": _redondear(bajas / lote.cantidad_inicial * 100) if lote.cantidad_inicial else None,
        })
    etiquetas = dict(Lote.ESTADO_CHOICES)
    return {
        "titulo": "Informe de lotes",
        "periodo": None,
        "filtros": [
            ("Galpón", galpon.galpon if galpon else "Todos"),
            ("Etapa", etiquetas.get(estado, "Todas")),
            ("Fecha de corte", hoy.strftime("%d/%m/%Y")),
        ],
        "columnas": [
            {"clave": "lote", "titulo": "Lote", "tipo": "texto"},
            {"clave": "galpon", "titulo": "Galpón", "tipo": "texto"},
            {"clave": "etapa", "titulo": "Etapa", "tipo": "texto"},
            {"clave": "fecha_ingreso", "titulo": "Ingreso", "tipo": "fecha"},
            {"clave": "edad_semanas", "titulo": "Edad (semanas)", "tipo": "entero"},
            {"clave": "cantidad_inicial", "titulo": "Gallinas iniciales", "tipo": "entero"},
            {"clave": "cantidad_actual", "titulo": "Gallinas actuales", "tipo": "entero"},
            {"clave": "mortandad", "titulo": "Mortandad", "tipo": "entero"},
            {"clave": "mortandad_pct", "titulo": "Mortandad (%)", "tipo": "decimal"},
        ],
        "filas": filas,
        "totales": {
            "lote": "Total",
            "cantidad_inicial": sum(f["cantidad_inicial"] for f in filas),
            "cantidad_actual": sum(f["cantidad_actual"] for f in filas),
            "mortandad": sum(f["mortandad"] for f in filas),
        },
    }


# ── CU87 Informe de materias primas ───────────────────────────────────────────

def _suma_por_materia(qs, campo_fk):
    totales = defaultdict(Decimal)
    for id_mp, cantidad in qs.values_list(campo_fk, "cantidad"):
        totales[id_mp] += cantidad
    return totales


def informe_materias_primas(desde, hasta, materia=None):
    consumido = _suma_por_materia(
        LineaEntrada.objects.filter(
            id_entrada__estado=Entrada.ESTADO_FINALIZADA,
            id_entrada__fecha__date__gte=desde, id_entrada__fecha__date__lte=hasta,
        ),
        "id_materia_prima",
    )
    comprado = _suma_por_materia(
        LineaCompra.objects.filter(
            id_compra__categoria=Compra.CATEGORIA_MATERIAS_PRIMAS,
            id_compra__estado=Compra.ESTADO_FINALIZADA,
            id_compra__fecha__gte=desde, id_compra__fecha__lte=hasta,
        ),
        "id_materia_prima",
    )
    descartado = _suma_por_materia(
        LineaDescarte.objects.filter(
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            # Solo los descartes de stock restan del stock (los de galpón ya
            # salieron de él al enviarse a los galpones).
            id_descarte__categoria=Descarte.CATEGORIA_STOCK,
            id_materia_prima__isnull=False,
            id_descarte__fecha__date__gte=desde, id_descarte__fecha__date__lte=hasta,
        ),
        "id_materia_prima",
    )

    qs = MateriaPrima.objects.order_by("materia_prima")
    if materia is not None:
        qs = qs.filter(pk=materia.pk)

    filas = []
    for mp in qs:
        stock = stock_actual_materia_prima(mp)
        filas.append({
            "id_materia_prima": mp.pk,
            "materia_prima": mp.materia_prima,
            "unidad": mp.unidad,
            "consumido": _redondear(consumido.get(mp.pk, 0), 2),
            "comprado": _redondear(comprado.get(mp.pk, 0), 2),
            "descartado": _redondear(descartado.get(mp.pk, 0), 2),
            "stock_actual": _redondear(stock, 2),
            "stock_minimo": _redondear(mp.stock_minimo, 2),
            "bajo_minimo": stock < mp.stock_minimo,
        })
    return {
        "titulo": "Informe de materias primas",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "filtros": [("Materia prima", materia.materia_prima if materia else "Todas")],
        "columnas": [
            {"clave": "materia_prima", "titulo": "Materia prima", "tipo": "texto"},
            {"clave": "unidad", "titulo": "Unidad", "tipo": "texto"},
            {"clave": "consumido", "titulo": "Consumido (enviado a galpones)", "tipo": "decimal"},
            {"clave": "comprado", "titulo": "Comprado", "tipo": "decimal"},
            {"clave": "descartado", "titulo": "Descartado de stock", "tipo": "decimal"},
            {"clave": "stock_actual", "titulo": "Stock actual", "tipo": "decimal"},
            {"clave": "stock_minimo", "titulo": "Stock mínimo", "tipo": "decimal"},
        ],
        "filas": filas,
        "totales": None,
    }


# ── CU88 Informe de descartes ─────────────────────────────────────────────────

TIPOS_DESCARTE = {"G": "Gallinas", "M": "Materia prima", "P": "Producto"}


def informe_descartes(desde, hasta, galpon=None, tipo=None):
    qs = (
        LineaDescarte.objects.filter(
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            id_descarte__fecha__date__gte=desde,
            id_descarte__fecha__date__lte=hasta,
        )
        .select_related("id_descarte", "id_galpon", "id_materia_prima", "id_producto", "id_lote")
        .order_by("-id_descarte__fecha", "-id_linea_descarte")
    )
    if galpon is not None:
        qs = qs.filter(id_galpon=galpon)
    if tipo == "G":
        qs = qs.filter(id_lote__isnull=False)
    elif tipo == "M":
        qs = qs.filter(id_materia_prima__isnull=False)
    elif tipo == "P":
        qs = qs.filter(id_producto__isnull=False)

    filas = []
    por_tipo = defaultdict(int)
    for l in qs:
        if l.id_lote_id:
            t, item, unidad = "G", l.id_lote.codigo, "gallinas"
        elif l.id_materia_prima_id:
            t, item, unidad = "M", l.id_materia_prima.materia_prima, l.id_materia_prima.unidad
        else:
            t, item, unidad = "P", l.id_producto.producto, "unid."
        por_tipo[t] += 1
        filas.append({
            "id_descarte": l.id_descarte_id,
            "fecha": _dia(l.id_descarte.fecha).isoformat(),
            "origen": "Galpón" if l.id_descarte.categoria == Descarte.CATEGORIA_GALPON else "Stock",
            "galpon": l.id_galpon.galpon if l.id_galpon_id else "—",
            "tipo": TIPOS_DESCARTE[t],
            "item": item,
            "cantidad": _redondear(l.cantidad, 2),
            "unidad": unidad,
            "motivo": l.motivo,
        })
    return {
        "titulo": "Informe de descartes",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "filtros": [
            ("Galpón", galpon.galpon if galpon else "Todos"),
            ("Tipo", TIPOS_DESCARTE.get(tipo, "Todos")),
        ],
        "columnas": [
            {"clave": "fecha", "titulo": "Fecha", "tipo": "fecha"},
            {"clave": "origen", "titulo": "Origen", "tipo": "texto"},
            {"clave": "galpon", "titulo": "Galpón", "tipo": "texto"},
            {"clave": "tipo", "titulo": "Tipo", "tipo": "texto"},
            {"clave": "item", "titulo": "Descartado", "tipo": "texto"},
            {"clave": "cantidad", "titulo": "Cantidad", "tipo": "decimal"},
            {"clave": "unidad", "titulo": "Unidad", "tipo": "texto"},
            {"clave": "motivo", "titulo": "Motivo", "tipo": "texto"},
        ],
        "filas": filas,
        "totales": {"fecha": "Registros", "cantidad": len(filas)} if filas else None,
        "resumen": {TIPOS_DESCARTE[k]: v for k, v in por_tipo.items()},
    }


# ── CU89 Indicadores productivos ──────────────────────────────────────────────

INDICADORES = {
    "postura": ("Postura", "%"),
    "mortandad": ("Mortandad", "gallinas"),
    "consumo": ("Consumo de materia prima", ""),
}


def _serie_mortandad(desde, hasta, id_galpon=None):
    qs = LineaDescarte.objects.filter(
        id_descarte__estado=Descarte.ESTADO_FINALIZADO,
        id_lote__isnull=False,
        id_descarte__fecha__date__gte=desde,
        id_descarte__fecha__date__lte=hasta,
    )
    if id_galpon is not None:
        qs = qs.filter(id_galpon=id_galpon)
    por_dia = defaultdict(int)
    for fecha, cantidad in qs.values_list("id_descarte__fecha", "cantidad"):
        por_dia[_dia(fecha)] += int(cantidad)
    return [{"fecha": d.isoformat(), "valor": por_dia.get(d, 0)} for d in dias_del_periodo(desde, hasta)]


def _serie_consumo(desde, hasta, materia, id_galpon=None):
    qs = LineaEntrada.objects.filter(
        id_entrada__estado=Entrada.ESTADO_FINALIZADA,
        id_materia_prima=materia.pk,
        id_entrada__fecha__date__gte=desde,
        id_entrada__fecha__date__lte=hasta,
    )
    if id_galpon is not None:
        qs = qs.filter(id_entrada__id_galpon=id_galpon)
    por_dia = defaultdict(Decimal)
    for fecha, cantidad in qs.values_list("id_entrada__fecha", "cantidad"):
        por_dia[_dia(fecha)] += cantidad
    return [
        {"fecha": d.isoformat(), "valor": _redondear(por_dia.get(d, 0), 2)}
        for d in dias_del_periodo(desde, hasta)
    ]


def indicadores(desde, hasta, indicador, galpon=None, materia=None, objetivo=None):
    id_galpon = galpon.pk if galpon else None
    if indicador not in INDICADORES:
        raise ValidationError({"indicador": "Indicador inválido. Usá postura, mortandad o consumo."})
    if indicador == "consumo" and materia is None:
        raise ValidationError({"id_materia_prima": "Elegí la materia prima para ver su consumo."})

    postura = serie_postura(desde, hasta, id_galpon)
    if indicador == "postura":
        serie, unidad = postura, "%"
    elif indicador == "mortandad":
        serie, unidad = _serie_mortandad(desde, hasta, id_galpon), "gallinas"
    else:
        serie, unidad = _serie_consumo(desde, hasta, materia, id_galpon), materia.unidad

    huevos = sum(_huevos_por_lote_y_dia(desde, hasta, id_galpon).values())
    valores = [p["valor"] for p in serie if p["valor"] is not None]
    nombre = INDICADORES[indicador][0] + (f" — {materia.materia_prima}" if indicador == "consumo" else "")
    resumen = {
        "huevos_producidos": huevos,
        "postura_promedio": _redondear(_promedio(p["valor"] for p in postura)),
        "mortandad_total": sum(p["valor"] for p in _serie_mortandad(desde, hasta, id_galpon)),
        "descartes_registrados": LineaDescarte.objects.filter(
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            id_descarte__fecha__date__gte=desde, id_descarte__fecha__date__lte=hasta,
            **({"id_galpon": id_galpon} if id_galpon else {}),
        ).count(),
    }
    promedio = _promedio(valores)
    etiqueta_valor = f"{nombre} ({unidad})" if unidad else nombre
    columnas = [
        {"clave": "fecha", "titulo": "Fecha", "tipo": "fecha"},
        {"clave": "valor", "titulo": etiqueta_valor, "tipo": "decimal"},
    ]
    filas = serie
    totales = {"fecha": "Promedio", "valor": _redondear(promedio, 2)}
    series_grafico = [{"nombre": nombre, "valores": [p["valor"] for p in serie]}]
    if objetivo is not None:
        # El valor objetivo lo escribe el usuario: sale como una línea constante.
        columnas.append({"clave": "objetivo", "titulo": "Valor objetivo", "tipo": "decimal"})
        filas = [{**p, "objetivo": objetivo} for p in serie]
        totales["objetivo"] = objetivo
        series_grafico.append({"nombre": "Valor objetivo", "valores": [objetivo] * len(serie)})
    return {
        "titulo": f"Indicador: {nombre}",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "filtros": [("Galpón", galpon.galpon if galpon else "Todos")],
        "indicador": indicador,
        "unidad": unidad,
        "serie": serie,
        "promedio": _redondear(promedio, 2),
        "total": _redondear(sum(valores), 2) if indicador != "postura" else None,
        "resumen": resumen,
        "objetivo": objetivo,
        "columnas": columnas,
        "filas": filas,
        "totales": totales,
        # Gráfica que acompaña a las exportaciones (PDF y Excel).
        "grafico": {
            "etiquetas": [p["fecha"] for p in serie],
            "series": series_grafico,
            "unidad": unidad,
        },
    }
