import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarCheck, Dumbbell, NotebookPen } from "lucide-react";
import { portalApi, PortalError } from "./portalApi";
import type { PortalState } from "../types";
import { PortalWorkout } from "./PortalWorkout";
import { PortalDiary } from "./PortalDiary";
import { PortalClose } from "./PortalClose";
import { PortalToastProvider } from "./PortalToast";

// El portal del cliente es SOLO seguimiento: 3 pestañas abajo (Entreno, Diario,
// Quincenal). Nada más (ni Hoy, ni Plan, ni Feedback): la dieta va en el PDF.
type Tab = "entreno" | "diario" | "cierre";

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
  const [tab, setTab] = useState<Tab>("entreno");

  const reload = useCallback(() => {
    apiClient
      .state()
      .then((s) => {
        setState(s);
        applyBrand(s);
      })
      .catch((e) => setError(e instanceof PortalError ? e.message : "No se pudo cargar tu portal"));
  }, [apiClient]);

  useEffect(reload, [reload]);

  if (error) {
    return (
      <Centered>
        <p className="text-lg font-semibold">Enlace no válido</p>
        <p className="mt-1 text-sm opacity-70">
          Este enlace no funciona o ha caducado. Pide a tu coach uno nuevo.
        </p>
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
    { id: "cierre", label: "Quincenal", icon: CalendarCheck },
  ];
  const visibleTabs = TABS;

  return (
    <PortalToastProvider light={light}>
      <div className="portal-root mx-auto flex min-h-screen max-w-md flex-col">
        {/* Cabecera con marca */}
        <header className="relative z-[1] flex items-center justify-between px-5 pb-2 pt-6">
          <div>
            <p className="text-xs uppercase tracking-widest opacity-50">{state.brand.name}</p>
            <h1 className="text-xl font-semibold">Hola, {state.first_name}</h1>
          </div>
          {state.period && (
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: state.brand.color_primary, textShadow: `0 0 12px ${state.brand.color_primary}55` }}>
                {state.period.days_left}
              </p>
              <p className="text-[11px] opacity-50">días restantes</p>
            </div>
          )}
        </header>

        <main className="relative z-[1] flex-1 px-5 pb-28 pt-2">
          {tab === "entreno" && <PortalWorkout api={apiClient} brand={state.brand} />}
          {tab === "diario" && <PortalDiary api={apiClient} brand={state.brand} />}
          {tab === "cierre" && (
            <PortalClose
              api={apiClient}
              brand={state.brand}
              onClosed={reload}
              canClose={canClose}
              daysLeft={state.period?.days_left ?? null}
              closeDate={state.period?.ends_on ?? null}
            />
          )}
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
                className={`relative flex flex-1 flex-col items-center gap-0.5 rounded-xl py-1.5 transition-colors ${active ? "nav-active" : ""}`}
                style={{ color: active ? undefined : "#9a8f7d" }}
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

function applyBrand(s: PortalState) {
  document.documentElement.style.setProperty("--brand-accent", s.brand.color_primary);
  document.documentElement.style.setProperty("--brand-accent-2", s.brand.color_secondary);
  document.title = `${s.brand.name} · Mi portal`;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-8 text-center"
      style={{ background: "#0a0a0f", color: "#e7e7ea" }}>
      {children}
    </div>
  );
}
