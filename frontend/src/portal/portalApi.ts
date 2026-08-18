/**
 * API del portal del cliente. Sin JWT: el token firmado va en la URL.
 *
 * Todas las llamadas cuelgan de /api/p/{token}. El token se captura de la ruta
 * del navegador (/p/:token) y se pasa a cada método.
 */

import type {
  ChangeRequestOut,
  DailyLogUpsert,
  FeedbackDocOut,
  PeriodCloseIn,
  PlanChanges,
  PortalPlanOut,
  PortalState,
  PushPending,
  PortalProgress,
  TodaySession,
  TodayView,
  TrainingWeek,
} from "../types";

export class PortalError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Los 422 de validación de FastAPI llegan en inglés y con la ruta técnica del
// campo: aquí se traducen a "Revisa el peso (entre 30 y 300)" — el cliente
// debe saber QUÉ corregir, no leer "Input should be greater than 30".
const FIELD_ES: Record<string, string> = {
  weight_kg: "el peso", sleep_hours: "las horas de sueño", steps: "los pasos",
  satiety_1_10: "la saciedad", water_liters: "el agua", reps: "las repeticiones",
  closing_weight_kg: "el peso final", closing_waist_cm: "la cintura",
  closing_hip_cm: "la cadera", closing_arm_cm: "el brazo", closing_thigh_cm: "el muslo",
  adherence_diet_0_10: "la adherencia a la dieta",
  adherence_training_0_10: "la adherencia al entreno",
  free_meals_count: "las comidas libres", closing_rating: "la valoración",
  closing_feelings_json: "las sensaciones", start_at: "la fecha y hora",
  message: "el mensaje", email: "el email", password: "la contraseña",
};

function friendly422(items: any[]): string {
  const labels = Array.from(new Set(items.map((x) => {
    const loc: any[] = Array.isArray(x?.loc) ? x.loc : [];
    const field = [...loc].reverse().find((p) => typeof p === "string" && p !== "body");
    return FIELD_ES[field as string] ?? (typeof field === "string" ? field : "un campo");
  })));
  return `Revisa ${labels.join(", ")}: valor fuera de rango o no válido`;
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;
  let jsonBody = false;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
    jsonBody = true;
  }
  // keepalive en los guardados con cuerpo JSON (diario, entreno): son pequeños y
  // así el "guardar al salir" (visibilitychange/pagehide, móvil que pasa a
  // segundo plano) LLEGA al servidor en vez de cancelarse — era la pérdida del
  // último dato tecleado. En subidas FormData (fotos) NO se activa (superan el
  // límite de 64 KB de keepalive).
  const res = await fetch(`/api${path}`, { method, headers, body: payload, keepalive: jsonBody });
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const d = await res.json();
      if (typeof d.detail === "string") detail = d.detail;
      else if (Array.isArray(d.detail)) detail = friendly422(d.detail);
    } catch {
      /* sin cuerpo */
    }
    throw new PortalError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Login del cliente por email + contraseña (sin token todavía). Devuelve el
 *  token de portal con el que se accede al resto del portal. */
export async function portalLogin(email: string, password: string): Promise<{ token: string; first_name: string }> {
  const res = await fetch(`/api/p/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let detail = "Email o contraseña incorrectos";
    try {
      const d = await res.json();
      if (typeof d.detail === "string") detail = d.detail;
    } catch { /* sin cuerpo */ }
    throw new PortalError(res.status, detail);
  }
  return res.json() as Promise<{ token: string; first_name: string }>;
}

// "Recordarme": guardamos el token (y el email para autorrellenar) para entrar
// sin volver a teclear. Es el mecanismo interno; el token equivale a la sesión.
const TOKEN_KEY = "dq_portal_token";
const EMAIL_KEY = "dq_portal_email";
export const portalSession = {
  save(token: string, email: string) {
    try { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(EMAIL_KEY, email); } catch { /* modo privado */ }
  },
  token(): string | null {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  email(): string | null {
    try { return localStorage.getItem(EMAIL_KEY); } catch { return null; }
  },
  clear() {
    try { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(EMAIL_KEY); } catch { /* noop */ }
  },
};

export function portalApi(token: string) {
  const base = `/p/${token}`;
  return {
    state: () => req<PortalState>("GET", `${base}/state`),
    today: () => req<TodayView>("GET", `${base}/today`),
    training: () => req<{ sessions: TodaySession[]; plan_changes?: PlanChanges | null; week?: TrainingWeek | null }>("GET", `${base}/training`),
    workoutHistory: () =>
      req<{ history: Record<string, { date: string; sets: { set: number; weight_kg: number | null; reps: number | null }[] }[]> }>(
        "GET", `${base}/workout-history`,
      ),
    plan: () => req<PortalPlanOut>("GET", `${base}/plan`),
    progress: () => req<PortalProgress>("GET", `${base}/progress`),
    photoUrl: (id: number) => `/api${base}/photos/${id}`,
    getDiary: (logDate: string) =>
      req<Record<string, any>>("GET", `${base}/diary/${logDate}`),
    saveDiary: (body: Partial<DailyLogUpsert> & { log_date: string }) =>
      req<{ saved: boolean }>("PUT", `${base}/diary`, body),
    close: (body: PeriodCloseIn) => req<{ closed: boolean }>("POST", `${base}/close`, body),
    // Seguimiento continuo: el cliente actualiza su evolución cuando se mide
    // (sin cerrar nada). Solo viaja lo que ha rellenado.
    saveMeasurements: (body: Record<string, unknown>) =>
      req<{ saved: boolean; fields: string[] }>("POST", `${base}/measurements`, body),
    closePhotos: (files: File[], kind: string) => {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      return req<unknown[]>("POST", `${base}/close/photos?kind=${kind}`, fd);
    },
    // El cliente confirma que envió sus fotos de progreso al coach (apaga el
    // recordatorio del portal y del push).
    confirmPhotos: () => req<{ confirmed: boolean }>("POST", `${base}/photos-confirmed`),
    feedback: () => req<FeedbackDocOut[]>("GET", `${base}/feedback`),
    changeRequest: (message: string) =>
      req<ChangeRequestOut>("POST", `${base}/change-request`, { message }),
    // --- Web Push (§8.1) ---
    pushPublicKey: () =>
      req<{ enabled: boolean; public_key: string | null }>("GET", `${base}/push/public-key`),
    pushSubscribe: (sub: { endpoint: string; keys: { p256dh: string; auth: string }; resync?: boolean }) =>
      req<{ subscribed: boolean }>("POST", `${base}/push/subscribe`, sub),
    pushUnsubscribe: (endpoint: string) =>
      req<{ removed: boolean }>("POST", `${base}/push/unsubscribe`, { endpoint }),
    pushPending: () =>
      req<PushPending>("GET", `${base}/push/pending`),
  };
}
