from django.db import models


class MateriaPrima(models.Model):
    """
    Corresponde a la tabla 'MateriasPrimas' del modelo relacional:
    idMateriaPrima INT PK, estado CHAR(1), materiaPrima VARCHAR(80),
    stockMinimo DECIMAL(10,2).

    Representa los insumos y consumibles utilizados en los galpones
    (alimento balanceado, vacunas, desinfectantes, nidales, etc.).
    El stock de materias primas se actualiza mediante:
      - Compras:  suman stock (módulo Compras, a implementar).
      - Entradas: descuentan stock al ingresar insumos a un galpón.
      - Descartes: descuentan stock al registrar pérdidas o bajas.
    Por ahora el stock_actual se ajusta manualmente con stock_inicial.

    stock_minimo es un umbral de alerta, no una restricción. Se muestra
    en la tarjeta para que el administrador sepa cuándo reponer.
    """

    ESTADO_ACTIVO = "A"
    ESTADO_INACTIVO = "I"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    id_materia_prima = models.AutoField(db_column="idMateriaPrima", primary_key=True)
    materia_prima = models.CharField(db_column="materiaPrima", max_length=80, unique=True)
    descripcion = models.TextField(blank=True, default="")
    unidad = models.CharField(max_length=20, default="kg")
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)
    stock_minimo = models.DecimalField(
        db_column="stockMinimo", max_digits=10, decimal_places=2, default=0
    )
    stock_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "MateriasPrimas"
        ordering = ["materia_prima"]
        verbose_name = "materia prima"
        verbose_name_plural = "materias primas"

    def __str__(self):
        return f"{self.materia_prima} ({self.get_estado_display()})"
