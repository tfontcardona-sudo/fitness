#!/usr/bin/env bash
# Demo de Professional en TU máquina, en un comando: ./demo.sh
# Levanta todo con Docker, siembra los 4 clientes de demo y te da los enlaces.
set -e
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "✗ Falta Docker. Instala Docker Desktop: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

# .env de demo si no existe (credenciales del panel: professional / cámbialas si quieres)
if [ ! -f .env ]; then
  cp .env.example .env
  # sed -i.bak funciona igual en GNU (Linux) y BSD (macOS)
  sed -i.bak \
    -e 's/^ADMIN_1_USER=.*/ADMIN_1_USER=professional/' \
    -e 's/^ADMIN_1_PASS=.*/ADMIN_1_PASS=Professional-Demo-2026/' \
    -e 's/^EMAILS_ENABLED=.*/EMAILS_ENABLED=false/' .env
  rm -f .env.bak
  echo "✓ .env creado (panel: professional / Professional-Demo-2026)"
  echo "  · Para IA en vivo (leer anamnesis / generar plan): añade ANTHROPIC_API_KEY al .env"
fi

# ACTUALIZARSE PRIMERO: el doble clic debe traer la última versión del código.
# Sin esto, el lanzador levantaba lo que hubiera en la carpeta aunque los
# cambios llevaran semanas subidos (pasó: la web "no cambiaba nunca").
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
  echo "→ Buscando la última versión del código…"
  if git pull --ff-only; then
    echo "✓ Código al día"
  else
    echo "! No se pudo actualizar (¿sin conexión o cambios locales?): sigo con la versión de la carpeta"
  fi
fi

# En dev el servicio `web` es Vite (5173), no Caddy: sus 80 y 443 quedarían
# publicados para nada y en Windows el 80 suele estar cogido. Si no puede
# reservarlos, el contenedor no arranca — pero la API sí, así que el lanzador
# daba la demo por lista y localhost:5173 no abría. Apartados a puertos altos.
export HTTP_PORT=8380 HTTPS_PORT=8343

# Apaga ESTE proyecto si estaba (a medias o entero): re-ejecutar = reiniciar.
# Sin esto, el chequeo de puertos de abajo se tropezaba con NUESTROS propios
# contenedores y el script abortaba culpando a otro proyecto.
docker compose -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans >/dev/null 2>&1 || true

# Si DQR (u otro proyecto) está arrancado en este PC, usa los mismos puertos:
# hay que pararlo primero (los proyectos están AISLADOS, pero no caben a la vez).
for port in 5173 8000 5432 8025 8380 8343; do
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    exec 3>&- 3<&-
    echo "✗ El puerto $port ya está en uso. ¿Tienes DQR u otro proyecto arrancado?"
    echo "  Páralo primero desde su carpeta:  docker compose down"
    exit 1
  fi
done

echo "→ Levantando la demo (la primera vez tarda unos minutos)…"
# El código de salida IMPORTA: si un contenedor no puede reservar su puerto,
# compose falla pero los que sí arrancaron siguen en pie. Sin esta comprobación,
# la API respondía, el script decía "DEMO LISTA" y la web no abría.
if ! docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build; then
  echo
  echo "✗ Docker no ha podido levantar la demo (el motivo va justo arriba)."
  exit 1
fi

echo "→ Esperando a la API…"
api_ok=0
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/docs >/dev/null 2>&1; then api_ok=1; break; fi
  sleep 2
done
# Si no arranca, ENSEÑAR el motivo aquí mismo: mandar al usuario a buscar los
# logs por su cuenta convertía cada fallo en una ronda de preguntas.
if [ "$api_ok" -ne 1 ]; then
  echo
  echo "✗ La API no arranca. Este es el motivo, tal cual:"
  echo "-----------------------------------------------------"
  docker compose -f docker-compose.yml -f docker-compose.dev.yml logs api --tail 40 --no-color 2>&1 || true
  echo "-----------------------------------------------------"
  exit 1
fi

echo "→ Sembrando los 4 clientes de demo…"
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/demo_seed.py

# ESPERAR TAMBIÉN A LA WEB. El lanzador solo miraba la API, así que cualquier
# problema del contenedor `web` acababa en un "DEMO LISTA" con localhost:5173
# sin abrir — el peor final posible: parece que todo fue bien. Va después del
# seed a propósito: en dev el contenedor hace `npm install` y la primera vez
# tarda varios minutos; darle ese margen extra evita falsos negativos.
echo "→ Esperando al panel (la primera vez instala dependencias, tarda)…"
web_ok=0
for i in $(seq 1 150); do
  if curl -sf http://localhost:5173 >/dev/null 2>&1; then web_ok=1; break; fi
  sleep 2
done
if [ "$web_ok" -ne 1 ]; then
  echo
  echo "✗ El panel no responde en http://localhost:5173. Este es el motivo:"
  echo "-----------------------------------------------------"
  docker compose -f docker-compose.yml -f docker-compose.dev.yml logs web --tail 40 --no-color 2>&1 || true
  echo "-----------------------------------------------------"
  exit 1
fi

# Decir las credenciales EXACTAS, comprobadas contra la base de datos. Antes
# esta línea decía "usuario y contraseña del .env" y quien no abría el fichero
# se quedaba adivinando delante de un "credenciales incorrectas".
# El script sale con 1 si las credenciales NO entran, y ese caso es justo el
# que hay que enseñar: se captura la salida pase lo que pase.
login_msg=$(docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  exec -T api python scripts/check_login.py 2>&1 | tr -d '\r') || true
[ -n "$login_msg" ] || login_msg="(no se pudo comprobar: mira ADMIN_1_USER y ADMIN_1_PASS en el .env)"

cat <<FIN

════════════════════════════════════════════════════════
  DEMO LISTA
  Panel del coach:    http://localhost:5173
  Página de planes:   http://localhost:5173/planes
  Login del panel:    $login_msg
  Enlaces del portal: arriba, impresos por el script
  Guión de la demo:   DEMO.md
  Reiniciar la demo:  ./demo.sh (se puede re-ejecutar siempre)
  Apagar:             docker compose -f docker-compose.yml -f docker-compose.dev.yml down
════════════════════════════════════════════════════════
FIN
