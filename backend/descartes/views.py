from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from lotes.models import Lote
from usuarios.permissions import EsAdministradorOOperario

from .models import Descarte
from .serializers import DescarteSerializer
from .stock import verificar_stock


class DescarteFilter(django_filters.FilterSet):
    """
    Filtros del listado:
        ?fecha_desde=AAAA-MM-DD   descartes desde ese día (inclusive)
        ?fecha_hasta=AAAA-MM-DD   descartes hasta ese día (inclusive)
        ?categoria=G|S            Galpón o Stock
        ?estado=P|F               Pendiente o Finalizado
        ?id_galpon=N              de un galpón en particular
    El día se toma en el horario local del sistema (settings.TIME_ZONE).
    """

    fecha_desde = django_filters.DateFilter(field_name="fecha", lookup_expr="date__gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha", lookup_expr="date__lte")

    class Meta:
        model = Descarte
        fields = ["categoria", "estado", "id_galpon"]


class DescarteViewSet(viewsets.ModelViewSet):
    """
    CRUD de descartes + acción /finalizar/.

    CU15 Buscar descarte   → GET  /api/descartes/
    CU16 Nuevo descarte    → POST /api/descartes/
    CU17 Finalizar         → POST /api/descartes/{id}/finalizar/
    CU18 Modificar         → PATCH/PUT /api/descartes/{id}/
    CU19 Eliminar          → DELETE /api/descartes/{id}/

    Categorías (ver models.Descarte):
        · Galpón (G): estadístico; solo las gallinas (lote) descuentan del lote.
        · Stock (S): descuenta stock de productos y materias primas.

    Permisos:
        - Administrador: acceso completo (CRUD + finalizar).
        - Operario: acceso completo (CRUD + finalizar), según la matriz de
          permisos por rol del README.
        - Consulta: solo lectura (list + retrieve).
        - Sin token: 401.
    """

    queryset = (
        Descarte.objects.select_related("id_galpon", "id_usuario")
        .prefetch_related(
            "lineas__id_materia_prima",
            "lineas__id_producto",
            "lineas__id_lote",
        )
        .all()
    )
    serializer_class = DescarteSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = DescarteFilter

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        # create, update, partial_update, destroy, finalizar
        return [EsAdministradorOOperario()]

    # ── Creación: registra quién cargó el descarte ────────────────────────────

    def perform_create(self, serializer):
        """El usuario autenticado queda como responsable de la carga."""
        serializer.save(id_usuario=self.request.user)

    # ── Eliminación: bloquea descartes finalizados ────────────────────────────

    def destroy(self, request, *args, **kwargs):
        """
        Un descarte finalizado ya hizo efecto (bajó gallinas del lote o stock);
        borrarlo dejaría esos números sin el registro que los respalda. Solo se
        eliminan los descartes pendientes.
        """
        descarte = self.get_object()
        if descarte.estado == Descarte.ESTADO_FINALIZADO:
            return Response(
                {"detail": "No se puede eliminar un descarte finalizado."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    # ── Acción: finalizar ─────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="finalizar")
    def finalizar(self, request, pk=None):
        """
        CU17 — Finaliza un descarte pendiente y aplica su efecto.

        Reglas:
        · Solo se puede finalizar un descarte en estado PENDIENTE.
          Si ya está Finalizado devuelve 409 Conflict.
        · Descarte de GALPÓN: para cada línea de gallinas (lote) decrementa
          cantidad_actual del lote (sin bajar de 0). Las líneas de materias
          primas y productos son solo estadísticas: no tocan el stock.
        · Descarte de STOCK: verifica que alcance el stock de cada producto y
          materia prima. Si no alcanza devuelve 400 y no cambia nada. Si
          alcanza, el stock actual se recalcula solo al quedar Finalizado.
        Todo ocurre en una transacción: o se aplica completo o no se aplica.
        """
        with transaction.atomic():
            # Se bloquea la fila para que dos finalizaciones simultáneas no
            # descuenten dos veces.
            descarte = Descarte.objects.select_for_update().get(pk=self.get_object().pk)

            if descarte.estado == Descarte.ESTADO_FINALIZADO:
                return Response(
                    {"detail": "El descarte ya está finalizado."},
                    status=status.HTTP_409_CONFLICT,
                )

            lineas = list(
                descarte.lineas.select_related(
                    "id_lote", "id_producto", "id_materia_prima"
                )
            )

            if descarte.categoria == Descarte.CATEGORIA_GALPON:
                for linea in lineas:
                    if linea.id_lote_id is None:
                        continue
                    lote = Lote.objects.select_for_update().get(pk=linea.id_lote_id)
                    nueva_cantidad = int(lote.cantidad_actual) - int(linea.cantidad)
                    lote.cantidad_actual = max(0, nueva_cantidad)
                    lote.save(update_fields=["cantidad_actual"])
            else:
                items = [
                    (linea.id_producto or linea.id_materia_prima, linea.cantidad)
                    for linea in lineas
                ]
                error = verificar_stock(items)
                if error:
                    raise ValidationError({"detail": error})

            descarte.estado = Descarte.ESTADO_FINALIZADO
            descarte.save(update_fields=["estado"])

        serializer = self.get_serializer(descarte)
        return Response(serializer.data, status=status.HTTP_200_OK)
