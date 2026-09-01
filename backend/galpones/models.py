from django.db import models


class Galpon(models.Model):
    """
    Corresponde a la tabla 'Galpones' del modelo relacional:
    idGalpon INT PK, galpon VARCHAR(80), latitud DECIMAL(9,6), longitud DECIMAL(9,6),
    superficie DECIMAL(9,6), capacidad INT, estado CHAR(1), descripcion MEDIUMTEXT.
    """

    ESTADO_ACTIVO = "A"
    ESTADO_INACTIVO = "I"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    id_galpon = models.AutoField(db_column="idGalpon", primary_key=True)
    galpon = models.CharField(max_length=80)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    superficie = models.DecimalField(max_digits=9, decimal_places=6)
    capacidad = models.IntegerField()
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "Galpones"
        ordering = ["galpon"]

    def __str__(self):
        return f"{self.galpon} ({self.get_estado_display()})"
