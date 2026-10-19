"""
Impacto de las compras en el stock de materias primas y lotes pendientes.

Solo cuentan las compras Finalizadas de materias primas: las pendientes
todavía no hicieron efecto. El stock no se guarda, se calcula (ver
descartes/stock.py):
    materia prima:  stock_inicial + comprado − descartado − ingresado a galpones
"""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import Compra, LineaCompra

_DECIMAL = DecimalField(max_digits=12, decimal_places=2)


def _lineas_materia_prima_finalizadas():
    return LineaCompra.objects.filter(
        id_compra__categoria=Compra.CATEGORIA_MATERIAS_PRIMAS,
        id_compra__estado=Compra.ESTADO_FINALIZADA,
    )


def comprado_materia_prima(id_materia_prima):
    """Total comprado de la materia prima en compras finalizadas."""
    total = (
        _lineas_materia_prima_finalizadas()
        .filter(id_materia_prima=id_materia_prima)
        .aggregate(total=Sum("cantidad"))["total"]
    )
    return total or Decimal("0")


def anotar_comprado(queryset):
    """
    Agrega `stock_compras` a un queryset de MateriaPrima con una subconsulta
    (una sola consulta para todo el listado, sin multiplicar filas).
    """
    subconsulta = (
        _lineas_materia_prima_finalizadas()
        .filter(id_materia_prima=OuterRef("pk"))
        .order_by()
        .values("id_materia_prima")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    return queryset.annotate(
        stock_compras=Coalesce(
            Subquery(subconsulta, output_field=_DECIMAL),
            Value(Decimal("0")),
            output_field=_DECIMAL,
        )
    )


def lotes_pendientes_de_asignar():
    """
    Líneas de compras de lotes finalizadas cuyo lote todavía no se asignó a un
    galpón (no tienen un Lote creado). Las más antiguas primero.
    """
    return (
        LineaCompra.objects.filter(
            id_compra__categoria=Compra.CATEGORIA_LOTES,
            id_compra__estado=Compra.ESTADO_FINALIZADA,
            id_lote__isnull=True,
        )
        .select_related("id_compra", "id_compra__id_proveedor")
        .order_by("id_compra__fecha", "id_compra_id", "id_linea_compra")
    )
