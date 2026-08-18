"""Schemas Pydantic de entidades para la API (request/response).

Espejados manualmente en frontend/src/types.ts (regla A.1.5).
"""


import re
from datetime import date, datetime
from typing import Annotated, Literal

from app import branding
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _http_url_or_none(v: str | None) -> str | None:
    """Normaliza una URL OPCIONAL exigiendo http/https (bloquea javascript:, data:…
    que el portal renderizaría como enlace o imagen). Vacío → None (permite
    'borrar' el campo, p. ej. quitar la imagen externa)."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not re.match(r"^https?://", v, re.IGNORECASE):
        raise ValueError("La URL debe empezar por http:// o https://")
    return v


def _http_url_required(v: str | None) -> str | None:
    """Como `_http_url_or_none` pero para campos OBLIGATORIOS: un valor solo de
    espacios NO se convierte en None (rompería un NOT NULL con un 500); se rechaza
    con 422. None se conserva (en un PATCH = 'sin cambio')."""
    if v is None:
        return None
    v = v.strip()
    if not re.match(r"^https?://", v, re.IGNORECASE):
        raise ValueError("La URL debe empezar por http:// o https://")
    return v

# Literales compartidos
Sex = Literal["male", "female"]
GoalType = Literal["fat_loss", "muscle_gain", "recomp", "maintenance", "injury_recovery"]
Level = Literal["beginner", "intermediate", "advanced"]
TrainingPlace = Literal["gym", "home", "outdoor"]
DietMode = Literal["flexible_7", "strict"]
# Patrón dietético ético/religioso: se respeta al 100% (violación = veto).
DietPattern = Literal["vegano", "vegetariano", "pescetariano", "sin_cerdo", "halal", "kosher"]
# Paquete/plan contratado por el cliente (define qué incluye y cómo se le entrega):
#   start = solo nutrición · full = nutrición + entreno · pro = full + contacto directo
PackageTier = Literal["nutri", "train", "full"]
# Duración contratada del plan: mensual, trimestral o semestral (cada paquete
# tiene un precio de Stripe por duración, 9 combinaciones) + "oferta": la
# promoción de captación del plan Full — 1 € el primer mes y después
# 120 €/mes en SUSCRIPCIÓN de Stripe (renovación automática).
# "unico" = PAGO ÚNICO (el modelo de Professional). Las duraciones
# mensuales y la oferta son del motor y se conservan para instancias que
# vendan por suscripción; esta marca solo usa "unico".
BillingPeriod = Literal["unico", "1m", "3m", "6m", "oferta"]
PaymentStatus = Literal["pending", "paid"]
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
    package_tier: PackageTier = "full"
    billing_period: BillingPeriod = "unico"


class AnamnesisSubmit(BaseModel):
    """Cuestionario inicial público del cliente (vía portal_token).

    El motor admite el cuestionario LARGO (todos los campos) y el CORTO de
    Professional: lo que un servicio concreto no pregunta llega vacío y el
    backend usa el valor prudente de siempre. Solo son obligatorios los datos
    sin los que NO se puede calcular nada (sexo, edad, altura, peso, objetivo)
    y el consentimiento."""

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
    level: Level = "beginner"
    # Objetivos
    goal_type: GoalType
    goal_weight_kg: float | None = Field(default=None, gt=30, lt=300)
    goal_deadline: date | None = None
    priority_zones: str | None = None  # se guarda en lifestyle_notes etiquetado
    # Entrenamiento — opcionales: un cliente de SOLO DIETA no los responde.
    training_days: int | None = Field(default=None, ge=2, le=6)
    daily_activity_level: str | None = None  # sedentary|light|active|very_active
    session_max_min: int | None = Field(default=None, ge=30, le=180)
    training_place: TrainingPlace | None = None
    equipment: list[str] = Field(default_factory=list)
    # Nutrición — número/horario de comidas OPCIONALES: si el cliente lo
    # delega ("lo decidís vosotros"), la IA elige el reparto óptimo.
    meals_per_day: int | None = Field(default=None, ge=2, le=6)
    meal_schedule: list[MealScheduleItem] = Field(default_factory=list)
    food_allergies: list[str] = Field(default_factory=list)
    food_dislikes: list[str] = Field(default_factory=list)
    food_likes: list[str] = Field(default_factory=list)
    lifestyle_notes: str | None = None
    current_supplements: str | None = None
    diet_mode: DietMode = "flexible_7"
    diet_pattern: DietPattern | None = None
    strict_free_meal_enabled: bool = False
    # RGPD
    consent_accepted: Literal[True]  # checkbox obligatorio


class ClientUpdate(BaseModel):
    """Edición por el coach (anamnesis editable con audit trail)."""

    # Estado del ciclo (reactivar inactivos / archivar): el endpoint lo valida
    # SIEMPRE contra la máquina de estados (can_transition) antes de aplicarlo.
    status: str | None = None
    full_name: str | None = None
    phone: str | None = None
    package_tier: PackageTier | None = None
    billing_period: BillingPeriod | None = None
    payment_status: PaymentStatus | None = None
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
    daily_activity_level: str | None = None  # sedentary|light|active|very_active
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
    diet_pattern: DietPattern | None = None
    strict_free_meal_enabled: bool | None = None
    auto_pilot: bool | None = None
    emails_enabled: bool | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    package_tier: PackageTier = "full"
    billing_period: BillingPeriod = "unico"
    payment_status: PaymentStatus = "paid"
    paid_at: datetime | None = None
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
    daily_activity_level: str | None = None
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
    goal_started_on: date | None = None
    goal_review_snoozed_on: date | None = None
    food_allergies: list[str] | None
    food_dislikes: list[str] | None
    food_likes: list[str] | None
    lifestyle_notes: str | None
    current_supplements: str | None
    diet_mode: DietMode | None
    diet_pattern: DietPattern | None = None
    # Peso de referencia ÚNICO (último registro > cierre > actual > inicial):
    # lo calcula el GET del cliente para que el editor valide topes con el
    # MISMO peso que usará el backend al guardar (auditoría de ediciones).
    reference_weight_kg: float | None = None
    strict_free_meal_enabled: bool
    status: ClientStatus
    auto_pilot: bool
    emails_enabled: bool
    consent_signed_at: datetime | None
    portal_access_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Aviso de revisión quincenal nueva sin ver por el coach (lista de clientes).
    # No viene de la BD; lo rellena el listado. Se apaga al abrir Seguimiento.
    pending_review: bool = False
    pending_review_period: int | None = None
    # Rellenados por el listado para las CARPETAS de la cartera:
    # ¿tiene planificación publicada? y nº de la última revisión recibida.
    has_published_plan: bool = False
    review_period_index: int | None = None


# ------------------------------------------------------------ exercises ----
class ExerciseIn(BaseModel):
    canonical_name: str = Field(min_length=3, max_length=160)
    aliases: list[str] = Field(default_factory=list)
    muscle_primary: str
    muscle_secondary: list[str] = Field(default_factory=list)
    movement_pattern: str
    equipment: list[str] = Field(default_factory=list)
    level_min: int = Field(ge=1, le=3)
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] = Field(default_factory=list)

    # El portal muestra el vídeo (enlace) y la imagen del ejercicio: exige http(s)
    # para no guardar un javascript:/data: que se renderizaría como enlace/imagen.



def _passthrough(v):
    return v


class ExerciseOut(ExerciseIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    archived: bool

    # SALIDA tolerante: anula el validador http(s) heredado de ExerciseIn. Los
    # datos LEGADOS (URLs guardadas antes de existir la validación) no pueden
    # romper el GET de la biblioteca — la validación estricta es de ENTRADA; el
    # portal además re-filtra las URLs al construir los recursos.



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
    # `docs_theme` se retiró del contrato: la columna existe en DB pero ningún
    # generador de documentos la consumía (control muerto — auditoría #6). Si
    # algún día los Word tienen tema oscuro, reintroducir aquí Y en docs/.
    portal_theme: Theme = branding.PORTAL_THEME


class BrandConfigOut(BrandConfigIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    logo_path: str | None
    links_photo_path: str | None = None
    plans_photo_path: str | None = None
    contact_email: str | None  # relaja EmailStr al leer de DB


# ------------------------------------------------- registro público (landing) ----
class PublicRegisterIn(BaseModel):
    """Registro self-serve desde /planes: datos mínimos antes de ir al pago."""

    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=40)
    tier: PackageTier
    period: BillingPeriod = "unico"

    @field_validator("tier", mode="before")
    @classmethod
    def _tier_legado(cls, v):
        # Una pestaña de /planes abierta ANTES del deploy envía los nombres
        # antiguos ("start"/"pro"): se traducen en vez de responder 422 en pleno
        # embudo de captación.
        if isinstance(v, str):
            return {"start": "nutri", "pro": "full"}.get(v.strip().lower(), v)
        return v


class LandingOut(BaseModel):
    """GET /api/public/landing — datos públicos de la página de enlaces (/professional)."""

    name: str
    tagline: str | None
    color_primary: str
    color_secondary: str
    color_bg: str
    logo_url: str | None
    links_photo_url: str | None
    plans_photo_url: str | None = None
    # Contacto público del coach (Marca → contacto): /planes abre WhatsApp con
    # este teléfono para pedir información (los precios no se publican).
    contact_phone: str | None = None
    contact_email: str | None = None


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
    # Valores acotados 1-5: un 0 o un 99 distorsionaría la nota /10 del coach y
    # la fatiga que lee el motor quincenal.
    closing_feelings_json: dict[str, Annotated[int, Field(ge=1, le=5)]] | None = None
    adherence_diet_0_10: int | None = Field(default=None, ge=0, le=10)
    adherence_training_0_10: int | None = Field(default=None, ge=0, le=10)
    free_meals_count: int | None = Field(default=None, ge=0, le=50)
    closing_changes: str | None = None            # Cambios importantes (sec 4)
    closing_next_goal: str | None = None          # Objetivo próximas 2 semanas (sec 6)


class PortalMeasurementsIn(BaseModel):
    """Medidas del cliente en SEGUIMIENTO CONTINUO (sin cierre quincenal).

    El cliente actualiza su evolución corporal cuando quiere: peso, perímetros
    y cómo se encuentra. Todos los campos son opcionales — manda solo lo que
    haya medido ese día (mismo criterio que el diario: lo que no se toca, no
    viaja y no se pisa)."""

    weight_kg: float | None = Field(default=None, gt=30, lt=300)
    waist_cm: float | None = Field(default=None, gt=30, lt=250)
    hip_cm: float | None = Field(default=None, gt=30, lt=250)
    arm_cm: float | None = Field(default=None, gt=10, lt=80)
    thigh_cm: float | None = Field(default=None, gt=20, lt=120)
    feelings_json: dict[str, Annotated[int, Field(ge=1, le=5)]] | None = None
    notes: str | None = Field(default=None, max_length=2000)


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
    # Resultado del envío automático del acceso al portal al dar de alta:
    # sent | disabled | failed | error | no_email | None (no intentado).
    portal_access: str | None = None


class ExerciseUpdate(BaseModel):
    """PATCH parcial de la biblioteca."""

    canonical_name: str | None = Field(default=None, min_length=3, max_length=160)
    aliases: list[str] | None = None
    muscle_primary: str | None = None
    muscle_secondary: list[str] | None = None
    movement_pattern: str | None = None
    equipment: list[str] | None = None
    level_min: int | None = Field(default=None, ge=1, le=3)
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] | None = None




class AnamnesisStateOut(BaseModel):
    """Estado público del cuestionario (GET /api/p/{token}) — datos mínimos.

    `package_tier` permite al formulario preguntar SOLO lo que aplica: a un
    cliente de dieta no se le piden días de entreno ni material."""

    first_name: str
    package_tier: PackageTier = "full"
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
    # Paquete del cliente: el portal se adapta (Start no tiene entreno).
    package_tier: PackageTier
    has_plan: bool
    period: PortalPeriodInfo | None
    brand: PortalBrand
    # Tras enviar la revisión: recordatorio de confirmar el envío de las fotos
    # de progreso al coach (persiste hasta que el cliente lo confirme).
    photos_pending: bool = False
    # Onboarding sin anamnesis: el portal muestra el camino a /anamnesis/{token}
    # (antes el cliente veía pestañas vacías sin ninguna ruta — auditoría).
    needs_anamnesis: bool = False
    # Fecha de NEGOCIO (today_local, zona del coach): Diario y Entreno registran
    # sobre ella, no sobre el reloj del dispositivo — un cliente de viaje con
    # otra zona horaria ya no crea el registro en un día que el backend
    # considera distinto (422 "fuera del período" o hueco en la adherencia).
    today: date | None = None


class PushKeyOut(BaseModel):
    """GET /api/p/{token}/push/public-key — clave pública VAPID para subscribe."""

    enabled: bool
    public_key: str | None = None


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscribeIn(BaseModel):
    """Cuerpo = PushSubscription.toJSON() del navegador."""

    endpoint: str = Field(min_length=10, max_length=2000)
    keys: PushSubscriptionKeys
    # True = resuscripción AUTOMÁTICA al abrir el portal (mantenimiento): si el
    # endpoint ya pertenece a OTRO cliente no lo roba — solo el gesto explícito
    # de activar (resync=False) puede reasignar el dispositivo.
    resync: bool = False


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)


class PushPendingOut(BaseModel):
    """GET /api/p/{token}/push/pending — para sincronizar el badge al abrir."""

    diary: bool
    workout: bool
    quincenal: bool
    photos: bool = False  # confirmar envío de fotos de progreso tras la revisión
    plan: bool = False  # planificación nueva sin ver (suma 1 al badge)
    count: int


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
    # Peso sugerido AJUSTADO a la semana del mesociclo (espejo de types.ts)
    week_weight_hint_kg: float | None = None
    technique_cue: str | None


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
