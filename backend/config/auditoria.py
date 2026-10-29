"""
Auditoría de los registros (F-23).

``ModeloAuditable`` es una clase base abstracta que heredan los modelos
principales. Guarda quién y cuándo creó, editó y finalizó cada registro. Los
campos se completan solos en ``save()``, tomando al usuario de la petición en
curso, así que las vistas no tienen que acordarse de pasarlo.

- Alta: ``creado_por`` y ``fecha_creacion``.
- Edición (o cambio de estado que no sea finalizar): ``editado_por`` y ``fecha_editado``.
- Finalización (el estado pasa a uno de ``ESTADOS_FINALIZADO``): ``finalizado_por``
  y ``fecha_finalizado``.

Los cambios que no vienen de una persona (por ejemplo, la transición automática
de un lote) quedan con la fecha pero sin usuario ("Sistema" en la pantalla).
Los registros anteriores a la auditoría no tienen fechas: se muestran como
«Sin registro».
"""

from contextvars import ContextVar

from django.db import models
from django.utils import timezone

# Usuario de la petición en curso (lo fija AuditoriaMixin en cada vista).
_usuario_actual = ContextVar("auditoria_usuario_actual", default=None)

# Campos que no cuentan como una edición del registro.
_CAMPOS_SIN_AUDITORIA = {"last_login"}


def usuario_actual():
    return _usuario_actual.get()


class ModeloAuditable(models.Model):
    """Campos y comportamiento de auditoría comunes a los modelos principales."""

    # Estados que significan «finalizado» (vacío: el modelo no tiene ese concepto).
    ESTADOS_FINALIZADO = ()

    creado_por = models.ForeignKey(
        "usuarios.Usuario", null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    editado_por = models.ForeignKey(
        "usuarios.Usuario", null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    finalizado_por = models.ForeignKey(
        "usuarios.Usuario", null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="+",
    )
    fecha_creacion = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_editado = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_finalizado = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):
        instancia = super().from_db(db, field_names, values)
        # Estado con el que se leyó el registro: permite detectar que pasó a finalizado.
        instancia._estado_previo = instancia.__dict__.get("estado")
        return instancia

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and set(update_fields) <= _CAMPOS_SIN_AUDITORIA:
            return super().save(*args, **kwargs)

        usuario = usuario_actual()
        ahora = timezone.now()
        estado = self.__dict__.get("estado")
        finaliza_ahora = estado in self.ESTADOS_FINALIZADO
        tocados = []

        if self._state.adding:
            if self.creado_por_id is None:
                self.creado_por = usuario
            if self.fecha_creacion is None:
                self.fecha_creacion = ahora
            tocados += ["creado_por", "fecha_creacion"]
            if finaliza_ahora:
                self.finalizado_por, self.fecha_finalizado = usuario, ahora
                tocados += ["finalizado_por", "fecha_finalizado"]
        else:
            previo = getattr(self, "_estado_previo", None)
            if finaliza_ahora and previo is not None and previo not in self.ESTADOS_FINALIZADO:
                self.finalizado_por, self.fecha_finalizado = usuario, ahora
                tocados += ["finalizado_por", "fecha_finalizado"]
            else:
                self.editado_por, self.fecha_editado = usuario, ahora
                tocados += ["editado_por", "fecha_editado"]

        if update_fields is not None:
            kwargs["update_fields"] = list(set(update_fields) | set(tocados))
        super().save(*args, **kwargs)
        self._estado_previo = estado


class AuditoriaMixin:
    """
    Mixin para los ViewSets: deja disponible al usuario autenticado para
    ``ModeloAuditable.save()`` y trae los usuarios de la auditoría en la misma
    consulta (sin una consulta extra por fila).
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        usuario = request.user if request.user and request.user.is_authenticated else None
        self._auditoria_token = _usuario_actual.set(usuario)

    def dispatch(self, request, *args, **kwargs):
        # try/finally: si la vista falla con una excepción inesperada, DRF no llega a
        # finalize_response, y el usuario quedaría puesto para la petición siguiente.
        self._auditoria_token = None
        try:
            return super().dispatch(request, *args, **kwargs)
        finally:
            if self._auditoria_token is not None:
                _usuario_actual.reset(self._auditoria_token)
                self._auditoria_token = None

    def filter_queryset(self, queryset):
        # Se hace acá (y no en get_queryset) porque varias vistas arman su propio
        # queryset sin llamar a super().get_queryset().
        queryset = super().filter_queryset(queryset)
        if hasattr(queryset, "select_related"):
            queryset = queryset.select_related("creado_por", "editado_por", "finalizado_por")
        return queryset


def _persona(usuario):
    if usuario is None:
        return None
    return {"nombre": usuario.nombre_completo, "usuario": usuario.usuario}


def _evento(usuario, fecha):
    return {
        "fecha": fecha.isoformat() if fecha else None,
        "por": _persona(usuario),
    }


def auditoria_de(obj):
    """Datos de auditoría de un registro, listos para el JSON."""
    return {
        "creado": _evento(obj.creado_por, obj.fecha_creacion),
        "editado": _evento(obj.editado_por, obj.fecha_editado),
        "finalizado": _evento(obj.finalizado_por, obj.fecha_finalizado),
    }


def puede_ver_auditoria(request):
    """La auditoría es visible para Administrador y Consulta (no para Operario)."""
    usuario = getattr(request, "user", None)
    return bool(
        usuario
        and usuario.is_authenticated
        and getattr(usuario, "rol", None) in ("A", "C")
    )


class AuditoriaSerializerMixin:
    """Agrega ``auditoria`` a la respuesta, solo para los roles que pueden verla."""

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and puede_ver_auditoria(request):
            datos["auditoria"] = auditoria_de(instance)
        return datos
