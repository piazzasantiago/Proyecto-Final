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


def existencias_galpon(id_galpon):
    """
    Existencia ESTIMADA de cada materia prima dentro de un galpón.

        existencia = max(último ingreso − descartes de galpón posteriores, 0)

    - Último ingreso: la línea de la entrada Finalizada más reciente de esa
      materia prima en el galpón. Se supone que la carga anterior ya se
      consumió; sumar todos los ingresos daría un número cada vez más alejado
      de la realidad, porque el sistema no registra el consumo diario.
    - Descartes posteriores: líneas de descartes de categoría Galpón
      Finalizados, de esa materia prima y ese galpón, con fecha posterior a la
      de la entrada. Los anteriores se refieren a la carga anterior.

    Es una cota superior: no resta lo que las gallinas consumieron. El descarte
    de galpón sigue siendo estadístico para el stock general (la materia prima
    ya salió de ahí al finalizar la entrada).

    Devuelve una lista de dicts ordenada por nombre, solo con las materias
    primas que ingresaron alguna vez al galpón.
    """
    # Import diferido: descartes.stock importa este módulo.
    from descartes.models import Descarte, LineaDescarte

    # Última línea finalizada por materia prima (la de fecha más reciente).
    ultimos = {}
    for linea in (
        _lineas_finalizadas()
        .filter(id_entrada__id_galpon=id_galpon)
        .select_related("id_entrada", "id_materia_prima")
        .order_by("-id_entrada__fecha", "-id_entrada__id_entrada", "-id_linea_entrada")
    ):
        ultimos.setdefault(linea.id_materia_prima_id, linea)
    if not ultimos:
        return []

    descartes = list(
        LineaDescarte.objects.filter(
            id_descarte__categoria=Descarte.CATEGORIA_GALPON,
            id_descarte__estado=Descarte.ESTADO_FINALIZADO,
            id_descarte__id_galpon=id_galpon,
            id_materia_prima__in=list(ultimos),
        ).values_list("id_materia_prima", "id_descarte__fecha", "cantidad")
    )

    filas = []
    for id_mp, linea in ultimos.items():
        fecha_ingreso = linea.id_entrada.fecha
        descartado = sum(
            (cant for mp, fecha, cant in descartes if mp == id_mp and fecha > fecha_ingreso),
            Decimal("0"),
        )
        mp = linea.id_materia_prima
        filas.append(
            {
                "id_materia_prima": mp.pk,
                "materia_prima": mp.materia_prima,
                "unidad": mp.unidad,
                "ultimo_ingreso_fecha": fecha_ingreso,
                "ultimo_ingreso": linea.cantidad,
                "descartado_desde_entonces": descartado,
                "existencia_estimada": max(linea.cantidad - descartado, Decimal("0")),
            }
        )
    filas.sort(key=lambda f: f["materia_prima"].lower())
    return filas
