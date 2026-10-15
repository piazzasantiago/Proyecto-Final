from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DescarteViewSet

router = DefaultRouter()
router.register(r"descartes", DescarteViewSet, basename="descarte")

urlpatterns = [
    path("", include(router.urls)),
]
