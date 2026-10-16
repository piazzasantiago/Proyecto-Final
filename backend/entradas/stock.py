"""
Impacto de las entradas a galpones en el stock de materias primas.

Solo cuentan las entradas Finalizadas: las pendientes todavía no hicieron
efecto. El stock no se guarda, se calcula (ver descartes/stock.py):
    materia prima:  stock_inicial − descartado − ingresado a galpones
"""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from materias_primas.models import MateriaPrima

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


def existencias_galpon(id_galpon):
    """
    Existencia ESTIMADA de cada materia prima dentro de un galpón.

        ingresado   = entradas finalizadas a ese galpón
        descartado  = descartes de galpón finalizados de esa materia prima
        existencia  = max(ingresado − descartado, 0)

    Es una estimación: el sistema no registra el consumo diario, así que lo que
    comen las gallinas no se resta. El descarte de galpón sigue siendo
    estadístico para el stock general (la materia prima ya salió de ahí al
    finalizar la entrada), pero sí reduce lo que queda en el galpón.

    Devuelve una lista de dicts ordenada por nombre, solo con las materias
    primas que alguna vez ingresaron o se descartaron en el galpón.
    """
    # Import diferido: descartes.stock importa este módulo.
    from descartes.models import Descarte, LineaDescarte

    ingresado = {
        fila["id_materia_prima"]: fila["total"]
        for fila in _lineas_finalizadas()
        .filter(id_entrada__id_galpon=id_galpon)
        .order_by()
        .values("id_materia_prima")
        .annotate(total=Sum("cantidad"))
    }
    descartado = {
        fila["id_materia_prima"]: fila["total"]
        for fila in LineaDescarte.objects.filter(
            id_descarte__categoria=Descarte.CATEGORIA_GALPON,
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            id_descarte__id_galpon=id_galpon,
            id_materia_prima__isnull=False,
        )
        .order_by()
        .values("id_materia_prima")
        .annotate(total=Sum("cantidad"))
    }

    ids = set(ingresado) | set(descartado)
    filas = []
    for mp in MateriaPrima.objects.filter(pk__in=ids).order_by("materia_prima"):
        entro = ingresado.get(mp.pk, Decimal("0"))
        se_descarto = descartado.get(mp.pk, Decimal("0"))
        filas.append(
            {
                "id_materia_prima": mp.pk,
                "materia_prima": mp.materia_prima,
                "unidad": mp.unidad,
                "ingresado": entro,
                "descartado": se_descarto,
                "existencia_estimada": max(entro - se_descarto, Decimal("0")),
            }
        )
    return filas
