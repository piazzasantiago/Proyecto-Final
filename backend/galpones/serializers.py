from rest_framework import serializers

from .models import Galpon


class GalponSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Galpon
        fields = [
            "id_galpon",
            "galpon",
            "latitud",
            "longitud",
            "superficie",
            "capacidad",
            "estado",
            "estado_display",
            "descripcion",
        ]
        read_only_fields = ["id_galpon"]

    def validate_capacidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La capacidad debe ser mayor a 0.")
        return value

    def validate_superficie(self, value):
        if value <= 0:
            raise serializers.ValidationError("La superficie debe ser mayor a 0.")
        return value
