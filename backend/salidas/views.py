from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from descartes.stock import verificar_stock
from productos.models import Producto
from usuarios.permissions import EsAdministradorOOperario

from config.pagination import PaginacionListado
from .models import Salida
from .serializers import SalidaSerializer
from config.auditoria import AuditoriaMixin


class SalidaFilter(django_filters.FilterSet):
    """
    Filtros del listado:
        ?fecha_desde=AAAA-MM-DD   salidas desde ese día (inclusive)
        ?fecha_hasta=AAAA-MM-DD   salidas hasta ese día (inclusive)
        ?estado=P|F               Pendiente o Finalizada
        ?id_producto=N            que incluyan ese producto
    El día se toma en el horario local del sistema (settings.TIME_ZONE).
    """

    fecha_desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")
    id_producto = django_filters.NumberFilter(
        field_name="lineas__id_producto", distinct=True
    )

    class Meta:
        model = Salida
        fields = ["estado"]


class SalidaViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD de salidas de productos + acción /finalizar/.

    Buscar salidas     → GET    /api/salidas/
    Nueva salida       → POST   /api/salidas/
    Modificar salida   → PATCH/PUT /api/salidas/{id}/
    Borrar salida      → DELETE /api/salidas/{id}/
    Finalizar salida   → POST   /api/salidas/{id}/finalizar/
    Líneas             → van anidadas en `lineas` de la salida.

    Permisos:
        - Administrador y Operario: CRUD + finalizar.
        - Consulta: solo lectura (list + retrieve).
        - Sin token: 401.
    """

    queryset = (
        Salida.objects.select_related("id_usuario")
        .prefetch_related("lineas__id_producto")
        .all()
    )
    serializer_class = SalidaSerializer
    pagination_class = PaginacionListado
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = SalidaFilter

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [EsAdministradorOOperario()]

    def perform_create(self, serializer):
        """El usuario autenticado queda como responsable de la carga."""
        serializer.save(id_usuario=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Una salida finalizada ya descontó stock; borrarla dejaría ese número
        sin el registro que lo respalda. Solo se eliminan las pendientes.
        """
        salida = self.get_object()
        if salida.estado == Salida.ESTADO_FINALIZADA:
            return Response(
                {"detail": "No se puede eliminar una salida finalizada."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="finalizar")
    def finalizar(self, request, pk=None):
        """
        Finaliza una salida pendiente y descuenta el stock.

        Verifica de nuevo que alcance el stock de cada producto (entre la carga
        y la finalización pudo cambiar). Si no alcanza devuelve 400 y no cambia
        nada. Si alcanza, el stock se recalcula solo al quedar Finalizada.
        Todo ocurre en una transacción, con la fila bloqueada: dos
        finalizaciones simultáneas no descuentan dos veces.
        """
        with transaction.atomic():
            salida = Salida.objects.select_for_update().get(pk=self.get_object().pk)

            if salida.estado == Salida.ESTADO_FINALIZADA:
                return Response(
                    {"detail": "La salida ya está finalizada."},
                    status=status.HTTP_409_CONFLICT,
                )

            lineas = list(salida.lineas.all())
            # Se bloquean los productos (en orden de id) para que dos salidas
            # que usan el mismo no pasen la verificación a la vez.
            ids = sorted(l.id_producto_id for l in lineas)
            bloqueados = {
                p.pk: p
                for p in Producto.objects.select_for_update()
                .filter(pk__in=ids)
                .order_by("pk")
            }
            error = verificar_stock(
                [(bloqueados[l.id_producto_id], l.cantidad) for l in lineas],
                accion="despachar",
            )
            if error:
                raise ValidationError({"detail": error})

            salida.estado = Salida.ESTADO_FINALIZADA
            salida.save(update_fields=["estado"])

        return Response(self.get_serializer(salida).data, status=status.HTTP_200_OK)
