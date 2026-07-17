"""Schemas Pydantic de entidades para la API (request/response).

Espejados manualmente en frontend/src/types.ts (regla A.1.5).
"""


import re
from datetime import date, datetime
from typing import Literal

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
# Paquete/plan contratado por el cliente (define qué incluye y cómo se le entrega):
#   start = solo nutrición · full = nutrición + entreno · pro = full + contacto directo
PackageTier = Literal["start", "full", "pro"]
# Duración contratada del plan: mensual, trimestral o semestral. Cada paquete
# tiene un precio de Stripe por duración (9 combinaciones en total).
BillingPeriod = Literal["1m", "3m", "6m"]
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
    billing_period: BillingPeriod = "1m"


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
    daily_activity_level: str | None = None  # sedentary|light|active|very_active
    session_max_min: int = Field(ge=30, le=180)
    training_place: TrainingPlace
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
    diet_mode: DietMode
    strict_free_meal_enabled: bool = False
    # RGPD
    consent_accepted: Literal[True]  # checkbox obligatorio


class ClientUpdate(BaseModel):
    """Edición por el coach (anamnesis editable con audit trail)."""

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
    strict_free_meal_enabled: bool | None = None
    auto_pilot: bool | None = None
    emails_enabled: bool | None = None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    package_tier: PackageTier = "pro"
    billing_period: BillingPeriod = "1m"
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
    video_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] = Field(default_factory=list)

    # El portal muestra el vídeo (enlace) y la imagen del ejercicio: exige http(s)
    # para no guardar un javascript:/data: que se renderizaría como enlace/imagen.
    _v_urls = field_validator("video_url", "image_url")(_http_url_or_none)


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
    _v_urls = field_validator("video_url", "image_url")(_passthrough)


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
    portal_theme: Theme = "light"


class BrandConfigOut(BrandConfigIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    logo_path: str | None
    contact_email: str | None  # relaja EmailStr al leer de DB


# ------------------------------------------ productos recomendados (portal) ----
# Catálogo único que el coach gestiona y el cliente ve en la sección "Recursos".
ProductCategory = Literal["suplemento", "material", "otro"]


def _clean_discount_code(v: str | None) -> str | None:
    """Recorta espacios; vacío → None (permite 'borrar' el código en un PATCH)."""
    if v is None:
        return None
    v = v.strip()
    return v or None


class RecommendedProductIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=300)
    url: str = Field(min_length=3, max_length=500)
    category: ProductCategory = "suplemento"
    image_url: str | None = Field(default=None, max_length=500)  # URL externa (opcional)
    # Código de descuento de la marca (afiliación): visible y copiable en el portal.
    discount_code: str | None = Field(default=None, max_length=40)
    active: bool = True
    # sort_order NO se pide al crear: el alta añade al final; se reordena por PATCH.

    _v_url = field_validator("url")(_http_url_required)
    _v_image = field_validator("image_url")(_http_url_or_none)
    _v_code = field_validator("discount_code")(_clean_discount_code)


class RecommendedProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, min_length=3, max_length=500)
    category: ProductCategory | None = None
    image_url: str | None = Field(default=None, max_length=500)
    discount_code: str | None = Field(default=None, max_length=40)
    active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100000)

    _v_url = field_validator("url")(_http_url_required)
    _v_image = field_validator("image_url")(_http_url_or_none)
    _v_code = field_validator("discount_code")(_clean_discount_code)


class RecommendedProductOut(BaseModel):
    """Salida con la imagen EFECTIVA ya resuelta (archivo subido o URL externa)."""

    id: int
    title: str
    description: str | None
    url: str
    category: str
    image_url: str | None  # URL para mostrar (servida si hay subida, si no la externa)
    discount_code: str | None
    has_upload: bool        # ¿tiene imagen subida? (el formulario del coach lo necesita)
    active: bool
    sort_order: int


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
    # Resultado del envío automático del acceso al portal al dar de alta:
    # sent | disabled | failed | error | no_email | None (no intentado).
    portal_access: str | None = None


class ExerciseUpdate(BaseModel):
    """PATCH parcial de la biblioteca (incluye video_url editable, F.3)."""

    canonical_name: str | None = Field(default=None, min_length=3, max_length=160)
    aliases: list[str] | None = None
    muscle_primary: str | None = None
    muscle_secondary: list[str] | None = None
    movement_pattern: str | None = None
    equipment: list[str] | None = None
    level_min: int | None = Field(default=None, ge=1, le=3)
    video_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)
    technique_notes: str | None = None
    biomechanics_notes: str | None = None
    contraindications: list[str] | None = None

    _v_urls = field_validator("video_url", "image_url")(_http_url_or_none)


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
    # Paquete del cliente: el portal se adapta (Start no tiene entreno).
    package_tier: PackageTier
    has_plan: bool
    period: PortalPeriodInfo | None
    brand: PortalBrand


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


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)


class PushPendingOut(BaseModel):
    """GET /api/p/{token}/push/pending — para sincronizar el badge al abrir."""

    diary: bool
    workout: bool
    quincenal: bool
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


# --------------------------------------------------- recursos del portal ----
class ResourceExerciseVideo(BaseModel):
    """Vídeo de un ejercicio de la rutina del cliente (título + imagen + vídeo)."""

    exercise_id: int
    title: str
    muscle: str | None = None
    video_url: str
    image_url: str | None = None  # miniatura (subida por el coach o portada YouTube)
    technique_notes: str | None = None


class ResourceProduct(BaseModel):
    """Producto recomendado (título + imagen + enlace + código de descuento)."""

    id: int
    title: str
    description: str | None = None
    url: str
    category: str
    image_url: str | None = None
    discount_code: str | None = None


class PortalResourcesOut(BaseModel):
    """GET /api/p/{token}/resources — vídeos de sus ejercicios + productos."""

    exercise_videos: list[ResourceExerciseVideo]
    products: list[ResourceProduct]


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
