from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

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
    """

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["producto", "descripcion"]
    ordering_fields = ["producto"]

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
