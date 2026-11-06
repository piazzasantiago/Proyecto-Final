from django.contrib import admin

from .models import Compra, LineaCompra


class LineaCompraInline(admin.TabularInline):
    model = LineaCompra
    extra = 0
    fields = ["id_materia_prima", "cantidad", "precio_unitario", "id_lote"]
    readonly_fields = ["id_lote"]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ["nro_comprobante", "id_proveedor", "categoria", "tipo", "fecha", "estado"]
    list_filter = ["estado", "categoria", "tipo"]
    search_fields = ["id_compra"]
    inlines = [LineaCompraInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado == Compra.ESTADO_FINALIZADA:
            return [f.name for f in obj._meta.fields]
        return []
