from django.contrib import admin

from .models import LineaSalida, Salida


class LineaSalidaInline(admin.TabularInline):
    model = LineaSalida
    extra = 0
    fields = ["id_producto", "cantidad"]


@admin.register(Salida)
class SalidaAdmin(admin.ModelAdmin):
    list_display = ["id_salida", "fecha", "estado", "observaciones"]
    list_filter = ["estado"]
    search_fields = ["observaciones"]
    inlines = [LineaSalidaInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado == Salida.ESTADO_FINALIZADA:
            return [f.name for f in obj._meta.fields]
        return []
