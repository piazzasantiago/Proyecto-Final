from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from lotes.models import Lote
from usuarios.permissions import EsAdministrador, EsAdministradorOOperario

from .models import Recoleccion
from .serializers import RecoleccionSerializer


class RecoleccionViewSet(viewsets.ModelViewSet):
    """
    CRUD de recolecciones diarias + acción /finalizar/.

    Permisos:
        - Administrador: acceso completo.
        - Operario: puede crear, editar y finalizar recolecciones PENDIENTES.
          No puede eliminar.
        - Consulta: solo lectura (list + retrieve).
    """

    queryset = (
        Recoleccion.objects.select_related("id_galpon", "id_lote", "id_usuario")
        .prefetch_related("lineas__id_producto", "lineas__id_galpon")
        .all()
    )
    serializer_class = RecoleccionSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action == "destroy":
            return [EsAdministrador()]
        # create, update, partial_update, finalizar
        return [EsAdministradorOOperario()]

    # ── Filtros básicos ───────────────────────────────────────────────────────

    def get_queryset(self):
        qs = super().get_queryset()
        galpon = self.request.query_params.get("id_galpon")
        estado = self.request.query_params.get("estado")
        if galpon:
            qs = qs.filter(id_galpon_id=galpon)
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    # ── Creación: detecta el lote activo e inyecta id_lote e id_usuario ──────

    def perform_create(self, serializer):
        """
        Busca el lote activo (estado T o P) del galpón de la recolección.
        Si no existe, devuelve 400 (no tiene sentido registrar una recolección
        sin un lote en curso).
        También registra el usuario autenticado como responsable de la carga.
        """
        galpon = serializer.validated_data.get("id_galpon")
        if galpon is None:
            raise ValidationError(
                {"id_galpon_id": "El galpón es obligatorio para crear una recolección."}
            )

        lote = (
            Lote.objects.filter(
                id_galpon=galpon,
                estado__in=[Lote.ESTADO_TRANSICION, Lote.ESTADO_PRODUCCION],
            )
            .order_by("-fecha_ingreso")
            .first()
        )
        if lote is None:
            raise ValidationError(
                {
                    "non_field_errors": [
                        f"El galpón '{galpon.galpon}' no tiene un lote activo. "
                        "Registrá un lote en estado Transición o Producción antes de crear una recolección."
                    ]
                }
            )

        serializer.save(id_lote=lote, id_usuario=self.request.user)

    # ── Edición: bloquea recolecciones finalizadas ────────────────────────────

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.estado == Recoleccion.ESTADO_FINALIZADA:
            raise ValidationError(
                {"detail": "No se puede editar una recolección finalizada."}
            )
        return super().update(request, *args, **kwargs)

    # ── Acción: finalizar ─────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="finalizar")
    def finalizar(self, request, pk=None):
        """
        CU-REC-FIN — Finaliza una recolección pendiente.
        Solo se puede finalizar una recolección en estado PENDIENTE.
        """
        recoleccion = self.get_object()

        if recoleccion.estado != Recoleccion.ESTADO_PENDIENTE:
            return Response(
                {"detail": "Solo se puede finalizar una recolección en estado Pendiente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recoleccion.estado = Recoleccion.ESTADO_FINALIZADA
        recoleccion.save(update_fields=["estado"])
        serializer = self.get_serializer(recoleccion)
        return Response(serializer.data)
