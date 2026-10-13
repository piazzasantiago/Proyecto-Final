from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("productos", "0002_producto_stock_actual"),
    ]

    operations = [
        migrations.RenameField(
            model_name="producto",
            old_name="stock_actual",
            new_name="stock_inicial",
        ),
    ]
