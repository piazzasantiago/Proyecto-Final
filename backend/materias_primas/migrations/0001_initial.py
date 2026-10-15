from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MateriaPrima",
            fields=[
                (
                    "id_materia_prima",
                    models.AutoField(
                        db_column="idMateriaPrima",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "materia_prima",
                    models.CharField(
                        db_column="materiaPrima", max_length=80, unique=True
                    ),
                ),
                ("descripcion", models.TextField(blank=True, default="")),
                ("unidad", models.CharField(default="kg", max_length=20)),
                (
                    "estado",
                    models.CharField(
                        choices=[("A", "Activo"), ("I", "Inactivo")],
                        default="A",
                        max_length=1,
                    ),
                ),
                (
                    "stock_minimo",
                    models.DecimalField(
                        db_column="stockMinimo",
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                    ),
                ),
                (
                    "stock_inicial",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=10
                    ),
                ),
            ],
            options={
                "verbose_name": "materia prima",
                "verbose_name_plural": "materias primas",
                "db_table": "MateriasPrimas",
                "ordering": ["materia_prima"],
            },
        ),
    ]
