from rest_framework import serializers

from .models import MateriaPrima
from .normalizacion import normalizar_nombre


# Debe coincidir con las opciones del combo "Unidad de medida" del frontend
# (MateriaPrimaFormModal.jsx).
UNIDADES_VALIDAS = ["kg", "g", "L", "mL", "unid.", "dosis", "bolsa", "saco"]


class MateriaPrimaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    stock_descartado = serializers.SerializerMethodField()
    stock_entradas = serializers.SerializerMethodField()
    stock_compras = serializers.SerializerMethodField()
    stock_actual = serializers.SerializerMethodField()

    def get_stock_descartado(self, obj):
        """
        Total de descartes de STOCK finalizados. El ViewSet lo anota en el
        queryset (una sola consulta para todo el listado); si el objeto no
        viene anotado (por ejemplo, uno recién actualizado) se calcula acá.
        """
        anotado = getattr(obj, "stock_descartado", None)
        if anotado is not None:
            return anotado
        # Import diferido: descartes depende de materias primas, no al revés.
        from descartes.stock import descartado_materia_prima

        return descartado_materia_prima(obj.pk)

    def get_stock_entradas(self, obj):
        """
        Total que salió a galpones en entradas finalizadas. Igual que el
        descartado: lo anota el ViewSet y, si falta, se calcula acá.
        """
        anotado = getattr(obj, "stock_entradas", None)
        if anotado is not None:
            return anotado
        # Import diferido: entradas depende de materias primas, no al revés.
        from entradas.stock import ingresado_materia_prima

        return ingresado_materia_prima(obj.pk)

    def get_stock_compras(self, obj):
        """
        Total comprado en compras finalizadas. Igual que el descartado: lo anota
        el ViewSet y, si falta, se calcula acá.
        """
        anotado = getattr(obj, "stock_compras", None)
        if anotado is not None:
            return anotado
        # Import diferido: compras depende de materias primas, no al revés.
        from compras.stock import comprado_materia_prima

        return comprado_materia_prima(obj.pk)

    def get_stock_actual(self, obj):
        """
        stock_inicial (stock de partida/ajuste manual) más lo comprado en
        compras finalizadas, menos lo descartado en descartes de stock
        finalizados y lo enviado a galpones en entradas finalizadas.
        """
        return (
            obj.stock_inicial
            + self.get_stock_compras(obj)
            - self.get_stock_descartado(obj)
            - self.get_stock_entradas(obj)
        )

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
            "stock_descartado",
            "stock_entradas",
            "stock_compras",
            "stock_actual",
        ]
        read_only_fields = ["id_materia_prima", "estado"]
