from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("usuarios.urls")),
    path("api/", include("galpones.urls")),
    path("api/", include("lotes.urls")),
    path("api/", include("productos.urls")),
    path("api/", include("recolecciones.urls")),
    path("api/", include("materias_primas.urls")),
]
