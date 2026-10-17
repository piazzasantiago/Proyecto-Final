from decimal import Decimal

from django.db import models

from lotes.models import Lote
from materias_primas.models import MateriaPrima
from proveedores.models import Proveedor
from usuarios.models import Usuario


class Compra(models.Model):
    """
    Cabecera de una compra a un proveedor.

    Tiene una CATEGORÍA que define qué se compra y qué efecto tiene al
    finalizarla:

    · Materias primas (M): cada línea es una materia prima ya existente en el
      sistema y una cantidad. Al finalizar, la cantidad se SUMA al stock de la
      materia prima. Si la materia prima todavía no existe hay que crearla antes
      desde la sección Materias Primas.

    · Lotes (L): cada línea es un lote de gallinas (cantidad de aves). Al
      finalizar no se crea ningún lote: la línea queda como "lote a asignar",
      pendiente de un galpón. Recién cuando se crea el lote en Lotes de gallinas
      eligiendo esa línea, el lote queda vinculado a la compra y empieza su ciclo
      productivo.

    Ciclo de vida: P (Pendiente) → F (Finalizada). Mientras está Pendiente se
    puede editar y borrar; al finalizarla queda de solo lectura y aplica su
    efecto. Una compra finalizada no se borra: ya movió stock o dejó lotes
    esperando un galpón.
    """

    CATEGORIA_MATERIAS_PRIMAS = "M"
    CATEGORIA_LOTES = "L"
    CATEGORIA_CHOICES = [
        (CATEGORIA_MATERIAS_PRIMAS, "Materias primas"),
        (CATEGORIA_LOTES, "Lotes"),
    ]

    TIPO_CONTADO = "C"
    TIPO_CUENTA_CORRIENTE = "X"
    TIPO_CHOICES = [
        (TIPO_CONTADO, "Contado"),
        (TIPO_CUENTA_CORRIENTE, "Cuenta corriente"),
    ]

    ESTADO_PENDIENTE = "P"
    ESTADO_FINALIZADA = "F"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_FINALIZADA, "Finalizada"),
    ]

    id_compra = models.AutoField(db_column="idCompra", primary_key=True)
    id_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        db_column="idProveedor",
        related_name="compras",
    )
    # Quién cargó la compra. Se inyecta desde la vista con el usuario
    # autenticado; nunca lo envía el cliente.
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="compras",
        null=True,
        blank=True,
    )
    categoria = models.CharField(max_length=1, choices=CATEGORIA_CHOICES)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, default=TIPO_CONTADO)
    nro_factura = models.CharField(db_column="nroFactura", max_length=20)
    fecha = models.DateField()
    estado = models.CharField(
        max_length=1, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE
    )
    observaciones = models.TextField(blank=True, default="")

    class Meta:
        db_table = "Compras"
        ordering = ["-fecha", "-id_compra"]
        verbose_name = "compra"
        verbose_name_plural = "compras"
        constraints = [
            # Un proveedor no repite el número de una factura.
            models.UniqueConstraint(
                fields=["id_proveedor", "nro_factura"],
                name="compra_factura_unica_por_proveedor",
            ),
        ]

    def __str__(self):
        return f"Compra {self.nro_factura} — {self.id_proveedor} [{self.get_estado_display()}]"


class LineaCompra(models.Model):
    """
    Línea de una compra.

    · Compra de materias primas: lleva id_materia_prima y una cantidad en la
      unidad de la materia prima (decimal).
    · Compra de lotes: no lleva materia prima; la cantidad es el número de aves
      (entero) y el precio es por ave. id_lote queda vacío hasta que el lote se
      asigna a un galpón; entonces apunta al Lote creado.

    El precio es UNITARIO; el subtotal (cantidad × precio) y el total de la
    compra se calculan al leer.

    Las validaciones de coherencia con la categoría de la cabecera se hacen en
    el serializer, no en el modelo.
    """

    id_linea_compra = models.AutoField(db_column="idLineaCompra", primary_key=True)
    id_compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        db_column="idCompra",
        related_name="lineas",
    )
    id_materia_prima = models.ForeignKey(
        MateriaPrima,
        on_delete=models.PROTECT,
        db_column="idMateriaPrima",
        related_name="lineas_compra",
        null=True,
        blank=True,
    )
    # Lote creado a partir de esta línea. Si ese lote se elimina, la línea
    # vuelve a quedar como lote pendiente de asignar.
    id_lote = models.OneToOneField(
        Lote,
        on_delete=models.SET_NULL,
        db_column="idLote",
        related_name="linea_compra",
        null=True,
        blank=True,
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField(
        db_column="precioUnitario", max_digits=12, decimal_places=2
    )

    class Meta:
        db_table = "LineasCompra"
        verbose_name = "línea de compra"
        verbose_name_plural = "líneas de compra"

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))

    def __str__(self):
        return f"Línea {self.id_linea_compra} — x{self.cantidad}"
