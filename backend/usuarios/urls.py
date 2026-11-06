from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .views import UsuarioViewSet

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = [
    path("auth/login/", views.login, name="login"),
    path("auth/me/", views.me, name="me"),
    path("auth/logout/", views.logout, name="logout"),
] + router.urls
