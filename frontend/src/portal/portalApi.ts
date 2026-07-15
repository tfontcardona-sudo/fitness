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
  PortalResources,
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
      else if (Array.isArray(d.detail)) detail = d.detail.map((x: any) => x.msg).join("; ");
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
    resources: () => req<PortalResources>("GET", `${base}/resources`),
    progress: () => req<PortalProgress>("GET", `${base}/progress`),
    photoUrl: (id: number) => `/api${base}/photos/${id}`,
    getDiary: (logDate: string) =>
      req<Record<string, any>>("GET", `${base}/diary/${logDate}`),
    saveDiary: (body: Partial<DailyLogUpsert> & { log_date: string }) =>
      req<{ saved: boolean }>("PUT", `${base}/diary`, body),
    close: (body: PeriodCloseIn) => req<{ closed: boolean }>("POST", `${base}/close`, body),
    closePhotos: (files: File[], kind: string) => {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      return req<unknown[]>("POST", `${base}/close/photos?kind=${kind}`, fd);
    },
    feedback: () => req<FeedbackDocOut[]>("GET", `${base}/feedback`),
    changeRequest: (message: string) =>
      req<ChangeRequestOut>("POST", `${base}/change-request`, { message }),
    // --- Web Push (§8.1) ---
    pushPublicKey: () =>
      req<{ enabled: boolean; public_key: string | null }>("GET", `${base}/push/public-key`),
    pushSubscribe: (sub: { endpoint: string; keys: { p256dh: string; auth: string } }) =>
      req<{ subscribed: boolean }>("POST", `${base}/push/subscribe`, sub),
    pushUnsubscribe: (endpoint: string) =>
      req<{ removed: boolean }>("POST", `${base}/push/unsubscribe`, { endpoint }),
    pushPending: () =>
      req<PushPending>("GET", `${base}/push/pending`),
  };
}
