from django.db import models

from productos.models import Producto
from usuarios.models import Usuario
from config.auditoria import ModeloAuditable


class Salida(ModeloAuditable):
    """
    Cabecera de una salida de productos de la granja.

    Una salida registra los productos (huevos clasificados por tamaño) que dejan
    la granja: por ejemplo, el camión que se lleva los huevos destinados a la
    venta.

    Ciclo de vida: P (Pendiente) → F (Finalizada).
    Mientras está Pendiente es editable y borrable; no afecta el stock. Al
    finalizarla queda de solo lectura y descuenta del stock de cada producto la
    cantidad de sus líneas.

    El stock de productos no se guarda: se calcula (ver descartes/stock.py y
    salidas/stock.py) como
        stock_inicial + recolectado − descartado − salidas finalizadas.
    """

    ESTADO_PENDIENTE = "P"
    ESTADO_FINALIZADA = "F"
    ESTADOS_FINALIZADO = ("F",)  # auditoría: estados que cuentan como finalizado
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_FINALIZADA, "Finalizada"),
    ]

    id_salida = models.AutoField(db_column="idSalida", primary_key=True)
    # Quién cargó la salida. Se inyecta desde la vista con el usuario
    # autenticado (igual que en Recolecciones, Descartes y Entradas); nunca lo
    # envía el cliente.
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="salidas",
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
        db_table = "Salidas"
        ordering = ["-fecha"]
        verbose_name = "salida"
        verbose_name_plural = "salidas"

    def __str__(self):
        return f"Salida {self.id_salida} ({self.fecha:%d/%m/%Y}) [{self.get_estado_display()}]"


class LineaSalida(models.Model):
    """
    Línea de una salida: un producto y la cantidad (unidades enteras) que sale.
    No se repite el mismo producto dentro de una salida (se valida en el
    serializer).
    """

    id_linea_salida = models.AutoField(db_column="idLineaSalida", primary_key=True)
    id_salida = models.ForeignKey(
        Salida,
        on_delete=models.CASCADE,
        db_column="idSalida",
        related_name="lineas",
    )
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="lineas_salida",
    )
    cantidad = models.PositiveIntegerField()

    class Meta:
        db_table = "LineasSalida"
        verbose_name = "línea de salida"
        verbose_name_plural = "líneas de salida"

    def __str__(self):
        return f"Línea {self.id_linea_salida} — {self.id_producto} x{self.cantidad}"
