import re

from rest_framework import serializers

from materias_primas.normalizacion import normalizar_nombre

from .models import Proveedor

_PESOS_CUIT = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def cuit_valido(digitos):
    """11 dígitos con dígito verificador correcto (algoritmo de AFIP)."""
    if not re.fullmatch(r"\d{11}", digitos):
        return False
    suma = sum(int(d) * p for d, p in zip(digitos[:10], _PESOS_CUIT))
    verificador = 11 - suma % 11
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    return verificador == int(digitos[10])


def formatear_cuit(digitos):
    """'20123456786' -> '20-12345678-6' (para mostrarlo)."""
    if len(digitos) != 11:
        return digitos
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"


class ProveedorSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    cuit_formateado = serializers.SerializerMethodField()
    nombre = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=150)
    telefono = serializers.CharField(max_length=45)
    direccion = serializers.CharField(max_length=150, required=False, allow_blank=True)
    cuit = serializers.CharField(max_length=20, required=False, allow_blank=True)

    class Meta:
        model = Proveedor
        fields = [
            "id_proveedor",
            "nombre",
            "cuit",
            "cuit_formateado",
            "direccion",
            "email",
            "telefono",
            "estado",
            "estado_display",
        ]
        read_only_fields = ["id_proveedor", "estado"]

    def get_cuit_formateado(self, obj):
        return formatear_cuit(obj.cuit) if obj.cuit else ""

    # ── Validaciones ──────────────────────────────────────────────────────────

    def validate_nombre(self, value):
        """El nombre es único sin distinguir mayúsculas, tildes ni espacios de más ("Álamo" == "alamo")."""
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        buscado = normalizar_nombre(value)
        otros = Proveedor.objects.all()
        if self.instance is not None:
            otros = otros.exclude(pk=self.instance.pk)
        for existente in otros.values_list("nombre", flat=True):
            if normalizar_nombre(existente) == buscado:
                raise serializers.ValidationError(
                    f'Ya existe un proveedor con ese nombre ("{existente}").'
                )
        return value

    def validate_cuit(self, value):
        """Opcional. Acepta con o sin guiones; se guarda solo con los 11 dígitos."""
        digitos = re.sub(r"[\s-]", "", value or "")
        if not digitos:
            return ""
        if not digitos.isdigit() or len(digitos) != 11:
            raise serializers.ValidationError("El CUIT debe tener 11 dígitos.")
        if not cuit_valido(digitos):
            raise serializers.ValidationError("El CUIT no es válido (dígito verificador incorrecto).")
        otros = Proveedor.objects.filter(cuit=digitos)
        if self.instance is not None:
            otros = otros.exclude(pk=self.instance.pk)
        existente = otros.first()
        if existente is not None:
            raise serializers.ValidationError(
                f'Ya existe un proveedor con ese CUIT ("{existente.nombre}").'
            )
        return digitos

    def validate_telefono(self, value):
        value = value.strip()
        if not re.fullmatch(r"[\d\s()+\-]+", value) or len(re.sub(r"\D", "", value)) < 6:
            raise serializers.ValidationError(
                "El teléfono debe tener al menos 6 dígitos y solo puede incluir números, "
                "espacios, +, - y paréntesis."
            )
        return value

    def validate_direccion(self, value):
        return " ".join((value or "").split())

    def validate_email(self, value):
        return value.strip().lower()
