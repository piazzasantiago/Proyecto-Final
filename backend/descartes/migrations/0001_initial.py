from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("galpones", "__first__"),
        ("lotes", "__first__"),
        ("materias_primas", "__first__"),
        ("productos", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="Descarte",
            fields=[
                (
                    "id_descarte",
                    models.AutoField(
                        db_column="idDescarte",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("fecha", models.DateTimeField()),
                (
                    "estado",
                    models.CharField(
                        choices=[("P", "Pendiente"), ("F", "Finalizado")],
                        default="P",
                        max_length=1,
                    ),
                ),
                ("observaciones", models.TextField(blank=True, default="")),
                (
                    "id_galpon",
                    models.ForeignKey(
                        db_column="idGalpon",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="descartes",
                        to="galpones.galpon",
                    ),
                ),
            ],
            options={
                "verbose_name": "descarte",
                "verbose_name_plural": "descartes",
                "db_table": "Descartes",
                "ordering": ["-fecha"],
            },
        ),
        migrations.CreateModel(
            name="LineaDescarte",
            fields=[
                (
                    "id_linea_descarte",
                    models.AutoField(
                        db_column="idLineaDescarte",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "cantidad",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                ("motivo", models.CharField(max_length=200)),
                (
                    "id_descarte",
                    models.ForeignKey(
                        db_column="idDescarte",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="descartes.descarte",
                    ),
                ),
                (
                    "id_galpon",
                    models.ForeignKey(
                        db_column="idGalpon",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lineas_descarte",
                        to="galpones.galpon",
                    ),
                ),
                (
                    "id_lote",
                    models.ForeignKey(
                        blank=True,
                        db_column="idLote",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lineas_descarte",
                        to="lotes.lote",
                    ),
                ),
                (
                    "id_materia_prima",
                    models.ForeignKey(
                        blank=True,
                        db_column="idMateriaPrima",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lineas_descarte",
                        to="materias_primas.materiaprima",
                    ),
                ),
                (
                    "id_producto",
                    models.ForeignKey(
                        blank=True,
                        db_column="idProducto",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lineas_descarte",
                        to="productos.producto",
                    ),
                ),
            ],
            options={
                "verbose_name": "línea de descarte",
                "verbose_name_plural": "líneas de descarte",
                "db_table": "LineasDescarte",
            },
        ),
    ]
