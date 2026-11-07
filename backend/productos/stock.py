"""
Stock de productos.

El stock no se guarda en la base: se calcula a partir de los movimientos
registrados, y siempre con la misma fórmula:

    stock_actual = stock_inicial
                 + recolectado  (recolecciones finalizadas)
                 - descartado   (descartes de stock finalizados)
                 - salidas      (salidas finalizadas)

Los registros pendientes todavía no hicieron efecto, así que no cuentan.

Este módulo deja la fórmula en un solo lugar: la usan el listado de productos
(ProductoViewSet) y el dashboard.
"""

from django.db.models import IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import Producto


def anotar_stock(queryset=None):
    """
    Anota `stock_recolectado`, `stock_descartado` y `stock_salidas` en un
    queryset de Producto, con una sola consulta para todo el listado.

    Las tres sumas son subconsultas correlacionadas (una por producto) y no un
    JOIN con GROUP BY. Con el JOIN, el GROUP BY arrastraba también las
    subconsultas de descartes y salidas, y PostgreSQL las ejecutaba una vez por
    cada línea de recolección en lugar de una vez por producto: el costo crecía
    con todo el historial y hacía lento el listado de productos y el panel.
    """
    # Imports diferidos: recolecciones, descartes y salidas dependen de
    # productos, no al revés.
    from descartes.stock import anotar_descartado
    from recolecciones.models import LineaRecoleccion, Recoleccion
    from salidas.stock import anotar_egresado

    recolectado = (
        LineaRecoleccion.objects.filter(
            id_producto=OuterRef("pk"),
            id_recoleccion__estado=Recoleccion.ESTADO_FINALIZADA,
        )
        .order_by()
        .values("id_producto")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    productos = (Producto.objects.all() if queryset is None else queryset).annotate(
        stock_recolectado=Coalesce(
            Subquery(recolectado, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
    )
    productos = anotar_descartado(productos, "id_producto")
    return anotar_egresado(productos)


def stock_actual(producto):
    """Stock de un producto ya anotado con `anotar_stock`."""
    return (
        producto.stock_inicial
        + int(producto.stock_recolectado or 0)
        - int(producto.stock_descartado or 0)
        - int(producto.stock_salidas or 0)
    )
