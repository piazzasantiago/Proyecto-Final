from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("descartes", "0002_categoria_y_galpon_opcional"),
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="descarte",
            name="id_usuario",
            field=models.ForeignKey(
                blank=True,
                db_column="idUsuario",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="descartes",
                to="usuarios.usuario",
            ),
        ),
    ]
