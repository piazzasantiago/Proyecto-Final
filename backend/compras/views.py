from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from usuarios.permissions import LecturaAdministradorYConsulta_EscrituraAdministrador

from config.pagination import PaginacionListado
from .models import Compra
from .serializers import CompraSerializer, LotePendienteSerializer
from .stock import lotes_pendientes_de_asignar


class CompraFilter(django_filters.FilterSet):
    """
    Filtros del listado:
        ?fecha_desde=AAAA-MM-DD   compras desde ese día (inclusive)
        ?fecha_hasta=AAAA-MM-DD   compras hasta ese día (inclusive)
        ?estado=P|F               Pendiente o Finalizada
        ?categoria=M|L            Materias primas o Lotes
        ?id_proveedor=N           de ese proveedor
        ?search=...               por número de factura
    """

    fecha_desde = django_filters.DateFilter(field_name="fecha", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="lte")

    class Meta:
        model = Compra
        fields = ["estado", "categoria", "id_proveedor"]


class CompraViewSet(viewsets.ModelViewSet):
    """
    CRUD de compras a proveedores + acción /finalizar/.

    Buscar compras     → GET    /api/compras/
    Nueva compra       → POST   /api/compras/
    Modificar compra   → PATCH  /api/compras/{id}/
    Borrar compra      → DELETE /api/compras/{id}/
    Finalizar compra   → POST   /api/compras/{id}/finalizar/
    Lotes a asignar    → GET    /api/compras/lotes-pendientes/
    Líneas             → van anidadas en `lineas` de la compra.

    Permisos:
        - Administrador: CRUD + finalizar.
        - Consulta: solo lectura.
        - Operario: sin acceso a la sección. Única excepción: la lista de lotes
          a asignar, que ven todos los usuarios autenticados porque la pantalla
          de Lotes (visible para todos) avisa cuando hay uno esperando.
        - Sin token: 401.
    """

    queryset = (
        Compra.objects.select_related("id_proveedor", "id_usuario")
        .prefetch_related("lineas__id_materia_prima", "lineas__id_lote")
        .all()
    )
    serializer_class = CompraSerializer
    permission_classes = [LecturaAdministradorYConsulta_EscrituraAdministrador]
    pagination_class = PaginacionListado
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CompraFilter
    search_fields = ["nro_factura"]
    ordering_fields = ["fecha", "nro_factura"]

    def get_permissions(self):
        if self.action == "lotes_pendientes":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """El usuario autenticado queda como responsable de la carga."""
        serializer.save(id_usuario=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Una compra finalizada ya sumó stock o dejó lotes esperando un galpón;
        borrarla dejaría ese efecto sin el registro que lo respalda. Solo se
        eliminan las pendientes.
        """
        compra = self.get_object()
        if compra.estado == Compra.ESTADO_FINALIZADA:
            return Response(
                {"detail": "No se puede eliminar una compra finalizada."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="finalizar")
    def finalizar(self, request, pk=None):
        """
        Finaliza una compra pendiente.

        · Materias primas: el stock de cada materia prima se recalcula solo al
          quedar Finalizada (suma lo comprado).
        · Lotes: cada línea queda como lote a asignar a un galpón.

        Todo ocurre en una transacción, con la fila bloqueada: dos
        finalizaciones simultáneas no cuentan dos veces.
        """
        with transaction.atomic():
            compra = Compra.objects.select_for_update().get(pk=self.get_object().pk)

            if compra.estado == Compra.ESTADO_FINALIZADA:
                return Response(
                    {"detail": "La compra ya está finalizada."},
                    status=status.HTTP_409_CONFLICT,
                )

            compra.estado = Compra.ESTADO_FINALIZADA
            compra.save(update_fields=["estado"])

        return Response(self.get_serializer(compra).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="lotes-pendientes")
    def lotes_pendientes(self, request):
        """
        Lotes comprados (compras finalizadas) que todavía no se asignaron a un
        galpón. Alimenta el cartel y el combo "Lotes a asignar" de Lotes.
        """
        datos = LotePendienteSerializer(lotes_pendientes_de_asignar(), many=True).data
        return Response(datos)
