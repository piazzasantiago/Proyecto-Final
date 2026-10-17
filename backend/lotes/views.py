import datetime

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.models import Usuario
from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

from .models import Lote
from .serializers import LoteSerializer


class LoteViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Lotes más acciones de cambio de estado.

    CU42  GET    /api/lotes/                        listar (con ?search=, ?estado=, ?id_galpon=)
    CU42  GET    /api/lotes/{id}/                   detalle
    CU43  POST   /api/lotes/                        crear (incluye plan de transición);
                                                    exige un lote comprado a asignar
                                                    (id_linea_compra, ver Compras)
    CU44  PATCH  /api/lotes/{id}/                   modificar
    CU45  DELETE /api/lotes/{id}/                   eliminar
    CU46  POST   /api/lotes/{id}/iniciar-produccion/ Transición → Producción
    CU48  POST   /api/lotes/{id}/vaciar/             cualquier estado → Finalizado + fecha_vaciado

    Permisos: leer requiere autenticación con cualquier rol; crear, modificar
    y eliminar requiere rol Administrador.

    Filtrado por rol:
    - Administrador y Consulta: ven todos los lotes.
    - Operario: ve solo los lotes de los galpones que tiene asignados.
      Si no tiene galpones asignados, recibe lista vacía.
    """

    serializer_class = LoteSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "id_galpon"]
    search_fields = ["id_lote"]
    ordering_fields = ["fecha_ingreso", "cantidad_inicial", "cantidad_actual"]

    def get_queryset(self):
        usuario = self.request.user
        qs = Lote.objects.select_related(
            "id_galpon", "plan_transicion", "linea_compra__id_compra__id_proveedor"
        )
        if usuario.rol == Usuario.ROL_OPERARIO:
            # El operario solo ve los lotes de los galpones que tiene asignados
            return qs.filter(
                id_galpon__operarios_asignados__id_usuario=usuario
            ).order_by("-fecha_ingreso")
        return qs.all()

    def update(self, request, *args, **kwargs):
        lote = self.get_object()
        serializer = self.get_serializer(lote, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        lote = serializer.save()
        return Response(LoteSerializer(lote).data)

    @action(detail=True, methods=["post"], url_path="iniciar-produccion")
    def iniciar_produccion(self, request, pk=None):
        """CU46 — Pasar el lote de Transición a Producción."""
        lote = self.get_object()
        if lote.estado != Lote.ESTADO_TRANSICION:
            return Response(
                {"detail": "Solo un lote en Transición puede pasar a Producción."},
                status=status.HTTP_409_CONFLICT,
            )
        lote.estado = Lote.ESTADO_PRODUCCION
        lote.save(update_fields=["estado"])

        # Marcar el plan de transición como finalizado
        plan = lote.plan_transicion
        plan.estado = plan.ESTADO_FINALIZADO
        plan.save(update_fields=["estado"])

        return Response(LoteSerializer(lote).data)

    @action(detail=True, methods=["post"], url_path="vaciar")
    def vaciar(self, request, pk=None):
        """
        CU48 — Vaciado sanitario: pasa el lote a Finalizado y registra la fecha.
        Puede ejecutarse desde cualquier estado activo (Transición o Producción).
        """
        lote = self.get_object()
        if lote.estado == Lote.ESTADO_FINALIZADO:
            return Response(
                {"detail": "El lote ya se encuentra finalizado."},
                status=status.HTTP_409_CONFLICT,
            )
        lote.estado = Lote.ESTADO_FINALIZADO
        lote.fecha_vaciado = datetime.date.today()
        lote.save(update_fields=["estado", "fecha_vaciado"])

        # Si el plan de transición todavía estaba en curso, lo cerramos también
        plan = lote.plan_transicion
        if plan.estado == plan.ESTADO_EN_CURSO:
            plan.estado = plan.ESTADO_FINALIZADO
            plan.save(update_fields=["estado"])

        return Response(LoteSerializer(lote).data)
