#!/bin/sh
# Despliegue de producción en UN comando (ejecutar en el servidor, en /root/fitness):
#     ./deploy.sh
# Trae main, reconstruye y reinicia. Las migraciones y seeds los aplica solo el
# contenedor `api` al arrancar (entrypoint.sh).
set -e
cd "$(dirname "$0")"
echo "== git pull =="
git checkout main
git pull origin main
echo "== rebuild + restart =="
docker compose up -d --build
echo "== estado =="
docker compose ps
echo
echo "Últimas líneas de la api (migraciones):"
docker compose logs --tail 15 api
echo
echo "Hecho. Web: https://app.dqrassessories.com"
