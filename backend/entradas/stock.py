"""
Impacto de las entradas a galpones en el stock de materias primas.

Solo cuentan las entradas Finalizadas: las pendientes todavía no hicieron
efecto. El stock no se guarda, se calcula (ver descartes/stock.py):
    materia prima:  stock_inicial − descartado − ingresado a galpones
"""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import Entrada, LineaEntrada

_DECIMAL = DecimalField(max_digits=12, decimal_places=2)


def _lineas_finalizadas():
    return LineaEntrada.objects.filter(id_entrada__estado=Entrada.ESTADO_FINALIZADA)


def ingresado_materia_prima(id_materia_prima):
    """Total de la materia prima que salió a galpones en entradas finalizadas."""
    total = (
        _lineas_finalizadas()
        .filter(id_materia_prima=id_materia_prima)
        .aggregate(total=Sum("cantidad"))["total"]
    )
    return total or Decimal("0")


def anotar_ingresado(queryset):
    """
    Agrega `stock_entradas` a un queryset de MateriaPrima con una subconsulta
    (una sola consulta para todo el listado, sin multiplicar filas).
    """
    subconsulta = (
        _lineas_finalizadas()
        .filter(id_materia_prima=OuterRef("pk"))
        .order_by()
        .values("id_materia_prima")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    return queryset.annotate(
        stock_entradas=Coalesce(
            Subquery(subconsulta, output_field=_DECIMAL),
            Value(Decimal("0")),
            output_field=_DECIMAL,
        )
    )
