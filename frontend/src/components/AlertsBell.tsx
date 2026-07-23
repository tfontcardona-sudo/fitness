import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Bell, Check, Smartphone } from "lucide-react";
import { api, keepIfSame, REFRESH_MS } from "../lib/api";
import {
  coachPushActive,
  coachPushSubscribed,
  disableCoachPush,
  enableCoachPush,
  resyncCoachPushIfGranted,
} from "../lib/coachPush";
import { useDismiss } from "../lib/useDismiss";
import { useToast } from "./ui";
import type { CoachAlert } from "../types";

/**
 * Campana de ALERTAS del coach — preventiva e inteligente. Las alertas se
 * calculan del estado real de cada cliente (backend /api/alerts): en cuanto
 * la acción se hace, la alerta desaparece sola. Nada que marcar como leído.
 */
export function AlertsBell() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [alerts, setAlerts] = useState<CoachAlert[] | null>(null);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  useDismiss(panelRef, () => setOpen(false), open);

  // Push al MÓVIL del coach: estado local del interruptor + resuscripción
  // silenciosa al abrir la web (si el permiso ya estaba concedido).
  const [pushOn, setPushOn] = useState(coachPushActive);
  const [pushBusy, setPushBusy] = useState(false);
  useEffect(() => {
    // Tras la resuscripción silenciosa, el interruptor refleja el estado REAL
    // (suscripción viva), no solo el permiso.
    resyncCoachPushIfGranted().finally(() => {
      coachPushSubscribed().then(setPushOn).catch(() => {});
    });
  }, []);

  async function togglePush() {
    if (pushBusy) return;
    setPushBusy(true);
    try {
      if (pushOn) {
        await disableCoachPush();
        setPushOn(false);
        toast.push("Notificaciones al móvil desactivadas en este dispositivo");
      } else {
        await enableCoachPush();
        setPushOn(true);
        toast.push("Activado: recibirás en este dispositivo el resumen de pendientes cada 3 h");
      }
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "No se pudo cambiar", "error");
    } finally {
      setPushBusy(false);
    }
  }

  const load = useCallback(() => {
    // keepIfSame: no re-renderiza la campana cada 3 s si las alertas no cambian.
    api.listAlerts().then((r) => setAlerts((prev) => keepIfSame(prev, r.alerts))).catch(() => {});
  }, []);

  // Al montar, al navegar (una acción resuelta debe apagar su alerta al
  // instante) y de fondo cada 30 s — la web siempre al día.
  useEffect(load, [load, location.pathname, location.search]);
  useEffect(() => {
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [load]);

  const count = alerts?.length ?? 0;
  const high = alerts?.filter((a) => a.severity === "alta").length ?? 0;

  // Navega a la pestaña exacta donde hay que actuar. La usan por igual el
  // nombre del cliente, el mensaje y el botón de acción de cada alerta.
  const go = useCallback((a: CoachAlert) => {
    setOpen(false);
    navigate(`/clientes/${a.client_id}?tab=${a.tab}`);
  }, [navigate]);

  async function snooze(a: CoachAlert) {
    try {
      await api.snoozeGoalReview(a.client_id);
      toast.push("Objetivo mantenido: se volverá a valorar en 45 días");
      load();
    } catch {
      toast.push("No se pudo posponer", "error");
    }
  }

  return (
    <div className="alerts-bell fixed right-5 top-4 z-40" ref={panelRef}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        aria-label={count ? `${count} alertas pendientes` : "Sin alertas"}
        aria-expanded={open}
        className="card relative flex h-11 w-11 items-center justify-center rounded-full"
        style={{ boxShadow: "0 4px 16px rgba(38,33,26,0.12)" }}
      >
        <Bell size={18} style={{ color: count ? (high ? "var(--brand-accent)" : "var(--brand-accent-2)") : "var(--text-faint)" }} />
        {count > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white"
            style={{ background: high ? "#C2453A" : "var(--brand-accent-2)" }}
          >
            {count}
          </span>
        )}
      </button>

      {open && (
        <div
          className="card absolute right-0 mt-2 w-[380px] max-w-[calc(100vw-40px)] overflow-hidden max-sm:bottom-14 max-sm:mt-0"
          role="dialog"
          aria-label="Alertas del coach"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "var(--line)" }}>
            <span className="text-sm font-semibold text-zinc-100">Alertas</span>
            <span className="text-xs text-zinc-500">
              {count === 0 ? "todo al día" : `${count} pendiente${count === 1 ? "" : "s"}`}
            </span>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            {count === 0 ? (
              <div className="flex items-center justify-center gap-2 px-4 py-8 text-sm text-zinc-500">
                <Check size={16} style={{ color: "var(--brand-accent)" }} /> Nada pendiente con tus clientes.
              </div>
            ) : (
              // AGRUPADAS por ámbito: primero el total (cabecera) y aquí cada
              // clase de alerta con su color, para escanearlas de un vistazo.
              GROUPS.map((g) => {
                const known = new Set(GROUPS.flatMap((x) => x.kinds));
                const items = (alerts ?? []).filter((a) =>
                  g.id === "otras" ? !known.has(a.kind) : g.kinds.includes(a.kind));
                if (!items.length) return null;
                return (
                  <div key={g.id}>
                    <div className="flex items-center gap-2 px-4 pb-1 pt-2.5"
                      style={{ background: `color-mix(in srgb, ${g.color} 6%, transparent)` }}>
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: g.color }} />
                      <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color: g.color }}>
                        {g.label}
                      </span>
                      <span className="text-[11px] text-zinc-500">{items.length}</span>
                    </div>
                    {items.map((a, i) => renderAlert(a, i))}
                  </div>
                );
              })
            )}
          </div>
          {/* Interruptor: recibir todo esto también en el MÓVIL (push cada 3 h) */}
          <div className="flex items-center justify-between gap-2 border-t px-4 py-2.5"
            style={{ borderColor: "var(--line)" }}>
            <span className="flex items-center gap-1.5 text-xs text-zinc-400">
              <Smartphone size={13} /> Avisos en el móvil
            </span>
            <button
              onClick={togglePush}
              disabled={pushBusy}
              className="text-xs font-semibold hover:opacity-80 disabled:opacity-50"
              style={{ color: pushOn ? "var(--brand-accent)" : "var(--text-faint)" }}
            >
              {pushBusy ? "…" : pushOn ? "Activados · desactivar" : "Activar"}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  function renderAlert(a: CoachAlert, i: number) {
    return (
                <div
                  key={`${a.client_id}-${a.kind}-${i}`}
                  className="flex items-start gap-2.5 border-b px-4 py-3 last:border-b-0"
                  style={{ borderColor: "var(--line)" }}
                >
                  <span
                    aria-hidden
                    className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: a.severity === "alta" ? "#C2453A" : "var(--brand-accent-2)" }}
                  />
                  <div className="min-w-0 flex-1">
                    {/* Nombre + mensaje clicables: llevan a la misma pestaña
                        donde hay que actuar que el botón de acción. */}
                    <button onClick={() => go(a)} className="group block w-full text-left">
                      <span className="block text-sm font-medium text-zinc-100 group-hover:opacity-80">{a.client_name}</span>
                      <span className="mt-0.5 block text-xs text-zinc-400 group-hover:text-zinc-300">{a.message}</span>
                    </button>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      <button
                        onClick={() => go(a)}
                        className="text-xs font-semibold hover:opacity-80"
                        style={{ color: "var(--brand-accent)" }}
                      >
                        {a.action} →
                      </button>
                      {a.kind === "goal_review" && (
                        <button onClick={() => snooze(a)} className="text-xs text-zinc-500 hover:text-zinc-200">
                          Mantener objetivo
                        </button>
                      )}
                    </div>
                  </div>
                </div>
    );
  }
}

/** Clases de alerta (ámbitos) para agruparlas en la campana, cada una con su
 *  color. Un kind no listado cae en "Otras". */
const GROUPS: { id: string; label: string; color: string; kinds: string[] }[] = [
  { id: "arranque", label: "Arranque / alta", color: "#6366F1", kinds: ["create_plan", "publish_plan"] },
  { id: "revision", label: "Revisión quincenal", color: "#8B5CF6", kinds: ["generate_feedback", "send_feedback"] },
  { id: "adaptacion", label: "Planificación", color: "#E8833A", kinds: ["adapt_plan", "regenerate_goal"] },
  { id: "seguimiento", label: "Seguimiento", color: "#C2453A", kinds: ["no_logs", "change_request"] },
  { id: "objetivo", label: "Objetivo", color: "#2E5E8C", kinds: ["goal_review"] },
  { id: "recursos", label: "Recursos / productos", color: "#28707C", kinds: ["missing_products"] },
  { id: "videollamada", label: "Videollamada", color: "#0EA5E9",
    kinds: ["video_call_wait", "video_call_proposed", "video_call_manual",
            "video_call_tomorrow", "video_call_confirm"] },
  { id: "otras", label: "Otras", color: "#7A7A7A", kinds: [] },
];
