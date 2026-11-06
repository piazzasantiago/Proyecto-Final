from django.db.models import ProtectedError
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.models import Usuario
from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

from config.pagination import PaginacionListado
from .models import Galpon
from .serializers import GalponSerializer
from config.auditoria import AuditoriaMixin


class GalponViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Galpones más acciones de cambio de estado.

    CU09  GET    /api/galpones/              listar (con ?search=, ?estado=, ?ordering=,
                                             ?libre=true para solo los que no tienen lote en curso)
    CU09  GET    /api/galpones/{id}/         detalle
    CU10  POST   /api/galpones/              crear
    CU11  PATCH  /api/galpones/{id}/         modificar
    CU12  DELETE /api/galpones/{id}/         eliminar
    CU13  POST   /api/galpones/{id}/alta/    dar de alta (Inactivo → Activo)
    CU14  POST   /api/galpones/{id}/baja/    dar de baja (Activo → Inactivo)
          GET    /api/galpones/{id}/existencias/  materias primas estimadas en el galpón

    Permisos: consultar requiere estar autenticado con cualquier rol; crear,
    modificar y eliminar requiere rol Administrador.

    Filtrado por rol:
    - Administrador y Consulta: ven todos los galpones.
    - Operario: ve solo los galpones a los que está asignado (UsuariosDelGalpon).
      Si no tiene galpones asignados, recibe lista vacía.
    """

    serializer_class = GalponSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    pagination_class = PaginacionListado
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["galpon", "descripcion"]
    ordering_fields = ["galpon", "capacidad", "superficie"]

    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == Usuario.ROL_OPERARIO:
            # El operario solo ve los galpones que tiene asignados
            qs = Galpon.objects.filter(
                operarios_asignados__id_usuario=usuario
            ).order_by("galpon")
        else:
            qs = Galpon.objects.all()
        if self.action == "list" and self.request.query_params.get("libre", "").lower() in ("1", "true"):
            qs = self._solo_libres(qs)
        return qs

    @staticmethod
    def _solo_libres(qs):
        """Galpones sin ningún lote en Transición o Producción (listos para recibir uno)."""
        from lotes.models import Lote

        ocupados = Lote.objects.filter(
            estado__in=[Lote.ESTADO_TRANSICION, Lote.ESTADO_PRODUCCION]
        ).values("id_galpon")
        return qs.exclude(pk__in=ocupados)

    # Registros que impiden borrar un galpón (related_name del FK PROTECT -> nombre legible).
    _REGISTROS_ASOCIADOS = (
        ("lotes", "lotes"),
        ("entradas", "entradas"),
        ("recolecciones", "recolecciones"),
        ("descartes", "descartes"),
    )

    def destroy(self, request, *args, **kwargs):
        """
        CU12 — Un galpón con registros asociados (lotes, entradas, recolecciones
        o descartes) no se borra: se responde 409 con un mensaje claro y se
        sugiere darlo de baja para conservar el historial.
        """
        galpon = self.get_object()
        try:
            galpon.delete()
        except ProtectedError:
            presentes = [
                nombre
                for relacion, nombre in self._REGISTROS_ASOCIADOS
                if getattr(galpon, relacion).exists()
            ]
            detalle = ", ".join(presentes) if presentes else "lotes, entradas, recolecciones o descartes"
            return Response(
                {
                    "detail": (
                        f"No se puede eliminar el galpón porque tiene registros asociados ({detalle}). "
                        "Dalo de baja en su lugar para conservar el historial."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        galpon = self.get_object()
        serializer = self.get_serializer(galpon, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        galpon = serializer.save()
        return Response(GalponSerializer(galpon).data)

    @action(detail=True, methods=["get"])
    def existencias(self, request, pk=None):
        """
        Existencia estimada de cada materia prima dentro del galpón
        (ingresado por entradas − descartado en el galpón). Es información
        adicional del detalle del galpón, no un caso de uso aparte. Lo puede
        ver cualquier usuario que pueda ver el galpón (el operario, solo los suyos).
        """
        from entradas.stock import existencias_galpon

        galpon = self.get_object()
        return Response(existencias_galpon(galpon.pk))

    @action(detail=True, methods=["post"])
    def alta(self, request, pk=None):
        """CU13 — Dar de alta un galpón (Inactivo → Activo)."""
        galpon = self.get_object()
        if galpon.estado == Galpon.ESTADO_ACTIVO:
            return Response(
                {"detail": "El galpón ya se encuentra activo."},
                status=status.HTTP_409_CONFLICT,
            )
        galpon.estado = Galpon.ESTADO_ACTIVO
        galpon.save(update_fields=["estado"])
        return Response(GalponSerializer(galpon).data)

    @action(detail=True, methods=["post"])
    def baja(self, request, pk=None):
        """CU14 — Dar de baja un galpón (Activo → Inactivo).

        No se permite si el galpón tiene un lote activo (Transición o
        Producción) alojado en este momento: dar de baja no lo reubica ni
        lo finaliza, así que hacerlo dejaría un lote con aves "vivas" en un
        galpón marcado como inactivo. El administrador primero debe
        resolver ese lote (por ejemplo, vaciarlo si terminó su ciclo).
        """
        from lotes.models import Lote

        galpon = self.get_object()
        if galpon.estado == Galpon.ESTADO_INACTIVO:
            return Response(
                {"detail": "El galpón ya se encuentra dado de baja."},
                status=status.HTTP_409_CONFLICT,
            )
        lote_activo = galpon.lotes.filter(
            estado__in=[Lote.ESTADO_TRANSICION, Lote.ESTADO_PRODUCCION]
        ).first()
        if lote_activo is not None:
            return Response(
                {
                    "detail": (
                        f"No se puede dar de baja el galpón porque tiene un lote activo "
                        f"({lote_activo.codigo}, estado: {lote_activo.get_estado_display()}). "
                        "Finalizá ese lote antes de dar de baja el galpón."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        galpon.estado = Galpon.ESTADO_INACTIVO
        galpon.save(update_fields=["estado"])
        return Response(GalponSerializer(galpon).data)
