

===== FILE: backend/app/main.py =====

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


===== FILE: backend/app/config.py =====

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


===== FILE: backend/app/db.py =====

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


===== FILE: backend/app/deps.py =====

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


===== FILE: backend/app/security.py =====

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


===== FILE: backend/app/models.py =====

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

    # Cierre / REVISIÓN QUINCENAL (cliente)
    closing_weight_kg: Mapped[float | None] = mapped_column(Float)
    closing_rating: Mapped[int | None] = mapped_column(Integer)  # 1–5 (global, legado)
    closing_hardest: Mapped[str | None] = mapped_column(Text)    # ¿Qué te está costando más? (sec 5)
    closing_questions: Mapped[str | None] = mapped_column(Text)
    closing_waist_cm: Mapped[float | None] = mapped_column(Float)
    closing_hip_cm: Mapped[float | None] = mapped_column(Float)
    closing_arm_cm: Mapped[float | None] = mapped_column(Float)
    closing_thigh_cm: Mapped[float | None] = mapped_column(Float)
    # Sensaciones (sec 2): {energia,hambre,sueno,recuperacion,animo,digestiones} cada 1–5
    closing_feelings_json: Mapped[dict | None] = mapped_column(JSONB)
    adherence_diet_0_10: Mapped[int | None] = mapped_column(Integer)      # Adherencia dieta (sec 3)
    adherence_training_0_10: Mapped[int | None] = mapped_column(Integer)  # Adherencia entreno (sec 3)
    free_meals_count: Mapped[int | None] = mapped_column(Integer)         # Comidas libres/saltadas (sec 3)
    closing_changes: Mapped[str | None] = mapped_column(Text)             # Cambios importantes (sec 4)
    closing_next_goal: Mapped[str | None] = mapped_column(Text)          # Objetivo próximas 2 semanas (sec 6)

    # Pipeline (backend + IA)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB)
    ai_analysis_json: Mapped[dict | None] = mapped_column(JSONB)
    ai_photo_analysis: Mapped[str | None] = mapped_column(Text)
    # Momento en que el coach vio esta revisión en Seguimiento (apaga el aviso "!"
    # en la lista de clientes). Nulo = revisión nueva sin ver.
    coach_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    weight_kg: Mapped[float | None] = mapped_column(Float)          # Peso (ayunas)
    sleep_hours: Mapped[float | None] = mapped_column(Float)        # Horas de sueño
    steps: Mapped[str | None] = mapped_column(String(160))         # Pasos (texto libre: "cardio + 4500")
    satiety_1_10: Mapped[float | None] = mapped_column(Float)       # Saciedad (1-10)
    water_liters: Mapped[float | None] = mapped_column(Float)       # Litros de agua
    diet_adherence: Mapped[str | None] = mapped_column(String(10))  # yes|partial|no
    diet_notes: Mapped[str | None] = mapped_column(Text)
    energy_1_5: Mapped[int | None] = mapped_column(Integer)
    mood_1_5: Mapped[int | None] = mapped_column(Integer)
    fatigue_1_5: Mapped[int | None] = mapped_column(Integer)
    free_notes: Mapped[str | None] = mapped_column(Text)            # Comentarios
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


===== FILE: backend/app/schemas/__init__.py =====

from app.schemas import ai, entities  # noqa: F401


===== FILE: backend/app/schemas/ai.py =====

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
    key: str | None = None  # "A".."C" o None; el render numera 1/2/3
    title: str
    ingredients: list[Ingredient] = Field(min_length=1)
    prep: str = ""
    prep_minutes: int = Field(default=0, ge=0, le=120)
    macros: OptionMacros
    tags: list[str] = Field(default_factory=list)


# --- Sistema de EQUIVALENCIAS (réplica del ejemplo del coach para comida/cena) ---
class EquivItem(BaseModel):
    """Un alimento intercambiable con su cantidad equivalente en macros."""
    food: str
    amount: str  # "140 g crudo = 380 g cocido", "150 g", "350 ml + 1 huevo entero"


class EquivGroup(BaseModel):
    name: str               # "Hidratos de carbono (refinados / rápidos)"
    note: str = ""          # ración/guía: "1 ración moderada (200 g aprox). Mejor cocida…"
    items: list[EquivItem] = Field(default_factory=list)  # vacío si el grupo es solo guía


class EquivalenceMeal(BaseModel):
    intro: str = ""         # "Equivalencias calculadas para aportar ~108 g de CH del cereal"
    groups: list[EquivGroup] = Field(min_length=1)


class FlexibleSlot(BaseModel):
    slot: int = Field(ge=1)
    fmt: Literal["options", "equivalences"] = "options"
    options: list[MealOption] = Field(default_factory=list)   # 3 si fmt="options"
    equivalences: EquivalenceMeal | None = None               # si fmt="equivalences"
    # Ejemplos concretos para la tabla "dieta semanal" (1 plato corto por día):
    weekly_examples: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherencia(self) -> "FlexibleSlot":
        if self.fmt == "equivalences":
            if self.equivalences is None:
                raise ValueError(f"slot {self.slot}: fmt=equivalences requiere 'equivalences'")
        elif not (1 <= len(self.options) <= 4):
            raise ValueError(f"slot {self.slot}: fmt=options requiere 1-4 opciones (objetivo 3)")
        return self


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


===== FILE: backend/app/schemas/entities.py =====

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
    # Aviso de revisión quincenal nueva sin ver por el coach (lista de clientes).
    # No viene de la BD; lo rellena el listado. Se apaga al abrir Seguimiento.
    pending_review: bool = False
    pending_review_period: int | None = None


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
    steps: str | None = Field(default=None, max_length=160)          # Pasos (texto libre)
    satiety_1_10: float | None = Field(default=None, ge=0, le=10)    # Saciedad
    water_liters: float | None = Field(default=None, ge=0, le=15)    # Litros de agua
    diet_adherence: DietAdherence | None = None
    diet_notes: str | None = None
    energy_1_5: int | None = Field(default=None, ge=1, le=5)
    mood_1_5: int | None = Field(default=None, ge=1, le=5)
    fatigue_1_5: int | None = Field(default=None, ge=1, le=5)
    free_notes: str | None = None                                    # Comentarios
    chosen_options_json: dict[str, str] | None = None  # {"1": "A"}
    option_feedback_json: dict[str, Literal["up", "down"]] | None = None
    workout_sets: list[WorkoutSetIn] = Field(default_factory=list)


# --------------------------------------------------- revisión quincenal ----
class PeriodCloseIn(BaseModel):
    closing_weight_kg: float = Field(gt=30, lt=300)
    closing_rating: int | None = Field(default=None, ge=1, le=5)  # legado (opcional)
    closing_hardest: str | None = None            # ¿Qué te cuesta más? (sec 5)
    closing_questions: str | None = None
    closing_waist_cm: float | None = Field(default=None, gt=30, lt=250)
    closing_hip_cm: float | None = Field(default=None, gt=30, lt=250)
    closing_arm_cm: float | None = Field(default=None, gt=10, lt=80)
    closing_thigh_cm: float | None = Field(default=None, gt=20, lt=120)
    # Sensaciones (sec 2): {"energia":4,"hambre":3,"sueno":4,"recuperacion":5,"animo":4,"digestiones":3}
    closing_feelings_json: dict[str, int] | None = None
    adherence_diet_0_10: int | None = Field(default=None, ge=0, le=10)
    adherence_training_0_10: int | None = Field(default=None, ge=0, le=10)
    free_meals_count: int | None = Field(default=None, ge=0, le=50)
    closing_changes: str | None = None            # Cambios importantes (sec 4)
    closing_next_goal: str | None = None          # Objetivo próximas 2 semanas (sec 6)


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


===== FILE: backend/alembic/versions/0001_initial.py =====

"""Migración inicial: crea todas las tablas desde Base.metadata.

Decisión declarada: la migración 0001 usa create_all sobre los modelos como
única fuente de verdad (cero riesgo de divergencia modelo↔migración). Las
migraciones siguientes se autogeneran con `alembic revision --autogenerate`.
"""
from alembic import op

from app.db import Base
import app.models  # noqa: F401 — registra todas las tablas en Base.metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())


===== FILE: backend/alembic/versions/0002_tracking_fields.py =====

"""0002: seguimiento diario (pasos/saciedad/litros) + revisión quincenal completa.

Añade columnas a daily_logs y periods para reflejar los documentos de seguimiento
del coach (diario y revisión quincenal). Todas nullable → no rompe filas existentes.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_DAILY = [
    ("steps", sa.String(160)),
    ("satiety_1_10", sa.Float()),
    ("water_liters", sa.Float()),
]
_PERIOD = [
    ("closing_feelings_json", JSONB()),
    ("adherence_diet_0_10", sa.Integer()),
    ("adherence_training_0_10", sa.Integer()),
    ("free_meals_count", sa.Integer()),
    ("closing_changes", sa.Text()),
    ("closing_next_goal", sa.Text()),
]


def upgrade() -> None:
    for name, coltype in _DAILY:
        op.add_column("daily_logs", sa.Column(name, coltype, nullable=True))
    for name, coltype in _PERIOD:
        op.add_column("periods", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _ in _PERIOD:
        op.drop_column("periods", name)
    for name, _ in _DAILY:
        op.drop_column("daily_logs", name)


===== FILE: backend/alembic/versions/0003_coach_reviewed_at.py =====

"""0003: periods.coach_reviewed_at — marca cuándo el coach vio la revisión.

Apaga el aviso "!" de la lista de clientes en cuanto el coach abre Seguimiento.
Nullable → no rompe filas existentes.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("periods", sa.Column("coach_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("periods", "coach_reviewed_at")


===== FILE: backend/app/seeds/run.py =====

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


===== FILE: backend/app/seeds/exercises_data.py =====

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
