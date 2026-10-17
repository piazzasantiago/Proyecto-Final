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


class EsOperario(BasePermission):
    """
    Solo los usuarios con rol Operario pueden acceder.
    """

    message = "Se requiere rol Operario para realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.es_operario)


class EsAdministradorOOperario(BasePermission):
    """
    Permite acceso a Administradores y Operarios.

    Se usa en los módulos donde ambos roles pueden escribir (ej: recolecciones).
    Reemplaza el uso de EsAdministrador() | EsOperario(), que requiere DRF >= 3.9
    con soporte de OperandHolder y no siempre está disponible.
    """

    message = "Se requiere rol Administrador u Operario para realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario
            and usuario.is_authenticated
            and (usuario.es_administrador or usuario.es_operario)
        )


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


class LecturaAdministradorYConsulta_EscrituraAdministrador(BasePermission):
    """
    Matriz del módulo Proveedores (y, más adelante, Compras):

      - GET / HEAD / OPTIONS  -> Administrador y Consulta.
      - POST / PUT / PATCH / DELETE -> solo Administrador.
      - Operario: sin acceso (ni siquiera de lectura), como indica la
        descripción de usuarios y el menú de la aplicación.
    """

    message = "No tiene permiso para acceder a esta sección."

    def has_permission(self, request, view):
        usuario = request.user
        if not (usuario and usuario.is_authenticated):
            return False
        if usuario.es_administrador:
            return True
        if request.method in SAFE_METHODS:
            return usuario.rol == type(usuario).ROL_CONSULTA
        self.message = "Se requiere rol Administrador para realizar esta operación."
        return False
