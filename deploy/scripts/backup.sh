#!/bin/sh
# Backup diario de la base. Guarda 14 días en /opt/avigest/backups.
set -e
cd /opt/avigest
mkdir -p backups
FECHA=$(date +%F_%H%M)
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > "backups/avigest_$FECHA.dump"
find backups -name 'avigest_*.dump' -mtime +14 -delete
