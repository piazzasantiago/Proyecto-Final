from config.auditoria import AuditoriaMixin
from django.contrib.auth import authenticate
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from config.pagination import PaginacionListado
from .models import Usuario
from .permissions import EsAdministrador
from .serializers import (
    LoginSerializer,
    RestablecerPasswordSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    CU01 - Iniciar Sesión.

    Recibe usuario (o email) y contraseña. Si son correctos y el usuario está
    activo, devuelve un token JWT que el frontend guarda y envía en cada
    petición posterior mediante el header:

        Authorization: Bearer <access>
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    identificador = serializer.validated_data["usuario"].strip()
    password = serializer.validated_data["password"]

    # La interfaz permite ingresar con usuario o con email. Si vino un email,
    # se busca a qué nombre de usuario corresponde antes de autenticar.
    if "@" in identificador:
        encontrado = Usuario.objects.filter(email__iexact=identificador).first()
        if encontrado is not None:
            identificador = encontrado.usuario

    # authenticate() verifica la contraseña y además comprueba is_active,
    # que en nuestro modelo se deriva de `estado`: un usuario dado de baja
    # no puede iniciar sesión.
    usuario = authenticate(request, username=identificador, password=password)

    if usuario is None:
        # Mensaje deliberadamente genérico: no revela si el usuario existe.
        return Response(
            {"detail": "Usuario o contraseña incorrectos."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(usuario)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "usuario": UsuarioSerializer(usuario).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Devuelve el usuario dueño del token.

    El frontend lo llama al abrir la aplicación para saber quién inició sesión
    y qué opciones mostrar según el rol. Se consulta al backend en lugar de
    confiar en datos guardados en el navegador, porque el usuario pudo haber
    sido dado de baja o cambiado de rol desde que inició sesión.
    """
    return Response(UsuarioSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    CU02 - Cerrar Sesión.

    Con JWT el token es autocontenido y el servidor no guarda sesiones, así que
    el cierre efectivo lo realiza el frontend descartando el token. Este
    endpoint existe para dejar el CU02 representado en la API y para poder
    agregar más adelante una lista de tokens revocados si hiciera falta.
    """
    return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    """
    Gestión de Usuarios. Exclusiva del rol Administrador.

    CU03 - Buscar Usuario         GET    /api/usuarios/
    CU04 - Nuevo Usuario          POST   /api/usuarios/
    CU05 - Modificar Usuario      PATCH  /api/usuarios/{id}/
    CU06 - Borrar Usuario         DELETE /api/usuarios/{id}/
    CU07 - Dar de Alta Usuario    POST   /api/usuarios/{id}/alta/
    CU08 - Dar de Baja Usuario    POST   /api/usuarios/{id}/baja/

    Además:
    Restablecer contraseña        POST   /api/usuarios/{id}/restablecer-password/
    """

    queryset = Usuario.objects.all()
    permission_classes = [EsAdministrador]
    pagination_class = PaginacionListado
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["rol", "estado"]
    search_fields = ["nombre", "apellido", "usuario", "email", "dni"]
    ordering_fields = ["apellido", "nombre", "usuario"]

    def get_serializer_class(self):
        """Un serializer distinto según la operación."""
        if self.action == "create":
            return UsuarioCreateSerializer
        if self.action in ("update", "partial_update"):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def create(self, request, *args, **kwargs):
        """CU04. Responde con el usuario completo, no con el serializer de entrada."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """CU05. Se fuerza partial=True para permitir modificaciones parciales."""
        usuario = self.get_object()
        serializer = self.get_serializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(UsuarioSerializer(usuario).data)

    def destroy(self, request, *args, **kwargs):
        """
        CU06. Un administrador no puede borrar su propio usuario. Un usuario
        con registros asociados (compras, recolecciones, descartes, entradas,
        salidas, etc.) no se borra: se responde 409 con un mensaje claro y se
        sugiere darlo de baja para conservar el historial.
        """
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            return Response(
                {"detail": "No podés borrar tu propio usuario."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            usuario.delete()
        except ProtectedError as error:
            # Nombres legibles de lo que lo impide, sin repetir y en orden estable.
            presentes = sorted(
                {str(o._meta.verbose_name_plural) for o in error.protected_objects}
            )
            detalle = ", ".join(presentes)
            return Response(
                {
                    "detail": (
                        "No se puede eliminar el usuario porque tiene registros asociados"
                        + (f" ({detalle})" if detalle else "")
                        + ". Dalo de baja en su lugar para conservar el historial."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def alta(self, request, pk=None):
        """CU07 - Dar de Alta Usuario."""
        usuario = self.get_object()
        if usuario.estado == Usuario.ESTADO_ACTIVO:
            return Response(
                {"detail": "El usuario ya se encuentra activo."},
                status=status.HTTP_409_CONFLICT,
            )
        usuario.estado = Usuario.ESTADO_ACTIVO
        usuario.save(update_fields=["estado"])
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"])
    def baja(self, request, pk=None):
        """
        CU08 - Dar de Baja Usuario.

        Baja lógica: el registro se conserva para no perder el historial de lo
        que ese usuario cargó. No puede darse de baja a sí mismo, porque
        quedaría sin poder volver a entrar.
        """
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            return Response(
                {"detail": "No podés darte de baja a vos mismo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if usuario.estado == Usuario.ESTADO_INACTIVO:
            return Response(
                {"detail": "El usuario ya se encuentra dado de baja."},
                status=status.HTTP_409_CONFLICT,
            )
        usuario.estado = Usuario.ESTADO_INACTIVO
        usuario.save(update_fields=["estado"])
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"], url_path="restablecer-password")
    def restablecer_password(self, request, pk=None):
        """
        Restablecer la contraseña de un usuario.

        A diferencia de un cambio de contraseña propio, acá NO se pide la
        contraseña actual: el administrador no la conoce, y ese es justamente
        el motivo por el que el usuario le pidió ayuda.
        """
        usuario = self.get_object()
        serializer = RestablecerPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario.set_password(serializer.validated_data["password_nueva"])
        usuario.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)