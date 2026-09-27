from rest_framework import serializers

from usuarios.models import Usuario
from .models import Galpon, UsuarioDelGalpon


class OperarioResumenSerializer(serializers.ModelSerializer):
    """Representación mínima de un operario para incluirlo en la respuesta de un galpón."""

    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = ["id_usuario", "nombre_completo"]


class GalponSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    # Lectura: lista de objetos {id_usuario, nombre_completo}
    operarios = serializers.SerializerMethodField()

    # Escritura: lista de IDs de usuario (operarios a asignar)
    operarios_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Galpon
        fields = [
            "id_galpon",
            "galpon",
            "latitud",
            "longitud",
            "superficie",
            "capacidad",
            "estado",
            "estado_display",
            "descripcion",
            "operarios",
            "operarios_ids",
        ]
        read_only_fields = ["id_galpon"]

    def get_operarios(self, obj):
        """Solo se listan los operarios actualmente activos.

        La asignación en `UsuarioDelGalpon` se conserva aunque el operario
        sea dado de baja, para no perder el vínculo si luego se reactiva.
        Pero mientras está inactivo, no debe aparecer como operario
        asignado en el detalle del galpón.
        """
        asignaciones = obj.operarios_asignados.select_related("id_usuario").filter(
            id_usuario__estado=Usuario.ESTADO_ACTIVO
        )
        usuarios = [a.id_usuario for a in asignaciones]
        return OperarioResumenSerializer(usuarios, many=True).data

    def validate_capacidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La capacidad debe ser mayor a 0.")
        return value

    def validate_superficie(self, value):
        if value <= 0:
            raise serializers.ValidationError("La superficie debe ser mayor a 0.")
        return value

    def validate_operarios_ids(self, ids):
        """Verifica que todos los IDs correspondan a operarios activos."""
        if not ids:
            return ids
        operarios = Usuario.objects.filter(
            id_usuario__in=ids,
            rol=Usuario.ROL_OPERARIO,
            estado=Usuario.ESTADO_ACTIVO,
        )
        encontrados = set(o.id_usuario for o in operarios)
        invalidos = set(ids) - encontrados
        if invalidos:
            raise serializers.ValidationError(
                f"Los siguientes IDs no corresponden a operarios activos: {sorted(invalidos)}"
            )
        return ids

    def _sincronizar_operarios(self, galpon, ids):
        """Reemplaza los operarios activos asignados al galpón con la lista recibida.

        Solo se tocan las asignaciones de operarios activos. `ids` siempre
        contiene operarios activos (lo garantiza `validate_operarios_ids`),
        y el formulario del frontend solo ofrece operarios activos para
        elegir, así que un operario inactivo nunca puede venir en `ids`.
        Si no excluyéramos las asignaciones de operarios inactivos de este
        reemplazo, guardar el galpón sin tocar el selector (p. ej. al editar
        solo el nombre) borraría también la asignación de cualquier operario
        que haya sido dado de baja, perdiendo el vínculo que `get_operarios`
        conserva a propósito para cuando se reactive.
        """
        UsuarioDelGalpon.objects.filter(
            id_galpon=galpon, id_usuario__estado=Usuario.ESTADO_ACTIVO
        ).delete()
        UsuarioDelGalpon.objects.bulk_create([
            UsuarioDelGalpon(id_usuario_id=uid, id_galpon=galpon)
            for uid in ids
        ])

    def create(self, validated_data):
        ids = validated_data.pop("operarios_ids", [])
        galpon = super().create(validated_data)
        self._sincronizar_operarios(galpon, ids)
        return galpon

    def update(self, instance, validated_data):
        ids = validated_data.pop("operarios_ids", None)
        galpon = super().update(instance, validated_data)
        if ids is not None:
            self._sincronizar_operarios(galpon, ids)
        return galpon
