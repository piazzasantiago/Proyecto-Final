from rest_framework import serializers

from .models import MateriaPrima


class MateriaPrimaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    stock_actual = serializers.SerializerMethodField()

    def get_stock_actual(self, obj):
        """
        Por ahora: stock_inicial es el stock de partida/ajuste manual.
        Cuando existan Entradas, Descartes y Compras, se calculará como:
          stock_inicial + compras - entradas_a_galpones - descartes
        """
        anotado = getattr(obj, "stock_actual", None)
        if anotado is not None:
            return anotado
        return obj.stock_inicial

    def validate_stock_minimo(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El stock mínimo no puede ser negativo."
            )
        return value

    def validate_stock_inicial(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El stock inicial no puede ser negativo."
            )
        return value

    class Meta:
        model = MateriaPrima
        fields = [
            "id_materia_prima",
            "materia_prima",
            "descripcion",
            "unidad",
            "estado",
            "estado_display",
            "stock_minimo",
            "stock_inicial",
            "stock_actual",
        ]
        read_only_fields = ["id_materia_prima", "estado"]
