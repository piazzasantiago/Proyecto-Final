from django.contrib import admin

from .models import Galpon


@admin.register(Galpon)
class GalponAdmin(admin.ModelAdmin):
    list_display = ("id_galpon", "galpon", "capacidad", "superficie", "estado")
    list_filter = ("estado",)
    search_fields = ("galpon",)
