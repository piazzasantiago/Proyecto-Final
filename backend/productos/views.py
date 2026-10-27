from django.db.models import ProtectedError, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

from config.pagination import PaginacionListado
from .models import Producto
from .serializers import ProductoSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Productos más acciones de cambio de estado.

    CU50  GET    /api/productos/                listar (con ?search=, ?estado=, ?ordering=)
    CU50  GET    /api/productos/{id}/           detalle
    CU49  POST   /api/productos/                crear
    CU52  PATCH  /api/productos/{id}/           modificar
    CU53  DELETE /api/productos/{id}/           eliminar
    CU51  POST   /api/productos/{id}/activar/   activar (Inactivo → Activo)
    CU54  POST   /api/productos/{id}/desactivar/ desactivar (Activo → Inactivo)

    Permisos: consultar requiere estar autenticado con cualquier rol; crear,
    modificar y eliminar requiere rol Administrador. Mismo patrón que
    GalponViewSet.

    Stock: stock_inicial se edita como un campo más (alta/modificación), a
    cargo del Administrador. stock_recolectado y stock_actual son de solo
    lectura y se calculan: stock_actual = stock_inicial + lo recolectado en
    recolecciones finalizadas - lo descartado en descartes de stock finalizados
    - lo que salió en salidas finalizadas.
    """

    queryset = Producto.objects.all()  # get_queryset() agrega el stock recolectado
    serializer_class = ProductoSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    pagination_class = PaginacionListado
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["producto", "descripcion"]
    ordering_fields = ["producto"]

    def get_queryset(self):
        """
        Anota cada producto con lo recolectado en recolecciones FINALIZADAS
        (stock_recolectado), lo descartado en descartes de stock FINALIZADOS
        (stock_descartado) y lo que salió en salidas FINALIZADAS
        (stock_salidas), para calcular el stock actual sin una consulta
        por producto.
        """
        # Import diferido: recolecciones, descartes y salidas dependen de
        # productos, no al revés.
        from descartes.stock import anotar_descartado
        from recolecciones.models import Recoleccion
        from salidas.stock import anotar_egresado

        productos = Producto.objects.annotate(
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
        # Descartes y salidas se suman con subconsultas (no con otro JOIN) para
        # no multiplicar las filas del Sum de recolecciones.
        productos = anotar_descartado(productos, "id_producto")
        productos = anotar_egresado(productos)
        # Al agrupar por el Sum, Django ignora el orden por defecto del modelo;
        # sin un orden explícito la paginación podría repetir o saltear filas.
        # (?ordering= lo reemplaza cuando se pide otro orden.)
        return productos.order_by("producto")

    def destroy(self, request, *args, **kwargs):
        """
        CU53 — Un producto con registros asociados (recolecciones, descartes o
        salidas) no se borra: se responde 409 con un mensaje claro y se sugiere
        desactivarlo para conservar el historial.
        """
        producto = self.get_object()
        try:
            producto.delete()
        except ProtectedError as error:
            presentes = sorted(
                {str(o._meta.verbose_name_plural) for o in error.protected_objects}
            )
            detalle = ", ".join(presentes)
            return Response(
                {
                    "detail": (
                        "No se puede eliminar el producto porque tiene registros asociados"
                        + (f" ({detalle})" if detalle else "")
                        + ". Desactivalo en su lugar para conservar el historial."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        producto = self.get_object()
        serializer = self.get_serializer(producto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response(ProductoSerializer(producto).data)

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """CU51 — Activar un producto (Inactivo → Activo)."""
        producto = self.get_object()
        if producto.estado == Producto.ESTADO_ACTIVO:
            return Response(
                {"detail": "El producto ya se encuentra activo."},
                status=status.HTTP_409_CONFLICT,
            )
        producto.estado = Producto.ESTADO_ACTIVO
        producto.save(update_fields=["estado"])
        return Response(ProductoSerializer(producto).data)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """CU54 — Desactivar un producto (Activo → Inactivo)."""
        producto = self.get_object()
        if producto.estado == Producto.ESTADO_INACTIVO:
            return Response(
                {"detail": "El producto ya se encuentra inactivo."},
                status=status.HTTP_409_CONFLICT,
            )
        producto.estado = Producto.ESTADO_INACTIVO
        producto.save(update_fields=["estado"])
        return Response(ProductoSerializer(producto).data)
