from django.contrib import admin

from .models import Galpon, UsuarioDelGalpon


class OperarioInline(admin.TabularInline):
    model = UsuarioDelGalpon
    extra = 1
    verbose_name = "operario asignado"
    verbose_name_plural = "operarios asignados"


@admin.register(Galpon)
class GalponAdmin(admin.ModelAdmin):
    list_display = ("id_galpon", "galpon", "capacidad", "superficie", "estado")
    list_filter = ("estado",)
    search_fields = ("galpon",)
    inlines = [OperarioInline]


@admin.register(UsuarioDelGalpon)
class UsuarioDelGalponAdmin(admin.ModelAdmin):
    list_display = ("id_galpon", "id_usuario")
    list_filter = ("id_galpon",)
