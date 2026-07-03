# Código BACKEND — Fitness System

> Snapshot completo del código (un bloque por archivo, con su ruta). Generado para traspaso. Total: 53 archivos.


## `.env.example`

```
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

```


## `backend/Dockerfile`

```
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Madrid

WORKDIR /code

# Dependencias del sistema para matplotlib/pillow/psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libfreetype6 libjpeg62-turbo zlib1g curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /code/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

```


## `backend/app/__init__.py`

```python

```


## `backend/app/api/__init__.py`

```python

```


## `backend/app/config.py`

```python
"""Configuración central de la aplicación.

Todas las variables se leen del entorno (.env). Una sola fuente de verdad:
cualquier servicio (API, scheduler, generación de documentos, email) importa
`settings` desde aquí.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- IA ---
    anthropic_api_key: str = ""
    model_heavy: str = "claude-opus-4-8"
    model_light: str = "claude-haiku-4-5-20251001"

    # --- Base de datos ---
    database_url: str = "postgresql+psycopg://fitness:fitness@db:5432/fitness"

    # --- Seguridad ---
    jwt_secret: str = "dev-insecure-jwt-secret"
    portal_token_secret: str = "dev-insecure-portal-secret"
    jwt_expire_minutes: int = 60 * 12  # jornada de trabajo del coach

    # --- Admins (seed inicial single-tenant) ---
    admin_1_user: str = ""
    admin_1_pass: str = ""
    admin_2_user: str = ""
    admin_2_pass: str = ""

    # --- URLs y almacenamiento ---
    domain: str = ""
    base_url: str = "http://localhost"
    storage_path: str = "./storage"

    # --- Email ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""
    emails_enabled: bool = True

    # --- Comportamiento ---
    auto_pilot_default: bool = False
    tz: str = "Europe/Madrid"

    @property
    def public_base_url(self) -> str:
        """URL pública del sistema (portal, links de email)."""
        if self.domain:
            return f"https://{self.domain}"
        return self.base_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

```


## `backend/app/db.py`

```python
"""Capa de base de datos: engine, Base declarativa y sesión.

Única fuente del engine para API, scheduler y scripts (seeds, migraciones).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

```


## `backend/app/deps.py`

```python
"""Dependencias compartidas de los routers."""


from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Client, User
from app.security import decode_access_token, portal_token_client_id

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Coach autenticado vía JWT Bearer (app de coaches)."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticación requerida")
    username = decode_access_token(credentials.credentials)
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado")
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")
    return user


def get_client_by_token(
    token: str = Path(min_length=10, max_length=255),
    db: Session = Depends(get_db),
) -> Client:
    """Cliente del portal: firma válida + coincidencia exacta en DB (revocable).

    404 genérico en cualquier fallo: no filtra si un token existió o fue revocado.
    """
    client_id = portal_token_client_id(token)
    if client_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    client = db.get(Client, client_id)
    if client is None or client.portal_token != token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    return client

```


## `backend/app/main.py`

```python
"""Punto de entrada de la API.

Health check + CORS + registro de routers. Migraciones y seeds se ejecutan
en entrypoint.sh antes de arrancar; el scheduler se añade en la Fase 4.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.routers import auth, brand, clients, exercises, plans, portal_public

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El scheduler se desactiva en tests/CI con SCHEDULER_ENABLED=false.
    scheduler_on = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler, start_scheduler

        start_scheduler()
    yield
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler

        shutdown_scheduler()
    engine.dispose()


app = FastAPI(
    title="Sistema de Asesorías Fitness",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiting compartido (los routers definen sus límites con su propio
# Limiter; este objeto en app.state habilita el manejador global de errores).
app.state.limiter = Limiter(key_func=get_remote_address)


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Demasiadas peticiones, inténtalo en un momento"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.public_base_url,
        "http://localhost",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(exercises.router)
app.include_router(brand.router)
app.include_router(plans.router)
app.include_router(portal_public.router)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Health check para monitoring (VPS) y para el healthcheck de Docker."""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": APP_VERSION,
        "database": "up" if db_ok else "down",
    }

```


## `backend/app/models.py`

```python
"""Modelos SQLAlchemy — contratos de PARTE C.1 (nombres exactos, no renombrar).

Decisiones declaradas (protocolo A.1.2):
- Tabla extra `users` (coaches/admins, single-tenant; seed desde ADMIN_x del .env).
- Campo extra `daily_logs.option_feedback_json` (valoración 👍/👎 de la opción
  elegida) para que "opciones mejor valoradas" del análisis mensual tenga dato real.
- Campo extra `exercises.archived` para retirar ejercicios de la biblioteca sin
  romper el historial de workout_logs.
- Enums como String + Literal en Pydantic (sin tipos ENUM nativos de Postgres:
  migraciones más simples, validación en la capa de aplicación).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- users ----
class User(Base):
    """Coaches/admins del sistema (single-tenant, 2 usuarios seedados)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# -------------------------------------------------------------- clients ----
class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))

    # Anamnesis — nullable hasta que el cliente la complete vía link público
    sex: Mapped[str | None] = mapped_column(String(10))  # male|female
    birth_date: Mapped[date | None] = mapped_column(Date)
    height_cm: Mapped[float | None] = mapped_column(Float)
    start_weight_kg: Mapped[float | None] = mapped_column(Float)
    current_weight_kg: Mapped[float | None] = mapped_column(Float)
    body_fat_pct: Mapped[float | None] = mapped_column(Float)
    goal_type: Mapped[str | None] = mapped_column(String(20))  # fat_loss|muscle_gain|recomp
    goal_weight_kg: Mapped[float | None] = mapped_column(Float)
    goal_deadline: Mapped[date | None] = mapped_column(Date)
    level: Mapped[str | None] = mapped_column(String(20))  # beginner|intermediate|advanced
    training_days: Mapped[int | None] = mapped_column(Integer)
    session_max_min: Mapped[int | None] = mapped_column(Integer)
    training_place: Mapped[str | None] = mapped_column(String(20))  # gym|home|outdoor
    equipment: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    excluded_exercise_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    injuries_notes: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    medication_notes: Mapped[str | None] = mapped_column(Text)
    sport_history: Mapped[str | None] = mapped_column(Text)
    meals_per_day: Mapped[int | None] = mapped_column(Integer)
    meal_schedule: Mapped[list | None] = mapped_column(JSONB)  # [{slot,name,time}]
    food_allergies: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    food_dislikes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    food_likes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    lifestyle_notes: Mapped[str | None] = mapped_column(Text)
    current_supplements: Mapped[str | None] = mapped_column(Text)
    diet_mode: Mapped[str | None] = mapped_column(String(20))  # flexible_7|strict
    strict_free_meal_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Gestión
    status: Mapped[str] = mapped_column(String(30), default="onboarding", index=True)
    auto_pilot: Mapped[bool] = mapped_column(Boolean, default=False)
    emails_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    portal_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    consent_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    plans: Mapped[list[Plan]] = relationship(back_populates="client")
    periods: Mapped[list[Period]] = relationship(back_populates="client")


# ---------------------------------------------------------------- plans ----
class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("client_id", "month_index", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    month_index: Mapped[int] = mapped_column(Integer)  # 1, 2, 3…
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|published|superseded
    nutrition_json: Mapped[dict | None] = mapped_column(JSONB)
    training_json: Mapped[dict | None] = mapped_column(JSONB)
    education_json: Mapped[dict | None] = mapped_column(JSONB)
    guardrail_flags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    generated_by: Mapped[str | None] = mapped_column(String(80))  # modelo IA o "coach"
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped[Client] = relationship(back_populates="plans")


# -------------------------------------------------------------- periods ----
class Period(Base):
    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    period_index: Mapped[int] = mapped_column(Integer)  # global: 1, 2, 3…
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|closed|analyzed

    # Cierre (cliente)
    closing_weight_kg: Mapped[float | None] = mapped_column(Float)
    closing_rating: Mapped[int | None] = mapped_column(Integer)  # 1–5
    closing_hardest: Mapped[str | None] = mapped_column(Text)
    closing_questions: Mapped[str | None] = mapped_column(Text)
    closing_waist_cm: Mapped[float | None] = mapped_column(Float)
    closing_hip_cm: Mapped[float | None] = mapped_column(Float)
    closing_arm_cm: Mapped[float | None] = mapped_column(Float)
    closing_thigh_cm: Mapped[float | None] = mapped_column(Float)

    # Pipeline (backend + IA)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB)
    ai_analysis_json: Mapped[dict | None] = mapped_column(JSONB)
    ai_photo_analysis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped[Client] = relationship(back_populates="periods")
    daily_logs: Mapped[list[DailyLog]] = relationship(back_populates="period")


# ----------------------------------------------------------- daily_logs ----
class DailyLog(Base):
    __tablename__ = "daily_logs"
    __table_args__ = (UniqueConstraint("period_id", "log_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), index=True)
    log_date: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    diet_adherence: Mapped[str | None] = mapped_column(String(10))  # yes|partial|no
    diet_notes: Mapped[str | None] = mapped_column(Text)
    energy_1_5: Mapped[int | None] = mapped_column(Integer)
    mood_1_5: Mapped[int | None] = mapped_column(Integer)
    fatigue_1_5: Mapped[int | None] = mapped_column(Integer)
    free_notes: Mapped[str | None] = mapped_column(Text)
    chosen_options_json: Mapped[dict | None] = mapped_column(JSONB)  # {slot: "A"…}
    option_feedback_json: Mapped[dict | None] = mapped_column(JSONB)  # {slot: "up"|"down"}

    period: Mapped[Period] = relationship(back_populates="daily_logs")
    workout_logs: Mapped[list[WorkoutLog]] = relationship(back_populates="daily_log")


# --------------------------------------------------------- workout_logs ----
class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    daily_log_id: Mapped[int] = mapped_column(ForeignKey("daily_logs.id"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    set_number: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    rpe: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    daily_log: Mapped[DailyLog] = relationship(back_populates="workout_logs")


# ------------------------------------------------------------ exercises ----
class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    muscle_primary: Mapped[str] = mapped_column(String(40), index=True)
    muscle_secondary: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    movement_pattern: Mapped[str] = mapped_column(String(40), index=True)
    equipment: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    level_min: Mapped[int] = mapped_column(Integer, default=1)  # 1 princ. 2 inter. 3 avanz.
    video_url: Mapped[str | None] = mapped_column(String(500))  # editable por el coach
    technique_notes: Mapped[str | None] = mapped_column(Text)
    biomechanics_notes: Mapped[str | None] = mapped_column(Text)
    contraindications: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


# ------------------------------------------------------ progress_photos ----
class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    period_id: Mapped[int | None] = mapped_column(ForeignKey("periods.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # front|side|back|detail
    file_path: Mapped[str] = mapped_column(String(500))
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# -------------------------------------------------------- feedback_docs ----
class FeedbackDoc(Base):
    __tablename__ = "feedback_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # biweekly|monthly
    content_json: Mapped[dict | None] = mapped_column(JSONB)
    docx_path: Mapped[str | None] = mapped_column(String(500))
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------- brand_config ----
class BrandConfig(Base):
    __tablename__ = "brand_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="Mi Asesoría")
    logo_path: Mapped[str | None] = mapped_column(String(500))
    color_primary: Mapped[str] = mapped_column(String(9), default="#6EE7B7")
    color_secondary: Mapped[str] = mapped_column(String(9), default="#34D399")
    color_bg: Mapped[str] = mapped_column(String(9), default="#0A0A0F")
    font_family: Mapped[str] = mapped_column(String(40), default="Inter")
    tagline: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(160))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    contact_web: Mapped[str | None] = mapped_column(String(200))
    docs_theme: Mapped[str] = mapped_column(String(10), default="light")  # light|dark
    portal_theme: Mapped[str] = mapped_column(String(10), default="dark")  # light|dark


# ------------------------------------------------------------ email_log ----
class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(String(255))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(20))  # sent|failed|disabled


# ------------------------------------------------------ change_requests ----
class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="open", index=True)  # open|resolved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ------------------------------------------------------------ audit_log ----
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    event: Mapped[str] = mapped_column(String(60), index=True)
    detail_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

```


## `backend/app/routers/__init__.py`

```python

```


## `backend/app/routers/auth.py`

```python
"""Autenticación de coaches (JWT)."""


from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.entities import LoginIn, TokenOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Login de los admins seedados desde el .env. 5 intentos/minuto por IP."""
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        # Mensaje único: no revela si el usuario existe
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    return TokenOut(access_token=create_access_token(user.username))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "username": user.username}

```


## `backend/app/routers/brand.py`

```python
"""Configuración de marca (H.1) — única fila, aplica a app/portal/docs/emails."""


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import BrandConfig
from app.schemas.entities import BrandConfigIn, BrandConfigOut
from app.services.audit import log_event
from app.services.storage import PhotoValidationError, save_brand_logo

router = APIRouter(prefix="/api/brand", tags=["brand"], dependencies=[Depends(get_current_user)])


def _brand(db: Session) -> BrandConfig:
    brand = db.scalar(select(BrandConfig).limit(1))
    if not brand:  # el seed la crea; defensa por si se vació la tabla
        brand = BrandConfig()
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


@router.get("", response_model=BrandConfigOut)
def get_brand(db: Session = Depends(get_db)) -> BrandConfigOut:
    return BrandConfigOut.model_validate(_brand(db))


@router.put("", response_model=BrandConfigOut)
def update_brand(body: BrandConfigIn, db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    for field, value in body.model_dump().items():
        setattr(brand, field, value)
    log_event(db, "brand", brand.id, "brand_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)


@router.post("/logo", response_model=BrandConfigOut)
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    try:
        brand.logo_path = save_brand_logo(file.file.read(), file.filename or "logo")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_logo_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)

```


## `backend/app/routers/clients.py`

```python
"""CRUD de clientes + links de portal + RGPD (supresión y portabilidad)."""


import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import (
    ChangeRequest,
    Client,
    DailyLog,
    EmailLog,
    FeedbackDoc,
    Period,
    Plan,
    ProgressPhoto,
    User,
    WorkoutLog,
)
from app.schemas.entities import (
    ClientCreate,
    ClientCreatedOut,
    ClientOut,
    ClientStatus,
    ClientUpdate,
    PortalLinkOut,
)
from app.security import new_portal_token
from app.services.audit import log_event
from app.services.storage import (
    DocumentValidationError,
    abs_path,
    delete_client_tree,
    list_documents,
    save_document,
    storage_root,
)

router = APIRouter(
    prefix="/api/clients", tags=["clients"], dependencies=[Depends(get_current_user)]
)


def _links(client: Client) -> PortalLinkOut:
    base = settings.public_base_url
    return PortalLinkOut(
        portal_token=client.portal_token,
        portal_url=f"{base}/p/{client.portal_token}",
        anamnesis_url=f"{base}/p/{client.portal_token}/anamnesis",
    )


def _get_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return client


# ------------------------------------------------------------------ alta ----
@router.post("", response_model=ClientCreatedOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientCreate, db: Session = Depends(get_db)) -> ClientCreatedOut:
    """Alta mínima: nombre + email (+ teléfono). El resto lo aporta el cliente
    en el wizard de anamnesis vía el link público que devuelve esta llamada."""
    if db.scalar(select(Client).where(Client.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")

    client = Client(
        full_name=body.full_name.strip(),
        email=body.email,
        phone=body.phone,
        status="onboarding",
        auto_pilot=settings.auto_pilot_default,
        portal_token="pendiente",  # se firma con el id real tras el flush
    )
    db.add(client)
    db.flush()
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "client_created", {"by": "coach"})
    db.commit()
    db.refresh(client)
    return ClientCreatedOut(client=ClientOut.model_validate(client), links=_links(client))


# --------------------------------------------------------------- listado ----
@router.get("", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    status_filter: ClientStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/email"),
) -> list[ClientOut]:
    stmt = select(Client).order_by(Client.created_at.desc())
    if status_filter:
        stmt = stmt.where(Client.status == status_filter)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Client.full_name.ilike(like), Client.email.ilike(like)))
    return [ClientOut.model_validate(c) for c in db.scalars(stmt)]


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientOut:
    return ClientOut.model_validate(_get_or_404(db, client_id))


# ---------------------------------------------------- edición con audit ----
@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientUpdate, db: Session = Depends(get_db)) -> ClientOut:
    """Edición por el coach (anamnesis editable con audit trail, H.2)."""
    client = _get_or_404(db, client_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return ClientOut.model_validate(client)

    diff: dict[str, dict] = {}
    for field, new_value in changes.items():
        old_value = getattr(client, field)
        serialized_new = (
            [item if isinstance(item, dict) else item.model_dump() for item in new_value]
            if field == "meal_schedule" and new_value is not None
            else new_value
        )
        if old_value != serialized_new:
            diff[field] = {"from": _jsonable(old_value), "to": _jsonable(serialized_new)}
        setattr(client, field, serialized_new)

    if diff:
        log_event(db, "client", client.id, "client_updated", {"fields": diff})
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


def _jsonable(value):
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


# ----------------------------------------------------------------- links ----
@router.get("/{client_id}/portal-link", response_model=PortalLinkOut)
def portal_link(client_id: int, db: Session = Depends(get_db)) -> PortalLinkOut:
    return _links(_get_or_404(db, client_id))


@router.post("/{client_id}/portal-token/regenerate", response_model=PortalLinkOut)
def regenerate_portal_token(client_id: int, db: Session = Depends(get_db)) -> PortalLinkOut:
    """Revoca el token anterior (deja de coincidir en DB) y firma uno nuevo."""
    client = _get_or_404(db, client_id)
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "portal_token_regenerated", None)
    db.commit()
    db.refresh(client)
    return _links(client)


# ------------------------------------------------- RGPD: portabilidad ----
@router.get("/{client_id}/export")
def export_client_zip(client_id: int, db: Session = Depends(get_db)) -> Response:
    """\"Descargar todo\": ZIP con datos estructurados + fotos + documentos."""
    client = _get_or_404(db, client_id)

    data = {
        "client": json.loads(ClientOut.model_validate(client).model_dump_json()),
        "plans": [
            {
                "month_index": p.month_index, "version": p.version, "status": p.status,
                "nutrition": p.nutrition_json, "training": p.training_json,
                "education": p.education_json, "published_at": _jsonable(p.published_at),
            }
            for p in db.scalars(select(Plan).where(Plan.client_id == client_id).order_by(Plan.month_index, Plan.version))
        ],
        "periods": [
            {
                "period_index": pe.period_index, "starts_on": _jsonable(pe.starts_on),
                "ends_on": _jsonable(pe.ends_on), "status": pe.status,
                "closing_weight_kg": pe.closing_weight_kg, "metrics": pe.metrics_json,
            }
            for pe in db.scalars(select(Period).where(Period.client_id == client_id).order_by(Period.period_index))
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("datos.json", json.dumps(data, ensure_ascii=False, indent=2))
        photos = db.scalars(select(ProgressPhoto).where(ProgressPhoto.client_id == client_id))
        for ph in photos:
            p = abs_path(ph.file_path)
            if p.exists():
                zf.write(p, f"fotos/{p.name}")
        docs_dir = storage_root() / "clients" / str(client_id) / "documents"
        if docs_dir.exists():
            for f in sorted(docs_dir.iterdir()):
                if f.is_file():
                    zf.write(f, f"documentos/{f.name}")

    log_event(db, "client", client.id, "client_exported", None)
    db.commit()
    # El header Content-Disposition viaja en latin-1: normalizamos el nombre a
    # ASCII (sin tildes ni ñ) para no romper la cabecera con nombres como "López".
    import unicodedata

    ascii_name = (
        unicodedata.normalize("NFKD", client.full_name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in ascii_name).strip("_").lower() or "cliente"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="export_{safe_name}.zip"'},
    )


# --------------------------------------------------- RGPD: supresión ----
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    confirm: str = Query(description="Debe coincidir EXACTAMENTE con el nombre completo"),
    db: Session = Depends(get_db),
) -> Response:
    """Supresión total RGPD con doble confirmación: modal en UI + nombre
    tecleado verificado aquí. Borra DB + archivos; deja registro anónimo."""
    client = _get_or_404(db, client_id)
    if confirm != client.full_name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La confirmación no coincide con el nombre completo del cliente",
        )

    period_ids = list(db.scalars(select(Period.id).where(Period.client_id == client_id)))
    if period_ids:
        daily_ids = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id.in_(period_ids))))
        if daily_ids:
            db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(daily_ids)))
            db.execute(delete(DailyLog).where(DailyLog.id.in_(daily_ids)))
        db.execute(delete(FeedbackDoc).where(FeedbackDoc.period_id.in_(period_ids)))
    db.execute(delete(ProgressPhoto).where(ProgressPhoto.client_id == client_id))
    db.execute(delete(Period).where(Period.client_id == client_id))
    db.execute(delete(Plan).where(Plan.client_id == client_id))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id == client_id))
    db.execute(update(EmailLog).where(EmailLog.client_id == client_id).values(client_id=None))
    db.delete(client)

    delete_client_tree(client_id)
    # Registro anónimo de la baja: sin nombre, sin email (PARTE I)
    log_event(db, "client", client_id, "client_deleted", {"anonymous": True})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------- documentos del cliente (anamnesis) ----
# El coach sube aquí la anamnesis oficial (PDF) rellenada por el cliente y la
# conserva asociada a su ficha. Camí A: el PDF es la anamnesis; el coach pasa
# luego los datos clave a la pestaña editable y genera el plan.

def _client_or_404_docs(db: Session, client_id: int) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return c


@router.post("/{client_id}/documents")
def upload_client_document(
    client_id: int,
    file: UploadFile = File(..., description="PDF de la anamnesis rellenada"),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un documento (PDF) y lo asocia al cliente."""
    _client_or_404_docs(db, client_id)
    # Una sola anamnesis por cliente: borrar las anteriores antes de guardar
    from app.services.storage import client_dir
    folder = client_dir(client_id, "documents")
    for old in folder.iterdir():
        if old.is_file() and old.suffix.lower() == ".pdf":
            try:
                old.unlink()
            except Exception:
                pass
    try:
        rel = save_document(client_id, file.file.read(), file.filename or "anamnesis.pdf")
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "client", client_id, "document_uploaded", {"path": rel})
    db.commit()
    name = rel.rsplit("/", 1)[-1]

    # Tras subir, intentar leer la anamnesis con IA y pre-rellenar la ficha.
    # Si la lectura falla, la subida sigue siendo válida (no rompe el proceso):
    # el coach podrá pulsar "Leer con IA" o rellenar a mano.
    read_ok = False
    read_error = None
    try:
        _do_read_anamnesis(client_id, db)
        read_ok = True
    except HTTPException as exc:
        read_error = exc.detail if isinstance(exc.detail, str) else (
            exc.detail.get("error") if isinstance(exc.detail, dict) else "Error al leer"
        )
    except Exception as exc:  # nunca dejar caer la subida por un fallo de lectura
        read_error = str(exc)

    return {"name": name, "rel_path": rel, "read_ok": read_ok, "read_error": read_error}


@router.get("/{client_id}/documents")
def get_client_documents(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lista los documentos subidos del cliente."""
    _client_or_404_docs(db, client_id)
    return list_documents(client_id)


@router.get("/{client_id}/photos")
def list_client_photos(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Fotos de progreso del cliente (las que sube en el portal al cerrar)."""
    _client_or_404_docs(db, client_id)
    rows = db.scalars(
        select(ProgressPhoto).where(ProgressPhoto.client_id == client_id)
        .order_by(ProgressPhoto.taken_at.desc())
    )
    return [
        {"id": p.id, "kind": p.kind, "period_id": p.period_id, "taken_at": p.taken_at.isoformat()}
        for p in rows
    ]


@router.get("/{client_id}/photos/{photo_id}")
def get_client_photo(client_id: int, photo_id: int, db: Session = Depends(get_db)):
    """Sirve una foto de progreso (requiere JWT del coach)."""
    p = db.get(ProgressPhoto, photo_id)
    if not p or p.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto no encontrada")
    path = abs_path(p.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    ext = path.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "application/octet-stream")
    return Response(
        content=path.read_bytes(), media_type=media,
        headers={"Content-Disposition": f'inline; filename="foto_{photo_id}{ext}"'},
    )


@router.get("/{client_id}/documents/{name}")
def download_client_document(client_id: int, name: str, db: Session = Depends(get_db)):
    """Descarga un documento concreto del cliente (PDF)."""
    _client_or_404_docs(db, client_id)
    # Evita traversal: solo nombres simples dentro de la carpeta del cliente
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nombre no válido")
    path = abs_path(f"clients/{client_id}/documents/{name}")
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


# ------------------------------------------- generación de plan con IA (D/F) ----
# Pieza central: a partir de los datos estructurados de la anamnesis del cliente,
# calcula métricas (BMR/TDEE/objetivo), filtra la biblioteca de ejercicios y pide
# a la IA el plan mensual (núcleo + comidas + educativo), bajo guardrails. Lo
# guarda como borrador para que el coach lo revise, publique y descargue.

# Campos estructurados imprescindibles para poder generar
_REQUIRED_FIELDS = {
    "sex": "Sexo", "birth_date": "Fecha de nacimiento", "height_cm": "Altura",
    "start_weight_kg": "Peso inicial", "goal_type": "Objetivo", "level": "Nivel",
    "training_days": "Días de entrenamiento", "session_max_min": "Duración de sesión",
    "training_place": "Dónde entrena", "diet_mode": "Modo de dieta",
    "meals_per_day": "Comidas al día",
}


@router.post("/{client_id}/generate-plan")
def generate_client_plan(
    client_id: int,
    month_index: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    """Genera (con IA real) el plan mensual del cliente y lo guarda como borrador."""
    from datetime import date

    from app.models import Exercise, Plan
    from app.services.ai.client import AIClient
    from app.services.ai.generator import (
        ClientContext,
        PlanGenerationError,
        generate_monthly_plan,
    )
    from app.services.guardrails import filter_exercises_for_client
    from app.services.metrics import age_from_birth, energy_targets

    client = _client_or_404_docs(db, client_id)

    # 1) Validar que la anamnesis estructurada está completa
    missing = []
    for field, label in _REQUIRED_FIELDS.items():
        if getattr(client, field, None) in (None, "", []):
            missing.append(label)
    if not client.meal_schedule:
        missing.append("Horario de comidas")
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Faltan datos en la anamnesis para generar el plan.",
                "missing": missing,
            },
        )

    # 2) Métricas calculadas por el backend (la IA nunca calcula)
    age = age_from_birth(client.birth_date, date.today())
    et = energy_targets(
        sex=client.sex, weight_kg=client.start_weight_kg, height_cm=client.height_cm,
        age=age, goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct,
    )

    # 3) Biblioteca de ejercicios filtrada (solo aptos para este cliente)
    all_ex = db.scalars(select(Exercise)).all()
    ex_dicts = [{
        "id": e.id, "canonical_name": e.canonical_name, "name": e.canonical_name,
        "movement_pattern": e.movement_pattern,
        "muscle_primary": e.muscle_primary, "muscle_secondary": e.muscle_secondary or [],
        "equipment": e.equipment or [], "level_min": e.level_min,
        "contraindications": e.contraindications or [], "archived": e.archived,
    } for e in all_ex]
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
    # En gimnasio se asume equipamiento estándar completo: no se restringe por
    # equipo (el cliente no tiene por qué listar banco, rack, etc.). En casa o
    # exterior sí se respeta el material declarado.
    equip = set() if client.training_place == "gym" else set(client.equipment or [])
    library = filter_exercises_for_client(
        ex_dicts,
        client_contraindications=set(),
        excluded_ids=set(client.excluded_exercise_ids or []),
        equipment_available=equip,
        level_max=level_map.get(client.level, 2),
        training_place=client.training_place,
    )
    if not library:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No hay ejercicios disponibles con las restricciones del cliente.",
        )

    # Análisis cualitativo guardado al leer la anamnesis con IA (si existe)
    deep_analysis = None
    try:
        import json as _json
        ap = _anamnesis_analysis_path(client_id)
        if ap.exists():
            saved = _json.loads(ap.read_text(encoding="utf-8"))
            deep_analysis = saved.get("deep_analysis") or saved.get("injuries_notes")
    except Exception:
        deep_analysis = None

    # 4) Construir el contexto y pedir el plan a la IA
    ctx = ClientContext(
        sex=client.sex, age=age, height_cm=client.height_cm,
        weight_kg=client.start_weight_kg, goal_type=client.goal_type,
        level=client.level, training_days=client.training_days,
        session_max_min=client.session_max_min, training_place=client.training_place,
        diet_mode=client.diet_mode, meals_per_day=client.meals_per_day,
        meal_schedule=client.meal_schedule or [],
        food_allergies=client.food_allergies or [],
        food_dislikes=client.food_dislikes or [],
        food_likes=client.food_likes or [],
        contraindications=set(),
        body_fat_pct=client.body_fat_pct,
        bmr=et.bmr, tdee=et.tdee, target_kcal=et.target_kcal, energy_method=et.method,
        exercise_library=library,
        deep_analysis=deep_analysis,
    )
    try:
        generated = generate_monthly_plan(ctx, AIClient())
    except PlanGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no devolvió un plan válido.", "error": str(exc)},
        ) from exc

    nutrition, training, education, flags = generated.to_persistable()

    # 5) Persistir como borrador (nueva versión del mes)
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    plan = Plan(
        client_id=client_id, month_index=month_index, version=version, status="draft",
        nutrition_json=nutrition, training_json=training, education_json=education,
        guardrail_flags=flags, generated_by="ai",
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_generated_ai", {
        "client_id": client_id, "version": version, "flags": flags,
    })
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": flags or [],
        "nutrition": nutrition, "training": training, "education": education,
    }


# ------------------------------------------- leer anamnesis PDF con IA (extracción) ----
# La IA lee el PDF subido, extrae los datos estructurados + análisis en
# profundidad, y pre-rellena la ficha del cliente. El coach revisa antes de
# generar. El análisis cualitativo se guarda como sidecar para enriquecer el plan.

def _anamnesis_analysis_path(client_id: int):
    from app.services.storage import client_dir
    return client_dir(client_id, "documents") / "_anamnesis_analysis.json"


def _do_read_anamnesis(client_id: int, db: Session) -> dict:
    """Lee el PDF más reciente del cliente con IA y pre-rellena su ficha.
    Reutilizado por la subida (automático) y por el botón 'Leer con IA'."""
    import json as _json

    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.extraction import extract_anamnesis_from_pdf

    client = _client_or_404_docs(db, client_id)
    docs = list_documents(client_id)
    if not docs:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Sube primero la anamnesis (PDF) antes de leerla con IA.",
        )
    pdf_bytes = abs_path(docs[0]["rel_path"]).read_bytes()
    try:
        extracted = extract_anamnesis_from_pdf(pdf_bytes, AIClient())
    except AIGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no pudo leer la anamnesis.", "error": str(exc)},
        ) from exc

    data = extracted.model_dump()
    for f in [
        "sex", "birth_date", "height_cm", "start_weight_kg", "body_fat_pct",
        "goal_type", "goal_weight_kg", "level", "training_days", "session_max_min",
        "training_place", "equipment", "diet_mode", "meals_per_day", "food_likes",
        "food_dislikes", "food_allergies", "injuries_notes", "medical_notes",
        "medication_notes", "current_supplements", "sport_history", "lifestyle_notes",
    ]:
        val = data.get(f)
        if val not in (None, [], ""):
            setattr(client, f, val)
    if data.get("meal_schedule"):
        client.meal_schedule = data["meal_schedule"]
    db.flush()
    log_event(db, "client", client_id, "anamnesis_read_ai", {"source": docs[0]["name"]})
    db.commit()
    try:
        _anamnesis_analysis_path(client_id).write_text(
            _json.dumps({
                "deep_analysis": data.get("deep_analysis"),
                "injuries_notes": data.get("injuries_notes"),
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass
    return data


@router.post("/{client_id}/read-anamnesis")
def read_anamnesis_with_ai(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Lee el PDF más reciente del cliente con IA y pre-rellena su ficha."""
    data = _do_read_anamnesis(client_id, db)
    return {
        "extracted": data,
        "deep_analysis": data.get("deep_analysis"),
        "message": "Anamnesis leída. Revisa los datos antes de generar el plan.",
    }

```


## `backend/app/routers/exercises.py`

```python
"""Biblioteca de ejercicios (F.3): filtros, alta de personalizados, edición
(video_url incluido) y archivado sin romper el historial."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Exercise
from app.schemas.entities import ExerciseIn, ExerciseOut, ExerciseUpdate
from app.services.audit import log_event

router = APIRouter(
    prefix="/api/exercises", tags=["exercises"], dependencies=[Depends(get_current_user)]
)


def _get_or_404(db: Session, exercise_id: int) -> Exercise:
    ex = db.get(Exercise, exercise_id)
    if not ex:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ejercicio no encontrado")
    return ex


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    db: Session = Depends(get_db),
    pattern: str | None = Query(default=None, description="movement_pattern exacto"),
    muscle: str | None = Query(default=None, description="músculo primario"),
    equipment: str | None = Query(default=None, description="requiere este equipamiento"),
    level_max: int | None = Query(default=None, ge=1, le=3, description="nivel mínimo ≤"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/aliases"),
    include_archived: bool = Query(default=False),
) -> list[ExerciseOut]:
    stmt = select(Exercise).order_by(Exercise.muscle_primary, Exercise.canonical_name)
    if not include_archived:
        stmt = stmt.where(Exercise.archived.is_(False))
    if pattern:
        stmt = stmt.where(Exercise.movement_pattern == pattern)
    if muscle:
        stmt = stmt.where(Exercise.muscle_primary == muscle)
    if equipment:
        stmt = stmt.where(Exercise.equipment.any(equipment))
    if level_max:
        stmt = stmt.where(Exercise.level_min <= level_max)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            Exercise.canonical_name.ilike(like) | Exercise.aliases.any(q.strip())
        )
    return [ExerciseOut.model_validate(e) for e in db.scalars(stmt)]


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    return ExerciseOut.model_validate(_get_or_404(db, exercise_id))


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(body: ExerciseIn, db: Session = Depends(get_db)) -> ExerciseOut:
    if db.scalar(select(Exercise).where(Exercise.canonical_name == body.canonical_name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un ejercicio con ese nombre")
    ex = Exercise(**body.model_dump())
    db.add(ex)
    db.flush()
    log_event(db, "exercise", ex.id, "exercise_created", {"name": ex.canonical_name})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.patch("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, body: ExerciseUpdate, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(ex, field, value)
    if changes:
        log_event(db, "exercise", ex.id, "exercise_updated", {"fields": sorted(changes)})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/archive", response_model=ExerciseOut)
def archive_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = True
    log_event(db, "exercise", ex.id, "exercise_archived", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/restore", response_model=ExerciseOut)
def restore_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = False
    log_event(db, "exercise", ex.id, "exercise_restored", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)

```


## `backend/app/routers/plans.py`

```python
"""Gestión de planes y períodos por el coach (soporte de Fases 6–7).

Cierra el ciclo de vida para que el portal tenga datos reales:
- POST /api/clients/{id}/plans         crea un plan (borrador) con el contenido
                                       generado (núcleo + banco + educativo).
- POST /api/plans/{id}/publish         publica el plan → cliente pasa a active,
                                       email de bienvenida/nuevo plan (G.5).
- POST /api/clients/{id}/periods       abre un período sobre un plan publicado.
- GET  /api/clients/{id}/plans         lista de planes del cliente (para la app).
- GET  /api/clients/{id}/change-requests  cola de solicitudes de ajuste.

La generación con IA (Fase 3) produce el contenido; aquí se persiste y publica.
El endpoint de creación acepta el contenido ya ensamblado para no acoplar la
publicación a una llamada de IA en vivo (que puede orquestarse aparte).
"""


from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ChangeRequest, Client, FeedbackDoc, Period, Plan
from app.schemas.entities import ChangeRequestOut, PeriodCreateIn
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config

router = APIRouter(tags=["plans"], dependencies=[Depends(get_current_user)])


class PlanCreateIn(BaseModel):
    month_index: int = 1
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None
    guardrail_flags: list[str] | None = None
    generated_by: str | None = None


class PlanOut(BaseModel):
    id: int
    client_id: int
    month_index: int
    version: int
    status: str
    nutrition_json: dict | None
    training_json: dict | None
    education_json: dict | None
    guardrail_flags: list[str] | None

    model_config = {"from_attributes": True}


def _client_or_404(db: Session, client_id: int) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return c


@router.post("/api/clients/{client_id}/plans", response_model=PlanOut,
             status_code=status.HTTP_201_CREATED)
def create_plan(client_id: int, body: PlanCreateIn, db: Session = Depends(get_db)) -> PlanOut:
    _client_or_404(db, client_id)
    # versión siguiente para ese mes
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == body.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    plan = Plan(
        client_id=client_id, month_index=body.month_index, version=version,
        status="draft", nutrition_json=body.nutrition_json,
        training_json=body.training_json, education_json=body.education_json,
        guardrail_flags=body.guardrail_flags, generated_by=body.generated_by,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_created", {"client_id": client_id, "version": version})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


class PlanUpdateIn(BaseModel):
    """Edición manual del plan por el coach (revisión antes de enviar)."""
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None


@router.patch("/api/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, body: PlanUpdateIn, db: Session = Depends(get_db)) -> PlanOut:
    """Guarda los cambios manuales del coach en el plan (núcleo/comidas/educativo).

    No re-ejecuta los guardrails: son ediciones del coach, que revisa bajo su
    criterio (el principio de seguridad aplica a lo que genera la IA, no a la
    corrección manual). El plan editado queda persistido y descargable.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            setattr(plan, field, value)
    log_event(db, "plan", plan.id, "plan_edited", {"fields": list(changes.keys())})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.get("/api/clients/{client_id}/plans", response_model=list[PlanOut])
def list_plans(client_id: int, db: Session = Depends(get_db)) -> list[PlanOut]:
    _client_or_404(db, client_id)
    plans = db.scalars(
        select(Plan).where(Plan.client_id == client_id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ).all()
    return [PlanOut.model_validate(p) for p in plans]


@router.post("/api/plans/{plan_id}/publish", response_model=PlanOut)
def publish_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    # Las versiones anteriores del mismo mes quedan supersedidas
    for older in db.scalars(
        select(Plan).where(
            Plan.client_id == plan.client_id, Plan.month_index == plan.month_index,
            Plan.status == "published",
        )
    ):
        older.status = "superseded"

    plan.status = "published"
    is_new_month = plan.month_index > 1
    if client.status == "onboarding":
        client.status = "active"

    log_event(db, "plan", plan.id, "plan_published", {"month_index": plan.month_index})

    # Email de bienvenida / nuevo plan (G.5)
    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    subject, html = tpl.plan_published(
        brand, client.full_name.split()[0], portal_url, is_new_month
    )
    EmailService(db).send(to=client.email, subject=subject, html=html,
                          kind="plan_published", client=client)

    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/api/clients/{client_id}/periods", response_model=dict,
             status_code=status.HTTP_201_CREATED)
def create_period(client_id: int, body: PeriodCreateIn, db: Session = Depends(get_db)) -> dict:
    _client_or_404(db, client_id)
    plan = db.get(Plan, body.plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado para este cliente")
    if plan.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "El plan debe estar publicado")

    last = db.scalar(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    period_index = (last.period_index + 1) if last else 1
    period = Period(
        client_id=client_id, plan_id=plan.id, period_index=period_index,
        starts_on=body.starts_on, ends_on=body.starts_on + timedelta(days=body.days - 1),
        status="open",
    )
    db.add(period)
    db.flush()
    log_event(db, "period", period.id, "period_opened", {"index": period_index})
    db.commit()
    return {"period_id": period.id, "period_index": period_index,
            "starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat()}


@router.get("/api/clients/{client_id}/change-requests", response_model=list[ChangeRequestOut])
def list_change_requests(client_id: int, db: Session = Depends(get_db)) -> list[ChangeRequestOut]:
    _client_or_404(db, client_id)
    crs = db.scalars(
        select(ChangeRequest).where(ChangeRequest.client_id == client_id)
        .order_by(ChangeRequest.created_at.desc())
    ).all()
    return [ChangeRequestOut.model_validate(c) for c in crs]


@router.post("/api/change-requests/{cr_id}/resolve", response_model=ChangeRequestOut)
def resolve_change_request(cr_id: int, db: Session = Depends(get_db)) -> ChangeRequestOut:
    from datetime import datetime, timezone

    cr = db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    cr.status = "resolved"
    cr.resolved_at = datetime.now(timezone.utc)
    log_event(db, "client", cr.client_id, "change_request_resolved", {"id": cr.id})
    db.commit()
    db.refresh(cr)
    return ChangeRequestOut.model_validate(cr)


# ------------------------------------------------------- feedback (cierre → informe) ----

class PeriodOut(BaseModel):
    id: int
    plan_id: int | None = None
    period_index: int
    starts_on: date
    ends_on: date
    status: str
    closing_weight_kg: float | None = None
    closing_rating: int | None = None
    closing_hardest: str | None = None
    closing_questions: str | None = None
    closing_waist_cm: float | None = None
    closing_hip_cm: float | None = None
    closing_arm_cm: float | None = None
    closing_thigh_cm: float | None = None
    feedback_id: int | None = None

    model_config = {"from_attributes": True}


@router.get("/api/clients/{client_id}/periods", response_model=list[PeriodOut])
def list_periods(client_id: int, db: Session = Depends(get_db)) -> list[PeriodOut]:
    """Períodos del cliente (con datos de cierre) + si ya tienen feedback."""
    _client_or_404(db, client_id)
    periods = db.scalars(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc())
    ).all()
    out = []
    for p in periods:
        po = PeriodOut.model_validate(p)
        fb = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == p.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
        po.feedback_id = fb.id if fb else None
        out.append(po)
    return out


@router.get("/api/periods/{period_id}/metrics")
def period_metrics(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Resumen de métricas del período (sin IA): peso, adherencia, fuerza, objetivo."""
    from app.services.feedback_service import FeedbackError, compute_period_summary

    if not db.get(Period, period_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        return compute_period_summary(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/api/periods/{period_id}/feedback")
def generate_feedback(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Genera (con IA) el feedback del período cerrado y lo persiste."""
    from app.services.feedback_service import FeedbackError, build_period_feedback

    period = db.get(Period, period_id)
    if not period:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        fb = build_period_feedback(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc)},
        ) from exc
    return {
        "feedback_id": fb.id, "period_id": period_id,
        "kind": fb.kind, "content": fb.content_json,
    }


@router.get("/api/feedback/{doc_id}")
def get_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Contenido del feedback (para mostrarlo en la pestaña del coach)."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    return {
        "id": fb.id, "period_id": fb.period_id, "kind": fb.kind,
        "content": fb.content_json,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
    }


@router.post("/api/feedback/{doc_id}/send")
def send_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía el feedback al cliente: lo hace visible en su portal (Progreso),
    avanza el ciclo (review_pending → active, cierra la notificación) y le avisa
    por email. Hasta este punto el feedback es un borrador que solo ve el coach."""
    from datetime import datetime, timezone

    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    fb.sent_at = datetime.now(timezone.utc)

    period = db.get(Period, fb.period_id)
    client = db.get(Client, period.client_id) if period else None
    if client and client.status == "review_pending":
        client.status = "active"  # cerrado el feedback, arranca el siguiente ciclo

    if client:
        log_event(db, "client", client.id, "feedback_sent", {"feedback_id": fb.id})
        # Aviso al cliente (si los emails están activos)
        try:
            brand = brand_from_config(db)
            portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
            subject, html = tpl.feedback_ready(brand, client.full_name.split()[0], portal_url)
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind="feedback_ready", client=client)
        except Exception:
            pass
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat()}


@router.get("/api/feedback/{doc_id}/document")
def download_feedback_document(doc_id: int, db: Session = Depends(get_db)):
    """Descarga el documento Word del feedback."""
    from fastapi import Response

    from app.services.storage import abs_path

    fb = db.get(FeedbackDoc, doc_id)
    if not fb or not fb.docx_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    path = abs_path(fb.docx_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    period = db.get(Period, fb.period_id)
    idx = period.period_index if period else fb.id
    return Response(
        content=path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="feedback_periodo{idx}.docx"'},
    )


# ------------------------------------------- documentos Word del plan (Fase 7) ----

def _doc_brand(db: Session):
    from app.models import BrandConfig
    from app.services.docs.word_base import DocBrand

    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        from app.services.storage import abs_path

        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


@router.get("/api/plans/{plan_id}/document")
def download_plan_document(plan_id: int, db: Session = Depends(get_db)):
    """Genera y descarga el documento Word del plan (H.3)."""
    from fastapi import Response

    from app.services.docs.plan_doc import generate_plan_doc

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    data = generate_plan_doc(
        brand=_doc_brand(db),
        client_name=client.full_name,
        month_index=plan.month_index,
        goal_type=client.goal_type,
        diet_mode=client.diet_mode,
        nutrition=plan.nutrition_json or {},
        training=plan.training_json or {},
        education=plan.education_json or {},
    )
    import unicodedata

    ascii_name = unicodedata.normalize("NFKD", client.full_name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_").lower() or "cliente"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="plan_{safe}_mes{plan.month_index}.docx"'},
    )


# ----------------------------------------------- swap de ejercicios (Fase 8, F.5) ----

class SwapProposeOut(BaseModel):
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int


class SwapApplyIn(BaseModel):
    session_index: int
    old_exercise_id: int
    new_exercise_id: int
    permanent: bool = False
    reason: str = ""


@router.get("/api/clients/{client_id}/plans/{plan_id}/swap-options/{exercise_id}",
            response_model=list[SwapProposeOut])
def swap_options(client_id: int, plan_id: int, exercise_id: int,
                 db: Session = Depends(get_db)) -> list[SwapProposeOut]:
    """Propone 2–3 alternativas válidas para sustituir un ejercicio (F.5.1)."""
    from app.services.swap import propose_alternatives

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    alts = propose_alternatives(db, client, exercise_id)
    return [SwapProposeOut(**a.__dict__) for a in alts]


@router.post("/api/clients/{client_id}/plans/{plan_id}/swap", response_model=dict)
def swap_apply(client_id: int, plan_id: int, body: SwapApplyIn,
               db: Session = Depends(get_db)) -> dict:
    """Aplica el swap creando una nueva versión del plan (borrador) (F.5.2–4)."""
    from app.services.swap import apply_swap

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    try:
        result = apply_swap(
            db, client=client, plan=plan, session_index=body.session_index,
            old_exercise_id=body.old_exercise_id, new_exercise_id=body.new_exercise_id,
            permanent=body.permanent, reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {
        "new_plan_id": result.new_plan_id, "new_version": result.new_version,
        "group_volume_after": result.group_volume_after,
        "guardrail_flags": result.guardrail_flags,
    }


# ------------------------------------------- plantilla de anamnesis (PDF oficial) ----

@router.get("/api/anamnesis-template")
def download_anamnesis_template():
    """Descarga la plantilla oficial de anamnesis (PDF en blanco) para que el
    coach la envíe por correo al cliente."""
    from pathlib import Path

    from fastapi import Response

    path = Path(__file__).resolve().parent.parent / "assets" / "anamnesis_template.pdf"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plantilla no encontrada")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="anamnesis.pdf"'},
    )

```


## `backend/app/routers/portal_public.py`

```python
"""Endpoints PÚBLICOS del portal (sin JWT — autenticación por token firmado).

Fase 2: el flujo de alta completo del cliente.
  GET  /api/p/{token}              → estado del wizard + marca para tematizar
  POST /api/p/{token}/anamnesis    → envío del formulario (consentimiento RGPD
                                     obligatorio → genera y archiva el PDF)
  POST /api/p/{token}/anamnesis/photos → fotos corporales iniciales (1–4)

Decisión declarada (A.1.7): las fotos se suben DESPUÉS de aceptar el
consentimiento (datos de salud — primero la base legal, luego el dato).
El mínimo de 1 foto lo exige el wizard y, en Fase 3, la generación del plan.
"""



from datetime import datetime, timezone
from typing import Annotated, List
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_client_by_token
from app.models import (
    BrandConfig,
    ChangeRequest,
    Client,
    DailyLog,
    FeedbackDoc,
    Period,
    ProgressPhoto,
    WorkoutLog,
)
from app.schemas.entities import (
    AnamnesisStateOut,
    AnamnesisSubmit,
    ChangeRequestIn,
    ChangeRequestOut,
    DailyLogUpsert,
    FeedbackDocOut,
    PeriodCloseIn,
    PhotoOut,
    PortalBrand,
    PortalPlanOut,
    PortalState,
    TodayView,
)
from app.services import portal as portal_svc
from app.services.audit import log_event
from app.services.consent_pdf import generate_consent_pdf
from app.services.email_service import EmailService, brand_from_config
from app.services import email_templates as tpl
from app.services.storage import PhotoValidationError, save_photo

router = APIRouter(prefix="/api/p", tags=["portal-public"])
limiter = Limiter(key_func=get_remote_address)

MAX_INITIAL_PHOTOS = 4


def _photos_count(db: Session, client_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ProgressPhoto)
            .where(ProgressPhoto.client_id == client_id, ProgressPhoto.period_id.is_(None))
        )
        or 0
    )


def _state(db: Session, client: Client) -> AnamnesisStateOut:
    brand = db.scalar(select(BrandConfig).limit(1)) or BrandConfig()
    return AnamnesisStateOut(
        first_name=client.full_name.split()[0],
        anamnesis_done=client.consent_signed_at is not None,
        photos_count=_photos_count(db, client.id),
        brand_name=brand.name,
        color_primary=brand.color_primary,
        color_bg=brand.color_bg,
        font_family=brand.font_family,
        portal_theme=brand.portal_theme,
    )


@router.get("/{token}", response_model=AnamnesisStateOut)
@limiter.limit("60/minute")
def portal_state(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> AnamnesisStateOut:
    return _state(db, client)


@router.post("/{token}/anamnesis", response_model=AnamnesisStateOut)
@limiter.limit("10/minute")
def submit_anamnesis(
    request: Request,
    body: AnamnesisSubmit,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> AnamnesisStateOut:
    """Recibe el wizard completo. Idempotencia: una vez firmada, 409 (las
    correcciones posteriores las hace el coach con audit trail)."""
    if client.consent_signed_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La anamnesis ya fue enviada; contacta con tu coach para cambios",
        )

    data = body.model_dump()
    data.pop("consent_accepted")
    priority_zones = data.pop("priority_zones", None)
    if priority_zones:
        prefix = f"[Zonas a priorizar] {priority_zones}"
        data["lifestyle_notes"] = (
            f"{prefix}\n{data['lifestyle_notes']}" if data.get("lifestyle_notes") else prefix
        )
    data["current_weight_kg"] = data["start_weight_kg"]

    for field, value in data.items():
        setattr(client, field, value)
    client.consent_signed_at = datetime.now(timezone.utc)

    brand = db.scalar(select(BrandConfig).limit(1)) or BrandConfig()
    pdf_rel = generate_consent_pdf(
        client.id, client.full_name, client.email, brand.name, client.consent_signed_at
    )
    log_event(db, "client", client.id, "anamnesis_submitted", {"diet_mode": client.diet_mode})
    log_event(db, "client", client.id, "consent_pdf_generated", {"path": pdf_rel})
    db.commit()
    db.refresh(client)
    return _state(db, client)


@router.post("/{token}/anamnesis/photos")
@limiter.limit("20/minute")
def upload_initial_photos(
    request: Request,
files: Annotated[List[UploadFile], File(description="1–4 fotos corporales")],    kind: str = Query(default="front", pattern="^(front|side|back|detail)$"),
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    """Fotos iniciales (línea base, period_id NULL). Requiere consentimiento."""
    if client.consent_signed_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Completa primero el formulario y acepta el consentimiento",
        )
    existing = _photos_count(db, client.id)
    if existing + len(files) > MAX_INITIAL_PHOTOS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Máximo {MAX_INITIAL_PHOTOS} fotos iniciales (ya hay {existing})",
        )

    created: list[ProgressPhoto] = []
    for f in files:
        try:
            rel = save_photo(client.id, f.file.read())
        except PhotoValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        photo = ProgressPhoto(client_id=client.id, period_id=None, kind=kind, file_path=rel)
        db.add(photo)
        created.append(photo)

    db.flush()
    log_event(db, "client", client.id, "initial_photos_uploaded", {"count": len(created)})
    db.commit()
    for p in created:
        db.refresh(p)
    return [PhotoOut.model_validate(p) for p in created]


# ============================================================ portal (Fase 6) ====
# Vistas del cliente: estado, HOY, plan, diario, cierre, feedback, ajuste.
# Todas autenticadas por el token firmado (get_client_by_token).

from datetime import date as _date  # noqa: E402


@router.get("/{token}/state", response_model=PortalState)
@limiter.limit("120/minute")
def portal_state_full(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> PortalState:
    """Estado completo para arrancar el portal: período activo y marca."""
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    return PortalState(
        first_name=client.full_name.split()[0],
        status=client.status,
        diet_mode=client.diet_mode,
        has_plan=plan is not None,
        period=portal_svc.period_info(period, _date.today()),
        brand=PortalBrand(**portal_svc.brand_payload(db)),
    )


@router.get("/{token}/today", response_model=TodayView)
@limiter.limit("120/minute")
def portal_today(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> TodayView:
    """Vista HOY: qué como y qué entreno hoy. Lectura en <30 s (G.4)."""
    return TodayView(**portal_svc.build_today_view(db, client, _date.today()))


@router.get("/{token}/training", response_model=dict)
@limiter.limit("120/minute")
def portal_training(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Todas las sesiones del plan (con nombres de ejercicio) para el selector
    de la pantalla de registro de entreno."""
    return {"sessions": portal_svc.build_training_sessions(db, client)}


@router.get("/{token}/plan", response_model=PortalPlanOut)
@limiter.limit("60/minute")
def portal_plan(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> PortalPlanOut:
    """Plan completo navegable (nutrición + entrenamiento + educativo)."""
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no tienes un plan publicado")
    return PortalPlanOut(
        month_index=plan.month_index,
        nutrition=plan.nutrition_json,
        training=plan.training_json,
        education=plan.education_json,
        diet_mode=client.diet_mode,
    )


@router.put("/{token}/diary", response_model=dict)
@limiter.limit("120/minute")
def portal_diary_upsert(
    request: Request,
    body: DailyLogUpsert,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Registro diario con autosave (upsert por fecha). Autocompletado desde el
    plan en el frontend; aquí solo se persiste lo que el cliente confirma."""
    period = portal_svc.active_period(db, client.id)
    if period is None or period.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período abierto")

    log = db.scalar(
        select(DailyLog).where(
            DailyLog.period_id == period.id, DailyLog.log_date == body.log_date
        )
    )
    if log is None:
        log = DailyLog(period_id=period.id, log_date=body.log_date)
        db.add(log)
        db.flush()

    # Upsert PARCIAL: solo se tocan los campos que el cliente envía. Así un
    # guardado de comidas/diario NO borra las series, ni viceversa (autosaves
    # independientes desde distintas pantallas del portal).
    data = body.model_dump(exclude_unset=True)
    for field in (
        "weight_kg", "sleep_hours", "diet_adherence", "diet_notes",
        "energy_1_5", "mood_1_5", "fatigue_1_5", "free_notes",
        "chosen_options_json", "option_feedback_json",
    ):
        if field in data:
            setattr(log, field, data[field])

    # Sets de entrenamiento: se reemplazan SOLO si vienen en la petición.
    if "workout_sets" in data:
        db.query(WorkoutLog).filter(WorkoutLog.daily_log_id == log.id).delete()
        for ws in body.workout_sets:
            db.add(WorkoutLog(
                daily_log_id=log.id, exercise_id=ws.exercise_id, set_number=ws.set_number,
                reps=ws.reps, weight_kg=ws.weight_kg, rpe=ws.rpe, notes=ws.notes,
            ))

    db.commit()
    return {"saved": True, "log_date": body.log_date.isoformat()}


@router.get("/{token}/diary/{log_date}", response_model=dict)
@limiter.limit("120/minute")
def portal_diary_get(
    request: Request,
    log_date: _date,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Recupera el registro de un día (para precargar el formulario)."""
    period = portal_svc.active_period(db, client.id)
    if period is None:
        return {"exists": False}
    log = db.scalar(
        select(DailyLog).where(
            DailyLog.period_id == period.id, DailyLog.log_date == log_date
        )
    )
    if log is None:
        return {"exists": False}
    sets = db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id == log.id)).all()
    return {
        "exists": True,
        "weight_kg": log.weight_kg, "sleep_hours": log.sleep_hours,
        "diet_adherence": log.diet_adherence, "diet_notes": log.diet_notes,
        "energy_1_5": log.energy_1_5, "mood_1_5": log.mood_1_5,
        "fatigue_1_5": log.fatigue_1_5, "free_notes": log.free_notes,
        "chosen_options_json": log.chosen_options_json,
        "workout_sets": [
            {"exercise_id": s.exercise_id, "set_number": s.set_number,
             "reps": s.reps, "weight_kg": s.weight_kg, "rpe": s.rpe}
            for s in sets
        ],
    }


@router.post("/{token}/close", response_model=dict)
@limiter.limit("20/minute")
def portal_close_period(
    request: Request,
    body: PeriodCloseIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Cierre del período (desde día 14). Dispara el pipeline en Fase 7;
    aquí persiste el cierre y pasa el cliente a awaiting→review."""
    period = portal_svc.active_period(db, client.id)
    if period is None or period.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período abierto")

    info = portal_svc.period_info(period, _date.today())
    if not info or not info["can_close"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El cierre estará disponible a partir del día 14 del período",
        )

    for field in (
        "closing_weight_kg", "closing_rating", "closing_hardest", "closing_questions",
        "closing_waist_cm", "closing_hip_cm", "closing_arm_cm", "closing_thigh_cm",
    ):
        setattr(period, field, getattr(body, field))
    period.status = "closed"

    # El cliente pasa a esperar la revisión del coach (review_pending)
    if client.status in ("active", "awaiting_feedback", "at_risk"):
        client.status = "review_pending"

    log_event(db, "client", client.id, "period_closed",
              {"period_index": period.period_index, "rating": body.closing_rating})
    db.commit()
    return {"closed": True, "period_index": period.period_index}


@router.post("/{token}/close/photos")
@limiter.limit("20/minute")
def portal_close_photos(
    request: Request,
 files: Annotated[List[UploadFile], File(description="hasta 4 fotos de cierre")],   kind: str = Query(default="front", pattern="^(front|side|back|detail)$"),
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    """Fotos del cierre (asociadas al período actual)."""
    period = portal_svc.active_period(db, client.id)
    if period is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período activo")

    existing = db.scalar(
        select(func.count()).select_from(ProgressPhoto)
        .where(ProgressPhoto.client_id == client.id, ProgressPhoto.period_id == period.id)
    ) or 0
    if existing + len(files) > 4:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Máximo 4 fotos por cierre (ya hay {existing})",
        )

    created: list[ProgressPhoto] = []
    for f in files:
        try:
            rel = save_photo(client.id, f.file.read())
        except PhotoValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        photo = ProgressPhoto(client_id=client.id, period_id=period.id, kind=kind, file_path=rel)
        db.add(photo)
        created.append(photo)
    db.flush()
    log_event(db, "client", client.id, "closing_photos_uploaded", {"count": len(created)})
    db.commit()
    for p in created:
        db.refresh(p)
    return [PhotoOut.model_validate(p) for p in created]


@router.get("/{token}/feedback", response_model=list[FeedbackDocOut])
@limiter.limit("60/minute")
def portal_feedback(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[FeedbackDocOut]:
    """Historial de feedbacks ENVIADOS del cliente (más reciente primero).

    Solo los que el coach ha enviado (sent_at). Los borradores en revisión no
    se muestran al cliente."""
    periods = db.scalars(select(Period.id).where(Period.client_id == client.id)).all()
    if not periods:
        return []
    docs = db.scalars(
        select(FeedbackDoc)
        .where(FeedbackDoc.period_id.in_(periods), FeedbackDoc.sent_at.isnot(None))
        .order_by(FeedbackDoc.id.desc())
    ).all()
    return [FeedbackDocOut.model_validate(d) for d in docs]


@router.post("/{token}/change-request", response_model=ChangeRequestOut)
@limiter.limit("10/minute")
def portal_change_request(
    request: Request,
    body: ChangeRequestIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> ChangeRequestOut:
    """'Solicitar ajuste': crea un change_request y alerta al coach por email."""
    cr = ChangeRequest(client_id=client.id, message=body.message.strip(), status="open")
    db.add(cr)
    db.flush()
    log_event(db, "client", client.id, "change_request_created", {"id": cr.id})

    # Alerta al coach (G.5)
    from app.config import settings

    coach_to = settings.smtp_from or settings.smtp_user
    if coach_to:
        brand = brand_from_config(db)
        subject, html = tpl.coach_change_request(
            brand, client.full_name, cr.message,
            f"{settings.public_base_url}/clientes/{client.id}",
        )
        EmailService(db).send(to=coach_to, subject=subject, html=html,
                              kind="coach_change_request", client=client)

    db.commit()
    db.refresh(cr)
    return ChangeRequestOut.model_validate(cr)

```


## `backend/app/schemas/__init__.py`

```python
from app.schemas import ai, entities  # noqa: F401

```


## `backend/app/schemas/ai.py`

```python
"""Schemas Pydantic de las salidas de IA — contratos C.2, C.3 y C.4.

Las 3 llamadas orquestadas devuelven JSON validado contra estos modelos:
  ① PlanCoreOutput   — núcleo del plan (nutrición estructural + entrenamiento)
  ② MealsOutput      — banco de comidas según diet_mode (flexible_7 | strict)
  ③ EducationOutput  — píldoras educativas, biomecánica por patrón y FAQ

La validación aritmética de macros (±5%) y los guardrails E.4/F.4 son del
backend (Fase 3); aquí se valida estructura, tipos y cardinalidades.
"""


from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================ llamada ① ====


class Macros(BaseModel):
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealSlotTarget(BaseModel):
    kcal: float = Field(gt=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealSlotDef(BaseModel):
    slot: int = Field(ge=1)
    name: str
    time: str  # "08:00"
    target: MealSlotTarget


class Supplement(BaseModel):
    name: str
    dose: str
    timing: str
    evidence_note: str = ""  # nota informativa; opcional para no tumbar el plan si la IA la omite


class NutritionCore(BaseModel):
    tdee_kcal: float = Field(gt=0)
    target_kcal: float = Field(gt=0)
    rationale: str
    macros: Macros
    meals: list[MealSlotDef] = Field(min_length=1)
    supplements: list[Supplement] = Field(default_factory=list)
    flexibility_rules: list[str] = Field(default_factory=list)
    refeed_or_break: str | None = None

    @model_validator(mode="after")
    def slots_unicos_y_ordenados(self) -> "NutritionCore":
        slots = [m.slot for m in self.meals]
        if len(set(slots)) != len(slots):
            raise ValueError("slots de comida duplicados")
        if slots != sorted(slots):
            raise ValueError("los slots deben venir ordenados")
        return self


class WeeklyProgressionWeek(BaseModel):
    week: int = Field(ge=1, le=4)
    intent: str  # Base | Progresión | Pico | Deload
    load_pct: float = Field(gt=0)
    rir_target: str
    volume_note: str


class PlannedExercise(BaseModel):
    exercise_id: int = Field(ge=1)  # SOLO ids de la biblioteca inyectada (F.3)
    sets: int = Field(ge=1, le=10)
    rep_range: str  # "6-8"
    rir: str  # "2" | "1-2"
    tempo: str | None = None
    rest_sec: int = Field(ge=15, le=600)
    start_weight_hint_kg: float | None = Field(default=None, ge=0)
    progression_rule: str
    technique_cue: str
    biomech_cue: str


class TrainingSession(BaseModel):
    day: str  # "Lunes"…
    name: str  # "Upper A"
    warmup: str
    exercises: list[PlannedExercise] = Field(min_length=1)
    cooldown: str


class CardioSession(BaseModel):
    type: Literal["liss", "hiit"]
    minutes: int = Field(ge=5, le=120)
    times_per_week: int = Field(ge=1, le=7)
    notes: str | None = None


class CardioPlan(BaseModel):
    daily_steps: int = Field(ge=0, le=30000)
    sessions: list[CardioSession] = Field(default_factory=list)


class TrainingCore(BaseModel):
    split_name: str
    split_rationale: str
    weekly_progression: list[WeeklyProgressionWeek]
    sessions: list[TrainingSession] = Field(min_length=1)
    cardio: CardioPlan
    deload_instructions: str

    @field_validator("weekly_progression")
    @classmethod
    def cuatro_semanas(cls, v: list[WeeklyProgressionWeek]) -> list[WeeklyProgressionWeek]:
        if [w.week for w in v] != [1, 2, 3, 4]:
            raise ValueError("weekly_progression debe cubrir exactamente las semanas 1-4")
        return v


class PlanCoreOutput(BaseModel):
    """Salida completa de la llamada ① (se persiste repartida en
    plans.nutrition_json / plans.training_json)."""

    nutrition: NutritionCore
    training: TrainingCore


# ============================================================ llamada ② ====


class Ingredient(BaseModel):
    food: str
    grams: float = Field(gt=0)  # SIEMPRE en crudo (E.3)
    household: str  # medida casera obligatoria


class OptionMacros(BaseModel):
    kcal: float = Field(gt=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class MealOption(BaseModel):
    key: Literal["A", "B", "C", "D", "E", "F", "G"] | None = None  # None en modo strict
    title: str
    ingredients: list[Ingredient] = Field(min_length=1)
    prep: str
    prep_minutes: int = Field(ge=0, le=120)
    macros: OptionMacros
    tags: list[str] = Field(default_factory=list)


class FlexibleSlot(BaseModel):
    slot: int = Field(ge=1)
    options: list[MealOption]

    @field_validator("options")
    @classmethod
    def exactamente_siete(cls, v: list[MealOption]) -> list[MealOption]:
        if len(v) != 7:
            raise ValueError("cada slot debe tener exactamente 7 opciones (A-G)")
        keys = [o.key for o in v]
        if keys != ["A", "B", "C", "D", "E", "F", "G"]:
            raise ValueError("las opciones deben llevar keys A-G en orden")
        return v


class MealsFlexibleOutput(BaseModel):
    mode: Literal["flexible_7"]
    slots: list[FlexibleSlot] = Field(min_length=1)


DAY_NAMES = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class StrictDayMeal(BaseModel):
    slot: int = Field(ge=1)
    dish: MealOption  # key = None


class StrictDay(BaseModel):
    day: str  # lunes…domingo (slug sin tildes)
    meals: list[StrictDayMeal] = Field(min_length=1)


class MealsStrictOutput(BaseModel):
    mode: Literal["strict"]
    days: list[StrictDay]
    free_meal_guidelines: str | None = None  # solo si strict_free_meal_enabled

    @field_validator("days")
    @classmethod
    def semana_completa(cls, v: list[StrictDay]) -> list[StrictDay]:
        if [d.day for d in v] != DAY_NAMES:
            raise ValueError(f"days debe ser exactamente {DAY_NAMES} en orden")
        return v

    @model_validator(mode="after")
    def mismos_slots_cada_dia(self) -> "MealsStrictOutput":
        slot_sets = {tuple(sorted(m.slot for m in d.meals)) for d in self.days}
        if len(slot_sets) != 1:
            raise ValueError("todos los días deben cubrir los mismos slots de comida")
        return self


MealsOutput = Annotated[
    Union[MealsFlexibleOutput, MealsStrictOutput], Field(discriminator="mode")
]


# ============================================================ llamada ③ ====


class EducationPill(BaseModel):
    topic: str
    for_client: str  # 4-6 líneas, lenguaje llano


class BiomechPattern(BaseModel):
    pattern: str  # "Empuje horizontal", "Bisagra de cadera"…
    cues: list[str] = Field(min_length=1)
    why: str


class FaqItem(BaseModel):
    q: str
    a: str


class EducationOutput(BaseModel):
    pills: list[EducationPill] = Field(min_length=3, max_length=5)
    biomech_by_pattern: list[BiomechPattern] = Field(min_length=1)
    faq: list[FaqItem] = Field(default_factory=list)

```


## `backend/app/schemas/entities.py`

```python
"""Schemas Pydantic de entidades para la API (request/response).

Espejados manualmente en frontend/src/types.ts (regla A.1.5).
"""


from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Literales compartidos
Sex = Literal["male", "female"]
GoalType = Literal["fat_loss", "muscle_gain", "recomp"]
Level = Literal["beginner", "intermediate", "advanced"]
TrainingPlace = Literal["gym", "home", "outdoor"]
DietMode = Literal["flexible_7", "strict"]
ClientStatus = Literal[
    "onboarding", "active", "awaiting_feedback", "at_risk", "review_pending", "inactive"
]
DietAdherence = Literal["yes", "partial", "no"]
PhotoKind = Literal["front", "side", "back", "detail"]
Theme = Literal["light", "dark"]


# ----------------------------------------------------------------- auth ----
class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# -------------------------------------------------------------- clients ----
class MealScheduleItem(BaseModel):
    slot: int = Field(ge=1)
    name: str  # "Desayuno"
    time: str  # "08:00"


class ClientCreate(BaseModel):
    """Alta mínima por el coach; el resto llega con la anamnesis del cliente."""

    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = None


class AnamnesisSubmit(BaseModel):
    """Wizard público del cliente (vía portal_token). Recoge TODO (G.3)."""

    # Personales
    sex: Sex
    birth_date: date
    height_cm: float = Field(gt=80, lt=250)
    start_weight_kg: float = Field(gt=30, lt=300)
    body_fat_pct: float | None = Field(default=None, gt=2, lt=60)
    # Salud
    injuries_notes: str | None = None
    medical_notes: str | None = None
    medication_notes: str | None = None
    sport_history: str | None = None
    level: Level
    # Objetivos
    goal_type: GoalType
    goal_weight_kg: float | None = Field(default=None, gt=30, lt=300)
    goal_deadline: date | None = None
    priority_zones: str | None = None  # se guarda en lifestyle_notes etiquetado
    # Entrenamiento
    training_days: int = Field(ge=2, le=6)
    session_max_min: int = Field(ge=30, le=180)
    training_place: TrainingPlace
    equipment: list[str] = Field(default_factory=list)
    # Nutrición
    meals_per_day: int = Field(ge=2, le=6)
    meal_schedule: list[MealScheduleItem] = Field(min_length=2)
    food_allergies: list[str] = Field(default_factory=list)
    food_dislikes: list[str] = Field(default_factory=list)
    food_likes: list[str] = Field(default_factory=list)
    lifestyle_notes: str | None = None
    current_supplements: str | None = None
    diet_mode: DietMode
    strict_free_meal_enabled: bool = False
    # RGPD
    consent_accepted: Literal[True]  # checkbox obligatorio


class ClientUpdate(BaseModel):
    """Edición por el coach (anamnesis editable con audit trail)."""

    full_name: str | None = None
    phone: str | None = None
    sex: Sex | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, gt=80, lt=250)
    start_weight_kg: float | None = Field(default=None, gt=30, lt=300)
    current_weight_kg: float | None = None
    body_fat_pct: float | None = Field(default=None, gt=2, lt=60)
    goal_type: GoalType | None = None
    goal_weight_kg: float | None = None
    goal_deadline: date | None = None
    level: Level | None = None
    training_days: int | None = Field(default=None, ge=2, le=6)
    session_max_min: int | None = Field(default=None, ge=30, le=180)
    training_place: TrainingPlace | None = None
    equipment: list[str] | None = None
    excluded_exercise_ids: list[int] | None = None
    injuries_notes: str | None = None
    medical_notes: str | None = None
    medication_notes: str | None = None
    sport_history: str | None = None
    meals_per_day: int | None = Field(default=None, ge=2, le=6)
    meal_schedule: list[MealScheduleItem] | None = None
    food_allergies: list[str] | None = None
    food_dislikes: list[str] | None = None
    food_likes: list[str] | None = None
    lifestyle_notes: str | None = None
    current_supplements: str | None = None
    diet_mode: DietMode | None = None
    strict_free_meal_enabled: bool | None = None
    auto_pilot: bool | None = None
    emails_enabled: bool | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    sex: Sex | None
    birth_date: date | None
    height_cm: float | None
    start_weight_kg: float | None
    current_weight_kg: float | None
    body_fat_pct: float | None
    goal_type: GoalType | None
    goal_weight_kg: float | None
    goal_deadline: date | None
    level: Level | None
    training_days: int | None
    session_max_min: int | None
    training_place: TrainingPlace | None
    equipment: list[str] | None
    excluded_exercise_ids: list[int] | None
    injuries_notes: str | None
    medical_notes: str | None
    medication_notes: str | None
    sport_history: str | None
    meals_per_day: int | None
    meal_schedule: list[MealScheduleItem] | None
    food_allergies: list[str] | None
    food_dislikes: list[str] | None
    food_likes: list[str] | None
    lifestyle_notes: str | None
    current_supplements: str | None
    diet_mode: DietMode | None
    strict_free_meal_enabled: bool
    status: ClientStatus
    auto_pilot: bool
    emails_enabled: bool
    consent_signed_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------ exercises ----
class ExerciseIn(BaseModel):
    canonical_name: str = Field(min_length=3, max_length=160)
    aliases: list[str] = Field(default_factory=list)
    muscle_primary: str
    muscle_secondary: list[str] = Field(default_factory=list)
    movement_pattern: str
    equipment: list[str] = Field(default_factory=list)
    level_min: int = Field(ge=1, le=3)
    video_url: str | None = None
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] = Field(default_factory=list)


class ExerciseOut(ExerciseIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archived: bool


# ---------------------------------------------------------------- brand ----
class BrandConfigIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color_primary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    color_secondary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    color_bg: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    font_family: Literal["Inter", "Montserrat", "Poppins", "DM Sans", "Plus Jakarta Sans"]
    tagline: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    contact_web: str | None = None
    docs_theme: Theme = "light"
    portal_theme: Theme = "dark"


class BrandConfigOut(BrandConfigIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    logo_path: str | None
    contact_email: str | None  # relaja EmailStr al leer de DB


# ----------------------------------------------------- diario del portal ----
class WorkoutSetIn(BaseModel):
    exercise_id: int
    set_number: int = Field(ge=1, le=20)
    reps: int | None = Field(default=None, ge=0, le=100)
    weight_kg: float | None = Field(default=None, ge=0, le=600)
    rpe: float | None = Field(default=None, ge=1, le=10)
    notes: str | None = None


class DailyLogUpsert(BaseModel):
    log_date: date
    weight_kg: float | None = Field(default=None, gt=30, lt=300)
    sleep_hours: float | None = Field(default=None, ge=0, le=16)
    diet_adherence: DietAdherence | None = None
    diet_notes: str | None = None
    energy_1_5: int | None = Field(default=None, ge=1, le=5)
    mood_1_5: int | None = Field(default=None, ge=1, le=5)
    fatigue_1_5: int | None = Field(default=None, ge=1, le=5)
    free_notes: str | None = None
    chosen_options_json: dict[str, str] | None = None  # {"1": "A"}
    option_feedback_json: dict[str, Literal["up", "down"]] | None = None
    workout_sets: list[WorkoutSetIn] = Field(default_factory=list)


# ------------------------------------------------------------- cierre ----
class PeriodCloseIn(BaseModel):
    closing_weight_kg: float = Field(gt=30, lt=300)
    closing_rating: int = Field(ge=1, le=5)
    closing_hardest: str | None = None
    closing_questions: str | None = None
    closing_waist_cm: float | None = Field(default=None, gt=30, lt=250)
    closing_hip_cm: float | None = Field(default=None, gt=30, lt=250)
    closing_arm_cm: float | None = Field(default=None, gt=10, lt=80)
    closing_thigh_cm: float | None = Field(default=None, gt=20, lt=120)


# ----------------------------------------------------- change requests ----
class ChangeRequestIn(BaseModel):
    message: str = Field(min_length=5, max_length=2000)


class ChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    message: str
    status: Literal["open", "resolved"]
    created_at: datetime
    resolved_at: datetime | None


# ------------------------------------------- respuestas de la Fase 2 ----
class PortalLinkOut(BaseModel):
    """Links que el coach copia/comparte (perfil de cliente, alta)."""

    portal_token: str
    portal_url: str
    anamnesis_url: str


class ClientCreatedOut(BaseModel):
    client: ClientOut
    links: PortalLinkOut


class ExerciseUpdate(BaseModel):
    """PATCH parcial de la biblioteca (incluye video_url editable, F.3)."""

    canonical_name: str | None = Field(default=None, min_length=3, max_length=160)
    aliases: list[str] | None = None
    muscle_primary: str | None = None
    muscle_secondary: list[str] | None = None
    movement_pattern: str | None = None
    equipment: list[str] | None = None
    level_min: int | None = Field(default=None, ge=1, le=3)
    video_url: str | None = None
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] | None = None


class AnamnesisStateOut(BaseModel):
    """Estado público del wizard (GET /api/p/{token}) — datos mínimos."""

    first_name: str
    anamnesis_done: bool
    photos_count: int
    brand_name: str
    color_primary: str
    color_bg: str
    font_family: str
    portal_theme: Theme


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Literal["front", "side", "back", "detail"]
    taken_at: datetime


# ============================================================ portal del cliente ====
# Schemas de SALIDA del portal (Fase 6). Lo de cara al cliente va en castellano.

class PortalBrand(BaseModel):
    """Marca aplicada al portal (tematización en runtime)."""

    name: str
    color_primary: str
    color_secondary: str
    color_bg: str
    font_family: str
    portal_theme: Theme
    logo_path: str | None = None


class PortalPeriodInfo(BaseModel):
    """Estado del período activo del cliente."""

    period_id: int
    period_index: int
    starts_on: date
    ends_on: date
    days_total: int
    days_elapsed: int
    days_left: int
    can_close: bool  # desde día 14
    status: Literal["open", "closed", "analyzed"]


class PortalState(BaseModel):
    """GET /api/p/{token}/state — todo lo que el portal necesita para arrancar."""

    first_name: str
    status: ClientStatus
    diet_mode: DietMode | None
    has_plan: bool
    period: PortalPeriodInfo | None
    brand: PortalBrand


class TodayMealOption(BaseModel):
    key: str
    title: str
    macros: dict
    prep_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)


class TodayMealSlot(BaseModel):
    slot: int
    name: str
    time: str
    target: dict
    # modo flexible: varias opciones para elegir; modo estricto: una sola (dish)
    options: list[TodayMealOption] = Field(default_factory=list)
    chosen_key: str | None = None


class TodayExercise(BaseModel):
    exercise_id: int
    name: str
    sets: int
    rep_range: str
    rir: str
    rest_sec: int
    start_weight_hint_kg: float | None
    technique_cue: str | None
    video_url: str | None


class TodaySession(BaseModel):
    day: str
    name: str
    warmup: str | None
    exercises: list[TodayExercise]
    cooldown: str | None


class TodayView(BaseModel):
    """GET /api/p/{token}/today — la vista estrella. Lectura en <30 s."""

    date: date
    day_label: str            # "Lunes", "Martes"…
    period: PortalPeriodInfo | None
    meals: list[TodayMealSlot]
    session: TodaySession | None  # None si hoy es día de descanso
    already_logged: bool


class PortalPlanOut(BaseModel):
    """GET /api/p/{token}/plan — plan completo navegable."""

    month_index: int
    nutrition: dict | None
    training: dict | None
    education: dict | None
    diet_mode: DietMode | None


class DailyLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_date: date
    weight_kg: float | None
    sleep_hours: float | None
    diet_adherence: DietAdherence | None
    energy_1_5: int | None
    mood_1_5: int | None
    fatigue_1_5: int | None


class FeedbackDocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str           # biweekly | monthly
    sent_at: datetime | None
    content_json: dict | None


# --- alta de período/plan por el coach (soporte para Fases 6–7) ---
class PeriodCreateIn(BaseModel):
    plan_id: int
    starts_on: date
    days: int = Field(default=14, ge=7, le=31)

```


## `backend/app/security.py`

```python
"""Seguridad: contraseñas (bcrypt), JWT de coaches y tokens de portal.

Diseño del token de portal (G.4 — "firmado, revocable/regenerable"):
- token = URLSafeSerializer(PORTAL_TOKEN_SECRET).dumps({"c": client_id, "n": nonce})
- La firma garantiza integridad (no se pueden fabricar tokens).
- La revocación se consigue comparando contra `clients.portal_token` en DB:
  regenerar = guardar un token nuevo → el anterior deja de coincidir y muere.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

JWT_ALGORITHM = "HS256"

_portal_serializer = URLSafeSerializer(settings.portal_token_secret, salt="portal")


# ----------------------------------------------------------- contraseñas ----
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ------------------------------------------------------------ JWT coaches ----
def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Devuelve el username o None si el token es inválido/expirado."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        return str(payload["sub"])
    except (jwt.PyJWTError, KeyError):
        return None


# -------------------------------------------------------- tokens de portal ----
def new_portal_token(client_id: int) -> str:
    return _portal_serializer.dumps({"c": client_id, "n": secrets.token_hex(8)})


def portal_token_client_id(token: str) -> int | None:
    """Verifica la FIRMA y devuelve el client_id embebido (o None).

    La validez final exige además que el token coincida con el guardado en DB
    (ver deps.get_client_by_token) — así un token regenerado revoca el anterior.
    """
    try:
        data = _portal_serializer.loads(token)
        return int(data["c"])
    except (BadSignature, KeyError, TypeError, ValueError):
        return None

```


## `backend/app/seeds/__init__.py`

```python

```


## `backend/app/seeds/exercises_data.py`

```python
# -*- coding: utf-8 -*-
"""Biblioteca de 150 ejercicios (seed, F.3).

Convenciones de valores (decisión declarada — slugs en castellano porque son
datos de cara al cliente en checklists, planes y gráficas):

- muscle_*: pecho, espalda, hombros, biceps, triceps, cuadriceps, isquios,
  gluteos, gemelos, core, antebrazos, trapecio, aductores
- movement_pattern (snake_case inglés, taxonomía técnica): horizontal_push,
  vertical_push, horizontal_pull, vertical_pull, squat, hip_hinge, lunge,
  knee_extension, knee_flexion, hip_extension, hip_abduction, hip_adduction,
  plantar_flexion, dorsiflexion, elbow_flexion, elbow_extension,
  shoulder_abduction, shoulder_flexion, shoulder_external_rotation,
  scapular_elevation, core_anti_extension, core_anti_rotation, core_flexion
- equipment: barra, mancuernas, maquina, polea, multipower, peso_corporal,
  banco, barra_dominadas, paralelas, bandas, kettlebell, barra_ez,
  barra_hexagonal, rack, disco, deslizadores, cajon, banco_scott, lastre
- contraindications (articulación sensible): hombro, codo, muneca, lumbar,
  rodilla, cadera, cuello, tobillo
- level_min: 1 principiante · 2 intermedio · 3 avanzado
- video_url: vacío por defecto, editable por el coach desde Settings (F.3)
"""

VALID_MUSCLES = {
    "pecho", "espalda", "hombros", "biceps", "triceps", "cuadriceps", "isquios",
    "gluteos", "gemelos", "core", "antebrazos", "trapecio", "aductores",
}
VALID_PATTERNS = {
    "horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull",
    "squat", "hip_hinge", "lunge", "knee_extension", "knee_flexion",
    "hip_extension", "hip_abduction", "hip_adduction", "plantar_flexion",
    "dorsiflexion", "elbow_flexion", "elbow_extension", "shoulder_abduction",
    "shoulder_flexion", "shoulder_external_rotation", "scapular_elevation",
    "core_anti_extension", "core_anti_rotation", "core_flexion",
}
VALID_EQUIPMENT = {
    "barra", "mancuernas", "maquina", "polea", "multipower", "peso_corporal",
    "banco", "barra_dominadas", "paralelas", "bandas", "kettlebell", "barra_ez",
    "barra_hexagonal", "rack", "disco", "deslizadores", "cajon", "banco_scott",
    "lastre",
}
VALID_CONTRA = {"hombro", "codo", "muneca", "lumbar", "rodilla", "cadera", "cuello", "tobillo"}


def _ex(name, aliases, mp, ms, pattern, equip, lvl, tech, bio, contra):
    return {
        "canonical_name": name,
        "aliases": aliases,
        "muscle_primary": mp,
        "muscle_secondary": ms,
        "movement_pattern": pattern,
        "equipment": equip,
        "level_min": lvl,
        "video_url": "",
        "technique_notes": tech,
        "biomechanics_notes": bio,
        "contraindications": contra,
    }


EXERCISES = [
    # ================= EMPUJE HORIZONTAL (15) =================
    _ex("Press banca con barra", ["press de banca", "bench press", "press plano"],
        "pecho", ["triceps", "hombros"], "horizontal_push", ["barra", "banco", "rack"], 1,
        "Escápulas retraídas, pies firmes, barra a la línea del pecho bajo.",
        "El arco torácico estabiliza el hombro y alinea las fibras del pectoral con el empuje.",
        ["hombro"]),
    _ex("Press banca inclinado con barra", ["press inclinado", "incline bench press"],
        "pecho", ["hombros", "triceps"], "horizontal_push", ["barra", "banco", "rack"], 1,
        "Banco a 30-45°, la barra baja a la clavícula sin rebotar.",
        "La inclinación orienta la resistencia hacia las fibras claviculares del pectoral.",
        ["hombro"]),
    _ex("Press banca declinado con barra", ["press declinado", "decline bench press"],
        "pecho", ["triceps"], "horizontal_push", ["barra", "banco", "rack"], 2,
        "Recorrido corto y controlado, la barra toca el pecho bajo.",
        "El declive enfatiza la porción esternocostal y reduce el estrés del hombro.",
        []),
    _ex("Press banca con mancuernas", ["press plano con mancuernas", "dumbbell bench press"],
        "pecho", ["triceps", "hombros"], "horizontal_push", ["mancuernas", "banco"], 1,
        "Baja hasta un estiramiento cómodo, codos a unos 45° del torso.",
        "Las mancuernas permiten mayor rango y trabajo estabilizador que la barra.",
        ["hombro"]),
    _ex("Press inclinado con mancuernas", ["incline dumbbell press"],
        "pecho", ["hombros", "triceps"], "horizontal_push", ["mancuernas", "banco"], 1,
        "Banco a 30°, muñecas neutras, junta las mancuernas arriba sin chocarlas.",
        "Gran estiramiento del pectoral superior bajo carga: estímulo hipertrófico clave.",
        ["hombro"]),
    _ex("Press de pecho en máquina", ["chest press", "press en máquina"],
        "pecho", ["triceps", "hombros"], "horizontal_push", ["maquina"], 1,
        "Ajusta el asiento para que los agarres queden a media altura del pecho.",
        "La trayectoria guiada permite cercanía al fallo con riesgo mínimo.",
        []),
    _ex("Press banca en multipower", ["press banca smith"],
        "pecho", ["triceps", "hombros"], "horizontal_push", ["multipower", "banco"], 1,
        "Coloca el banco para que la barra baje a la línea del pecho bajo.",
        "La guía vertical elimina la estabilización: útil para fatigar con seguridad.",
        ["hombro"]),
    _ex("Press inclinado en multipower", ["press inclinado smith"],
        "pecho", ["hombros", "triceps"], "horizontal_push", ["multipower", "banco"], 1,
        "Banco a 30-45° centrado bajo la barra, baja a la clavícula.",
        "Trayectoria fija que estandariza el estímulo del pectoral superior serie a serie.",
        ["hombro"]),
    _ex("Flexiones", ["push ups", "lagartijas", "fondos en el suelo"],
        "pecho", ["triceps", "hombros", "core"], "horizontal_push", ["peso_corporal"], 1,
        "Cuerpo en línea recta, manos algo más anchas que los hombros.",
        "Empuje en cadena cerrada con escápulas libres: protracción completa arriba.",
        ["muneca"]),
    _ex("Flexiones lastradas", ["push ups con lastre", "flexiones con peso"],
        "pecho", ["triceps", "hombros", "core"], "horizontal_push", ["peso_corporal", "lastre"], 2,
        "Disco centrado en la espalda alta o chaleco; mismo cuerpo rígido.",
        "Permite sobrecarga progresiva manteniendo el patrón de cadena cerrada.",
        ["muneca"]),
    _ex("Fondos en paralelas (énfasis pecho)", ["dips pecho", "fondos pecho"],
        "pecho", ["triceps", "hombros"], "horizontal_push", ["paralelas"], 2,
        "Torso inclinado adelante, baja hasta sentir estiramiento sin dolor.",
        "La inclinación del torso desplaza la demanda del tríceps al pectoral inferior.",
        ["hombro"]),
    _ex("Aperturas con mancuernas", ["flyes", "aperturas planas"],
        "pecho", [], "horizontal_push", ["mancuernas", "banco"], 1,
        "Codos semiflexionados fijos, abre hasta estiramiento cómodo.",
        "Aísla la aducción horizontal: máxima tensión en estiramiento, controla la bajada.",
        ["hombro"]),
    _ex("Cruce de poleas", ["crossover", "cruces en polea", "cable fly"],
        "pecho", [], "horizontal_push", ["polea"], 1,
        "Paso adelante, abraza un árbol imaginario, junta manos al frente.",
        "La polea mantiene tensión constante también en el acortamiento máximo.",
        []),
    _ex("Contractora de pecho", ["pec deck", "peck deck", "mariposa"],
        "pecho", [], "horizontal_push", ["maquina"], 1,
        "Codos a la altura del pecho, junta y aprieta 1 segundo.",
        "Aducción horizontal guiada: aislamiento del pectoral sin demanda de estabilidad.",
        []),
    _ex("Press de suelo con barra", ["floor press"],
        "pecho", ["triceps"], "horizontal_push", ["barra", "rack"], 2,
        "Tumbado en el suelo, los codos tocan suavemente y empuja.",
        "El rango parcial limita la extensión del hombro: opción amable con hombros sensibles.",
        []),

    # ================= EMPUJE VERTICAL (10) =================
    _ex("Press militar de pie con barra", ["overhead press", "press militar", "ohp"],
        "hombros", ["triceps", "core"], "vertical_push", ["barra", "rack"], 2,
        "Glúteos y core firmes, la barra sube pegada a la cara y acaba sobre la coronilla.",
        "Empuje vertical global: el deltoides anterior lidera con gran demanda de core.",
        ["hombro", "lumbar"]),
    _ex("Press militar sentado con barra", ["press militar sentado"],
        "hombros", ["triceps"], "vertical_push", ["barra", "banco", "rack"], 2,
        "Respaldo casi vertical, antebrazos verticales bajo la barra.",
        "El apoyo elimina la extensión lumbar compensatoria y concentra el trabajo en el deltoides.",
        ["hombro"]),
    _ex("Press de hombros con mancuernas sentado", ["press militar con mancuernas", "shoulder press"],
        "hombros", ["triceps"], "vertical_push", ["mancuernas", "banco"], 1,
        "Codos ligeramente por delante del plano del torso, sube sin chocar arriba.",
        "El plano escapular (ligeramente frontal) es la trayectoria más amable para el manguito.",
        ["hombro"]),
    _ex("Press Arnold", ["arnold press"],
        "hombros", ["triceps"], "vertical_push", ["mancuernas", "banco"], 2,
        "Inicia con palmas hacia ti y rota mientras empujas hacia arriba.",
        "La rotación añade recorrido y solicita el deltoides anterior en mayor rango.",
        ["hombro"]),
    _ex("Press de hombros en máquina", ["shoulder press machine"],
        "hombros", ["triceps"], "vertical_push", ["maquina"], 1,
        "Ajusta el asiento: los agarres parten a la altura de las orejas.",
        "Guiado y estable: ideal para progresar cerca del fallo con técnica constante.",
        []),
    _ex("Press de hombros en multipower", ["press militar smith"],
        "hombros", ["triceps"], "vertical_push", ["multipower", "banco"], 1,
        "Banco casi vertical, la barra baja por delante hasta la barbilla.",
        "Trayectoria fija que permite cargar el empuje vertical sin estabilización.",
        ["hombro"]),
    _ex("Push press", ["press con empuje de piernas"],
        "hombros", ["triceps", "cuadriceps", "core"], "vertical_push", ["barra", "rack"], 3,
        "Pequeña flexión de rodillas y extiende explosivo transfiriendo a los brazos.",
        "El impulso de piernas permite sobrecargar la fase excéntrica del press.",
        ["hombro", "lumbar"]),
    _ex("Press landmine de pie", ["landmine press", "press con barra en esquina"],
        "hombros", ["pecho", "triceps", "core"], "vertical_push", ["barra"], 1,
        "Empuja la barra en diagonal hacia arriba y adelante, costillas abajo.",
        "El ángulo diagonal reduce la demanda de movilidad de hombro: ideal con limitaciones.",
        []),
    _ex("Flexiones pike", ["pike push ups", "flexiones en V"],
        "hombros", ["triceps"], "vertical_push", ["peso_corporal"], 2,
        "Cadera alta en V invertida, la cabeza baja entre las manos.",
        "Convierte la flexión en empuje casi vertical: progresión calisténica del press.",
        ["muneca", "hombro"]),
    _ex("Press de hombro unilateral con mancuerna de pie", ["press unilateral de hombro"],
        "hombros", ["triceps", "core"], "vertical_push", ["mancuernas"], 2,
        "Aprieta el glúteo del mismo lado y evita inclinarte al empujar.",
        "El empuje unilateral añade antiflexión lateral: hombro y core en un gesto.",
        ["hombro"]),

    # ================= TRACCIÓN HORIZONTAL (13) =================
    _ex("Remo con barra", ["barbell row", "remo inclinado"],
        "espalda", ["biceps", "trapecio", "isquios"], "horizontal_pull", ["barra"], 2,
        "Torso a 30-45°, lleva la barra al abdomen bajo sin dar tirones.",
        "Tracción horizontal global: dorsal y retractores escapulares con bisagra isométrica.",
        ["lumbar"]),
    _ex("Remo Pendlay", ["pendlay row"],
        "espalda", ["biceps", "trapecio"], "horizontal_pull", ["barra"], 3,
        "Torso paralelo al suelo, la barra parte del suelo en cada repetición.",
        "El reinicio desde el suelo elimina inercia y exige tracción explosiva estricta.",
        ["lumbar"]),
    _ex("Remo con mancuerna a una mano", ["remo unilateral", "one arm row"],
        "espalda", ["biceps"], "horizontal_pull", ["mancuernas", "banco"], 1,
        "Rodilla y mano apoyadas en el banco, tira del codo hacia la cadera.",
        "El apoyo descarga la lumbar y permite gran rango con sobrecarga unilateral.",
        []),
    _ex("Remo con pecho apoyado en banco", ["chest supported row", "remo tumbado en banco inclinado"],
        "espalda", ["biceps", "trapecio"], "horizontal_pull", ["mancuernas", "banco"], 1,
        "Pecho fijo al banco inclinado; tira de los codos atrás y junta escápulas.",
        "El apoyo elimina toda implicación lumbar: aislamiento real de la tracción.",
        []),
    _ex("Remo sentado en polea", ["remo en polea baja", "seated cable row", "remo gironda"],
        "espalda", ["biceps", "trapecio"], "horizontal_pull", ["polea"], 1,
        "Torso erguido estable, lleva el agarre al ombligo y junta escápulas.",
        "Tensión constante de la polea con torso fijo: técnica fácil de estandarizar.",
        []),
    _ex("Remo en máquina", ["remo hammer", "machine row"],
        "espalda", ["biceps", "trapecio"], "horizontal_pull", ["maquina"], 1,
        "Pecho apoyado en el pad, tira sin encoger los hombros hacia las orejas.",
        "Trayectoria guiada con apoyo torácico: progresión segura cerca del fallo.",
        []),
    _ex("Remo con barra T", ["t-bar row", "remo en punta"],
        "espalda", ["biceps", "trapecio", "isquios"], "horizontal_pull", ["barra", "maquina"], 2,
        "Agarre neutro, torso fijo a 45°, la carga sube al pecho bajo.",
        "El agarre neutro favorece la retracción y permite cargas altas de tracción.",
        ["lumbar"]),
    _ex("Remo invertido", ["inverted row", "remo australiano"],
        "espalda", ["biceps", "core"], "horizontal_pull", ["barra", "rack", "peso_corporal"], 1,
        "Cuerpo en tabla, lleva el pecho a la barra; más horizontal = más difícil.",
        "Tracción en cadena cerrada autorregulable por el ángulo del cuerpo.",
        []),
    _ex("Remo en polea a una mano", ["remo unilateral en polea"],
        "espalda", ["biceps"], "horizontal_pull", ["polea"], 1,
        "Permite rotar levemente el torso al tirar para alargar el dorsal.",
        "La tracción unilateral en polea maximiza el rango y corrige asimetrías.",
        []),
    _ex("Remo Meadows", ["meadows row"],
        "espalda", ["biceps", "trapecio"], "horizontal_pull", ["barra"], 3,
        "Perpendicular a la barra landmine, agarre por encima, tira hacia la cadera.",
        "El ángulo y el agarre pronado castigan dorsal alto y redondo mayor.",
        ["lumbar"]),
    _ex("Face pull en polea", ["face pull", "jalón a la cara"],
        "hombros", ["trapecio", "espalda"], "horizontal_pull", ["polea"], 1,
        "Cuerda a la altura de la cara, tira separando las manos hacia las orejas.",
        "Combina retracción y rotación externa: salud de hombro y deltoides posterior.",
        []),
    _ex("Pájaros con mancuernas", ["reverse fly", "aperturas invertidas", "bent over lateral raise"],
        "hombros", ["trapecio", "espalda"], "horizontal_pull", ["mancuernas"], 1,
        "Torso inclinado, codos semifijos, abre hacia los lados sin balanceo.",
        "Abducción horizontal pura: aísla deltoides posterior y trapecio medio.",
        ["lumbar"]),
    _ex("Contractora invertida", ["reverse pec deck", "peck deck invertido"],
        "hombros", ["trapecio", "espalda"], "horizontal_pull", ["maquina"], 1,
        "Pecho contra el pad, abre los brazos hasta la línea del torso.",
        "Aislamiento guiado del deltoides posterior sin implicación lumbar.",
        []),

    # ================= TRACCIÓN VERTICAL (10) =================
    _ex("Dominadas pronas", ["pull ups", "dominadas"],
        "espalda", ["biceps", "core"], "vertical_pull", ["barra_dominadas", "peso_corporal"], 2,
        "Desde brazos extendidos, lleva el pecho hacia la barra sin balanceo.",
        "Tracción vertical reina: el dorsal aduce y extiende el hombro contra el peso corporal.",
        ["hombro", "codo"]),
    _ex("Dominadas supinas", ["chin ups", "dominadas agarre supino"],
        "espalda", ["biceps", "core"], "vertical_pull", ["barra_dominadas", "peso_corporal"], 2,
        "Agarre al ancho de hombros con palmas hacia ti, sube hasta barbilla sobre barra.",
        "La supinación implica más al bíceps y suele permitir más repeticiones.",
        ["codo"]),
    _ex("Dominadas neutras", ["dominadas agarre neutro"],
        "espalda", ["biceps", "core"], "vertical_pull", ["barra_dominadas", "peso_corporal"], 2,
        "Palmas enfrentadas, codos hacia las costillas al subir.",
        "El agarre neutro es la posición más amable para hombro y codo.",
        []),
    _ex("Dominadas lastradas", ["weighted pull ups"],
        "espalda", ["biceps", "core"], "vertical_pull", ["barra_dominadas", "lastre"], 3,
        "Lastre estable en cinturón; mismas dominadas estrictas de siempre.",
        "Sobrecarga progresiva del patrón de tracción vertical más completo.",
        ["hombro", "codo"]),
    _ex("Jalón al pecho", ["lat pulldown", "polea al pecho", "jalón frontal"],
        "espalda", ["biceps"], "vertical_pull", ["polea", "maquina"], 1,
        "Ligera inclinación atrás fija, lleva la barra a la clavícula con codos abajo.",
        "Versión regulable de la dominada: misma aducción de hombro con carga ajustable.",
        []),
    _ex("Jalón agarre estrecho neutro", ["jalón neutro", "close grip pulldown"],
        "espalda", ["biceps"], "vertical_pull", ["polea", "maquina"], 1,
        "Maneral en V, tira hacia el pecho alto alargando el torso.",
        "El agarre estrecho neutro maximiza el recorrido del dorsal en el plano sagital.",
        []),
    _ex("Jalón unilateral en polea", ["jalón a una mano"],
        "espalda", ["biceps"], "vertical_pull", ["polea"], 2,
        "De rodillas o sentado, tira del codo hacia el bolsillo del mismo lado.",
        "La versión unilateral permite máximo estiramiento y corrige déficits laterales.",
        []),
    _ex("Jalón con brazos rectos en polea", ["straight arm pulldown", "pullover en polea de pie"],
        "espalda", ["triceps", "core"], "vertical_pull", ["polea"], 1,
        "Brazos casi rectos, lleva la barra de los hombros a las caderas en arco.",
        "Extensión pura de hombro: aísla el dorsal sin que el bíceps limite la serie.",
        []),
    _ex("Pullover en polea alta", ["cable pullover"],
        "espalda", ["pecho", "triceps"], "vertical_pull", ["polea"], 1,
        "Torso inclinado, arco amplio con codos semifijos hasta la cadera.",
        "Tensión constante en el dorsal a lo largo de todo el arco de extensión.",
        []),
    _ex("Pullover con mancuerna", ["dumbbell pullover"],
        "espalda", ["pecho", "triceps"], "vertical_pull", ["mancuernas", "banco"], 2,
        "Tumbado transversal al banco, baja la mancuerna tras la cabeza con codos semifijos.",
        "Gran estiramiento simultáneo de dorsal y pectoral bajo carga.",
        ["hombro"]),

    # ================= SENTADILLA (12) =================
    _ex("Sentadilla trasera con barra", ["back squat", "sentadilla con barra"],
        "cuadriceps", ["gluteos", "isquios", "core"], "squat", ["barra", "rack"], 2,
        "Barra sobre trapecios, baja entre las rodillas con torso firme y talones fijos.",
        "Patrón de rodilla dominante global: máxima transferencia de fuerza al tren inferior.",
        ["rodilla", "lumbar"]),
    _ex("Sentadilla frontal con barra", ["front squat"],
        "cuadriceps", ["gluteos", "core"], "squat", ["barra", "rack"], 3,
        "Barra en deltoides anteriores, codos altos, torso lo más vertical posible.",
        "La carga frontal verticaliza el torso: más cuádriceps y menos cizalla lumbar.",
        ["rodilla", "muneca"]),
    _ex("Sentadilla goblet", ["goblet squat", "sentadilla con mancuerna al pecho"],
        "cuadriceps", ["gluteos", "core"], "squat", ["mancuernas", "kettlebell"], 1,
        "Mancuerna pegada al pecho, baja entre las rodillas con codos por dentro.",
        "El contrapeso anterior enseña la mecánica de sentadilla profunda con torso erguido.",
        []),
    _ex("Sentadilla hack en máquina", ["hack squat"],
        "cuadriceps", ["gluteos"], "squat", ["maquina"], 1,
        "Pies a media plataforma, baja profundo sin despegar el sacro del respaldo.",
        "El respaldo fija el torso: flexión de rodilla profunda con mínima demanda lumbar.",
        ["rodilla"]),
    _ex("Prensa de piernas 45°", ["leg press", "prensa inclinada"],
        "cuadriceps", ["gluteos", "isquios"], "squat", ["maquina"], 1,
        "Baja controlado hasta donde la pelvis no bascule; no bloquees con golpe.",
        "Permite cargar el patrón de rodilla con el torso completamente descargado.",
        ["rodilla"]),
    _ex("Prensa de piernas horizontal", ["prensa sentada", "seated leg press"],
        "cuadriceps", ["gluteos"], "squat", ["maquina"], 1,
        "Espalda y sacro pegados al respaldo durante todo el recorrido.",
        "Versión más accesible de la prensa: ideal para principiantes y rehabilitación.",
        []),
    _ex("Sentadilla en multipower", ["sentadilla smith"],
        "cuadriceps", ["gluteos"], "squat", ["multipower"], 1,
        "Pies ligeramente adelantados respecto a la barra, baja vertical.",
        "La guía permite manipular el vector para sesgar cuádriceps o glúteo.",
        ["rodilla"]),
    _ex("Sentadilla a cajón", ["box squat", "sentadilla al banco"],
        "cuadriceps", ["gluteos", "isquios"], "squat", ["barra", "rack", "cajon"], 1,
        "Siéntate atrás con control hasta el cajón, pausa breve y sube sin balanceo.",
        "El cajón estandariza la profundidad y enseña a sentarse atrás con confianza.",
        []),
    _ex("Sentadilla Zercher", ["zercher squat"],
        "cuadriceps", ["gluteos", "core", "biceps"], "squat", ["barra", "rack"], 3,
        "Barra en el pliegue de los codos abrazada al cuerpo, torso erguido.",
        "La carga en los codos dispara la demanda de core y mantiene el torso vertical.",
        ["codo", "lumbar"]),
    _ex("Sentadilla sissy", ["sissy squat"],
        "cuadriceps", [], "knee_extension", ["peso_corporal", "maquina"], 3,
        "Rodillas adelante y torso atrás en línea con el muslo; rango progresivo.",
        "Flexión de rodilla extrema con cadera extendida: estiramiento máximo del recto femoral.",
        ["rodilla"]),
    _ex("Sentadilla pistol asistida", ["pistol squat asistida", "sentadilla a una pierna"],
        "cuadriceps", ["gluteos", "core"], "squat", ["peso_corporal", "bandas"], 3,
        "Sujétate de un soporte o banda, baja a una pierna con talón fijo.",
        "Fuerza unilateral con gran demanda de control de rodilla y tobillo.",
        ["rodilla"]),
    _ex("Sentadilla pausada con barra", ["pause squat"],
        "cuadriceps", ["gluteos", "core"], "squat", ["barra", "rack"], 2,
        "Pausa real de 2-3 s abajo manteniendo tensión, sube sin rebote.",
        "La pausa elimina el reflejo elástico: más tensión muscular con menos carga absoluta.",
        ["rodilla", "lumbar"]),

    # ================= BISAGRA DE CADERA (12) =================
    _ex("Peso muerto convencional", ["deadlift", "peso muerto"],
        "isquios", ["gluteos", "espalda", "trapecio", "antebrazos"], "hip_hinge", ["barra"], 2,
        "Barra pegada a la tibia, espalda neutra, empuja el suelo y estira la cadera.",
        "La bisagra cargada más global: cadena posterior completa más agarre y espalda.",
        ["lumbar"]),
    _ex("Peso muerto sumo", ["sumo deadlift"],
        "gluteos", ["isquios", "cuadriceps", "aductores"], "hip_hinge", ["barra"], 2,
        "Postura ancha con puntas abiertas, rodillas siguen a los pies, torso más vertical.",
        "La postura ancha acorta la palanca lumbar y recluta más aductor y glúteo.",
        ["cadera", "lumbar"]),
    _ex("Peso muerto rumano con barra", ["rdl", "peso muerto rumano"],
        "isquios", ["gluteos", "espalda"], "hip_hinge", ["barra"], 1,
        "Desde de pie, cadera atrás con rodillas semiflexionadas hasta media tibia.",
        "Bisagra con énfasis excéntrico: el isquio se alarga bajo carga, estímulo clave.",
        ["lumbar"]),
    _ex("Peso muerto rumano con mancuernas", ["rdl con mancuernas"],
        "isquios", ["gluteos"], "hip_hinge", ["mancuernas"], 1,
        "Mancuernas rozando los muslos, cadera atrás, espalda neutra siempre.",
        "Versión accesible del rumano: ideal para aprender la bisagra en casa o gym.",
        ["lumbar"]),
    _ex("Peso muerto con barra hexagonal", ["trap bar deadlift", "peso muerto hexagonal"],
        "cuadriceps", ["gluteos", "isquios", "trapecio"], "hip_hinge", ["barra_hexagonal"], 1,
        "Dentro de la barra, agarres neutros, empuja el suelo con torso firme.",
        "El centro de masa alineado reduce la cizalla lumbar: el tirón más amable de aprender.",
        []),
    _ex("Buenos días con barra", ["good morning"],
        "isquios", ["gluteos", "espalda"], "hip_hinge", ["barra", "rack"], 3,
        "Barra como en sentadilla, cadera atrás hasta torso ~45°, rodillas semiflexionadas.",
        "Bisagra con la carga lejos de la cadera: enorme palanca para isquios y erectores.",
        ["lumbar"]),
    _ex("Hiperextensiones 45°", ["back extension", "extensiones lumbares", "hiperextensiones"],
        "isquios", ["gluteos", "espalda"], "hip_hinge", ["maquina"], 1,
        "Pad en la cadera, baja redondeando lo justo y sube apretando glúteo.",
        "Extensión de cadera guiada; con pelvis retrovertida sesga el glúteo.",
        []),
    _ex("Hip thrust con barra", ["empuje de cadera", "hip thrust"],
        "gluteos", ["isquios", "cuadriceps"], "hip_extension", ["barra", "banco"], 1,
        "Espalda alta en el banco, barbilla al pecho, extiende y bloquea 1 s arriba.",
        "Tensión máxima del glúteo en acortamiento: el complemento perfecto de la bisagra.",
        []),
    _ex("Puente de glúteos", ["glute bridge", "puente de cadera en suelo"],
        "gluteos", ["isquios"], "hip_extension", ["peso_corporal", "barra"], 1,
        "Tumbado con rodillas flexionadas, eleva la cadera apretando glúteo arriba.",
        "Patrón base de extensión de cadera, progresable con carga sobre la pelvis.",
        []),
    _ex("Pull through en polea", ["cable pull through"],
        "gluteos", ["isquios"], "hip_hinge", ["polea"], 1,
        "De espaldas a la polea baja, cuerda entre las piernas, bisagra y extiende.",
        "La resistencia desde atrás enseña la extensión de cadera con tensión al final.",
        []),
    _ex("Swing con kettlebell", ["kettlebell swing", "balanceo ruso"],
        "gluteos", ["isquios", "core"], "hip_hinge", ["kettlebell"], 2,
        "Bisagra explosiva: la kettlebell flota hasta el pecho por el empuje de cadera.",
        "Potencia de cadera balística con gran demanda metabólica y de core.",
        ["lumbar"]),
    _ex("Peso muerto rumano a una pierna", ["single leg rdl", "peso muerto unilateral"],
        "isquios", ["gluteos", "core"], "hip_hinge", ["mancuernas", "kettlebell"], 2,
        "Cadera cuadrada al frente, la pierna libre extiende atrás como contrapeso.",
        "Bisagra unilateral: añade estabilidad de cadera y equilibrio al estímulo de isquio.",
        []),

    # ================= ZANCADA (8) =================
    _ex("Zancadas caminando con mancuernas", ["walking lunges", "zancadas"],
        "cuadriceps", ["gluteos", "core"], "lunge", ["mancuernas"], 2,
        "Pasos largos y estables, la rodilla trasera roza el suelo.",
        "Patrón unilateral dinámico: fuerza, estabilidad y gran coste metabólico.",
        ["rodilla"]),
    _ex("Zancada estática", ["split squat", "zancada en el sitio"],
        "cuadriceps", ["gluteos"], "lunge", ["mancuernas", "peso_corporal"], 1,
        "Posición de paso fija, sube y baja vertical sin cambiar los apoyos.",
        "La versión más estable de la zancada: ideal para aprender el patrón unilateral.",
        ["rodilla"]),
    _ex("Sentadilla búlgara", ["bulgarian split squat", "zancada búlgara"],
        "cuadriceps", ["gluteos"], "lunge", ["mancuernas", "banco"], 2,
        "Empeine trasero en el banco, baja vertical; el torso inclinado sesga el glúteo.",
        "El pie elevado concentra la carga en la pierna delantera: unilateral estrella.",
        ["rodilla"]),
    _ex("Zancada inversa", ["reverse lunge", "zancada atrás"],
        "cuadriceps", ["gluteos"], "lunge", ["mancuernas", "peso_corporal"], 1,
        "Paso atrás controlado, empuja con el talón delantero para volver.",
        "El paso atrás reduce el estrés de la rodilla delantera frente a la zancada frontal.",
        []),
    _ex("Zancada lateral", ["lateral lunge", "zancada al lado"],
        "cuadriceps", ["gluteos", "aductores"], "lunge", ["mancuernas", "peso_corporal"], 2,
        "Paso lateral amplio, siéntate sobre esa cadera con el otro pie plano.",
        "Trabajo en plano frontal: aductores y glúteo medio que la zancada normal no toca.",
        ["rodilla", "cadera"]),
    _ex("Subida a cajón", ["step up", "subida al banco"],
        "cuadriceps", ["gluteos"], "lunge", ["mancuernas", "cajon", "banco"], 1,
        "Sube empujando solo con la pierna del cajón, baja con control.",
        "Extensión unilateral de rodilla y cadera con transferencia directa a la vida diaria.",
        []),
    _ex("Split squat en multipower", ["zancada en smith"],
        "cuadriceps", ["gluteos"], "lunge", ["multipower"], 1,
        "Pie delantero adelantado a la barra, baja vertical por la guía.",
        "La guía elimina el equilibrio: permite acercarse al fallo en unilateral con seguridad.",
        ["rodilla"]),
    _ex("Zancada curtsy", ["curtsy lunge", "zancada cruzada"],
        "gluteos", ["cuadriceps", "aductores"], "lunge", ["mancuernas", "peso_corporal"], 2,
        "Cruza la pierna por detrás en diagonal manteniendo la cadera al frente.",
        "La aducción combinada con extensión enfatiza glúteo medio y mayor.",
        ["rodilla", "cadera"]),

    # ================= EXTENSIÓN / FLEXIÓN DE RODILLA (7) =================
    _ex("Extensión de rodilla en máquina", ["leg extension", "extensiones de cuádriceps"],
        "cuadriceps", [], "knee_extension", ["maquina"], 1,
        "Eje de la máquina alineado con la rodilla, extiende y aprieta 1 s.",
        "Único ejercicio que aísla el recto femoral en extensión: tensión pico en acortamiento.",
        ["rodilla"]),
    _ex("Extensión de rodilla unilateral", ["leg extension a una pierna"],
        "cuadriceps", [], "knee_extension", ["maquina"], 1,
        "Una pierna cada vez, mismo ajuste; controla la bajada 2-3 s.",
        "Corrige asimetrías de cuádriceps con el mismo aislamiento guiado.",
        ["rodilla"]),
    _ex("Curl femoral tumbado", ["leg curl tumbado", "curl de piernas"],
        "isquios", ["gemelos"], "knee_flexion", ["maquina"], 1,
        "Cadera pegada al banco, flexiona sin levantar la pelvis.",
        "Aísla la flexión de rodilla: complementa al rumano (que carga la cadera).",
        []),
    _ex("Curl femoral sentado", ["seated leg curl"],
        "isquios", [], "knee_flexion", ["maquina"], 1,
        "Muslos fijados por el pad, flexiona en rango completo.",
        "Con la cadera flexionada el isquio trabaja más alargado: mayor estímulo distal.",
        []),
    _ex("Curl femoral de pie unilateral", ["standing leg curl"],
        "isquios", [], "knee_flexion", ["maquina", "polea"], 1,
        "Talón al glúteo con la cadera quieta, baja con control.",
        "Flexión unilateral que evidencia y corrige diferencias entre piernas.",
        []),
    _ex("Curl nórdico", ["nordic curl", "curl nórdico de isquios"],
        "isquios", [], "knee_flexion", ["peso_corporal", "maquina"], 3,
        "Tobillos fijados, déjate caer recto frenando con los isquios.",
        "Excéntrico supramáximo del isquio: protector frente a lesiones de carrera.",
        ["rodilla"]),
    _ex("Curl femoral con deslizadores", ["slider leg curl", "curl con toalla"],
        "isquios", ["gluteos", "core"], "knee_flexion", ["deslizadores", "peso_corporal"], 2,
        "En puente de glúteo, desliza los talones lejos y vuelve sin caer la cadera.",
        "Flexión de rodilla con cadera extendida en cadena cerrada: opción sin máquina.",
        []),

    # ================= GLÚTEO ABD/ADD (7) =================
    _ex("Patada de glúteo en polea", ["glute kickback", "patada trasera en polea"],
        "gluteos", ["isquios"], "hip_extension", ["polea"], 1,
        "Tobillera en polea baja, extiende la cadera atrás sin arquear la lumbar.",
        "Extensión unilateral con tensión constante en el rango final del glúteo.",
        []),
    _ex("Hip thrust en máquina", ["hip thrust machine"],
        "gluteos", ["isquios"], "hip_extension", ["maquina"], 1,
        "Ajusta el pad sobre la pelvis, extiende y bloquea arriba 1 s.",
        "Misma curva del hip thrust con montaje en segundos: facilita la progresión.",
        []),
    _ex("Abducción de cadera en máquina", ["hip abduction", "máquina de abductores"],
        "gluteos", [], "hip_abduction", ["maquina"], 1,
        "Torso ligeramente inclinado adelante, abre con pausa fuera.",
        "Aísla el glúteo medio: estabilidad de pelvis y forma lateral de la cadera.",
        []),
    _ex("Abducción de cadera con banda", ["clamshell con banda", "abducción con banda"],
        "gluteos", [], "hip_abduction", ["bandas"], 1,
        "Banda sobre las rodillas, separa contra la resistencia sin rotar la pelvis.",
        "Activación accesible del glúteo medio: ideal en calentamientos y en casa.",
        []),
    _ex("Frog pump", ["puente de glúteo con plantas juntas"],
        "gluteos", [], "hip_extension", ["peso_corporal", "mancuernas"], 1,
        "Plantas de los pies juntas, rodillas abiertas, eleva la pelvis apretando.",
        "La rotación externa pre-acorta el glúteo: gran sensación con poca carga.",
        []),
    _ex("Aducción de cadera en máquina", ["máquina de aductores", "hip adduction"],
        "aductores", [], "hip_adduction", ["maquina"], 1,
        "Junta las piernas con control y abre lento hasta estiramiento cómodo.",
        "Aísla los aductores: estabilidad de cadera y prevención en deportes con cambios de dirección.",
        ["cadera"]),
    _ex("Plancha Copenhagen", ["copenhagen plank", "plancha de aductores"],
        "aductores", ["core"], "hip_adduction", ["banco", "peso_corporal"], 3,
        "Pie superior apoyado en el banco, cuerpo en línea; empieza con rodilla apoyada.",
        "Aductor en isometría de alta tensión: estándar preventivo en deportes de campo.",
        ["cadera"]),

    # ================= GEMELO / TIBIAL (5) =================
    _ex("Elevación de talones de pie", ["calf raise de pie", "gemelos de pie"],
        "gemelos", [], "plantar_flexion", ["maquina", "multipower", "mancuernas"], 1,
        "Estiramiento completo abajo 1 s, sube a máxima puntilla sin rebotar.",
        "Con rodilla extendida trabaja el gastrocnemio; la pausa abajo elimina el rebote del Aquiles.",
        ["tobillo"]),
    _ex("Elevación de talones sentado", ["calf raise sentado", "gemelos sentado"],
        "gemelos", [], "plantar_flexion", ["maquina"], 1,
        "Pad sobre las rodillas, mismo rango completo con pausa abajo.",
        "La rodilla flexionada desactiva el gastrocnemio y aísla el sóleo.",
        []),
    _ex("Elevación de talones en prensa", ["gemelos en prensa"],
        "gemelos", [], "plantar_flexion", ["maquina"], 1,
        "Punteras en el borde de la plataforma, rango completo controlado.",
        "Permite cargar la flexión plantar con la espalda totalmente apoyada.",
        []),
    _ex("Elevación de talones unilateral con mancuerna", ["gemelo a una pierna"],
        "gemelos", [], "plantar_flexion", ["mancuernas", "peso_corporal"], 1,
        "En un escalón, mancuerna del mismo lado, rango completo lento.",
        "El trabajo unilateral con déficit maximiza rango y corrige asimetrías.",
        ["tobillo"]),
    _ex("Elevación de talones tipo burro", ["donkey calf raise", "gemelo burro"],
        "gemelos", [], "plantar_flexion", ["maquina", "peso_corporal"], 2,
        "Torso flexionado a 90° con apoyo, carga sobre la pelvis, rango completo.",
        "La cadera flexionada pre-estira el gastrocnemio: mayor tensión en alargamiento.",
        ["lumbar"]),
    _ex("Elevación de puntas (tibial anterior)", ["tibialis raise", "flexión dorsal con banda"],
        "gemelos", [], "dorsiflexion", ["bandas", "peso_corporal"], 1,
        "Talones apoyados, sube las punteras hacia ti con pausa arriba.",
        "Fortalece el tibial anterior: equilibrio articular del tobillo y prevención en carrera.",
        []),

    # ================= FLEXIÓN DE CODO (9) =================
    _ex("Curl de bíceps con barra", ["barbell curl", "curl con barra recta"],
        "biceps", ["antebrazos"], "elbow_flexion", ["barra"], 1,
        "Codos pegados al torso, sube sin balanceo y baja en 2-3 s.",
        "Flexión con supinación fija: la barra recta permite la mayor carga del patrón.",
        ["muneca", "codo"]),
    _ex("Curl de bíceps con barra EZ", ["curl ez", "curl con barra z"],
        "biceps", ["antebrazos"], "elbow_flexion", ["barra_ez"], 1,
        "Agarre en las inclinaciones de la barra, codos fijos al costado.",
        "La semipronación de la EZ reduce el estrés de muñeca conservando el estímulo.",
        []),
    _ex("Curl alterno con mancuernas", ["curl alterno", "dumbbell curl"],
        "biceps", ["antebrazos"], "elbow_flexion", ["mancuernas"], 1,
        "Supina la muñeca mientras subes; alterna sin balancear el torso.",
        "La supinación activa durante la flexión es la doble función del bíceps.",
        []),
    _ex("Curl martillo", ["hammer curl", "curl neutro"],
        "biceps", ["antebrazos"], "elbow_flexion", ["mancuernas"], 1,
        "Palmas enfrentadas todo el recorrido, codos quietos.",
        "El agarre neutro carga braquial y braquiorradial: grosor total del brazo.",
        []),
    _ex("Curl inclinado con mancuernas", ["incline curl", "curl en banco inclinado"],
        "biceps", [], "elbow_flexion", ["mancuernas", "banco"], 2,
        "Respaldo a 45-60°, brazos colgando atrás, sube sin adelantar los codos.",
        "El hombro extendido alarga la cabeza larga: máxima tensión en estiramiento.",
        ["hombro"]),
    _ex("Curl predicador", ["preacher curl", "curl scott", "curl en banco scott"],
        "biceps", [], "elbow_flexion", ["barra_ez", "banco_scott", "maquina"], 1,
        "Axilas sobre el pad, extiende casi del todo abajo sin rebotar.",
        "El apoyo elimina el balanceo y castiga el rango de estiramiento del bíceps.",
        ["codo"]),
    _ex("Curl bayesian en polea", ["bayesian curl", "curl en polea tras el cuerpo"],
        "biceps", [], "elbow_flexion", ["polea"], 2,
        "De espaldas a la polea baja, brazo atrás, flexiona sin mover el codo.",
        "La polea desde atrás mantiene tensión máxima con el bíceps alargado.",
        []),
    _ex("Curl araña", ["spider curl"],
        "biceps", [], "elbow_flexion", ["mancuernas", "barra_ez", "banco"], 2,
        "Pecho apoyado en banco inclinado, brazos verticales colgando, sube estricto.",
        "Brazo perpendicular al suelo: tensión pico en el acortamiento completo.",
        []),
    _ex("Curl invertido con barra EZ", ["reverse curl", "curl agarre prono"],
        "antebrazos", ["biceps"], "elbow_flexion", ["barra_ez"], 1,
        "Agarre prono, muñecas firmes, sube sin que los nudillos caigan.",
        "El agarre prono prioriza braquiorradial y extensores: antebrazo y codo sanos.",
        ["muneca"]),

    # ================= EXTENSIÓN DE CODO (10) =================
    _ex("Press francés con barra EZ", ["skullcrusher", "rompecráneos", "extensión tumbado"],
        "triceps", [], "elbow_extension", ["barra_ez", "banco"], 2,
        "Baja la barra hacia la frente o detrás con codos estables, sin abrirlos.",
        "Extensión con hombro semiflexionado: carga la cabeza larga en alargamiento.",
        ["codo"]),
    _ex("Extensión de tríceps en polea con cuerda", ["pushdown con cuerda", "jalones de tríceps"],
        "triceps", [], "elbow_extension", ["polea"], 1,
        "Codos pegados, separa la cuerda abajo y bloquea 1 s.",
        "La cuerda permite extensión completa con pronación final: pico de contracción.",
        []),
    _ex("Extensión de tríceps en polea con barra", ["pushdown con barra"],
        "triceps", [], "elbow_extension", ["polea"], 1,
        "Barra recta o EZ, empuja hasta el bloqueo sin inclinarte sobre ella.",
        "La barra estandariza el gesto y admite más carga que la cuerda.",
        ["codo"]),
    _ex("Extensión de tríceps sobre la cabeza en polea", ["overhead cable extension"],
        "triceps", [], "elbow_extension", ["polea"], 2,
        "De espaldas a la polea, codos al cielo, extiende adelante-arriba.",
        "El hombro flexionado alarga la cabeza larga: el mejor estímulo de estiramiento.",
        ["hombro", "codo"]),
    _ex("Extensión de tríceps sobre la cabeza con mancuerna", ["extensión trasnuca", "french press de pie"],
        "triceps", [], "elbow_extension", ["mancuernas"], 1,
        "Mancuerna a dos manos tras la nuca, codos cerrados apuntando arriba.",
        "Versión libre del estiramiento de cabeza larga, viable en casa.",
        ["hombro", "codo"]),
    _ex("Patada de tríceps con mancuerna", ["kickback"],
        "triceps", [], "elbow_extension", ["mancuernas"], 1,
        "Torso inclinado, húmero paralelo al suelo fijo, extiende hasta bloquear.",
        "Tensión pico en el acortamiento total: complementa los gestos de estiramiento.",
        []),
    _ex("Fondos entre bancos", ["bench dips", "fondos de tríceps en banco"],
        "triceps", ["hombros", "pecho"], "elbow_extension", ["banco", "peso_corporal"], 1,
        "Manos al borde del banco, baja con el torso cerca de él.",
        "Cadena cerrada accesible; cuidado con bajar más allá del confort del hombro.",
        ["hombro"]),
    _ex("Press banca agarre cerrado", ["close grip bench press", "press cerrado"],
        "triceps", ["pecho", "hombros"], "elbow_extension", ["barra", "banco", "rack"], 2,
        "Agarre al ancho de hombros, codos cerca del torso, toca el pecho bajo.",
        "El press pesado del tríceps: el agarre estrecho desplaza la demanda del pectoral.",
        ["muneca", "hombro"]),
    _ex("JM press", ["jm press"],
        "triceps", ["pecho"], "elbow_extension", ["barra", "banco", "rack", "multipower"], 3,
        "Híbrido entre press cerrado y francés: baja la barra hacia la barbilla.",
        "Sobrecarga la extensión de codo con más estabilidad que el francés puro.",
        ["codo"]),
    _ex("Fondos en paralelas (énfasis tríceps)", ["dips tríceps"],
        "triceps", ["pecho", "hombros"], "elbow_extension", ["paralelas"], 2,
        "Torso vertical y codos cerrados; rango hasta codo a 90° aprox.",
        "La verticalidad concentra la extensión de codo con el peso corporal.",
        ["hombro"]),

    # ================= HOMBRO LATERAL / FRONTAL / ROTACIÓN (9) =================
    _ex("Elevaciones laterales con mancuernas", ["lateral raises", "vuelos laterales"],
        "hombros", [], "shoulder_abduction", ["mancuernas"], 1,
        "Sube hasta la horizontal con codos semiflexionados, baja en 2-3 s.",
        "Abducción pura: el deltoides medio es el responsable de la anchura de hombros.",
        ["hombro"]),
    _ex("Elevación lateral en polea unilateral", ["lateral raise en polea"],
        "hombros", [], "shoulder_abduction", ["polea"], 1,
        "Polea baja por detrás del cuerpo, sube en arco hasta la horizontal.",
        "La polea da tensión desde el primer grado, donde la mancuerna no pesa.",
        []),
    _ex("Elevaciones laterales en máquina", ["lateral raise machine"],
        "hombros", [], "shoulder_abduction", ["maquina"], 1,
        "Pads en los codos, abre hasta la horizontal sin encoger el cuello.",
        "Trayectoria guiada que permite llegar al fallo sin que la técnica se degrade.",
        []),
    _ex("Elevaciones laterales sentado", ["seated lateral raise"],
        "hombros", [], "shoulder_abduction", ["mancuernas", "banco"], 1,
        "Sentado para eliminar todo impulso, mismas pautas que de pie.",
        "Quitar el balanceo de cadera convierte cada kilo en estímulo real del deltoides.",
        ["hombro"]),
    _ex("Remo al mentón con barra EZ", ["upright row", "remo vertical"],
        "hombros", ["trapecio", "biceps"], "shoulder_abduction", ["barra_ez", "polea"], 2,
        "Agarre algo más ancho que los hombros, sube hasta el pecho, no más.",
        "Abducción con carga axial; el agarre ancho y rango medio protegen el manguito.",
        ["hombro"]),
    _ex("Elevación lateral con banda", ["lateral raise con banda"],
        "hombros", [], "shoulder_abduction", ["bandas"], 1,
        "Pisa la banda, sube hasta la horizontal con control.",
        "La resistencia creciente de la banda acentúa el final del recorrido.",
        []),
    _ex("Elevaciones frontales con mancuernas", ["front raises", "vuelos frontales"],
        "hombros", [], "shoulder_flexion", ["mancuernas", "disco"], 1,
        "Sube al frente hasta la horizontal, alternando o a la vez, sin balanceo.",
        "Flexión pura de hombro: accesorio del deltoides anterior cuando hay poco press.",
        ["hombro"]),
    _ex("Elevación frontal con disco", ["front raise con disco"],
        "hombros", [], "shoulder_flexion", ["disco"], 1,
        "Disco a dos manos, sube hasta los ojos y baja lento.",
        "El agarre a dos manos estabiliza el gesto y permite pausas arriba.",
        []),
    _ex("Rotación externa de hombro en polea", ["external rotation", "rotación externa con polea"],
        "hombros", [], "shoulder_external_rotation", ["polea", "bandas"], 1,
        "Codo pegado al costado a 90°, rota el antebrazo hacia fuera.",
        "Fortalece el manguito rotador: equilibrio articular y prevención en pressers.",
        []),

    # ================= TRAPECIO (3) =================
    _ex("Encogimientos con barra", ["shrugs con barra", "encogimientos de hombros"],
        "trapecio", ["antebrazos"], "scapular_elevation", ["barra"], 1,
        "Sube los hombros hacia las orejas con pausa de 1 s, sin rotar.",
        "Elevación escapular pura: el trapecio superior responde a cargas altas y pausas.",
        ["cuello"]),
    _ex("Encogimientos con mancuernas", ["shrugs con mancuernas"],
        "trapecio", ["antebrazos"], "scapular_elevation", ["mancuernas"], 1,
        "Mancuernas a los costados, mismo gesto con rango algo mayor.",
        "El agarre neutro lateral permite un recorrido más natural que la barra.",
        ["cuello"]),
    _ex("Encogimientos en multipower", ["shrugs en smith"],
        "trapecio", ["antebrazos"], "scapular_elevation", ["multipower"], 1,
        "Barra guiada por delante o detrás, pausa arriba en cada repetición.",
        "La guía elimina el equilibrio y deja toda la atención en la elevación escapular.",
        ["cuello"]),

    # ================= ANTEBRAZO (2) =================
    _ex("Curl de muñeca con barra", ["wrist curl", "flexión de muñeca"],
        "antebrazos", [], "elbow_flexion", ["barra", "mancuernas", "banco"], 1,
        "Antebrazos apoyados, deja rodar la barra a los dedos y flexiona.",
        "Flexores del antebrazo: agarre más fuerte para tirones y pesos muertos.",
        ["muneca"]),
    _ex("Extensión de muñeca con barra", ["reverse wrist curl", "extensión de muñeca"],
        "antebrazos", [], "elbow_extension", ["barra", "mancuernas", "banco"], 1,
        "Palmas hacia abajo apoyadas, extiende las muñecas con poco peso.",
        "Extensores del antebrazo: equilibran a los flexores y protegen el codo.",
        ["muneca", "codo"]),

    # ================= CORE ANTI-EXTENSIÓN (6) =================
    _ex("Plancha abdominal", ["plank", "plancha frontal"],
        "core", ["hombros"], "core_anti_extension", ["peso_corporal"], 1,
        "Antebrazos bajo los hombros, pelvis neutra, glúteo y abdomen firmes.",
        "Isometría anti-extensión: el core resiste que la gravedad arquee la lumbar.",
        []),
    _ex("Plancha con lastre", ["weighted plank"],
        "core", ["hombros"], "core_anti_extension", ["peso_corporal", "disco", "lastre"], 2,
        "Disco centrado en la espalda baja-media, misma postura impecable.",
        "Progresión de intensidad de la plancha sin alargar series eternas.",
        ["lumbar"]),
    _ex("Rueda abdominal", ["ab wheel", "rodillo abdominal"],
        "core", ["hombros", "espalda"], "core_anti_extension", ["maquina", "peso_corporal"], 3,
        "Desde rodillas, rueda adelante solo hasta donde la lumbar no se arquee.",
        "Anti-extensión dinámica de alta demanda: el rango es la variable de progresión.",
        ["lumbar", "hombro"]),
    _ex("Dead bug", ["bicho muerto"],
        "core", [], "core_anti_extension", ["peso_corporal"], 1,
        "Lumbar pegada al suelo, extiende brazo y pierna contrarios lento.",
        "Enseña a disociar extremidades con pelvis estable: base de control lumbopélvico.",
        []),
    _ex("Body saw", ["sierra en plancha"],
        "core", ["hombros"], "core_anti_extension", ["deslizadores", "peso_corporal"], 2,
        "En plancha de antebrazos, desliza el cuerpo atrás y adelante pocos cm.",
        "El desplazamiento alarga la palanca: intensifica la plancha sin añadir carga.",
        ["hombro"]),
    _ex("Plancha con brazos extendidos", ["long lever plank", "plancha extendida"],
        "core", ["hombros"], "core_anti_extension", ["peso_corporal"], 2,
        "Manos más adelantadas que los hombros, cuerpo en línea férrea.",
        "Adelantar los apoyos multiplica el torque anti-extensión sobre el abdomen.",
        ["hombro", "muneca"]),

    # ================= CORE ANTI-ROTACIÓN (5) =================
    _ex("Press Pallof", ["pallof press", "antirrotación en polea"],
        "core", [], "core_anti_rotation", ["polea", "bandas"], 1,
        "Perpendicular a la polea, extiende los brazos al frente sin girar el torso.",
        "Anti-rotación pura: los oblicuos resisten el giro en lugar de producirlo.",
        []),
    _ex("Plancha lateral", ["side plank"],
        "core", ["hombros", "gluteos"], "core_anti_rotation", ["peso_corporal"], 1,
        "Codo bajo el hombro, cadera alta en línea, sin hundirte.",
        "Isometría anti-flexión lateral: oblicuos y glúteo medio en cadena.",
        ["hombro"]),
    _ex("Bird dog", ["perro de caza", "cuadrupedia alterna"],
        "core", ["gluteos", "espalda"], "core_anti_rotation", ["peso_corporal"], 1,
        "En cuadrupedia, extiende brazo y pierna contrarios sin bascular la pelvis.",
        "Estabilidad rotacional con extensión de cadera: control lumbopélvico básico.",
        []),
    _ex("Leñador en polea", ["cable chop", "woodchopper"],
        "core", ["hombros"], "core_anti_rotation", ["polea"], 2,
        "De arriba a abajo en diagonal con brazos casi rectos, pivota desde la cadera.",
        "El torso transmite el giro de la cadera: patrón rotacional con control.",
        ["lumbar"]),
    _ex("Paseo del granjero unilateral", ["suitcase carry", "paseo de la maleta"],
        "core", ["antebrazos", "trapecio"], "core_anti_rotation", ["mancuernas", "kettlebell"], 1,
        "Carga pesada en una mano, camina erguido sin inclinarte hacia ella.",
        "Anti-flexión lateral dinámica más agarre: core funcional con transferencia real.",
        []),

    # ================= CORE FLEXIÓN (6) =================
    _ex("Crunch en polea alta", ["cable crunch", "crunch de rodillas en polea"],
        "core", [], "core_flexion", ["polea"], 1,
        "De rodillas, cuerda junto a la cabeza, flexiona el torso llevando codos a muslos.",
        "Flexión de columna con carga regulable: el recto abdominal como motor principal.",
        ["lumbar"]),
    _ex("Crunch en máquina", ["machine crunch", "abdominal en máquina"],
        "core", [], "core_flexion", ["maquina"], 1,
        "Flexiona acercando costillas a pelvis y vuelve con control.",
        "Resistencia guiada y progresiva para hipertrofiar el recto abdominal.",
        []),
    _ex("Elevaciones de piernas colgado", ["hanging leg raise", "elevación de piernas en barra"],
        "core", ["antebrazos"], "core_flexion", ["barra_dominadas"], 3,
        "Colgado, sube las piernas rectas curvando la pelvis al final, sin balanceo.",
        "La retroversión final de la pelvis es lo que activa de verdad el abdomen bajo.",
        ["hombro"]),
    _ex("Elevaciones de rodillas colgado", ["hanging knee raise"],
        "core", ["antebrazos"], "core_flexion", ["barra_dominadas"], 1,
        "Rodillas al pecho enrollando la pelvis, baja sin balanceo.",
        "Versión accesible de la elevación colgado con la misma clave pélvica.",
        []),
    _ex("Crunch en banco declinado", ["decline crunch", "abdominales en banco declinado"],
        "core", [], "core_flexion", ["banco", "disco"], 1,
        "Baja solo hasta medio recorrido y sube enrollando vértebra a vértebra.",
        "El declive aumenta el rango bajo carga; lastrable con disco al pecho.",
        ["lumbar", "cuello"]),
    _ex("Crunch bicicleta", ["bicycle crunch"],
        "core", [], "core_flexion", ["peso_corporal"], 1,
        "Codo hacia rodilla contraria alternando, lento y sin tirar del cuello.",
        "Combina flexión y rotación: recto abdominal y oblicuos en un gesto.",
        ["cuello"]),
]

```


## `backend/app/seeds/run.py`

```python
"""Seed idempotente. Se ejecuta en cada arranque (entrypoint.sh):

1. Biblioteca de 150 ejercicios — solo si la tabla está vacía.
2. brand_config por defecto (H.1) — solo si no existe ninguna fila.
3. Usuarios admin desde ADMIN_x del .env — solo los que falten.

Uso manual: python -m app.seeds.run
"""

import sys

from sqlalchemy import func, select

from app.config import settings
from app.db import SessionLocal
from app.models import BrandConfig, Exercise, User
from app.security import hash_password
from app.seeds.exercises_data import EXERCISES


def seed_exercises(db) -> int:
    count = db.scalar(select(func.count()).select_from(Exercise))
    if count:
        return 0
    db.add_all(Exercise(**data) for data in EXERCISES)
    db.commit()
    return len(EXERCISES)


def seed_brand(db) -> bool:
    if db.scalar(select(func.count()).select_from(BrandConfig)):
        return False
    db.add(BrandConfig())  # defaults premium de H.1 definidos en el modelo
    db.commit()
    return True


def seed_admins(db) -> int:
    created = 0
    for username, password in (
        (settings.admin_1_user, settings.admin_1_pass),
        (settings.admin_2_user, settings.admin_2_pass),
    ):
        if not username or not password:
            continue
        exists = db.scalar(select(func.count()).where(User.username == username))
        if exists:
            continue
        db.add(User(username=username, password_hash=hash_password(password)))
        created += 1
    db.commit()
    return created


def main() -> None:
    db = SessionLocal()
    try:
        n_ex = seed_exercises(db)
        brand = seed_brand(db)
        n_admins = seed_admins(db)
        print(
            f"[seed] ejercicios: {n_ex or 'ya existían'} · "
            f"brand: {'creada' if brand else 'ya existía'} · "
            f"admins creados: {n_admins}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

```


## `backend/app/services/__init__.py`

```python

```


## `backend/app/services/ai/__init__.py`

```python

```


## `backend/app/services/ai/client.py`

```python
"""Cliente de IA — capa fina sobre la API de Anthropic (PARTE D).

Responsabilidades:
- Llamar al modelo (HEAVY para generación/visión, LIGHT para parseo/matching).
- Forzar salida JSON, parsearla de forma robusta (tolera ```json ... ``` por si
  el modelo se desvía) y validarla contra un schema Pydantic.
- Retry 1 con el error de validación inyectado ("tu JSON falló en X, corrígelo").
- Segundo fallo → AIGenerationError, que el orquestador traduce a estado de
  error recuperable + notificación al coach.

Parámetros fijos (D.2): temperatura 0.3, max_tokens generoso.

El cliente NO conoce el dominio (nutrición/entrenamiento): solo recibe system
prompt, user prompt y schema. El conocimiento experto vive en prompts.py y la
orquestación en generator.py.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

TEMPERATURE = 0.3
# Generoso: el banco de comidas (4 slots × 7 opciones con ingredientes/macros) y el
# núcleo del plan son salidas grandes; 8000 truncaba el JSON → fallo de parseo.
MAX_TOKENS = 16000

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AIGenerationError(RuntimeError):
    """La IA no produjo JSON válido conforme al schema tras el reintento."""

    def __init__(self, message: str, last_error: str | None = None):
        super().__init__(message)
        self.last_error = last_error


def _translate_api_error(exc: Exception) -> "AIGenerationError | None":
    """Traduce un error de la API de Anthropic (sin crédito, rate limit, clave
    inválida, etc.) a AIGenerationError con mensaje legible, para que el endpoint
    devuelva un 502 claro en vez de un 500 opaco. Devuelve None si no es un error
    de la API (en ese caso, se deja propagar)."""
    try:
        from anthropic import APIError
    except Exception:
        return None
    if isinstance(exc, APIError):
        msg = getattr(exc, "message", None) or str(exc)
        return AIGenerationError(f"La API de Anthropic devolvió un error: {msg}")
    return None


def _extract_json(text: str) -> str:
    """Aísla el JSON aunque venga envuelto en markdown o con texto alrededor."""
    text = text.strip()
    fenced = _JSON_FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    # Primer { hasta el último } — defensa ante preámbulos accidentales.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class AIClient:
    """Wrapper con reintento y validación. Inyectable/mockeable en tests."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.anthropic_api_key
        self._client = None  # perezoso: no instanciar SDK si se usa un mock

    def _anthropic(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def _raw_call(self, *, model: str, system: str, user: str) -> str:
        """Una llamada cruda al modelo. Sobrescribible en tests."""
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def _raw_call_with_pdf(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes
    ) -> str:
        """Una llamada al modelo incluyendo un PDF como documento adjunto.

        Usa el bloque `document` de la API de Anthropic (lectura nativa de PDF).
        Sobrescribible en tests.
        """
        import base64

        b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        try:
            resp = self._anthropic().messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user},
                    ],
                }],
            )
        except Exception as exc:
            translated = _translate_api_error(exc)
            if translated:
                raise translated from exc
            raise
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )

    def read_pdf_json(
        self, *, model: str, system: str, user: str, pdf_bytes: bytes, schema: type[T]
    ) -> T:
        """Lee un PDF, extrae datos y los valida contra el esquema. Reintenta una vez."""
        last_error: str | None = None
        attempt_user = user
        for _ in range(2):
            raw = self._raw_call_with_pdf(
                model=model, system=system, user=attempt_user, pdf_bytes=pdf_bytes
            )
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )
        raise AIGenerationError(
            "La IA no extrajo un JSON válido del PDF tras el reintento", last_error
        )

    def generate_json(
        self, *, model: str, system: str, user: str, schema: type[T]
    ) -> T:
        """Genera, parsea y valida. Reintenta UNA vez con el error inyectado."""
        last_error: str | None = None
        attempt_user = user

        for attempt in range(2):
            raw = self._raw_call(model=model, system=system, user=attempt_user)
            try:
                data = json.loads(_extract_json(raw))
            except json.JSONDecodeError as exc:
                last_error = f"JSON mal formado: {exc}"
            else:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    last_error = _summarize_validation_error(exc)

            # Preparar reintento con el error concreto inyectado.
            attempt_user = (
                f"{user}\n\n--- CORRECCIÓN REQUERIDA ---\n"
                f"Tu respuesta anterior falló la validación: {last_error}\n"
                "Devuelve de nuevo SOLO el JSON corregido, sin texto adicional."
            )

        raise AIGenerationError(
            "La IA no devolvió un JSON válido tras el reintento", last_error
        )


def _summarize_validation_error(exc: ValidationError) -> str:
    """Resumen compacto y accionable de los errores de Pydantic para el reintento."""
    parts = []
    for err in exc.errors()[:6]:
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return " | ".join(parts)

```


## `backend/app/services/ai/extraction.py`

```python
"""Extracción de la anamnesis desde el PDF con IA (lectura nativa).

La IA lee el PDF oficial rellenado por el cliente y extrae:
- Los campos ESTRUCTURADOS que el sistema necesita para calcular y generar
  (sexo, antropometría, objetivo, nivel, entrenamiento, dieta, preferencias).
- Un ANÁLISIS cualitativo en profundidad (lesiones, hábitos, sueño, estrés,
  conducta alimentaria, contexto) que enriquece la planificación.

El coach revisa los campos extraídos antes de generar (seguridad): la IA puede
malinterpretar texto manuscrito o ambiguo, y un error en peso o lesiones sería
grave. Por eso esto solo PRE-RELLENA; la decisión final es del coach.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class MealSlot(BaseModel):
    """Toma de comida. Los campos son opcionales en la extracción porque la IA a
    veces omite slot/name; se autocompletan en AnamnesisExtraction para no
    descartar toda la lectura por un detalle de formato."""

    slot: int | None = None
    name: str | None = None
    time: str | None = None  # "HH:MM"


class AnamnesisExtraction(BaseModel):
    """Datos extraídos del PDF oficial de anamnesis (DQ). Campos opcionales: si
    la IA no los encuentra, los deja en null (o lista/texto vacío) y el coach
    los completa.

    El esquema refleja las secciones del PDF: los campos ESTRUCTURADOS que el
    backend necesita para calcular y filtrar, más un resumen por SECCIÓN
    cualitativa (cada uno mapea a una columna de la ficha del cliente) y una
    síntesis final (deep_analysis) para personalizar el plan.
    """

    # --- Datos personales y antropometría (PDF: "Datos personales" / "Antropometría inicial") ---
    sex: str | None = Field(None, description="male|female (mapea Hombre→male, Mujer→female)")
    birth_date: date | None = Field(None, description="Fecha de nacimiento YYYY-MM-DD")
    height_cm: float | None = None
    start_weight_kg: float | None = Field(None, description="Peso actual (kg)")
    body_fat_pct: float | None = None

    # --- Objetivo (PDF: "Motivo y objetivos") ---
    goal_type: str | None = Field(None, description="fat_loss|muscle_gain|recomp")
    goal_weight_kg: float | None = None

    # --- Entrenamiento (PDF: "Experiencia con pesas" / "Entrenamiento actual y preferencias") ---
    level: str | None = Field(None, description="beginner|intermediate|advanced")
    training_days: int | None = Field(None, description="Días que puede entrenar por semana")
    session_max_min: int | None = Field(None, description="Duración media/máxima de sesión en minutos")
    training_place: str | None = Field(None, description="gym|home|outdoor")
    equipment: list[str] = Field(
        default_factory=list,
        description=(
            "Material disponible SOLO si entrena en casa/exterior (mancuernas, "
            "barra, banco, jaula, gomas…). Vacío si entrena en gimnasio."
        ),
    )

    # --- Dieta (PDF: "Hábitos dietéticos" / "Preferencias y aversiones") ---
    diet_mode: str | None = Field(None, description="flexible_7|strict")
    meals_per_day: int | None = None
    meal_schedule: list[MealSlot] = Field(default_factory=list)
    food_likes: list[str] = Field(default_factory=list)
    food_dislikes: list[str] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)

    # --- Resúmenes por sección cualitativa (texto libre; cada uno → una columna) ---
    injuries_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historial de lesiones y movilidad': resume TODAS las lesiones/"
            "molestias con zona, lado, si está resuelto y qué movimientos evitar. "
            "Crítico para la seguridad del entrenamiento."
        ),
    )
    medical_notes: str | None = Field(
        None,
        description=(
            "PDF 'Historia clínica' + 'Salud digestiva y hormonal' + 'Salud "
            "femenina': patologías, antecedentes familiares, cirugías, "
            "intolerancias, tabaco/alcohol/otras sustancias, analítica reciente, "
            "salud digestiva (deposiciones, Bristol, síntomas) y, si aplica, "
            "ciclo menstrual/embarazos/menopausia. Resume lo relevante."
        ),
    )
    medication_notes: str | None = Field(
        None,
        description=(
            "PDF 'Medicación actual' + 'Anticonceptivos hormonales': nombre, "
            "dosis y frecuencia. null si no toma nada."
        ),
    )
    current_supplements: str | None = Field(
        None,
        description=(
            "PDF 'Suplementación': suplementos actuales con dosis y momento del "
            "día. null si no toma nada."
        ),
    )
    sport_history: str | None = Field(
        None,
        description=(
            "PDF 'Experiencia con pesas' + 'Otros deportes': años entrenando, "
            "nivel/técnica de los básicos, métodos/rutinas seguidas, y otros "
            "deportes recreativos con su frecuencia semanal."
        ),
    )
    lifestyle_notes: str | None = Field(
        None,
        description=(
            "PDF 'Motivo y objetivos' (corto/largo plazo, qué funcionó o no, "
            "motivación), 'Logística y entorno alimentario', 'Comida emocional', "
            "'Hidratación', 'Tu trabajo y tu día a día', 'Sueño y recuperación', "
            "'Estrés y energía' y la auto-evaluación final. Resume hábitos, "
            "sueño, estrés, conducta alimentaria, logística y contexto."
        ),
    )

    @field_validator("meal_schedule")
    @classmethod
    def _normalize_meal_schedule(cls, v: list[MealSlot]) -> list[MealSlot]:
        """Autocompleta slot (1,2,3…) y name si la IA los omitió, para que la
        ficha quede usable y no se pierda la extracción entera."""
        _default_names = {1: "Desayuno", 2: "Comida", 3: "Merienda", 4: "Cena"}
        out: list[MealSlot] = []
        for i, m in enumerate(v, start=1):
            slot = m.slot if m.slot is not None else i
            name = m.name or _default_names.get(slot, f"Toma {slot}")
            out.append(MealSlot(slot=slot, name=name, time=m.time or ""))
        return out

    # --- Síntesis final para personalizar el plan ---
    deep_analysis: str | None = Field(
        None,
        description=(
            "Síntesis ejecutiva (4-8 frases) con lo MÁS relevante para "
            "personalizar el plan: cruza objetivo, lesiones, hábitos, sueño, "
            "estrés, conducta alimentaria y qué ha funcionado o no en el pasado."
        ),
    )


_EXTRACTION_SYSTEM = """Eres un dietista-entrenador experto leyendo la ficha de \
ANAMNESIS oficial (marca DQ) que un cliente ha rellenado a mano. Tu tarea es EXTRAER \
toda la información del documento de forma fiel y estructurada, sin inventar nada.

REGLA DE ORO: si un dato no aparece, está en blanco o pone "no aplica", déjalo en null \
(o lista/texto vacío). NUNCA inventes datos: un error en peso, lesiones o medicación \
sería grave. El coach revisará todo antes de generar el plan. MAPEAR o INFERIR un valor \
a partir de lo que el cliente escribió NO es inventar; es obligatorio.

CAMPOS ESTRUCTURADOS OBLIGATORIOS — recórrelos UNO A UNO y rellénalos SIEMPRE que el dato \
aparezca en CUALQUIER parte del documento. NO dejes en null un campo cuyo dato esté presente:
  · birth_date ← "Fecha de nacimiento": convierte DD/MM/AAAA a YYYY-MM-DD (12/03/1990 → 1990-03-12).
  · sex ← "Sexo biológico": Hombre→"male", Mujer→"female" (Otro→null).
  · height_cm ← "Altura"; start_weight_kg ← "Peso actual"; goal_weight_kg ← "Peso objetivo".
  · goal_type ← "Motivo y objetivos" (NO hay casilla: INFIÉRELO del texto): perder grasa/definir/\
adelgazar→"fat_loss"; ganar músculo/volumen→"muscle_gain"; recomposición/mantener/tonificar→"recomp".
  · level ← "Nivel auto-percibido en sala de pesas": Principiante→"beginner"; Intermedio→\
"intermediate"; Avanzado→"advanced".
  · training_place ← "Dónde entrenas": Gimnasio/gym→"gym"; Casa→"home"; Exterior→"outdoor".
  · training_days ← cuenta los días marcados en "Días que puedes entrenar" (L M X J V S D).
  · session_max_min ← "Duración media de la sesión", en minutos.
  · diet_mode ← bloque de dieta: si menciona equivalencias/flexibilidad→"flexible_7"; si pide \
menú cerrado→"strict". Si no está claro, usa "flexible_7".
  · meals_per_day ← "¿Cuántas comidas haces al día?".
  · meal_schedule: deduce las tomas y sus horas. Cada toma DEBE ser un objeto con \
"slot" (1,2,3…), "name" ("Desayuno","Comida","Merienda","Cena"…) y "time" ("HH:MM"). \
Si no hay horas exactas, propón horarios razonables coherentes con el nº de comidas.
  · equipment: SOLO si entrena en casa/exterior, lista el material declarado (mancuernas, barra, \
banco, jaula, gomas, máquinas…). Si entrena en gimnasio, deja la lista vacía.
  · food_likes / food_dislikes / food_allergies: de "Preferencias y aversiones" e "Historia \
clínica" (alergias/intolerancias alimentarias). Listas de alimentos concretos.

RESÚMENES POR SECCIÓN (texto libre, fiel al PDF, en español; cada uno resume SU sección):
  · injuries_notes ← "Historial de lesiones y movilidad": cada lesión marcada con zona, lado, \
si está resuelta y qué movimientos dan molestia. Crítico para la seguridad.
  · medical_notes ← "Historia clínica" + "Salud digestiva y hormonal" + "Salud femenina (si \
aplica)": patologías, antecedentes familiares, cirugías, intolerancias, tabaco/alcohol/otras \
sustancias, analítica reciente; deposiciones/Bristol/síntomas digestivos; y ciclo menstrual/\
embarazos/menopausia si aplica.
  · medication_notes ← "Medicación actual" + "Anticonceptivos hormonales": nombre, dosis, frecuencia.
  · current_supplements ← "Suplementación": suplementos actuales con dosis y momento del día.
  · sport_history ← "Experiencia con pesas" + "Otros deportes": años entrenando, comodidad con \
la técnica de los básicos, métodos/rutinas previas, y otros deportes recreativos y su frecuencia.
  · lifestyle_notes ← "Motivo y objetivos" (corto/largo plazo, qué funcionó o no, motivación/\
confianza), "Logística y entorno alimentario", "Comida emocional", "Hidratación", "Tu trabajo \
y tu día a día", "Sueño y recuperación", "Estrés y energía" y la auto-evaluación final.

SÍNTESIS:
  · deep_analysis: 4-8 frases con lo MÁS relevante para personalizar el plan, cruzando objetivo, \
lesiones, hábitos, sueño, estrés y conducta alimentaria. Concreto y accionable.

Devuelve SOLO un objeto JSON válido que cumpla el esquema. Sin texto adicional."""

_EXTRACTION_USER = """Lee la ficha de anamnesis adjunta (PDF oficial DQ, ~10 páginas) y \
extrae TODA la información en JSON según el esquema. Recorre el documento sección por \
sección y rellena tanto los campos estructurados (antropometría, objetivo, entrenamiento, \
dieta) como los resúmenes por sección (clínica, medicación, suplementos, deportes, lesiones, \
estilo de vida). Lo que no encuentres o esté en blanco, déjalo en null; no inventes datos."""


def extract_anamnesis_from_pdf(pdf_bytes: bytes, ai) -> AnamnesisExtraction:
    """Lee el PDF con la IA y devuelve los datos extraídos validados."""
    from app.config import settings

    return ai.read_pdf_json(
        model=settings.model_heavy,
        system=_EXTRACTION_SYSTEM,
        user=_EXTRACTION_USER,
        pdf_bytes=pdf_bytes,
        schema=AnamnesisExtraction,
    )

```


## `backend/app/services/ai/feedback.py`

```python
"""Análisis de feedback con IA (parte cualitativa del informe quincenal).

El backend calcula TODAS las métricas (peso, adherencia, e1RM, perímetros) en
services/metrics.py y se las entrega ya hechas. La IA SOLO redacta el análisis
en lenguaje natural y las recomendaciones, NUNCA recalcula números.

Salida validada contra `FeedbackAIOutput`. Campos con defaults: si la IA omite
alguno, no se descarta todo el informe (el coach revisa antes de enviarlo).
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import settings


class FeedbackAIOutput(BaseModel):
    """Texto cualitativo del feedback. El backend aporta los números."""

    natural_analysis: str = Field(
        default="",
        description="Análisis en lenguaje natural de cómo ha ido el período (peso, "
        "adherencia, energía, fuerza), cercano y honesto. 1-3 párrafos.",
    )
    changes_bullets: list[str] = Field(
        default_factory=list,
        description="Qué se va a cambiar en el plan y por qué. Máximo 5 bullets.",
    )
    answers: str | None = Field(
        default=None,
        description="Respuesta a las dudas que dejó el cliente al cerrar (si las hay).",
    )
    next_objectives: list[str] = Field(
        default_factory=list,
        description="2-4 objetivos concretos para las próximas 2 semanas.",
    )
    closing_message: str = Field(
        default="",
        description="Mensaje de cierre breve y motivador.",
    )
    ai_photo_analysis: str | None = Field(
        default=None,
        description="Análisis de la evolución visible en las fotos (solo si hay fotos).",
    )


_SYSTEM = """Eres el dietista-entrenador (marca DQ) redactando el FEEDBACK quincenal \
para tu cliente, en castellano, con tono cercano, honesto y motivador (sin adular).

REGLA CRÍTICA: NO calcules ni inventes números. El backend ya te entrega las métricas \
(cambio de peso, ritmo semanal, adherencia, energía/sueño, progresión de fuerza). \
Úsalas tal cual; tu trabajo es INTERPRETARLAS y dar recomendaciones accionables.

- natural_analysis: explica cómo ha ido el período cruzando peso, adherencia, energía/\
sueño/ánimo y fuerza. Reconoce lo bueno y señala con tacto lo mejorable. 1-3 párrafos.
- changes_bullets: máximo 5 cambios concretos para el plan y POR QUÉ (p. ej. "subo 100 \
kcal porque el ritmo de bajada es muy agresivo").
- answers: responde a las dudas del cliente si las dejó; si no, déjalo en null.
- next_objectives: 2-4 objetivos claros y medibles para las próximas 2 semanas.
- closing_message: 1-2 frases de cierre motivadoras.
- ai_photo_analysis: SOLO si te indican que hay fotos; describe la evolución visible \
de forma prudente. Si no hay fotos, déjalo en null.

Devuelve SOLO un objeto JSON válido conforme al esquema. Sin texto adicional."""


def _user_prompt(payload: dict) -> str:
    return (
        "Redacta el feedback del período con estos DATOS YA CALCULADOS por el backend "
        "(no recalcules). Devuelve el JSON del esquema.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def generate_feedback_analysis(payload: dict, ai) -> FeedbackAIOutput:
    """Pide a la IA la parte cualitativa del feedback a partir de las métricas."""
    return ai.generate_json(
        model=settings.model_heavy,
        system=_SYSTEM,
        user=_user_prompt(payload),
        schema=FeedbackAIOutput,
    )

```


## `backend/app/services/ai/generator.py`

```python
"""Orquestación de la generación del plan mensual (PARTE B + D.2).

Tres llamadas encadenadas a la IA, con el backend haciendo el trabajo duro
entre medias:

  ①  núcleo del plan (nutrición + entrenamiento)
        → guardrails de nutrición y entrenamiento
  ②  banco de comidas según diet_mode (flexible_7 | strict)
        → guardrail ±5% por opción; re-pide SOLO las opciones que fallan
  ③  contenido educativo

El backend:
- calcula BMR/TDEE/kcal objetivo y se los entrega a la IA (nunca al revés),
- filtra la biblioteca de ejercicios ANTES de la llamada (solo aptos),
- revalida cada salida con guardrails sobre números reales,
- ensambla `PlanCoreOutput + MealsOutput + EducationOutput` para persistir.

`PlanGenerationError` encapsula cualquier fallo recuperable (la IA no convergió
o una salida violó guardrails de forma irreparable) → el caller marca estado de
error y notifica al coach.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.config import settings
from app.schemas.ai import (
    EducationOutput,
    MealsFlexibleOutput,
    MealsStrictOutput,
    PlanCoreOutput,
)
from app.services import guardrails as gr
from app.services.ai.client import AIClient, AIGenerationError
from app.services.ai.prompts import (
    system_prompt_education,
    system_prompt_full,
    system_prompt_meals,
)


class PlanGenerationError(RuntimeError):
    def __init__(self, message: str, flags: list[str] | None = None):
        super().__init__(message)
        self.flags = flags or []


@dataclass
class ClientContext:
    """Datos del cliente y métricas pre-calculadas que alimentan los prompts."""

    sex: str
    age: int
    height_cm: float
    weight_kg: float
    goal_type: str
    level: str
    training_days: int
    session_max_min: int
    training_place: str
    diet_mode: str
    meals_per_day: int
    meal_schedule: list[dict]
    food_allergies: list[str]
    food_dislikes: list[str]
    food_likes: list[str]
    contraindications: set[str]
    body_fat_pct: float | None
    # métricas calculadas por el backend (services/metrics.py)
    bmr: float
    tdee: float
    target_kcal: float
    energy_method: str
    # biblioteca ya filtrada: [{id, name, pattern, muscle, ...}]
    exercise_library: list[dict]
    # análisis cualitativo del coach/IA (lesiones, hábitos, contexto) — opcional
    deep_analysis: str | None = None
    notes: str = ""


@dataclass
class GeneratedPlan:
    core: PlanCoreOutput
    meals: MealsFlexibleOutput | MealsStrictOutput
    education: EducationOutput
    guardrail_flags: list[str]
    generated_by: str

    def to_persistable(self) -> tuple[dict, dict, dict, list[str]]:
        """(nutrition_json, training_json, education_json, guardrail_flags)."""
        nutrition = self.core.nutrition.model_dump()
        nutrition["meal_bank"] = self.meals.model_dump()
        return (
            nutrition,
            self.core.training.model_dump(),
            self.education.model_dump(),
            self.guardrail_flags,
        )


def _exercise_lookup(library: list[dict]) -> dict[int, dict]:
    return {ex["id"]: ex for ex in library}


def _slot_targets(core: PlanCoreOutput) -> dict[int, dict]:
    """{slot: {kcal, protein_g, carbs_g, fat_g}} desde el núcleo, para validar
    opciones de comida con ±5%."""
    return {
        m.slot: {
            "kcal": m.target.kcal, "protein_g": m.target.protein_g,
            "carbs_g": m.target.carbs_g, "fat_g": m.target.fat_g,
        }
        for m in core.nutrition.meals
    }


# ------------------------------------------------------ construcción prompts ----

def _client_block(ctx: ClientContext) -> str:
    return json.dumps(
        {
            "sexo": ctx.sex, "edad": ctx.age, "altura_cm": ctx.height_cm,
            "peso_kg": ctx.weight_kg, "porcentaje_graso": ctx.body_fat_pct,
            "objetivo": ctx.goal_type, "nivel": ctx.level,
            "dias_entrenamiento": ctx.training_days,
            "duracion_max_sesion_min": ctx.session_max_min,
            "lugar_entrenamiento": ctx.training_place,
            "modo_dieta": ctx.diet_mode, "num_comidas": ctx.meals_per_day,
            "horario_comidas": ctx.meal_schedule,
            "alergias": ctx.food_allergies, "aversiones": ctx.food_dislikes,
            "preferencias": ctx.food_likes,
            "lesiones_contraindicaciones": sorted(ctx.contraindications),
            "notas": ctx.notes,
            "metricas_backend": {
                "bmr": ctx.bmr, "tdee": ctx.tdee,
                "kcal_objetivo": ctx.target_kcal, "metodo": ctx.energy_method,
            },
        },
        ensure_ascii=False, indent=2,
    )


def _analysis_block(ctx: ClientContext) -> str:
    """Bloque opcional con el análisis cualitativo (lesiones, hábitos, contexto)."""
    if not ctx.deep_analysis:
        return ""
    return (
        "\nANÁLISIS EN PROFUNDIDAD DE LA ANAMNESIS (tenlo MUY en cuenta para "
        "personalizar dieta y entrenamiento: lesiones a respetar, hábitos, sueño, "
        "estrés, conducta alimentaria, logística y contexto):\n"
        f"{ctx.deep_analysis}\n"
    )


def _core_user_prompt(ctx: ClientContext) -> str:
    library = [
        {"id": e["id"], "nombre": e["canonical_name"],
         "patron": e["movement_pattern"], "musculo": e["muscle_primary"]}
        for e in ctx.exercise_library
    ]
    max_sets = max(
        1,
        (ctx.session_max_min - gr.SESSION_MINUTES_FIXED_OVERHEAD)
        // gr.SESSION_MINUTES_FORMULA_PER_SET,
    )
    return f"""Genera el NÚCLEO del plan mensual para este cliente.

DATOS DEL CLIENTE Y MÉTRICAS (ya calculadas por el backend, NO recalcules):
{_client_block(ctx)}
{_analysis_block(ctx)}
BIBLIOTECA DE EJERCICIOS DISPONIBLE (usa SOLO estos exercise_id):
{json.dumps(library, ensure_ascii=False)}

Devuelve un JSON con esta forma EXACTA (sin texto fuera del JSON). TODOS los campos de
cada objeto son OBLIGATORIOS salvo los marcados como (null si no aplica). No omitas NINGUNO:
- "nutrition": tdee_kcal, target_kcal, rationale, macros{{protein_g,carbs_g,fat_g}},
  meals[] (un objeto por comida del horario: slot, name, time, target{{kcal,protein_g,carbs_g,fat_g}}),
  supplements[] (cada uno con los 4 campos: name, dose, timing, evidence_note),
  flexibility_rules[] (strings), refeed_or_break (null si no aplica).
- "training": split_name, split_rationale,
  weekly_progression[] (EXACTAMENTE 4 objetos para las semanas 1,2,3,4; cada uno con los 5
  campos: week (1-4), intent (Base|Progresión|Pico|Deload), load_pct (número), rir_target, volume_note),
  sessions[] (day, name, warmup, exercises[], cooldown),
  cardio{{daily_steps, sessions[] (cada uno: type "liss"|"hiit", minutes, times_per_week, notes)}},
  deload_instructions.
  Cada ejercicio: exercise_id (de la biblioteca), sets, rep_range, rir, tempo, rest_sec,
  start_weight_hint_kg, progression_rule, technique_cue, biomech_cue.

RESTRICCIÓN DE DURACIÓN: la duración de cada sesión se estima como (total de series × \
{gr.SESSION_MINUTES_FORMULA_PER_SET} min) + {gr.SESSION_MINUTES_FIXED_OVERHEAD} min. El cliente \
declaró un máximo de {ctx.session_max_min} min/sesión, así que NO pongas más de {max_sets} series \
por sesión (sumando TODOS los ejercicios de esa sesión).

Respeta TODOS los guardrails. La suma de los targets de slot debe acercarse al target_kcal."""


def _meals_user_prompt(ctx: ClientContext, core: PlanCoreOutput) -> str:
    targets = _slot_targets(core)
    common = f"""Genera el BANCO DE COMIDAS para el cliente.

OBJETIVOS POR SLOT (cada opción debe cumplirlos con ±5%):
{json.dumps(targets, ensure_ascii=False, indent=2)}

RESTRICCIONES: alergias={ctx.food_allergies}, aversiones={ctx.food_dislikes}, \
preferencias={ctx.food_likes}, horario={ctx.meal_schedule}."""

    if ctx.diet_mode == "flexible_7":
        return common + """

MODO flexible_7: para CADA slot, EXACTAMENTE 7 opciones con keys A–G en orden.
Mínimo 2 opciones rápidas (<10 min) y 1 para llevar por slot.
JSON: {"mode":"flexible_7","slots":[{"slot":N,"options":[{"key":"A","title":...,
"ingredients":[{"food":...,"grams":N,"household":...}],"prep":...,"prep_minutes":N,
"macros":{"kcal":N,"protein_g":N,"carbs_g":N,"fat_g":N},"tags":[...]}, ... 7 opciones]}]}"""

    return common + """

MODO strict: menú CERRADO de 7 días (lunes→domingo), un plato por slot y día.
JSON: {"mode":"strict","days":[{"day":"lunes","meals":[{"slot":N,"dish":{"key":"A","title":...,
"ingredients":[{"food":...,"grams":N,"household":...}],"prep":...,"prep_minutes":N,
"macros":{"kcal":N,"protein_g":N,"carbs_g":N,"fat_g":N},"tags":[...]}}, ...]}, ... 7 días],
"free_meal_guidelines": null}"""


def _education_user_prompt(core: PlanCoreOutput) -> str:
    patterns = sorted({
        "empuje_horizontal", "empuje_vertical", "traccion_horizontal",
        "traccion_vertical", "sentadilla", "bisagra_cadera",
    })
    return f"""Genera el CONTENIDO EDUCATIVO del plan.

Split del cliente: {core.training.split_name}.
JSON: {{"pills":[{{"topic":...,"for_client":...}} (3–5 píldoras)],
"biomech_by_pattern":[{{"pattern":...,"cues":[...],"why":...}}],
"faq":[{{"q":...,"a":...}}]}}.
Patrones sugeridos para biomech_by_pattern: {patterns}.
Temas de píldoras a rotar: sobrecarga progresiva, RIR, tempo, volumen, proteína,
balance energético, sueño y recuperación, NEAT, hidratación, deload."""


# --------------------------------------------------------------- pipeline ----

def generate_monthly_plan(ctx: ClientContext, ai: AIClient) -> GeneratedPlan:
    """Ejecuta las 3 llamadas con guardrails. Lanza PlanGenerationError si no
    se puede producir un plan seguro."""
    flags: list[str] = []
    model = settings.model_heavy

    # ① Núcleo
    try:
        core = ai.generate_json(
            model=model, system=system_prompt_full(),
            user=_core_user_prompt(ctx), schema=PlanCoreOutput,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"núcleo del plan: {exc}") from exc

    nut_report = gr.check_nutrition(
        core.nutrition.model_dump(), sex=ctx.sex, weight_kg=ctx.weight_kg,
        bmr=ctx.bmr, tdee=ctx.tdee,
    )
    tr_report = gr.check_training(
        core.training.model_dump(),
        training_days_declared=ctx.training_days,
        session_max_min=ctx.session_max_min,
        client_contraindications=ctx.contraindications,
        exercise_lookup=_exercise_lookup(ctx.exercise_library),
    )
    core_report = nut_report.merge(tr_report)
    if not core_report.ok:
        raise PlanGenerationError(
            "el núcleo viola guardrails: " + "; ".join(core_report.violations),
            flags=core_report.as_flags(),
        )
    flags += core_report.as_flags()

    # ② Comidas según diet_mode
    schema = MealsFlexibleOutput if ctx.diet_mode == "flexible_7" else MealsStrictOutput
    try:
        meals = ai.generate_json(
            model=model, system=system_prompt_meals(),
            user=_meals_user_prompt(ctx, core), schema=schema,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"banco de comidas: {exc}") from exc

    targets = _slot_targets(core)
    if isinstance(meals, MealsFlexibleOutput):
        meal_report = gr.check_meal_options(
            [s.model_dump() for s in meals.slots], targets
        )
    else:
        meal_report = gr.check_strict_day_meals(
            [d.model_dump() for d in meals.days], targets
        )
    # Las opciones fuera de ±5% son warnings recuperables: se marcan para que el
    # coach revise; no bloquean (re-pedir opción por opción se hace en Fase 4
    # cuando hay scheduler/SSE; aquí lo dejamos como flag accionable).
    flags += meal_report.as_flags()

    # ③ Educativo
    try:
        education = ai.generate_json(
            model=model, system=system_prompt_education(),
            user=_education_user_prompt(core), schema=EducationOutput,
        )
    except AIGenerationError as exc:
        raise PlanGenerationError(f"contenido educativo: {exc}") from exc

    return GeneratedPlan(
        core=core, meals=meals, education=education,
        guardrail_flags=flags, generated_by=model,
    )

```


## `backend/app/services/ai/prompts.py`

```python
"""Prompts de IA embebidos (PARTE D).

Toda la metodología de las PARTES E (nutrición) y F (entrenamiento) se embebe
LITERALMENTE como contexto experto en el system prompt, junto con los
guardrails como instrucciones explícitas (la validación dura la hace el
backend en services/guardrails.py; aquí se le pide a la IA que los respete de
entrada para minimizar reintentos).

Estas constantes son la ÚNICA fuente de verdad de los prompts. No se generan
ni se improvisan en runtime: se formatean con datos del cliente y nada más.
"""

from __future__ import annotations

# ============================================================ D.1 base ====

SYSTEM_BASE = """Eres un experto en nutrición deportiva y ciencias del entrenamiento de fuerza. \
Trabajas con evidencia científica actual, personalización extrema y lenguaje profesional pero \
cercano. Tus planes los seguirán personas reales: prioriza adherencia, claridad y seguridad por \
encima de la perfección teórica. Respondes EXCLUSIVAMENTE con JSON válido conforme al schema \
indicado, sin markdown ni texto fuera del JSON."""


METHODOLOGY_NUTRITION = """\
=== METODOLOGÍA DE NUTRICIÓN (conocimiento experto) ===

ENERGÍA
- BMR: Mifflin-St Jeor; si hay % graso, Katch-McArdle (370 + 21.6 × masa magra kg).
- TDEE: BMR × factor de actividad (1.2 / 1.375 / 1.55 / 1.725 / 1.9) según días de entrenamiento.
- Pérdida de grasa: déficit 15–25% del TDEE (mayor a mayor % graso; conservador en magros/novatos).
  Ganancia: superávit 5–12% (menor en avanzados). Recomposición: mantenimiento ±5% con proteína alta.
- Las calorías SIEMPRE con justificación: TDEE estimado + ajuste + por qué.
  IMPORTANTE: el backend ya te entrega BMR, TDEE y kcal objetivo calculados. NO recalcules:
  parte de esos números y justifícalos. Tú afinas dentro de los límites, no inventas la base.

MACROS Y DISTRIBUCIÓN
- Proteína 1.6–2.2 g/kg (hasta 2.6 en déficit agresivo y sujeto magro); grasas mínimo 0.6–0.8 g/kg;
  carbohidratos el resto, priorizados peri-entrenamiento.
- Reparto de proteína en tomas de 0.3–0.5 g/kg según número de comidas declarado.
- Fibra orientativa 25–40 g/día; agua 30–40 ml/kg como guía.

FORMATO DEL PLAN (clave: facilidad de seguimiento)
- Macros = contrato; menú = plantilla. El banco de opciones por slot debe cumplir los macros del slot.
- Doble medida SIEMPRE: gramos + medida casera. Conversiones estándar: cucharada sopera ≈ 15 ml
  (aceite 10 g); cucharadita ≈ 5 ml; taza ≈ 250 ml; puñado de arroz/pasta crudos ≈ 60–80 g;
  palma de la mano ≈ 100–120 g de carne/pescado; huevo M ≈ 55 g; rebanada de pan ≈ 40 g;
  pieza mediana de fruta ≈ 150 g. Úsalas para los campos `household`.
- TODOS los pesos en CRUDO (estándar profesional).
- Suplementación solo con evidencia (creatina 5 g/día, cafeína 3–6 mg/kg pre-entreno si tolera,
  proteína en polvo como conveniencia, vitamina D, omega-3). NUNCA sustancias farmacológicas.
- Reglas de flexibilidad explícitas: comidas sociales (1–2/semana con pautas), alcohol, viajes,
  qué hacer si falla una comida (compensación simple, nunca castigo).
- Déficit >8 semanas consecutivas → considerar refeed semanal o diet break de 1 semana.
- Respeta SIEMPRE alergias, aversiones, preferencias y horarios de la anamnesis.

GUARDRAILS DE NUTRICIÓN (obligatorios — el backend los revalida):
- kcal objetivo ≥ max(BMR, 1400 mujer / 1600 hombre).
- Ajuste máximo ±15% kcal por recalibración.
- Proteína mínima 1.4 g/kg; grasas mínimas 0.5 g/kg.
- Déficit máximo 30% del TDEE; superávit máximo 15% del TDEE.
- Cada opción de comida debe cumplir los macros de su slot con ±5% de tolerancia."""


METHODOLOGY_TRAINING = """\
=== METODOLOGÍA DE ENTRENAMIENTO (conocimiento experto) ===

PROGRAMACIÓN Y SOBRECARGA PROGRESIVA
- División según días: 2→Full Body / 3→FB o U-L+FB / 4→Upper-Lower / 5→U-L+PPL o especialización /
  6→PPL×2. Siempre justificada.
- Sobrecarga progresiva EXPLÍCITA: tabla de progresión semanal (semana 1 base, 2–3 progresión de
  carga y/o volumen, semana 4 deload con volumen −40–50% e intensidad −10–20%). Cada ejercicio
  lleva su `progression_rule` en lenguaje claro ("cuando completes 4×8 con RIR 2, sube 2.5 kg").
- Doble progresión por defecto; lineal simple en principiantes los 2 primeros meses.
- RIR: compuestos pesados 2–3, secundarios 1–2, aislamiento 0–2. Tempo solo cuando aporte.
  Descansos: compuestos 2–3 min, aislamiento 60–90 s.
- Volumen semanal (series efectivas/grupo): principiante 8–12, intermedio 10–18, avanzado 14–22.
- Cardio sin interferir con la recuperación: pasos diarios objetivo + LISS/HIIT según objetivo.
- En recalibraciones: ajusta cargas desde los e1RM reales que te entrega el backend.

BIOMECÁNICA Y EDUCACIÓN
- Cada ejercicio lleva `technique_cue` (1 línea accionable) y `biomech_cue` (por qué, 1 línea
  accesible). La sección educativa incluye píldoras de ciencia y cues por patrón de movimiento.
- Objetivo: que el cliente entienda QUÉ hace y POR QUÉ.

BIBLIOTECA DE EJERCICIOS
- SOLO seleccionas ejercicios de la biblioteca que se te entrega (ya filtrada por equipamiento,
  nivel, lesiones y exclusiones). Usa exclusivamente los `exercise_id` proporcionados.

GUARDRAILS DE ENTRENAMIENTO (obligatorios — el backend los revalida):
- Máximo 25 series por grupo muscular y semana.
- Incremento de carga máximo +10% por ejercicio y recalibración.
- Nunca uses ejercicios contraindicados para las lesiones declaradas.
- Nunca excedas los días ni la duración de sesión declarados (estimación: series × 3 min + 10)."""


# Solo nutrición + guardrails de comida para la llamada ② (ahorra contexto).
METHODOLOGY_NUTRITION_BRIEF = """\
=== REGLAS DE COMIDAS ===
- TODOS los pesos en CRUDO. Doble medida siempre: gramos + medida casera (`household`).
- Conversiones: cucharada ≈ 15 ml (aceite 10 g); cucharadita ≈ 5 ml; taza ≈ 250 ml;
  puñado de arroz/pasta crudos ≈ 60–80 g; palma ≈ 100–120 g; huevo M ≈ 55 g; rebanada ≈ 40 g;
  fruta mediana ≈ 150 g.
- Cada opción/plato cumple los macros de su slot con ±5%.
- Respeta alergias, aversiones, preferencias y horarios de la anamnesis.
- Lenguaje de preparación directo, 2–3 pasos máximo por opción."""


def system_prompt_full() -> str:
    """System prompt para la llamada ① (núcleo): base + metodología completa."""
    return "\n\n".join([SYSTEM_BASE, METHODOLOGY_NUTRITION, METHODOLOGY_TRAINING])


def system_prompt_meals() -> str:
    """System prompt para la llamada ② (comidas): base + reglas de comida."""
    return "\n\n".join([SYSTEM_BASE, METHODOLOGY_NUTRITION_BRIEF])


def system_prompt_education() -> str:
    """System prompt para la llamada ③ (educativo)."""
    return (
        SYSTEM_BASE
        + "\n\nGeneras contenido educativo claro y basado en evidencia, sin citas "
        "académicas pero sin afirmaciones pseudocientíficas. Tono profesional y cercano."
    )


SYSTEM_PHOTO_ANALYSIS = (
    SYSTEM_BASE
    + "\n\nAnalizas fotografías de progreso físico con lenguaje PRUDENTE y accesible. "
    "Describe cambios visibles por zona corporal y su coherencia con el peso y perímetros "
    "aportados. NUNCA inventes porcentajes de grasa corporal ni hagas promesas. El texto "
    "será revisado y editado por el coach antes de enviarse al cliente. Responde en JSON "
    'con la forma {"analysis": "texto en español, 4–8 frases"}.'
)

```


## `backend/app/services/audit.py`

```python
"""Registro de auditoría (audit_log) — toda acción relevante deja traza."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    entity: str,
    entity_id: int | None,
    event: str,
    detail: dict | None = None,
) -> None:
    """Añade la entrada al UoW actual; el commit lo hace el caller."""
    db.add(AuditLog(entity=entity, entity_id=entity_id, event=event, detail_json=detail))

```


## `backend/app/services/consent_pdf.py`

```python
"""PDF de consentimiento informado RGPD (G.3) — generado y archivado en alta."""

from __future__ import annotations

from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.services.storage import client_dir, storage_root

CONSENT_TEXT = (
    "De conformidad con el Reglamento (UE) 2016/679 (RGPD) y la LOPDGDD 3/2018, "
    "el cliente abajo identificado CONSIENTE de forma explícita el tratamiento de "
    "sus datos personales, incluidos datos de salud (categoría especial del art. 9 "
    "RGPD: peso, medidas corporales, fotografías de progreso, lesiones, patologías "
    "y medicación), con la única finalidad de elaborar y hacer seguimiento de su "
    "planificación personalizada de nutrición y entrenamiento. "
    "Los datos se conservarán mientras dure la relación de asesoría. El cliente "
    "puede ejercer en cualquier momento sus derechos de acceso, rectificación, "
    "supresión, portabilidad, limitación y oposición dirigiéndose al responsable. "
    "Las fotografías de progreso nunca serán públicas ni se cederán a terceros."
)


def generate_consent_pdf(
    client_id: int, client_name: str, client_email: str, brand_name: str, signed_at: datetime
) -> str:
    """Crea el PDF en documents/ y devuelve su ruta relativa al storage."""
    dest = client_dir(client_id, "documents") / "consentimiento_rgpd.pdf"
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=16, spaceAfter=6)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=15)
    meta = ParagraphStyle("m", parent=styles["BodyText"], fontSize=10, leading=14)

    doc = SimpleDocTemplate(
        str(dest), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=24 * mm, bottomMargin=20 * mm,
        title="Consentimiento informado RGPD", author=brand_name,
    )
    stamp = signed_at.strftime("%d/%m/%Y %H:%M UTC")
    doc.build([
        Paragraph("Consentimiento informado — protección de datos", title),
        Paragraph(brand_name, styles["Heading3"]),
        Spacer(1, 8),
        Paragraph(f"<b>Cliente:</b> {client_name} &nbsp;&nbsp; <b>Email:</b> {client_email}", meta),
        Paragraph(f"<b>Fecha y hora de aceptación:</b> {stamp}", meta),
        Spacer(1, 12),
        Paragraph(CONSENT_TEXT, body),
        Spacer(1, 14),
        Paragraph(
            "Aceptación registrada electrónicamente mediante casilla de verificación "
            "obligatoria en el formulario de anamnesis del portal del cliente "
            f"(identificador interno de cliente: {client_id}).",
            meta,
        ),
    ])
    return str(dest.relative_to(storage_root()))

```


## `backend/app/services/docs/__init__.py`

```python

```


## `backend/app/services/docs/charts.py`

```python
"""Generación de gráficas matplotlib con colores de marca (H.4).

Cada función devuelve PNG en bytes (BytesIO), listo para incrustar en el
documento Word. Usa el backend 'Agg' (sin display) y un estilo limpio acorde
al tema claro de los documentos. El color de acento es el de la marca.

Los datos vienen ya calculados por services/metrics.py (la IA nunca calcula):
estas funciones solo dibujan.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# Estilo base para documentos (tema claro, premium)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.edgecolor": "#D8D8DE",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#EEEEF2",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": "#6B6B76",
    "ytick.color": "#6B6B76",
    "text.color": "#1A1A24",
    "axes.labelcolor": "#1A1A24",
})


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def weight_trend_chart(
    points: list[tuple[str, float]], goal_kg: float | None, accent: str
) -> bytes:
    """Peso a lo largo del período con línea de tendencia y objetivo."""
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = [p[0] for p in points]
    values = [p[1] for p in points]
    xs = list(range(len(values)))

    ax.plot(xs, values, color=accent, linewidth=2.4, marker="o",
            markersize=5, markerfacecolor="white", markeredgecolor=accent,
            markeredgewidth=1.8, zorder=3, label="Peso")

    # Tendencia (regresión lineal simple) si hay ≥2 puntos
    if len(values) >= 2:
        n = len(values)
        mx = sum(xs) / n
        my = sum(values) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom
            intercept = my - slope * mx
            trend = [slope * x + intercept for x in xs]
            ax.plot(xs, trend, color="#9A9AA6", linewidth=1.4, linestyle="--",
                    zorder=2, label="Tendencia")

    if goal_kg is not None:
        ax.axhline(goal_kg, color=accent, linewidth=1.2, linestyle=":",
                   alpha=0.6, zorder=1)
        ax.text(xs[-1], goal_kg, "  objetivo", va="center", fontsize=9,
                color=accent, alpha=0.8)

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("kg")
    ax.legend(frameon=False, fontsize=9, loc="best")
    return _fig_to_png(fig)


def adherence_chart(diet_pct: float, training_pct: float, accent: str) -> bytes:
    """Barras horizontales de adherencia a dieta y entrenamiento (0–100%)."""
    fig, ax = plt.subplots(figsize=(6.4, 2.0))
    cats = ["Entrenamiento", "Dieta"]
    vals = [training_pct, diet_pct]
    bars = ax.barh(cats, vals, color=[accent, "#8B9DF7"], height=0.55, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de adherencia")
    for bar, v in zip(bars, vals):
        ax.text(min(v + 2, 96), bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}%", va="center", fontsize=10, fontweight="bold",
                color="#1A1A24")
    ax.grid(axis="y", visible=False)
    return _fig_to_png(fig)


def e1rm_chart(exercises: list[dict], accent: str) -> bytes:
    """Barras de e1RM por ejercicio (3–5 principales) con valor encima.

    `exercises`: [{name, e1rm_kg, delta_kg}] ya ordenados.
    """
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    names = [e["name"] for e in exercises]
    vals = [e["e1rm_kg"] for e in exercises]
    bars = ax.bar(names, vals, color=accent, width=0.6, zorder=3)
    ax.set_ylabel("e1RM (kg)")
    for bar, e in zip(bars, exercises):
        label = f"{e['e1rm_kg']:.0f}"
        if e.get("delta_kg"):
            sign = "+" if e["delta_kg"] > 0 else ""
            label += f"\n{sign}{e['delta_kg']:.1f}"
        ax.text(bar.get_x() + bar.get_width() / 2, e["e1rm_kg"],
                label, ha="center", va="bottom", fontsize=9,
                color="#1A1A24", fontweight="bold")
    ax.margins(y=0.18)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=9)
    return _fig_to_png(fig)


def perimeters_chart(
    perimeters: dict[str, list[tuple[str, float]]], accent: str
) -> bytes:
    """Evolución de perímetros (cintura, cadera…) a lo largo de los cierres."""
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    palette = [accent, "#8B9DF7", "#F7C96E", "#C99EF7"]
    for i, (name, series) in enumerate(perimeters.items()):
        xs = list(range(len(series)))
        ys = [v for _, v in series]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=2,
                color=palette[i % len(palette)], label=name, zorder=3)
    ax.set_ylabel("cm")
    if perimeters:
        any_series = next(iter(perimeters.values()))
        ax.set_xticks(list(range(len(any_series))))
        ax.set_xticklabels([lbl for lbl, _ in any_series], fontsize=9)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="best")
    return _fig_to_png(fig)


def volume_by_group_chart(volume: dict[str, float], accent: str) -> bytes:
    """Barras horizontales de series semanales por grupo muscular."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    items = sorted(volume.items(), key=lambda x: x[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(names, vals, color=accent, height=0.6, zorder=3)
    ax.set_xlabel("series / semana")
    ax.axvline(25, color="#F77E7E", linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(25, -0.6, "máx 25", color="#F77E7E", fontsize=8, ha="center")
    return _fig_to_png(fig)

```


## `backend/app/services/docs/feedback_doc.py`

```python
"""Documento de feedback quincenal/mensual con gráficas (H.4).

Estructura: resumen del período en datos (peso+tendencia, adherencia,
perímetros, volumen) → progresión de fuerza (e1RM) → composición física (fotos
lado a lado + análisis IA) → análisis en lenguaje natural → "qué ha cambiado y
por qué" (máx 5 bullets) → respuesta a dudas + objetivos + cierre.

Las gráficas (services/docs/charts) usan datos ya calculados por
services/metrics. Las imágenes se incrustan desde BytesIO.
"""

from __future__ import annotations

import io
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.services.docs import charts
from app.services.docs.word_base import (
    DocBrand,
    add_bullets,
    add_cards_row,
    add_cover,
    add_section_heading,
    init_document,
)


def _add_chart(doc: Document, png: bytes, width_in: float = 6.0) -> None:
    doc.add_picture(io.BytesIO(png), width=Inches(width_in))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def generate_feedback_doc(
    *,
    brand: DocBrand,
    client_name: str,
    period_index: int,
    metrics: dict,
    weight_points: list[tuple[str, float]],
    goal_kg: float | None,
    e1rm_exercises: list[dict],
    perimeters: dict[str, list[tuple[str, float]]] | None,
    volume_by_group: dict[str, float] | None,
    photo_pairs: list[tuple[str, str]] | None,
    ai_photo_analysis: str | None,
    natural_analysis: str,
    changes_bullets: list[str],
    answers: str | None,
    next_objectives: list[str],
    closing_message: str,
) -> bytes:
    doc = init_document(brand)
    accent = brand.color_primary

    add_cover(doc, brand, client_name,
              subtitle=f"Informe de progreso · Período {period_index}",
              goal="Tu evolución en datos")

    # 1) Resumen del período en datos
    add_section_heading(doc, brand, "Tu período en datos")
    adh = metrics.get("adherence", {})
    weight = metrics.get("weight", {})
    add_cards_row(doc, brand, [
        ("Cambio de peso", _fmt_delta(weight.get("delta_kg"), "kg")),
        ("Adherencia dieta", f"{round(adh.get('diet_adherence_ratio', 0) * 100)}%"),
        ("Días registrados", f"{adh.get('days_logged', 0)}/{adh.get('period_days', 0)}"),
    ])
    doc.add_paragraph()

    if weight_points:
        doc.add_heading("Evolución de peso", level=2)
        _add_chart(doc, charts.weight_trend_chart(weight_points, goal_kg, accent))

    doc.add_heading("Adherencia", level=2)
    diet_pct = adh.get("diet_adherence_ratio", 0) * 100
    train_pct = min(100, adh.get("log_ratio", 0) * 100)
    _add_chart(doc, charts.adherence_chart(diet_pct, train_pct, accent), width_in=5.5)

    if perimeters:
        doc.add_heading("Perímetros", level=2)
        _add_chart(doc, charts.perimeters_chart(perimeters, accent))

    if volume_by_group:
        doc.add_heading("Volumen por grupo muscular", level=2)
        _add_chart(doc, charts.volume_by_group_chart(volume_by_group, accent))

    # 2) Progresión de fuerza
    if e1rm_exercises:
        doc.add_page_break()
        add_section_heading(doc, brand, "Progresión de fuerza")
        doc.add_paragraph(
            "Fuerza estimada (1RM por Epley) de tus ejercicios principales."
        )
        _add_chart(doc, charts.e1rm_chart(e1rm_exercises, accent))

    # 3) Composición física
    if (photo_pairs or ai_photo_analysis):
        doc.add_page_break()
        add_section_heading(doc, brand, "Composición física")
        if photo_pairs:
            for before, after in photo_pairs:
                _add_photo_pair(doc, before, after)
        if ai_photo_analysis:
            doc.add_paragraph(ai_photo_analysis)

    # 4) Análisis en lenguaje natural
    doc.add_page_break()
    add_section_heading(doc, brand, "Cómo ha ido")
    doc.add_paragraph(natural_analysis)

    # 5) Qué ha cambiado y por qué (máx 5 bullets)
    if changes_bullets:
        doc.add_heading("Qué ha cambiado en tu plan y por qué", level=2)
        add_bullets(doc, changes_bullets[:5])

    # 6) Dudas + objetivos + cierre
    if answers:
        doc.add_heading("Tus dudas", level=2)
        doc.add_paragraph(answers)

    if next_objectives:
        doc.add_heading("Objetivos para las próximas 2 semanas", level=2)
        add_bullets(doc, next_objectives)

    p = doc.add_paragraph()
    p.add_run(closing_message).italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _add_photo_pair(doc: Document, before_path: str, after_path: str) -> None:
    """Dos fotos lado a lado (antes/después) emparejadas por ángulo."""
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    headers = table.rows[0].cells
    for i, label in enumerate(("Período anterior", "Período actual")):
        p = headers[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(label)
        run.font.size = Pt(9)
        run.font.color.rgb = run.font.color.rgb  # mantiene color por defecto
    cells = table.rows[1].cells
    for i, path in enumerate((before_path, after_path)):
        p = cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if path and os.path.exists(path):
            try:
                run = p.add_run()
                run.add_picture(path, width=Inches(2.6))
            except Exception:
                p.add_run("(imagen no disponible)")
        else:
            p.add_run("—")


def _fmt_delta(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value} {unit}"

```


## `backend/app/services/docs/plan_doc.py`

```python
"""Documento Word del plan completo (H.3).

Estructura: portada → resumen ejecutivo (cards) → nutrición (macros, menú/banco
o menú cerrado + lista de la compra) → entrenamiento (progresión + sesiones) →
educativo (píldoras + biomecánica) → anexos (medidas caseras, FAQ).

Recibe el plan ya persistido (nutrition_json con meal_bank, training_json,
education_json) y el cliente. Devuelve los bytes del .docx.
"""

from __future__ import annotations

import io

from docx import Document

from app.services.docs.shopping_list import build_shopping_list
from app.services.docs.word_base import (
    DocBrand,
    add_bullets,
    add_cards_row,
    add_cover,
    add_section_heading,
    clean_table,
    init_document,
)

# Tabla de medidas caseras (anexo, E.3)
HOUSEHOLD_MEASURES = [
    ["Cucharada sopera", "15 ml (aceite ≈ 10 g)"],
    ["Cucharadita", "5 ml"],
    ["Taza", "250 ml"],
    ["Puñado de arroz/pasta (crudo)", "60–80 g"],
    ["Palma de la mano", "100–120 g de carne/pescado"],
    ["Huevo M", "55 g"],
    ["Rebanada de pan", "40 g"],
    ["Pieza mediana de fruta", "150 g"],
]


def _goal_label(goal: str | None) -> str:
    return {"fat_loss": "Pérdida de grasa", "muscle_gain": "Ganancia muscular",
            "recomp": "Recomposición"}.get(goal or "", "Plan personalizado")


def generate_plan_doc(
    *, brand: DocBrand, client_name: str, month_index: int, goal_type: str | None,
    diet_mode: str | None, nutrition: dict, training: dict, education: dict,
) -> bytes:
    doc = init_document(brand)

    # --- Portada ---
    add_cover(doc, brand, client_name,
              subtitle=f"Planificación · Mes {month_index}",
              goal=_goal_label(goal_type))

    # --- Resumen ejecutivo ---
    add_section_heading(doc, brand, "Resumen del mes")
    macros = nutrition.get("macros", {})
    add_cards_row(doc, brand, [
        ("Calorías diarias", f"{round(nutrition.get('target_kcal', 0))} kcal"),
        ("Proteína", f"{round(macros.get('protein_g', 0))} g"),
        ("Carbohidratos", f"{round(macros.get('carbs_g', 0))} g"),
        ("Grasas", f"{round(macros.get('fat_g', 0))} g"),
    ])
    doc.add_paragraph()
    add_cards_row(doc, brand, [
        ("Tu rutina", training.get("split_name", "—")),
        ("Por semana", f"{len(training.get('sessions', []))} días"),
        ("Objetivo", _goal_label(goal_type)),
    ])
    if nutrition.get("rationale"):
        doc.add_paragraph()
        doc.add_paragraph(nutrition["rationale"])

    # --- Nutrición ---
    doc.add_page_break()
    add_section_heading(doc, brand, "Nutrición")
    _nutrition_section(doc, brand, diet_mode, nutrition)

    # --- Entrenamiento ---
    doc.add_page_break()
    add_section_heading(doc, brand, "Entrenamiento")
    _training_section(doc, brand, training)

    # --- Educativo ---
    doc.add_page_break()
    add_section_heading(doc, brand, "Aprende")
    _education_section(doc, brand, education)

    # --- Anexos ---
    doc.add_page_break()
    add_section_heading(doc, brand, "Anexos")
    doc.add_heading("Medidas caseras", level=2)
    clean_table(doc, ["Medida", "Equivalencia"], HOUSEHOLD_MEASURES, brand,
                col_widths=[3600, 5426])
    faq = education.get("faq", [])
    if faq:
        doc.add_heading("Preguntas frecuentes", level=2)
        for item in faq:
            p = doc.add_paragraph()
            r = p.add_run(item.get("q", ""))
            r.font.bold = True
            doc.add_paragraph(item.get("a", ""))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _nutrition_section(doc: Document, brand: DocBrand, diet_mode: str | None, nutrition: dict) -> None:
    bank = nutrition.get("meal_bank") or {}
    meals = nutrition.get("meals", [])

    if diet_mode == "strict":
        doc.add_heading("Menú cerrado de 7 días", level=2)
        for day in bank.get("days", []):
            doc.add_heading(day.get("day", "").capitalize(), level=3)
            rows = []
            for meal in day.get("meals", []):
                dish = meal.get("dish", {})
                m = dish.get("macros", {})
                rows.append([
                    str(meal.get("slot", "")),
                    dish.get("title", ""),
                    f"{round(m.get('kcal', 0))} kcal",
                    f"{round(m.get('protein_g', 0))}P/{round(m.get('carbs_g', 0))}C/{round(m.get('fat_g', 0))}G",
                ])
            clean_table(doc, ["#", "Plato", "Energía", "Macros"], rows, brand,
                        col_widths=[700, 4626, 1900, 1800])

        # Lista de la compra exacta
        doc.add_heading("Lista de la compra semanal", level=2)
        shopping = build_shopping_list(bank)
        for cat, items in shopping.items():
            doc.add_heading(cat, level=3)
            rows = [[it["food"], f"{it['grams']} g" if it["grams"] else "al gusto"] for it in items]
            clean_table(doc, ["Alimento", "Cantidad semanal"], rows, brand,
                        col_widths=[6000, 3026])
    else:
        # Flexible: las opciones por slot en fichas compactas
        doc.add_heading("Tus comidas: 7 opciones por toma", level=2)
        doc.add_paragraph(
            "Para cada comida tienes 7 opciones intercambiables. Todas cumplen los "
            "mismos macros, así que elige según el día y tus ganas."
        )
        for meal_def in meals:
            slot = meal_def.get("slot")
            doc.add_heading(f"{meal_def.get('name', f'Comida {slot}')} · {meal_def.get('time', '')}", level=3)
            slot_opts = []
            for s in bank.get("slots", []):
                if s.get("slot") == slot:
                    slot_opts = s.get("options", [])
            rows = []
            for opt in slot_opts:
                m = opt.get("macros", {})
                ingredients = ", ".join(
                    f"{ing.get('food')} {ing.get('grams')}g" if ing.get("grams") else ing.get("food", "")
                    for ing in opt.get("ingredients", [])[:4]
                )
                rows.append([
                    opt.get("key", ""),
                    opt.get("title", ""),
                    f"{round(m.get('kcal', 0))} kcal",
                    ingredients,
                ])
            if rows:
                clean_table(doc, ["", "Opción", "Energía", "Ingredientes principales"], rows, brand,
                            col_widths=[500, 2800, 1500, 4226])

    # Suplementación
    supplements = nutrition.get("supplements", [])
    if supplements:
        doc.add_heading("Suplementación", level=2)
        rows = [[s.get("name", ""), s.get("dose", ""), s.get("timing", ""),
                 s.get("evidence_note", "")] for s in supplements]
        clean_table(doc, ["Suplemento", "Dosis", "Cuándo", "Por qué"], rows, brand,
                    col_widths=[2200, 1400, 1600, 3826])

    # Reglas de flexibilidad
    rules = nutrition.get("flexibility_rules", [])
    if rules:
        doc.add_heading("Reglas de flexibilidad", level=2)
        add_bullets(doc, rules)


def _training_section(doc: Document, brand: DocBrand, training: dict) -> None:
    doc.add_paragraph(training.get("split_rationale", ""))

    # Progresión semanal destacada
    prog = training.get("weekly_progression", [])
    if prog:
        doc.add_heading("Progresión semanal", level=2)
        rows = [[
            f"Sem {w.get('week')}", w.get("intent", ""),
            f"{w.get('load_pct', '')}%", f"RIR {w.get('rir_target', '')}",
            w.get("volume_note", ""),
        ] for w in prog]
        clean_table(doc, ["Semana", "Enfoque", "Carga", "RIR", "Notas"], rows, brand,
                    col_widths=[1100, 1800, 1100, 1100, 3926])

    # Sesiones
    for sess in training.get("sessions", []):
        doc.add_heading(f"{sess.get('day', '')} · {sess.get('name', '')}", level=2)
        if sess.get("warmup"):
            p = doc.add_paragraph()
            p.add_run("Calentamiento: ").bold = True
            p.add_run(sess["warmup"])
        rows = []
        for ex in sess.get("exercises", []):
            rows.append([
                f"#{ex.get('exercise_id', '')}",
                f"{ex.get('sets', '')}×{ex.get('rep_range', '')}",
                f"RIR {ex.get('rir', '')}",
                f"{ex.get('rest_sec', '')}s",
                ex.get("technique_cue", "") or "",
            ])
        clean_table(doc, ["Ej.", "Series", "RIR", "Descanso", "Clave técnica"], rows, brand,
                    col_widths=[900, 1400, 1100, 1200, 4426])
        if sess.get("cooldown"):
            p = doc.add_paragraph()
            p.add_run("Vuelta a la calma: ").bold = True
            p.add_run(sess["cooldown"])

    if training.get("deload_instructions"):
        doc.add_heading("Semana de descarga", level=2)
        doc.add_paragraph(training["deload_instructions"])


def _education_section(doc: Document, brand: DocBrand, education: dict) -> None:
    pills = education.get("pills", [])
    if pills:
        doc.add_heading("Píldoras de ciencia", level=2)
        for pill in pills:
            p = doc.add_paragraph()
            p.add_run(pill.get("topic", "") + ": ").bold = True
            p.add_run(pill.get("for_client", ""))

    biomech = education.get("biomech_by_pattern", [])
    if biomech:
        doc.add_heading("Biomecánica por patrón", level=2)
        for b in biomech:
            doc.add_heading(b.get("pattern", "").replace("_", " ").capitalize(), level=3)
            add_bullets(doc, b.get("cues", []))
            if b.get("why"):
                doc.add_paragraph(b["why"])

```


## `backend/app/services/docs/shopping_list.py`

```python
"""Lista de la compra semanal (modo strict).

Deriva por agregación aritmética la lista de la compra exacta a partir del
menú cerrado de 7 días: suma los gramos de cada ingrediente a lo largo de toda
la semana y los agrupa por categoría. Es aritmética pura (testable) y debe
cuadrar con el menú (test de agregación, PARTE B).

El agrupado por categoría usa un diccionario de palabras clave; lo desconocido
cae en "Otros" para no perder nada.
"""

from __future__ import annotations

from collections import defaultdict

# Categorización por palabras clave (es de cara al cliente, en castellano).
CATEGORIES: dict[str, list[str]] = {
    "Proteínas": [
        "pollo", "pavo", "ternera", "cerdo", "huevo", "atún", "salmón", "merluza",
        "pescado", "gambas", "lomo", "jamón", "queso", "yogur", "skyr", "requesón",
        "tofu", "seitán", "proteína", "clara",
    ],
    "Verduras y hortalizas": [
        "lechuga", "tomate", "cebolla", "pimiento", "calabacín", "berenjena",
        "brócoli", "espinaca", "zanahoria", "pepino", "champiñón", "ajo", "espárrago",
        "judía", "col", "coliflor", "canónigos", "rúcula", "verdura", "ensalada",
    ],
    "Frutas": [
        "manzana", "plátano", "fresa", "naranja", "kiwi", "arándano", "pera", "uva",
        "melón", "sandía", "mango", "piña", "frambuesa", "fruta", "aguacate", "limón",
    ],
    "Hidratos": [
        "arroz", "pasta", "pan", "patata", "avena", "quinoa", "couscous", "legumbre",
        "lenteja", "garbanzo", "tortita", "cereal", "boniato", "harina",
    ],
    "Grasas y otros": [
        "aceite", "oliva", "almendra", "nuez", "cacahuete", "semilla", "mantequilla",
        "chocolate", "coco", "tahini", "crema",
    ],
}


def _categorize(food: str) -> str:
    f = food.lower()
    for cat, keywords in CATEGORIES.items():
        if any(k in f for k in keywords):
            return cat
    return "Otros"


def build_shopping_list(strict_menu: dict) -> dict[str, list[dict]]:
    """Agrega ingredientes de un menú strict (MealsStrictOutput serializado).

    Devuelve {categoría: [{food, grams, mentions}]} ordenado, donde `grams` es
    la suma semanal y `mentions` cuántas veces aparece (para detectar staples).
    """
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    non_gram: dict[str, int] = defaultdict(int)  # ingredientes "al gusto" sin gramos

    for day in strict_menu.get("days", []):
        for meal in day.get("meals", []):
            dish = meal.get("dish", {})
            for ing in dish.get("ingredients", []):
                food = ing.get("food", "").strip()
                if not food:
                    continue
                grams = ing.get("grams")
                if grams:
                    totals[food] += float(grams)
                    counts[food] += 1
                else:
                    non_gram[food] += 1

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for food, grams in totals.items():
        by_cat[_categorize(food)].append({
            "food": food, "grams": round(grams), "mentions": counts[food],
        })
    for food, n in non_gram.items():
        if food not in totals:
            by_cat[_categorize(food)].append({
                "food": food, "grams": None, "mentions": n,
            })

    # Ordena categorías por el orden canónico y los ítems por gramos desc.
    order = list(CATEGORIES.keys()) + ["Otros"]
    out: dict[str, list[dict]] = {}
    for cat in order:
        if cat in by_cat:
            out[cat] = sorted(by_cat[cat], key=lambda x: (x["grams"] is None, -(x["grams"] or 0)))
    return out


def shopping_list_total_grams(shopping: dict[str, list[dict]]) -> float:
    """Suma total de gramos (para el test de agregación: debe cuadrar con el menú)."""
    return sum(
        item["grams"] for items in shopping.values() for item in items if item["grams"]
    )

```


## `backend/app/services/docs/word_base.py`

```python
"""Helpers de generación Word con python-docx, tema claro con marca (H.3).

Centraliza el estilo (tipografía, colores de marca, espaciados) y las
primitivas de maquetación (portada, cabeceras de sección, cards de resumen,
tablas limpias con ancho explícito). Las reglas de oro de tablas (ancho en DXA,
sin viñetas unicode, padding de celda, sombreado CLEAR) siguen las del skill de
docx, aplicadas al equivalente de python-docx.

Tanto el documento de plan como el de feedback construyen sobre estas piezas
para garantizar un aspecto coherente y profesional.
"""

from __future__ import annotations

from dataclasses import dataclass

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

# Ancho de contenido en EMU/twips para A4 con márgenes de 2 cm
CONTENT_WIDTH_DXA = 9026  # A4 menos márgenes


@dataclass
class DocBrand:
    name: str
    color_primary: str   # "#6EE7B7"
    color_secondary: str
    font_family: str
    tagline: str | None = None
    contact_email: str | None = None
    logo_path: str | None = None  # ruta absoluta a imagen, opcional


def _hex(color: str) -> RGBColor:
    return RGBColor.from_string(color.lstrip("#").upper())


def _shade_cell(cell, hex_color: str) -> None:
    """Sombreado de celda (equivale a ShadingType.CLEAR del skill).

    shd debe ir al inicio de tcPr (antes de tcMar/tcW) según el esquema OOXML.
    """
    tcPr = cell._tc.get_or_add_tcPr()
    # Quita un shd previo si existiera (evita duplicados en zebra+header)
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = tcPr.makeelement(qn("w:shd"), {
        qn("w:val"): "clear", qn("w:color"): "auto",
        qn("w:fill"): hex_color.lstrip("#").upper(),
    })
    # shd va después de tcW/gridSpan si existen, antes de tcMar
    tcW = tcPr.findall(qn("w:tcW"))
    if tcW:
        tcW[-1].addnext(shd)
    else:
        tcPr.insert(0, shd)


def _set_cell_margins(cell, top=60, bottom=60, left=110, right=110) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    m = tcPr.makeelement(qn("w:tcMar"), {})
    # El esquema de tcMar exige el orden: top, left (start), bottom, right (end)
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = m.makeelement(qn(f"w:{side}"), {qn("w:w"): str(val), qn("w:type"): "dxa"})
        m.append(node)
    tcPr.append(m)


def init_document(brand: DocBrand) -> Document:
    """Documento con estilos base de marca (tipografía y headings)."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = brand.font_family
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _hex("#1A1A24")

    for level, size in (("Heading 1", 20), ("Heading 2", 14), ("Heading 3", 11.5)):
        st = doc.styles[level]
        st.font.name = brand.font_family
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = _hex("#1A1A24")

    # Márgenes de 2 cm
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Pt(56)
        section.left_margin = section.right_margin = Pt(56)

    # El zoom por defecto de python-docx (val="bestFit") sin percent falla la
    # validación OOXML estricta; fijamos percent=100.
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None:
        zoom.set(qn("w:percent"), "100")
    return doc


def add_cover(doc: Document, brand: DocBrand, client_name: str, subtitle: str,
              goal: str) -> None:
    """Portada: marca, nombre del cliente, mes/objetivo."""
    import os

    from docx.shared import Inches

    if brand.logo_path and os.path.exists(brand.logo_path):
        try:
            doc.add_picture(brand.logo_path, width=Inches(1.4))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass

    for _ in range(3):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(brand.name)
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = _hex(brand.color_primary)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(client_name)
    run.font.size = Pt(30)
    run.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(subtitle)
    run.font.size = Pt(13)
    run.font.color.rgb = _hex("#6B6B76")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(goal)
    run.font.size = Pt(12)
    run.font.color.rgb = _hex(brand.color_secondary)

    doc.add_page_break()


def add_section_heading(doc: Document, brand: DocBrand, text: str) -> None:
    """Encabezado de sección con regla inferior de color de marca."""
    h = doc.add_heading(text, level=1)
    # Regla inferior (border en el párrafo, no tabla — regla del skill)
    pPr = h._p.get_or_add_pPr()
    borders = pPr.makeelement(qn("w:pBdr"), {})
    bottom = borders.makeelement(qn("w:bottom"), {
        qn("w:val"): "single", qn("w:sz"): "12",
        qn("w:space"): "4", qn("w:color"): brand.color_primary.lstrip("#").upper(),
    })
    borders.append(bottom)
    pPr.append(borders)


def add_cards_row(doc: Document, brand: DocBrand, cards: list[tuple[str, str]]) -> None:
    """Fila de 'cards' visuales (label, value) para el resumen ejecutivo."""
    n = len(cards)
    table = doc.add_table(rows=1, cols=n)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    col_w = CONTENT_WIDTH_DXA // n
    for i, (label, value) in enumerate(cards):
        cell = table.rows[0].cells[i]
        cell.width = Pt(col_w / 20)
        _shade_cell(cell, "F4F4F7")
        _set_cell_margins(cell, top=120, bottom=120)
        cell.paragraphs[0].text = ""
        pv = cell.paragraphs[0]
        pv.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rv = pv.add_run(value)
        rv.font.size = Pt(17)
        rv.font.bold = True
        rv.font.color.rgb = _hex(brand.color_primary)
        pl = cell.add_paragraph()
        pl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rl = pl.add_run(label)
        rl.font.size = Pt(8.5)
        rl.font.color.rgb = _hex("#6B6B76")
    _no_table_borders(table)


def clean_table(doc: Document, headers: list[str], rows: list[list[str]],
                brand: DocBrand, col_widths: list[int] | None = None):
    """Tabla limpia con cabecera de marca, ancho explícito y padding (skill)."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if col_widths is None:
        col_widths = [CONTENT_WIDTH_DXA // len(headers)] * len(headers)

    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].width = Pt(col_widths[i] / 20)
        _shade_cell(hdr[i], brand.color_primary.lstrip("#"))
        _set_cell_margins(hdr[i])
        p = hdr[i].paragraphs[0]
        run = p.add_run(h)
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = _hex("#0A0A0F")

    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].width = Pt(col_widths[i] / 20)
            _set_cell_margins(cells[i])
            if r_idx % 2 == 1:
                _shade_cell(cells[i], "F8F8FA")
            p = cells[i].paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(9.5)
    _thin_borders(table)
    return table


def add_bullets(doc: Document, items: list[str]) -> None:
    """Lista con viñetas usando el estilo nativo (nunca viñetas unicode, skill)."""
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def _thin_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = borders.makeelement(qn(f"w:{edge}"), {
            qn("w:val"): "single", qn("w:sz"): "4",
            qn("w:space"): "0", qn("w:color"): "E0E0E6",
        })
        borders.append(e)
    _insert_tbl_borders(tblPr, borders)


def _no_table_borders(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = tblPr.makeelement(qn("w:tblBorders"), {})
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = borders.makeelement(qn(f"w:{edge}"), {qn("w:val"): "none"})
        borders.append(e)
    _insert_tbl_borders(tblPr, borders)


def _insert_tbl_borders(tblPr, borders) -> None:
    """Inserta tblBorders en la posición correcta del esquema OOXML.

    El orden en tblPr es estricto: ...tblW, jc, tblCellSpacing, tblInd,
    tblBorders, shd, ... Insertamos tblBorders justo después de tblInd/jc/tblW
    (lo que exista) y antes de cualquier shd.
    """
    after = ("w:tblInd", "w:tblCellSpacing", "w:jc", "w:tblW", "w:tblStyle")
    anchor = None
    for tag in after:
        found = tblPr.findall(qn(tag))
        if found:
            anchor = found[-1]
            break
    if anchor is not None:
        anchor.addnext(borders)
    else:
        tblPr.insert(0, borders)

```


## `backend/app/services/email_service.py`

```python
"""Servicio de envío de email (G.5).

- Envía vía SMTP usando smtplib (síncrono; el scheduler corre en su propio
  hilo y los endpoints que envían lo hacen de forma puntual).
- Respeta el toggle GLOBAL (settings.emails_enabled) y POR CLIENTE
  (client.emails_enabled): si cualquiera está desactivado, no envía pero
  registra el intento con status "disabled".
- Toda salida (enviada, fallida o desactivada) deja traza en email_log.
- En desarrollo, docker-compose.dev.yml apunta SMTP a Mailpit, así que los
  emails se ven en http://localhost:8025 sin configurar un SMTP real.

El servicio NO decide CUÁNDO enviar (eso es la máquina de estados / scheduler /
endpoints); solo CÓMO enviar y registrar.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BrandConfig, Client, EmailLog
from app.services.email_templates import Brand


def brand_from_config(db: Session) -> Brand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return Brand(name="Tu asesoría", color_primary="#6EE7B7", color_bg="#0A0A0F")
    logo_url = None
    if cfg.logo_path:
        logo_url = f"{settings.public_base_url}/storage/{cfg.logo_path}"
    return Brand(
        name=cfg.name,
        color_primary=cfg.color_primary,
        color_bg=cfg.color_bg,
        contact_email=cfg.contact_email or None,
        logo_url=logo_url,
    )


class EmailService:
    """Envío + registro. Inyectable: en tests se sustituye `_transport`."""

    def __init__(self, db: Session):
        self.db = db

    # -- transporte (sobrescribible en tests) --
    def _transport(self, msg: EmailMessage) -> None:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                self._auth_and_send(s, msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                try:
                    s.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass  # Mailpit y algunos relays no usan TLS
                self._auth_and_send(s, msg)

    def _auth_and_send(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)

    def _log(self, client_id: int | None, kind: str, subject: str, status: str) -> None:
        self.db.add(EmailLog(client_id=client_id, kind=kind, subject=subject, status=status))

    def send(
        self, *, to: str, subject: str, html: str, kind: str,
        client: Client | None = None,
    ) -> str:
        """Envía un email y registra el resultado. Devuelve el status final.

        No hace commit: el caller controla la transacción (así el envío y los
        cambios de estado que lo motivan se confirman juntos o no).
        """
        client_id = client.id if client else None

        # Toggle global o por cliente desactivado → no enviar, pero registrar.
        if not settings.emails_enabled or (client is not None and not client.emails_enabled):
            self._log(client_id, kind, subject, "disabled")
            return "disabled"

        msg = EmailMessage()
        msg["From"] = settings.smtp_from or settings.smtp_user or "no-reply@fitness.local"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(
            "Este email requiere un cliente compatible con HTML. "
            "Abre tu portal para ver el contenido."
        )
        msg.add_alternative(html, subtype="html")

        try:
            self._transport(msg)
            self._log(client_id, kind, subject, "sent")
            return "sent"
        except Exception:
            self._log(client_id, kind, subject, "failed")
            return "failed"

```


## `backend/app/services/email_templates.py`

```python
"""Plantillas HTML de email con marca (G.5).

Cada plantilla es una función que recibe los datos y la marca, y devuelve
(asunto, html). El diseño es sobrio, mobile-first y aplica los colores de
brand_config. Todo el texto de cara al cliente va en castellano.

Las plantillas se mantienen como HTML inline (sin dependencias de assets
externos salvo el logo si existe) para máxima compatibilidad con clientes de
correo. El logo se referencia por URL pública si está disponible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Brand:
    name: str
    color_primary: str
    color_bg: str
    contact_email: str | None = None
    logo_url: str | None = None


def _shell(brand: Brand, title: str, body_html: str, cta_url: str | None = None,
           cta_label: str | None = None) -> str:
    """Envoltorio común: cabecera con marca, cuerpo, CTA opcional y pie."""
    logo = (
        f'<img src="{brand.logo_url}" alt="{brand.name}" '
        f'style="max-height:48px;margin-bottom:8px">'
        if brand.logo_url else
        f'<div style="font-size:20px;font-weight:700;color:{brand.color_primary}">'
        f'{brand.name}</div>'
    )
    cta = ""
    if cta_url and cta_label:
        cta = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="margin:24px 0"><tr><td style="border-radius:10px;'
            f'background:{brand.color_primary}">'
            f'<a href="{cta_url}" style="display:inline-block;padding:13px 26px;'
            f'font-weight:600;color:#0A0A0F;text-decoration:none;border-radius:10px">'
            f'{cta_label}</a></td></tr></table>'
        )
    footer_contact = (
        f'<br>¿Dudas? Escríbenos a <a href="mailto:{brand.contact_email}" '
        f'style="color:{brand.color_primary}">{brand.contact_email}</a>.'
        if brand.contact_email else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:Inter,Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="padding:28px 28px 0">{logo}</td></tr>
<tr><td style="padding:8px 28px 28px;color:#1a1a24;font-size:15px;line-height:1.6">
<h1 style="font-size:19px;margin:12px 0 4px;color:#1a1a24">{title}</h1>
{body_html}
{cta}
<p style="font-size:13px;color:#8a8a94;margin-top:24px">
Este mensaje es parte de tu asesoría personalizada con {brand.name}.{footer_contact}
</p>
</td></tr></table></td></tr></table></body></html>"""


# ---------------------------------------------------------- al cliente ----

def plan_published(brand: Brand, first_name: str, portal_url: str, is_new_month: bool) -> tuple[str, str]:
    if is_new_month:
        subject = f"Tu nuevo plan del mes ya está listo · {brand.name}"
        intro = (
            f"Hola {first_name}, hemos preparado tu plan para el nuevo mes a partir de "
            "tus resultados y tu feedback. Encontrarás los ajustes en tu portal."
        )
    else:
        subject = f"¡Bienvenido/a! Tu plan ya está disponible · {brand.name}"
        intro = (
            f"Hola {first_name}, tu planificación personalizada de nutrición y "
            "entrenamiento ya está lista. Entra en tu portal para verla y registrar "
            "tu día a día."
        )
    body = f"<p>{intro}</p><p>En la vista <strong>HOY</strong> verás qué comer y qué entrenar cada día, en menos de 30 segundos.</p>"
    return subject, _shell(brand, "Tu plan está listo", body, portal_url, "Abrir mi portal")


def reminder_no_logs(brand: Brand, first_name: str, portal_url: str, days_left: int) -> tuple[str, str]:
    subject = f"Un recordatorio rápido de tu seguimiento · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos visto que llevas unos días sin registrar tu "
        f"seguimiento. Quedan <strong>{days_left} días</strong> para cerrar este "
        "período.</p><p>Registrar tu peso, entrenos y adherencia nos permite ajustar "
        "tu plan con precisión. ¡Solo te lleva un minuto al día!</p>"
    )
    return subject, _shell(brand, "¿Cómo va tu seguimiento?", body, portal_url, "Registrar ahora")


def closing_due(brand: Brand, first_name: str, portal_url: str, period_index: int) -> tuple[str, str]:
    subject = f"Es momento de cerrar tu período · {brand.name}"
    body = (
        f"<p>Hola {first_name}, tu período actual ha llegado a su fin. Para preparar "
        "tu siguiente fase necesitamos que completes el <strong>cierre</strong>: peso "
        "final, medidas opcionales, alguna foto y cómo te ha ido.</p>"
        "<p>Con esa información ajustaremos tu plan para que sigas progresando.</p>"
    )
    return subject, _shell(brand, "Cierra tu período", body, f"{portal_url}/cierre", "Completar cierre")


def feedback_ready(brand: Brand, first_name: str, portal_url: str) -> tuple[str, str]:
    subject = f"Tu informe de progreso está listo · {brand.name}"
    body = (
        f"<p>Hola {first_name}, ya tienes tu informe de seguimiento con tus gráficas "
        "de progreso, evolución de fuerza y los cambios que hemos hecho en tu plan "
        "(y por qué).</p>"
    )
    return subject, _shell(brand, "Tu progreso, en detalle", body, f"{portal_url}/feedback", "Ver mi informe")


def plan_republished(brand: Brand, first_name: str, portal_url: str, change_summary: str) -> tuple[str, str]:
    subject = f"Tu planificación se ha actualizado · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos actualizado tu planificación:</p>"
        f"<p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>{change_summary}</p>"
        "<p>Ya puedes ver los cambios en tu portal.</p>"
    )
    return subject, _shell(brand, "Plan actualizado", body, portal_url, "Ver cambios")


# ------------------------------------------------------------ al coach ----

def coach_change_request(brand: Brand, client_name: str, message: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Acción] {client_name} ha solicitado un ajuste"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha enviado una solicitud de "
        f"ajuste:</p><p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>"
        f"{message}</p><p>Revísala y republica el plan cuando lo resuelvas.</p>"
    )
    return subject, _shell(brand, "Solicitud de ajuste", body, dashboard_url, "Abrir panel")


def coach_at_risk(brand: Brand, client_name: str, reason: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Aviso] {client_name} está en riesgo de abandono"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha pasado a estado "
        f"<strong>at_risk</strong>:</p>"
        f"<p style='background:#fff4f4;border-radius:10px;padding:12px 14px'>{reason}</p>"
        "<p>Quizá convenga un contacto personal para recuperar la adherencia.</p>"
    )
    return subject, _shell(brand, "Cliente en riesgo", body, dashboard_url, "Abrir panel")

```


## `backend/app/services/feedback_service.py`

```python
"""Orquestación del FEEDBACK quincenal del coach (cierre → informe).

A partir de un período CERRADO por el cliente:
1. reúne los registros diarios + datos de cierre + período anterior,
2. calcula TODAS las métricas con services/metrics (la IA nunca calcula),
3. pide a la IA SOLO la parte cualitativa (análisis y recomendaciones),
4. genera el documento Word con gráficas y lo persiste como FeedbackDoc,
5. marca el período como `analyzed` y guarda métricas/análisis.

Devuelve el FeedbackDoc creado. Reutilizable con un AIClient inyectado (tests).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, FeedbackDoc, Period, WorkoutLog
from app.services import metrics as M
from app.services.audit import log_event
from app.services.docs.feedback_doc import generate_feedback_doc
from app.services.docs.word_base import DocBrand
from app.services.storage import abs_path, client_dir, storage_root


class FeedbackError(RuntimeError):
    """No se pudo generar el feedback (datos insuficientes o fallo de IA)."""


def _doc_brand(db: Session) -> DocBrand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


def _prev_period(db: Session, period: Period) -> Period | None:
    return db.scalar(
        select(Period).where(
            Period.client_id == period.client_id,
            Period.period_index < period.period_index,
        ).order_by(Period.period_index.desc()).limit(1)
    )


def _perimeters(prev: Period | None, cur: Period) -> dict[str, list[tuple[str, float]]] | None:
    """Series de perímetros: período anterior (si hay) → actual."""
    fields = [("Cintura", "closing_waist_cm"), ("Cadera", "closing_hip_cm"),
              ("Brazo", "closing_arm_cm"), ("Muslo", "closing_thigh_cm")]
    out: dict[str, list[tuple[str, float]]] = {}
    for label, attr in fields:
        cur_v = getattr(cur, attr, None)
        if cur_v is None:
            continue
        series: list[tuple[str, float]] = []
        prev_v = getattr(prev, attr, None) if prev else None
        if prev_v is not None:
            series.append(("Anterior", prev_v))
        series.append(("Actual", cur_v))
        out[label] = series
    return out or None


def _photo_pairs(db: Session, prev: Period | None, cur: Period) -> list[tuple[str, str]] | None:
    """Empareja fotos por ángulo: período anterior vs actual."""
    from app.models import ProgressPhoto

    if not prev:
        return None
    def by_kind(pid: int) -> dict[str, str]:
        rows = db.scalars(select(ProgressPhoto).where(ProgressPhoto.period_id == pid))
        d: dict[str, str] = {}
        for ph in rows:
            try:
                p = abs_path(ph.file_path)
                if p.exists():
                    d[ph.kind] = str(p)
            except Exception:
                pass
        return d
    before, after = by_kind(prev.id), by_kind(cur.id)
    pairs = [(before[k], after[k]) for k in after if k in before]
    return pairs or None


def _workout_sets_for_logs(db: Session, log_ids: list[int]) -> list[dict]:
    if not log_ids:
        return []
    return [
        {"exercise_id": wl.exercise_id, "weight_kg": wl.weight_kg, "reps": wl.reps, "daily_log_id": wl.daily_log_id}
        for wl in db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(log_ids)))
    ]


def compute_period_summary(db: Session, period_id: int) -> dict:
    """Resumen de métricas del período SIN IA, a partir de lo que el cliente
    registró: cambio de peso corporal, adherencia, fuerza ganada (e1RM vs período
    anterior) y distancia al objetivo. Para el botón de feedback rápido del coach."""
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    client = db.get(Client, period.client_id)

    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period_id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    wt = M.weight_trend(raw_points)

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)

    # Fuerza: mejor e1RM por ejercicio este período vs el período anterior
    sets = _workout_sets_for_logs(db, [dl.id for dl in logs])
    progress = M.exercise_e1rm_progress(sets)[:6]
    prev = _prev_period(db, period)
    prev_best: dict[int, float] = {}
    if prev:
        prev_logs = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id == prev.id)))
        for p in M.exercise_e1rm_progress(_workout_sets_for_logs(db, list(prev_logs))):
            prev_best[p.exercise_id] = p.best_e1rm_kg
    ex_ids = {p.exercise_id for p in progress}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    strength = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
        "delta_kg": round(p.best_e1rm_kg - prev_best[p.exercise_id], 1) if p.exercise_id in prev_best else None,
    } for p in progress]

    current = period.closing_weight_kg if period.closing_weight_kg is not None else (
        wt.end_kg if wt.end_kg is not None else client.start_weight_kg
    )
    goal = client.goal_weight_kg
    distance = round(current - goal, 1) if (current is not None and goal is not None) else None

    return {
        "period_index": period.period_index,
        "status": period.status,
        "weight": {
            "start_kg": wt.start_kg, "end_kg": wt.end_kg,
            "delta_kg": wt.delta_kg, "weekly_rate_kg": wt.weekly_rate_kg,
        },
        "body_weight_now_kg": current,
        "goal_weight_kg": goal,
        "distance_to_goal_kg": distance,
        "adherence": {
            "diet_pct": round(adh.diet_adherence_ratio * 100),
            "log_pct": round(min(1.0, adh.log_ratio) * 100),
            "days_logged": adh.days_logged, "period_days": adh.period_days,
        },
        "strength": strength,
    }


def build_period_feedback(db: Session, period_id: int, ai=None) -> FeedbackDoc:
    """Genera y persiste el feedback de un período cerrado."""
    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.feedback import generate_feedback_analysis

    ai = ai or AIClient()
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    if period.status == "open":
        raise FeedbackError("El período aún no está cerrado por el cliente")
    client = db.get(Client, period.client_id)

    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period_id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    # --- Peso: puntos del diario + cierre ---
    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    weight_points = [(f"{d.day}/{d.month}", w) for d, w in sorted(raw_points)]
    wt = M.weight_trend(raw_points)

    # --- Adherencia y bienestar ---
    log_dicts = [{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs]
    adh = M.adherence_summary(log_dicts, period_days)

    # --- Fuerza (e1RM) y volumen por grupo ---
    log_ids = [dl.id for dl in logs]
    sets: list[dict] = []
    if log_ids:
        for wl in db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(log_ids))):
            sets.append({"exercise_id": wl.exercise_id, "weight_kg": wl.weight_kg,
                         "reps": wl.reps, "daily_log_id": wl.daily_log_id})
    progress = M.exercise_e1rm_progress(sets)[:5]
    ex_ids = {p.exercise_id for p in progress} | {s["exercise_id"] for s in sets}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    e1rm_exercises = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
    } for p in progress]

    weeks = max(1.0, period_days / 7)
    vol_counts: dict[str, float] = {}
    for s in sets:
        info = ex_info.get(s["exercise_id"])
        group = info.muscle_primary if info else "otros"
        vol_counts[group] = vol_counts.get(group, 0) + 1
    volume_by_group = {g: round(c / weeks, 1) for g, c in vol_counts.items()} or None

    prev = _prev_period(db, period)
    perimeters = _perimeters(prev, period)
    photo_pairs = _photo_pairs(db, prev, period)

    pm = M.PeriodMetrics(weight=wt, adherence=adh, exercise_progress=progress)
    metrics_json = pm.to_json()

    # --- IA: parte cualitativa ---
    payload = {
        "objetivo": client.goal_type, "peso_objetivo_kg": client.goal_weight_kg,
        "periodo_index": period.period_index, "metricas": metrics_json,
        "cierre": {
            "valoracion_1_5": period.closing_rating,
            "lo_mas_dificil": period.closing_hardest,
            "dudas": period.closing_questions,
        },
        "hay_fotos": bool(photo_pairs),
    }
    try:
        ai_out = generate_feedback_analysis(payload, ai)
    except AIGenerationError as exc:
        raise FeedbackError(f"La IA no devolvió un feedback válido: {exc}") from exc

    # --- Documento Word ---
    docx = generate_feedback_doc(
        brand=_doc_brand(db),
        client_name=client.full_name,
        period_index=period.period_index,
        metrics=metrics_json,
        weight_points=weight_points,
        goal_kg=client.goal_weight_kg,
        e1rm_exercises=e1rm_exercises,
        perimeters=perimeters,
        volume_by_group=volume_by_group,
        photo_pairs=photo_pairs,
        ai_photo_analysis=ai_out.ai_photo_analysis if photo_pairs else None,
        natural_analysis=ai_out.natural_analysis,
        changes_bullets=ai_out.changes_bullets,
        answers=ai_out.answers,
        next_objectives=ai_out.next_objectives,
        closing_message=ai_out.closing_message,
    )
    folder = client_dir(client.id, "feedback")
    fname = f"feedback_p{period.period_index}.docx"
    (folder / fname).write_bytes(docx)
    docx_rel = str((folder / fname).relative_to(storage_root()))

    # --- Persistir ---
    content_json = {**ai_out.model_dump(), "metrics": metrics_json}
    fb = FeedbackDoc(period_id=period.id, kind="biweekly",
                     content_json=content_json, docx_path=docx_rel)
    db.add(fb)
    period.status = "analyzed"
    period.metrics_json = metrics_json
    period.ai_analysis_json = ai_out.model_dump()
    period.ai_photo_analysis = ai_out.ai_photo_analysis
    db.flush()
    log_event(db, "period", period.id, "feedback_generated", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb

```


## `backend/app/services/guardrails.py`

```python
"""Guardrails — validación de seguridad de TODA salida de IA (E.4 + F.4).

Capa independiente de la validación de forma (Pydantic en schemas/ai.py).
Pydantic garantiza que el JSON tiene la *estructura* correcta; los guardrails
garantizan que los *valores* son seguros y coherentes con la metodología.

Cada función devuelve `GuardrailReport`:
- `violations`: problemas que BLOQUEAN la publicación (kcal por debajo del
  mínimo fisiológico, proteína insuficiente, volumen excesivo, ejercicio
  contraindicado…). Si hay alguna, el plan no se publica tal cual.
- `warnings`: avisos no bloqueantes que se registran en plans.guardrail_flags
  y se muestran al coach para revisión.

Diseño: los guardrails NO modifican la salida; informan. El servicio de IA
decide reintentar (con el error inyectado) o escalar al coach.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Constantes E.4 (nutrición) ---
KCAL_FLOOR_FEMALE = 1400
KCAL_FLOOR_MALE = 1600
RECAL_KCAL_ADJUST_MAX = 0.15   # ±15% kcal por recalibración
PROTEIN_MIN_G_PER_KG = 1.4
FAT_MIN_G_PER_KG = 0.5
DEFICIT_MAX_PCT = 0.30         # 30% TDEE
SURPLUS_MAX_PCT = 0.15         # 15% TDEE
MEAL_OPTION_TOLERANCE = 0.05   # ±5% macros del slot

# --- Constantes F.4 (entrenamiento) ---
SETS_MAX_PER_GROUP_WEEK = 25
LOAD_INCREMENT_MAX_PCT = 0.10  # +10% por ejercicio y recalibración
SESSION_MINUTES_FORMULA_PER_SET = 3
SESSION_MINUTES_FIXED_OVERHEAD = 10
# La duración es una ESTIMACIÓN heurística y la logística no es seguridad: un
# exceso leve sobre el máximo declarado es aviso (el coach recorta), no bloqueo.
# Solo bloquea un exceso holgado (> tolerancia).
SESSION_MINUTES_TOLERANCE = 0.20

KCAL_PER_G = {"protein_g": 4, "carbs_g": 4, "fat_g": 9}


@dataclass
class GuardrailReport:
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def merge(self, other: "GuardrailReport") -> "GuardrailReport":
        return GuardrailReport(
            violations=self.violations + other.violations,
            warnings=self.warnings + other.warnings,
        )

    def as_flags(self) -> list[str]:
        """Para persistir en plans.guardrail_flags (prefijo legible)."""
        return [f"violation:{v}" for v in self.violations] + [
            f"warning:{w}" for w in self.warnings
        ]


# =================================================================== E.4 ====

def check_nutrition(
    nutrition: dict,
    *,
    sex: str,
    weight_kg: float,
    bmr: float,
    tdee: float,
    is_recalibration: bool = False,
    previous_target_kcal: float | None = None,
) -> GuardrailReport:
    """Valida el bloque de nutrición de la salida de IA contra E.4.

    `nutrition` es el dict `nutrition` de PlanCoreOutput (ya validado en forma).
    """
    r = GuardrailReport()
    target = float(nutrition["target_kcal"])
    macros = nutrition["macros"]
    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])

    # Suelo calórico: max(BMR, suelo por sexo)
    floor = max(bmr, KCAL_FLOOR_MALE if sex == "male" else KCAL_FLOOR_FEMALE)
    if target < floor:
        r.violations.append(
            f"kcal objetivo {target:.0f} por debajo del mínimo {floor:.0f} "
            f"(max BMR/{'1600' if sex == 'male' else '1400'})"
        )

    # Déficit / superávit máximos respecto al TDEE
    if tdee > 0:
        delta_pct = (target - tdee) / tdee
        if delta_pct < -DEFICIT_MAX_PCT:
            r.violations.append(
                f"déficit {abs(delta_pct) * 100:.0f}% supera el máximo "
                f"{DEFICIT_MAX_PCT * 100:.0f}% del TDEE"
            )
        if delta_pct > SURPLUS_MAX_PCT:
            r.violations.append(
                f"superávit {delta_pct * 100:.0f}% supera el máximo "
                f"{SURPLUS_MAX_PCT * 100:.0f}% del TDEE"
            )

    # Mínimos de proteína y grasa por kg
    if weight_kg > 0:
        if protein < PROTEIN_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"proteína {protein:.0f} g < mínimo "
                f"{PROTEIN_MIN_G_PER_KG * weight_kg:.0f} g ({PROTEIN_MIN_G_PER_KG} g/kg)"
            )
        if fat < FAT_MIN_G_PER_KG * weight_kg - 0.5:
            r.violations.append(
                f"grasa {fat:.0f} g < mínimo "
                f"{FAT_MIN_G_PER_KG * weight_kg:.0f} g ({FAT_MIN_G_PER_KG} g/kg)"
            )

    # Coherencia kcal ↔ macros (no debe desviarse mucho de target)
    macro_kcal = sum(float(macros[k]) * v for k, v in KCAL_PER_G.items())
    if target > 0 and abs(macro_kcal - target) / target > 0.10:
        r.warnings.append(
            f"suma de macros ({macro_kcal:.0f} kcal) se desvía >10% del "
            f"objetivo ({target:.0f} kcal)"
        )

    # Límite de ajuste en recalibración (±15%)
    if is_recalibration and previous_target_kcal:
        change = abs(target - previous_target_kcal) / previous_target_kcal
        if change > RECAL_KCAL_ADJUST_MAX:
            r.violations.append(
                f"ajuste de {change * 100:.0f}% supera el máximo "
                f"{RECAL_KCAL_ADJUST_MAX * 100:.0f}% por recalibración"
            )

    # Slots de comida: cada target de slot dentro de ±5% no aplica aquí
    # (se valida por opción en check_meal_options). Aquí: suma de slots ≈ target.
    meals = nutrition.get("meals", [])
    if meals:
        slot_sum = sum(float(m["target"]["kcal"]) for m in meals)
        if target > 0 and abs(slot_sum - target) / target > 0.10:
            r.warnings.append(
                f"suma de slots ({slot_sum:.0f} kcal) se desvía >10% del "
                f"objetivo diario ({target:.0f} kcal)"
            )
    return r


def check_meal_options(slots: list[dict], day_targets: dict[int, dict]) -> GuardrailReport:
    """Valida que cada opción de comida cumple los macros de su slot ±5% (E.4).

    `slots`: lista de FlexibleSlot serializados (slot + options[]).
    `day_targets`: {slot: {kcal, protein_g, carbs_g, fat_g}} del plan núcleo.
    Devuelve violación por cada opción concreta fuera de tolerancia, indicando
    slot y key para que el servicio de IA re-pida SOLO esa opción.
    """
    r = GuardrailReport()
    for slot_block in slots:
        slot = slot_block["slot"]
        target = day_targets.get(slot)
        if not target:
            r.warnings.append(f"slot {slot} sin target de referencia")
            continue
        for opt in slot_block["options"]:
            _check_single_option(r, slot, opt, target)
    return r


def check_strict_day_meals(days: list[dict], day_targets: dict[int, dict]) -> GuardrailReport:
    """Igual que check_meal_options pero para el modo strict (un plato/slot/día)."""
    r = GuardrailReport()
    for day_block in days:
        day_name = day_block.get("day", "?")
        for meal in day_block["meals"]:
            slot = meal["slot"]
            target = day_targets.get(slot)
            if not target:
                r.warnings.append(f"slot {slot} sin target de referencia")
                continue
            _check_single_option(r, slot, meal["dish"], target, label=f"{day_name}/")
    return r


def _check_single_option(
    r: GuardrailReport, slot: int, opt: dict, target: dict, label: str = ""
) -> None:
    macros = opt["macros"]
    key = opt.get("key", opt.get("title", "?"))
    for macro in ("kcal", "protein_g", "carbs_g", "fat_g"):
        tgt = float(target[macro])
        val = float(macros[macro])
        if tgt <= 0:
            continue
        if abs(val - tgt) / tgt > MEAL_OPTION_TOLERANCE:
            r.violations.append(
                f"opción {label}slot {slot} '{key}': {macro} {val:.0f} fuera de "
                f"±{MEAL_OPTION_TOLERANCE * 100:.0f}% del objetivo {tgt:.0f}"
            )


# =================================================================== F.4 ====

def check_training(
    training: dict,
    *,
    training_days_declared: int,
    session_max_min: int,
    client_contraindications: set[str],
    exercise_lookup: dict[int, dict],
    is_recalibration: bool = False,
    previous_weights: dict[int, float] | None = None,
) -> GuardrailReport:
    """Valida el bloque de entrenamiento contra F.4.

    `exercise_lookup`: {exercise_id: {contraindications, muscle_primary, name}}
    para cruzar contraindicaciones y contar volumen por grupo.
    `previous_weights`: {exercise_id: start_weight_hint_kg} del plan anterior,
    para el límite de +10% por recalibración.
    """
    r = GuardrailReport()
    sessions = training.get("sessions", [])

    # 1) Nunca exceder días declarados
    if len(sessions) > training_days_declared:
        r.violations.append(
            f"{len(sessions)} sesiones > {training_days_declared} días declarados"
        )

    weekly_sets_by_group: dict[str, float] = {}

    for sess in sessions:
        session_sets = 0
        for ex in sess.get("exercises", []):
            ex_id = ex["exercise_id"]
            sets = int(ex["sets"])
            session_sets += sets
            info = exercise_lookup.get(ex_id)

            if info is None:
                r.violations.append(
                    f"exercise_id {ex_id} no existe en la biblioteca"
                )
                continue

            # 2) Contraindicaciones (doble verificación post-IA)
            contra = set(info.get("contraindications") or [])
            clash = contra & client_contraindications
            if clash:
                r.violations.append(
                    f"'{info.get('canonical_name', ex_id)}' contraindicado para "
                    f"lesión(es): {', '.join(sorted(clash))}"
                )

            # Volumen por grupo (primario cuenta completo)
            group = info.get("muscle_primary", "desconocido")
            weekly_sets_by_group[group] = weekly_sets_by_group.get(group, 0) + sets

            # 3) Incremento de carga máx +10% por recalibración
            if is_recalibration and previous_weights:
                prev = previous_weights.get(ex_id)
                new = ex.get("start_weight_hint_kg")
                if prev and new and prev > 0:
                    inc = (new - prev) / prev
                    if inc > LOAD_INCREMENT_MAX_PCT:
                        r.violations.append(
                            f"'{info.get('canonical_name', ex_id)}': subida de "
                            f"{inc * 100:.0f}% supera el máximo "
                            f"{LOAD_INCREMENT_MAX_PCT * 100:.0f}%"
                        )

        # 4) Duración estimada de la sesión: series×3min + 10. Exceso leve = aviso;
        # exceso holgado (> tolerancia) = violación que bloquea.
        est_min = session_sets * SESSION_MINUTES_FORMULA_PER_SET + SESSION_MINUTES_FIXED_OVERHEAD
        if est_min > session_max_min * (1 + SESSION_MINUTES_TOLERANCE):
            r.violations.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera el "
                f"máximo declarado {session_max_min} min"
            )
        elif est_min > session_max_min:
            r.warnings.append(
                f"sesión '{sess.get('name', '?')}' ~{est_min} min supera "
                f"ligeramente el máximo declarado {session_max_min} min; revisa y recorta series si quieres"
            )

    # 5) Volumen semanal máximo por grupo
    for group, total in weekly_sets_by_group.items():
        if total > SETS_MAX_PER_GROUP_WEEK:
            r.violations.append(
                f"grupo '{group}': {total:.0f} series/semana supera el máximo "
                f"{SETS_MAX_PER_GROUP_WEEK}"
            )
    return r


def filter_exercises_for_client(
    exercises: list[dict],
    *,
    client_contraindications: set[str],
    excluded_ids: set[int],
    equipment_available: set[str],
    level_max: int,
    training_place: str,
) -> list[dict]:
    """Filtro determinista PREVIO a la IA (F.3 / D.2): la IA solo ve ejercicios
    aptos. Reduce contexto y previene contraindicaciones de raíz.

    En 'home'/'outdoor' no se exige equipamiento de gimnasio; en 'gym' se
    requiere que el cliente disponga de TODO el equipamiento del ejercicio.
    """
    out = []
    for ex in exercises:
        if ex.get("archived"):
            continue
        if ex["id"] in excluded_ids:
            continue
        if ex.get("level_min", 1) > level_max:
            continue
        contra = set(ex.get("contraindications") or [])
        if contra & client_contraindications:
            continue
        needed = set(ex.get("equipment") or [])
        if training_place == "gym":
            # En gimnasio se asume equipamiento estándar; solo se exige que el
            # cliente no haya excluido el equipamiento explícitamente.
            if needed and equipment_available and not needed <= equipment_available:
                # permite peso corporal siempre
                if needed != {"peso_corporal"}:
                    continue
        else:
            # casa/exterior: solo lo que el cliente declaró tener (o peso corporal)
            if needed and not needed <= (equipment_available | {"peso_corporal"}):
                continue
        out.append(ex)
    return out

```


## `backend/app/services/jobs.py`

```python
"""Jobs del scheduler (G.1/G.2/G.5) — la capa con efectos.

`run_daily_maintenance(db, today)` es el job diario idempotente:
- Para cada cliente con período activo, calcula los hechos desde la DB.
- Llama a la máquina de estados (función pura) para decidir transiciones.
- Persiste cambios de estado, registra en audit_log y dispara los emails que
  correspondan (recordatorio al cliente, alerta at_risk al coach).

Idempotencia: un email de un `kind` concreto no se reenvía si ya se registró
para ese cliente hoy (se consulta email_log por kind + fecha). Así, ejecutar el
job dos veces el mismo día no duplica nada.

Se ejecuta vía APScheduler (scheduler.py) una vez al día, y también puede
invocarse manualmente para pruebas o backfill.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, DailyLog, EmailLog, Period
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config
from app.services.state_machine import (
    ClientFacts,
    can_transition,
    evaluate_transition,
)


def _already_sent_today(db: Session, client_id: int, kind: str, today: date) -> bool:
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    n = db.scalar(
        select(func.count())
        .select_from(EmailLog)
        .where(
            EmailLog.client_id == client_id,
            EmailLog.kind == kind,
            EmailLog.sent_at >= start,
        )
    )
    return bool(n)


def _active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente del cliente que no esté analizado."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def _facts_for(db: Session, client: Client) -> ClientFacts:
    period = _active_period(db, client.id)
    if period is None:
        return ClientFacts(status=client.status)

    days_logged = db.scalar(
        select(func.count())
        .select_from(DailyLog)
        .where(DailyLog.period_id == period.id)
    ) or 0

    last_log_date = db.scalar(
        select(func.max(DailyLog.log_date)).where(DailyLog.period_id == period.id)
    )
    last_activity = last_log_date or period.starts_on

    return ClientFacts(
        status=client.status,
        has_active_period=True,
        period_start=period.starts_on,
        period_end=period.ends_on,
        period_closed=period.status in ("closed", "analyzed"),
        days_logged_in_period=int(days_logged),
        last_activity_date=last_activity,
    )


def run_daily_maintenance(db: Session, today: date | None = None) -> dict:
    """Job diario. Devuelve un resumen de lo actuado (útil para logs/tests)."""
    today = today or date.today()
    summary = {"evaluated": 0, "transitions": 0, "reminders": 0, "at_risk_alerts": 0}

    clients = db.scalars(
        select(Client).where(Client.status.notin_(["inactive"]))
    ).all()
    if not clients:
        return summary

    emailer = EmailService(db)
    brand = brand_from_config(db)
    base = settings.public_base_url

    for client in clients:
        summary["evaluated"] += 1
        facts = _facts_for(db, client)
        decision = evaluate_transition(facts, today)

        # 1) Recordatorio día 12 (no cambia estado)
        if decision.send_reminder and not _already_sent_today(db, client.id, "reminder_no_logs", today):
            period = _active_period(db, client.id)
            days_left = max(0, (period.ends_on - today).days) if period else 0
            subject, html = tpl.reminder_no_logs(
                brand, client.full_name.split()[0],
                f"{base}/p/{client.portal_token}", days_left,
            )
            emailer.send(to=client.email, subject=subject, html=html,
                         kind="reminder_no_logs", client=client)
            summary["reminders"] += 1

        # 2) Cambio de estado
        if decision.new_status and decision.new_status != client.status:
            if can_transition(client.status, decision.new_status):
                old = client.status
                client.status = decision.new_status
                log_event(db, "client", client.id, "status_changed",
                          {"from": old, "to": decision.new_status, "reason": decision.reason})
                summary["transitions"] += 1

                # 3) Alerta al coach si pasa a at_risk
                if decision.notify_coach_at_risk and not _already_sent_today(
                    db, client.id, "coach_at_risk", today
                ):
                    coach_to = settings.smtp_from or settings.smtp_user
                    if coach_to:
                        subject, html = tpl.coach_at_risk(
                            brand, client.full_name, decision.reason, f"{base}/clients/{client.id}",
                        )
                        emailer.send(to=coach_to, subject=subject, html=html,
                                     kind="coach_at_risk", client=client)
                        summary["at_risk_alerts"] += 1

    db.commit()
    return summary

```


## `backend/app/services/metrics.py`

```python
"""Servicio de métricas — TODA la aritmética del sistema vive aquí.

Principio rector (PARTE D.2): **la IA nunca calcula**. El backend computa
energía, medias, tendencias, adherencias y e1RM, y se los entrega ya hechos.
Esto garantiza reproducibilidad, testabilidad y que los guardrails operen
sobre números fiables, no sobre lo que la IA "creía" haber calculado.

Unidades: kg, cm, kcal, gramos. Pesos de comida siempre en crudo (E.3).
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

# ----------------------------------------------------------------- energía ----

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Ajuste calórico por objetivo (fracción del TDEE). El signo lo aplica el caller.
GOAL_ADJUSTMENT = {
    "fat_loss": (0.15, 0.25),   # déficit 15–25%
    "muscle_gain": (0.05, 0.12),  # superávit 5–12%
    "recomp": (0.0, 0.05),       # mantenimiento ±5%
}


def mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """BMR (kcal/día). Mifflin-St Jeor — el estándar cuando no hay % graso."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if sex == "male" else -161), 1)


def katch_mcardle(weight_kg: float, body_fat_pct: float) -> float:
    """BMR vía masa magra (kcal/día). Preferible si hay % graso fiable."""
    lean = weight_kg * (1 - body_fat_pct / 100)
    return round(370 + 21.6 * lean, 1)


def bmr(
    sex: str, weight_kg: float, height_cm: float, age: int,
    body_fat_pct: float | None = None,
) -> float:
    """BMR usando Katch-McArdle si hay % graso, Mifflin-St Jeor si no (E.1)."""
    if body_fat_pct is not None and 3 <= body_fat_pct <= 60:
        return katch_mcardle(weight_kg, body_fat_pct)
    return mifflin_st_jeor(sex, weight_kg, height_cm, age)


def activity_factor_for_days(training_days: int) -> float:
    """Mapea días de entrenamiento/semana a factor de actividad (E.1)."""
    if training_days <= 1:
        return ACTIVITY_FACTORS["sedentary"]
    if training_days <= 2:
        return ACTIVITY_FACTORS["light"]
    if training_days <= 4:
        return ACTIVITY_FACTORS["moderate"]
    if training_days <= 5:
        return ACTIVITY_FACTORS["active"]
    return ACTIVITY_FACTORS["very_active"]


def tdee(bmr_value: float, training_days: int) -> float:
    return round(bmr_value * activity_factor_for_days(training_days), 1)


def age_from_birth(birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


@dataclass
class EnergyTargets:
    bmr: float
    tdee: float
    target_kcal: float
    method: str           # "mifflin" | "katch"
    adjustment_pct: float  # negativo = déficit, positivo = superávit


def energy_targets(
    sex: str, weight_kg: float, height_cm: float, age: int, goal_type: str,
    training_days: int, body_fat_pct: float | None = None,
) -> EnergyTargets:
    """Objetivo calórico de referencia que el backend entrega a la IA.

    La IA puede afinar dentro de los guardrails, pero parte de esta base
    objetiva en lugar de inventarla.
    """
    use_katch = body_fat_pct is not None and 3 <= body_fat_pct <= 60
    b = bmr(sex, weight_kg, height_cm, age, body_fat_pct)
    t = tdee(b, training_days)
    lo, hi = GOAL_ADJUSTMENT.get(goal_type, (0.0, 0.05))
    mid = (lo + hi) / 2
    if goal_type == "fat_loss":
        target = t * (1 - mid)
        adj = -mid
    elif goal_type == "muscle_gain":
        target = t * (1 + mid)
        adj = mid
    else:  # recomp
        target = t
        adj = 0.0
    return EnergyTargets(
        bmr=b, tdee=t, target_kcal=round(target, 1),
        method="katch" if use_katch else "mifflin",
        adjustment_pct=round(adj, 4),
    )


def protein_target_g(weight_kg: float, goal_type: str) -> tuple[float, float]:
    """Rango de proteína recomendado (g/día) según objetivo (E.2)."""
    if goal_type == "fat_loss":
        lo, hi = 2.0, 2.4
    elif goal_type == "muscle_gain":
        lo, hi = 1.6, 2.2
    else:
        lo, hi = 1.8, 2.2
    return round(weight_kg * lo, 1), round(weight_kg * hi, 1)


# ------------------------------------------------------------------- e1RM ----

def epley_1rm(weight_kg: float, reps: int) -> float:
    """1RM estimado (Epley). reps=1 → el propio peso."""
    if reps <= 0:
        return 0.0
    if reps == 1:
        return round(weight_kg, 2)
    return round(weight_kg * (1 + reps / 30), 2)


# ------------------------------------------------- agregados de un período ----

@dataclass
class WeightTrend:
    start_kg: float | None = None
    end_kg: float | None = None
    delta_kg: float | None = None
    weekly_rate_kg: float | None = None  # ritmo semanal (negativo = bajada)
    mean_kg: float | None = None
    n_measurements: int = 0


def weight_trend(points: list[tuple[date, float]]) -> WeightTrend:
    """Tendencia de peso a partir de (fecha, kg). Robusta a huecos.

    El ritmo semanal usa una regresión lineal simple por mínimos cuadrados
    sobre los días transcurridos: más estable que (fin - inicio) ante ruido.
    """
    pts = sorted((d, w) for d, w in points if w is not None)
    if not pts:
        return WeightTrend()
    weights = [w for _, w in pts]
    if len(pts) == 1:
        return WeightTrend(
            start_kg=weights[0], end_kg=weights[0], delta_kg=0.0,
            weekly_rate_kg=0.0, mean_kg=round(weights[0], 2), n_measurements=1,
        )
    day0 = pts[0][0]
    xs = [(d - day0).days for d, _ in pts]
    slope = _least_squares_slope(xs, weights)  # kg/día
    return WeightTrend(
        start_kg=round(weights[0], 2),
        end_kg=round(weights[-1], 2),
        delta_kg=round(weights[-1] - weights[0], 2),
        weekly_rate_kg=round(slope * 7, 3) if slope is not None else None,
        mean_kg=round(statistics.fmean(weights), 2),
        n_measurements=len(pts),
    )


def _least_squares_slope(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


@dataclass
class AdherenceSummary:
    days_logged: int = 0
    period_days: int = 0
    log_ratio: float = 0.0          # días registrados / días del período
    diet_yes: int = 0
    diet_partial: int = 0
    diet_no: int = 0
    diet_adherence_ratio: float = 0.0  # (yes + 0.5·partial) / registros de dieta
    mean_sleep_h: float | None = None
    mean_energy: float | None = None
    mean_mood: float | None = None
    mean_fatigue: float | None = None


def adherence_summary(
    logs: list[dict], period_days: int,
) -> AdherenceSummary:
    """Resume la adherencia y el bienestar del período.

    `logs`: lista de dicts con claves opcionales diet_adherence, sleep_hours,
    energy_1_5, mood_1_5, fatigue_1_5. Tolera campos ausentes/None.
    """
    s = AdherenceSummary(days_logged=len(logs), period_days=period_days)
    if period_days > 0:
        s.log_ratio = round(len(logs) / period_days, 3)

    diet = [g.get("diet_adherence") for g in logs if g.get("diet_adherence")]
    s.diet_yes = diet.count("yes")
    s.diet_partial = diet.count("partial")
    s.diet_no = diet.count("no")
    if diet:
        s.diet_adherence_ratio = round((s.diet_yes + 0.5 * s.diet_partial) / len(diet), 3)

    s.mean_sleep_h = _mean_of(logs, "sleep_hours")
    s.mean_energy = _mean_of(logs, "energy_1_5")
    s.mean_mood = _mean_of(logs, "mood_1_5")
    s.mean_fatigue = _mean_of(logs, "fatigue_1_5")
    return s


def _mean_of(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.fmean(vals), 2) if vals else None


@dataclass
class ExerciseProgress:
    exercise_id: int
    best_e1rm_kg: float
    best_set: tuple[float, int]  # (peso, reps) que produjo el mejor e1RM
    sessions: int


def exercise_e1rm_progress(sets: list[dict]) -> list[ExerciseProgress]:
    """Mejor e1RM por ejercicio dentro del período.

    `sets`: dicts con exercise_id, weight_kg, reps. Ignora sets sin peso/reps.
    El feedback grafica 3–5 ejercicios; esto da el dato a graficar (H.4).
    """
    by_ex: dict[int, list[dict]] = {}
    for st in sets:
        if st.get("weight_kg") and st.get("reps"):
            by_ex.setdefault(st["exercise_id"], []).append(st)

    out: list[ExerciseProgress] = []
    for ex_id, ex_sets in by_ex.items():
        best = max(ex_sets, key=lambda s: epley_1rm(s["weight_kg"], s["reps"]))
        out.append(ExerciseProgress(
            exercise_id=ex_id,
            best_e1rm_kg=epley_1rm(best["weight_kg"], best["reps"]),
            best_set=(best["weight_kg"], best["reps"]),
            sessions=len({s.get("daily_log_id") for s in ex_sets}),
        ))
    out.sort(key=lambda p: p.best_e1rm_kg, reverse=True)
    return out


def option_choice_stats(chosen: list[dict]) -> dict[int, dict[str, int]]:
    """Frecuencia de elección de opciones por slot (para regeneración mensual).

    `chosen`: lista de chosen_options_json, p.ej. [{"1":"A","2":"C"}, ...].
    Devuelve {slot: {opcion: veces}} para conservar las 4–5 más usadas (C.3).
    """
    counters: dict[int, Counter] = {}
    for day in chosen:
        if not day:
            continue
        for slot_str, opt in day.items():
            try:
                slot = int(slot_str)
            except (ValueError, TypeError):
                continue
            counters.setdefault(slot, Counter())[opt] += 1
    return {slot: dict(c.most_common()) for slot, c in counters.items()}


# ------------------------------------------------- ensamblado para la IA ----

@dataclass
class PeriodMetrics:
    """Paquete completo que el backend persiste en periods.metrics_json y
    entrega a la IA en recalibración/análisis. La IA solo lee, nunca recalcula."""

    weight: WeightTrend
    adherence: AdherenceSummary
    exercise_progress: list[ExerciseProgress] = field(default_factory=list)
    option_stats: dict[int, dict[str, int]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "weight": {
                "start_kg": self.weight.start_kg, "end_kg": self.weight.end_kg,
                "delta_kg": self.weight.delta_kg,
                "weekly_rate_kg": self.weight.weekly_rate_kg,
                "mean_kg": self.weight.mean_kg,
                "n_measurements": self.weight.n_measurements,
            },
            "adherence": {
                "days_logged": self.adherence.days_logged,
                "period_days": self.adherence.period_days,
                "log_ratio": self.adherence.log_ratio,
                "diet_yes": self.adherence.diet_yes,
                "diet_partial": self.adherence.diet_partial,
                "diet_no": self.adherence.diet_no,
                "diet_adherence_ratio": self.adherence.diet_adherence_ratio,
                "mean_sleep_h": self.adherence.mean_sleep_h,
                "mean_energy": self.adherence.mean_energy,
                "mean_mood": self.adherence.mean_mood,
                "mean_fatigue": self.adherence.mean_fatigue,
            },
            "exercise_progress": [
                {
                    "exercise_id": p.exercise_id, "best_e1rm_kg": p.best_e1rm_kg,
                    "best_weight_kg": p.best_set[0], "best_reps": p.best_set[1],
                    "sessions": p.sessions,
                }
                for p in self.exercise_progress
            ],
            "option_stats": {str(k): v for k, v in self.option_stats.items()},
        }

```


## `backend/app/services/portal.py`

```python
"""Lógica de presentación del portal del cliente (G.4).

Resuelve "el plan y período vigentes" de un cliente y arma la vista HOY a
partir del plan publicado y los registros del día. Mantener esto fuera del
router permite testearlo y reutilizarlo (p. ej. el documento Word offline de
seguimiento de la Fase 7 parte de la misma estructura día a día).

La vista HOY mapea el día de la semana actual a la sesión de entrenamiento
correspondiente del plan y a las comidas del día (banco flexible: las 7
opciones por slot; estricto: el plato del día).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, Period, Plan

DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DAY_SLUGS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente no analizado (el que el cliente está viviendo)."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def published_plan_for_period(db: Session, period: Period) -> Plan | None:
    return db.get(Plan, period.plan_id)


def latest_published_plan(db: Session, client_id: int) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc())
        .limit(1)
    )


def period_info(period: Period | None, today: date) -> dict | None:
    if period is None:
        return None
    days_total = (period.ends_on - period.starts_on).days + 1
    days_elapsed = max(0, min(days_total, (today - period.starts_on).days + 1))
    days_left = max(0, (period.ends_on - today).days)
    # Cierre disponible desde el día 14 del período (G.4)
    can_close = days_elapsed >= 14 and period.status == "open"
    return {
        "period_id": period.id,
        "period_index": period.period_index,
        "starts_on": period.starts_on,
        "ends_on": period.ends_on,
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "days_left": days_left,
        "can_close": can_close,
        "status": period.status,
    }


def brand_payload(db: Session) -> dict:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return {
            "name": "Tu asesoría", "color_primary": "#6EE7B7",
            "color_secondary": "#8B9DF7", "color_bg": "#0A0A0F",
            "font_family": "Inter", "portal_theme": "dark", "logo_path": None,
        }
    return {
        "name": cfg.name, "color_primary": cfg.color_primary,
        "color_secondary": cfg.color_secondary, "color_bg": cfg.color_bg,
        "font_family": cfg.font_family, "portal_theme": cfg.portal_theme,
        "logo_path": cfg.logo_path,
    }


def _meals_for_today(plan: Plan, client: Client, chosen: dict | None) -> list[dict]:
    """Comidas del día desde el plan. Flexible: 7 opciones/slot. Estricto: plato del día."""
    nutrition = plan.nutrition_json or {}
    meal_defs = nutrition.get("meals", [])  # slots con name/time/target
    bank = nutrition.get("meal_bank") or {}
    mode = client.diet_mode
    chosen = chosen or {}

    slots_out: list[dict] = []
    for mdef in meal_defs:
        slot = mdef["slot"]
        entry = {
            "slot": slot,
            "name": mdef.get("name", f"Comida {slot}"),
            "time": mdef.get("time", ""),
            "target": mdef.get("target", {}),
            "options": [],
            "chosen_key": chosen.get(str(slot)),
        }
        if mode == "flexible_7":
            for s in bank.get("slots", []):
                if s["slot"] == slot:
                    entry["options"] = [
                        {"key": o["key"], "title": o["title"], "macros": o["macros"],
                         "prep_minutes": o.get("prep_minutes"), "tags": o.get("tags", [])}
                        for o in s["options"]
                    ]
        elif mode == "strict":
            # plato del día = el del weekday actual en el menú cerrado
            today_idx = date.today().weekday()
            slug = DAY_SLUGS[today_idx]
            for d in bank.get("days", []):
                if d["day"] == slug:
                    for meal in d["meals"]:
                        if meal["slot"] == slot:
                            dish = meal["dish"]
                            entry["options"] = [{
                                "key": dish.get("key", "A"), "title": dish["title"],
                                "macros": dish["macros"], "prep_minutes": dish.get("prep_minutes"),
                                "tags": dish.get("tags", []),
                            }]
        slots_out.append(entry)
    return slots_out


def _resolve_session(db: Session, sess: dict) -> dict:
    """Convierte una sesión del plan (con exercise_id) en una sesión con nombres
    de ejercicio y vídeo resueltos desde la biblioteca."""
    ex_ids = [e["exercise_id"] for e in sess.get("exercises", [])]
    lib = {
        ex.id: ex
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))
    } if ex_ids else {}
    exercises = []
    for e in sess.get("exercises", []):
        ex = lib.get(e["exercise_id"])
        exercises.append({
            "exercise_id": e["exercise_id"],
            "name": ex.canonical_name if ex else f"Ejercicio {e['exercise_id']}",
            "sets": e["sets"], "rep_range": e["rep_range"], "rir": e.get("rir", ""),
            "rest_sec": e.get("rest_sec", 90),
            "start_weight_hint_kg": e.get("start_weight_hint_kg"),
            "technique_cue": e.get("technique_cue"),
            "video_url": ex.video_url if ex and ex.video_url else None,
        })
    return {
        "day": sess.get("day", ""), "name": sess.get("name", ""),
        "warmup": sess.get("warmup"), "exercises": exercises,
        "cooldown": sess.get("cooldown"),
    }


def _session_for_today(db: Session, plan: Plan, today: date) -> dict | None:
    """Sesión de entrenamiento que toca hoy según el día de la semana.

    Mapea el weekday actual al `day` de las sesiones del plan (que vienen como
    "Lunes", "Martes"…). Si hoy no hay sesión, es día de descanso → None.
    """
    training = plan.training_json or {}
    today_label = DAY_LABELS[today.weekday()].lower()
    for sess in training.get("sessions", []):
        if sess.get("day", "").strip().lower() == today_label:
            return _resolve_session(db, sess)
    return None


def build_training_sessions(db: Session, client: Client) -> list[dict]:
    """TODAS las sesiones del plan vigente, con nombres de ejercicio resueltos.

    Para el selector de sesión del portal (el cliente registra la que ha hecho,
    no solo la del día)."""
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)
    if plan is None:
        return []
    training = plan.training_json or {}
    return [_resolve_session(db, s) for s in training.get("sessions", [])]


def build_today_view(db: Session, client: Client, today: date) -> dict:
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)

    meals: list[dict] = []
    session = None
    already_logged = False

    if plan is not None:
        chosen = None
        if period is not None:
            log = db.scalar(
                select(DailyLog).where(
                    DailyLog.period_id == period.id, DailyLog.log_date == today
                )
            )
            if log is not None:
                already_logged = True
                chosen = log.chosen_options_json
        meals = _meals_for_today(plan, client, chosen)
        session = _session_for_today(db, plan, today)

    return {
        "date": today,
        "day_label": DAY_LABELS[today.weekday()],
        "period": period_info(period, today),
        "meals": meals,
        "session": session,
        "already_logged": already_logged,
    }

```


## `backend/app/services/scheduler.py`

```python
"""Scheduler de tareas programadas (APScheduler).

Un único job diario que ejecuta el mantenimiento de la máquina de estados y los
recordatorios. Corre en un BackgroundScheduler (hilo aparte) con la zona horaria
de settings.tz (Europe/Madrid por defecto).

El job abre su PROPIA sesión de base de datos (no comparte la de los requests).
`misfire_grace_time` y `coalesce` evitan ejecuciones acumuladas si el proceso
estuvo caído; `max_instances=1` impide solapamiento. Como el job es idempotente
(jobs.run_daily_maintenance), reejecutar el mismo día es seguro.

El arranque/parada se engancha al lifespan de FastAPI (main.py).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db import SessionLocal
from app.services.jobs import run_daily_maintenance

logger = logging.getLogger("scheduler")

DAILY_HOUR = 6   # 06:00 hora local: tras el cierre natural del día anterior
DAILY_MINUTE = 30

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    db = SessionLocal()
    try:
        summary = run_daily_maintenance(db)
        logger.info("mantenimiento diario: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en el mantenimiento diario")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=settings.tz)
    sched.add_job(
        _daily_job,
        trigger=CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        id="daily_maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    sched.start()
    logger.info("scheduler iniciado (job diario %02d:%02d %s)", DAILY_HOUR, DAILY_MINUTE, settings.tz)
    _scheduler = sched
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None

```


## `backend/app/services/state_machine.py`

```python
"""Máquina de estados del cliente (G.2).

    onboarding → active → awaiting_feedback
              → (at_risk si +4 días sin cerrar tras fin de período
                 o <30% de registros a día 10)
              → review_pending → active …
    inactive (manual o >30 días sin actividad)

Diseño en dos capas:

1. `evaluate_transition(...)` — FUNCIÓN PURA: dado el estado actual y unos
   hechos (fechas, conteo de registros, si el período está cerrado…), decide
   el nuevo estado y el motivo. Sin DB, sin emails: 100% testable.

2. `apply_daily_transitions(db, ...)` — capa con efectos: lee los clientes,
   calcula los hechos desde la DB, llama a la función pura y, si hay cambio,
   persiste el estado, registra en audit_log y dispara el email/alerta que
   corresponda. Idempotente: ejecutarla dos veces el mismo día no duplica
   transiciones ni emails (los emails de aviso se controlan por kind+día).

Las transiciones que dependen de eventos (publicar plan → active; enviar
feedback → review_pending→active) las disparan los endpoints/pipeline, no el
scheduler; aquí vive solo lo que depende del paso del tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Umbrales de G.2
AT_RISK_DAYS_AFTER_PERIOD_END = 4   # +4 días sin cerrar tras fin de período
LOG_RATIO_CHECK_DAY = 10            # a día 10 del período
LOG_RATIO_MIN = 0.30               # <30% de registros → at_risk
INACTIVE_DAYS = 30                 # >30 días sin actividad → inactive
REMINDER_DAY = 12                  # recordatorio si no registra (día 12)


@dataclass
class ClientFacts:
    """Hechos observables de un cliente, calculados desde la DB."""

    status: str
    has_active_period: bool = False
    period_start: date | None = None
    period_end: date | None = None
    period_closed: bool = False
    days_logged_in_period: int = 0
    last_activity_date: date | None = None  # último log o cierre


@dataclass
class TransitionDecision:
    new_status: str | None      # None = sin cambio
    reason: str = ""
    # Señales para la capa de efectos (no cambian estado pero disparan email):
    send_reminder: bool = False
    notify_coach_at_risk: bool = False


def _period_day(today: date, start: date) -> int:
    """Día del período (1-indexado). Día de inicio = día 1."""
    return (today - start).days + 1


def evaluate_transition(facts: ClientFacts, today: date) -> TransitionDecision:
    """Decide la transición por paso del tiempo. Función pura.

    Orden de prioridad: inactividad > at_risk > recordatorio. Estados terminales
    o gestionados por eventos (onboarding, review_pending) no transicionan aquí.
    """
    status = facts.status

    # inactive: cualquier estado activo con >30 días sin actividad
    if status in ("active", "awaiting_feedback", "at_risk"):
        if facts.last_activity_date is not None:
            idle = (today - facts.last_activity_date).days
            if idle > INACTIVE_DAYS:
                return TransitionDecision("inactive", f"{idle} días sin actividad")

    # onboarding no transiciona por tiempo (espera a publicar plan → evento)
    if status == "onboarding":
        return TransitionDecision(None)

    if status in ("active", "awaiting_feedback"):
        # ¿Período terminado y sin cerrar +4 días? → at_risk
        if facts.period_end is not None and not facts.period_closed:
            days_past_end = (today - facts.period_end).days
            if days_past_end >= AT_RISK_DAYS_AFTER_PERIOD_END:
                return TransitionDecision(
                    "at_risk",
                    f"{days_past_end} días sin cerrar el período",
                    notify_coach_at_risk=True,
                )

        # ¿Baja adherencia a día 10? → at_risk
        if facts.period_start is not None and not facts.period_closed:
            day = _period_day(today, facts.period_start)
            if day >= LOG_RATIO_CHECK_DAY:
                expected = day
                ratio = facts.days_logged_in_period / expected if expected else 0
                if ratio < LOG_RATIO_MIN:
                    return TransitionDecision(
                        "at_risk",
                        f"adherencia {ratio * 100:.0f}% (<{LOG_RATIO_MIN * 100:.0f}%) a día {day}",
                        notify_coach_at_risk=True,
                    )

        # Recordatorio día 12 si aún no ha registrado nada hoy/poco (no cambia estado)
        if (
            status == "active"
            and facts.period_start is not None
            and not facts.period_closed
            and _period_day(today, facts.period_start) == REMINDER_DAY
            and facts.days_logged_in_period < REMINDER_DAY // 2
        ):
            return TransitionDecision(None, "recordatorio día 12", send_reminder=True)

    return TransitionDecision(None)


# valid transitions for event-driven changes (validación defensiva)
VALID_TRANSITIONS = {
    "onboarding": {"active", "inactive"},
    "active": {"awaiting_feedback", "at_risk", "inactive"},
    "awaiting_feedback": {"review_pending", "at_risk", "active", "inactive"},
    "at_risk": {"review_pending", "active", "inactive"},
    "review_pending": {"active", "inactive"},
    "inactive": {"active"},  # reactivación manual
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())

```


## `backend/app/services/storage.py`

```python
"""Almacenamiento de archivos (PARTE I).

Estructura: {STORAGE_PATH}/clients/{id}/photos|documents|uploads/ y /brand/.
Fotos: validación de formato/tamaño y eliminación de EXIF (la geolocalización
de una foto corporal es dato sensible — se re-codifica la imagen sin metadatos).
"""

from __future__ import annotations

import io
import secrets
import shutil
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import settings

MAX_PHOTO_MB = 10
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def storage_root() -> Path:
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def brand_dir() -> Path:
    p = storage_root() / "brand"
    p.mkdir(parents=True, exist_ok=True)
    return p


def client_dir(client_id: int, sub: str | None = None) -> Path:
    p = storage_root() / "clients" / str(client_id)
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


class PhotoValidationError(ValueError):
    """Formato no soportado, archivo corrupto o demasiado grande."""


def save_photo(client_id: int, raw: bytes, sub: str = "photos") -> str:
    """Valida, elimina EXIF re-codificando y guarda. Devuelve la ruta relativa."""
    if len(raw) > MAX_PHOTO_MB * 1024 * 1024:
        raise PhotoValidationError(f"La foto supera {MAX_PHOTO_MB} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")

    fmt = img.format
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))  # píxeles sí, metadatos no
    if fmt == "JPEG" and clean.mode not in ("RGB", "L"):
        clean = clean.convert("RGB")

    name = f"{secrets.token_hex(12)}.{_EXT[fmt]}"
    dest = client_dir(client_id, sub) / name
    params = {"quality": 92} if fmt == "JPEG" else {}
    clean.save(dest, format=fmt, **params)
    return str(dest.relative_to(storage_root()))


MAX_DOC_MB = 25
_DOC_EXT = {"application/pdf": "pdf"}


class DocumentValidationError(ValueError):
    """Documento no soportado o demasiado grande."""


def save_document(client_id: int, raw: bytes, original_name: str) -> str:
    """Guarda un documento (PDF) del cliente. Devuelve la ruta relativa.

    Conserva un nombre legible (saneado) para que el coach lo reconozca, con un
    sufijo aleatorio que evita colisiones. Solo acepta PDF (la anamnesis oficial).
    """
    if len(raw) > MAX_DOC_MB * 1024 * 1024:
        raise DocumentValidationError(f"El documento supera {MAX_DOC_MB} MB")
    if raw[:5] != b"%PDF-":
        raise DocumentValidationError("El archivo no es un PDF válido")

    import re

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", (original_name or "documento").rsplit(".", 1)[0])[:60]
    stem = stem.strip("_") or "documento"
    name = f"{stem}_{secrets.token_hex(4)}.pdf"
    dest = client_dir(client_id, "documents") / name
    dest.write_bytes(raw)
    return str(dest.relative_to(storage_root()))


def list_documents(client_id: int) -> list[dict]:
    """Lista la anamnesis subida del cliente (solo el PDF, más reciente primero).

    Se excluyen los archivos internos (sidecar `_anamnesis_analysis.json` y
    cualquier `_*`) y todo lo que no sea PDF: la web solo debe mostrar la
    anamnesis, y solo hay una por cliente (cada subida reemplaza la anterior).
    """
    folder = storage_root() / "clients" / str(client_id) / "documents"
    if not folder.exists():
        return []
    items = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf" and not f.name.startswith("_"):
            st = f.stat()
            items.append({
                "name": f.name,
                "size_kb": round(st.st_size / 1024),
                "uploaded_at": st.st_mtime,
                "rel_path": str(f.relative_to(storage_root())),
            })
    return sorted(items, key=lambda x: x["uploaded_at"], reverse=True)


def save_brand_logo(raw: bytes, filename_hint: str) -> str:
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError("El logo supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")
    dest = brand_dir() / f"logo.{_EXT[img.format]}"
    img.save(dest, format=img.format)
    return str(dest.relative_to(storage_root()))


def abs_path(rel: str) -> Path:
    """Ruta absoluta segura dentro del storage (evita path traversal)."""
    p = (storage_root() / rel).resolve()
    if not str(p).startswith(str(storage_root().resolve())):
        raise PhotoValidationError("Ruta fuera del almacenamiento")
    return p


def delete_client_tree(client_id: int) -> None:
    """Supresión RGPD: borra todos los archivos del cliente."""
    p = storage_root() / "clients" / str(client_id)
    if p.exists():
        shutil.rmtree(p)

```


## `backend/app/services/swap.py`

```python
"""Swap de ejercicios — solo coach, desde el plan publicado (F.5).

Dos operaciones:

1. `propose_alternatives(...)` — dado un ejercicio del plan y el cliente,
   devuelve 2–3 alternativas de la biblioteca con el MISMO patrón de movimiento
   y músculo primario, filtradas por equipamiento, nivel, lesiones y exclusiones
   (filtro determinista de guardrails). No usa IA: es selección + orden por
   similitud de estímulo (mismo patrón > mismos secundarios > equipamiento).

2. `apply_swap(...)` — sustituye el ejercicio en el plan heredando
   series/reps/RIR/descansos, ajustando start_weight_hint proporcionalmente,
   regenerando los cues desde la biblioteca, recalculando el volumen del grupo y
   revalidando guardrails. Registra el motivo en audit_log y, si es permanente,
   lo añade a las exclusiones del cliente. Crea una nueva VERSIÓN del plan
   (borrador) para que el coach la republique.

Mantener esto fuera del router permite testearlo de forma aislada.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Exercise, Plan
from app.services import guardrails as gr


@dataclass
class Alternative:
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int  # mayor = más parecido


def _client_equipment(client: Client) -> set[str]:
    return set(client.equipment or [])


def _client_excluded(client: Client) -> set[int]:
    return set(client.excluded_exercise_ids or [])


def _client_contraindications(client: Client) -> set[str]:
    # La anamnesis guarda lesiones como texto libre (injuries_notes); no hay un
    # conjunto estructurado de contraindicaciones articulares por cliente. El
    # filtro por patrón/músculo/equipamiento/nivel ya acota fuerte; aquí
    # devolvemos vacío y dejamos que el coach valide el caso clínico.
    return set()


def propose_alternatives(
    db: Session, client: Client, current_exercise_id: int, limit: int = 3
) -> list[Alternative]:
    """Alternativas válidas para sustituir un ejercicio (F.5.1)."""
    current = db.get(Exercise, current_exercise_id)
    if current is None:
        return []

    level_max = {"beginner": 1, "intermediate": 2, "advanced": 3}.get(client.level or "intermediate", 2)
    equipment = _client_equipment(client)
    excluded = _client_excluded(client) | {current_exercise_id}
    contra = _client_contraindications(client)

    # Candidatos del mismo patrón de movimiento (requisito duro F.5.1)
    candidates = db.scalars(
        select(Exercise).where(
            Exercise.movement_pattern == current.movement_pattern,
            Exercise.muscle_primary == current.muscle_primary,
            Exercise.archived.is_(False),
        )
    ).all()

    # Filtro determinista de guardrails (equipamiento, nivel, lesiones, exclusiones)
    as_dicts = [{
        "id": e.id, "movement_pattern": e.movement_pattern, "muscle_primary": e.muscle_primary,
        "muscle_secondary": e.muscle_secondary, "equipment": e.equipment,
        "contraindications": e.contraindications, "level_min": e.level_min,
        "archived": e.archived, "canonical_name": e.canonical_name,
    } for e in candidates]

    valid = gr.filter_exercises_for_client(
        as_dicts, client_contraindications=contra, excluded_ids=excluded,
        equipment_available=equipment, level_max=level_max,
        training_place=client.training_place or "gym",
    )

    # Orden por similitud de estímulo: comparte músculos secundarios + equipamiento
    cur_sec = set(current.muscle_secondary or [])
    cur_eq = set(current.equipment or [])
    out: list[Alternative] = []
    for e in valid:
        sec_overlap = len(cur_sec & set(e.get("muscle_secondary") or []))
        eq_overlap = len(cur_eq & set(e.get("equipment") or []))
        out.append(Alternative(
            exercise_id=e["id"], name=e["canonical_name"],
            movement_pattern=e["movement_pattern"], muscle_primary=e["muscle_primary"],
            equipment=e.get("equipment") or [],
            similarity=sec_overlap * 2 + eq_overlap,
        ))
    out.sort(key=lambda a: a.similarity, reverse=True)
    return out[:limit]


@dataclass
class SwapResult:
    new_plan_id: int
    new_version: int
    group_volume_after: float
    guardrail_flags: list[str]


def apply_swap(
    db: Session,
    *,
    client: Client,
    plan: Plan,
    session_index: int,
    old_exercise_id: int,
    new_exercise_id: int,
    permanent: bool,
    reason: str,
) -> SwapResult:
    """Sustituye un ejercicio creando una nueva versión del plan (borrador).

    Hereda series/reps/RIR/descansos, ajusta el peso orientativo
    proporcionalmente (heurística por nivel del ejercicio), regenera cues desde
    la biblioteca y recalcula/valida el volumen. F.5.2–F.5.4.
    """
    from app.services.audit import log_event

    new_ex = db.get(Exercise, new_exercise_id)
    if new_ex is None:
        raise ValueError("Ejercicio de destino no existe")

    training = copy.deepcopy(plan.training_json or {})
    sessions = training.get("sessions", [])
    if session_index >= len(sessions):
        raise ValueError("Sesión fuera de rango")

    exercises = sessions[session_index].get("exercises", [])
    target = next((e for e in exercises if e["exercise_id"] == old_exercise_id), None)
    if target is None:
        raise ValueError("El ejercicio a sustituir no está en esa sesión")

    # Hereda parámetros; sustituye id y cues
    target["exercise_id"] = new_exercise_id
    target["technique_cue"] = (new_ex.technique_notes or "")[:160]
    target["biomech_cue"] = (new_ex.biomechanics_notes or "")[:160]
    # Ajuste proporcional del peso orientativo por nivel del ejercicio
    old_ex = db.get(Exercise, old_exercise_id)
    if target.get("start_weight_hint_kg") and old_ex:
        factor = 1.0
        if old_ex.level_min and new_ex.level_min:
            factor = old_ex.level_min / max(1, new_ex.level_min)
        target["start_weight_hint_kg"] = round(target["start_weight_hint_kg"] * factor, 1)

    # Nueva versión (borrador) del plan
    last = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.month_index == plan.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    new_plan = Plan(
        client_id=client.id, month_index=plan.month_index, version=last.version + 1,
        status="draft", nutrition_json=plan.nutrition_json, training_json=training,
        education_json=plan.education_json, generated_by="swap",
    )
    db.add(new_plan)
    db.flush()

    # Recalcula volumen del grupo y valida guardrails
    lib = {e.id: {"canonical_name": e.canonical_name, "muscle_primary": e.muscle_primary,
                  "contraindications": e.contraindications}
           for e in db.scalars(select(Exercise))}
    report = gr.check_training(
        training, training_days_declared=client.training_days or len(sessions),
        session_max_min=client.session_max_min or 90,
        client_contraindications=_client_contraindications(client),
        exercise_lookup=lib,
    )
    new_plan.guardrail_flags = report.as_flags()

    group_volume = sum(
        ex["sets"] for s in sessions for ex in s.get("exercises", [])
        if lib.get(ex["exercise_id"], {}).get("muscle_primary") == new_ex.muscle_primary
    )

    # Exclusión permanente
    if permanent:
        excluded = list(_client_excluded(client))
        if old_exercise_id not in excluded:
            excluded.append(old_exercise_id)
            client.excluded_exercise_ids = excluded

    log_event(db, "plan", new_plan.id, "exercise_swapped", {
        "old_exercise_id": old_exercise_id, "new_exercise_id": new_exercise_id,
        "permanent": permanent, "reason": reason, "from_plan": plan.id,
    })
    db.commit()
    return SwapResult(
        new_plan_id=new_plan.id, new_version=new_plan.version,
        group_volume_after=group_volume, guardrail_flags=new_plan.guardrail_flags or [],
    )

```


## `backend/entrypoint.sh`

```bash
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

```


## `backend/requirements.txt`

```text
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

```


## `docker-compose.dev.yml`

```yaml
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

```


## `docker-compose.yml`

```yaml
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

```
