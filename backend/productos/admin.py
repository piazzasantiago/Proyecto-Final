from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("id_producto", "producto", "estado")
    list_filter = ("estado",)
    search_fields = ("producto",)
