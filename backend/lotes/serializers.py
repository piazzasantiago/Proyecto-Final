import datetime

from rest_framework import serializers

from galpones.models import Galpon
from .models import Lote, PlanTransicion


class PlanTransicionSerializer(serializers.ModelSerializer):
    """
    Serializer del plan de transición.
    Se usa embebido dentro de LoteSerializer: no tiene endpoint propio.
    En lectura devuelve todos los campos del plan.
    En escritura acepta solo los 12 campos de manejo semanal; el resto
    (id_lote, estado, fecha_inicio, fecha_fin) los calcula LoteSerializer.
    """

    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = PlanTransicion
        fields = [
            "id_plan",
            "estado",
            "estado_display",
            "fecha_inicio",
            "fecha_fin",
            "agua_semana1",
            "alimento_semana1",
            "horas_luz_semana1",
            "agua_semana2",
            "alimento_semana2",
            "horas_luz_semana2",
            "agua_semana3",
            "alimento_semana3",
            "horas_luz_semana3",
            "agua_semana4",
            "alimento_semana4",
            "horas_luz_semana4",
        ]
        read_only_fields = ["id_plan", "estado", "estado_display", "fecha_inicio", "fecha_fin"]

    def validate_agua_semana1(self, value):
        if value <= 0:
            raise serializers.ValidationError("El agua debe ser mayor a 0.")
        return value

    def validate_agua_semana2(self, value):
        if value <= 0:
            raise serializers.ValidationError("El agua debe ser mayor a 0.")
        return value

    def validate_agua_semana3(self, value):
        if value <= 0:
            raise serializers.ValidationError("El agua debe ser mayor a 0.")
        return value

    def validate_agua_semana4(self, value):
        if value <= 0:
            raise serializers.ValidationError("El agua debe ser mayor a 0.")
        return value

    def validate_alimento_semana1(self, value):
        if value <= 0:
            raise serializers.ValidationError("El alimento debe ser mayor a 0.")
        return value

    def validate_alimento_semana2(self, value):
        if value <= 0:
            raise serializers.ValidationError("El alimento debe ser mayor a 0.")
        return value

    def validate_alimento_semana3(self, value):
        if value <= 0:
            raise serializers.ValidationError("El alimento debe ser mayor a 0.")
        return value

    def validate_alimento_semana4(self, value):
        if value <= 0:
            raise serializers.ValidationError("El alimento debe ser mayor a 0.")
        return value

    def validate_horas_luz_semana1(self, value):
        if value <= 0 or value > 24:
            raise serializers.ValidationError("Las horas de luz deben estar entre 0 y 24.")
        return value

    def validate_horas_luz_semana2(self, value):
        if value <= 0 or value > 24:
            raise serializers.ValidationError("Las horas de luz deben estar entre 0 y 24.")
        return value

    def validate_horas_luz_semana3(self, value):
        if value <= 0 or value > 24:
            raise serializers.ValidationError("Las horas de luz deben estar entre 0 y 24.")
        return value

    def validate_horas_luz_semana4(self, value):
        if value <= 0 or value > 24:
            raise serializers.ValidationError("Las horas de luz deben estar entre 0 y 24.")
        return value


class GalponResumenSerializer(serializers.ModelSerializer):
    """Representación mínima de un galpón para incluirlo en la respuesta de un lote."""

    class Meta:
        model = Galpon
        fields = ["id_galpon", "galpon"]


class LoteSerializer(serializers.ModelSerializer):
    """
    Serializer principal del módulo de lotes.

    Lectura:
    - codigo: propiedad calculada del modelo (L-YYYY-NNN).
    - estado_display: texto legible del estado del lote.
    - edad_semanas: semanas transcurridas desde fecha_ingreso hasta hoy.
    - galpon: objeto {id_galpon, galpon} para mostrar en el frontend.
    - plan_transicion: objeto completo con todas las semanas.

    Escritura:
    - id_galpon_id: ID del galpón a asignar.
    - plan_transicion: los 12 campos de manejo semanal. El serializer
      calcula y guarda automáticamente fecha_inicio, fecha_fin y estado.
    - cantidad_actual se inicializa igual a cantidad_inicial al crear.
    - fecha_vaciado no se acepta en escritura: la completa la acción /vaciar/.
    - estado no se acepta en escritura: lo cambian las acciones
      /iniciar-produccion/ y /vaciar/.
    """

    codigo = serializers.CharField(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    edad_semanas = serializers.SerializerMethodField()

    # Lectura: objeto con id y nombre del galpón
    galpon = GalponResumenSerializer(source="id_galpon", read_only=True)

    # Escritura: ID del galpón
    id_galpon_id = serializers.PrimaryKeyRelatedField(
        queryset=Galpon.objects.filter(estado=Galpon.ESTADO_ACTIVO),
        source="id_galpon",
        write_only=True,
    )

    # Lectura y escritura: plan de transición embebido
    plan_transicion = PlanTransicionSerializer()

    class Meta:
        model = Lote
        fields = [
            "id_lote",
            "codigo",
            "id_galpon_id",
            "galpon",
            "fecha_ingreso",
            "fecha_vaciado",
            "cantidad_inicial",
            "cantidad_actual",
            "estado",
            "estado_display",
            "edad_semanas",
            "observaciones",
            "plan_transicion",
        ]
        read_only_fields = [
            "id_lote",
            "cantidad_actual",
            "fecha_vaciado",
            "estado",
        ]

    def get_edad_semanas(self, obj):
        """Semanas completas transcurridas desde la fecha de ingreso hasta hoy."""
        hoy = datetime.date.today()
        delta = hoy - obj.fecha_ingreso
        return delta.days // 7

    def validate_cantidad_inicial(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad inicial debe ser mayor a 0.")
        return value

    def validate_fecha_ingreso(self, value):
        if value > datetime.date.today():
            raise serializers.ValidationError(
                "La fecha de ingreso no puede ser una fecha futura."
            )
        return value

    def validate(self, data):
        """
        Valida que el galpón no tenga ya un lote activo (estado T o P).
        Un galpón solo puede albergar un lote a la vez; para admitir uno nuevo
        el lote anterior debe estar en estado Finalizado (F).

        En edición (PATCH) se omite esta validación porque id_galpon no cambia.
        """
        galpon = data.get("id_galpon")

        # En PATCH el campo puede no venir; si no viene, no hay nada que validar.
        if galpon is None:
            return data

        # En edición, self.instance ya existe; excluimos el lote actual de la consulta
        # para no bloquearnos a nosotros mismos (aunque id_galpon es inmutable en el
        # formulario, es una buena práctica defensiva).
        qs = Lote.objects.filter(
            id_galpon=galpon,
            estado__in=[Lote.ESTADO_TRANSICION, Lote.ESTADO_PRODUCCION],
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            lote_activo = qs.first()
            raise serializers.ValidationError({
                "id_galpon_id": (
                    f"El galpón ya tiene un lote activo ({lote_activo.codigo}, "
                    f"estado: {lote_activo.get_estado_display()}). "
                    "Solo se puede asignar un nuevo lote cuando el anterior esté Finalizado."
                )
            })

        return data

    def create(self, validated_data):
        plan_data = validated_data.pop("plan_transicion")
        fecha_ingreso = validated_data["fecha_ingreso"]

        # cantidad_actual arranca igual a cantidad_inicial
        validated_data["cantidad_actual"] = validated_data["cantidad_inicial"]

        lote = Lote.objects.create(**validated_data)

        # fecha_inicio = fecha de ingreso del lote
        # fecha_fin = fecha_inicio + 28 días (4 semanas fijas)
        fecha_inicio = fecha_ingreso
        fecha_fin = fecha_inicio + datetime.timedelta(days=28)

        PlanTransicion.objects.create(
            id_lote=lote,
            estado=PlanTransicion.ESTADO_EN_CURSO,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            **plan_data,
        )

        return lote

    def update(self, instance, validated_data):
        plan_data = validated_data.pop("plan_transicion", None)
        lote = super().update(instance, validated_data)

        if plan_data is not None:
            plan = lote.plan_transicion
            for campo, valor in plan_data.items():
                setattr(plan, campo, valor)
            plan.save()

        return lote
