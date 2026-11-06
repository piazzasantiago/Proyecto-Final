from django.db import models

from lotes.models import Lote


class TipoAlerta(models.Model):
    """
    Corresponde a la tabla 'TiposAlerta' del modelo relacional:
    idTipoAlerta SMALLINT PK, nombre VARCHAR(100).

    Las filas no se cargan desde la aplicación: cada tipo existe porque el
    sistema sabe detectarlo (ver alertas/reglas.py), así que los crea una
    migración de datos. Agregar un tipo nuevo es agregar su regla y su fila.

    Dos columnas se suman a las del modelo relacional:
        · clave      identifica el tipo en el código y en la pantalla. El
                     nombre es un texto para mostrar y puede cambiarse sin
                     romper nada; la clave no.
        · severidad  ordena las alertas por urgencia y define el color con el
                     que se muestran.
    """

    SEVERIDAD_ALTA = "A"
    SEVERIDAD_MEDIA = "M"
    SEVERIDAD_CHOICES = [
        (SEVERIDAD_ALTA, "Alta"),
        (SEVERIDAD_MEDIA, "Media"),
    ]

    id_tipo_alerta = models.SmallAutoField(db_column="idTipoAlerta", primary_key=True)
    clave = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=100)
    severidad = models.CharField(
        max_length=1,
        choices=SEVERIDAD_CHOICES,
        default=SEVERIDAD_MEDIA,
    )

    class Meta:
        db_table = "TiposAlerta"
        ordering = ["severidad", "nombre"]
        verbose_name = "tipo de alerta"
        verbose_name_plural = "tipos de alerta"

    def __str__(self):
        return self.nombre


class Alerta(models.Model):
    """
    Corresponde a la tabla 'Alertas' del modelo relacional:
    idAlerta INT PK, idLote INT FK, idTipoAlerta SMALLINT FK,
    descripcion VARCHAR(255), estado CHAR(1), fechaGeneracion TIMESTAMP.

    Una alerta avisa que un lote está en una situación que conviene mirar
    (postura por debajo del objetivo, transición por vencer, etc.). No la
    carga nadie: la genera y la resuelve el sistema al evaluar las reglas
    (ver alertas/generacion.py), por eso el modelo no hereda de
    ModeloAuditable: no hay un usuario que la haya creado ni editado.

    El estado es el ciclo de vida de la alerta:
        P (Pendiente): la situación sigue vigente.
        R (Resuelta):  la situación dejó de cumplirse; la alerta queda en el
                       historial con la fecha en que se resolvió.

    fecha_resolucion se agrega al modelo relacional para poder mostrar
    «resuelta el ...» y ordenar el historial.

    Un lote no puede acumular dos alertas pendientes del mismo tipo: mientras
    la situación siga vigente se actualiza la descripción de la que ya existe
    (lo garantiza la restricción «alerta_pendiente_unica»). Si la situación se
    resuelve y más adelante vuelve a darse, se genera una alerta nueva.
    """

    ESTADO_PENDIENTE = "P"
    ESTADO_RESUELTA = "R"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_RESUELTA, "Resuelta"),
    ]

    id_alerta = models.AutoField(db_column="idAlerta", primary_key=True)
    id_lote = models.ForeignKey(
        Lote,
        on_delete=models.CASCADE,
        db_column="idLote",
        related_name="alertas",
    )
    id_tipo_alerta = models.ForeignKey(
        TipoAlerta,
        on_delete=models.PROTECT,
        db_column="idTipoAlerta",
        related_name="alertas",
    )
    descripcion = models.CharField(max_length=255)
    estado = models.CharField(
        max_length=1,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
    )
    fecha_generacion = models.DateTimeField()
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "Alertas"
        ordering = ["-fecha_generacion"]
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        constraints = [
            models.UniqueConstraint(
                fields=["id_lote", "id_tipo_alerta"],
                condition=models.Q(estado="P"),
                name="alerta_pendiente_unica",
            )
        ]
        indexes = [
            models.Index(fields=["estado", "-fecha_generacion"], name="alerta_estado_fecha_idx"),
        ]

    def __str__(self):
        return f"{self.id_tipo_alerta} — {self.id_lote.codigo} ({self.get_estado_display()})"
