"""
Generación y resolución automática de alertas.

Las alertas no las carga nadie: el sistema evalúa las reglas
(alertas/reglas.py) y mantiene la tabla al día.

    · La situación aparece  → se crea la alerta Pendiente.
    · La situación sigue    → se actualiza la descripción (el dato cambia: hoy
                              faltan 2 días y mañana 1).
    · La situación se va    → la alerta pasa a Resuelta y queda en el historial.

No hay tarea programada: se ejecuta antes de resolver cada consulta de alertas
y del dashboard, igual que la transición automática de los lotes
(lotes/transiciones.py). Es idempotente: ejecutarla dos veces seguidas no
cambia nada.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from lotes.transiciones import pasar_a_produccion_vencidos

from . import reglas
from .models import Alerta, TipoAlerta


def generar_alertas(hoy=None):
    """
    Pone al día las alertas y devuelve (creadas, resueltas).

    Primero se actualiza el estado de los lotes, porque las reglas dependen de
    él (un lote que vence hoy su transición ya es un lote en producción).
    """
    hoy = hoy or timezone.localdate()
    pasar_a_produccion_vencidos(hoy)

    tipos = {t.clave: t for t in TipoAlerta.objects.all()}
    ahora = timezone.now()
    creadas = resueltas = 0

    for clave, situaciones in reglas.evaluar(hoy).items():
        tipo = tipos.get(clave)
        if tipo is None:
            # El tipo todavía no existe en la base (migración de datos sin
            # aplicar): no se inventa, se ignora la regla.
            continue

        pendientes = {
            alerta.id_lote_id: alerta
            for alerta in Alerta.objects.filter(
                id_tipo_alerta=tipo, estado=Alerta.ESTADO_PENDIENTE
            )
        }

        for id_lote, descripcion in situaciones.items():
            alerta = pendientes.get(id_lote)
            if alerta is None:
                creadas += _crear(tipo, id_lote, descripcion, ahora)
            elif alerta.descripcion != descripcion:
                Alerta.objects.filter(pk=alerta.pk).update(descripcion=descripcion)

        a_resolver = [
            alerta.pk for id_lote, alerta in pendientes.items() if id_lote not in situaciones
        ]
        if a_resolver:
            resueltas += Alerta.objects.filter(pk__in=a_resolver).update(
                estado=Alerta.ESTADO_RESUELTA, fecha_resolucion=ahora
            )

    return creadas, resueltas


def _crear(tipo, id_lote, descripcion, ahora):
    """
    Crea la alerta. Si dos pedidos entran a la vez, la restricción
    «alerta_pendiente_unica» deja pasar solo a uno: el otro no es un error.
    """
    try:
        with transaction.atomic():
            Alerta.objects.create(
                id_lote_id=id_lote,
                id_tipo_alerta=tipo,
                descripcion=descripcion,
                estado=Alerta.ESTADO_PENDIENTE,
                fecha_generacion=ahora,
            )
        return 1
    except IntegrityError:
        return 0
