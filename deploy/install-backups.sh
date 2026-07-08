#!/usr/bin/env bash
# =============================================================================
# Programa la copia de seguridad diaria (cron) del Fitness System. Idempotente:
# se puede re-ejecutar sin duplicar nada. Lo llama el instalador principal, y
# también puedes ejecutarlo tú a mano una sola vez.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DEST="${FITNESS_BACKUP_DIR:-/root/fitness-backups}"
CRON="${FITNESS_CRON_FILE:-/etc/cron.d/dq-fitness-backup}"
HOUR="${FITNESS_BACKUP_HOUR:-4}"     # hora del backup (madrugada por defecto)

mkdir -p "$DEST"

cat > "$CRON" <<EOF
# Copia de seguridad diaria del Fitness System (generado por install-backups.sh).
# BD + ficheros -> $DEST · conserva las últimas copias · rota solo.
SHELL=/bin/bash
0 $HOUR * * * root $REPO/deploy/backup.sh >> $DEST/backup.log 2>&1
EOF
chmod 0644 "$CRON"

echo "Backup diario programado a las 0${HOUR}:00 -> $DEST"
echo "Lanzar uno ahora:   bash $REPO/deploy/backup.sh"
echo "Ver / restaurar:    bash $REPO/deploy/restore.sh"
