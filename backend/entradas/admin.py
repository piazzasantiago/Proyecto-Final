from django.contrib import admin

from .models import Entrada, LineaEntrada


class LineaEntradaInline(admin.TabularInline):
    model = LineaEntrada
    extra = 0
    fields = ["id_materia_prima", "cantidad"]


@admin.register(Entrada)
class EntradaAdmin(admin.ModelAdmin):
    list_display = ["id_entrada", "id_galpon", "fecha", "estado", "observaciones"]
    list_filter = ["estado", "id_galpon"]
    search_fields = ["observaciones"]
    inlines = [LineaEntradaInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado == Entrada.ESTADO_FINALIZADA:
            return [f.name for f in obj._meta.fields]
        return []
