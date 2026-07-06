#!/usr/bin/env bash
# =============================================================================
# Auto-despliegue: si hay cambios nuevos en main (GitHub), los aplica solo.
# Lo ejecuta cron cada 5 minutos (lo instala la línea de deploy una vez).
# Solo reconstruye cuando HAY cambios; si no, sale al instante sin tocar nada.
# =============================================================================
set -euo pipefail

cd /root/fitness

# Evita dos despliegues a la vez (el build tarda unos minutos)
exec 9>/tmp/dq-deploy.lock
flock -n 9 || exit 0

git fetch origin main -q
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && exit 0

echo "[$(date '+%F %T')] Cambios detectados: $LOCAL -> $REMOTE. Desplegando…"
git merge --ff-only origin/main -q
docker compose up -d --build
echo "[$(date '+%F %T')] Desplegado $REMOTE ✔"
