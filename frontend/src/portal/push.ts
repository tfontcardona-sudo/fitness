/**
 * Web Push del portal (TRASPASO §8.1) — lado navegador.
 *
 * - registra el service worker (/sw.js, scope raíz → cubre /p/{token})
 * - inyecta el manifest PWA POR CLIENTE (para "Añadir a pantalla de inicio")
 * - gestiona la suscripción push contra /api/p/{token}/push/*
 * - sincroniza el badge del icono (navigator.setAppBadge)
 *
 * Notas de plataforma:
 * - Android/Chrome y escritorio: funciona en el navegador y como app instalada.
 * - iOS ≥16.4: el push SOLO funciona con la app instalada (Compartir →
 *   "Añadir a pantalla de inicio"); en Safari normal no existe PushManager.
 * - Requiere contexto seguro (HTTPS o localhost).
 */

import type { portalApi } from "./portalApi";

type PortalApiClient = ReturnType<typeof portalApi>;

export function isPushSupported(): boolean {
  return (
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function isIOS(): boolean {
  // iPadOS moderno se anuncia como Mac, pero tiene pantalla táctil
  const ua = navigator.userAgent;
  return /iPad|iPhone|iPod/.test(ua) || (ua.includes("Mac") && "ontouchend" in document);
}

export function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as any).standalone === true
  );
}

/** iOS sin instalar: no hay push posible hasta añadir a pantalla de inicio. */
export function needsInstallFirst(): boolean {
  return isIOS() && !isStandalone();
}

export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch(() => {
    /* http sin localhost, navegador antiguo… el portal funciona igual */
  });
}

/** Manifest dinámico: cada cliente instala SU portal (start_url con su token). */
export function injectManifest(token: string): void {
  const href = `/api/p/${token}/manifest.webmanifest`;
  let link = document.querySelector<HTMLLinkElement>('link[rel="manifest"]');
  if (!link) {
    link = document.createElement("link");
    link.rel = "manifest";
    document.head.appendChild(link);
  }
  link.href = href;
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

/**
 * Pide permiso (si hace falta), crea la suscripción en el navegador y la
 * registra en el backend. Lanza Error con mensaje en castellano si algo falla.
 */
export async function enablePush(api: PortalApiClient): Promise<void> {
  if (!isPushSupported()) throw new Error("Este navegador no soporta notificaciones");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Permiso de notificaciones denegado");
  }

  const { enabled, public_key } = await api.pushPublicKey();
  if (!enabled || !public_key) {
    throw new Error("Las notificaciones no están activadas en el servidor");
  }

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
  await api.pushSubscribe({
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  });
  // Activar explícitamente siempre gana al interruptor de apagado.
  localStorage.removeItem(PUSH_OFF_KEY);
}

// Interruptor local: el cliente puede APAGAR sus notificaciones desde el portal
// (y volver a encenderlas). El flag vive en este dispositivo; con él puesto, la
// resuscripción automática no vuelve a activarlas por su cuenta.
const PUSH_OFF_KEY = "portal_push_off";

export function isPushOff(): boolean {
  return localStorage.getItem(PUSH_OFF_KEY) === "1";
}

/** Estado efectivo del interruptor en ESTE dispositivo. */
export function pushIsOn(): boolean {
  return isPushSupported() && Notification.permission === "granted" && !isPushOff();
}

/** Vuelve a encender las notificaciones (limpia el flag y resuscribe). */
export async function turnPushOn(api: PortalApiClient): Promise<void> {
  localStorage.removeItem(PUSH_OFF_KEY);
  await enablePush(api);
}

/** Apaga las notificaciones: borra la suscripción del backend y del navegador
 *  y deja el flag para que la resuscripción automática no las reactive. */
export async function turnPushOff(api: PortalApiClient): Promise<void> {
  localStorage.setItem(PUSH_OFF_KEY, "1");
  try {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = reg ? await reg.pushManager.getSubscription() : null;
    if (sub) {
      const json = sub.toJSON();
      if (json.endpoint) await api.pushUnsubscribe(json.endpoint).catch(() => {});
      await sub.unsubscribe().catch(() => {});
    }
    syncAppBadge(0);
  } catch {
    /* el flag ya está puesto: no volverá a suscribirse solo */
  }
}

/**
 * Si el permiso YA está concedido, reengancha la suscripción en segundo plano
 * (autocura tras borrar la BD o cambiar de dispositivo). Silencioso. Respeta
 * el interruptor: apagado a mano → no se reactiva sola.
 */
export async function resyncPushIfGranted(api: PortalApiClient): Promise<void> {
  if (!isPushSupported() || Notification.permission !== "granted" || isPushOff()) return;
  try {
    await enablePush(api);
  } catch {
    /* silencioso: es solo mantenimiento */
  }
}

/** Pone/quita el numerito del icono de la app instalada. */
export function syncAppBadge(count: number): void {
  const nav = navigator as any;
  if (typeof nav.setAppBadge !== "function") return;
  if (count > 0) nav.setAppBadge(count).catch(() => {});
  else nav.clearAppBadge?.().catch(() => {});
}

/** Lee pendientes del backend y sincroniza el badge. Devuelve el count. */
export async function refreshBadge(api: PortalApiClient): Promise<number> {
  try {
    const pending = await api.pushPending();
    syncAppBadge(pending.count);
    return pending.count;
  } catch {
    return 0;
  }
}
