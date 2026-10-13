from django.db import models

from galpones.models import Galpon
from lotes.models import Lote
from productos.models import Producto
from usuarios.models import Usuario


class Recoleccion(models.Model):
    """
    Cabecera de una recolección diaria.

    Una recolección agrupa las líneas de productos recolectados en un galpón
    en una fecha y hora determinadas.

    El campo id_lote guarda el lote activo del galpón en el momento de crear la
    recolección (Opción B). Esto garantiza que el historial quede intacto aunque
    el lote del galpón cambie posteriormente (vaciado sanitario → nuevo lote).

    Un galpón debe tener un lote activo (estado T o P) para poder registrar una
    recolección; si no lo tiene, la API devuelve 400.

    El campo id_usuario registra quién cargó la recolección (se inyecta
    automáticamente desde request.user en perform_create).

    El campo estado refleja el ciclo de vida de la recolección:
        P (Pendiente): recién creada, editable.
        F (Finalizada): confirmada, de solo lectura.
    """

    ESTADO_PENDIENTE = "P"
    ESTADO_FINALIZADA = "F"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_FINALIZADA, "Finalizada"),
    ]

    id_recoleccion = models.AutoField(db_column="idRecoleccion", primary_key=True)
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="recolecciones",
    )
    id_lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        db_column="idLote",
        related_name="recolecciones",
        null=True,
        blank=True,
    )
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="recolecciones",
        null=True,
        blank=True,
    )
    fecha = models.DateTimeField()
    estado = models.CharField(
        max_length=1,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
    )
    observaciones = models.TextField(blank=True, default="")

    class Meta:
        db_table = "Recolecciones"
        ordering = ["-fecha"]
        verbose_name = "recolección"
        verbose_name_plural = "recolecciones"

    def __str__(self):
        return f"Recolección {self.id_recoleccion} — {self.id_galpon} ({self.fecha:%d/%m/%Y})"


class LineaRecoleccion(models.Model):
    """
    Línea de una recolección: galpón + producto + cantidad.

    El campo id_galpon se propaga desde la cabecera al guardar.
    """

    id_linea_recoleccion = models.AutoField(db_column="idLineaRecoleccion", primary_key=True)
    id_recoleccion = models.ForeignKey(
        Recoleccion,
        on_delete=models.CASCADE,
        db_column="idRecoleccion",
        related_name="lineas",
    )
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="lineas_recoleccion",
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="lineas_recoleccion",
    )
    cantidad = models.PositiveIntegerField()

    class Meta:
        db_table = "LineasRecoleccion"
        verbose_name = "línea de recolección"
        verbose_name_plural = "líneas de recolección"

    def __str__(self):
        return f"Línea {self.id_linea_recoleccion} — {self.id_producto} x{self.cantidad}"
