from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from usuarios.permissions import LecturaAutenticados_EscrituraAdministrador

from .models import MateriaPrima
from .normalizacion import normalizar_nombre
from .serializers import MateriaPrimaSerializer


class MateriaPrimaViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Materias Primas más acciones de cambio de estado.

    CU55  GET    /api/materias-primas/                 listar (con ?search=, ?estado=)
    CU55  GET    /api/materias-primas/{id}/            detalle
    CU56  POST   /api/materias-primas/                 crear
    CU57  PATCH  /api/materias-primas/{id}/            modificar
    CU58  DELETE /api/materias-primas/{id}/            eliminar
    --    GET    /api/materias-primas/similares/     nombres iguales/parecidos (ayuda del formulario)
    CU59  POST   /api/materias-primas/{id}/activar/    dar de alta (Inactivo → Activo)
    CU60  POST   /api/materias-primas/{id}/desactivar/ dar de baja (Activo → Inactivo)

    Permisos: consultar requiere estar autenticado con cualquier rol;
    crear, modificar y eliminar requiere rol Administrador.
    """

    queryset = MateriaPrima.objects.all()
    serializer_class = MateriaPrimaSerializer
    permission_classes = [LecturaAutenticados_EscrituraAdministrador]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["materia_prima", "descripcion"]
    ordering_fields = ["materia_prima"]

    def update(self, request, *args, **kwargs):
        instancia = self.get_object()
        serializer = self.get_serializer(instancia, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instancia = serializer.save()
        return Response(MateriaPrimaSerializer(instancia).data)

    @action(detail=False, methods=["get"])
    def similares(self, request):
        """
        Ayuda al formulario: GET /api/materias-primas/similares/?nombre=maiz[&excluir=ID]
        Devuelve las materias primas cuyo nombre es igual (exacta=true) o
        parecido (una contiene a la otra) ignorando mayúsculas y tildes.
        """
        buscado = normalizar_nombre(request.query_params.get("nombre", ""))
        if not buscado:
            return Response([])
        excluir = request.query_params.get("excluir")
        resultado = []
        for mp in MateriaPrima.objects.all():
            if excluir and str(mp.pk) == excluir:
                continue
            nombre = normalizar_nombre(mp.materia_prima)
            exacta = nombre == buscado
            if exacta or buscado in nombre or nombre in buscado:
                resultado.append(
                    {
                        "id_materia_prima": mp.pk,
                        "materia_prima": mp.materia_prima,
                        "estado": mp.estado,
                        "exacta": exacta,
                    }
                )
        resultado.sort(key=lambda r: (not r["exacta"], r["materia_prima"]))
        return Response(resultado[:5])

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """CU59 — Dar de alta una materia prima (Inactivo → Activo)."""
        mp = self.get_object()
        if mp.estado == MateriaPrima.ESTADO_ACTIVO:
            return Response(
                {"detail": "La materia prima ya se encuentra activa."},
                status=status.HTTP_409_CONFLICT,
            )
        mp.estado = MateriaPrima.ESTADO_ACTIVO
        mp.save(update_fields=["estado"])
        return Response(MateriaPrimaSerializer(mp).data)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """CU60 — Dar de baja una materia prima (Activo → Inactivo)."""
        mp = self.get_object()
        if mp.estado == MateriaPrima.ESTADO_INACTIVO:
            return Response(
                {"detail": "La materia prima ya se encuentra inactiva."},
                status=status.HTTP_409_CONFLICT,
            )
        mp.estado = MateriaPrima.ESTADO_INACTIVO
        mp.save(update_fields=["estado"])
        return Response(MateriaPrimaSerializer(mp).data)
