from django.db import models


class Producto(models.Model):
    """
    Corresponde a la tabla 'Productos' del modelo relacional:
    idProducto INT PK, producto VARCHAR(80), descripcion MEDIUMTEXT, estado CHAR(1).

    Representa los productos que se obtienen de la producción (en este caso,
    huevos clasificados por tamaño: Nº1, Nº2 y Nº3), tal como lo describe la
    Educción de requisitos (CU49-54). Cada línea de recolección (ver
    feature/gestion-recolecciones) referencia uno de estos productos.

    Solo se pueden asignar productos activos a una nueva línea de
    recolección; desactivar un producto no afecta las líneas ya registradas
    con él (mismo criterio que con los operarios inactivos de un galpón).

    stock_inicial es el stock de partida (o un ajuste manual) que carga el
    Administrador. El stock actual que muestra la API no se guarda: se calcula
    como stock_inicial + lo recolectado en recolecciones FINALIZADAS (ver
    ProductoSerializer). Cuando existan Descartes y Salidas, también se les
    restará.
    """

    ESTADO_ACTIVO = "A"
    ESTADO_INACTIVO = "I"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    id_producto = models.AutoField(db_column="idProducto", primary_key=True)
    producto = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)
    stock_inicial = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "Productos"
        ordering = ["producto"]
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return f"{self.producto} ({self.get_estado_display()})"
