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


def telefono_nacional(texto):
    """
    Devuelve los 10 dígitos nacionales (característica + número) de un teléfono
    argentino, o None si no es válido. Acepta +54, el 9 de celulares, el 0 inicial
    de la característica y el 15 intermedio: 381-455-0102, 0381 15 455-0102,
    +54 9 381 455 0102, (011) 4555-1234.
    """
    d = re.sub(r"\D", "", texto)
    if d.startswith("54"):
        d = d[2:]
        if d.startswith("9"):
            d = d[1:]
    if d.startswith("0"):
        d = d[1:]
    if len(d) == 12:  # característica + 15 + número
        for area in (2, 3, 4):
            if d[area:area + 2] == "15" and len(d) - 2 == 10:
                d = d[:area] + d[area + 2:]
                break
    if len(d) != 10 or len(set(d)) < 3:
        return None
    if not (d.startswith("11") or d[0] in "23"):
        return None
    return d


def telefono_internacional(texto):
    """
    Devuelve los dígitos de un teléfono internacional (empieza con + y un código
    de país distinto de 54), o None si no es válido. Solo se controla lo básico,
    porque cada país tiene su propio plan de numeración: entre 8 y 15 dígitos en
    total (máximo de la norma E.164), que el código de país no empiece con 0 y que
    no sea una repetición de dígitos.
    """
    d = re.sub(r"\D", "", texto)
    if not 8 <= len(d) <= 15 or d.startswith("0") or len(set(d)) < 3:
        return None
    return d


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
        if len(re.findall(r"[^\W_]", value)) < 2 or not re.search(r"[^\W\d_]", value):
            raise serializers.ValidationError(
                "El nombre debe tener al menos 2 caracteres e incluir letras."
            )
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
        """
        Teléfono argentino con característica (código de área) o, si empieza con
        + y un código de país distinto de 54, un teléfono internacional.
        """
        value = value.strip()
        if not re.fullmatch(r"\+?[\d\s()\-]+", value):
            raise serializers.ValidationError(
                "El teléfono solo puede incluir números, espacios, guiones, paréntesis "
                "y un + al inicio."
            )
        if value.startswith("+") and not re.sub(r"\D", "", value).startswith("54"):
            if telefono_internacional(value) is None:
                raise serializers.ValidationError(
                    "Ingresá un teléfono internacional válido con código de país, "
                    "por ejemplo +598 99 123 456."
                )
            return value
        nacional = telefono_nacional(value)
        if nacional is None:
            raise serializers.ValidationError(
                "Ingresá un teléfono argentino válido con característica, por ejemplo "
                "381-455-0102 o +54 9 381 455 0102. Para otro país, empezá con + y el "
                "código de país."
            )
        return value

    def validate_direccion(self, value):
        value = " ".join((value or "").split())
        if value and len(re.findall(r"[^\W_]", value)) < 3:
            raise serializers.ValidationError("Ingresá una dirección válida.")
        return value

    def validate_email(self, value):
        return value.strip().lower()
