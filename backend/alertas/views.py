from django.db.models import Case, IntegerField, Value, When
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from config.pagination import PaginacionListado
from galpones.acceso import limitar_a_galpones_asignados

from .generacion import generar_alertas
from .models import Alerta
from .serializers import AlertaSerializer

#: Orden de las alertas: primero lo que sigue pendiente, dentro de eso lo más
#: grave ("A" de alta ordena antes que "M" de media) y lo más nuevo.
ORDEN = (
    Case(
        When(estado=Alerta.ESTADO_PENDIENTE, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    ),
    "id_tipo_alerta__severidad",
    "-fecha_generacion",
)


def alertas_visibles(usuario):
    """
    Alertas que puede ver el usuario, ya ordenadas. El Operario solo ve las de
    los lotes de sus galpones asignados (F-32); los demás roles las ven todas.
    La usan el listado y el dashboard, para que no se separen.
    """
    qs = Alerta.objects.select_related("id_tipo_alerta", "id_lote", "id_lote__id_galpon")
    qs = limitar_a_galpones_asignados(qs, usuario, campo="id_lote__id_galpon")
    return qs.order_by(*ORDEN)


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado y detalle de las alertas de los lotes (sección Dashboard; el
    número de caso de uso todavía no está definido).

    Es de solo lectura a propósito: las alertas las genera y las resuelve el
    sistema al evaluar las reglas, no se cargan ni se editan a mano.

        GET /api/alertas/        listar  (?estado=P|R &id_lote= &id_galpon=)
        GET /api/alertas/{id}/   detalle

    Permisos: cualquier usuario autenticado puede consultarlas. El Operario
    solo ve las alertas de los lotes de sus galpones asignados (F-32); las de
    otros galpones no se listan y devuelven 404.
    """

    queryset = Alerta.objects.all()  # get_queryset() aplica el acceso por galpón
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginacionListado

    @staticmethod
    def _id_param(valor, nombre):
        """Un id de filtro tiene que ser un entero positivo; si no, 400 (no 500)."""
        if not valor.isascii() or not valor.isdigit() or int(valor) > 2_147_483_647:
            raise ValidationError({nombre: "Debe ser un número entero válido."})
        return int(valor)

    def get_queryset(self):
        # Antes de responder se ponen al día: así el listado nunca muestra una
        # alerta que ya se resolvió ni oculta una que acaba de aparecer.
        generar_alertas()

        qs = alertas_visibles(self.request.user)
        params = self.request.query_params
        estado = params.get("estado")
        if estado:
            if estado not in dict(Alerta.ESTADO_CHOICES):
                raise ValidationError(
                    {"estado": "Estado inválido. Usá P (pendiente) o R (resuelta)."}
                )
            qs = qs.filter(estado=estado)
        if params.get("id_lote"):
            qs = qs.filter(id_lote_id=self._id_param(params["id_lote"], "id_lote"))
        if params.get("id_galpon"):
            qs = qs.filter(
                id_lote__id_galpon_id=self._id_param(params["id_galpon"], "id_galpon")
            )
        return qs
