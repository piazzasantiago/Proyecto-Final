from django.utils import timezone
from rest_framework import serializers

from galpones.models import Galpon
from lotes.models import Lote
from productos.models import Producto

from .models import LineaRecoleccion, Recoleccion


# ── Resúmenes de objetos relacionados ────────────────────────────────────────

class GalponResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Galpon
        fields = ["id_galpon", "galpon"]


class LoteResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lote
        fields = ["id_lote", "codigo"]


class ProductoResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ["id_producto", "producto"]


# ── Líneas ────────────────────────────────────────────────────────────────────

class LineaRecoleccionSerializer(serializers.ModelSerializer):
    galpon = GalponResumenSerializer(source="id_galpon", read_only=True)
    producto = ProductoResumenSerializer(source="id_producto", read_only=True)

    # El galpón de la línea se propaga desde la cabecera en create/update;
    # el frontend nunca lo envía por línea.
    id_galpon_id = serializers.PrimaryKeyRelatedField(
        queryset=Galpon.objects.all(),
        source="id_galpon",
        write_only=True,
        required=False,
        allow_null=True,
        default=None,
    )
    id_producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.filter(estado=Producto.ESTADO_ACTIVO),
        source="id_producto",
        write_only=True,
    )

    cantidad = serializers.IntegerField(min_value=1)

    class Meta:
        model = LineaRecoleccion
        fields = [
            "id_linea_recoleccion",
            "galpon",
            "id_galpon_id",
            "producto",
            "id_producto_id",
            "cantidad",
        ]
        read_only_fields = ["id_linea_recoleccion"]


# ── Cabecera ──────────────────────────────────────────────────────────────────

class RecoleccionSerializer(serializers.ModelSerializer):
    galpon = GalponResumenSerializer(source="id_galpon", read_only=True)
    lote = LoteResumenSerializer(source="id_lote", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    lineas = LineaRecoleccionSerializer(many=True, read_only=False)

    id_galpon_id = serializers.PrimaryKeyRelatedField(
        queryset=Galpon.objects.filter(estado=Galpon.ESTADO_ACTIVO),
        source="id_galpon",
        write_only=True,
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = Recoleccion
        fields = [
            "id_recoleccion",
            "galpon",
            "id_galpon_id",
            "lote",          # read-only; se asigna en perform_create de la vista
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "lineas",
        ]
        read_only_fields = ["id_recoleccion", "estado"]

    # ── Validaciones ──────────────────────────────────────────────────────────

    def validate_fecha(self, value):
        """Una recolección registra algo que ya ocurrió: no admite fecha/hora futura."""
        if value > timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora de la recolección no puede ser futura."
            )
        return value

    def validate_lineas(self, lineas):
        if not lineas:
            raise serializers.ValidationError(
                "La recolección debe tener al menos una línea."
            )
        return lineas

    def validate(self, data):
        """Cada producto debe aparecer como máximo una vez por recolección."""
        lineas = data.get("lineas", [])
        productos_vistos = set()
        for linea in lineas:
            producto = linea["id_producto"]
            if producto.id_producto in productos_vistos:
                raise serializers.ValidationError(
                    f"El producto '{producto.producto}' aparece más de una vez en las líneas."
                )
            productos_vistos.add(producto.id_producto)
        return data

    # ── Escritura ─────────────────────────────────────────────────────────────

    def create(self, validated_data):
        """
        id_lote llega inyectado por RecoleccionViewSet.perform_create().
        El galpón de cada línea se copia desde la cabecera.
        """
        lineas_data = validated_data.pop("lineas")
        recoleccion = Recoleccion.objects.create(**validated_data)
        for linea_data in lineas_data:
            linea_data["id_galpon"] = recoleccion.id_galpon
            LineaRecoleccion.objects.create(id_recoleccion=recoleccion, **linea_data)
        return recoleccion

    def update(self, instance, validated_data):
        # El lote se fija al crear según el galpón; si el galpón cambiara, el
        # lote quedaría desfasado. Por eso el galpón no se puede modificar.
        nuevo_galpon = validated_data.pop("id_galpon", None)
        if nuevo_galpon is not None and nuevo_galpon != instance.id_galpon:
            raise serializers.ValidationError(
                {"id_galpon_id": "No se puede cambiar el galpón de una recolección existente."}
            )
        lineas_data = validated_data.pop("lineas", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lineas_data is not None:
            instance.lineas.all().delete()
            for linea_data in lineas_data:
                linea_data["id_galpon"] = instance.id_galpon
                LineaRecoleccion.objects.create(id_recoleccion=instance, **linea_data)
        return instance
