from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from materias_primas.models import MateriaPrima
from proveedores.models import Proveedor
from recolecciones.serializers import UsuarioResumenSerializer

from .models import Compra, LineaCompra

# Topes sensatos por línea (evitan cargas absurdas por error de tipeo).
CANTIDAD_MAX = Decimal("1000000")
PRECIO_MAX = Decimal("10000000")


class ProveedorResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ["id_proveedor", "nombre"]


# ── Línea ─────────────────────────────────────────────────────────────────────

class LineaCompraSerializer(serializers.ModelSerializer):
    materia_prima_nombre = serializers.CharField(
        source="id_materia_prima.materia_prima", read_only=True, default=None
    )
    materia_prima_unidad = serializers.CharField(
        source="id_materia_prima.unidad", read_only=True, default=None
    )
    # Se acepta cualquier materia prima existente; que esté activa se valida en
    # la cabecera, porque una compra que se edita conserva las que ya tenía.
    # En las compras de lotes no va.
    id_materia_prima = serializers.PrimaryKeyRelatedField(
        queryset=MateriaPrima.objects.all(), required=False, allow_null=True
    )
    cantidad = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=CANTIDAD_MAX,
    )
    precio_unitario = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=PRECIO_MAX,
    )
    subtotal = serializers.SerializerMethodField()
    id_lote = serializers.PrimaryKeyRelatedField(read_only=True)
    lote_codigo = serializers.SerializerMethodField()

    class Meta:
        model = LineaCompra
        fields = [
            "id_linea_compra",
            "id_materia_prima",
            "materia_prima_nombre",
            "materia_prima_unidad",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "id_lote",
            "lote_codigo",
        ]
        read_only_fields = ["id_linea_compra"]

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_lote_codigo(self, obj):
        return obj.id_lote.codigo if obj.id_lote_id else None


# ── Cabecera ──────────────────────────────────────────────────────────────────

class CompraSerializer(serializers.ModelSerializer):
    proveedor = ProveedorResumenSerializer(source="id_proveedor", read_only=True)
    usuario = UsuarioResumenSerializer(source="id_usuario", read_only=True)
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    # Lo genera el sistema (autoincremental): no se envía ni se edita.
    nro_comprobante = serializers.CharField(read_only=True)
    items_count = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    lineas = LineaCompraSerializer(many=True)

    # Se acepta cualquier proveedor existente; que esté activo se valida más
    # abajo, porque una compra que se edita conserva el que ya tenía.
    id_proveedor = serializers.PrimaryKeyRelatedField(queryset=Proveedor.objects.all())

    class Meta:
        model = Compra
        fields = [
            "id_compra",
            "proveedor",
            "id_proveedor",
            "usuario",  # read-only; se asigna en perform_create de la vista
            "categoria",
            "categoria_display",
            "tipo",
            "tipo_display",
            "nro_comprobante",
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "items_count",
            "total",
            "lineas",
        ]
        read_only_fields = ["id_compra", "estado"]
        extra_kwargs = {
            "observaciones": {"max_length": 500},
        }

    def get_items_count(self, obj):
        return obj.lineas.count()

    def get_total(self, obj):
        return sum((l.subtotal for l in obj.lineas.all()), Decimal("0.00"))

    # ── Validaciones de campos ────────────────────────────────────────────────

    def validate_fecha(self, value):
        """Una compra registra algo que ya ocurrió: no admite fechas futuras."""
        if value > timezone.localdate():
            raise serializers.ValidationError("La fecha de la compra no puede ser futura.")
        return value

    def validate_lineas(self, lineas):
        if not lineas:
            raise serializers.ValidationError("La compra debe tener al menos una línea.")
        return lineas

    # ── Validación general ────────────────────────────────────────────────────

    def validate(self, data):
        instancia = self.instance
        if instancia is not None and instancia.estado == Compra.ESTADO_FINALIZADA:
            raise serializers.ValidationError("Compra finalizada. No se puede editar.")

        # La categoría no cambia una vez creada: define cómo son las líneas.
        if instancia is not None and data.get("categoria", instancia.categoria) != instancia.categoria:
            raise serializers.ValidationError(
                {"categoria": "No se puede cambiar la categoría de una compra existente."}
            )
        categoria = instancia.categoria if instancia is not None else data.get("categoria")

        # Proveedor activo (una compra que se edita conserva el que ya tenía).
        proveedor = data.get("id_proveedor", instancia.id_proveedor if instancia else None)
        if (
            "id_proveedor" in data
            and proveedor.estado != Proveedor.ESTADO_ACTIVO
            and (instancia is None or proveedor.pk != instancia.id_proveedor_id)
        ):
            raise serializers.ValidationError(
                {"id_proveedor": f"El proveedor '{proveedor.nombre}' está dado de baja."}
            )

        lineas = data.get("lineas")
        if lineas is None:
            return data

        if categoria == Compra.CATEGORIA_MATERIAS_PRIMAS:
            self._validar_lineas_materias_primas(lineas, instancia)
        elif categoria == Compra.CATEGORIA_LOTES:
            self._validar_lineas_lotes(lineas)
        return data

    def _validar_lineas_materias_primas(self, lineas, instancia):
        vistas = set()
        for linea in lineas:
            mp = linea.get("id_materia_prima")
            if mp is None:
                raise serializers.ValidationError(
                    {"lineas": "Cada línea debe indicar una materia prima."}
                )
            if mp.pk in vistas:
                raise serializers.ValidationError(
                    {"lineas": f"La materia prima '{mp.materia_prima}' está repetida en la compra."}
                )
            vistas.add(mp.pk)

        # Solo materias primas activas. Una compra que se edita conserva las que
        # ya tenía aunque se hayan dado de baja después.
        ya_cargadas = set()
        if instancia is not None:
            ya_cargadas = set(instancia.lineas.values_list("id_materia_prima_id", flat=True))
        for linea in lineas:
            mp = linea["id_materia_prima"]
            if mp.estado != MateriaPrima.ESTADO_ACTIVO and mp.pk not in ya_cargadas:
                raise serializers.ValidationError(
                    {"lineas": f"La materia prima '{mp.materia_prima}' está inactiva."}
                )

    def _validar_lineas_lotes(self, lineas):
        for linea in lineas:
            if linea.get("id_materia_prima") is not None:
                raise serializers.ValidationError(
                    {"lineas": "Una compra de lotes no lleva materias primas."}
                )
            cantidad = linea["cantidad"]
            if cantidad != cantidad.to_integral_value():
                raise serializers.ValidationError(
                    {"lineas": "La cantidad de aves debe ser un número entero."}
                )

    # ── Escritura ─────────────────────────────────────────────────────────────

    # La cabecera y sus líneas se guardan en una sola transacción: si algo falla
    # a mitad de camino no queda una compra sin líneas ni líneas viejas borradas.

    def create(self, validated_data):
        lineas_data = validated_data.pop("lineas")
        with transaction.atomic():
            compra = Compra.objects.create(**validated_data)
            for linea_data in lineas_data:
                LineaCompra.objects.create(id_compra=compra, **linea_data)
        return compra

    def update(self, instance, validated_data):
        lineas_data = validated_data.pop("lineas", None)
        validated_data.pop("categoria", None)  # inmutable (validado arriba)
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            if lineas_data is not None:
                instance.lineas.all().delete()
                for linea_data in lineas_data:
                    LineaCompra.objects.create(id_compra=instance, **linea_data)
        return instance


class LotePendienteSerializer(serializers.ModelSerializer):
    """Un lote comprado que espera ser asignado a un galpón (combo de Lotes)."""

    id_compra = serializers.IntegerField(source="id_compra_id", read_only=True)
    nro_comprobante = serializers.CharField(source="id_compra.nro_comprobante", read_only=True)
    fecha_compra = serializers.DateField(source="id_compra.fecha", read_only=True)
    proveedor_nombre = serializers.CharField(
        source="id_compra.id_proveedor.nombre", read_only=True
    )
    cantidad = serializers.SerializerMethodField()

    class Meta:
        model = LineaCompra
        fields = [
            "id_linea_compra",
            "id_compra",
            "nro_comprobante",
            "fecha_compra",
            "proveedor_nombre",
            "cantidad",
        ]

    def get_cantidad(self, obj):
        return int(obj.cantidad)
