from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SalidaViewSet

router = DefaultRouter()
router.register(r"salidas", SalidaViewSet, basename="salida")

urlpatterns = [
    path("", include(router.urls)),
]
