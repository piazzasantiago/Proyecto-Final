from rest_framework import serializers

from .models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "producto",
            "descripcion",
            "estado",
            "estado_display",
            "stock_actual",
        ]
        read_only_fields = ["id_producto", "estado"]
