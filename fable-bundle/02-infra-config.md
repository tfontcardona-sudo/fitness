

===== FILE: docker-compose.yml =====

name: fitness-system

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-fitness}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-fitness}
      POSTGRES_DB: ${POSTGRES_DB:-fitness}
      TZ: ${TZ:-Europe/Madrid}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-fitness} -d ${POSTGRES_DB:-fitness}"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build:
      context: ./backend
    restart: unless-stopped
    env_file: .env
    environment:
      STORAGE_PATH: /storage
    volumes:
      - ./storage:/storage
    depends_on:
      db:
        condition: service_healthy
    expose:
      - "8000"

  web:
    build:
      context: ./frontend
    restart: unless-stopped
    environment:
      DOMAIN: ${DOMAIN:-}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api

volumes:
  db_data:
  caddy_data:
  caddy_config:


===== FILE: docker-compose.dev.yml =====

# Uso: docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# Añade: hot-reload del backend, servidor Vite, Mailpit para ver emails, puertos abiertos.

services:
  db:
    ports:
      - "5432:5432"

  api:
    build:
      context: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/code
      - ./storage:/storage
    ports:
      - "8000:8000"
    environment:
      SMTP_HOST: mailpit
      SMTP_PORT: "1025"
      SMTP_USER: ""
      SMTP_PASS: ""
      SMTP_FROM: dev@fitness.local
    depends_on:
      mailpit:
        condition: service_started
      db:
        condition: service_healthy

  web:
    # En dev usamos el servidor de Vite con HMR en lugar del build estático
    build:
      context: ./frontend
      target: build
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"
    working_dir: /app
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://api:8000

  mailpit:
    image: axllent/mailpit:latest
    restart: unless-stopped
    ports:
      - "8025:8025"   # UI web para ver los emails enviados
      - "1025:1025"   # SMTP

volumes:
  frontend_node_modules:


===== FILE: backend/Dockerfile =====

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Madrid

WORKDIR /code

# Dependencias del sistema para matplotlib/pillow/psycopg + LibreOffice headless
# (conversión determinista de los planes .docx → PDF, idéntica a la del QA) y fuentes.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libfreetype6 libjpeg62-turbo zlib1g curl \
    libreoffice-writer libreoffice-core fonts-liberation fonts-dejavu-core \
    fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /code/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


===== FILE: backend/entrypoint.sh =====

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


===== FILE: backend/requirements.txt =====

# --- Core API ---
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.4
pydantic-settings==2.9.1
python-multipart==0.0.20
email-validator==2.2.0
# --- Base de datos ---
sqlalchemy==2.0.40
alembic==1.15.2
psycopg[binary]==3.2.6

# --- Seguridad ---
pyjwt==2.10.1
bcrypt==4.2.1
itsdangerous==2.2.0
slowapi==0.1.9

# --- IA ---
anthropic==0.51.0
httpx==0.28.1

# --- Scheduler ---
apscheduler==3.11.0

# --- Documentos y gráficas ---
python-docx==1.1.2
reportlab==4.4.0
matplotlib==3.10.1
pillow==11.2.1

# --- Email y plantillas ---
aiosmtplib==4.0.1
jinja2==3.1.6

# --- Tests ---
pytest==8.3.5
pytest-asyncio==0.26.0


===== FILE: backend/alembic.ini =====

[alembic]
script_location = alembic
prepend_sys_path = .
# La URL real se inyecta desde app.config.settings en alembic/env.py
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S


===== FILE: backend/alembic/env.py =====

"""Entorno de Alembic: toma la URL de app.config.settings.

En la Fase 1, `target_metadata` se conecta a Base.metadata de los modelos
para soportar autogeneración de migraciones.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db import Base
import app.models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


===== FILE: frontend/package.json =====

{
  "name": "fitness-system-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "date-fns": "^3.6.0",
    "lucide-react": "^0.383.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.3",
    "vite": "^5.3.4"
  }
}


===== FILE: frontend/vite.config.ts =====

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev, las llamadas a /api se proxyean al backend (hot-reload completo).
// En producción, Caddy hace este papel.
export default defineConfig({
  plugins: [react()],
  server: {
    // En Windows + Docker el watcher nativo no detecta cambios del bind mount;
    // el polling garantiza que el hot-reload SIEMPRE recoja las ediciones.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});


===== FILE: frontend/tsconfig.json =====

{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}


===== FILE: frontend/postcss.config.js =====

export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};


===== FILE: frontend/index.html =====

<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex" />
    <title>Asesorías Fitness</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>


===== FILE: .env.example =====

# ============================================================
# SISTEMA DE ASESORÍAS FITNESS — Variables de entorno
# Copia este archivo a .env y rellena los valores.
# ============================================================

# --- IA (Anthropic) ---
ANTHROPIC_API_KEY=
MODEL_HEAVY=claude-opus-4-8
MODEL_LIGHT=claude-haiku-4-5-20251001

# --- Base de datos ---
# En Docker se resuelve contra el servicio "db"
DATABASE_URL=postgresql+psycopg://fitness:fitness@db:5432/fitness
POSTGRES_USER=fitness
POSTGRES_PASSWORD=fitness
POSTGRES_DB=fitness

# --- Seguridad ---
JWT_SECRET=cambia-esto-por-una-cadena-larga-aleatoria
PORTAL_TOKEN_SECRET=cambia-esto-por-otra-cadena-larga-aleatoria

# --- Usuarios admin (seed inicial, single-tenant) ---
ADMIN_1_USER=coach1
ADMIN_1_PASS=cambiar-en-produccion
ADMIN_2_USER=coach2
ADMIN_2_PASS=cambiar-en-produccion

# --- URLs y dominio ---
# DOMAIN vacío => Caddy sirve en :80 sin TLS (dev / pruebas en VPS sin dominio)
# DOMAIN=app.tudominio.com => Caddy obtiene certificado HTTPS automático
DOMAIN=
BASE_URL=http://localhost
STORAGE_PATH=./storage

# --- Email (SMTP) ---
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
EMAILS_ENABLED=true

# --- Comportamiento ---
AUTO_PILOT_DEFAULT=false
TZ=Europe/Madrid


===== FILE: .gitignore =====

# Entorno
.env
__pycache__/
*.pyc
.venv/
venv/

# Frontend
node_modules/
frontend/dist/

# Datos y almacenamiento (nunca al repo: datos de salud RGPD)
storage/*
!storage/.gitkeep

# Varios
.DS_Store
*.log
.pytest_cache/
