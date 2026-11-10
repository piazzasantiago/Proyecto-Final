"""
Datos del panel principal.

El dashboard no tiene modelos propios: resume lo que ya cargaron los demás
módulos, con las mismas definiciones que los informes (solo cuentan los
registros FINALIZADOS) y el mismo criterio de acceso que el resto del sistema
(el Operario solo ve sus galpones asignados, F-32).

Todo se calcula acá y se entrega listo para mostrar: la pantalla solo da
formato.
"""

import datetime
import re
from collections import defaultdict

from django.db.models import Count, Q, Sum
from django.utils import timezone

from alertas.views import alertas_visibles
from alertas.models import Alerta
from compras.models import Compra
from descartes.models import Descarte
from entradas.models import Entrada
from galpones.acceso import es_operario, ids_galpones_asignados, limitar_a_galpones_asignados
from galpones.models import Galpon
from informes.calculos import (
    Gallinas,
    dias_del_periodo,
    huevos_por_lote_y_dia,
    postura_del_dia,
    serie_postura,
)
from lotes.models import Lote
from productos.models import Producto
from productos.stock import anotar_stock, stock_actual
from recolecciones.models import Recoleccion
from salidas.models import Salida

#: Días de producción que muestra el gráfico de barras.
DIAS_PRODUCCION = 7

#: Cuántas alertas entran en la tarjeta del panel.
MAX_ALERTAS = 6

#: Durante cuántos días sigue apareciendo una alerta ya resuelta.
DIAS_ALERTAS_RESUELTAS = 7


def _galpones_visibles(usuario):
    """Ids de los galpones que ve el usuario, o None si los ve todos."""
    if es_operario(usuario):
        return ids_galpones_asignados(usuario)
    return None


def _variacion_porcentual(actual, anterior):
    """Cuánto creció o bajó un valor respecto del anterior, en %."""
    if not anterior:
        return None
    return round((actual - anterior) / anterior * 100, 1)


def _produccion(hoy, ids_galpones):
    """Huevos recolectados por día en la última semana."""
    desde = hoy - datetime.timedelta(days=DIAS_PRODUCCION - 1)
    huevos = huevos_por_lote_y_dia(desde, hoy, ids_galpones=ids_galpones)
    por_dia = defaultdict(int)
    for (_id_lote, _id_galpon, dia), cantidad in huevos.items():
        por_dia[dia] += cantidad
    return [
        {"fecha": dia.isoformat(), "huevos": por_dia.get(dia, 0)}
        for dia in dias_del_periodo(desde, hoy)
    ]


def _galpones(ids_galpones):
    """
    Estado de los galpones para la tarjeta del panel: de los activos, cuántos
    tienen un lote en producción, cuántos uno en transición y cuántos no tienen
    lote; más los inactivos y las gallinas que hay en producción.
    """
    todos = Galpon.objects.all()
    if ids_galpones is not None:
        todos = todos.filter(pk__in=ids_galpones)
    activos = todos.filter(estado=Galpon.ESTADO_ACTIVO)

    en_produccion = set(
        activos.filter(lotes__estado=Lote.ESTADO_PRODUCCION).values_list("pk", flat=True)
    )
    # Un galpón con lote en producción cuenta solo como "en producción".
    en_transicion = (
        set(activos.filter(lotes__estado=Lote.ESTADO_TRANSICION).values_list("pk", flat=True))
        - en_produccion
    )
    total_activos = activos.count()
    gallinas = (
        Lote.objects.filter(estado=Lote.ESTADO_PRODUCCION, id_galpon__in=activos).aggregate(
            total=Sum("cantidad_actual")
        )["total"]
        or 0
    )
    return {
        "activos": total_activos,
        "en_produccion": len(en_produccion),
        "en_transicion": len(en_transicion),
        "sin_lote": total_activos - len(en_produccion) - len(en_transicion),
        "inactivos": todos.exclude(estado=Galpon.ESTADO_ACTIVO).count(),
        "gallinas": gallinas,
    }


def _orden_natural(nombre):
    """«Galpón 2» antes que «Galpón 10»."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", nombre)]


def _mapa_galpones(usuario, ids_galpones, hoy, ids_con_alerta):
    """
    Un renglón por galpón para el mapa del panel: su situación (producción,
    transición, activo sin lote o inactivo), el lote y las gallinas que tiene,
    su postura del último día con recolección de la semana y si tiene alertas
    pendientes.

    La postura es la del último día con datos y no siempre la de hoy: a primera
    hora todavía no se recolectó y el galpón no tiene que quedar «sin dato».
    `postura_fecha` dice a qué día corresponde.
    """
    galpones = Galpon.objects.all()
    if ids_galpones is not None:
        galpones = galpones.filter(pk__in=ids_galpones)

    # De cada galpón, el lote que cuenta: el que está en producción y, si no hay, el que está en transición.
    lotes = {}
    for lote in Lote.objects.filter(
        estado__in=[Lote.ESTADO_PRODUCCION, Lote.ESTADO_TRANSICION], id_galpon__in=galpones
    ).order_by("estado", "pk"):
        # "P" ordena antes que "T": el primero que aparece es el de producción.
        lotes.setdefault(lote.id_galpon_id, lote)

    desde = hoy - datetime.timedelta(days=DIAS_PRODUCCION - 1)
    huevos = huevos_por_lote_y_dia(desde, hoy, ids_galpones=ids_galpones)
    gallinas = Gallinas(k[0] for k in huevos)
    # {galpón: {día: [huevos, gallinas]}}
    por_galpon = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for (id_lote, id_galpon, dia), cantidad in huevos.items():
        acumulado = por_galpon[id_galpon][dia]
        acumulado[0] += cantidad
        acumulado[1] += gallinas.en(id_lote, dia) or 0

    filas = []
    for galpon in galpones:
        lote = lotes.get(galpon.pk)
        if galpon.estado != Galpon.ESTADO_ACTIVO:
            situacion = "I"
        elif lote is None:
            situacion = "S"
        else:
            situacion = lote.estado  # "P" o "T"
        postura = postura_fecha = None
        dias = por_galpon.get(galpon.pk)
        if dias:
            ultimo = max(dias)
            postura = postura_del_dia(*dias[ultimo])
            postura = round(postura, 1) if postura is not None else None
            postura_fecha = ultimo.isoformat() if postura is not None else None
        filas.append(
            {
                "id_galpon": galpon.pk,
                "galpon": galpon.galpon,
                "estado": situacion,
                "lote": lote.codigo if lote else None,
                "gallinas": lote.cantidad_actual if lote else None,
                "postura": postura,
                "postura_fecha": postura_fecha,
                "alerta": galpon.pk in ids_con_alerta,
            }
        )
    filas.sort(key=lambda f: _orden_natural(f["galpon"]))
    return filas


def _stock_productos():
    """
    Stock de cada producto y su peso en el total.

    Se muestran los productos activos y, además, los que están inactivos pero
    todavía tienen existencias: esconderlos haría que el total no cierre.
    """
    items = []
    for producto in anotar_stock().order_by("producto"):
        stock = stock_actual(producto)
        if producto.estado != Producto.ESTADO_ACTIVO and stock == 0:
            continue
        items.append(
            {
                "id_producto": producto.pk,
                "producto": producto.producto,
                "descripcion": producto.descripcion,
                "estado": producto.estado,
                "stock": stock,
            }
        )
    # El porcentaje se reparte entre lo que suma: un stock negativo (una carga
    # mal hecha) no puede comerse la porción de los demás.
    total_positivo = sum(item["stock"] for item in items if item["stock"] > 0)
    for item in items:
        item["porcentaje"] = (
            round(item["stock"] / total_positivo * 100, 1)
            if total_positivo and item["stock"] > 0
            else 0
        )
    return {"total": sum(item["stock"] for item in items), "items": items}


def _pendientes(usuario):
    """
    Cuántos registros siguen sin finalizar en cada módulo que ve el usuario.

    Es lo que tiene a medio hacer: una recolección cargada que todavía no
    sumó stock, una compra que no se cerró. El Operario cuenta solo los de sus
    galpones asignados (F-32) y no recibe las compras, porque no tiene esa
    sección.
    """
    pendientes = {
        "recolecciones": limitar_a_galpones_asignados(
            Recoleccion.objects.filter(estado=Recoleccion.ESTADO_PENDIENTE), usuario
        ).count(),
        "entradas": limitar_a_galpones_asignados(
            Entrada.objects.filter(estado=Entrada.ESTADO_PENDIENTE), usuario
        ).count(),
        # Los descartes de stock no pertenecen a ningún galpón: los ve cualquiera.
        "descartes": limitar_a_galpones_asignados(
            Descarte.objects.filter(estado=Descarte.ESTADO_PENDIENTE),
            usuario,
            incluir_sin_galpon=True,
        ).count(),
        "salidas": Salida.objects.filter(estado=Salida.ESTADO_PENDIENTE).count(),
    }
    if not es_operario(usuario):
        pendientes["compras"] = Compra.objects.filter(estado=Compra.ESTADO_PENDIENTE).count()
    return pendientes


def _alertas(usuario, ahora):
    """
    Las alertas de la tarjeta: las pendientes y las que se resolvieron hace
    poco (para que se vea que la situación se normalizó).
    """
    visibles = alertas_visibles(usuario)
    desde = ahora - datetime.timedelta(days=DIAS_ALERTAS_RESUELTAS)
    recientes = visibles.filter(
        Q(estado=Alerta.ESTADO_PENDIENTE)
        | Q(estado=Alerta.ESTADO_RESUELTA, fecha_resolucion__gte=desde)
    )[:MAX_ALERTAS]
    pendientes = visibles.filter(estado=Alerta.ESTADO_PENDIENTE)
    # order_by() vacío: el orden de la lista agregaría columnas al GROUP BY y no agruparía por tipo.
    por_tipo = [
        {
            "clave": fila["id_tipo_alerta__clave"],
            "tipo": fila["id_tipo_alerta__nombre"],
            "severidad": fila["id_tipo_alerta__severidad"],
            "cantidad": fila["cantidad"],
        }
        for fila in pendientes.order_by()
        .values("id_tipo_alerta__clave", "id_tipo_alerta__nombre", "id_tipo_alerta__severidad")
        .annotate(cantidad=Count("pk"))
    ]
    # Primero las más urgentes (la severidad "A" va antes que la "M") y, dentro de cada una, las más frecuentes.
    por_tipo.sort(key=lambda t: (t["severidad"], -t["cantidad"], t["tipo"]))
    return {
        "pendientes": pendientes.count(),
        "por_tipo": por_tipo,
        "recientes": list(recientes),
        # Galpones con alguna alerta pendiente: el mapa los marca con un punto.
        "ids_galpones": set(pendientes.order_by().values_list("id_lote__id_galpon", flat=True)),
    }


def resumen(usuario):
    """Todo lo que muestra el panel principal, ya calculado."""
    hoy = timezone.localdate()
    ayer = hoy - datetime.timedelta(days=1)
    ids_galpones = _galpones_visibles(usuario)

    produccion = _produccion(hoy, ids_galpones)
    huevos = {dia["fecha"]: dia["huevos"] for dia in produccion}
    huevos_hoy = huevos.get(hoy.isoformat(), 0)
    huevos_ayer = huevos.get(ayer.isoformat(), 0)

    desde_postura = hoy - datetime.timedelta(days=DIAS_PRODUCCION - 1)
    postura_serie = serie_postura(desde_postura, hoy, ids_galpones=ids_galpones)
    postura = {dia["fecha"]: dia["valor"] for dia in postura_serie}
    postura_hoy = postura.get(hoy.isoformat())
    postura_ayer = postura.get(ayer.isoformat())

    galpones = _galpones(ids_galpones)
    alertas = _alertas(usuario, timezone.now())
    mapa_galpones = _mapa_galpones(usuario, ids_galpones, hoy, alertas["ids_galpones"])
    pendientes = _pendientes(usuario)

    return {
        "fecha": hoy.isoformat(),
        "huevos_hoy": huevos_hoy,
        "huevos_ayer": huevos_ayer,
        "variacion_huevos": _variacion_porcentual(huevos_hoy, huevos_ayer),
        "postura_hoy": postura_hoy,
        "postura_ayer": postura_ayer,
        # La postura se compara en puntos porcentuales, no en porcentaje de
        # porcentaje: de 70% a 72% son 2 puntos.
        "variacion_postura": (
            round(postura_hoy - postura_ayer, 1)
            if postura_hoy is not None and postura_ayer is not None
            else None
        ),
        # Postura de los últimos 7 días (valor = None si ese día no hubo recolección).
        "postura_serie": postura_serie,
        "galpones_activos": galpones["activos"],
        "galpones_en_produccion": galpones["en_produccion"],
        "galpones_en_transicion": galpones["en_transicion"],
        "galpones_sin_lote": galpones["sin_lote"],
        "galpones_inactivos": galpones["inactivos"],
        "gallinas_en_produccion": galpones["gallinas"],
        "mapa_galpones": mapa_galpones,
        "alertas_pendientes": alertas["pendientes"],
        "alertas_por_tipo": alertas["por_tipo"],
        "pendientes": pendientes,
        "pendientes_total": sum(pendientes.values()),
        "produccion": produccion,
        "stock_productos": _stock_productos(),
        "alertas": alertas["recientes"],
    }
