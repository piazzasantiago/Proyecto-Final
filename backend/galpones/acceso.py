"""
Acceso de los operarios a los registros de sus galpones (F-32).

Un operario solo trabaja con los galpones que tiene asignados (tabla
``UsuariosDelGalpon``). Estas funciones aplican esa regla a los módulos cuyos
registros pertenecen a un galpón (recolecciones, descartes de galpón y
entradas). Administrador y Consulta no tienen restricción.

Los registros ajenos no se listan y, si se pide uno por su id, responde 404
(igual que si no existiera: no se revela que existe en otro galpón).
"""

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from usuarios.models import Usuario

from .models import UsuarioDelGalpon


def es_operario(usuario):
    return bool(usuario and getattr(usuario, "rol", None) == Usuario.ROL_OPERARIO)


def ids_galpones_asignados(usuario):
    """Ids de los galpones asignados al usuario (subconsulta, sin duplicados)."""
    return UsuarioDelGalpon.objects.filter(id_usuario=usuario).values("id_galpon")


def limitar_a_galpones_asignados(queryset, usuario, campo="id_galpon", incluir_sin_galpon=False):
    """
    Para un operario, deja solo los registros de sus galpones asignados.
    Con ``incluir_sin_galpon`` conserva además los que no pertenecen a ningún
    galpón (por ejemplo, los descartes de stock). Para otros roles no cambia nada.
    """
    if not es_operario(usuario):
        return queryset
    condicion = Q(**{f"{campo}__in": ids_galpones_asignados(usuario)})
    if incluir_sin_galpon:
        condicion |= Q(**{f"{campo}__isnull": True})
    return queryset.filter(condicion)


def validar_galpon_asignado(usuario, galpon, campo="id_galpon"):
    """Un operario no puede cargar registros en un galpón que no tiene asignado."""
    if galpon is None or not es_operario(usuario):
        return
    if not ids_galpones_asignados(usuario).filter(id_galpon=galpon.pk).exists():
        raise ValidationError({campo: "No tenés asignado ese galpón."})
