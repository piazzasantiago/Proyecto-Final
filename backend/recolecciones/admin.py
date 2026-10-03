from django.contrib import admin
from .models import Recoleccion, LineaRecoleccion


class LineaRecoleccionInline(admin.TabularInline):
    model = LineaRecoleccion
    extra = 0
    fields = ["id_galpon", "id_producto", "cantidad"]
    autocomplete_fields = ["id_galpon", "id_producto"]


@admin.register(Recoleccion)
class RecoleccionAdmin(admin.ModelAdmin):
    list_display = ["id_recoleccion", "id_galpon", "fecha", "estado", "observaciones"]
    list_filter = ["estado", "id_galpon"]
    search_fields = ["observaciones", "id_galpon__galpon"]
    ordering = ["-fecha"]
    inlines = [LineaRecoleccionInline]
    readonly_fields = ["estado"]
