from rest_framework import serializers

from .models import Alerta


class AlertaSerializer(serializers.ModelSerializer):
    """
    Una alerta lista para mostrar: además de sus campos trae el tipo, el lote y
    el galpón ya resueltos, para que la pantalla no tenga que pedirlos aparte.
    """

    tipo = serializers.CharField(source="id_tipo_alerta.nombre", read_only=True)
    clave = serializers.CharField(source="id_tipo_alerta.clave", read_only=True)
    severidad = serializers.CharField(source="id_tipo_alerta.severidad", read_only=True)
    severidad_display = serializers.CharField(
        source="id_tipo_alerta.get_severidad_display", read_only=True
    )
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    lote = serializers.CharField(source="id_lote.codigo", read_only=True)
    id_galpon = serializers.IntegerField(source="id_lote.id_galpon_id", read_only=True)
    galpon = serializers.CharField(source="id_lote.id_galpon.galpon", read_only=True)

    class Meta:
        model = Alerta
        fields = [
            "id_alerta",
            "id_tipo_alerta",
            "clave",
            "tipo",
            "severidad",
            "severidad_display",
            "id_lote",
            "lote",
            "id_galpon",
            "galpon",
            "descripcion",
            "estado",
            "estado_display",
            "fecha_generacion",
            "fecha_resolucion",
        ]
        read_only_fields = fields
