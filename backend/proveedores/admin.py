from django.contrib import admin

from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ["nombre", "cuit", "email", "telefono", "estado"]
    list_filter = ["estado"]
    search_fields = ["nombre", "cuit", "email", "telefono", "direccion"]
