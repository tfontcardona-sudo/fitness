/**
 * types.ts — espejo manual de los schemas Pydantic del backend (regla A.1.5).
 *
 * Fuente de verdad: backend/app/schemas/ai.py y backend/app/schemas/entities.py.
 * Si cambia un schema en el backend, este archivo se actualiza en el mismo commit.
 */

// ===================================================== literales comunes ====
export type Sex = "male" | "female";
export type GoalType = "fat_loss" | "muscle_gain" | "recomp" | "maintenance" | "injury_recovery";
export type Level = "beginner" | "intermediate" | "advanced";
export type TrainingPlace = "gym" | "home" | "outdoor";
export type DietMode = "flexible_7" | "strict";
export type PackageTier = "start" | "full" | "pro";
// Duración contratada del plan (decide el precio de Stripe que se cobra):
// mensual, trimestral o semestral.
export type BillingPeriod = "1m" | "3m" | "6m";
export type PaymentStatus = "pending" | "paid";
export type ClientStatus =
  | "onboarding"
  | "active"
  | "awaiting_feedback"
  | "at_risk"
  | "review_pending"
  | "inactive";
export type DietAdherence = "yes" | "partial" | "no";
export type PhotoKind = "front" | "side" | "back" | "detail";
export type Theme = "light" | "dark";
export type PlanStatus = "draft" | "published" | "superseded";
export type PeriodStatus = "open" | "closed" | "analyzed";
export type OptionKey = "A" | "B" | "C" | "D" | "E" | "F" | "G";

// ========================================== salida IA ① — núcleo del plan ====
export interface Macros {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealSlotTarget {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealSlotDef {
  slot: number;
  name: string;
  time: string;
  target: MealSlotTarget;
}

export interface Supplement {
  name: string;
  dose: string;
  timing: string;
  evidence_note: string;
}

export interface NutritionCore {
  tdee_kcal: number;
  target_kcal: number;
  rationale: string;
  macros: Macros;
  meals: MealSlotDef[];
  supplements: Supplement[];
  flexibility_rules: string[];
  refeed_or_break: string | null;
}

export interface WeeklyProgressionWeek {
  week: 1 | 2 | 3 | 4;
  intent: string;
  load_pct: number;
  rir_target: string;
  volume_note: string;
}

export interface PlannedExercise {
  exercise_id: number;
  sets: number;
  rep_range: string;
  rir: string;
  tempo: string | null;
  rest_sec: number;
  start_weight_hint_kg: number | null;
  progression_rule: string;
  technique_cue: string;
  biomech_cue: string;
  /** Indicaciones personalizadas del coach (capacidades/limitaciones). */
  coach_notes?: string | null;
}

export interface TrainingSession {
  day: string;
  name: string;
  warmup: string;
  exercises: PlannedExercise[];
  cooldown: string;
}

export interface CardioSession {
  type: "liss" | "hiit";
  minutes: number;
  times_per_week: number;
  notes: string | null;
}

export interface CardioPlan {
  daily_steps: number;
  sessions: CardioSession[];
}

export interface TrainingCore {
  split_name: string;
  split_rationale: string;
  weekly_progression: WeeklyProgressionWeek[];
  sessions: TrainingSession[];
  cardio: CardioPlan;
  deload_instructions: string;
}

export interface PlanCoreOutput {
  nutrition: NutritionCore;
  training: TrainingCore;
}

// ======================================= salida IA ② — banco de comidas ====
export interface Ingredient {
  food: string;
  grams: number; // siempre en CRUDO
  household: string;
}

export interface OptionMacros {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealOption {
  key: OptionKey | null; // null en modo strict
  title: string;
  ingredients: Ingredient[];
  prep: string;
  prep_minutes: number;
  macros: OptionMacros;
  tags: string[];
}

export interface FlexibleSlot {
  slot: number;
  options: MealOption[]; // exactamente 7, keys A-G
}

export interface MealsFlexibleOutput {
  mode: "flexible_7";
  slots: FlexibleSlot[];
}

export interface StrictDayMeal {
  slot: number;
  dish: MealOption;
}

export interface StrictDay {
  day:
    | "lunes"
    | "martes"
    | "miercoles"
    | "jueves"
    | "viernes"
    | "sabado"
    | "domingo";
  meals: StrictDayMeal[];
}

export interface MealsStrictOutput {
  mode: "strict";
  days: StrictDay[]; // exactamente 7, lunes→domingo
  free_meal_guidelines: string | null;
}

export type MealsOutput = MealsFlexibleOutput | MealsStrictOutput;

// ==================================== salida IA ③ — contenido educativo ====
export interface EducationPill {
  topic: string;
  for_client: string;
}

export interface BiomechPattern {
  pattern: string;
  cues: string[];
  why: string;
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface EducationOutput {
  pills: EducationPill[];
  biomech_by_pattern: BiomechPattern[];
  faq: FaqItem[];
}

// ================================================== entidades de la API ====
export interface MealScheduleItem {
  slot: number;
  name: string;
  time: string;
}

export interface ClientCreate {
  full_name: string;
  email: string;
  phone?: string | null;
  package_tier?: PackageTier;
  billing_period?: BillingPeriod;
}

export interface AnamnesisSubmit {
  sex: Sex;
  birth_date: string; // ISO date
  height_cm: number;
  start_weight_kg: number;
  body_fat_pct?: number | null;
  injuries_notes?: string | null;
  medical_notes?: string | null;
  medication_notes?: string | null;
  sport_history?: string | null;
  level: Level;
  goal_type: GoalType;
  goal_weight_kg?: number | null;
  goal_deadline?: string | null;
  priority_zones?: string | null;
  training_days: number;
  session_max_min: number;
  training_place: TrainingPlace;
  equipment: string[];
  meals_per_day: number;
  meal_schedule: MealScheduleItem[];
  food_allergies: string[];
  food_dislikes: string[];
  food_likes: string[];
  lifestyle_notes?: string | null;
  current_supplements?: string | null;
  diet_mode: DietMode;
  strict_free_meal_enabled: boolean;
  consent_accepted: true;
}

export interface ClientOut {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  package_tier: PackageTier;
  billing_period: BillingPeriod;
  payment_status: PaymentStatus;
  paid_at: string | null;
  sex: Sex | null;
  birth_date: string | null;
  height_cm: number | null;
  start_weight_kg: number | null;
  current_weight_kg: number | null;
  body_fat_pct: number | null;
  goal_type: GoalType | null;
  goal_weight_kg: number | null;
  goal_deadline: string | null;
  level: Level | null;
  training_days: number | null;
  daily_activity_level: string | null;
  session_max_min: number | null;
  training_place: TrainingPlace | null;
  equipment: string[] | null;
  excluded_exercise_ids: number[] | null;
  injuries_notes: string | null;
  medical_notes: string | null;
  medication_notes: string | null;
  sport_history: string | null;
  meals_per_day: number | null;
  meal_schedule: MealScheduleItem[] | null;
  goal_started_on: string | null;
  goal_review_snoozed_on: string | null;
  food_allergies: string[] | null;
  food_dislikes: string[] | null;
  food_likes: string[] | null;
  lifestyle_notes: string | null;
  current_supplements: string | null;
  diet_mode: DietMode | null;
  strict_free_meal_enabled: boolean;
  status: ClientStatus;
  auto_pilot: boolean;
  emails_enabled: boolean;
  consent_signed_at: string | null;
  portal_access_sent_at?: string | null;
  created_at: string;
  updated_at: string;
  pending_review?: boolean;
  pending_review_period?: number | null;
  has_published_plan?: boolean;
  review_period_index?: number | null;
}

export interface ExerciseOut {
  id: number;
  canonical_name: string;
  aliases: string[];
  muscle_primary: string;
  muscle_secondary: string[];
  movement_pattern: string;
  equipment: string[];
  level_min: 1 | 2 | 3;
  video_url: string | null;
  image_url: string | null;
  technique_notes: string | null;
  biomechanics_notes: string | null;
  contraindications: string[];
  archived: boolean;
}

// --- Productos recomendados (sección Recursos del portal) ---
export type ProductCategory = "suplemento" | "material" | "otro";

export interface RecommendedProductOut {
  id: number;
  title: string;
  description: string | null;
  url: string;
  category: string;
  image_url: string | null; // URL efectiva (subida servida por la API o externa)
  has_upload: boolean;
  active: boolean;
  sort_order: number;
  discount_code: string | null;
}

export interface RecommendedProductIn {
  title: string;
  description?: string | null;
  url: string;
  category?: ProductCategory;
  image_url?: string | null;
  /** Código de descuento de la marca (afiliación), copiable en el portal. */
  discount_code?: string | null;
  active?: boolean;
}

export interface RecommendedProductUpdate {
  title?: string;
  description?: string | null;
  url?: string;
  category?: ProductCategory;
  image_url?: string | null;
  active?: boolean;
  sort_order?: number;
  discount_code?: string | null;
}

export interface BrandConfigOut {
  id: number;
  name: string;
  logo_path: string | null;
  color_primary: string;
  color_secondary: string;
  color_bg: string;
  font_family: "Inter" | "Montserrat" | "Poppins" | "DM Sans" | "Plus Jakarta Sans";
  tagline: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  contact_web: string | null;
  docs_theme: Theme;
  portal_theme: Theme;
  // Página pública de enlaces (/dq): foto de fondo + afiliación del partner.
  links_photo_path: string | null;
  partner_store_url: string | null;
  partner_discount_code: string | null;
}

/** GET /api/public/landing — datos públicos de la página de enlaces (/dq). */
export interface LandingOut {
  name: string;
  tagline: string | null;
  color_primary: string;
  color_secondary: string;
  color_bg: string;
  logo_url: string | null;
  links_photo_url: string | null;
  partner_store_url: string | null;
  partner_discount_code: string | null;
}

export interface WorkoutSetIn {
  exercise_id: number;
  set_number: number;
  reps?: number | null;
  weight_kg?: number | null;
  rpe?: number | null;
  notes?: string | null;
}

export interface DailyLogUpsert {
  log_date: string;
  weight_kg?: number | null;
  sleep_hours?: number | null;
  steps?: string | null;
  satiety_1_10?: number | null;
  water_liters?: number | null;
  diet_adherence?: DietAdherence | null;
  diet_notes?: string | null;
  energy_1_5?: number | null;
  mood_1_5?: number | null;
  fatigue_1_5?: number | null;
  free_notes?: string | null;
  chosen_options_json?: Record<string, OptionKey> | null;
  option_feedback_json?: Record<string, "up" | "down"> | null;
  workout_sets: WorkoutSetIn[];
}

export interface PeriodCloseIn {
  closing_weight_kg: number;
  closing_rating?: number | null;
  closing_hardest?: string | null;
  closing_questions?: string | null;
  closing_waist_cm?: number | null;
  closing_hip_cm?: number | null;
  closing_arm_cm?: number | null;
  closing_thigh_cm?: number | null;
  closing_feelings_json?: Record<string, number> | null;
  adherence_diet_0_10?: number | null;
  adherence_training_0_10?: number | null;
  free_meals_count?: number | null;
  closing_changes?: string | null;
  closing_next_goal?: string | null;
}

export interface ChangeRequestOut {
  id: number;
  client_id: number;
  message: string;
  status: "open" | "resolved";
  created_at: string;
  resolved_at: string | null;
}

export interface LoginIn {
  username: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
}

// --- Respuestas compuestas de la API (Fase 2) ---
export interface PortalLinkOut {
  portal_token: string;
  portal_url: string;
  anamnesis_url: string;
}

export interface ClientCreatedOut {
  client: ClientOut;
  links: PortalLinkOut;
  // Resultado del envío automático del acceso al portal al dar de alta.
  portal_access: "sent" | "disabled" | "failed" | "error" | "no_email" | null;
}

export interface MeOut {
  id: number;
  username: string;
}

// --- Portal del cliente (Fase 6) ---
export interface PortalBrand {
  name: string;
  color_primary: string;
  color_secondary: string;
  color_bg: string;
  font_family: string;
  portal_theme: Theme;
  logo_path: string | null;
}

export interface PortalPeriodInfo {
  period_id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  days_total: number;
  days_elapsed: number;
  days_left: number;
  can_close: boolean;
  status: PeriodStatus;
}

export interface PortalState {
  first_name: string;
  status: ClientStatus;
  diet_mode: DietMode | null;
  package_tier: PackageTier;
  has_plan: boolean;
  period: PortalPeriodInfo | null;
  brand: PortalBrand;
}

/** GET /api/p/{token}/push/pending — espejo de PushPendingOut. */
export interface PushPending {
  diary: boolean;
  workout: boolean;
  quincenal: boolean;
  plan?: boolean;
  count: number;
}

export interface TodayMealOption {
  key: string;
  title: string;
  macros: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
  prep_minutes: number | null;
  tags: string[];
}

export interface TodayMealSlot {
  slot: number;
  name: string;
  time: string;
  target: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
  options: TodayMealOption[];
  chosen_key: string | null;
}

export interface TodayExercise {
  exercise_id: number;
  name: string;
  sets: number;
  rep_range: string;
  rir: string;
  rest_sec: number;
  start_weight_hint_kg: number | null;
  /** Peso sugerido AJUSTADO a la semana del mesociclo en curso (a 0,5 kg). */
  week_weight_hint_kg?: number | null;
  technique_cue: string | null;
  /** Indicaciones personalizadas del coach para este cliente. */
  coach_notes?: string | null;
  video_url: string | null;
}

/** Semana del mesociclo que el cliente vive hoy: fase, carga, RIR y porqué. */
export interface TrainingWeek {
  week: number;
  total_weeks: number;
  intent: string | null;
  load_pct: number;
  rir_target: string | null;
  volume_note: string | null;
  load_factor: number;
  started_on: string;
  why: string;
}

export interface TodaySession {
  day: string;
  name: string;
  warmup: string | null;
  exercises: TodayExercise[];
  cooldown: string | null;
}

export interface TodayView {
  date: string;
  day_label: string;
  period: PortalPeriodInfo | null;
  meals: TodayMealSlot[];
  session: TodaySession | null;
  already_logged: boolean;
}

/** Cambios aplicados al plan en la última adaptación (revisión quincenal):
 *  qué cambió (con antes→después si fue automático), dónde y por qué. */
export interface PlanChangeItem {
  area: string;               // "dieta" | "entreno" | otro
  change: string;             // el cambio tal como lo propuso el feedback
  reason: string;             // el porqué
  applied: boolean;           // false = lo aplicó el coach a mano al editar
  detail: string | null;      // "Proteína: 185 → 200 g" (antes→después)
}
export interface PlanChanges {
  period_index: number;
  items: PlanChangeItem[];
}

export interface PortalPlanOut {
  month_index: number;
  nutrition: NutritionCore & { meal_bank?: MealsOutput } | null;
  training: TrainingCore | null;
  education: EducationOutput | null;
  diet_mode: DietMode | null;
}

export interface FeedbackDocOut {
  id: number;
  kind: string;
  sent_at: string | null;
  content_json: Record<string, unknown> | null;
}

// --- Sección Recursos del portal (GET /api/p/{token}/resources) ---
export interface ResourceExerciseVideo {
  exercise_id: number;
  title: string;
  muscle: string | null;
  video_url: string;
  image_url: string | null;
  technique_notes: string | null;
}

export interface ResourceProduct {
  id: number;
  title: string;
  description: string | null;
  url: string;
  category: string;
  image_url: string | null;
  discount_code?: string | null;
}

export interface PortalResources {
  exercise_videos: ResourceExerciseVideo[];
  products: ResourceProduct[];
}

// Progreso del cliente que ve él mismo en el portal (GET /api/p/{token}/progress)
export interface PortalProgress {
  weight: {
    start_kg: number | null;
    current_kg: number | null;
    goal_kg: number | null;
    delta_kg: number | null;
    weekly_rate_kg: number | null;
    series: { d: string; kg: number }[];
  };
  measurements: {
    label: string;
    weight_kg: number | null;
    waist_cm: number | null;
    hip_cm: number | null;
    arm_cm: number | null;
    thigh_cm: number | null;
  }[];
  adherence: { label: string; diet_0_10: number | null; training_0_10: number | null }[];
  strength: { exercise: string; first_e1rm: number; best_e1rm: number; gain_pct: number; sessions: number }[];
  photos: {
    first: { id: number; kind: string }[];
    last: { id: number; kind: string }[];
    first_date: string | null;
    last_date: string | null;
  };
}

// Alerta del centro de notificaciones del coach (GET /api/alerts)
export interface CoachAlert {
  client_id: number;
  client_name: string;
  kind: string;
  severity: "alta" | "media";
  message: string;
  tab: string;
  action: string;
}
