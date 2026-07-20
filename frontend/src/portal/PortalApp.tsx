import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bell, BellOff, CalendarCheck, Check, ChevronDown, Dumbbell, LineChart, Library, LogOut, NotebookPen, Share, Smartphone, X } from "lucide-react";
import { portalApi, portalSession, PortalError } from "./portalApi";
import type { PortalState } from "../types";
import { PortalWorkout } from "./PortalWorkout";
import { PortalDiary } from "./PortalDiary";
import { PortalClose } from "./PortalClose";
import { PortalProgress } from "./PortalProgress";
import { PortalResources } from "./PortalResources";
import { PortalToastProvider, usePortalToast } from "./PortalToast";
import {
  enablePush,
  injectManifest,
  isPushSupported,
  needsInstallFirst,
  pushIsOn,
  refreshBadge,
  registerServiceWorker,
  resyncPushIfGranted,
  turnPushOff,
  turnPushOn,
} from "./push";

// El portal del cliente es SOLO seguimiento: 3 pestañas abajo (Entreno, Diario,
// Quincenal). Nada más (ni Hoy, ni Plan, ni Feedback): la dieta va en el PDF.
type Tab = "entreno" | "recursos" | "diario" | "progreso" | "cierre";

/**
 * Portal del cliente: mobile-first, sin login. El token sale de la URL
 * (/p/:token). Aplica la marca como variables CSS sobre un contenedor propio,
 * de modo que el portal puede ser oscuro o claro según brand.portal_theme sin
 * afectar al resto.
 */
export default function PortalApp({ token }: { token: string }) {
  const apiClient = useMemo(() => portalApi(token), [token]);
  const [state, setState] = useState<PortalState | null>(null);
  const [error, setError] = useState<string | null>(null);
  // La pestaña vive en la URL (?tab=): el botón "atrás" del navegador vuelve a
  // la pestaña anterior (no expulsa del portal) y los overlays abiertos se
  // cierran solos al cambiar de ruta (el contenido de la pestaña se desmonta).
  const [params, setParams] = useSearchParams();
  const rawTab = params.get("tab");
  const tab: Tab =
    rawTab === "diario" || rawTab === "cierre" || rawTab === "progreso" || rawTab === "recursos"
      ? rawTab
      : "entreno";
  const setTab = (t: Tab) => setParams(t === "entreno" ? {} : { tab: t });

  const reload = useCallback(() => {
    apiClient
      .state()
      .then((s) => {
        setState(s);
        applyBrand(s);
        refreshBadge(apiClient); // badge del icono = pendientes de hoy
      })
      .catch((e) => setError(e instanceof PortalError ? e.message : "No se pudo cargar tu portal"));
  }, [apiClient]);

  useEffect(reload, [reload]);

  // PWA + Web Push (§8.1): manifest por cliente, service worker, resuscripción
  // silenciosa si el permiso ya está concedido, y badge al volver a la app.
  useEffect(() => {
    injectManifest(token);
    registerServiceWorker();
    resyncPushIfGranted(apiClient);
    const onFocus = () => refreshBadge(apiClient);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [token, apiClient]);

  if (error) {
    // Si el token que falla es el GUARDADO (recordarme), lo limpiamos al volver
    // para no quedar atrapados: sin esto, /portal vuelve a redirigir a este mismo
    // token caducado y el cliente no podría iniciar sesión nunca más.
    const savedIsStale = portalSession.token() === token;
    return (
      <Centered>
        <p className="text-lg font-semibold">Enlace no válido</p>
        <p className="mt-1 text-sm opacity-70">
          Este enlace no funciona o ha caducado. {savedIsStale ? "Vuelve a iniciar sesión." : "Pide a tu coach uno nuevo."}
        </p>
        <button
          onClick={() => { portalSession.clear(); window.location.href = "/portal"; }}
          className="portal-btn3d mt-4 rounded-xl px-4 py-2 text-sm font-semibold"
        >
          Volver a iniciar sesión
        </button>
      </Centered>
    );
  }

  if (!state) {
    return (
      <Centered>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent opacity-50" />
      </Centered>
    );
  }

  const light = state.brand.portal_theme === "light";
  const canClose = state.period?.can_close ?? false;

  // Paquete Start = solo nutrición: sin pestaña de entreno. La vista por defecto
  // pasa a ser el Diario (si la URL trae ?tab=entreno, se reencamina a diario).
  const isStart = state.package_tier === "start";
  const effTab: Tab = isStart && tab === "entreno" ? "diario" : tab;

  const TABS: { id: Tab; label: string; icon: typeof Dumbbell }[] = [
    { id: "entreno", label: "Entreno", icon: Dumbbell },
    { id: "recursos", label: "Recursos", icon: Library },
    { id: "diario", label: "Diario", icon: NotebookPen },
    { id: "progreso", label: "Progreso", icon: LineChart },
    { id: "cierre", label: "Quincenal", icon: CalendarCheck },
  ];
  const visibleTabs = isStart ? TABS.filter((t) => t.id !== "entreno") : TABS;

  return (
    <PortalToastProvider light={light}>
      <div className={`portal-root ${light ? "" : "portal-dark"} mx-auto flex min-h-screen max-w-md flex-col`}>
        {/* Cabecera con marca */}
        <header className="relative z-[1] flex items-center justify-between px-5 pb-2 pt-6">
          <div className="flex items-center gap-3">
            <img src="/dq-logo.png" alt="" className="h-9 w-auto rounded-lg shadow-sm" />
            <div>
              <p className="text-[10px] uppercase tracking-widest opacity-50">{state.brand.name}</p>
              <h1 className="text-xl font-semibold">Hola, {state.first_name}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {state.period && (
              <div className="text-right">
                {/* Azul (secundario): es un dato del ciclo, no una acción.
                    Nunca negativo (período vencido pendiente de cerrar → 0). */}
                <p className="text-2xl font-bold" style={{ color: state.brand.color_secondary, textShadow: `0 0 12px ${state.brand.color_secondary}55` }}>
                  {Math.max(0, state.period.days_left)}
                </p>
                <p className="text-[11px] opacity-50">días restantes</p>
              </div>
            )}
            <PushToggle api={apiClient} />
            {portalSession.token() && (
              <button
                onClick={() => { portalSession.clear(); window.location.href = "/portal"; }}
                aria-label="Cerrar sesión"
                className="tap -m-1 rounded-lg p-1 opacity-40 hover:opacity-80"
              >
                <LogOut size={18} />
              </button>
            )}
          </div>
        </header>

        <main className="relative z-[1] flex-1 px-5 pb-28 pt-2">
          <WelcomeSetup api={apiClient} accent={state.brand.color_primary}
            secondary={state.brand.color_secondary} hasTraining={!isStart} />
          {/* key={effTab} → transición suave (animate-rise respeta reduced-motion) */}
          <div key={effTab} className="animate-rise">
            {effTab === "entreno" && <PortalWorkout api={apiClient} brand={state.brand} periodStatus={state.period?.status ?? null} />}
            {effTab === "recursos" && <PortalResources api={apiClient} brand={state.brand} hasTraining={!isStart} />}
            {effTab === "diario" && <PortalDiary api={apiClient} brand={state.brand} periodStatus={state.period?.status ?? null} />}
            {effTab === "progreso" && <PortalProgress api={apiClient} brand={state.brand} hasTraining={!isStart} />}
            {effTab === "cierre" && (
              <PortalClose
                api={apiClient}
                brand={state.brand}
                onClosed={reload}
                canClose={canClose}
                daysLeft={state.period?.days_left ?? null}
                closeDate={state.period?.ends_on ?? null}
                periodStatus={state.period?.status ?? null}
                hasTraining={!isStart}
                directContact={state.package_tier === "pro"}
              />
            )}
          </div>
        </main>

        {/* Navegación inferior: 3 pestañas, relieve + neón */}
        <nav className="portal-nav fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-md justify-around px-2 py-2"
          style={{ backdropFilter: "blur(12px)" }}>
          {visibleTabs.map(({ id, label, icon: Icon }) => {
            const active = effTab === id;
            const alert = id === "cierre" && canClose;  // "!" el día que ya se puede rellenar
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                aria-current={active ? "page" : undefined}
                className={`tap relative flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 transition-colors ${active ? "nav-active" : ""}`}
                style={{ color: active ? undefined : "var(--p-nav-idle)" }}
              >
                <span className="nav-ico p-1"><Icon size={20} /></span>
                <span className="text-[10px] font-medium">{label}</span>
                {alert && <span className="portal-tab-badge">!</span>}
              </button>
            );
          })}
        </nav>
      </div>
    </PortalToastProvider>
  );
}

/** Interruptor de NOTIFICACIONES en la cabecera: campana = activadas (toca para
 *  apagar), campana tachada = apagadas (toca para encender). El apagado borra la
 *  suscripción y deja un flag local para que no se reactive sola. */
function PushToggle({ api }: { api: ReturnType<typeof portalApi> }) {
  const toast = usePortalToast();
  const [on, setOn] = useState(pushIsOn);
  const [busy, setBusy] = useState(false);

  // Navegador sin push posible (ni instalando): no enseñar un botón muerto.
  if (!isPushSupported() && !needsInstallFirst()) return null;

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (on) {
        await turnPushOff(api);
        setOn(false);
        toast.push("Notificaciones desactivadas");
      } else {
        if (needsInstallFirst()) {
          toast.push("En iPhone: añade primero el portal a tu pantalla de inicio y actívalas desde la app");
          return;
        }
        await turnPushOn(api);
        setOn(true);
        refreshBadge(api);
        toast.push("Notificaciones activadas 🔔");
      }
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "No se pudo cambiar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={toggle}
      disabled={busy}
      aria-label={on ? "Desactivar notificaciones" : "Activar notificaciones"}
      title={on ? "Notificaciones activadas — toca para desactivarlas" : "Notificaciones desactivadas — toca para activarlas"}
      className="tap -m-1 rounded-lg p-1 hover:opacity-80"
      style={{ opacity: on ? 0.85 : 0.4 }}
    >
      {on ? <Bell size={18} /> : <BellOff size={18} />}
    </button>
  );
}

const WELCOME_DONE_KEY = "portal_welcome_done";
// Compat con el banner antiguo: quien ya lo descartó no vuelve a verlo.
const PUSH_DISMISSED_KEY = "portal_push_dismissed";

/**
 * DESPLEGABLE de primera visita: configura el portal en 2 pasos sin ocupar
 * espacio (cerrado por defecto, con resumen de una línea):
 *  1) instalar el portal como APP en la pantalla de inicio (instrucciones según
 *     iPhone o Android; en iOS es requisito para los avisos), y
 *  2) activar las notificaciones/recordatorios.
 * Desaparece al pulsar "Listo" o solo cuando ambos pasos están hechos.
 */
function WelcomeSetup({ api, accent, secondary, hasTraining = true }: {
  api: ReturnType<typeof portalApi>; accent: string; secondary: string; hasTraining?: boolean;
}) {
  const toast = usePortalToast();
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(WELCOME_DONE_KEY) === "1"
      || localStorage.getItem(PUSH_DISMISSED_KEY) === "1"
  );
  const [granted, setGranted] = useState(
    () => isPushSupported() && Notification.permission === "granted"
  );
  const [busy, setBusy] = useState(false);

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const installed = window.matchMedia("(display-mode: standalone)").matches
    || (navigator as unknown as { standalone?: boolean }).standalone === true;
  const installFirst = needsInstallFirst();

  // Todo hecho (o nada que ofrecer en este navegador) → no molestar más.
  if (dismissed || (granted && installed)) return null;
  if (!isPushSupported() && !installFirst && installed) return null;

  const done = () => {
    localStorage.setItem(WELCOME_DONE_KEY, "1");
    setDismissed(true);
  };

  const activate = async () => {
    setBusy(true);
    try {
      await enablePush(api);
      setGranted(true);
      refreshBadge(api);
      toast.push("Recordatorios activados 🔔");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "No se pudo activar");
    } finally {
      setBusy(false);
    }
  };

  const Step = ({ n, done: stepDone, children }: {
    n: number; done: boolean; children: React.ReactNode;
  }) => (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
        style={stepDone
          ? { background: "#2E7D46", color: "#fff" }
          : { background: `color-mix(in srgb, ${secondary} 16%, transparent)`, color: secondary }}>
        {stepDone ? <Check size={12} /> : n}
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );

  return (
    <details className="portal-card mb-4 overflow-hidden">
      <summary className="tap flex cursor-pointer items-center gap-2.5 p-3">
        <span className="shrink-0" style={{ color: accent }}><Bell size={18} /></span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold">Configura tu portal (1 min)</span>
          <span className="block text-[11px] opacity-60">
            Ponlo como app en tu móvil y activa tus avisos
          </span>
        </span>
        <ChevronDown size={16} className="shrink-0 opacity-50" />
      </summary>
      <div className="space-y-3.5 px-3 pb-3.5 pt-1">
        {/* Paso 1 — instalar como app (instrucciones según el móvil) */}
        <Step n={1} done={installed}>
          <p className="flex items-center gap-1.5 text-xs font-semibold">
            <Smartphone size={13} /> Pon el portal en tu pantalla de inicio
          </p>
          {installed ? (
            <p className="mt-0.5 text-[11px] opacity-60">¡Hecho! Ya lo tienes como app.</p>
          ) : isIOS ? (
            <p className="mt-0.5 text-[11px] leading-relaxed opacity-70">
              En Safari: toca <span className="font-semibold">Compartir</span>{" "}
              <Share size={11} className="inline" /> y elige{" "}
              <span className="font-semibold">"Añadir a pantalla de inicio"</span>.
            </p>
          ) : (
            <p className="mt-0.5 text-[11px] leading-relaxed opacity-70">
              En Chrome: toca el menú <span className="font-semibold">⋮</span> (arriba a la
              derecha) y elige <span className="font-semibold">"Añadir a pantalla de inicio"</span>{" "}
              o <span className="font-semibold">"Instalar aplicación"</span>.
            </p>
          )}
        </Step>

        {/* Paso 2 — notificaciones (en iOS, tras instalar) */}
        <Step n={2} done={granted}>
          <p className="text-xs font-semibold">Activa tus recordatorios</p>
          {granted ? (
            <p className="mt-0.5 text-[11px] opacity-60">¡Hecho! Te avisaré si te falta algo.</p>
          ) : installFirst ? (
            <p className="mt-0.5 text-[11px] opacity-70">
              Primero haz el paso 1; después abre la app y activa aquí los avisos.
            </p>
          ) : (
            <>
              <p className="mt-0.5 text-[11px] opacity-70">
                Un aviso si queda {hasTraining ? "el diario, el entreno o la revisión" : "el diario o la revisión"} sin rellenar.
              </p>
              <button
                onClick={activate}
                disabled={busy}
                className="portal-btn3d mt-1.5 min-h-[38px] px-4 py-1.5 text-xs font-semibold"
                style={{ background: accent, color: "#fff" }}
              >
                {busy ? "Activando…" : "Activar recordatorios"}
              </button>
            </>
          )}
        </Step>

        <button onClick={done} className="tap flex items-center gap-1 text-[11px] font-medium opacity-50 hover:opacity-80">
          <X size={12} /> No volver a mostrar
        </button>
      </div>
    </details>
  );
}

function applyBrand(s: PortalState) {
  document.documentElement.style.setProperty("--brand-accent", s.brand.color_primary);
  document.documentElement.style.setProperty("--brand-accent-2", s.brand.color_secondary);
  document.title = `${s.brand.name} · Mi portal`;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-8 text-center"
      style={{ background: "#f6f1e7", color: "#26211a" }}>
      {children}
    </div>
  );
}
