from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from galpones.models import Galpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from productos.models import Producto
from recolecciones.serializers import UsuarioResumenSerializer

from .models import Descarte, LineaDescarte
from .stock import verificar_stock
from config.auditoria import AuditoriaSerializerMixin


# ── Resúmenes de objetos relacionados ─────────────────────────────────────────

class GalponResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Galpon
        fields = ["id_galpon", "galpon"]


# ── Línea ─────────────────────────────────────────────────────────────────────

class LineaDescarteSerializer(serializers.ModelSerializer):
    # Campos de lectura con datos del ítem descartado
    tipo = serializers.SerializerMethodField()
    materia_prima_nombre = serializers.SerializerMethodField()
    materia_prima_unidad = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    lote_codigo = serializers.SerializerMethodField()

    # FKs de escritura (exactamente uno de los tres debe estar presente)
    id_materia_prima = serializers.PrimaryKeyRelatedField(
        queryset=MateriaPrima.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    id_producto = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    id_lote = serializers.PrimaryKeyRelatedField(
        queryset=Lote.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    cantidad = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    class Meta:
        model = LineaDescarte
        fields = [
            "id_linea_descarte",
            "tipo",
            "id_materia_prima",
            "id_producto",
            "id_lote",
            "materia_prima_nombre",
            "materia_prima_unidad",
            "producto_nombre",
            "lote_codigo",
            "cantidad",
            "motivo",
        ]
        read_only_fields = ["id_linea_descarte"]

    # ── Campos calculados ─────────────────────────────────────────────────────

    def get_tipo(self, obj):
        return obj.tipo

    def get_materia_prima_nombre(self, obj):
        if obj.id_materia_prima_id:
            return obj.id_materia_prima.materia_prima
        return None

    def get_materia_prima_unidad(self, obj):
        if obj.id_materia_prima_id:
            return obj.id_materia_prima.unidad
        return None

    def get_producto_nombre(self, obj):
        if obj.id_producto_id:
            return obj.id_producto.producto
        return None

    def get_lote_codigo(self, obj):
        if obj.id_lote_id:
            return obj.id_lote.codigo
        return None

    # ── Validación: exactamente un ítem ──────────────────────────────────────

    def validate(self, data):
        mp = data.get("id_materia_prima")
        prod = data.get("id_producto")
        lote = data.get("id_lote")
        rellenos = sum(1 for x in [mp, prod, lote] if x is not None)
        if rellenos == 0:
            raise serializers.ValidationError(
                "Debe especificarse exactamente un ítem: "
                "id_materia_prima, id_producto o id_lote."
            )
        if rellenos > 1:
            raise serializers.ValidationError(
                "Solo se puede especificar un ítem por línea "
                "(id_materia_prima, id_producto o id_lote)."
            )
        # Los huevos y las gallinas se cuentan de a unidades enteras; solo las
        # materias primas admiten decimales (kg, L, etc.).
        if (prod is not None or lote is not None) and data["cantidad"] != data[
            "cantidad"
        ].to_integral_value():
            raise serializers.ValidationError(
                {"cantidad": "La cantidad debe ser un número entero (sin decimales)."}
            )
        return data


# ── Cabecera ──────────────────────────────────────────────────────────────────

class DescarteSerializer(AuditoriaSerializerMixin, serializers.ModelSerializer):
    galpon = GalponResumenSerializer(source="id_galpon", read_only=True)
    usuario = UsuarioResumenSerializer(source="id_usuario", read_only=True)
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    items_count = serializers.SerializerMethodField()
    lineas = LineaDescarteSerializer(many=True)

    # El galpón es obligatorio solo en los descartes de categoría Galpón; en los
    # de Stock debe quedar vacío. Esa regla se valida en validate().
    id_galpon = serializers.PrimaryKeyRelatedField(
        queryset=Galpon.objects.filter(estado=Galpon.ESTADO_ACTIVO),
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = Descarte
        fields = [
            "id_descarte",
            "categoria",
            "categoria_display",
            "galpon",
            "id_galpon",
            "usuario",       # read-only; se asigna en perform_create de la vista
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "items_count",
            "lineas",
        ]
        read_only_fields = ["id_descarte", "estado"]
        extra_kwargs = {
            "observaciones": {"max_length": 500},
            "categoria": {"required": True},
        }

    def get_items_count(self, obj):
        return obj.lineas.count()

    # ── Validaciones ──────────────────────────────────────────────────────────

    def validate_fecha(self, value):
        """Un descarte registra algo que ya ocurrió: no admite fechas futuras."""
        if value > timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora del descarte no pueden ser futuras."
            )
        return value

    def validate_lineas(self, lineas):
        if not lineas:
            raise serializers.ValidationError(
                "El descarte debe tener al menos una línea."
            )
        return lineas

    def validate(self, data):
        if self.instance is not None:
            if self.instance.estado == Descarte.ESTADO_FINALIZADO:
                raise serializers.ValidationError(
                    "No se puede modificar un descarte ya finalizado."
                )
            # La categoría define cómo se aplica el descarte: no se cambia.
            if "categoria" in data and data["categoria"] != self.instance.categoria:
                raise serializers.ValidationError(
                    {"categoria": "No se puede cambiar la categoría de un descarte existente."}
                )

        categoria = data.get("categoria") or (
            self.instance.categoria if self.instance else None
        )
        galpon = data.get("id_galpon") or (
            self.instance.id_galpon if self.instance else None
        )
        lineas = data.get("lineas", [])

        if categoria == Descarte.CATEGORIA_GALPON:
            self._validar_galpon(galpon, lineas)
        elif categoria == Descarte.CATEGORIA_STOCK:
            self._validar_stock(data, lineas)
        return data

    def _validar_galpon(self, galpon, lineas):
        if galpon is None:
            raise serializers.ValidationError(
                {"id_galpon": "El galpón es obligatorio en los descartes de galpón."}
            )
        # Si un mismo lote aparece en varias líneas, se suman: el total no puede
        # superar las gallinas que tiene el lote.
        descartadas = {}
        for linea in lineas:
            lote = linea.get("id_lote")
            if lote is None:
                continue
            if lote.id_galpon_id != galpon.pk:
                raise serializers.ValidationError(
                    {"lineas": f"El lote {lote.codigo} no pertenece al galpón seleccionado."}
                )
            if lote.estado == Lote.ESTADO_FINALIZADO:
                raise serializers.ValidationError(
                    {"lineas": f"El lote {lote.codigo} ya está finalizado."}
                )
            lote_y_total = descartadas.get(lote.pk, (lote, Decimal("0")))
            descartadas[lote.pk] = (lote, lote_y_total[1] + linea["cantidad"])

        for lote, total in descartadas.values():
            if total > lote.cantidad_actual:
                raise serializers.ValidationError(
                    {
                        "lineas": (
                            f"No se pueden descartar {int(total)} gallinas del lote "
                            f"{lote.codigo}: solo quedan {lote.cantidad_actual}."
                        )
                    }
                )

    def _validar_stock(self, data, lineas):
        # Un descarte de stock no pertenece a ningún galpón.
        if data.get("id_galpon") is not None:
            raise serializers.ValidationError(
                {"id_galpon": "Los descartes de stock no pertenecen a un galpón."}
            )
        if any(linea.get("id_lote") is not None for linea in lineas):
            raise serializers.ValidationError(
                {
                    "lineas": "Los descartes de stock solo admiten materias primas y "
                    "productos (las gallinas se descartan desde un galpón)."
                }
            )
        items = [
            (linea.get("id_producto") or linea.get("id_materia_prima"), linea["cantidad"])
            for linea in lineas
        ]
        error = verificar_stock(items)
        if error:
            raise serializers.ValidationError({"lineas": error})

    # ── Escritura ─────────────────────────────────────────────────────────────

    def create(self, validated_data):
        lineas_data = validated_data.pop("lineas")
        descarte = Descarte.objects.create(**validated_data)
        for linea_data in lineas_data:
            linea_data["id_galpon"] = descarte.id_galpon
            LineaDescarte.objects.create(id_descarte=descarte, **linea_data)
        return descarte

    def update(self, instance, validated_data):
        lineas_data = validated_data.pop("lineas", None)
        # El galpón no cambia al editar (igual que en recolecciones): las
        # líneas de gallinas se validaron contra el galpón original.
        validated_data.pop("id_galpon", None)
        validated_data.pop("categoria", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lineas_data is not None:
            instance.lineas.all().delete()
            for linea_data in lineas_data:
                linea_data["id_galpon"] = instance.id_galpon
                LineaDescarte.objects.create(id_descarte=instance, **linea_data)
        return instance
