#!/usr/bin/env bash
# Demo de Professional en TU máquina, en un comando: ./demo.sh
# Levanta todo con Docker, siembra los 3 clientes de demo y te da los enlaces.
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

echo "→ Levantando la demo (la primera vez tarda unos minutos)…"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

echo "→ Esperando a la API…"
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/docs >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "→ Sembrando los 3 clientes de demo…"
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/demo_seed.py

cat <<FIN

════════════════════════════════════════════════════════
  DEMO LISTA
  Panel del coach:    http://localhost:5173
  Página de planes:   http://localhost:5173/planes
  Login del panel:    (usuario y contraseña del .env)
  Enlaces del portal: arriba, impresos por el script
  Guión de la demo:   DEMO.md
  Reiniciar la demo:  ./demo.sh (se puede re-ejecutar siempre)
  Apagar:             docker compose -f docker-compose.yml -f docker-compose.dev.yml down
════════════════════════════════════════════════════════
FIN
