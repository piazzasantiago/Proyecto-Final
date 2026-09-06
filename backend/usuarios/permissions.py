from rest_framework.permissions import SAFE_METHODS, BasePermission


class EsAdministrador(BasePermission):
    """
    Solo los usuarios con rol Administrador pueden acceder.

    Se usa en la gestión de usuarios (CU03 a CU08), que es exclusiva del
    Administrador según la descripción de usuarios participantes.
    """

    message = "Se requiere rol Administrador para realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.es_administrador)


class LecturaAutenticados_EscrituraAdministrador(BasePermission):
    """
    Implementa la matriz rol x caso de uso de los módulos productivos:

      - GET / HEAD / OPTIONS  -> cualquier usuario autenticado (Operario,
        Consulta y Administrador pueden consultar la información).
      - POST / PUT / PATCH / DELETE -> solo Administrador.

    Se aplica a Galpones y servirá para los módulos que se agreguen después.
    """

    message = "Se requiere rol Administrador para realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return usuario.es_administrador
