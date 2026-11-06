from django.db import migrations, models


class Migration(migrations.Migration):
    """
    - N° de factura → N° de comprobante: el número ahora lo genera el sistema
      (es el id autoincremental de la compra), así que se elimina la columna
      que se cargaba a mano y su restricción de unicidad por proveedor.
    - Nuevas formas de pago: Débito, Crédito y Otro.
    """

    dependencies = [
        ("compras", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="compra",
            name="compra_factura_unica_por_proveedor",
        ),
        migrations.RemoveField(
            model_name="compra",
            name="nro_factura",
        ),
        migrations.AlterField(
            model_name="compra",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("C", "Contado"),
                    ("X", "Cuenta corriente"),
                    ("D", "Débito"),
                    ("R", "Crédito"),
                    ("O", "Otro"),
                ],
                default="C",
                max_length=1,
            ),
        ),
    ]
