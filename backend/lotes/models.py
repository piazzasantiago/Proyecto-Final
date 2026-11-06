from django.db import models

from galpones.models import Galpon
from config.auditoria import ModeloAuditable


class Lote(ModeloAuditable):
    """
    Corresponde a la tabla 'Lotes' del modelo relacional:
    idLote INT PK, idGalpon INT FK, fechaIngreso DATE, fechaVaciado DATE,
    cantidadInicial INT, cantidadActual INT, estado CHAR(1),
    observaciones MEDIUMTEXT.

    El estado representa la etapa productiva del lote:
        T (Transición) → P (Producción) → F (Finalizado).
    El estado Finalizado se alcanza ejecutando el vaciado sanitario (CU48),
    que además registra automáticamente la fecha_vaciado. Al iniciar la
    producción (CU46) se registra fecha_inicio_produccion: la etapa de
    Producción va desde esa fecha hasta la fecha_vaciado.

    cantidad_actual arranca igual a cantidad_inicial al crear el lote.
    Cuando se implemente feature/descartes, una señal post_save en Descarte
    la recalculará automáticamente: cantidad_actual = cantidad_inicial - Σ descartes.
    El campo existe en la base para evitar recalcular en cada consulta.
    """

    ESTADO_TRANSICION = "T"
    ESTADO_PRODUCCION = "P"
    ESTADO_FINALIZADO = "F"
    ESTADOS_FINALIZADO = ("F",)  # auditoría: estados que cuentan como finalizado
    ESTADO_CHOICES = [
        (ESTADO_TRANSICION, "Transición"),
        (ESTADO_PRODUCCION, "Producción"),
        (ESTADO_FINALIZADO, "Finalizado"),
    ]

    id_lote = models.AutoField(db_column="idLote", primary_key=True)
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="lotes",
    )
    fecha_ingreso = models.DateField()
    fecha_vaciado = models.DateField(null=True, blank=True)
    # Día en que el lote pasó de Transición a Producción (CU46). Es null mientras
    # el lote está en Transición y en los lotes que se vaciaron sin llegar a producir.
    fecha_inicio_produccion = models.DateField(null=True, blank=True)
    cantidad_inicial = models.IntegerField()
    cantidad_actual = models.IntegerField()
    estado = models.CharField(
        max_length=1,
        choices=ESTADO_CHOICES,
        default=ESTADO_TRANSICION,
    )
    observaciones = models.TextField(blank=True, default="")

    class Meta:
        db_table = "Lotes"
        ordering = ["-fecha_ingreso"]
        verbose_name = "lote"
        verbose_name_plural = "lotes"

    @property
    def codigo(self):
        """
        Código legible generado a partir del año de ingreso y el id.
        Ejemplo: L-2026-011
        No es un campo de la base de datos; se calcula al leer el objeto.
        """
        return f"L-{self.fecha_ingreso.year}-{self.id_lote:03d}"

    def __str__(self):
        return f"{self.codigo} ({self.get_estado_display()})"


class PlanTransicion(models.Model):
    """
    Corresponde a la tabla 'PlanesTransicion' del modelo relacional:
    idPlanTransicion INT PK, idLote INT FK (1 a 1), estado CHAR(1),
    fechaInicio DATE, fechaFin DATE, y 12 columnas de manejo semanal
    (agua, alimento, horasLuz × 4 semanas).

    El estado es propio del plan, independiente del estado del lote:
        C (En curso): el lote está atravesando las 4 semanas de transición.
        F (Finalizado): las 4 semanas ya transcurrieron.

    fechaInicio coincide con la fecha de ingreso del lote.
    fechaFin = fechaInicio + 28 días (4 semanas fijas).
    Ambas fechas se calculan automáticamente en el serializer al crear el lote.
    """

    ESTADO_EN_CURSO = "C"
    ESTADO_FINALIZADO = "F"
    ESTADO_CHOICES = [
        (ESTADO_EN_CURSO, "En curso"),
        (ESTADO_FINALIZADO, "Finalizado"),
    ]

    id_plan = models.AutoField(db_column="idPlanTransicion", primary_key=True)
    id_lote = models.OneToOneField(
        Lote,
        on_delete=models.CASCADE,
        db_column="idLote",
        related_name="plan_transicion",
    )
    estado = models.CharField(
        max_length=1,
        choices=ESTADO_CHOICES,
        default=ESTADO_EN_CURSO,
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    # Semana 1
    agua_semana1 = models.DecimalField(max_digits=9, decimal_places=2, db_column="aguaSemana1")
    alimento_semana1 = models.DecimalField(max_digits=9, decimal_places=2, db_column="alimentoSemana1")
    horas_luz_semana1 = models.DecimalField(max_digits=4, decimal_places=2, db_column="horasLuzSemana1")

    # Semana 2
    agua_semana2 = models.DecimalField(max_digits=9, decimal_places=2, db_column="aguaSemana2")
    alimento_semana2 = models.DecimalField(max_digits=9, decimal_places=2, db_column="alimentoSemana2")
    horas_luz_semana2 = models.DecimalField(max_digits=4, decimal_places=2, db_column="horasLuzSemana2")

    # Semana 3
    agua_semana3 = models.DecimalField(max_digits=9, decimal_places=2, db_column="aguaSemana3")
    alimento_semana3 = models.DecimalField(max_digits=9, decimal_places=2, db_column="alimentoSemana3")
    horas_luz_semana3 = models.DecimalField(max_digits=4, decimal_places=2, db_column="horasLuzSemana3")

    # Semana 4
    agua_semana4 = models.DecimalField(max_digits=9, decimal_places=2, db_column="aguaSemana4")
    alimento_semana4 = models.DecimalField(max_digits=9, decimal_places=2, db_column="alimentoSemana4")
    horas_luz_semana4 = models.DecimalField(max_digits=4, decimal_places=2, db_column="horasLuzSemana4")

    class Meta:
        db_table = "PlanesTransicion"
        verbose_name = "plan de transición"
        verbose_name_plural = "planes de transición"

    def __str__(self):
        return f"Plan de transición — {self.id_lote.codigo} ({self.get_estado_display()})"
