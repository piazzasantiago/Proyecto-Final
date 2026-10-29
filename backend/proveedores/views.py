from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from materias_primas.normalizacion import normalizar_nombre
from usuarios.permissions import LecturaAdministradorYConsulta_EscrituraAdministrador

from config.pagination import PaginacionListado
from .models import Proveedor
from .serializers import ProveedorSerializer
from config.auditoria import AuditoriaMixin


class ProveedorViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    CRUD de Proveedores más acciones de alta y baja.

    CU70  GET    /api/proveedores/                 buscar (?search=, ?estado=, ?ordering=)
    CU70  GET    /api/proveedores/{id}/            detalle
    CU71  POST   /api/proveedores/                 crear
    CU72  PATCH  /api/proveedores/{id}/            modificar
    CU73  DELETE /api/proveedores/{id}/            borrar
    CU74  POST   /api/proveedores/{id}/alta/       dar de alta (Inactivo → Activo)
    CU75  POST   /api/proveedores/{id}/baja/       dar de baja (Activo → Inactivo)
    --    GET    /api/proveedores/similares/       nombres iguales o parecidos (ayuda del formulario)

    Permisos: Administrador hace todo; Consulta solo lee; Operario no tiene
    acceso a la sección.
    """

    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [LecturaAdministradorYConsulta_EscrituraAdministrador]
    pagination_class = PaginacionListado
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["nombre", "cuit", "email", "telefono", "direccion"]
    ordering_fields = ["nombre"]

    def update(self, request, *args, **kwargs):
        instancia = self.get_object()
        serializer = self.get_serializer(instancia, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instancia = serializer.save()
        return Response(ProveedorSerializer(instancia).data)

    def destroy(self, request, *args, **kwargs):
        """
        CU73 — Un proveedor con registros asociados (por ejemplo, compras) no
        se borra: se da de baja para conservar el historial.
        """
        proveedor = self.get_object()
        try:
            proveedor.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar el proveedor porque tiene registros "
                        "asociados. Dalo de baja en su lugar."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def similares(self, request):
        """
        Ayuda al formulario: GET /api/proveedores/similares/?nombre=agro[&excluir=ID]
        Devuelve los proveedores cuyo nombre es igual (exacta=true) o parecido
        (uno contiene al otro) ignorando mayúsculas y tildes.
        """
        buscado = normalizar_nombre(request.query_params.get("nombre", ""))
        if not buscado:
            return Response([])
        excluir = request.query_params.get("excluir")
        resultado = []
        for p in Proveedor.objects.all():
            if excluir and str(p.pk) == excluir:
                continue
            nombre = normalizar_nombre(p.nombre)
            exacta = nombre == buscado
            if exacta or buscado in nombre or nombre in buscado:
                resultado.append(
                    {
                        "id_proveedor": p.pk,
                        "nombre": p.nombre,
                        "estado": p.estado,
                        "exacta": exacta,
                    }
                )
        resultado.sort(key=lambda r: (not r["exacta"], r["nombre"]))
        return Response(resultado[:5])

    @action(detail=True, methods=["post"])
    def alta(self, request, pk=None):
        """CU74 — Dar de alta un proveedor (Inactivo → Activo)."""
        proveedor = self.get_object()
        if proveedor.estado == Proveedor.ESTADO_ACTIVO:
            return Response(
                {"detail": "El proveedor ya se encuentra activo."},
                status=status.HTTP_409_CONFLICT,
            )
        proveedor.estado = Proveedor.ESTADO_ACTIVO
        proveedor.save(update_fields=["estado"])
        return Response(ProveedorSerializer(proveedor).data)

    @action(detail=True, methods=["post"])
    def baja(self, request, pk=None):
        """CU75 — Dar de baja un proveedor (Activo → Inactivo)."""
        proveedor = self.get_object()
        if proveedor.estado == Proveedor.ESTADO_INACTIVO:
            return Response(
                {"detail": "El proveedor ya se encuentra dado de baja."},
                status=status.HTTP_409_CONFLICT,
            )
        proveedor.estado = Proveedor.ESTADO_INACTIVO
        proveedor.save(update_fields=["estado"])
        return Response(ProveedorSerializer(proveedor).data)
