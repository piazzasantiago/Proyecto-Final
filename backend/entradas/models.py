from django.db import models

from galpones.models import Galpon
from materias_primas.models import MateriaPrima
from usuarios.models import Usuario
from config.auditoria import ModeloAuditable


class Entrada(ModeloAuditable):
    """
    Cabecera de una entrada a un galpón (CU33–CU37).

    Una entrada registra los insumos (alimento balanceado, vacunas,
    desinfectantes, nidales, etc.) que salen del stock de materias primas de la
    granja y pasan a usarse en un galpón.

    Ciclo de vida: P (Pendiente) → F (Finalizada).
    Mientras está Pendiente es editable (CU36) y borrable (CU34); no afecta el
    stock. Al finalizarla (CU37) queda de solo lectura y descuenta de cada
    materia prima la cantidad de sus líneas.

    El stock de materias primas no se guarda: se calcula (ver
    descartes/stock.py y entradas/stock.py) como
        stock_inicial − descartes de stock finalizados − entradas finalizadas.
    Las compras (módulo futuro) lo van a incrementar.

    Las gallinas no pasan por acá: ingresan a un galpón como un Lote.
    """

    ESTADO_PENDIENTE = "P"
    ESTADO_FINALIZADA = "F"
    ESTADOS_FINALIZADO = ("F",)  # auditoría: estados que cuentan como finalizado
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_FINALIZADA, "Finalizada"),
    ]

    id_entrada = models.AutoField(db_column="idEntrada", primary_key=True)
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.PROTECT,
        db_column="idGalpon",
        related_name="entradas",
    )
    # Quién cargó la entrada. Se inyecta desde la vista con el usuario
    # autenticado (igual que en Recolecciones y Descartes); nunca lo envía el cliente.
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column="idUsuario",
        related_name="entradas",
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
        db_table = "Entradas"
        ordering = ["-fecha"]
        verbose_name = "entrada"
        verbose_name_plural = "entradas"

    def __str__(self):
        return (
            f"Entrada {self.id_entrada} — {self.id_galpon} "
            f"({self.fecha:%d/%m/%Y}) [{self.get_estado_display()}]"
        )


class LineaEntrada(models.Model):
    """
    Línea de una entrada: una materia prima y la cantidad que ingresa al galpón
    (en la unidad de la materia prima: kg, L, unidades…). No se repite la misma
    materia prima dentro de una entrada (se valida en el serializer).
    """

    id_linea_entrada = models.AutoField(db_column="idLineaEntrada", primary_key=True)
    id_entrada = models.ForeignKey(
        Entrada,
        on_delete=models.CASCADE,
        db_column="idEntrada",
        related_name="lineas",
    )
    id_materia_prima = models.ForeignKey(
        MateriaPrima,
        on_delete=models.PROTECT,
        db_column="idMateriaPrima",
        related_name="lineas_entrada",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "LineasEntrada"
        verbose_name = "línea de entrada"
        verbose_name_plural = "líneas de entrada"

    def __str__(self):
        return f"Línea {self.id_linea_entrada} — {self.id_materia_prima} x{self.cantidad}"
