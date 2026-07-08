import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bell, CalendarCheck, Dumbbell, LineChart, LogOut, NotebookPen, X } from "lucide-react";
import { portalApi, portalSession, PortalError } from "./portalApi";
import type { PortalState } from "../types";
import { PortalWorkout } from "./PortalWorkout";
import { PortalDiary } from "./PortalDiary";
import { PortalClose } from "./PortalClose";
import { PortalProgress } from "./PortalProgress";
import { PortalToastProvider, usePortalToast } from "./PortalToast";
import {
  enablePush,
  injectManifest,
  isPushSupported,
  needsInstallFirst,
  refreshBadge,
  registerServiceWorker,
  resyncPushIfGranted,
} from "./push";

// El portal del cliente es SOLO seguimiento: 3 pestañas abajo (Entreno, Diario,
// Quincenal). Nada más (ni Hoy, ni Plan, ni Feedback): la dieta va en el PDF.
type Tab = "entreno" | "diario" | "progreso" | "cierre";

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
    rawTab === "diario" || rawTab === "cierre" || rawTab === "progreso" ? rawTab : "entreno";
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

  const TABS: { id: Tab; label: string; icon: typeof Dumbbell }[] = [
    { id: "entreno", label: "Entreno", icon: Dumbbell },
    { id: "diario", label: "Diario", icon: NotebookPen },
    { id: "progreso", label: "Progreso", icon: LineChart },
    { id: "cierre", label: "Quincenal", icon: CalendarCheck },
  ];
  const visibleTabs = TABS;

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
          <PushBanner api={apiClient} accent={state.brand.color_primary} />
          {/* key={tab} → transición suave (animate-rise respeta reduced-motion) */}
          <div key={tab} className="animate-rise">
            {tab === "entreno" && <PortalWorkout api={apiClient} brand={state.brand} periodStatus={state.period?.status ?? null} />}
            {tab === "diario" && <PortalDiary api={apiClient} brand={state.brand} periodStatus={state.period?.status ?? null} />}
            {tab === "progreso" && <PortalProgress api={apiClient} brand={state.brand} />}
            {tab === "cierre" && (
              <PortalClose
                api={apiClient}
                brand={state.brand}
                onClosed={reload}
                canClose={canClose}
                daysLeft={state.period?.days_left ?? null}
                closeDate={state.period?.ends_on ?? null}
                periodStatus={state.period?.status ?? null}
              />
            )}
          </div>
        </main>

        {/* Navegación inferior: 3 pestañas, relieve + neón */}
        <nav className="portal-nav fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-md justify-around px-2 py-2"
          style={{ backdropFilter: "blur(12px)" }}>
          {visibleTabs.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
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

const PUSH_DISMISSED_KEY = "portal_push_dismissed";

/**
 * Banner de activación de recordatorios (§8.1). Tres estados:
 * - Android/escritorio sin permiso → botón "Activar" (pide permiso + suscribe).
 * - iOS en Safari sin instalar → instrucciones de "Añadir a pantalla de inicio"
 *   (en iOS el push solo funciona con la app instalada).
 * - Permiso ya concedido, denegado o descartado → no se muestra nada.
 */
function PushBanner({ api, accent }: { api: ReturnType<typeof portalApi>; accent: string }) {
  const toast = usePortalToast();
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(PUSH_DISMISSED_KEY) === "1"
  );
  const [granted, setGranted] = useState(
    () => isPushSupported() && Notification.permission === "granted"
  );
  const [busy, setBusy] = useState(false);

  const installFirst = needsInstallFirst();
  if (dismissed || granted || (!isPushSupported() && !installFirst)) return null;

  const dismiss = () => {
    localStorage.setItem(PUSH_DISMISSED_KEY, "1");
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
      if (isPushSupported() && Notification.permission === "denied") dismiss();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="portal-card mb-4 flex items-start gap-3 p-3">
      {/* Azul: banner informativo, no acción principal */}
      <span className="mt-0.5 shrink-0" style={{ color: "var(--p-accent-2)" }}>
        <Bell size={18} />
      </span>
      <div className="min-w-0 flex-1">
        {installFirst ? (
          <>
            <p className="text-sm font-semibold">Recibe recordatorios</p>
            <p className="mt-0.5 text-xs opacity-70">
              Instala la app para no olvidar tus registros: toca{" "}
              <span className="font-medium">Compartir</span> y luego{" "}
              <span className="font-medium">"Añadir a pantalla de inicio"</span>.
              Después actívalos desde aquí.
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold">¿Te aviso si te falta algo?</p>
            <p className="mt-0.5 text-xs opacity-70">
              Un recordatorio si queda el diario, el entreno o la revisión sin rellenar.
            </p>
            <button
              onClick={activate}
              disabled={busy}
              className="portal-btn3d mt-2 min-h-[40px] px-4 py-2 text-xs font-semibold"
              style={{ background: accent, color: "#fff" }}
            >
              {busy ? "Activando…" : "Activar recordatorios"}
            </button>
          </>
        )}
      </div>
      <button onClick={dismiss} aria-label="Cerrar" className="-m-2 shrink-0 p-2 opacity-40 hover:opacity-80">
        <X size={16} />
      </button>
    </div>
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
