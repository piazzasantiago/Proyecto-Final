import datetime

from django.db import transaction
from rest_framework import serializers

from compras.models import Compra, LineaCompra
from galpones.models import Galpon
from .models import Lote, PlanTransicion


def _miles(n):
    """Número entero con punto como separador de miles (2500 → 2.500)."""
    return f"{int(n):,}".replace(",", ".")


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
    - id_linea_compra: el lote comprado que se asigna al galpón (obligatorio al
      crear). Un lote no se crea "de la nada": tiene que venir de una compra de
      lotes finalizada que todavía no se haya asignado. La cantidad inicial
      sale de esa compra (lo que se envíe en cantidad_inicial se ignora).
    - cantidad_actual se inicializa igual a cantidad_inicial al crear.
    - fecha_vaciado y fecha_inicio_produccion no se aceptan en escritura: las
      completan las acciones /vaciar/ e /iniciar-produccion/.
    - El galpón tiene que tener capacidad para todas las aves del lote.
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

    # Escritura: línea de la compra de lotes de la que sale este lote.
    id_linea_compra = serializers.IntegerField(write_only=True, required=False)
    # En lectura: de qué compra viene (None en lotes cargados antes de Compras).
    compra = serializers.SerializerMethodField()
    # Al crear sale de la compra; en lotes viejos sin compra se puede corregir.
    cantidad_inicial = serializers.IntegerField(required=False)

    class Meta:
        model = Lote
        fields = [
            "id_lote",
            "codigo",
            "id_galpon_id",
            "id_linea_compra",
            "compra",
            "galpon",
            "fecha_ingreso",
            "fecha_inicio_produccion",
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
            "fecha_inicio_produccion",
            "fecha_vaciado",
            "estado",
        ]

    def get_edad_semanas(self, obj):
        """Semanas completas transcurridas desde la fecha de ingreso hasta hoy."""
        hoy = datetime.date.today()
        delta = hoy - obj.fecha_ingreso
        return delta.days // 7

    def get_compra(self, obj):
        linea = getattr(obj, "linea_compra", None)
        if linea is None:
            return None
        compra = linea.id_compra
        return {
            "id_compra": compra.pk,
            "nro_factura": compra.nro_factura,
            "proveedor": compra.id_proveedor.nombre,
        }

    def _linea_a_asignar(self, id_linea):
        """
        Línea de compra de lotes que se va a asignar. Un lote no se crea sin una
        compra de lotes finalizada que lo respalde.
        """
        if id_linea is None:
            if not Compra.objects.filter(
                categoria=Compra.CATEGORIA_LOTES,
                estado=Compra.ESTADO_FINALIZADA,
                lineas__id_lote__isnull=True,
            ).exists():
                raise serializers.ValidationError({
                    "id_linea_compra": (
                        "No hay lotes comprados esperando un galpón. Registrá y "
                        "finalizá primero una compra de lotes."
                    )
                })
            raise serializers.ValidationError({
                "id_linea_compra": "Seleccioná el lote comprado que querés asignar a un galpón."
            })
        linea = LineaCompra.objects.filter(
            pk=id_linea,
            id_compra__categoria=Compra.CATEGORIA_LOTES,
            id_compra__estado=Compra.ESTADO_FINALIZADA,
        ).first()
        if linea is None:
            raise serializers.ValidationError({
                "id_linea_compra": "El lote seleccionado no está disponible para asignar."
            })
        if linea.id_lote_id is not None:
            raise serializers.ValidationError({
                "id_linea_compra": "Ese lote ya fue asignado a un galpón."
            })
        return linea

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

        Al crear, además, el lote tiene que venir de una compra de lotes
        finalizada y todavía sin asignar; su cantidad inicial es la comprada.
        """
        id_linea = data.pop("id_linea_compra", None)
        if self.instance is None:
            self._linea = self._linea_a_asignar(id_linea)
            data["cantidad_inicial"] = int(self._linea.cantidad)
        else:
            # Un lote que viene de una compra conserva la cantidad comprada.
            linea = getattr(self.instance, "linea_compra", None)
            nueva = data.get("cantidad_inicial")
            if linea is not None and nueva is not None and nueva != self.instance.cantidad_inicial:
                raise serializers.ValidationError({
                    "cantidad_inicial": (
                        "La cantidad inicial viene de la compra y no se puede modificar."
                    )
                })

        galpon = data.get("id_galpon")

        # En PATCH el campo puede no venir; si no viene, no hay nada que validar.
        if galpon is None:
            return data

        # El galpón tiene que tener lugar para todas las aves del lote.
        cantidad = data.get("cantidad_inicial")
        if cantidad is None and self.instance is not None:
            cantidad = self.instance.cantidad_inicial
        if cantidad is not None and cantidad > galpon.capacidad:
            raise serializers.ValidationError({
                "id_galpon_id": (
                    f"El galpón {galpon.galpon} tiene capacidad para "
                    f"{_miles(galpon.capacidad)} aves y el lote tiene {_miles(cantidad)}. "
                    "Elegí un galpón con mayor capacidad."
                )
            })

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

        with transaction.atomic():
            # Se bloquea la línea de la compra: dos altas simultáneas no pueden
            # asignar el mismo lote comprado.
            linea = LineaCompra.objects.select_for_update().get(pk=self._linea.pk)
            if linea.id_lote_id is not None:
                raise serializers.ValidationError({
                    "id_linea_compra": "Ese lote ya fue asignado a un galpón."
                })

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

            linea.id_lote = lote
            linea.save(update_fields=["id_lote"])

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
