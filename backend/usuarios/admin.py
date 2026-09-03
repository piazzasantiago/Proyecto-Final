from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Hereda de UserAdmin, que ya trae el manejo seguro de contraseñas:
    al editar muestra un enlace para cambiarla en vez del hash.
    """

    list_display = ("usuario", "nombre_completo", "email", "rol", "estado")
    list_filter = ("rol", "estado")
    search_fields = ("nombre", "apellido", "usuario", "email", "dni")
    ordering = ("apellido", "nombre")
    readonly_fields = ("last_login",)

    fieldsets = (
        ("Acceso", {"fields": ("usuario", "password")}),
        ("Datos personales", {"fields": ("nombre", "apellido", "email", "dni")}),
        ("Rol y estado", {"fields": ("rol", "estado")}),
        ("Permisos del panel", {"fields": ("is_staff", "is_superuser")}),
        ("Fechas", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("usuario", "email", "nombre", "apellido", "dni", "rol",
                       "password1", "password2"),
        }),
    )

    @admin.display(description="Nombre completo")
    def nombre_completo(self, obj):
        return obj.nombre_completo


admin.site.site_header = "AvíGest · Administración"
admin.site.site_title = "AvíGest"
admin.site.index_title = "Gestión de la granja avícola"
