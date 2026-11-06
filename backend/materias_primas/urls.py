from rest_framework.routers import DefaultRouter

from .views import MateriaPrimaViewSet

router = DefaultRouter()
router.register(r"materias-primas", MateriaPrimaViewSet, basename="materia-prima")

urlpatterns = router.urls
