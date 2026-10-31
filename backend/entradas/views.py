from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from descartes.stock import verificar_stock
from materias_primas.models import MateriaPrima
from usuarios.permissions import EsAdministradorOOperario

from config.pagination import PaginacionListado
from galpones.acceso import limitar_a_galpones_asignados, validar_galpon_asignado
from .models import Entrada
from .serializers import EntradaSerializer
from config.auditoria import AuditoriaMixin


class EntradaFilter(django_filters.FilterSet):
    """
    Filtros del listado:
        ?fecha_desde=AAAA-MM-DD   entradas desde ese día (inclusive)
        ?fecha_hasta=AAAA-MM-DD   entradas hasta ese día (inclusive)
        ?estado=P|F               Pendiente o Finalizada
        ?id_galpon=N              de un galpón en particular
        ?id_materia_prima=N       que incluyan esa materia prima
    El día se toma en el horario local del sistema (settings.TIME_ZONE).
    """

    fecha_desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")
    id_materia_prima = django_filters.NumberFilter(
        field_name="lineas__id_materia_prima", distinct=True
    )

    class Meta:
        model = Entrada
        fields = ["estado", "id_galpon"]


class EntradaViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD de entradas a galpones + acción /finalizar/.

    CU33 Buscar avanzado entradas → GET    /api/entradas/
    CU35 Nueva entrada            → POST   /api/entradas/
    CU36 Modificar entrada        → PATCH/PUT /api/entradas/{id}/
    CU34 Borrar entrada           → DELETE /api/entradas/{id}/
    CU37 Finalizar entrada        → POST   /api/entradas/{id}/finalizar/
    CU38–CU41 (líneas)            → van anidadas en `lineas` de la entrada.

    Permisos:
        - Administrador y Operario: CRUD + finalizar.
        - Consulta: solo lectura (list + retrieve).
        - Sin token: 401.
        - El Operario solo ve y trabaja con las entradas de los galpones que tiene
          asignados (F-32); las de otros galpones no se listan y devuelven 404.
    """

    queryset = (
        Entrada.objects.select_related("id_galpon", "id_usuario")
        .prefetch_related("lineas__id_materia_prima")
        .all()
    )
    serializer_class = EntradaSerializer
    pagination_class = PaginacionListado
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = EntradaFilter

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [EsAdministradorOOperario()]

    def get_queryset(self):
        return limitar_a_galpones_asignados(super().get_queryset(), self.request.user)

    def perform_create(self, serializer):
        """El usuario autenticado queda como responsable de la carga."""
        validar_galpon_asignado(self.request.user, serializer.validated_data.get("id_galpon"))
        serializer.save(id_usuario=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Una entrada finalizada ya descontó stock; borrarla dejaría ese número
        sin el registro que lo respalda. Solo se eliminan las pendientes.
        """
        entrada = self.get_object()
        if entrada.estado == Entrada.ESTADO_FINALIZADA:
            return Response(
                {"detail": "No se puede eliminar una entrada finalizada."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="finalizar")
    def finalizar(self, request, pk=None):
        """
        CU37 — Finaliza una entrada pendiente y descuenta el stock.

        Verifica de nuevo que alcance el stock de cada materia prima (entre la
        carga y la finalización pudo cambiar). Si no alcanza devuelve 400 y no
        cambia nada. Si alcanza, el stock se recalcula solo al quedar Finalizada.
        Todo ocurre en una transacción, con la fila bloqueada: dos
        finalizaciones simultáneas no descuentan dos veces.
        """
        with transaction.atomic():
            entrada = Entrada.objects.select_for_update().get(pk=self.get_object().pk)

            if entrada.estado == Entrada.ESTADO_FINALIZADA:
                return Response(
                    {"detail": "La entrada ya está finalizada."},
                    status=status.HTTP_409_CONFLICT,
                )

            lineas = list(entrada.lineas.all())
            # Se bloquean las materias primas (en orden de id) para que dos
            # entradas que usan la misma no pasen la verificación a la vez.
            ids = sorted(l.id_materia_prima_id for l in lineas)
            bloqueadas = {
                mp.pk: mp
                for mp in MateriaPrima.objects.select_for_update()
                .filter(pk__in=ids)
                .order_by("pk")
            }
            error = verificar_stock(
                [(bloqueadas[l.id_materia_prima_id], l.cantidad) for l in lineas],
                accion="ingresar",
            )
            if error:
                raise ValidationError({"detail": error})

            entrada.estado = Entrada.ESTADO_FINALIZADA
            entrada.save(update_fields=["estado"])

        return Response(self.get_serializer(entrada).data, status=status.HTTP_200_OK)
