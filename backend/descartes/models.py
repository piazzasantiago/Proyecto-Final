from django.db import models

from galpones.models import Galpon
from lotes.models import Lote
from materias_primas.models import MateriaPrima
from productos.models import Producto
from usuarios.models import Usuario
from config.auditoria import ModeloAuditable


class Descarte(ModeloAuditable):
    """
    Cabecera de un descarte (CU15–CU19).

    Un descarte tiene una CATEGORÍA que define de dónde sale lo descartado y
    qué efecto tiene al finalizarlo:

    · Galpón (G): ocurre dentro de un galpón (una gallina que muere o deja de
      producir, alimento ya servido que se pudrió, un nidal roto, huevos rotos
      encontrados, etc.). Lleva el galpón en id_galpon. Sirve sobre todo para
      estadísticas: NO reduce stock de productos ni de materias primas. La
      única excepción son las líneas de gallinas (lote), que al finalizar
      descuentan cantidad_actual del lote.

    · Stock (S): baja de lo que ya está almacenado (huevos recolectados,
      materias primas listas para consumir). No pertenece a ningún galpón
      (id_galpon queda vacío) y SÍ reduce el stock de los productos y de las
      materias primas descartados una vez finalizado.

    Ciclo de vida: P (Pendiente) → F (Finalizado).
    Mientras está Pendiente es editable (CU17) y borrable (CU18). Al
    finalizarlo (CU19) queda de solo lectura y aplica su efecto.
    """

    CATEGORIA_GALPON = "G"
    CATEGORIA_STOCK = "S"
    CATEGORIA_CHOICES = [
        (CATEGORIA_GALPON, "Galpón"),
        (CATEGORIA_STOCK, "Stock"),
    ]

    ESTADO_PENDIENTE = "P"
    ESTADO_FINALIZADO = "F"
    ESTADOS_FINALIZADO = ("F",)  # auditoría: estados que cuentan como finalizado
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_FINALIZADO, "Finalizado"),
    ]

    id_descarte = models.AutoField(db_column="idDescarte", primary_key=True)
    categoria = models.CharField(
        max_length=1,
        choices=CATEGORIA_CHOICES,
        default=CATEGORIA_GALPON,
    )
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="descartes",
        null=True,
        blank=True,
    )
    # Quién cargó el descarte. Se inyecta desde la vista con el usuario
    # autenticado (igual que en Recolecciones); nunca lo envía el cliente.
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="descartes",
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
        db_table = "Descartes"
        ordering = ["-fecha"]
        verbose_name = "descarte"
        verbose_name_plural = "descartes"

    def __str__(self):
        origen = self.id_galpon if self.id_galpon_id else "Stock"
        return (
            f"Descarte {self.id_descarte} — {origen} "
            f"({self.fecha:%d/%m/%Y}) [{self.get_estado_display()}]"
        )


class LineaDescarte(models.Model):
    """
    Línea de un descarte: identifica el ítem descartado y la cantidad.

    Exactamente uno de los tres campos de ítem debe estar relleno:
        · id_materia_prima → insumos (balanceado, vacunas, nidales, etc.)
        · id_producto      → productos (huevos, etc.)
        · id_lote          → gallinas de un lote (solo en descartes de galpón)

    Las validaciones de exclusividad y de coherencia con la categoría de la
    cabecera se hacen en el serializer, no en el modelo.

    El campo id_galpon se propaga desde la cabecera al crear (queda vacío en
    los descartes de stock).
    """

    id_linea_descarte = models.AutoField(db_column="idLineaDescarte", primary_key=True)
    id_descarte = models.ForeignKey(
        Descarte,
        on_delete=models.CASCADE,
        db_column="idDescarte",
        related_name="lineas",
    )
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="lineas_descarte",
        null=True,
        blank=True,
    )

    # ── Ítem descartado (exactamente uno) ────────────────────────────────────
    id_materia_prima = models.ForeignKey(
        MateriaPrima,
        on_delete=models.PROTECT,
        db_column="idMateriaPrima",
        related_name="lineas_descarte",
        null=True,
        blank=True,
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="lineas_descarte",
        null=True,
        blank=True,
    )
    id_lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        db_column="idLote",
        related_name="lineas_descarte",
        null=True,
        blank=True,
    )

    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=200)

    class Meta:
        db_table = "LineasDescarte"
        verbose_name = "línea de descarte"
        verbose_name_plural = "líneas de descarte"

    @property
    def tipo(self):
        """Devuelve el tipo de ítem: 'materia_prima', 'producto' o 'lote'."""
        if self.id_materia_prima_id:
            return "materia_prima"
        if self.id_producto_id:
            return "producto"
        if self.id_lote_id:
            return "lote"
        return None

    def __str__(self):
        return f"Línea {self.id_linea_descarte} — {self.tipo} x{self.cantidad}"
