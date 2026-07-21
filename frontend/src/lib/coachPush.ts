/**
 * Web Push del COACH (web del coach) — lado navegador.
 *
 * Registra el mismo service worker del dominio (/sw.js) y suscribe el
 * dispositivo contra /api/coach/push/*. El backend le envía cada 3 h el
 * resumen de alertas/pendientes de sus clientes (services/push.run_coach_digest)
 * para que esté al día sin tener la web abierta.
 *
 * En iPhone el push solo funciona con la web AÑADIDA a la pantalla de inicio
 * (igual que el portal del cliente); en Android/escritorio funciona directo.
 */

import { api } from "./api";

const COACH_PUSH_OFF_KEY = "coach_push_off";

export function isCoachPushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

/** iOS sin instalar como app: el navegador no expone PushManager. */
export function coachNeedsInstallFirst(): boolean {
  const ua = navigator.userAgent;
  const ios = /iPad|iPhone|iPod/.test(ua) || (ua.includes("Mac") && "ontouchend" in document);
  const standalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as any).standalone === true;
  return ios && !standalone;
}

/** ¿El coach apagó las notificaciones desde la web? (decisión local por dispositivo) */
export function coachPushOff(): boolean {
  return localStorage.getItem(COACH_PUSH_OFF_KEY) === "1";
}

/** Estado efectivo en ESTE dispositivo: permiso concedido y no apagado a mano. */
export function coachPushActive(): boolean {
  return isCoachPushSupported() && Notification.permission === "granted" && !coachPushOff();
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

async function currentSubscription(): Promise<PushSubscription | null> {
  if (!("serviceWorker" in navigator)) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

/** Pide permiso (si hace falta), suscribe este dispositivo y lo registra como
 *  dispositivo del coach en el backend. Lanza Error con mensaje en castellano. */
export async function enableCoachPush(): Promise<void> {
  if (!isCoachPushSupported()) {
    throw new Error(
      coachNeedsInstallFirst()
        ? "En iPhone: añade primero la web a la pantalla de inicio (Compartir → Añadir a pantalla de inicio) y actívalo desde la app"
        : "Este navegador no soporta notificaciones",
    );
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Permiso de notificaciones denegado");

  const { enabled, public_key } = await api.coachPushPublicKey();
  if (!enabled || !public_key) {
    throw new Error("Las notificaciones no están activadas en el servidor (claves VAPID)");
  }

  await navigator.serviceWorker.register("/sw.js");
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key) as BufferSource,
    });
  }
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("El navegador devolvió una suscripción incompleta");
  }
  await api.coachPushSubscribe({
    endpoint: json.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  });
  localStorage.removeItem(COACH_PUSH_OFF_KEY);
}

/** Apaga las notificaciones de este dispositivo: lo borra del backend y anula
 *  la suscripción del navegador. Silencioso si no había nada que apagar. */
export async function disableCoachPush(): Promise<void> {
  localStorage.setItem(COACH_PUSH_OFF_KEY, "1");
  try {
    const sub = await currentSubscription();
    if (sub) {
      const json = sub.toJSON();
      if (json.endpoint && json.keys?.p256dh && json.keys?.auth) {
        await api
          .coachPushUnsubscribe({
            endpoint: json.endpoint,
            p256dh: json.keys.p256dh,
            auth: json.keys.auth,
          })
          .catch(() => {});
      }
      await sub.unsubscribe().catch(() => {});
    }
  } catch {
    /* el flag local ya está puesto: no volverá a suscribirse solo */
  }
}

/** Mantenimiento silencioso al abrir la web: si el permiso ya está concedido y
 *  no se apagó a mano, reengancha la suscripción (autocura tras limpiar datos). */
export async function resyncCoachPushIfGranted(): Promise<void> {
  if (!isCoachPushSupported() || Notification.permission !== "granted" || coachPushOff()) return;
  try {
    await enableCoachPush();
  } catch {
    /* silencioso: es solo mantenimiento */
  }
}
