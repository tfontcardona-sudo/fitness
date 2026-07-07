import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Bell, Check } from "lucide-react";
import { api } from "../lib/api";
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

  const load = useCallback(() => {
    api.listAlerts().then((r) => setAlerts(r.alerts)).catch(() => {});
  }, []);

  // Al montar, al navegar (una acción resuelta debe apagar su alerta al
  // instante) y de fondo cada 2 minutos.
  useEffect(load, [load, location.pathname, location.search]);
  useEffect(() => {
    const t = window.setInterval(load, 120000);
    return () => window.clearInterval(t);
  }, [load]);

  const count = alerts?.length ?? 0;
  const high = alerts?.filter((a) => a.severity === "alta").length ?? 0;

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
              (alerts ?? []).map((a, i) => (
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
                    <p className="text-sm font-medium text-zinc-100">{a.client_name}</p>
                    <p className="mt-0.5 text-xs text-zinc-400">{a.message}</p>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      <button
                        onClick={() => { setOpen(false); navigate(`/clientes/${a.client_id}?tab=${a.tab}`); }}
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
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
