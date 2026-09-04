from rest_framework import serializers

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
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
