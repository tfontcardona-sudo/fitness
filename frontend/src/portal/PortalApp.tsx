import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSinConexion } from "../lib/offline";
import { activarAcordeon } from "../lib/accordion";
import { useSearchParams } from "react-router-dom";
import { Bell, BellOff, CalendarCheck, Camera, Check, ChevronDown, Dumbbell, FileText, LineChart, Library, LogOut, MessageSquare, NotebookPen, Share, Smartphone, Video, X } from "lucide-react";
import { portalApi, portalSession, PortalError } from "./portalApi";
import type { VideoCallStatus } from "./portalApi";
import { pkg } from "../lib/packages";
import { useAppUpdate } from "../lib/appUpdate";
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
  PUSH_CHANGED_EVENT,
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
  // Abrir un desplegable cierra el hermano abierto (también en el portal).
  useEffect(activarAcordeon, []);
  const apiClient = useMemo(() => portalApi(token), [token]);
  // Actualización EN CALIENTE de la app instalada: al volver del segundo plano
  // con una versión nueva desplegada se recarga sola; en uso activo, aviso
  // discreto para tocar y actualizar. El cliente nunca reinstala nada.
  const update = useAppUpdate();
  const sinConexion = useSinConexion();
  const [state, setState] = useState<PortalState | null>(null);
  // Sube en cada recarga del estado: los hijos con fetch propio (videollamada)
  // se refrescan a la vez que el resto del portal.
  const [stateVersion, setStateVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  // 404 = token inválido/caducado (sesión fuera). Cualquier otro fallo (red,
  // 500, 429) es TEMPORAL: se ofrece reintentar sin tocar la sesión — antes
  // un corte de red decía "tu enlace ha caducado" y borraba el acceso.
  const [errorKind, setErrorKind] = useState<"token" | "transient">("transient");
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
    setError(null);
    apiClient
      .state()
      .then((s) => {
        setState(s);
        setStateVersion((v) => v + 1);
        applyBrand(s);
        refreshBadge(apiClient); // badge del icono = pendientes de hoy
      })
      .catch((e) => {
        setErrorKind(e instanceof PortalError && e.status === 404 ? "token" : "transient");
        setError(e instanceof PortalError ? e.message : "No se pudo cargar tu portal");
      });
  }, [apiClient]);

  useEffect(reload, [reload]);

  // PWA + Web Push (§8.1): manifest por cliente, service worker, resuscripción
  // silenciosa si el permiso ya está concedido, y badge al volver a la app.
  useEffect(() => {
    injectManifest(token);
    registerServiceWorker();
    resyncPushIfGranted(apiClient);
    const onFocus = () => refreshBadge(apiClient);
    // Al VOLVER a la app (segundo plano → visible) se refresca también el
    // estado: la fecha de negocio, la pausa y la videollamada quedan al día
    // sin recargar (una PWA resucitada al día siguiente ya no escribe ayer).
    const onVisible = () => {
      refreshBadge(apiClient);
      if (!document.hidden) reload();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [token, apiClient]);

  if (error && errorKind === "transient") {
    // Fallo de red / servidor: NO es un problema del enlace. Reintentar sin
    // tocar la sesión guardada.
    return (
      <Centered>
        <p className="p-title">No se pudo conectar</p>
        <p className="mt-1 text-sm opacity-70">Revisa tu conexión.</p>
        <button
          onClick={reload}
          className="portal-btn3d mt-4 rounded-xl px-4 py-2 text-sm font-semibold"
        >
          Reintentar
        </button>
      </Centered>
    );
  }

  if (error) {
    // Si el token que falla es el GUARDADO (recordarme), lo limpiamos al volver
    // para no quedar atrapados: sin esto, /portal vuelve a redirigir a este mismo
    // token caducado y el cliente no podría iniciar sesión nunca más.
    const savedIsStale = portalSession.token() === token;
    return (
      <Centered>
        <p className="p-title">Enlace no válido</p>
        <p className="mt-1 text-sm opacity-70">
          Caducado. {savedIsStale ? "Vuelve a entrar." : "Pide otro a tu coach."}
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
  // Estado del período para las pestañas. Ventana "feedback generado pero aún
  // no enviado": el período pasa a `analyzed` (deja de ser el activo → null)
  // pero el cliente sigue `review_pending`. Sin este sintético, el portal
  // perdía la pausa: el diario aparecía VACÍO y editable, cada guardado moría
  // con 409 (dato perdido) y la pestaña Quincenal retrocedía a "se desbloquea
  // al completar tus 2 semanas" — todo mientras el coach redactaba el feedback
  // (auditoría crítica). Con "closed" sintético, la pausa se mantiene.
  const periodStatus: string | null =
    state.period?.status ?? (state.status === "review_pending" ? "closed" : null);

  // Plan sin entreno (nutri): sin pestaña de entreno. La vista por defecto pasa
  // a ser el Diario (si la URL trae ?tab=entreno, se reencamina a diario).
  const caps = pkg(state.package_tier);
  const isStart = !caps.hasTraining;
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
        <header className="portal-header relative z-[1] flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-3">
            <img src="/dq-logo.png" alt="" className="h-9 w-auto shrink-0 rounded-lg shadow-sm" />
            <div className="min-w-0">
              <p className="p-eyebrow truncate">{state.brand.name}</p>
              <h1 className="p-title truncate">Hola, {state.first_name}</h1>
              {/* Racha 🔥: días seguidos con el diario al día. A partir de 2
                  (un solo día no es racha); el cliente no quiere romperla. */}
              {(state.streak_days ?? 0) >= 2 && (
                <p className="p-micro mt-0.5 flex items-center gap-1"
                   style={{ color: state.brand.color_primary }}>
                  🔥 {state.streak_days} días
                </p>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {state.period && (
              <div className="flex flex-col items-center">
                {/* Anillo de progreso de la quincena: el número dentro del
                    círculo que se va cerrando — se VE cuánto queda, no solo se
                    lee. Azul (secundario): dato del ciclo, no una acción.
                    Nunca negativo (período vencido pendiente de cerrar → 0). */}
                {(() => {
                  const total = Math.max(1, state.period.days_total);
                  const hecho = Math.max(0, Math.min(total, state.period.days_elapsed));
                  const R = 20;
                  const C = 2 * Math.PI * R;
                  return (
                    <div className="relative h-12 w-12">
                      <svg viewBox="0 0 48 48" className="h-12 w-12 -rotate-90">
                        <circle cx="24" cy="24" r={R} fill="none" strokeWidth="4"
                          stroke={`${state.brand.color_secondary}30`} />
                        <circle cx="24" cy="24" r={R} fill="none" strokeWidth="4"
                          strokeLinecap="round"
                          stroke={state.brand.color_secondary}
                          strokeDasharray={C}
                          strokeDashoffset={C * (1 - hecho / total)}
                          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1)" }} />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-base font-bold"
                        style={{ color: state.brand.color_secondary }}>
                        {Math.max(0, state.period.days_left)}
                      </span>
                    </div>
                  );
                })()}
                {/* Concordancia y momento clave: "1 día restante" (no "1 días")
                    y, a 0, la llamada a la acción de la quincena. */}
                {/* La etiqueta se ciñe al ancho del anillo y parte en dos
                    líneas: en una sola, "días restantes" empujaba la cabecera
                    y el saludo salía cortado ("Hola, M…") en un móvil de
                    390 px, que es donde vive el cliente. */}
                <p className="p-micro mt-1 w-14 text-center leading-tight">
                  {Math.max(0, state.period.days_left) === 0
                    ? "¡toca revisión!"
                    : Math.max(0, state.period.days_left) === 1
                      ? "día restante"
                      : "días restantes"}
                </p>
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

        <main className="portal-main relative z-[1] flex-1">
          {/* Onboarding sin anamnesis: antes el cliente entraba a un portal
              con pestañas vacías y NINGÚN camino hacia el cuestionario
              (auditoría del ciclo). El enlace usa su mismo token. */}
          {state.needs_anamnesis && (
            <a href={`/anamnesis/${token}`}
              className="portal-note portal-note--action">
              <span className="min-w-0">
                <span className="p-head block" style={{ color: state.brand.color_primary }}>
                  Completa tu anamnesis →
                </span>
                <span className="p-sub mt-0.5 block">6 pasos · unos minutos</span>
              </span>
            </a>
          )}
          {/* SU PLAN, siempre a mano: la dieta y las pautas viven en el PDF y
              el cliente tenía que rebuscarlo en el WhatsApp de hace semanas
              ("¿qué como hoy?" es su consulta más frecuente). El PDF se sirve
              con su mismo token. */}
          {state.has_plan && (
            <a href={`/api/p/${token}/plan.pdf`} target="_blank" rel="noreferrer"
              className="portal-note portal-note--info items-center">
              <FileText size={18} style={{ color: state.brand.color_secondary }} />
              <span className="min-w-0">
                <span className="p-head block" style={{ color: state.brand.color_secondary }}>
                  Ver mi plan (PDF)
                </span>
                <span className="p-sub mt-0.5 block">
                  {/* Lo que el cliente TIENE, no lo que tiene el paquete Full.
                      La condición solo distinguía Start (sin entreno), así que
                      a un DQR Train —que no lleva nutrición— el portal le
                      anunciaba una dieta que su PDF no contiene. */}
                  {[caps.hasNutrition && "Dieta", caps.hasTraining && "rutina", "pautas"]
                    .filter(Boolean).join(" · ")}
                </span>
              </span>
            </a>
          )}
          {caps.hasVideoCall && (
            <VideoCallBanner api={apiClient} accent={state.brand.color_secondary} refreshKey={stateVersion} />
          )}
          {state.photos_pending && (
            <PhotosReminder api={apiClient} accent={state.brand.color_primary} onConfirmed={reload} />
          )}
          <WelcomeSetup api={apiClient} token={token} accent={state.brand.color_primary}
            secondary={state.brand.color_secondary} />
          <EscribirAlCoach api={apiClient} accent={state.brand.color_primary} />
          {/* key={effTab+fecha}: transición suave al cambiar de pestaña Y
              remontaje si cambia la FECHA DE NEGOCIO — una PWA resucitada días
              después registraba en el día viejo, pisándolo en silencio
              (auditoría crítica). El refetch del estado corre al volver del
              segundo plano (abajo); cada pestaña vuelca sus pendientes en
              visibilitychange antes del remontaje. */}
          <div key={`${effTab}-${state.today ?? ""}`} className="animate-rise"
            ref={(el) => { if (el) window.scrollTo({ top: 0 }); }}>
            {effTab === "entreno" && <PortalWorkout api={apiClient} token={token} brand={state.brand} periodStatus={periodStatus} businessToday={state.today ?? null} hasPeriod={state.period != null || state.status === "review_pending"} />}
            {effTab === "recursos" && <PortalResources api={apiClient} brand={state.brand} hasTraining={!isStart} />}
            {effTab === "diario" && <PortalDiary api={apiClient} token={token} brand={state.brand} periodStatus={periodStatus} businessToday={state.today ?? null} hasPeriod={state.period != null || state.status === "review_pending"} hasNutrition={caps.hasNutrition} hasTraining={!isStart} />}
            {effTab === "progreso" && <PortalProgress api={apiClient} brand={state.brand} hasTraining={!isStart} token={token} />}
            {effTab === "cierre" && (
              <PortalClose
                api={apiClient}
                token={token}
                brand={state.brand}
                onClosed={reload}
                canClose={canClose}
                daysLeft={state.period?.days_left ?? null}
                closeDate={state.period?.ends_on ?? null}
                periodStatus={periodStatus}
                hasTraining={!isStart}
                hasNutrition={caps.hasNutrition}
                directContact={caps.directContact}
              />
            )}
          </div>
        </main>

          {/* Sin conexión: el cliente seguía tecleando series creyendo que se
            guardaban. Se avisa, pero NO se bloquea: puede seguir apuntando y
            el autosave lo reintenta en cuanto vuelva la cobertura. */}
        {sinConexion && (
          <div role="status"
            className="fixed inset-x-0 z-50 mx-auto w-fit max-w-[calc(100vw-2rem)] rounded-full px-4 py-2 text-xs font-semibold"
            style={{
              bottom: "calc(4.5rem + env(safe-area-inset-bottom))",
              background: "var(--p-danger)", color: "#fff", boxShadow: "var(--p-e-3)",
            }}>
            Sin conexión · lo que apuntes se guardará al volver
          </div>
        )}

      {/* Versión nueva desplegada con la app en uso: aviso discreto sobre la
            navegación — un toque y el portal queda al día, sin reinstalar. */}
        {update.ready && (
          <button
            onClick={update.apply}
            className="animate-rise fixed inset-x-0 z-50 mx-auto mb-2 flex w-fit items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold"
            style={{
              bottom: "calc(4.5rem + env(safe-area-inset-bottom))",
              background: state.brand.color_primary,
              color: "var(--p-on-accent)",
              boxShadow: "var(--p-e-3)",
            }}
          >
            ✨ Actualizado · toca para recargar
          </button>
        )}

        {/* Navegación inferior: cristal, indicador fino y píldora lavada */}
        <nav className="portal-nav fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-md justify-around px-2 py-2">
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

/** Fecha de HOY (YYYY-MM-DD) para el mínimo del selector. */
function portalLocalToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Videollamada de revisión en el portal (Pro). Se muestra sobre cualquier
 *  pestaña para que no pase por alto. Estados:
 *   - book: al enviar la revisión, el cliente PROPONE día y hora.
 *   - proposed: propuesta enviada, esperando confirmación del coach.
 *   - pending_manual: el coach la agenda (te escribirá por WhatsApp).
 *   - scheduled: agendada → botón "Unirme" (Google Meet). */
function VideoCallBanner({ api, accent, refreshKey = 0 }: { api: ReturnType<typeof portalApi>; accent: string; refreshKey?: number }) {
  const toast = usePortalToast();
  const [vc, setVc] = useState<VideoCallStatus | null>(null);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("17:00");
  const [busy, setBusy] = useState(false);
  const [showResched, setShowResched] = useState(false);

  const reload = useCallback(() => {
    api.videoCall().then(setVc).catch(() => {});
  }, [api]);
  // refreshKey: el padre lo incrementa al recargar el estado (enviar la
  // revisión, volver del segundo plano) — sin esto, el formulario para
  // agendar la videollamada no aparecía hasta recargar la app a mano.
  useEffect(reload, [reload, refreshKey]);

  if (!vc || vc.state === "none") return null;

  const box = {
    background: `color-mix(in srgb, ${accent} 12%, transparent)`,
    border: `1px solid color-mix(in srgb, ${accent} 35%, transparent)`,
  } as const;
  const header = (
    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest" style={{ color: accent }}>
      <Video size={13} /> Videollamada de revisión
    </div>
  );

  async function propose() {
    if (!date || !time || busy) return;
    setBusy(true);
    try {
      const r = await api.proposeVideoCall(`${date}T${time}`);
      setVc(r);
      toast.push("Enviada · tu coach confirmará");
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar");
    } finally {
      setBusy(false);
    }
  }

  async function reschedule() {
    if (!date || !time || busy) return;
    setBusy(true);
    try {
      const r = await api.rescheduleVideoCall(`${date}T${time}`);
      setVc(r);
      setShowResched(false);
      toast.push("Reprogramada · pendiente de confirmar");
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo reprogramar");
    } finally {
      setBusy(false);
    }
  }

  // AGENDADA → confirmación del coach + "Unirme" y opción de reprogramar.
  if (vc.state === "scheduled" && vc.call) {
    return (
      <div className="mb-4 rounded-2xl p-4" style={box}>
        {header}
        <p className="mt-1 text-sm font-semibold">Confirmada por tu coach</p>
        <p className="mt-0.5 text-sm font-medium capitalize">{vc.call.when_label}</p>
        {vc.call.duration_min ? <p className="text-[11px] opacity-50">{vc.call.duration_min} min</p> : null}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {vc.call.meet_url && (
            <a href={vc.call.meet_url} target="_blank" rel="noopener noreferrer"
              className="tap inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold text-white"
              style={{ background: accent }}>
              <Video size={15} /> {vc.call.is_today ? "Unirme ahora" : "Unirme a Meet"}
            </a>
          )}
          {!showResched && (
            <button onClick={() => setShowResched(true)}
              className="tap inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold"
              style={{ border: `1px solid color-mix(in srgb, ${accent} 45%, transparent)`, color: accent }}>
              ¿No te va bien? Reprogramar
            </button>
          )}
        </div>
        {showResched && (
          <div className="mt-3">
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input type="date" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
                value={date} min={portalLocalToday()} onChange={(e) => setDate(e.target.value)} />
              <input type="time" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
                value={time} onChange={(e) => setTime(e.target.value)} />
              <button onClick={reschedule} disabled={!date || !time || busy}
                className="tap inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                style={{ background: accent }}>
                <CalendarCheck size={15} /> Reprogramar
              </button>
              <button onClick={() => setShowResched(false)} disabled={busy}
                className="tap inline-flex items-center rounded-xl px-3 py-1.5 text-xs font-semibold opacity-70">
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // TOCA PROPONER → formulario día + hora.
  if (vc.state === "book") {
    return (
      <div className="mb-4 rounded-2xl p-4" style={box}>
        {header}
        <p className="mt-1 text-sm">Elige día y hora</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input type="date" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
            value={date} min={portalLocalToday()} onChange={(e) => setDate(e.target.value)} />
          <input type="time" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
            value={time} onChange={(e) => setTime(e.target.value)} />
          <button onClick={propose} disabled={!date || !time || busy}
            className="tap inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: accent }}>
            <CalendarCheck size={15} /> Solicitar
          </button>
        </div>
      </div>
    );
  }

  // PROPUESTA ENVIADA → esperando al coach (con opción de cambiarla).
  if (vc.state === "proposed") {
    return (
      <div className="mb-4 rounded-2xl p-4" style={box}>
        {header}
        <p className="mt-1 text-sm">
          Propuesto: <b className="capitalize">{vc.call?.when_label}</b> · pendiente de confirmar
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input type="date" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
            value={date} min={portalLocalToday()} onChange={(e) => setDate(e.target.value)} />
          <input type="time" className="rounded-lg border px-2.5 py-1.5 text-sm" style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)`, background: "transparent" }}
            value={time} onChange={(e) => setTime(e.target.value)} />
          <button onClick={propose} disabled={!date || !time || busy}
            className="tap inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold"
            style={{ border: `1px solid color-mix(in srgb, ${accent} 45%, transparent)`, color: accent }}>
            Cambiar propuesta
          </button>
        </div>
      </div>
    );
  }

  // PENDIENTE MANUAL → el coach la agenda contigo por WhatsApp.
  if (vc.state === "pending_manual") {
    return (
      <div className="mb-4 rounded-2xl p-4" style={box}>
        {header}
        <p className="mt-1 text-sm">Te escribirá por WhatsApp</p>
      </div>
    );
  }

  return null;
}

/** Interruptor de NOTIFICACIONES en la cabecera: campana = activadas (toca para
 *  apagar), campana tachada = apagadas (toca para encender). El apagado borra la
 *  suscripción y deja un flag local para que no se reactive sola. */
function PushToggle({ api }: { api: ReturnType<typeof portalApi> }) {
  const toast = usePortalToast();
  const [on, setOn] = useState(pushIsOn);
  const [busy, setBusy] = useState(false);

  // Si el push cambia desde OTRO control (pasos de bienvenida), la campana
  // se actualiza sola — un solo estado real, varias vistas.
  useEffect(() => {
    const sync = () => setOn(pushIsOn());
    window.addEventListener(PUSH_CHANGED_EVENT, sync);
    return () => window.removeEventListener(PUSH_CHANGED_EVENT, sync);
  }, []);

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
          toast.push("iPhone: añádelo a inicio primero");
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
      title={on ? "Activadas · toca para apagar" : "Desactivadas · toca para activar"}
      className="tap -m-1 rounded-lg p-1 hover:opacity-80"
      style={{ opacity: on ? 0.85 : 0.4 }}
    >
      {on ? <Bell size={18} /> : <BellOff size={18} />}
    </button>
  );
}

/** ESCRIBIR AL COACH desde el portal (petición de ajuste).
 *
 *  Entre revisión y revisión el cliente no tenía NINGUNA forma de avisar: si se
 *  lesionaba el día 3, se iba de viaje o un alimento le sentaba mal, su única
 *  casilla de texto era "Dudas para tu coach"… que solo se abre el día 14. El
 *  circuito entero ya estaba construido en el backend (push inmediato ✋, email,
 *  alerta del panel y tarjeta "Peticiones sin responder" en Seguimiento) y
 *  nadie lo disparaba: no había pantalla. Esto lo enciende.
 *
 *  Cerrado por defecto para no competir con el registro del día. */
function EscribirAlCoach({ api, accent }: {
  api: ReturnType<typeof portalApi>; accent: string;
}) {
  const toast = usePortalToast();
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  const MIN = 5;      // el backend exige 5 caracteres…
  const MAX = 2000;   // …y admite 2000: se avisa AQUÍ, no con un 422 críptico.
  const limpio = texto.trim();

  const enviar = async () => {
    if (enviando || limpio.length < MIN) return;
    setEnviando(true);
    try {
      await api.changeRequest(limpio.slice(0, MAX));
      setTexto("");
      setEnviado(true);
      setAbierto(false);
      toast.push("Enviado · tu coach lo verá hoy ✅");
    } catch {
      // El mensaje NO se borra: el cliente puede reintentar sin reescribirlo.
      toast.push("No se pudo enviar · inténtalo de nuevo");
    } finally {
      setEnviando(false);
    }
  };

  if (!abierto) {
    return (
      <button
        onClick={() => { setAbierto(true); setEnviado(false); }}
        className="portal-note portal-note--info mb-4 w-full items-center text-left"
      >
        <MessageSquare size={18} style={{ color: accent }} />
        <span className="min-w-0">
          <span className="p-head block" style={{ color: accent }}>
            {enviado ? "Mensaje enviado ✅" : "Escribir a mi coach"}
          </span>
          <span className="p-sub mt-0.5 block">
            {enviado
              ? "Te responderá en cuanto lo vea · toca para escribir otro"
              : "Una duda, una molestia, un viaje… lo que necesites"}
          </span>
        </span>
      </button>
    );
  }

  return (
    <div className="portal-card mb-4 p-3.5">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0" style={{ color: accent }}><MessageSquare size={18} /></span>
        <div className="min-w-0 flex-1">
          <label htmlFor="mensaje-coach" className="text-sm font-semibold">
            Escribir a mi coach
          </label>
          <p className="mt-0.5 text-[11px] opacity-60">
            Le llega al momento. Cuéntale qué pasa y qué necesitas.
          </p>
          <textarea
            id="mensaje-coach"
            autoFocus
            rows={4}
            value={texto}
            maxLength={MAX}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Ej.: me molesta el hombro derecho en el press y esta semana estoy de viaje…"
            className="mt-2 min-h-[92px] w-full resize-y rounded-xl border bg-transparent p-3 text-sm"
            style={{ borderColor: "rgba(128,128,128,0.2)" }}
          />
          <div className="mt-1 text-right text-[11px] opacity-50">
            {limpio.length}/{MAX}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              onClick={enviar}
              disabled={enviando || limpio.length < MIN}
              className="portal-btn3d min-h-[36px] px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
              style={{ background: accent, color: "var(--p-on-accent)" }}
            >
              {enviando ? "Enviando…" : "Enviar a mi coach"}
            </button>
            <button
              onClick={() => setAbierto(false)}
              disabled={enviando}
              className="tap min-h-[36px] rounded-xl px-3 py-1.5 text-xs font-medium opacity-60 hover:opacity-90"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


/** FOTOS DE PROGRESO: tras enviar la revisión quincenal, el cliente puede
 *  SUBIRLAS aquí mismo, o confirmar que ya se las mandó al coach por otra vía.
 *  "Todavía no" lo pliega y el push se lo recuerda cada 3 h.
 *
 *  El botón de subir vive aquí porque, una vez enviada la revisión, la pantalla
 *  Quincenal pasa a "Revisión enviada · analizando" y pierde su sección de
 *  fotos — era la ÚNICA de toda la app que permitía subirlas. El cliente
 *  quedaba con un aviso cada 3 h que solo podía quitarse mintiendo ("sí, ya las
 *  envié") o posponiéndolo para siempre. El endpoint del backend siempre lo
 *  admitió: el período cerrado sigue siendo el activo. */
function PhotosReminder({ api, accent, onConfirmed }: {
  api: ReturnType<typeof portalApi>; accent: string; onConfirmed: () => void;
}) {
  const toast = usePortalToast();
  const [busy, setBusy] = useState(false);
  // "Todavía no": se pliega en ESTA sesión; el aviso vuelve al recargar (sigue
  // pendiente) y el push lo recuerda cada 3 h.
  const [snoozed, setSnoozed] = useState(false);
  const [fotos, setFotos] = useState(0);
  const [maxFotos, setMaxFotos] = useState(4);
  const [subiendo, setSubiendo] = useState(false);
  const entrada = useRef<HTMLInputElement | null>(null);

  // Cuántas lleva ya, según el SERVIDOR (que es quien pone el tope).
  useEffect(() => {
    let vivo = true;
    api.closePhotosCount()
      .then((r) => { if (vivo) { setFotos(r.count); setMaxFotos(r.max); } })
      .catch(() => { /* sin dato, el servidor sigue mandando */ });
    return () => { vivo = false; };
  }, [api]);

  if (snoozed) return null;

  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await api.confirmPhotos();
      toast.push("¡Gracias! Fotos confirmadas 📸");
      onConfirmed();
    } catch {
      toast.push("No se pudo confirmar");
      setBusy(false);
    }
  };

  /** Sube las que falten. El `kind` continúa por donde se quedó (frontal,
   *  lateral, espalda, detalle): si se reiniciara, el "antes y ahora" del
   *  informe compararía ángulos distintos. */
  const subir = async (files: FileList | null) => {
    if (!files || !files.length || subiendo) return;
    const tipos = ["front", "side", "back", "detail"];
    const lote = Array.from(files).slice(0, Math.max(0, maxFotos - fotos));
    if (!lote.length) { toast.push(`Ya has subido el máximo de ${maxFotos} fotos`); return; }
    setSubiendo(true);
    let subidas = 0;
    try {
      for (const f of lote) {
        await api.closePhotos([f], tipos[Math.min(fotos + subidas, tipos.length - 1)]);
        subidas += 1;
        setFotos(fotos + subidas);
      }
      toast.push(`${subidas} foto${subidas === 1 ? "" : "s"} subida${subidas === 1 ? "" : "s"} 📸`);
      // Con las fotos YA en el sistema el aviso sobra: el coach las tiene.
      await api.confirmPhotos().catch(() => {});
      onConfirmed();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudieron subir. Inténtalo de nuevo.");
      api.closePhotosCount().then((r) => setFotos(r.count)).catch(() => {});
    } finally {
      setSubiendo(false);
    }
  };

  return (
    <div className="portal-card mb-4 p-3.5">
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0" style={{ color: accent }}><Camera size={18} /></span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Tus fotos de progreso</p>
          <p className="mt-0.5 text-[11px] opacity-60">
            Frontal · lateral · espalda
            {fotos > 0 ? ` · llevas ${fotos} de ${maxFotos}` : ""}
          </p>
          <input
            ref={entrada}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => { subir(e.target.files); e.target.value = ""; }}
          />
          <div className="mt-2.5 flex flex-wrap gap-2">
            <button
              onClick={() => entrada.current?.click()}
              disabled={busy || subiendo || fotos >= maxFotos}
              className="portal-btn3d min-h-[36px] px-4 py-1.5 text-xs font-semibold"
              style={{ background: accent, color: "var(--p-on-accent)" }}
            >
              <span className="inline-flex items-center gap-1">
                <Camera size={13} /> {subiendo ? "Subiendo…" : fotos > 0 ? "Añadir más" : "Subir mis fotos"}
              </span>
            </button>
            <button
              onClick={confirm}
              disabled={busy || subiendo}
              className="tap min-h-[36px] rounded-xl px-3 py-1.5 text-xs font-medium opacity-70 hover:opacity-100"
            >
              <span className="inline-flex items-center gap-1"><Check size={13} /> Ya se las mandé</span>
            </button>
            <button
              onClick={() => { setSnoozed(true); toast.push("Te aviso cada 3 h"); }}
              disabled={busy}
              className="tap min-h-[36px] rounded-xl px-3 py-1.5 text-xs font-medium opacity-60 hover:opacity-90"
            >
              Todavía no
            </button>
          </div>
        </div>
      </div>
    </div>
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
function WelcomeSetup({ api, token, accent, secondary }: {
  api: ReturnType<typeof portalApi>; token: string; accent: string; secondary: string;
}) {
  const toast = usePortalToast();
  // Clave POR CLIENTE (token): en un móvil compartido, que un cliente lo
  // descarte no se lo esconde a otro. Las claves antiguas (globales) se
  // respetan como "ya descartado" para no reaparecer a quien ya lo cerró.
  const doneKey = `${WELCOME_DONE_KEY}_${token.slice(0, 16)}`;
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(doneKey) === "1"
      || localStorage.getItem(WELCOME_DONE_KEY) === "1"
      || localStorage.getItem(PUSH_DISMISSED_KEY) === "1"
  );
  // "Hecho" = las notificaciones están realmente ACTIVAS en este dispositivo
  // (permiso + no apagadas a mano), sincronizado con la campana de arriba.
  const [granted, setGranted] = useState(pushIsOn);
  useEffect(() => {
    const sync = () => setGranted(pushIsOn());
    window.addEventListener(PUSH_CHANGED_EVENT, sync);
    return () => window.removeEventListener(PUSH_CHANGED_EVENT, sync);
  }, []);
  const [busy, setBusy] = useState(false);
  // Descartar a mano exige CONFIRMAR: una vez oculto no vuelve a aparecer
  // (si completa los dos pasos, en cambio, desaparece solo sin preguntar).
  const [confirming, setConfirming] = useState(false);

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const installed = window.matchMedia("(display-mode: standalone)").matches
    || (navigator as unknown as { standalone?: boolean }).standalone === true;
  const installFirst = needsInstallFirst();

  // Todo hecho (o nada que ofrecer en este navegador) → no molestar más.
  if (dismissed || (granted && installed)) return null;
  // Navegador sin push posible y sin camino de instalación (WebView de
  // Instagram/WhatsApp en Android): el botón de activar solo daría error.
  if (!isPushSupported() && !installFirst) return null;

  const done = () => {
    localStorage.setItem(doneKey, "1");
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
            App en el móvil + avisos
          </span>
        </span>
        <ChevronDown size={16} className="shrink-0 opacity-50" />
      </summary>
      <div className="space-y-3.5 px-3 pb-3.5 pt-1">
        {/* Paso 1 — instalar como app (instrucciones según el móvil) */}
        <Step n={1} done={installed}>
          <p className="flex items-center gap-1.5 text-xs font-semibold">
            <Smartphone size={13} /> Añadir a pantalla de inicio
          </p>
          {installed ? (
            <p className="mt-0.5 text-[11px] opacity-60">Hecho · ya es app</p>
          ) : isIOS ? (
            <p className="mt-0.5 text-[11px] leading-relaxed opacity-70">
              Safari → <span className="font-semibold">Compartir</span>{" "}
              <Share size={11} className="inline" /> →{" "}
              <span className="font-semibold">Añadir a pantalla de inicio</span>
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
            <p className="mt-0.5 text-[11px] opacity-60">Hecho · te avisaré</p>
          ) : installFirst ? (
            <p className="mt-0.5 text-[11px] opacity-70">
              Haz antes el paso 1
            </p>
          ) : (
            <>
              <button
                onClick={activate}
                disabled={busy}
                className="portal-btn3d mt-1.5 min-h-[38px] px-4 py-1.5 text-xs font-semibold"
                style={{ background: accent, color: "var(--p-on-accent)" }}
              >
                {busy ? "Activando…" : "Activar recordatorios"}
              </button>
            </>
          )}
        </Step>

        {confirming ? (
          <div
            className="rounded-xl border p-2.5"
            style={{ borderColor: `color-mix(in srgb, ${accent} 35%, transparent)` }}
          >
            <p className="text-[11px] font-semibold">¿Seguro que quieres ocultarlo?</p>
            <p className="mt-0.5 text-[11px] opacity-60">
              No volverá a aparecer
            </p>
            <div className="mt-2 flex gap-2">
              <button
                onClick={done}
                className="tap rounded-lg px-3 py-1.5 text-[11px] font-semibold text-white"
                style={{ background: accent }}
              >
                Sí, ocultar
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="tap rounded-lg px-3 py-1.5 text-[11px] font-medium opacity-60 hover:opacity-90"
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="tap flex items-center gap-1 text-[11px] font-medium opacity-50 hover:opacity-80"
          >
            <X size={12} /> No volver a mostrar
          </button>
        )}
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
    // `portal-root`: sin él no existe ningún token --p-*, así que los botones
    // de estas pantallas salían sin fondo, sin radio y sin sombra.
    <div className="portal-root mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-8 text-center">
      {children}
    </div>
  );
}
