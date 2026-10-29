from django.db import models

from usuarios.models import Usuario
from config.auditoria import ModeloAuditable


class Galpon(ModeloAuditable):
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
        verbose_name = "galpón"
        verbose_name_plural = "galpones"

    def __str__(self):
        return f"{self.galpon} ({self.get_estado_display()})"


class UsuarioDelGalpon(models.Model):
    """
    Corresponde a la tabla 'UsuariosDelGalpon' del modelo relacional:
    idUsuario INT PK FK -> Usuarios, idGalpon INT PK FK -> Galpones.

    Asocia operarios con los galpones a los que tienen acceso.
    Solo usuarios con rol Operario (O) pueden ser asignados.
    """

    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column="idUsuario",
        related_name="galpones_asignados",
        limit_choices_to={"rol": Usuario.ROL_OPERARIO},
    )
    id_galpon = models.ForeignKey(
        Galpon,
        on_delete=models.CASCADE,
        db_column="idGalpon",
        related_name="operarios_asignados",
    )

    class Meta:
        db_table = "UsuariosDelGalpon"
        unique_together = [("id_usuario", "id_galpon")]
        verbose_name = "operario del galpón"
        verbose_name_plural = "operarios del galpón"

    def __str__(self):
        return f"{self.id_usuario} → {self.id_galpon}"
