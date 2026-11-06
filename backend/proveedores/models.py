from django.db import models
from django.db.models import Q
from config.auditoria import ModeloAuditable


class Proveedor(ModeloAuditable):
    """
    Corresponde a la tabla 'Proveedores' del modelo relacional:
    idProveedor INT PK, direccion VARCHAR(150), email VARCHAR(150),
    estado CHAR(1), telefono VARCHAR(45).

    Se agregaron `nombre` y `cuit`, que el diagrama original no tenía: sin un
    nombre los proveedores solo se distinguirían por su número, y el módulo de
    Compras necesita elegirlos por nombre. La Educción de requisitos pide que
    cada proveedor esté "unívocamente identificado".

    Un proveedor vende materias primas y lotes de gallinas a la granja. Se da
    de baja (estado Inactivo) en lugar de borrarlo cuando ya tiene compras,
    para conservar el historial.
    """

    ESTADO_ACTIVO = "A"
    ESTADO_INACTIVO = "I"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    id_proveedor = models.AutoField(db_column="idProveedor", primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    # Solo dígitos, sin guiones (el serializer los normaliza). Opcional.
    cuit = models.CharField(max_length=11, blank=True, default="")
    direccion = models.CharField(db_column="direccion", max_length=150, blank=True, default="")
    email = models.CharField(max_length=150)
    telefono = models.CharField(max_length=45)
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)

    class Meta:
        db_table = "Proveedores"
        ordering = ["nombre"]
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        constraints = [
            # El CUIT, cuando se carga, no se repite.
            models.UniqueConstraint(
                fields=["cuit"],
                condition=~Q(cuit=""),
                name="proveedor_cuit_unico",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"
