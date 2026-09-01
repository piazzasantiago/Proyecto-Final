from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Galpon
from .serializers import GalponSerializer


class GalponViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Galpones.
    GET    /api/galpones/          -> listar
    POST   /api/galpones/          -> crear
    GET    /api/galpones/{id}/     -> detalle
    PUT    /api/galpones/{id}/     -> actualizar completo
    PATCH  /api/galpones/{id}/     -> actualizar parcial
    DELETE /api/galpones/{id}/     -> eliminar
    """

    queryset = Galpon.objects.all()
    serializer_class = GalponSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado"]
    search_fields = ["galpon", "descripcion"]
    ordering_fields = ["galpon", "capacidad", "superficie"]
