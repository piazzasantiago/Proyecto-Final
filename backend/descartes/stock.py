"""
Cálculo del impacto de los descartes de STOCK en el stock de productos y de
materias primas.

Solo cuentan los descartes de categoría Stock y estado Finalizado: los
descartes de galpón son estadísticos y los pendientes todavía no hicieron
efecto.

El stock no se guarda: se calcula (igual que el de recolecciones) como
    producto:        stock_inicial + recolectado - descartado - salidas
    materia prima:   stock_inicial + comprado - descartado - ingresado a galpones
                     (compras y entradas)
"""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import Descarte, LineaDescarte

_DECIMAL = DecimalField(max_digits=12, decimal_places=2)


def _lineas_de_stock_finalizadas():
    return LineaDescarte.objects.filter(
        id_descarte__categoria=Descarte.CATEGORIA_STOCK,
        id_descarte__estado=Descarte.ESTADO_FINALIZADO,
    )


def descartado_producto(id_producto):
    total = (
        _lineas_de_stock_finalizadas()
        .filter(id_producto=id_producto)
        .aggregate(total=Sum("cantidad"))["total"]
    )
    return total or Decimal("0")


def descartado_materia_prima(id_materia_prima):
    total = (
        _lineas_de_stock_finalizadas()
        .filter(id_materia_prima=id_materia_prima)
        .aggregate(total=Sum("cantidad"))["total"]
    )
    return total or Decimal("0")


def anotar_descartado(queryset, campo_fk):
    """
    Agrega `stock_descartado` a un queryset de Producto o MateriaPrima con una
    subconsulta (una sola consulta para todo el listado). Se usa una
    subconsulta y no un Sum con JOIN para no multiplicar las filas del Sum de
    recolecciones que ya anota ProductoViewSet.

    campo_fk: "id_producto" o "id_materia_prima".
    """
    subconsulta = (
        _lineas_de_stock_finalizadas()
        .filter(**{campo_fk: OuterRef("pk")})
        .order_by()
        .values(campo_fk)
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    return queryset.annotate(
        stock_descartado=Coalesce(
            Subquery(subconsulta, output_field=_DECIMAL),
            Value(Decimal("0")),
            output_field=_DECIMAL,
        )
    )


def stock_actual_producto(producto):
    # Imports diferidos: recolecciones y salidas dependen de productos, no al
    # revés (y salidas.serializers importa este módulo).
    from recolecciones.models import LineaRecoleccion, Recoleccion
    from salidas.stock import egresado_producto

    recolectado = (
        LineaRecoleccion.objects.filter(
            id_producto=producto,
            id_recoleccion__estado=Recoleccion.ESTADO_FINALIZADA,
        ).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )
    return (
        producto.stock_inicial
        + recolectado
        - int(descartado_producto(producto.pk))
        - egresado_producto(producto.pk)
    )


def stock_actual_materia_prima(materia_prima):
    # Imports diferidos: compras y entradas dependen de materias primas y de
    # este módulo.
    from compras.stock import comprado_materia_prima
    from entradas.stock import ingresado_materia_prima

    return (
        materia_prima.stock_inicial
        + comprado_materia_prima(materia_prima.pk)
        - descartado_materia_prima(materia_prima.pk)
        - ingresado_materia_prima(materia_prima.pk)
    )


def _formatear(numero):
    return format(Decimal(numero).normalize(), "f")


def verificar_stock(items, accion="descartar"):
    """
    Comprueba que alcance el stock para descartar.

    items: iterable de (objeto, cantidad) donde objeto es un Producto o una
    MateriaPrima. Si un mismo ítem aparece en varias líneas se suman.
    accion: verbo para el mensaje de error ("descartar", "ingresar", …).

    Devuelve un mensaje de error en español, o None si alcanza para todo.
    """
    # Import diferido: evita ciclos al importar los modelos de otras apps.
    from materias_primas.models import MateriaPrima
    from productos.models import Producto

    pedidos = {}
    for objeto, cantidad in items:
        clave = (type(objeto), objeto.pk)
        previo = pedidos.get(clave, (objeto, Decimal("0")))[1]
        pedidos[clave] = (objeto, previo + Decimal(cantidad))

    for objeto, pedido in pedidos.values():
        if isinstance(objeto, Producto):
            disponible = stock_actual_producto(objeto)
            nombre = objeto.producto
        elif isinstance(objeto, MateriaPrima):
            disponible = stock_actual_materia_prima(objeto)
            nombre = objeto.materia_prima
        else:  # pragma: no cover - no debería ocurrir
            continue
        if pedido > Decimal(disponible):
            return (
                f"Stock insuficiente de '{nombre}': hay {_formatear(disponible)} "
                f"en stock y se quieren {accion} {_formatear(pedido)}."
            )
    return None
