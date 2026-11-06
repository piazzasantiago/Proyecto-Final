from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Agrega la categoría del descarte (Galpón / Stock) y hace opcional el galpón.

    Los descartes que ya existían pertenecían todos a un galpón, por eso la
    categoría por defecto es "G".
    """

    dependencies = [
        ("galpones", "__first__"),
        ("descartes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="descarte",
            name="categoria",
            field=models.CharField(
                choices=[("G", "Galpón"), ("S", "Stock")],
                default="G",
                max_length=1,
            ),
        ),
        migrations.AlterField(
            model_name="descarte",
            name="id_galpon",
            field=models.ForeignKey(
                blank=True,
                db_column="idGalpon",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="descartes",
                to="galpones.galpon",
            ),
        ),
        migrations.AlterField(
            model_name="lineadescarte",
            name="id_galpon",
            field=models.ForeignKey(
                blank=True,
                db_column="idGalpon",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_descarte",
                to="galpones.galpon",
            ),
        ),
    ]
