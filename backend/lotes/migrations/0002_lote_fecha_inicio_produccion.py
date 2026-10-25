import datetime

from django.db import migrations, models


def completar_inicio_produccion(apps, schema_editor):
    """
    Los lotes que ya estaban en Producción antes de este campo no guardaron el
    día en que empezaron: se toma el fin de su plan de transición (ingreso + 28
    días), que es cuando la producción debería haber comenzado. Los lotes ya
    Finalizados quedan en null: no hay forma de saber si llegaron a producir.
    """
    Lote = apps.get_model("lotes", "Lote")
    for lote in Lote.objects.filter(estado="P", fecha_inicio_produccion__isnull=True):
        lote.fecha_inicio_produccion = lote.fecha_ingreso + datetime.timedelta(days=28)
        lote.save(update_fields=["fecha_inicio_produccion"])


class Migration(migrations.Migration):

    dependencies = [
        ("lotes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lote",
            name="fecha_inicio_produccion",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(completar_inicio_produccion, migrations.RunPython.noop),
    ]
