from rest_framework.routers import DefaultRouter

from .views import GalponViewSet

router = DefaultRouter()
router.register(r"galpones", GalponViewSet, basename="galpon")

urlpatterns = router.urls
