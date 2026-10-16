from django.contrib import admin
from .models import Descarte, LineaDescarte


class LineaDescarteInline(admin.TabularInline):
    model = LineaDescarte
    extra = 0
    fields = ["id_materia_prima", "id_producto", "id_lote", "cantidad", "motivo"]
    readonly_fields = []


@admin.register(Descarte)
class DescarteAdmin(admin.ModelAdmin):
    list_display = ["id_descarte", "categoria", "id_galpon", "fecha", "estado", "observaciones"]
    list_filter = ["categoria", "estado", "id_galpon"]
    search_fields = ["observaciones"]
    readonly_fields = []
    inlines = [LineaDescarteInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado == Descarte.ESTADO_FINALIZADO:
            return [f.name for f in obj._meta.fields]
        return []
