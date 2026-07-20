/**
 * Capa de acceso a la API.
 *
 * Un único cliente fetch que adjunta el JWT, parsea JSON y normaliza errores.
 * Cada método mapea a un endpoint real de las Fases 2–4. Los tipos vienen de
 * types.ts (espejo de los schemas Pydantic).
 */

/** Intervalo de refresco (polling) de las vistas del coach: la web se actualiza
 *  sola cada 3 s (solo con la pestaña visible) para verlo todo casi en vivo.
 *  Fuente única: cambiar aquí ajusta panel, clientes, ficha, seguimiento y
 *  campana a la vez. */
export const REFRESH_MS = 3000;

/** Igualdad "por valor" de dos respuestas de la API (objetos JSON planos).
 *  Se usa en el polling de 3 s: si los datos nuevos son idénticos a los que ya
 *  hay en pantalla, NO se actualiza el estado. Así se evita el parpadeo y las
 *  desincronizaciones (re-render y re-fetch inútiles cada 3 s cuando nada ha
 *  cambiado). El orden de claves de FastAPI/Pydantic es estable, así que
 *  comparar el JSON serializado es fiable para estos payloads. */
export function sameData(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  try {
    return JSON.stringify(a) === JSON.stringify(b);
  } catch {
    return false;
  }
}

/** Ayuda para los setState del polling: conserva la referencia anterior si los
 *  datos no han cambiado (evita re-render). Uso: `setX((prev) => keepIfSame(prev, next))`. */
export function keepIfSame<T>(prev: T, next: T): T {
  return sameData(prev, next) ? prev : next;
}

import type {
  BrandConfigOut,
  CoachAlert,
  ChangeRequestOut,
  ClientCreate,
  ClientCreatedOut,
  ClientOut,
  ClientStatus,
  ExerciseOut,
  LandingOut,
  MeOut,
  PlanPricesOut,
  PortalLinkOut,
  RecommendedProductIn,
  RecommendedProductOut,
  RecommendedProductUpdate,
  TokenOut,
  VideoCallOut,
} from "../types";

const TOKEN_KEY = "fitness_coach_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { raw?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    clearToken();
    // Señaliza a la app que debe volver al login.
    window.dispatchEvent(new CustomEvent("auth:expired"));
    throw new ApiError(401, "Sesión caducada");
  }

  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail);
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- auth ---
  login: (username: string, password: string) =>
    request<TokenOut>("POST", "/auth/login", { username, password }),
  me: () => request<MeOut>("GET", "/auth/me"),

  // --- clients ---
  listClients: (params: { status?: ClientStatus; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ClientOut[]>("GET", `/clients${suffix}`);
  },
  getClient: (id: number) => request<ClientOut>("GET", `/clients/${id}`),
  createClient: (body: ClientCreate) =>
    request<ClientCreatedOut>("POST", "/clients", body),
  updateClient: (id: number, patch: Partial<ClientOut>) =>
    request<ClientOut>("PATCH", `/clients/${id}`, patch),
  // Borrado total (RGPD): el backend exige `confirm` == nombre completo exacto.
  deleteClient: (id: number, confirm: string) =>
    request<void>("DELETE", `/clients/${id}?confirm=${encodeURIComponent(confirm)}`),
  portalLink: (id: number) =>
    request<PortalLinkOut>("GET", `/clients/${id}/portal-link`),
  regeneratePortalToken: (id: number) =>
    request<PortalLinkOut>("POST", `/clients/${id}/portal-token/regenerate`),
  sendPortalAccess: (id: number) =>
    request<{ status: string; email: string; password: string | null }>(
      "POST", `/clients/${id}/send-portal-access`),
  // Pagos (Stripe)
  // Registro personal: crea la sesión de pago del plan × duración elegidos y
  // devuelve la URL de Stripe.
  publicCheckout: (tier: string, period: string) =>
    request<{ url: string }>("POST", "/public/checkout", { tier, period }),
  // Alta manual: envía por email el mensaje de arranque (pago + anamnesis).
  sendOnboarding: (id: number) =>
    request<{ status: string; email: string }>("POST", `/clients/${id}/send-onboarding`),
  // Enlace ESTABLE de pago de un cliente (para mandarlo por WhatsApp/email).
  payLinkUrl: (portalToken: string) => `${window.location.origin}/api/pay/${portalToken}`,
  exportClientUrl: (id: number) => `/api/clients/${id}/export`,
  listPlans: (clientId: number) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      nutrition_json: any; training_json: any; education_json: any;
      guardrail_flags: string[] | null;
      goal_type: string | null; published_at: string | null; created_at: string | null;
    }[]>("GET", `/clients/${clientId}/plans`),
  // ---- Etapa del objetivo (45 días) + alertas del coach ----
  goalReviewAnalysis: (clientId: number) =>
    request<{ text: string; options: string[] }>("POST", `/clients/${clientId}/goal-review/analysis`),
  snoozeGoalReview: (clientId: number) =>
    request<ClientOut>("POST", `/clients/${clientId}/goal-review/snooze`),
  changeGoal: (clientId: number, body: { goal_type: string; goal_weight_kg?: number | null }) =>
    request<ClientOut>("POST", `/clients/${clientId}/change-goal`, body),
  listAlerts: () =>
    request<{ alerts: CoachAlert[]; count: number; high: number }>("GET", "/alerts"),
  planDocumentUrl: (planId: number) => `/api/plans/${planId}/document`,
  listClientDocuments: (clientId: number) =>
    request<{ name: string; size_kb: number; uploaded_at: number }[]>(
      "GET", `/clients/${clientId}/documents`),
  uploadClientDocument: (clientId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ name: string; read_ok: boolean; read_error: string | null; portal_access: string | null }>(
      "POST", `/clients/${clientId}/documents`, fd);
  },
  clientDocumentUrl: (clientId: number, name: string) =>
    `/api/clients/${clientId}/documents/${encodeURIComponent(name)}`,
  listClientPhotos: (clientId: number) =>
    request<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>(
      "GET", `/clients/${clientId}/photos`),
  clientPhotoUrl: (clientId: number, photoId: number) =>
    `/api/clients/${clientId}/photos/${photoId}`,
  getClientHistory: (clientId: number) =>
    request<{
      start_weight_kg: number | null; current_weight_kg: number | null; goal_weight_kg: number | null;
      remaining_to_goal_kg: number | null;
      measures: Record<"waist" | "hip" | "arm" | "thigh", { before: number | null; after: number | null }>;
      total_strength_gain_pct: number | null;
      periods: {
        period_index: number; starts_on: string; ends_on: string; status: string;
        closing_weight_kg: number | null; weight_delta_kg: number | null; adherence_pct: number | null;
        best_e1rm_kg: number | null; strength_gain_pct: number | null; distance_to_goal_kg: number | null;
        waist_cm: number | null; hip_cm: number | null; arm_cm: number | null; thigh_cm: number | null;
        feedback_id: number | null; feedback_sent: boolean;
      }[];
      plans: { id: number; month_index: number; version: number; status: string }[];
    }>("GET", `/clients/${clientId}/history`),
  getClientTracking: (clientId: number) =>
    request<{
      has_period: boolean;
      period?: { index: number; starts_on: string; ends_on: string; status: string; days_elapsed: number; days_total: number };
      daily?: {
        date: string; weight_kg: number | null; sleep_hours: number | null; steps: string | null;
        satiety_1_10: number | null; water_liters: number | null; diet_adherence: string | null;
        free_notes: string | null; workout_sets: number;
      }[];
      daily_averages?: {
        weight_kg: number | null; sleep_hours: number | null; steps: number | null;
        satiety_1_10: number | null; water_liters: number | null; workout_sets: number | null;
        diet_adherence_pct: number | null;
      };
      days_logged?: number;
      today_logged?: boolean;
      quincenal_pending?: boolean;
      quincenals?: {
        period_index: number; starts_on: string; ends_on: string; status: string; analyzed: boolean;
        weight_before: number | null; weight_after: number | null;
        waist_before: number | null; waist_after: number | null;
        hip_before: number | null; hip_after: number | null;
        arm_before: number | null; arm_after: number | null;
        thigh_before: number | null; thigh_after: number | null;
        feelings: Record<string, number> | null; feelings_score_10: number | null;
        adherence_diet: number | null; adherence_training: number | null;
        free_meals: number | null; changes: string | null; hardest: string | null;
        next_goal: string | null; questions: string | null;
      }[];
    }>("GET", `/clients/${clientId}/tracking`),
  anamnesisTemplateUrl: () => `/api/anamnesis-template`,
  // meals (opcional): claves canónicas del reparto de comidas elegido por el
  // coach en el selector; si viene, sustituye al de la anamnesis y se regenera.
  generatePlan: (clientId: number, monthIndex = 1, meals?: string[]) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[];
      nutrition: any; training: any; education: any;
    }>("POST", `/clients/${clientId}/generate-plan?month_index=${monthIndex}`,
      meals && meals.length ? { meals } : undefined),
  adaptPlan: (clientId: number) =>
    request<{ id: number; month_index: number; version: number; status: string }>(
      "POST", `/clients/${clientId}/adapt-plan`),
  publishPlan: (planId: number) =>
    request<{ status: string }>("POST", `/plans/${planId}/publish`),
  updatePlan: (planId: number, patch: { nutrition_json?: any; training_json?: any; education_json?: any }) =>
    request<{ id: number; status: string; nutrition_json: any; training_json: any; education_json: any; guardrail_flags: string[] | null; month_index: number; version: number }>(
      "PATCH", `/plans/${planId}`, patch),
  readAnamnesis: (clientId: number) =>
    request<{ extracted: any; deep_analysis: string | null; message: string }>(
      "POST", `/clients/${clientId}/read-anamnesis`),

  // --- feedback (cierre → informe) ---
  createPeriod: (clientId: number, planId: number, startsOn: string, days = 14) =>
    request<{ period_id: number; period_index: number; starts_on: string; ends_on: string }>(
      "POST", `/clients/${clientId}/periods`, { plan_id: planId, starts_on: startsOn, days }),
  listPeriods: (clientId: number) =>
    request<{
      id: number; plan_id: number | null; period_index: number; starts_on: string; ends_on: string; status: string;
      closing_weight_kg: number | null; closing_rating: number | null;
      closing_hardest: string | null; closing_questions: string | null;
      closing_waist_cm: number | null; closing_hip_cm: number | null;
      closing_arm_cm: number | null; closing_thigh_cm: number | null;
      feedback_id: number | null;
    }[]>("GET", `/clients/${clientId}/periods`),
  generateFeedback: (periodId: number) =>
    request<{ feedback_id: number; period_id: number; kind: string; content: any }>(
      "POST", `/periods/${periodId}/feedback`),
  getFeedback: (docId: number) =>
    request<{ id: number; period_id: number; kind: string; content: any; sent_at: string | null }>(
      "GET", `/feedback/${docId}`),
  sendFeedback: (docId: number) =>
    request<{ sent: boolean; sent_at: string }>("POST", `/feedback/${docId}/send`),
  // Entrega por EMAIL (paquetes Start/Full): el informe va en el propio correo
  // y el ciclo avanza igual que con WhatsApp.
  sendFeedbackEmail: (docId: number) =>
    request<{ sent: boolean; sent_at: string; email_status: string }>(
      "POST", `/feedback/${docId}/send-email`),
  // Entrega de la planificación por EMAIL (adjunta el PDF).
  sendPlanEmail: (planId: number) =>
    request<{ sent: boolean; email_status: string; attached_pdf: boolean }>(
      "POST", `/plans/${planId}/send-email`),
  editFeedback: (docId: number, patch: {
    natural_analysis?: string; changes_bullets?: string[]; answers?: string | null;
    next_objectives?: string[]; closing_message?: string;
  }) => request<{ id: number; content: any; sent_at: string | null }>("PATCH", `/feedback/${docId}`, patch),
  getPeriodMetrics: (periodId: number) =>
    request<{
      period_index: number; status: string;
      weight: { start_kg: number | null; end_kg: number | null; delta_kg: number | null; weekly_rate_kg: number | null };
      body_weight_now_kg: number | null; goal_weight_kg: number | null; distance_to_goal_kg: number | null;
      adherence: { diet_pct: number; log_pct: number; days_logged: number; period_days: number };
      strength: { name: string; e1rm_kg: number; delta_kg: number | null }[];
    }>("GET", `/periods/${periodId}/metrics`),
  feedbackDocumentUrl: (docId: number) => `/api/feedback/${docId}/document`,
  // Cambios manuales del plan: marcarlos como enviados/atendidos, o enviarlos
  // por email con la lista de lo que se cambió (detectada al editar).
  ackManualChanges: (planId: number) =>
    request<{ cleared: number }>("POST", `/plans/${planId}/manual-changes/ack`),
  sendPlanUpdateEmail: (planId: number) =>
    request<{ sent: boolean; email_status: string; attached_pdf: boolean }>(
      "POST", `/plans/${planId}/send-update-email`),

  // --- videollamadas quincenales (Pro): agendar → fecha → confirmar/reagendar ---
  listVideoCalls: (clientId: number) =>
    request<VideoCallOut[]>("GET", `/clients/${clientId}/video-calls`),
  createVideoCall: (clientId: number, periodIndex: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls`, { period_index: periodIndex }),
  scheduleVideoCall: (clientId: number, callId: number, scheduledFor: string) =>
    request<VideoCallOut>("PATCH", `/clients/${clientId}/video-calls/${callId}`, { scheduled_for: scheduledFor }),
  videoCallDone: (clientId: number, callId: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/done`),
  videoCallReschedule: (clientId: number, callId: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/reschedule`),

  // --- push del COACH (su móvil recibe el resumen de alertas cada 3 h) ---
  coachPushPublicKey: () =>
    request<{ enabled: boolean; public_key: string | null }>("GET", "/coach/push/public-key"),
  coachPushSubscribe: (sub: { endpoint: string; p256dh: string; auth: string }) =>
    request<{ id: number }>("POST", "/coach/push/subscribe", sub),
  coachPushUnsubscribe: (sub: { endpoint: string; p256dh: string; auth: string }) =>
    request<{ removed: boolean }>("POST", "/coach/push/unsubscribe", sub),

  // Autorrelleno del formulario de producto: lee la página del enlace y devuelve
  // título, descripción e imagen (metadatos OpenGraph).
  scrapeProduct: (url: string) =>
    request<{ title: string | null; description: string | null; image_url: string | null }>(
      "POST", "/resources/products/scrape", { url }),

  // --- brand ---
  getBrand: () => request<BrandConfigOut>("GET", "/brand"),
  updateBrand: (body: Omit<BrandConfigOut, "id" | "logo_path" | "links_photo_path">) =>
    request<BrandConfigOut>("PUT", "/brand", body),
  uploadLogo: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/logo", fd);
  },
  // Foto de fondo de la página pública de enlaces (/dq).
  uploadLinksPhoto: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/links-photo", fd);
  },
  // Foto de fondo de la página pública de planes (/planes).
  uploadPlansPhoto: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/plans-photo", fd);
  },
  // Portada única de todos los vídeos de ejercicios.
  uploadVideoCover: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<BrandConfigOut>("POST", "/brand/video-cover", fd);
  },
  // Vídeo del ejercicio subido como archivo (tiene prioridad sobre el enlace).
  uploadExerciseVideo: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<ExerciseOut>("POST", `/exercises/${id}/video`, fd);
  },
  deleteExerciseVideo: (id: number) =>
    request<ExerciseOut>("DELETE", `/exercises/${id}/video`),

  // --- página pública de enlaces + registro self-serve ---
  publicLanding: () => request<LandingOut>("GET", "/public/landing"),
  publicPlanPrices: () => request<PlanPricesOut>("GET", "/public/plan-prices"),
  // URL pública de un archivo bajo media/ (foto de landing, portada de vídeos…).
  mediaUrl: (path: string | null | undefined) =>
    path && path.startsWith("media/") ? `/api/media/${path.slice(6)}` : null,
  // Registro personal desde /planes: crea la ficha, envía el email de arranque
  // (pago + anamnesis) y devuelve la URL de pago de Stripe (o null si no está).
  publicRegister: (body: {
    full_name: string; email: string; phone: string; tier: string; period: string;
  }) => request<{ url: string | null; email_status: string }>("POST", "/public/register", body),

  // --- exercises ---
  listExercises: (params: { q?: string; pattern?: string; muscle?: string; include_archived?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.pattern) qs.set("pattern", params.pattern);
    if (params.muscle) qs.set("muscle", params.muscle);
    if (params.include_archived) qs.set("include_archived", "true");
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<ExerciseOut[]>("GET", `/exercises${suffix}`);
  },
  createExercise: (body: {
    canonical_name: string;
    muscle_primary: string;
    movement_pattern: string;
    aliases?: string[];
    muscle_secondary?: string[];
    equipment?: string[];
    level_min?: number;
  }) => request<ExerciseOut>("POST", "/exercises", body),
  archiveExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/archive`),
  restoreExercise: (id: number) =>
    request<ExerciseOut>("POST", `/exercises/${id}/restore`),
  updateExercise: (id: number, patch: Partial<ExerciseOut>) =>
    request<ExerciseOut>("PATCH", `/exercises/${id}`, patch),

  // --- recursos: productos recomendados (sección Recursos del portal) ---
  listProducts: () => request<RecommendedProductOut[]>("GET", "/resources/products"),
  createProduct: (body: RecommendedProductIn) =>
    request<RecommendedProductOut>("POST", "/resources/products", body),
  updateProduct: (id: number, patch: RecommendedProductUpdate) =>
    request<RecommendedProductOut>("PATCH", `/resources/products/${id}`, patch),
  deleteProduct: (id: number) => request<void>("DELETE", `/resources/products/${id}`),
  uploadProductImage: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<RecommendedProductOut>("POST", `/resources/products/${id}/image`, fd);
  },
  removeProductImage: (id: number) =>
    request<RecommendedProductOut>("DELETE", `/resources/products/${id}/image`),
};

export type { ChangeRequestOut };
