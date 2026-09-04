from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario
from .serializers import LoginSerializer, UsuarioSerializer


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
