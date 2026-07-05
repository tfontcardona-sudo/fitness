#!/usr/bin/env bash
# =============================================================================
# Fitness System — instalador de producción para VPS (Ubuntu 22.04/24.04)
#
# Hace TODO el despliegue: Docker, firewall, .env con secretos autogenerados,
# arranque de los contenedores, claves VAPID para push y resumen final.
# Solo pregunta lo que no puede inventar: dominio, usuarios del coach,
# clave de Anthropic (opcional) y un email de contacto.
#
# Uso (como root, desde cualquier sitio):
#   bash /root/fitness/deploy/install-vps.sh
#
# Es seguro re-ejecutarlo: conserva los secretos de un .env existente.
# =============================================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")/.."   # raíz del repo

echo ""
echo "== Fitness System — instalador de producción =="
echo ""
[ "$(id -u)" = "0" ] || { echo "ERROR: ejecuta este script como root."; exit 1; }

# ---------------------------------------------------------------- preguntas --
read -rp "Dominio del sistema (ej. app.dqfitness.com): " DOM
[ -n "$DOM" ] || { echo "ERROR: el dominio es obligatorio."; exit 1; }
read -rp  "Usuario coach 1 [david]: " A1U; A1U=${A1U:-david}
read -rsp "Contraseña coach 1: " A1P; echo
read -rp  "Usuario coach 2 [socio]: " A2U; A2U=${A2U:-socio}
read -rsp "Contraseña coach 2: " A2P; echo
read -rp  "ANTHROPIC_API_KEY (Enter para dejarla vacía de momento): " AKEY
read -rp  "Email de contacto (para las notificaciones push): " PMAIL
[ -n "$A1P" ] && [ -n "$A2P" ] || { echo "ERROR: las contraseñas no pueden estar vacías."; exit 1; }

# --------------------------------------------------------------- chequeo DNS --
SRV_IP=$(curl -4 -s --max-time 10 https://ifconfig.me || echo "?")
DOM_IP=$(getent ahostsv4 "$DOM" 2>/dev/null | awk '{print $1; exit}' || true)
if [ -n "${DOM_IP:-}" ] && [ "$DOM_IP" = "$SRV_IP" ]; then
  echo "DNS correcto: $DOM → $SRV_IP"
else
  echo ""
  echo "AVISO: $DOM aún no apunta a este servidor."
  echo "  El dominio resuelve a: ${DOM_IP:-<sin registro A>}"
  echo "  La IP de este servidor es: $SRV_IP"
  echo "  Sin esto, el certificado HTTPS fallará. Puedes continuar y el"
  echo "  certificado se emitirá solo cuando el DNS se propague."
  read -rp "¿Continuar igualmente? [s/N]: " CONT
  case "${CONT:-n}" in s|S) ;; *) echo "Cancelado."; exit 1 ;; esac
fi

# ------------------------------------------------------- docker + firewall --
command -v git >/dev/null 2>&1 || { apt-get update -qq; apt-get install -y -qq git; }
if ! command -v docker >/dev/null 2>&1; then
  echo "Instalando Docker…"
  curl -fsSL https://get.docker.com | sh
fi
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH >/dev/null
  ufw allow 80 >/dev/null
  ufw allow 443 >/dev/null
  ufw --force enable >/dev/null
  echo "Firewall configurado (SSH/80/443)."
fi

# ------------------------------------------------------------------- .env ---
# patch_env CLAVE VALOR — sustitución segura (los valores pueden llevar
# cualquier carácter; nada de sed con delimitadores frágiles).
patch_env() {
  KEY="$1" VAL="$2" python3 - <<'PY'
import os, re
key, val = os.environ["KEY"], os.environ["VAL"]
s = open(".env").read()
pat = re.compile(rf"(?m)^{re.escape(key)}=.*$")
if pat.search(s):
    s = pat.sub(lambda m: f"{key}={val}", s)
else:
    s = s.rstrip("\n") + f"\n{key}={val}\n"
open(".env", "w").write(s)
PY
}
rand_hex() { python3 -c "import secrets; print(secrets.token_hex($1))"; }

if [ -f .env ]; then
  echo "Ya existe un .env: se conservan sus secretos (JWT, BD, VAPID)."
else
  cp .env.example .env
  PGPASS=$(rand_hex 16)
  patch_env JWT_SECRET "$(rand_hex 32)"
  patch_env PORTAL_TOKEN_SECRET "$(rand_hex 32)"
  patch_env POSTGRES_PASSWORD "$PGPASS"
  patch_env DATABASE_URL "postgresql+psycopg://fitness:$PGPASS@db:5432/fitness"
  # Sin SMTP real configurado los emails se desactivan (Mailpit es solo dev)
  patch_env EMAILS_ENABLED "false"
fi

patch_env DOMAIN "$DOM"
patch_env ADMIN_1_USER "$A1U"
patch_env ADMIN_1_PASS "$A1P"
patch_env ADMIN_2_USER "$A2U"
patch_env ADMIN_2_PASS "$A2P"
[ -n "$AKEY" ]  && patch_env ANTHROPIC_API_KEY "$AKEY"
[ -n "$PMAIL" ] && patch_env VAPID_SUBJECT "mailto:$PMAIL"
chmod 600 .env

# ---------------------------------------------------------------- arranque --
echo ""
echo "Construyendo y arrancando (la primera vez tarda unos minutos)…"
docker compose up -d --build

echo "Esperando a que la API esté lista…"
API_OK=0
for _ in $(seq 1 60); do
  if docker compose exec -T api python -c "import app" >/dev/null 2>&1; then API_OK=1; break; fi
  sleep 2
done
[ "$API_OK" = "1" ] || { echo "ERROR: la API no arranca. Mira: docker compose logs api --tail 100"; exit 1; }

# ------------------------------------------------------------- claves push --
# Se generan UNA vez y no se cambian (cambiarlas invalida las suscripciones).
if grep -q '^VAPID_PRIVATE_KEY=$' .env; then
  echo "Generando claves VAPID (Web Push)…"
  KEYS=$(docker compose exec -T api python -m scripts.generate_vapid_keys)
  patch_env VAPID_PRIVATE_KEY "$(printf '%s\n' "$KEYS" | sed -n 's/^VAPID_PRIVATE_KEY=//p')"
  patch_env VAPID_PUBLIC_KEY  "$(printf '%s\n' "$KEYS" | sed -n 's/^VAPID_PUBLIC_KEY=//p')"
  docker compose up -d
fi

# ----------------------------------------------------------------- resumen --
echo ""
echo "=================================================================="
echo "  LISTO ✔"
echo ""
echo "  Web del coach:    https://$DOM"
echo "     usuario 1:     $A1U"
echo "     usuario 2:     $A2U   (para tu socio, con su contraseña)"
echo ""
echo "  Portal clientes:  https://$DOM/p/{token}"
echo "     (en la ficha de cada cliente → 'enlace del portal')"
echo ""
echo "  El certificado HTTPS se emite solo en la primera visita (~30 s)."
echo "  Guarda una copia segura de $(pwd)/.env — contiene los secretos."
echo ""
echo "  Actualizar más adelante:  cd $(pwd) && git pull && docker compose up -d --build"
echo "  Backup diario de la BD:   docker compose exec db pg_dump -U fitness fitness > backup.sql"
echo "=================================================================="
