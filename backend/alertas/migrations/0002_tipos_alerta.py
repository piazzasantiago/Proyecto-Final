from django.db import migrations

# Tipos de alerta que el sistema sabe detectar. Van acá, escritos tal cual, y
# no importados de alertas/reglas.py, porque una migración tiene que seguir
# haciendo lo mismo aunque el código cambie más adelante.
# (clave, nombre, severidad)
TIPOS = [
    ("postura_baja", "Postura baja", "A"),
    ("mortandad_alta", "Mortandad alta", "A"),
    ("transicion_por_vencer", "Plan de transición por vencer", "M"),
    ("sin_recoleccion", "Sin recolecciones recientes", "M"),
]


def crear_tipos(apps, schema_editor):
    TipoAlerta = apps.get_model("alertas", "TipoAlerta")
    for clave, nombre, severidad in TIPOS:
        TipoAlerta.objects.update_or_create(
            clave=clave, defaults={"nombre": nombre, "severidad": severidad}
        )


def borrar_tipos(apps, schema_editor):
    TipoAlerta = apps.get_model("alertas", "TipoAlerta")
    TipoAlerta.objects.filter(clave__in=[t[0] for t in TIPOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("alertas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_tipos, borrar_tipos),
    ]
