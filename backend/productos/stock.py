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

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from .models import Producto


def anotar_stock(queryset=None):
    """
    Anota `stock_recolectado`, `stock_descartado` y `stock_salidas` en un
    queryset de Producto, con una sola consulta para todo el listado.
    """
    # Imports diferidos: recolecciones, descartes y salidas dependen de
    # productos, no al revés.
    from descartes.stock import anotar_descartado
    from recolecciones.models import Recoleccion
    from salidas.stock import anotar_egresado

    productos = (Producto.objects.all() if queryset is None else queryset).annotate(
        stock_recolectado=Coalesce(
            Sum(
                "lineas_recoleccion__cantidad",
                filter=Q(
                    lineas_recoleccion__id_recoleccion__estado=Recoleccion.ESTADO_FINALIZADA
                ),
            ),
            0,
        )
    )
    # Descartes y salidas se suman con subconsultas (no con otro JOIN) para no
    # multiplicar las filas del Sum de recolecciones.
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
