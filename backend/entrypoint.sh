#!/bin/sh
# Se ejecuta cada vez que arranca el contenedor del backend.
set -e

# Aplica las migraciones pendientes (en una base nueva crea todas las tablas
# y los tipos de alerta).
python manage.py migrate --noinput

# Junta los archivos estáticos del admin en /app/staticfiles, que sirve nginx.
python manage.py collectstatic --noinput

exec "$@"
