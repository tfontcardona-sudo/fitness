#!/usr/bin/env bash
# =============================================================================
# ÓRDENES PUNTUALES DEL DUEÑO sobre el .env REAL del servidor.
#
# Para qué sirve: el `.env` de producción NO vive en git (secretos), y el repo es
# PÚBLICO, así que una credencial nueva no puede viajar escrita en un fichero ni
# en un parámetro del workflow (los logs y las entradas de un workflow_dispatch
# se leen desde fuera). Esto resuelve el trayecto con cifrado asimétrico:
#
#   1. El despliegue genera EN EL SERVIDOR un par de claves RSA y publica solo la
#      clave PÚBLICA en su log (no es secreta). La privada no sale del servidor.
#   2. Quien lanza la orden cifra con esa pública un texto
#          ADMIN_1_USER=…  ADMIN_1_PASS=…  ADMIN_2_USER=  ADMIN_2_PASS=  PAUSA=1
#      y lo pasa como entrada `ordenes` del workflow (base64). Es ilegible para
#      cualquiera que no sea ese servidor.
#   3. El despliegue lo descifra, reescribe SOLO esas cuatro variables del .env
#      (con copia de seguridad), reconstruye (el arranque del contenedor aplica
#      la rotación: `seed_admins`) y COMPRUEBA el resultado sin imprimir nunca la
#      contraseña: solo códigos HTTP y los nombres de usuario de la base.
#   4. Si todo va bien, deja la orden marcada como aplicada y borra la clave.
#
# Es de UN SOLO USO por orden (se identifica por su huella sha256): repetir el
# despliegue no vuelve a pisar un .env que el dueño haya cambiado a mano después.
# Tras usarse se retira de la rama principal (queda en el historial).
#
# Se invoca desde .github/workflows/deploy.yml (ejecutándose en /root/fitness)
# con `bash` EXPLÍCITO — no se hace `source`: no sabemos con qué shell ejecuta
# el paso SSH, y un error de sintaxis al cargar un fichero con `.` tumbaría el
# despliegue entero. Nada de lo que hace puede tumbarlo: el workflow lo llama
# con `|| echo …`.
#     bash deploy/ordenes_del_dueno.sh preparar    (antes de reconstruir)
#     bash deploy/ordenes_del_dueno.sh verificar   (después, con la API viva)
# El estado pasa de una fase a otra por `$ORD_DIR/pendiente` (modo 600), que la
# segunda fase BORRA nada más leerlo.
# =============================================================================

ORD_DIR="${ORD_DIR:-/root/.fitness_ordenes}"
ENV_FILE="${ENV_FILE:-.env}"
API_URL="${API_URL:-http://localhost:8000}"

# Estado que pasa de `aplicar` (antes de reconstruir) a `verificar` (después).
ORD_HUELLA=""
ORD_USER=""
ORD_PASS=""
ORD_PAUSA=""
ORD_NADMINS=""

_ord_valor_ok() { [[ "$1" =~ ^[A-Za-z0-9._@+-]{0,64}$ ]]; }

ordenes_preparar() {
  mkdir -p "$ORD_DIR" && chmod 700 "$ORD_DIR" || return 1
  rm -f "$ORD_DIR/pendiente"   # nunca sobrevive un estado de un despliegue anterior
  # Una orden ya aplicada deja su marca: no se vuelve a generar nada.
  if [ -s "$ORD_DIR/aplicadas" ] && [ -z "${CRED_ENC:-}" ]; then
    echo "— Órdenes del dueño: ya aplicadas, nada pendiente."
    return 0
  fi
  if [ ! -s "$ORD_DIR/clave.pem" ] && [ -z "${CRED_ENC:-}" ]; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
      -out "$ORD_DIR/clave.pem" 2>/dev/null || return 1
    chmod 600 "$ORD_DIR/clave.pem"
    openssl pkey -in "$ORD_DIR/clave.pem" -pubout -out "$ORD_DIR/publica.pem" || return 1
  fi
  if [ -s "$ORD_DIR/publica.pem" ] && [ -z "${CRED_ENC:-}" ]; then
    echo "— CLAVE PÚBLICA del servidor para cifrar órdenes (no es secreta):"
    cat "$ORD_DIR/publica.pem"
  fi
  ordenes_aplicar
}

ordenes_aplicar() {
  [ -n "${CRED_ENC:-}" ] || { echo "— Sin órdenes del dueño en este despliegue."; return 0; }

  local huella; huella=$(printf %s "$CRED_ENC" | sha256sum | cut -d' ' -f1)
  if grep -qs "$huella" "$ORD_DIR/aplicadas" 2>/dev/null; then
    echo "— Orden ${huella:0:8} ya aplicada antes: no se repite."
    return 0
  fi
  if [ ! -s "$ORD_DIR/clave.pem" ]; then
    echo "⚠️ Hay una orden pero el servidor no tiene su clave privada: no se toca nada."
    return 1
  fi

  local payload
  payload=$(printf %s "$CRED_ENC" | tr -d ' \r\n' | base64 -d 2>/dev/null \
    | openssl pkeyutl -decrypt -inkey "$ORD_DIR/clave.pem" \
        -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 2>/dev/null) || {
    echo "⚠️ La orden no se pudo descifrar (¿cifrada con otra clave?). No se toca nada."
    return 1
  }

  # Solo estas claves, solo estos caracteres: lo que no encaje se rechaza ENTERO
  # (un valor con comillas o saltos de línea corrompería el .env).
  # ⚠️ Los mensajes de error NO repiten NUNCA texto descifrado (el log del paso
  # es público): una línea sin `=` haría que `$k` fuera la línea entera, con la
  # contraseña dentro. Se valida la FORMA antes de partir en clave/valor y solo
  # se nombra una de las cinco claves permitidas, o el número de línea.
  local a1u="" a1p="" a2u="" a2p="" pausa="0" linea k v n=0 dio2u=0 dio2p=0
  while IFS= read -r linea || [ -n "$linea" ]; do
    n=$((n+1))
    linea="${linea%$'\r'}"
    [ -z "$linea" ] && continue
    case "$linea" in
      ADMIN_1_USER=*|ADMIN_1_PASS=*|ADMIN_2_USER=*|ADMIN_2_PASS=*|PAUSA=*) ;;
      *) echo "⚠️ Línea $n de la orden con formato inválido (se espera CLAVE=valor con una clave permitida). No se toca nada."
         return 1 ;;
    esac
    k="${linea%%=*}"; v="${linea#*=}"
    _ord_valor_ok "$v" || { echo "⚠️ Valor no permitido en $k (línea $n). No se toca nada."; return 1; }
    case "$k" in
      ADMIN_1_USER) a1u="$v" ;;
      ADMIN_1_PASS) a1p="$v" ;;
      ADMIN_2_USER) a2u="$v"; dio2u=1 ;;
      ADMIN_2_PASS) a2p="$v"; dio2p=1 ;;
      PAUSA)        pausa="$v" ;;
    esac
  done <<<"$payload"
  unset payload

  # Un admin siempre COMPLETO; el segundo, completo o vacío del todo (vacío =
  # un único acceso compartido). Un hueco a medias sería un error de edición.
  if [ -z "$a1u" ] || [ -z "$a1p" ]; then
    echo "⚠️ El admin 1 de la orden está incompleto. No se toca nada."; return 1
  fi
  # La orden debe DECLARAR el segundo admin (aunque sea vacío = dar de baja): si
  # no, "cambiar solo mi contraseña" borraría al segundo acceso sin avisar.
  if [ "$dio2u" != 1 ] || [ "$dio2p" != 1 ]; then
    echo "⚠️ La orden debe declarar ADMIN_2_USER y ADMIN_2_PASS (vacíos = sin segundo acceso). No se toca nada."; return 1
  fi
  if { [ -n "$a2u" ] && [ -z "$a2p" ]; } || { [ -z "$a2u" ] && [ -n "$a2p" ]; }; then
    echo "⚠️ El admin 2 de la orden está a medias. No se toca nada."; return 1
  fi
  if [ -n "$a2u" ] && [ "$a2u" = "$a1u" ]; then
    echo "⚠️ Los dos admins no pueden tener el mismo usuario. No se toca nada."; return 1
  fi
  [ "$pausa" = "0" ] || [ "$pausa" = "1" ] || { echo "⚠️ PAUSA debe ser 0 (no tocar la pausa) o 1 (activarla)."; return 1; }
  local nadmins=1; [ -n "$a2u" ] && nadmins=2

  [ -f "$ENV_FILE" ] || { echo "⚠️ No existe $ENV_FILE. No se toca nada."; return 1; }
  # Copia y temporal FUERA del repo (/root/fitness): así no aparecen como
  # ficheros sin seguir de git ni se cuelan en un `git add` descuidado.
  local copia="$ORD_DIR/env.bak-$(date +%Y%m%d-%H%M%S)"
  cp -p "$ENV_FILE" "$copia" || return 1
  local tmp; tmp=$(mktemp "$ORD_DIR/env.XXXXXX") || return 1
  # `-a`: un .env con algún byte raro no debe tratarse como binario y perder
  # líneas. rc=1 (ninguna línea seleccionada) es válido; rc>=2 es un fallo real.
  LC_ALL=C grep -avE '^(ADMIN_1_USER|ADMIN_1_PASS|ADMIN_2_USER|ADMIN_2_PASS)=' "$ENV_FILE" > "$tmp"
  [ $? -le 1 ] || { rm -f "$tmp"; echo "⚠️ No se pudo leer $ENV_FILE. No se toca nada."; return 1; }
  # El fichero original puede no acabar en salto de línea.
  if [ -s "$tmp" ] && [ -n "$(tail -c1 "$tmp")" ]; then printf '\n' >> "$tmp"; fi
  {
    printf 'ADMIN_1_USER=%s\n' "$a1u"
    printf 'ADMIN_1_PASS=%s\n' "$a1p"
    printf 'ADMIN_2_USER=%s\n' "$a2u"
    printf 'ADMIN_2_PASS=%s\n' "$a2p"
  } >> "$tmp" || { rm -f "$tmp"; echo "⚠️ No se pudo escribir el .env nuevo. No se toca nada."; return 1; }
  # Antes de sustituir: el nuevo debe traer exactamente las 4 variables ADMIN_*.
  [ "$(grep -c '^ADMIN_[12]_\(USER\|PASS\)=' "$tmp")" = 4 ] \
    || { rm -f "$tmp"; echo "⚠️ El .env nuevo no quedó bien formado. No se toca nada."; return 1; }
  chmod --reference="$ENV_FILE" "$tmp" 2>/dev/null || chmod 600 "$tmp"
  mv "$tmp" "$ENV_FILE" || return 1

  ( umask 077
    printf 'ORD_HUELLA=%s\nORD_USER=%s\nORD_PASS=%s\nORD_PAUSA=%s\nORD_NADMINS=%s\n' \
      "$huella" "$a1u" "$a1p" "$pausa" "$nadmins" > "$ORD_DIR/pendiente" ) || return 1
  # Sin nombres de usuario: el login del panel sale a internet y el log es
  # público; con el usuario conocido el secreto sería solo la contraseña.
  echo "✅ Orden ${huella:0:8}: .env actualizado (copia en $copia). Accesos al panel: $nadmins."
}

# Se llama DESPUÉS de reconstruir y de comprobar que la API vive.
ordenes_verificar() {
  [ -s "$ORD_DIR/pendiente" ] || { echo "— Órdenes del dueño: nada que verificar."; return 0; }
  local k v
  while IFS='=' read -r k v; do
    case "$k" in
      ORD_HUELLA|ORD_USER|ORD_PASS|ORD_PAUSA|ORD_NADMINS) printf -v "$k" '%s' "$v" ;;
    esac
  done < "$ORD_DIR/pendiente"
  rm -f "$ORD_DIR/pendiente"   # ya está en memoria: no se deja la contraseña en disco

  # ¿El contenedor arrancó con el .env nuevo? (compose lo recrea al cambiar el
  # env_file, pero un fallo aquí dejaría el acceso antiguo vivo sin avisar).
  local vivo
  vivo=$(docker compose exec -T api printenv ADMIN_1_USER 2>/dev/null | tr -d '\r\n')
  if [ "$vivo" != "$ORD_USER" ]; then
    echo "— El contenedor aún no tiene el .env nuevo: se recrea."
    docker compose up -d --no-deps --force-recreate api >/dev/null 2>&1 || true
    local i
    for i in 1 2 3 4 5 6 7 8; do
      sleep 5
      docker compose exec -T api curl -s --max-time 6 "$API_URL/api/health" >/dev/null 2>&1 && break
    done
  fi

  # Cuántos admins quedan en la base (sin imprimir sus nombres: el log es público).
  local cuantos
  cuantos=$(docker compose exec -T api python - <<'PY' 2>/dev/null | tr -d '\r\n'
from sqlalchemy import func, select
from app.db import SessionLocal
from app.models import User
db = SessionLocal()
print(db.execute(select(func.count()).select_from(User)).scalar())
PY
)
  if [ "$cuantos" = "$ORD_NADMINS" ]; then
    echo "✅ Accesos al panel en la base: $cuantos (los esperados)."
  else
    echo "❌ Accesos al panel en la base: ${cuantos:-?} (se esperaban $ORD_NADMINS). La orden queda sin marcar."
    ORD_PASS=""; return 1
  fi

  # Login con la credencial NUEVA. La contraseña va por stdin (nunca en argv) y
  # lo único que se imprime es el código HTTP.
  local resp token code
  resp=$(printf 'url = "%s/api/auth/login"\nrequest = "POST"\nheader = "Content-Type: application/json"\ndata = "{\\"username\\":\\"%s\\",\\"password\\":\\"%s\\"}"\n' \
    "$API_URL" "$ORD_USER" "$ORD_PASS" \
    | docker compose exec -T api curl -s --max-time 10 -K - 2>/dev/null)
  token=$(printf '%s' "$resp" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
  if [ -z "$token" ]; then
    echo "❌ El login con la credencial nueva FALLA. La orden queda sin marcar (se puede reintentar)."
    ORD_PASS=""; return 1
  fi
  echo "✅ Login con la credencial nueva: OK (HTTP 200)."

  if [ "$ORD_PAUSA" = "1" ]; then
    code=$(printf 'url = "%s/api/system/mantenimiento"\nrequest = "POST"\nheader = "Content-Type: application/json"\nheader = "Authorization: Bearer %s"\ndata = "{\\"activo\\":true}"\nwrite-out = "%%{http_code}"\noutput = "/dev/null"\nsilent\n' \
      "$API_URL" "$token" \
      | docker compose exec -T api curl --max-time 10 -K - 2>/dev/null)
    echo "— Activar la pausa del acceso público: HTTP ${code:-?}"
    code=$(docker compose exec -T api curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
      "$API_URL/api/public/landing" 2>/dev/null)
    if [ "$code" = "503" ]; then
      echo "✅ Acceso público en pausa: /api/public/landing responde 503."
    else
      echo "❌ La pausa NO está activa (landing responde ${code:-?})."
      ORD_PASS=""; return 1
    fi
  fi

  # Todo comprobado: la orden queda como aplicada y la clave privada se destruye.
  echo "$ORD_HUELLA" >> "$ORD_DIR/aplicadas"
  rm -f "$ORD_DIR/clave.pem" "$ORD_DIR/publica.pem"
  ORD_PASS=""
  echo "✅ Orden ${ORD_HUELLA:0:8} aplicada y verificada; clave de cifrado destruida."
}

# Punto de entrada cuando se ejecuta como programa (no cuando se carga con `.`).
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    preparar)  ordenes_preparar ;;
    verificar) ordenes_verificar ;;
    *) echo "uso: bash deploy/ordenes_del_dueno.sh preparar|verificar"; exit 2 ;;
  esac
fi
