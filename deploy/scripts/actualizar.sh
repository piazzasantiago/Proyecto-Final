#!/bin/sh
# Publica la última versión de main: baja el código y reconstruye.
set -e
cd /opt/avigest
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
# nginx resuelve la IP del backend una sola vez, al arrancar. Si el backend se
# recreó, puede tener otra IP interna: se reinicia nginx para que no dé 502.
docker compose -f docker-compose.prod.yml restart nginx
docker image prune -f
