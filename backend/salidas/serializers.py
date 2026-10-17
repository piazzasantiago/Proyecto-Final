from django.utils import timezone
from rest_framework import serializers

from descartes.stock import verificar_stock
from productos.models import Producto
from recolecciones.serializers import UsuarioResumenSerializer

from .models import LineaSalida, Salida

# Tope sensato por línea (evita cargas absurdas por error de tipeo).
CANTIDAD_MAX = 1_000_000


# ── Línea ─────────────────────────────────────────────────────────────────────

class LineaSalidaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="id_producto.producto", read_only=True)
    # Se acepta cualquier producto existente; que esté activo se valida en la
    # cabecera, porque una salida que se edita conserva los que ya tenía.
    id_producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    # Los productos se cuentan en unidades enteras.
    cantidad = serializers.IntegerField(min_value=1, max_value=CANTIDAD_MAX)

    class Meta:
        model = LineaSalida
        fields = [
            "id_linea_salida",
            "id_producto",
            "producto_nombre",
            "cantidad",
        ]
        read_only_fields = ["id_linea_salida"]


# ── Cabecera ──────────────────────────────────────────────────────────────────

class SalidaSerializer(serializers.ModelSerializer):
    usuario = UsuarioResumenSerializer(source="id_usuario", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    items_count = serializers.SerializerMethodField()
    lineas = LineaSalidaSerializer(many=True)

    class Meta:
        model = Salida
        fields = [
            "id_salida",
            "usuario",  # read-only; se asigna en perform_create de la vista
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "items_count",
            "lineas",
        ]
        read_only_fields = ["id_salida", "estado"]
        extra_kwargs = {"observaciones": {"max_length": 500}}

    def get_items_count(self, obj):
        return obj.lineas.count()

    # ── Validaciones ──────────────────────────────────────────────────────────

    def validate_fecha(self, value):
        """Una salida registra algo que ya ocurrió: no admite fechas futuras."""
        if value > timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora de la salida no pueden ser futuras."
            )
        return value

    def validate_lineas(self, lineas):
        if not lineas:
            raise serializers.ValidationError("La salida debe tener al menos una línea.")
        return lineas

    def validate(self, data):
        if self.instance is not None and self.instance.estado == Salida.ESTADO_FINALIZADA:
            raise serializers.ValidationError("Salida finalizada. No se puede editar.")

        lineas = data.get("lineas")
        if lineas is None:
            return data

        # No se repite el mismo producto dentro de una salida.
        vistos = set()
        for linea in lineas:
            producto = linea["id_producto"]
            if producto.pk in vistos:
                raise serializers.ValidationError(
                    {"lineas": f"El producto '{producto.producto}' está repetido en la salida."}
                )
            vistos.add(producto.pk)

        # Solo productos activos. Una salida que se edita conserva los que ya
        # tenía aunque se hayan desactivado después.
        ya_cargados = set()
        if self.instance is not None:
            ya_cargados = set(self.instance.lineas.values_list("id_producto_id", flat=True))
        for linea in lineas:
            producto = linea["id_producto"]
            if producto.estado != Producto.ESTADO_ACTIVO and producto.pk not in ya_cargados:
                raise serializers.ValidationError(
                    {"lineas": f"El producto '{producto.producto}' está inactivo."}
                )

        # Aviso temprano: debe alcanzar el stock (se vuelve a verificar al finalizar).
        error = verificar_stock(
            [(l["id_producto"], l["cantidad"]) for l in lineas], accion="despachar"
        )
        if error:
            raise serializers.ValidationError({"lineas": error})
        return data

    # ── Escritura ─────────────────────────────────────────────────────────────

    def create(self, validated_data):
        lineas_data = validated_data.pop("lineas")
        salida = Salida.objects.create(**validated_data)
        for linea_data in lineas_data:
            LineaSalida.objects.create(id_salida=salida, **linea_data)
        return salida

    def update(self, instance, validated_data):
        lineas_data = validated_data.pop("lineas", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lineas_data is not None:
            instance.lineas.all().delete()
            for linea_data in lineas_data:
                LineaSalida.objects.create(id_salida=instance, **linea_data)
        return instance
