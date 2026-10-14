from rest_framework import serializers

from .models import MateriaPrima
from .normalizacion import normalizar_nombre


# Debe coincidir con las opciones del combo "Unidad de medida" del frontend
# (MateriaPrimaFormModal.jsx).
UNIDADES_VALIDAS = ["kg", "g", "L", "mL", "unid.", "dosis", "bolsa", "saco"]


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

    def validate_materia_prima(self, value):
        """El nombre es único sin distinguir mayúsculas ni tildes ("Maíz" == "maiz")."""
        value = " ".join(value.split())
        buscado = normalizar_nombre(value)
        otras = MateriaPrima.objects.all()
        if self.instance is not None:
            otras = otras.exclude(pk=self.instance.pk)
        for existente in otras.values_list("materia_prima", flat=True):
            if normalizar_nombre(existente) == buscado:
                raise serializers.ValidationError(
                    f'Ya existe una materia prima con ese nombre ("{existente}").'
                )
        return value

    def validate_unidad(self, value):
        """
        Solo unidades del combo. Si una materia prima ya tenía otra unidad
        guardada, se le permite conservarla al editar.
        """
        if value in UNIDADES_VALIDAS:
            return value
        if self.instance is not None and value == self.instance.unidad:
            return value
        raise serializers.ValidationError(
            "Unidad de medida no válida. Opciones: " + ", ".join(UNIDADES_VALIDAS) + "."
        )

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
