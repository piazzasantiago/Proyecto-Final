from django.contrib import admin

from .models import Alerta, TipoAlerta


@admin.register(TipoAlerta)
class TipoAlertaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "clave", "severidad")
    list_filter = ("severidad",)
    search_fields = ("nombre", "clave")


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    """Solo para mirar: las alertas las genera y las resuelve el sistema."""

    list_display = ("id_alerta", "id_tipo_alerta", "id_lote", "estado", "fecha_generacion")
    list_filter = ("estado", "id_tipo_alerta")
    search_fields = ("descripcion",)
    readonly_fields = (
        "id_lote",
        "id_tipo_alerta",
        "descripcion",
        "estado",
        "fecha_generacion",
        "fecha_resolucion",
    )

    def has_add_permission(self, request):
        return False
