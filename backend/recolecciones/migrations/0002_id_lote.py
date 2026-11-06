import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lotes", "0001_initial"),
        ("recolecciones", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="recoleccion",
            name="id_lote",
            field=models.ForeignKey(
                blank=True,
                db_column="idLote",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="recolecciones",
                to="lotes.lote",
            ),
        ),
    ]
