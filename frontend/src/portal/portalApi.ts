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
  TodaySession,
  TodayView,
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
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload });
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

export function portalApi(token: string) {
  const base = `/p/${token}`;
  return {
    state: () => req<PortalState>("GET", `${base}/state`),
    today: () => req<TodayView>("GET", `${base}/today`),
    training: () => req<{ sessions: TodaySession[]; plan_changes?: PlanChanges | null }>("GET", `${base}/training`),
    workoutHistory: () =>
      req<{ history: Record<string, { date: string; sets: { set: number; weight_kg: number | null; reps: number | null }[] }[]> }>(
        "GET", `${base}/workout-history`,
      ),
    plan: () => req<PortalPlanOut>("GET", `${base}/plan`),
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
