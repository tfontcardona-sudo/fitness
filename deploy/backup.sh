#!/usr/bin/env bash
# =============================================================================
# Copia de seguridad diaria del Fitness System.
#   · Base de datos completa (pg_dump comprimido, con DROP ... IF EXISTS para
#     poder restaurar encima).
#   · Ficheros subidos (fotos de progreso y PDFs) del volumen ./storage.
# Guarda en /root/fitness-backups (FUERA del repo, para que `git pull` no lo
# toque) y conserva solo las últimas N copias. Lo lanza cron una vez al día
# (lo programa deploy/install-backups.sh).
#
# Ejecutar a mano:  bash /root/fitness/deploy/backup.sh
# =============================================================================
set -euo pipefail

REPO="${FITNESS_REPO:-/root/fitness}"
DEST="${FITNESS_BACKUP_DIR:-/root/fitness-backups}"
KEEP="${FITNESS_BACKUP_KEEP:-14}"     # cuántas copias diarias conservar
# Nunca borrar TODAS las copias: un KEEP=0 o no numérico haría 'tail -n +1' y la
# rotación se llevaría por delante hasta la copia recién creada.
case "$KEEP" in ''|*[!0-9]*) KEEP=14 ;; esac
[ "$KEEP" -ge 1 ] || KEEP=14
cd "$REPO"

# Credenciales de la BD desde el .env (con los mismos valores por defecto que
# el docker-compose de producción).
env_val() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2-; }
PGUSER="$(env_val POSTGRES_USER)"; PGUSER="${PGUSER:-fitness}"
PGDB="$(env_val POSTGRES_DB)";     PGDB="${PGDB:-fitness}"

mkdir -p "$DEST"
chmod 700 "$DEST" 2>/dev/null || true   # datos de salud: solo root
# Evita dos backups solapados (el volcado puede tardar).
exec 9>"$DEST/.backup.lock"
flock -n 9 || { echo "[$(date '+%F %T')] otro backup en curso, salto"; exit 0; }

STAMP="$(date +%F_%H%M)"
DB_FILE="$DEST/db-$STAMP.sql.gz"
TMP="$DB_FILE.part"

# --- volcado de la base de datos -------------------------------------------
if docker compose exec -T db pg_dump --clean --if-exists -U "$PGUSER" "$PGDB" | gzip > "$TMP"; then
  # Sanidad: un volcado válido empieza por la cabecera de pg_dump y no está
  # truncado (si el .gz estuviera cortado, `gzip -dc` fallaría y no casaría).
  if [ "$(stat -c%s "$TMP" 2>/dev/null || echo 0)" -ge 200 ] \
     && gzip -dc "$TMP" 2>/dev/null | head -c 40 | grep -q "PostgreSQL database dump"; then
    mv "$TMP" "$DB_FILE"
    echo "[$(date '+%F %T')] BD  -> $(basename "$DB_FILE") ($(du -h "$DB_FILE" | cut -f1))"
  else
    rm -f "$TMP"
    echo "[$(date '+%F %T')] ERROR: volcado vacío o corrupto; conservo las copias previas"
    exit 1
  fi
else
  rm -f "$TMP"
  echo "[$(date '+%F %T')] ERROR: pg_dump falló (¿está arriba el contenedor 'db'?)"
  exit 1
fi

# --- ficheros subidos (fotos de progreso, documentos) ----------------------
if [ -d "$REPO/storage" ] && [ -n "$(ls -A "$REPO/storage" 2>/dev/null)" ]; then
  if tar czf "$DEST/storage-$STAMP.tar.gz" -C "$REPO" storage 2>/dev/null; then
    echo "[$(date '+%F %T')] Ficheros -> storage-$STAMP.tar.gz ($(du -h "$DEST/storage-$STAMP.tar.gz" | cut -f1))"
  fi
fi

# --- rotación: conserva las últimas $KEEP de cada tipo ---------------------
rotate() {
  # shellcheck disable=SC2012
  ls -1t "$DEST"/$1 2>/dev/null | tail -n +"$(( KEEP + 1 ))" | xargs -r rm -f
}
rotate 'db-*.sql.gz'
rotate 'storage-*.tar.gz'

echo "[$(date '+%F %T')] OK · copias en $DEST (guardando $KEEP)"
