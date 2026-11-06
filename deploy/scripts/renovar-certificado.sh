#!/bin/sh
# Renueva el certificado si le faltan menos de 30 días y recarga nginx.
set -e
cd /opt/avigest
docker compose -f docker-compose.prod.yml run --rm certbot \
  renew --webroot -w /var/www/certbot --quiet
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
