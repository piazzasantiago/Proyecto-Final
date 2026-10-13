from django.db.models import Sum
from rest_framework import serializers

from .models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    stock_recolectado = serializers.SerializerMethodField()
    stock_actual = serializers.SerializerMethodField()

    def get_stock_recolectado(self, obj):
        """
        Total de huevos de recolecciones FINALIZADAS. El ViewSet lo anota en el
        queryset (una sola consulta para todo el listado); si el objeto no viene
        anotado (por ejemplo, uno recién creado) se calcula acá.
        """
        anotado = getattr(obj, "stock_recolectado", None)
        if anotado is not None:
            return anotado
        # Import diferido: recolecciones depende de productos, no al revés.
        from recolecciones.models import LineaRecoleccion, Recoleccion

        total = LineaRecoleccion.objects.filter(
            id_producto=obj,
            id_recoleccion__estado=Recoleccion.ESTADO_FINALIZADA,
        ).aggregate(total=Sum("cantidad"))["total"]
        return total or 0

    def get_stock_actual(self, obj):
        """Stock inicial/ajuste + lo recolectado en recolecciones finalizadas."""
        return obj.stock_inicial + self.get_stock_recolectado(obj)

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "producto",
            "descripcion",
            "estado",
            "estado_display",
            "stock_inicial",
            "stock_recolectado",
            "stock_actual",
        ]
        read_only_fields = ["id_producto", "estado"]
