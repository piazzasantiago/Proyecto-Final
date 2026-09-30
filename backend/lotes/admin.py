from django.contrib import admin

from .models import Lote, PlanTransicion


class PlanTransicionInline(admin.StackedInline):
    model = PlanTransicion
    extra = 0
    readonly_fields = ("id_plan", "estado", "fecha_inicio", "fecha_fin")
    fieldsets = (
        ("Identificación", {
            "fields": ("id_plan", "estado", "fecha_inicio", "fecha_fin"),
        }),
        ("Semana 1", {
            "fields": (
                ("agua_semana1", "alimento_semana1", "horas_luz_semana1"),
            ),
        }),
        ("Semana 2", {
            "fields": (
                ("agua_semana2", "alimento_semana2", "horas_luz_semana2"),
            ),
        }),
        ("Semana 3", {
            "fields": (
                ("agua_semana3", "alimento_semana3", "horas_luz_semana3"),
            ),
        }),
        ("Semana 4", {
            "fields": (
                ("agua_semana4", "alimento_semana4", "horas_luz_semana4"),
            ),
        }),
    )


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    inlines = [PlanTransicionInline]

    list_display = (
        "codigo",
        "id_galpon",
        "fecha_ingreso",
        "cantidad_inicial",
        "cantidad_actual",
        "estado",
        "fecha_vaciado",
    )
    list_filter = ("estado", "id_galpon")
    search_fields = ("id_lote",)
    ordering = ("-fecha_ingreso",)

    readonly_fields = ("codigo", "cantidad_actual", "fecha_vaciado", "estado")

    fieldsets = (
        ("Identificación", {
            "fields": ("codigo", "id_galpon"),
        }),
        ("Datos del lote", {
            "fields": ("fecha_ingreso", "cantidad_inicial", "cantidad_actual", "observaciones"),
        }),
        ("Estado", {
            "fields": ("estado", "fecha_vaciado"),
        }),
    )
