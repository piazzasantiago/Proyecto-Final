# Generated manually for UsuariosDelGalpon table

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("galpones", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UsuarioDelGalpon",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "id_galpon",
                    models.ForeignKey(
                        db_column="idGalpon",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operarios_asignados",
                        to="galpones.galpon",
                    ),
                ),
                (
                    "id_usuario",
                    models.ForeignKey(
                        db_column="idUsuario",
                        limit_choices_to={"rol": "O"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="galpones_asignados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "operario del galpón",
                "verbose_name_plural": "operarios del galpón",
                "db_table": "UsuariosDelGalpon",
            },
        ),
        migrations.AlterUniqueTogether(
            name="usuariodelgalpon",
            unique_together={("id_usuario", "id_galpon")},
        ),
    ]
