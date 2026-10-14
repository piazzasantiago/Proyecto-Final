from rest_framework.routers import DefaultRouter
from .views import RecoleccionViewSet

router = DefaultRouter()
router.register(r"recolecciones", RecoleccionViewSet, basename="recoleccion")

urlpatterns = router.urls