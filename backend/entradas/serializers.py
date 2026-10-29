from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from descartes.serializers import GalponResumenSerializer
from descartes.stock import verificar_stock
from galpones.models import Galpon
from materias_primas.models import MateriaPrima
from recolecciones.serializers import UsuarioResumenSerializer

from .models import Entrada, LineaEntrada
from config.auditoria import AuditoriaSerializerMixin

# Tope sensato por línea (evita cargas absurdas por error de tipeo).
CANTIDAD_MAX = Decimal("1000000")


# ── Línea ─────────────────────────────────────────────────────────────────────

class LineaEntradaSerializer(serializers.ModelSerializer):
    materia_prima_nombre = serializers.CharField(
        source="id_materia_prima.materia_prima", read_only=True
    )
    materia_prima_unidad = serializers.CharField(
        source="id_materia_prima.unidad", read_only=True
    )
    # Se acepta cualquier materia prima existente; que esté activa se valida en
    # la cabecera, porque una entrada que se edita conserva las que ya tenía.
    id_materia_prima = serializers.PrimaryKeyRelatedField(
        queryset=MateriaPrima.objects.all()
    )
    cantidad = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=CANTIDAD_MAX,
    )

    class Meta:
        model = LineaEntrada
        fields = [
            "id_linea_entrada",
            "id_materia_prima",
            "materia_prima_nombre",
            "materia_prima_unidad",
            "cantidad",
        ]
        read_only_fields = ["id_linea_entrada"]


# ── Cabecera ──────────────────────────────────────────────────────────────────

class EntradaSerializer(AuditoriaSerializerMixin, serializers.ModelSerializer):
    galpon = GalponResumenSerializer(source="id_galpon", read_only=True)
    usuario = UsuarioResumenSerializer(source="id_usuario", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    items_count = serializers.SerializerMethodField()
    lineas = LineaEntradaSerializer(many=True)

    id_galpon = serializers.PrimaryKeyRelatedField(
        queryset=Galpon.objects.filter(estado=Galpon.ESTADO_ACTIVO),
        required=False,
    )

    class Meta:
        model = Entrada
        fields = [
            "id_entrada",
            "galpon",
            "id_galpon",
            "usuario",  # read-only; se asigna en perform_create de la vista
            "fecha",
            "estado",
            "estado_display",
            "observaciones",
            "items_count",
            "lineas",
        ]
        read_only_fields = ["id_entrada", "estado"]
        extra_kwargs = {"observaciones": {"max_length": 500}}

    def get_items_count(self, obj):
        return obj.lineas.count()

    # ── Validaciones ──────────────────────────────────────────────────────────

    def validate_fecha(self, value):
        """Una entrada registra algo que ya ocurrió: no admite fechas futuras."""
        if value > timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora de la entrada no pueden ser futuras."
            )
        return value

    def validate_lineas(self, lineas):
        if not lineas:
            raise serializers.ValidationError(
                "La entrada debe tener al menos una línea."
            )
        return lineas

    def validate(self, data):
        if self.instance is not None:
            if self.instance.estado == Entrada.ESTADO_FINALIZADA:
                raise serializers.ValidationError(
                    "Entrada finalizada. No se puede editar."
                )
        elif data.get("id_galpon") is None:
            raise serializers.ValidationError(
                {"id_galpon": "El galpón es obligatorio para crear una entrada."}
            )

        lineas = data.get("lineas")
        if lineas is None:
            return data

        # No se repite la misma materia prima dentro de una entrada.
        vistas = set()
        for linea in lineas:
            mp = linea["id_materia_prima"]
            if mp.pk in vistas:
                raise serializers.ValidationError(
                    {"lineas": f"La materia prima '{mp.materia_prima}' está repetida en la entrada."}
                )
            vistas.add(mp.pk)

        # Solo materias primas activas. Una entrada que se edita conserva las que
        # ya tenía aunque se hayan dado de baja después.
        ya_cargadas = set()
        if self.instance is not None:
            ya_cargadas = set(
                self.instance.lineas.values_list("id_materia_prima_id", flat=True)
            )
        for linea in lineas:
            mp = linea["id_materia_prima"]
            if mp.estado != MateriaPrima.ESTADO_ACTIVO and mp.pk not in ya_cargadas:
                raise serializers.ValidationError(
                    {"lineas": f"La materia prima '{mp.materia_prima}' está inactiva."}
                )

        # Aviso temprano: debe alcanzar el stock (se vuelve a verificar al finalizar).
        error = verificar_stock(
            [(l["id_materia_prima"], l["cantidad"]) for l in lineas], accion="ingresar"
        )
        if error:
            raise serializers.ValidationError({"lineas": error})
        return data

    # ── Escritura ─────────────────────────────────────────────────────────────

    def create(self, validated_data):
        lineas_data = validated_data.pop("lineas")
        entrada = Entrada.objects.create(**validated_data)
        for linea_data in lineas_data:
            LineaEntrada.objects.create(id_entrada=entrada, **linea_data)
        return entrada

    def update(self, instance, validated_data):
        lineas_data = validated_data.pop("lineas", None)
        # El galpón no se cambia al editar una entrada ya creada.
        nuevo_galpon = validated_data.pop("id_galpon", None)
        if nuevo_galpon is not None and nuevo_galpon != instance.id_galpon:
            raise serializers.ValidationError(
                {"id_galpon": "No se puede cambiar el galpón de una entrada existente."}
            )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lineas_data is not None:
            instance.lineas.all().delete()
            for linea_data in lineas_data:
                LineaEntrada.objects.create(id_entrada=instance, **linea_data)
        return instance
