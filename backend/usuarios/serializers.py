from rest_framework import serializers

from .models import Usuario
from config.auditoria import AuditoriaSerializerMixin


class UsuarioSerializer(AuditoriaSerializerMixin, serializers.ModelSerializer):
    """
    Representación de un usuario para la API.

    No incluye `password` en ningún caso: el hash nunca sale del backend.
    Los campos `*_display` traen el texto legible ("Administrador", "Activo")
    para que el frontend no tenga que conocer los códigos internos.
    """

    nombre_completo = serializers.CharField(read_only=True)
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id_usuario",
            "nombre",
            "apellido",
            "nombre_completo",
            "usuario",
            "email",
            "dni",
            "rol",
            "rol_display",
            "estado",
            "estado_display",
        ]
        read_only_fields = ["id_usuario", "estado"]


class LoginSerializer(serializers.Serializer):
    """
    Datos del formulario de inicio de sesión (CU01).

    El campo se llama `usuario` pero acepta el nombre de usuario o el email,
    tal como indica la interfaz ("Usuario o email").
    """

    usuario = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """
    CU04 - Nuevo Usuario.

    `password` es write_only: entra pero nunca sale en las respuestas.
    """

    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128,
        style={"input_type": "password"},
    )

    class Meta:
        model = Usuario
        fields = ["nombre", "apellido", "usuario", "email", "dni", "rol", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # create_user() hashea la contraseña. Nunca usar Usuario(**datos).save(),
        # porque guardaría la contraseña en texto plano.
        return Usuario.objects.create_user(password=password, **validated_data)


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """
    CU05 - Modificar Usuario.

    No permite cambiar la contraseña: para eso está el restablecimiento, que
    es una operación distinta y con su propio endpoint.
    """

    class Meta:
        model = Usuario
        fields = ["nombre", "apellido", "usuario", "email", "dni", "rol"]
        extra_kwargs = {campo: {"required": False} for campo in fields}


class RestablecerPasswordSerializer(serializers.Serializer):
    """
    Un Administrador asigna una contraseña provisoria a otro usuario.

    Es la contraparte del cartel "¿Olvidaste tu contraseña?" del login: el
    sistema no envía mails de recupero, el usuario le pide al administrador
    que se la restablezca.
    """

    password_nueva = serializers.CharField(min_length=8, max_length=128)
