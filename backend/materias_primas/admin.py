from django.contrib import admin

from .models import MateriaPrima


@admin.register(MateriaPrima)
class MateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ["materia_prima", "unidad", "stock_minimo", "stock_inicial", "estado"]
    list_filter = ["estado"]
    search_fields = ["materia_prima", "descripcion"]
