#!/usr/bin/env bash
# =============================================================================
# Restaura una copia de seguridad de la base de datos.
# DESTRUCTIVO: reemplaza los datos actuales por los del fichero elegido.
#
#   Ver copias:   bash /root/fitness/deploy/restore.sh
#   Restaurar:    bash /root/fitness/deploy/restore.sh /root/fitness-backups/db-2026-07-08_0400.sql.gz
# =============================================================================
set -euo pipefail

REPO="${FITNESS_REPO:-/root/fitness}"
DEST="${FITNESS_BACKUP_DIR:-/root/fitness-backups}"
cd "$REPO"

env_val() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2-; }
PGUSER="$(env_val POSTGRES_USER)"; PGUSER="${PGUSER:-fitness}"
PGDB="$(env_val POSTGRES_DB)";     PGDB="${PGDB:-fitness}"

FILE="${1:-}"
if [ -z "$FILE" ]; then
  echo "Copias de la base de datos disponibles (más reciente arriba):"
  echo ""
  ls -1t "$DEST"/db-*.sql.gz 2>/dev/null | head -20 | nl || echo "  (ninguna todavía)"
  echo ""
  echo "Para restaurar:  bash $0 <ruta-del-fichero.sql.gz>"
  exit 0
fi
[ -f "$FILE" ] || { echo "No existe el fichero: $FILE"; exit 1; }

echo ""
echo "ATENCIÓN: esto REEMPLAZA por completo la base de datos actual ($PGDB)"
echo "por el contenido de:"
echo "   $FILE"
echo ""
read -rp "Escribe 'RESTAURAR' (en mayúsculas) para continuar: " CONFIRM
[ "$CONFIRM" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

# Red de seguridad: antes de sobrescribir, guardar un volcado del estado ACTUAL
# por si el fichero elegido no es el correcto.
SNAP="$DEST/pre-restore-$(date +%F_%H%M%S).sql.gz"
echo "Guardando copia del estado actual en $SNAP …"
if docker compose exec -T db pg_dump --clean --if-exists -U "$PGUSER" "$PGDB" | gzip > "$SNAP" 2>/dev/null && [ -s "$SNAP" ]; then
  echo "Copia previa OK."
else
  rm -f "$SNAP"
  read -rp "No se pudo guardar la copia previa. ¿Continuar igualmente? [escribe SI]: " C2
  [ "$C2" = "SI" ] || { echo "Cancelado."; exit 1; }
fi

echo "Parando la API para restaurar sin conflictos…"
docker compose stop api >/dev/null 2>&1 || true

echo "Restaurando la base de datos…"
if gzip -dc "$FILE" | docker compose exec -T db psql -v ON_ERROR_STOP=0 -U "$PGUSER" -d "$PGDB" >/tmp/dq-restore.log 2>&1; then
  echo "Restauración aplicada."
else
  echo "Hubo avisos durante la restauración (normal en la primera vez). Detalle: /tmp/dq-restore.log"
fi

echo "Arrancando la API…"
docker compose up -d api >/dev/null 2>&1

echo ""
echo "Hecho. Abre la web y comprueba que los datos son los esperados."
