import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("productos", "0003_rename_stock_actual_producto_stock_inicial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Salida",
            fields=[
                (
                    "id_salida",
                    models.AutoField(
                        db_column="idSalida", primary_key=True, serialize=False
                    ),
                ),
                ("fecha", models.DateTimeField()),
                (
                    "estado",
                    models.CharField(
                        choices=[("P", "Pendiente"), ("F", "Finalizada")],
                        default="P",
                        max_length=1,
                    ),
                ),
                ("observaciones", models.TextField(blank=True, default="")),
                (
                    "id_usuario",
                    models.ForeignKey(
                        blank=True,
                        db_column="idUsuario",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="salidas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "salida",
                "verbose_name_plural": "salidas",
                "db_table": "Salidas",
                "ordering": ["-fecha"],
            },
        ),
        migrations.CreateModel(
            name="LineaSalida",
            fields=[
                (
                    "id_linea_salida",
                    models.AutoField(
                        db_column="idLineaSalida", primary_key=True, serialize=False
                    ),
                ),
                ("cantidad", models.PositiveIntegerField()),
                (
                    "id_producto",
                    models.ForeignKey(
                        db_column="idProducto",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lineas_salida",
                        to="productos.producto",
                    ),
                ),
                (
                    "id_salida",
                    models.ForeignKey(
                        db_column="idSalida",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="salidas.salida",
                    ),
                ),
            ],
            options={
                "verbose_name": "línea de salida",
                "verbose_name_plural": "líneas de salida",
                "db_table": "LineasSalida",
            },
        ),
    ]
