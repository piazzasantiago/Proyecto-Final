import datetime

from django.db import transaction

from .models import Lote, PlanTransicion


def pasar_a_produccion_vencidos(hoy=None):
    """
    La transición dura como máximo 4 semanas (el plan guarda ese tope en
    fecha_fin). Los lotes en Transición que ya llegaron a ese tope pasan solos a
    Producción: la producción arranca el día en que venció la transición (no el
    día en que alguien abre la pantalla) y el plan queda Finalizado.

    No hay tarea programada: se ejecuta antes de resolver cada consulta de
    lotes, así que el estado siempre está al día. Es idempotente.
    Devuelve la cantidad de lotes que pasaron a Producción.
    """
    hoy = hoy or datetime.date.today()
    vencidos = list(
        Lote.objects.filter(
            estado=Lote.ESTADO_TRANSICION, plan_transicion__fecha_fin__lte=hoy
        ).select_related("plan_transicion")
    )
    pasados = 0
    for lote in vencidos:
        with transaction.atomic():
            actualizados = Lote.objects.filter(
                pk=lote.pk, estado=Lote.ESTADO_TRANSICION
            ).update(
                estado=Lote.ESTADO_PRODUCCION,
                fecha_inicio_produccion=lote.plan_transicion.fecha_fin,
            )
            if actualizados:
                PlanTransicion.objects.filter(pk=lote.plan_transicion.pk).update(
                    estado=PlanTransicion.ESTADO_FINALIZADO
                )
                pasados += 1
    return pasados
