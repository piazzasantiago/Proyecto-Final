from django.db import transaction
from django_filters import rest_framework as django_filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from lotes.models import Lote
from usuarios.permissions import EsAdministradorOOperario

from config.pagination import PaginacionListado
from galpones.acceso import limitar_a_galpones_asignados, validar_galpon_asignado
from .models import Descarte
from .serializers import DescarteSerializer
from .stock import verificar_stock
from config.auditoria import AuditoriaMixin


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


class DescarteViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD de descartes + acción /finalizar/.

    CU15 Buscar descarte   → GET  /api/descartes/
    CU16 Nuevo descarte    → POST /api/descartes/
    CU17 Modificar         → PATCH/PUT /api/descartes/{id}/
    CU18 Borrar            → DELETE /api/descartes/{id}/
    CU19 Finalizar         → POST /api/descartes/{id}/finalizar/

    Categorías (ver models.Descarte):
        · Galpón (G): estadístico; solo las gallinas (lote) descuentan del lote.
        · Stock (S): descuenta stock de productos y materias primas.

    Permisos:
        - Administrador: acceso completo (CRUD + finalizar).
        - Operario: acceso completo (CRUD + finalizar), según la matriz de
          permisos por rol del README.
        - Consulta: solo lectura (list + retrieve).
        - Sin token: 401.
        - El Operario solo ve y trabaja con los descartes de los galpones que tiene
          asignados (F-32). Los descartes de stock no pertenecen a ningún galpón y
          los ve cualquier operario. Los de otros galpones devuelven 404.
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
    pagination_class = PaginacionListado
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = DescarteFilter

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        # create, update, partial_update, destroy, finalizar
        return [EsAdministradorOOperario()]

    # ── Creación: registra quién cargó el descarte ────────────────────────────

    def get_queryset(self):
        return limitar_a_galpones_asignados(
            super().get_queryset(), self.request.user, incluir_sin_galpon=True
        )

    def perform_create(self, serializer):
        """El usuario autenticado queda como responsable de la carga."""
        validar_galpon_asignado(self.request.user, serializer.validated_data.get("id_galpon"))
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
        CU19 — Finaliza un descarte pendiente y aplica su efecto.

        Reglas:
        · Solo se puede finalizar un descarte en estado PENDIENTE.
          Si ya está Finalizado devuelve 409 Conflict.
        · Descarte de GALPÓN: para cada lote con líneas de gallinas verifica
          que alcancen (sumando las líneas del mismo lote) y decrementa
          cantidad_actual. Si no alcanzan devuelve 400 y no cambia nada.
          Las líneas de materias primas y productos son solo estadísticas:
          no tocan el stock.
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
                # Gallinas a descontar por lote (un lote puede repetirse en
                # varias líneas). Se bloquean en orden de id para evitar
                # bloqueos cruzados entre finalizaciones simultáneas.
                por_lote = {}
                for linea in lineas:
                    if linea.id_lote_id is not None:
                        por_lote[linea.id_lote_id] = (
                            por_lote.get(linea.id_lote_id, 0) + int(linea.cantidad)
                        )
                for id_lote in sorted(por_lote):
                    lote = Lote.objects.select_for_update().get(pk=id_lote)
                    a_descartar = por_lote[id_lote]
                    # Entre la carga y la finalización el lote pudo cambiar
                    # (otro descarte finalizado, lote cerrado): se vuelve a
                    # verificar y, si no alcanza, no se cambia nada.
                    if lote.estado == Lote.ESTADO_FINALIZADO:
                        raise ValidationError(
                            {"detail": f"El lote {lote.codigo} ya está finalizado."}
                        )
                    if a_descartar > lote.cantidad_actual:
                        raise ValidationError(
                            {
                                "detail": (
                                    f"No se pueden descartar {a_descartar} gallinas del lote "
                                    f"{lote.codigo}: solo quedan {lote.cantidad_actual}."
                                )
                            }
                        )
                    lote.cantidad_actual -= a_descartar
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
