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

/** Refresco de las ALERTAS (campana + panel). Van aparte porque /api/alerts
 *  recorre TODOS los clientes con sus planes, períodos y banco de comidas: a 3 s
 *  y desde dos sitios a la vez eran ~40 barridos por minuto que solo servían
 *  para calentar el servidor (auditoría de calidad). Las alertas no cambian
 *  segundo a segundo y, además, se recargan al navegar y al hacer cada acción. */
export const ALERTS_REFRESH_MS = 20000;

/** Biblioteca de ejercicios cacheada en memoria (por juego de filtros). Se
 *  guarda la PROMESA, así que dos pantallas que la piden a la vez comparten
 *  una sola petición en vuelo. Caduca sola y la invalida cualquier cambio en
 *  Recursos. */
const _cacheEjercicios = new Map<string, Promise<ExerciseOut[]>>();
/** Lista de fotos por cliente (ver `listClientPhotos`). */
const _cacheFotos = new Map<string, Promise<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>>();
const EJERCICIOS_TTL_MS = 5 * 60 * 1000;

/** Olvida la biblioteca cacheada: la llaman crear/editar/archivar/restaurar. */
export function olvidaEjercicios(): void {
  _cacheEjercicios.clear();
}

/** Envuelve una mutación de la biblioteca para invalidar la caché al terminar. */
function _trasTocarEjercicios<T>(p: Promise<T>): Promise<T> {
  return p.finally(() => olvidaEjercicios());
}

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
  WhatsAppRoundOut,
  AiCreditOut,
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
  PaymentsListOut,
  PaymentsSummaryOut,
  PlanPricesOut,
  PortalLinkOut,
  RecommendedProductIn,
  RecommendedProductOut,
  RecommendedProductUpdate,
  SalesCatalogOut,
  TokenOut,
  VideoCallAgendaItem,
  VideoCallOut,
} from "../types";

const TOKEN_KEY = "fitness_coach_token";

export function getToken(): string | null {
  // localStorage puede LANZAR (Safari "bloquear todas las cookies", webviews
  // con storage capado): sin el try, el arranque entero moría en blanco.
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}
export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Sin storage la sesión será solo de esta pestaña; mejor que no entrar.
  }
}
export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // sin storage no hay nada que limpiar
  }
}

export class ApiError extends Error {
  status: number;
  /** `detail` crudo del backend cuando es un objeto (p. ej. {message, missing}
   *  del 422 de anamnesis incompleta o {message, error} de los 502 de IA). */
  detail?: any;
  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/** Nombre EN ESPAÑOL de los campos que más aparecen en un 422. Lo que llega de
 *  Pydantic es el nombre técnico en inglés, y sin él el mensaje no dice ni de
 *  qué casilla habla. */
const CAMPOS_ES: Record<string, string> = {
  full_name: "nombre", email: "email", phone: "teléfono",
  height_cm: "altura", start_weight_kg: "peso inicial",
  current_weight_kg: "peso actual", goal_weight_kg: "peso objetivo",
  body_fat_pct: "grasa corporal", birth_date: "fecha de nacimiento",
  training_days: "días de entreno", session_max_min: "minutos por sesión",
  amount_eur: "importe", paid_on: "fecha del cobro", method: "método de cobro",
  target_kcal: "calorías", protein_g: "proteína", carbs_g: "carbohidratos",
  fat_g: "grasas", sets: "series", reps: "repeticiones", weight_kg: "peso",
};

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
    let rawDetail: any;
    try {
      const data = await res.json();
      rawDetail = data.detail;
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) {
        detail = data.detail.map((d: any) => {
          const campo = Array.isArray(d.loc)
            ? d.loc.filter((x: any) => typeof x === "string" && x !== "body").pop()
            : null;
          const nombre = campo ? (CAMPOS_ES[campo] ?? campo.replace(/_/g, " ")) : null;
          return nombre ? `${nombre}: ${d.msg}` : d.msg;
        }).join("; ");
      }
      else if (data.detail && typeof data.detail === "object") {
        // Los endpoints de IA devuelven {message, error} / {message, missing}:
        // sin esto, el coach veía "Error 502" en vez de "recarga crédito…".
        detail = [data.detail.message, data.detail.error].filter(Boolean).join(" — ") || detail;
      }
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(res.status, detail, rawDetail);
  }

  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface PlanSummary {
  id: number;
  client_id: number;
  month_index: number;
  version: number;
  status: string;
  goal_type: string | null;
  generated_by: string | null;
  guardrail_flags: string[] | null;
  published_at: string | null;
  created_at: string | null;
  target_kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  meals_count: number | null;
  split_name: string | null;
  sessions_count: number | null;
  applied_adjustments: {
    period_index?: number;
    items?: { change?: string; detail?: string; reason?: string }[];
  } | null;
  rationale: string | null;
  has_nutrition: boolean;
  has_training: boolean;
}

export const api = {
  // --- auth ---
  login: (username: string, password: string) =>
    request<TokenOut>("POST", "/auth/login", { username, password }),
  me: () => request<MeOut>("GET", "/auth/me"),

  // --- clients ---
  listClients: (params: { status?: ClientStatus; q?: string; light?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.q) qs.set("q", params.q);
    // Sin las notas largas de la anamnesis: para los listados que se refrescan
    // solos y no las pintan. La ficha (`getClient`) las sigue trayendo.
    if (params.light) qs.set("light", "1");
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
  /** Las versiones del plan EN UNA LÍNEA (sin el banco de comidas ni el
   *  educativo): es lo que necesita el archivo de "Planificaciones anteriores",
   *  el chip de dieta de la ficha y el selector. La versión que se abre y se
   *  edita se pide entera con `getPlan`. */
  listPlanSummaries: (clientId: number) =>
    request<PlanSummary[]>("GET", `/clients/${clientId}/plans/summary`),
  getPlan: (planId: number) =>
    request<{
      id: number; client_id: number; month_index: number; version: number; status: string;
      nutrition_json: any; training_json: any; education_json: any;
      guardrail_flags: string[] | null; review_json: any;
      goal_type: string | null; published_at: string | null; created_at: string | null;
    }>("GET", `/plans/${planId}`),
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
  // `kind` distingue el CUESTIONARIO de los adjuntos (analítica, informes):
  // sin él, subir una analítica daba la anamnesis por recibida y "Ver PDF"
  // abría el informe de sangre.
  listClientDocuments: (clientId: number, kind?: "anamnesis" | "adjunto") =>
    request<{ name: string; kind?: string; size_kb: number; uploaded_at: number }[]>(
      "GET", `/clients/${clientId}/documents${kind ? `?kind=${kind}` : ""}`),
  // Lo que dejó anotado la lectura de la anamnesis: la síntesis y las
  // CONTRADICCIONES detectadas (se calculaban y no las veía nadie).
  anamnesisAnalysis: (clientId: number) =>
    request<{ deep_analysis: string | null; contradictions: string[]; read_at: string | null }>(
      "GET", `/clients/${clientId}/anamnesis-analysis`),
  uploadClientDocument: (clientId: number, file: File, kind: "anamnesis" | "adjunto" = "anamnesis") => {
    const fd = new FormData();
    fd.append("file", file);
    // "adjunto" = documento ADICIONAL (analítica, informe): no sustituye la
    // anamnesis ni se lee con IA — antes subir la analítica la destruía.
    fd.append("kind", kind);
    return request<{ name: string; read_ok: boolean | null; read_error: string | null; portal_access: string | null }>(
      "POST", `/clients/${clientId}/documents`, fd);
  },
  clientDocumentUrl: (clientId: number, name: string) =>
    `/api/clients/${clientId}/documents/${encodeURIComponent(name)}`,
  // La pestaña Feedback pinta una tarjeta por revisión y CADA UNA pedía la
  // lista entera de fotos del cliente (con 6 revisiones, 6 peticiones idénticas
  // al abrir, y otra por tarjeta desplegada). Se comparte una sola petición en
  // vuelo y se recuerda 30 s: dentro de la misma pantalla no cambia.
  listClientPhotos: (clientId: number) => {
    const k = `fotos:${clientId}`;
    const ya = _cacheFotos.get(k);
    if (ya) return ya;
    const p = request<{ id: number; kind: string; period_id: number | null; taken_at: string }[]>(
      "GET", `/clients/${clientId}/photos`)
      .catch((e) => { _cacheFotos.delete(k); throw e; });
    _cacheFotos.set(k, p);
    window.setTimeout(() => _cacheFotos.delete(k), 30000);
    return p;
  },
  // `ancho`: miniatura servida por el backend. Las tiras de fotos las pintaban
  // a 80×96 px descargando el original de varios MB, una detrás de otra.
  clientPhotoUrl: (clientId: number, photoId: number, ancho?: number) =>
    `/api/clients/${clientId}/photos/${photoId}` + (ancho ? `?w=${ancho}` : ""),
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
  // monthIndex: normalmente NO se pasa — el backend deriva el mes de asesoría
  // del ciclo real (dos revisiones quincenales = un mes).
  generatePlan: (clientId: number, monthIndex?: number | null, meals?: string[]) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[];
      // true = quedó en BORRADOR retenido por los guardarraíles (toast honesto).
      retained?: boolean;
      nutrition: any; training: any; education: any;
    }>("POST", `/clients/${clientId}/generate-plan${monthIndex ? `?month_index=${monthIndex}` : ""}`,
      meals && meals.length ? { meals } : undefined),
  // Plan BASE determinista para clientes AVANZADOS (0 llamadas a la IA):
  // borrador con los números/comidas/banco/sesiones ya preparados, para que el
  // coach lo termine en el editor y lo active él.
  scaffoldPlan: (clientId: number, monthIndex?: number | null, meals?: string[]) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[];
      nutrition: any; training: any; education: any;
    }>("POST", `/clients/${clientId}/scaffold-plan${monthIndex ? `?month_index=${monthIndex}` : ""}`,
      meals && meals.length ? { meals } : undefined),
  // ---- Biblioteca de planificaciones (todo a 0 créditos) ----------------
  /** Los MODELOS guardados + el plan vigente de cada cliente, con su resumen
   *  de una línea: es la lista de "empezar desde otro plan". */
  planLibrary: () => request<{
    templates: { id: number; title: string; summary: string | null; created_at: string | null }[];
    client_plans: { plan_id: number; client_id: number; client_name: string;
      status: string; summary: string; updated_at: string | null }[];
  }>("GET", "/plan-library"),
  /** Congela un plan como modelo reutilizable ("Planificación base"). */
  saveTemplate: (planId: number, title: string) =>
    request<{ id: number; title: string; summary: string | null }>(
      "POST", "/plan-library/templates", { plan_id: planId, title }),
  renameTemplate: (templateId: number, title: string) =>
    request<{ id: number; title: string }>(
      "PATCH", `/plan-library/templates/${templateId}`, { title }),
  deleteTemplate: (templateId: number) =>
    request<void>("DELETE", `/plan-library/templates/${templateId}`),
  /** Copia un plan (de otro cliente o de un modelo) como BORRADOR para este
   *  cliente. La estructura viene del origen; kcal/macros/comidas/banco se
   *  recalculan para el destino. Devuelve avisos de seguridad. */
  applyFromLibrary: (clientId: number, source: { plan_id?: number; template_id?: number }) =>
    request<{
      id: number; month_index: number; version: number; status: string;
      guardrail_flags: string[]; nutrition: any; training: any; education: any;
      warnings: string[]; summary: string;
    }>("POST", "/plan-library/apply", { client_id: clientId, ...source }),
  adaptPlan: (clientId: number) =>
    request<{ id: number; month_index: number; version: number; status: string }>(
      "POST", `/clients/${clientId}/adapt-plan`),
  /** Descarta un borrador (copia o base equivocada): pasa a superseded. */
  discardPlan: (planId: number) =>
    request<{ status: string }>("POST", `/plans/${planId}/discard`),
  publishPlan: (planId: number) =>
    request<{ status: string }>("POST", `/plans/${planId}/publish`),
  /** Ida y vuelta del Word editable: sube el .docx editado y devuelve los
   *  cambios detectados + los JSON candidatos (NO aplica nada todavía). */
  importPlanWord: (planId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{
      changes: string[]; warnings: string[]; has_changes: boolean;
      base_rev: number; nutrition_json: any; training_json: any;
      // solo viene con contenido si el Word trae cambios del educativo
      education_json: any | null;
    }>("POST", `/plans/${planId}/import-word`, fd);
  },
  updatePlan: (planId: number, patch: { nutrition_json?: any; training_json?: any; education_json?: any; base_rev?: number }) =>
    request<{ id: number; status: string; nutrition_json: any; training_json: any; education_json: any; guardrail_flags: string[] | null; month_index: number; version: number }>(
      "PATCH", `/plans/${planId}`, patch),
  planHistory: (planId: number) =>
    request<{ index: number; at: string | null; label: string;
      summary: { target_kcal?: number; protein_g?: number; carbs_g?: number; fat_g?: number; n_meals?: number } }[]>(
      "GET", `/plans/${planId}/history`),
  // Recupera SOLO el contenido educativo cuando su llamada falló (el plan se
  // guarda igual, con el aviso). Modelo ligero + caché por split: cuesta una
  // fracción de regenerar el plan entero, que es lo único que había antes.
  generateEducation: (planId: number) =>
    request<{ id: number; status: string; education_json: any;
      guardrail_flags: string[] | null }>(
      "POST", `/plans/${planId}/generate-education`),
  revertPlan: (planId: number, index: number) =>
    request<{ id: number; status: string; nutrition_json: any; training_json: any; education_json: any }>(
      "POST", `/plans/${planId}/revert`, { index }),
  // Diagnóstico del correo: por qué no sale un email y qué pasó en los últimos
  // intentos. El backend lo tenía desde hace tandas y no había pantalla que lo
  // abriera — "no le llega el correo al cliente" se diagnosticaba entrando por
  // SSH a leer los logs del contenedor.
  emailStatus: () =>
    request<{
      config: {
        emails_enabled: boolean; smtp_host: string | null; smtp_port: number;
        smtp_user: string | null; smtp_from: string | null;
        smtp_pass_set: boolean; ready: boolean; missing: string[];
      };
      recent: { kind: string; subject: string; status: string;
                error: string | null; sent_at: string | null }[];
    }>("GET", "/email/status"),
  emailTest: (to: string) =>
    request<{ status: string; error: string | null }>("POST", "/email/test", { to }),
  macroRecommendation: (clientId: number) =>
    request<{ available: boolean; weight_kg?: number; tdee?: number; adjustment_pct?: number;
      kcal?: number; protein_g?: number; carbs_g?: number; fat_g?: number; warnings?: string[] }>(
      "GET", `/clients/${clientId}/macro-recommendation`),
  readAnamnesis: (clientId: number) =>
    request<{ extracted: any; deep_analysis: string | null; contradictions: string[]; message: string }>(
      "POST", `/clients/${clientId}/read-anamnesis`),

  // --- peticiones de cambio del cliente (portal → coach) ---
  listChangeRequests: (clientId: number) =>
    request<{ id: number; client_id: number; message: string; status: "open" | "resolved";
      created_at: string; resolved_at: string | null }[]>(
      "GET", `/clients/${clientId}/change-requests`),
  resolveChangeRequest: (crId: number) =>
    request<{ id: number; status: string }>("POST", `/change-requests/${crId}/resolve`),

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
      plan_adjustments?: { area: string; change: string; reason: string }[] | null;
      biweekly_decision?: { action?: string; kcal_delta_pct?: number; rationale?: string } | null;
    }[]>("GET", `/clients/${clientId}/periods`),
  // Cierre de la quincena POR EL COACH cuando el cliente no la envía: sin esto
  // el ciclo se quedaba bloqueado esperándole indefinidamente.
  closePeriodByCoach: (periodId: number, closingWeightKg?: number | null) =>
    request<{ closed: boolean; period_index: number; closing_weight_kg: number }>(
      "POST", `/periods/${periodId}/close-by-coach`,
      { closing_weight_kg: closingWeightKg ?? null }),
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
    plan_adjustments?: { area?: string; change?: string; reason?: string }[];
  }) => request<{ id: number; content: any; sent_at: string | null }>("PATCH", `/feedback/${docId}`, patch),
  getPeriodMetrics: (periodId: number) =>
    request<{
      period_index: number; status: string;
      weight: { start_kg: number | null; end_kg: number | null; delta_kg: number | null; weekly_rate_kg: number | null };
      body_weight_now_kg: number | null; goal_weight_kg: number | null; distance_to_goal_kg: number | null;
      adherence: { diet_pct: number | null; log_pct: number; days_logged: number; period_days: number };
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

  // --- videollamadas quincenales (Pro): el cliente propone → coach acepta/modifica ---
  listVideoCalls: (clientId: number) =>
    request<VideoCallOut[]>("GET", `/clients/${clientId}/video-calls`),
  // Aceptar la propuesta del cliente tal cual (crea el evento + Meet + invita).
  acceptVideoCall: (clientId: number, callId: number, durationMin = 30) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/accept`, { duration_min: durationMin }),
  // Modificar: queda pendiente de agendar a mano (se acuerda por WhatsApp).
  modifyVideoCall: (clientId: number, callId: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/modify`),
  videoCallDone: (clientId: number, callId: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/done`),
  videoCallReschedule: (clientId: number, callId: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/${callId}/reschedule`),
  // Agenda a mano (o acepta con otra hora): crea el evento con Meet, invita al
  // cliente y devuelve el enlace. startAt en formato "YYYY-MM-DDTHH:MM".
  scheduleVideoCallMeet: (clientId: number, periodIndex: number, startAt: string, durationMin: number) =>
    request<VideoCallOut>("POST", `/clients/${clientId}/video-calls/schedule-meet`,
      { period_index: periodIndex, start_at: startAt, duration_min: durationMin }),
  // Agenda del coach: videollamadas agendadas (día, hora, cliente, enlace).
  videoCallsAgenda: () =>
    request<{ calls: VideoCallAgendaItem[]; count: number }>("GET", "/video-calls/agenda"),

  // --- Google Calendar / Meet (conexión de la cuenta del coach) ---
  googleStatus: () =>
    request<{ enabled: boolean; connected: boolean; email: string | null }>("GET", "/google/status"),
  googleStart: () => request<{ authorize_url: string }>("GET", "/google/oauth/start"),
  googleDisconnect: () => request<{ disconnected: boolean }>("POST", "/google/disconnect"),

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

  // --- ronda diaria de WhatsApp ---
  getWhatsAppRound: (useAi = true, force = false) =>
    request<WhatsAppRoundOut>("GET", `/whatsapp/round?use_ai=${useAi}&force=${force}`),
  markWhatsAppSent: (round_id: number, client_id: number, text: string) =>
    request<{ ok: boolean }>("POST", "/whatsapp/round/sent", { round_id, client_id, text }),

  // --- créditos IA (Anthropic) ---
  // --- pagos (libro de caja de Stripe) ---
  listPayments: (params: { limit?: number; offset?: number; status?: string; client_id?: number; orphan?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.status) q.set("status", params.status);
    if (params.client_id) q.set("client_id", String(params.client_id));
    if (params.orphan) q.set("orphan", "true");
    const qs = q.toString();
    return request<PaymentsListOut>("GET", `/payments${qs ? `?${qs}` : ""}`);
  },
  paymentsSummary: () => request<PaymentsSummaryOut>("GET", "/payments/summary"),
  /** Ingresos netos por mes (gráfica de la pantalla de Pagos). */
  paymentsMonthly: (months = 6) =>
    request<{ months: { month: string; total_cents: number; count: number }[] }>(
      "GET", `/payments/monthly?months=${months}`),
  /** Sella lo leído (sin ids = todos): apaga el punto azul y el badge. */
  markPaymentsSeen: (ids?: number[]) =>
    request<{ marked: number; unseen: number }>("POST", "/payments/seen", ids ? { ids } : {}),
  /** Repesca de Stripe lo que falte (histórico + webhooks perdidos). */
  // `partial` = el barrido se cortó por el freno de objetos: NO cubre todo el
  // rango pedido y la pantalla no puede decir "sin cobros pendientes".
  syncPayments: (days?: number) =>
    request<{ created: number; scanned: number; errors: string[]; partial?: boolean }>(
      "POST", `/payments/sync${days ? `?days=${days}` : ""}`),

  /** Cobro FUERA de Stripe (efectivo, transferencia, Bizum) con su importe:
   *  sin él, el total del mes solo contaba la pasarela. */
  /** Borra un cobro anotado A MANO (los de Stripe son el extracto: no se
   *  tocan). Sin esto, un importe mal tecleado se quedaba para siempre en el
   *  total del mes, en la gráfica y en el CSV de la gestoría. */
  borrarCobro: (paymentId: number) =>
    request<void>("DELETE", `/payments/${paymentId}`),
  registrarCobroManual: (body: {
    client_id: number; amount_eur: number;
    method: "efectivo" | "transferencia" | "bizum" | "otro";
    paid_on?: string; note?: string;
  }) => request<{ id: number; amount_cents: number }>("POST", "/payments/manual", body),

  // --- VENDER: catálogo de ofertas/planes con su enlace de pago ------------
  /** Todo lo vendible con importes REALES de Stripe, el enlace definitivo y si
   *  está listo para enviarse (precio y cupón presentes en Stripe). */
  salesCatalog: (refresh = false) =>
    request<SalesCatalogOut>("GET", `/sales/catalog${refresh ? "?refresh=true" : ""}`),
  /** Enlace de pago de UN cliente ya dado de alta + qué hará al abrirlo. */
  clientPayLink: (clientId: number) =>
    request<{ url: string; state: "cobra" | "pagado" | "renovacion" | "suscripcion";
      note: string; tier: string | null; period: string | null;
      payment_status: string | null }>("GET", `/sales/client-link/${clientId}`),

  /** Lecciones aprendidas de las ediciones del coach (aprendizaje continuo). */
  learningLessons: () =>
    request<{ lessons: string[]; updated_at: string | null; source_edits: number;
              total_edits: number; min_edits: number }>("GET", "/learning/lessons"),
  refreshLearningLessons: () =>
    request<{ lessons: string[]; updated_at: string | null; source_edits: number;
              skipped?: string | null }>("POST", "/learning/lessons/refresh"),
  /** Borra UNA lección con la que el coach no está de acuerdo. */
  deleteLearningLesson: (index: number) =>
    request<{ lessons: string[]; removed: string }>("DELETE", `/learning/lessons/${index}`),

  getAiCredit: () => request<AiCreditOut>("GET", "/ai-credit"),
  setAiCredit: (balance_usd: number) =>
    request<AiCreditOut>("PUT", "/ai-credit", { balance_usd }),

  // --- brand ---
  getBrand: () => request<BrandConfigOut>("GET", "/brand"),
  // El PUT lleva SOLO los campos de BrandConfigIn: las rutas de archivos
  // subidos (logo, fotos, portada) se gestionan por sus endpoints de subida.
  updateBrand: (body: Omit<BrandConfigOut, "id" | "logo_path" | "links_photo_path"
    | "video_cover_path" | "plans_photo_path">) =>
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
    // CACHÉ de la biblioteca: son ~90 KB que viajaban DOS veces al abrir la
    // ficha (el panel y el editor la piden por separado) y otra vez en cada
    // apertura del editor. La biblioteca solo cambia cuando el coach toca
    // Recursos, y esas acciones la invalidan (`olvidaEjercicios`).
    const cacheada = _cacheEjercicios.get(suffix);
    if (cacheada) return cacheada;
    const p = request<ExerciseOut[]>("GET", `/exercises${suffix}`)
      .catch((e) => { _cacheEjercicios.delete(suffix); throw e; });
    _cacheEjercicios.set(suffix, p);
    window.setTimeout(() => _cacheEjercicios.delete(suffix), EJERCICIOS_TTL_MS);
    return p;
  },
  createExercise: (body: {
    canonical_name: string;
    muscle_primary: string;
    movement_pattern: string;
    aliases?: string[];
    muscle_secondary?: string[];
    equipment?: string[];
    level_min?: number;
  }) => _trasTocarEjercicios(request<ExerciseOut>("POST", "/exercises", body)),
  archiveExercise: (id: number) =>
    _trasTocarEjercicios(request<ExerciseOut>("POST", `/exercises/${id}/archive`)),
  restoreExercise: (id: number) =>
    _trasTocarEjercicios(request<ExerciseOut>("POST", `/exercises/${id}/restore`)),
  updateExercise: (id: number, patch: Partial<ExerciseOut>) =>
    _trasTocarEjercicios(request<ExerciseOut>("PATCH", `/exercises/${id}`, patch)),

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
