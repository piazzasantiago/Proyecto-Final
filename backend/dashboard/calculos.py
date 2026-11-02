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
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from alertas.views import alertas_visibles
from alertas.models import Alerta
from compras.models import Compra
from descartes.models import Descarte
from entradas.models import Entrada
from galpones.acceso import es_operario, ids_galpones_asignados, limitar_a_galpones_asignados
from galpones.models import Galpon
from informes.calculos import dias_del_periodo, serie_postura, huevos_por_lote_y_dia
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
    """Galpones activos y cuántos de ellos tienen un lote en producción."""
    galpones = Galpon.objects.filter(estado=Galpon.ESTADO_ACTIVO)
    if ids_galpones is not None:
        galpones = galpones.filter(pk__in=ids_galpones)
    return {
        "activos": galpones.count(),
        "en_produccion": galpones.filter(lotes__estado=Lote.ESTADO_PRODUCCION)
        .distinct()
        .count(),
    }


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
    return {
        "pendientes": visibles.filter(estado=Alerta.ESTADO_PENDIENTE).count(),
        "recientes": list(recientes),
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

    postura = {
        dia["fecha"]: dia["valor"]
        for dia in serie_postura(ayer, hoy, ids_galpones=ids_galpones)
    }
    postura_hoy = postura.get(hoy.isoformat())
    postura_ayer = postura.get(ayer.isoformat())

    galpones = _galpones(ids_galpones)
    alertas = _alertas(usuario, timezone.now())
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
        "galpones_activos": galpones["activos"],
        "galpones_en_produccion": galpones["en_produccion"],
        "alertas_pendientes": alertas["pendientes"],
        "pendientes": pendientes,
        "pendientes_total": sum(pendientes.values()),
        "produccion": produccion,
        "stock_productos": _stock_productos(),
        "alertas": alertas["recientes"],
    }
