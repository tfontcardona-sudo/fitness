#!/bin/sh
set -e

echo "[entrypoint] esperando a la base de datos…"
python - << 'PYEOF'
import time, sys
from sqlalchemy import create_engine, text
from app.config import settings

for attempt in range(30):
    try:
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        print("[entrypoint] base de datos lista")
        sys.exit(0)
    except Exception:
        time.sleep(1)
print("[entrypoint] la base de datos no responde", file=sys.stderr)
sys.exit(1)
PYEOF

echo "[entrypoint] aplicando migraciones…"
alembic upgrade head

echo "[entrypoint] ejecutando seeds idempotentes…"
python -m app.seeds.run

echo "[entrypoint] arrancando API…"
exec "$@"
