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
    goal_type: Mapped[str | None] = mapped_column(String(20))  # fat_loss|muscle_gain|recomp|maintenance|injury_recovery
    goal_weight_kg: Mapped[float | None] = mapped_column(Float)
    goal_deadline: Mapped[date | None] = mapped_column(Date)
    # Etapa del objetivo: cuándo empezó (para la alerta de los 45 días) y hasta
    # cuándo está pospuesta la revisión de objetivo ("mantener objetivo actual").
    goal_started_on: Mapped[date | None] = mapped_column(Date)
    goal_review_snoozed_on: Mapped[date | None] = mapped_column(Date)
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
    goal_type: Mapped[str | None] = mapped_column(String(20))  # objetivo que servía este plan (archivo)
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
    color_primary: Mapped[str] = mapped_column(String(9), default="#E8833A")   # naranja DQ
    color_secondary: Mapped[str] = mapped_column(String(9), default="#2E5E8C") # azul DQ
    color_bg: Mapped[str] = mapped_column(String(9), default="#0B111C")        # azul noche
    font_family: Mapped[str] = mapped_column(String(40), default="Inter")
    tagline: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(160))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    contact_web: Mapped[str | None] = mapped_column(String(200))
    docs_theme: Mapped[str] = mapped_column(String(10), default="light")  # light|dark
    portal_theme: Mapped[str] = mapped_column(String(10), default="light")  # light|dark


# --------------------------------------------------- push_subscriptions ----
class PushSubscription(Base):
    """Suscripción Web Push de un dispositivo del cliente (portal).

    Un cliente puede tener varias (móvil + tablet). `endpoint` es la URL única
    que da el servicio de push del navegador; `p256dh` y `auth` son las claves
    de cifrado del payload. Si el servicio responde 404/410 al enviar, la
    suscripción caducó y se borra la fila.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
