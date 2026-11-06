import datetime
import re

from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.models import Usuario
from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

from .models import Lote
from .transiciones import pasar_a_produccion_vencidos
from .serializers import LoteSerializer
from config.auditoria import AuditoriaMixin

# El código del lote, tal como se ve en pantalla y en las alertas: L-2026-029.
# Se aceptan también variantes razonables de tipeo: sin la L, con espacios en
# lugar de guiones y sin los ceros de relleno.
_CODIGO_CON_ANIO = re.compile(r"^(?:l[-\s]?)?(\d{4})[-\s]0*(\d{1,9})$")
_CODIGO_SIN_ANIO = re.compile(r"^l[-\s]?0*(\d{1,9})$")


def filtrar_por_busqueda(queryset, texto):
    """
    Busca un lote por su código, por su número o por parte del número.

    El código que muestra el sistema (L-2026-029) no es una columna de la base:
    se arma con el año de ingreso y el id del lote. Por eso, cuando el texto
    tiene forma de código se traduce a esos dos datos. Un número suelto sigue
    funcionando como antes, por coincidencia parcial del id, que es lo que
    espera quien escribe «29» en el buscador.
    """
    texto = (texto or "").strip().lower()
    if not texto:
        return queryset
    con_anio = _CODIGO_CON_ANIO.match(texto)
    if con_anio:
        anio, numero = con_anio.groups()
        return queryset.filter(pk=int(numero), fecha_ingreso__year=int(anio))
    sin_anio = _CODIGO_SIN_ANIO.match(texto)
    if sin_anio:
        return queryset.filter(pk=int(sin_anio.group(1)))
    # «029»: el número del código con sus ceros de relleno. Sin esto no
    # encontraría nada, porque ningún id empieza con cero.
    if texto.isdigit() and texto.startswith("0") and len(texto) <= 10:
        return queryset.filter(pk=int(texto))
    return queryset.filter(id_lote__icontains=texto)


class LoteViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD completo de Lotes más acciones de cambio de estado.

    CU42  GET    /api/lotes/                        listar (con ?search=, ?estado=, ?id_galpon=,
                                                    ?fecha_desde= y ?fecha_hasta= en formato AAAA-MM-DD)
    CU42  GET    /api/lotes/{id}/                   detalle
    CU43  POST   /api/lotes/                        crear (incluye plan de transición);
                                                    exige un lote comprado a asignar
                                                    (id_linea_compra, ver Compras)
    CU44  PATCH  /api/lotes/{id}/                   modificar
    CU45  DELETE /api/lotes/{id}/                   eliminar
    CU46  POST   /api/lotes/{id}/iniciar-produccion/ Transición → Producción (también ocurre solo
                                                    al cumplirse las 4 semanas de transición)
    CU48  POST   /api/lotes/{id}/vaciar/             cualquier estado → Finalizado + fecha_vaciado

    Permisos: leer requiere autenticación con cualquier rol; crear, modificar
    y eliminar requiere rol Administrador.

    Búsqueda (solo en el listado): ?search= acepta el código del lote tal como
    se ve en pantalla (L-2026-029), el año con el número (2026-029) o el número
    suelto (29, que busca por coincidencia parcial del id).

    Rango de fechas (solo en el listado): ?fecha_desde= y ?fecha_hasta= (ambos
    inclusivos y opcionales) dejan los lotes cuya fecha de ingreso, o sea el día
    en que se asignaron a un galpón, cae dentro del rango. Sin ninguno, se
    listan todos. Una fecha inválida o un desde posterior al hasta devuelve 400.

    Filtrado por rol:
    - Administrador y Consulta: ven todos los lotes.
    - Operario: ve solo los lotes de los galpones que tiene asignados.
      Si no tiene galpones asignados, recibe lista vacía.
    """

    serializer_class = LoteSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["estado", "id_galpon"]
    ordering_fields = ["fecha_ingreso", "cantidad_inicial", "cantidad_actual"]

    def get_queryset(self):
        # Los lotes que cumplieron las 4 semanas de transición pasan solos a Producción.
        pasar_a_produccion_vencidos()
        usuario = self.request.user
        qs = Lote.objects.select_related(
            "id_galpon", "plan_transicion", "linea_compra__id_compra__id_proveedor"
        )
        if usuario.rol == Usuario.ROL_OPERARIO:
            # El operario solo ve los lotes de los galpones que tiene asignados
            qs = qs.filter(
                id_galpon__operarios_asignados__id_usuario=usuario
            ).order_by("-fecha_ingreso")
        else:
            qs = qs.all()
        if self.action == "list":
            qs = self._filtrar_por_fecha_de_ingreso(qs)
            # La búsqueda se resuelve acá (y no con SearchFilter) porque el
            # código del lote se arma con dos columnas; ver filtrar_por_busqueda.
            qs = filtrar_por_busqueda(qs, self.request.query_params.get("search"))
        return qs

    def _fecha_param(self, nombre):
        valor = self.request.query_params.get(nombre)
        if not valor:
            return None
        try:
            return datetime.date.fromisoformat(valor)
        except ValueError:
            raise ValidationError({nombre: "Fecha inválida. Usá el formato AAAA-MM-DD."})

    def _filtrar_por_fecha_de_ingreso(self, qs):
        """Deja los lotes cuya fecha de ingreso cae en ?fecha_desde= / ?fecha_hasta=."""
        desde = self._fecha_param("fecha_desde")
        hasta = self._fecha_param("fecha_hasta")
        if desde and hasta and desde > hasta:
            raise ValidationError({"fecha_desde": "La fecha desde no puede ser posterior a la fecha hasta."})
        if desde:
            qs = qs.filter(fecha_ingreso__gte=desde)
        if hasta:
            qs = qs.filter(fecha_ingreso__lte=hasta)
        return qs

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
        lote.fecha_inicio_produccion = datetime.date.today()
        lote.save(update_fields=["estado", "fecha_inicio_produccion"])

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
