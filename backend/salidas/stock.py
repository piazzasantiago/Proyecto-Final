"""
Impacto de las salidas de productos en el stock de productos.

Solo cuentan las salidas Finalizadas: las pendientes todavía no hicieron
efecto. El stock no se guarda, se calcula (ver descartes/stock.py):
    producto:  stock_inicial + recolectado − descartado − salidas
"""

from django.db.models import IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import LineaSalida, Salida


def _lineas_finalizadas():
    return LineaSalida.objects.filter(id_salida__estado=Salida.ESTADO_FINALIZADA)


def egresado_producto(id_producto):
    """Total del producto que salió de la granja en salidas finalizadas."""
    total = (
        _lineas_finalizadas()
        .filter(id_producto=id_producto)
        .aggregate(total=Sum("cantidad"))["total"]
    )
    return total or 0


def anotar_egresado(queryset):
    """
    Agrega `stock_salidas` a un queryset de Producto con una subconsulta (una
    sola consulta para todo el listado). Se usa una subconsulta y no un Sum con
    JOIN para no multiplicar las filas del Sum de recolecciones que ya anota
    ProductoViewSet.
    """
    subconsulta = (
        _lineas_finalizadas()
        .filter(id_producto=OuterRef("pk"))
        .order_by()
        .values("id_producto")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    return queryset.annotate(
        stock_salidas=Coalesce(
            Subquery(subconsulta, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
    )
