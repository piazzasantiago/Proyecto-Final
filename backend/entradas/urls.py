from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EntradaViewSet

router = DefaultRouter()
router.register(r"entradas", EntradaViewSet, basename="entrada")

urlpatterns = [
    path("", include(router.urls)),
]
