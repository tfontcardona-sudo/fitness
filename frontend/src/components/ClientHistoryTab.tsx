import { useEffect, useState } from "react";
import { Download, TrendingDown, History, Ruler } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

type Hist = Awaited<ReturnType<typeof api.getClientHistory>>;

const STATUS: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };
function badge(s: string): React.CSSProperties {
  if (s === "analyzed") return { background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" };
  if (s === "closed") return { background: "rgba(154,107,21,0.14)", color: "#9A6B15" };
  return { background: "rgba(38,33,26,0.08)", color: "#7A7060" };
}

/**
 * Historial: toda la evolución del cliente en el tiempo, resumida y limpia.
 * Resumen global + tabla por período (peso/adherencia/fuerza) + planes. Todo
 * descargable (ZIP completo o cada plan en Word). Editable desde sus pestañas.
 */
export function ClientHistoryTab({ client }: { client: ClientOut }) {
  const toast = useToast();
  const [h, setH] = useState<Hist | null>(null);

  useEffect(() => {
    api.getClientHistory(client.id).then(setH).catch(() => setH(null));
  }, [client.id]);

  function dl(url: string, name: string) {
    fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((b) => {
        const u = URL.createObjectURL(b);
        const a = document.createElement("a");
        a.href = u; a.download = name; a.click();
        URL.revokeObjectURL(u);
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (!h) {
    return <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500"><Spinner /> Cargando historial…</div>;
  }

  const delta = h.current_weight_kg != null && h.start_weight_kg != null
    ? Math.round((h.current_weight_kg - h.start_weight_kg) * 10) / 10 : null;
  const closings = h.periods.map((p) => p.closing_weight_kg).filter((w): w is number => w != null);
  const slug = client.full_name.replace(/\s+/g, "_").toLowerCase();
  const measureRows: [string, "waist" | "hip" | "arm" | "thigh"][] = [
    ["Cintura", "waist"], ["Cadera", "hip"], ["Brazo", "arm"], ["Muslo", "thigh"],
  ];
  const hasMeasures = measureRows.some(([, k]) => h.measures?.[k]?.before != null || h.measures?.[k]?.after != null);

  return (
    <div className="space-y-4">
      {/* Resumen global + objetivo */}
      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <Title icon={History} text="Resumen del cliente" />
          <button onClick={() => dl(api.exportClientUrl(client.id), `cliente_${slug}.zip`)} className="btn btn-ghost">
            <Download size={15} /> Descargar todo
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Stat label="Peso inicial" value={h.start_weight_kg != null ? `${h.start_weight_kg} kg` : "—"} />
          <Stat label="Peso actual" value={h.current_weight_kg != null ? `${h.current_weight_kg} kg` : "—"} />
          <Stat label="Cambio total" value={delta != null ? `${delta > 0 ? "+" : ""}${delta} kg` : "—"} highlight />
          <Stat label="Objetivo" value={h.goal_weight_kg != null ? `${h.goal_weight_kg} kg` : "—"} />
          <Stat label="Le quedan" value={h.remaining_to_goal_kg != null ? `${h.remaining_to_goal_kg} kg` : "—"} highlight />
          <Stat label="Fuerza ganada (total)" value={h.total_strength_gain_pct != null ? `${h.total_strength_gain_pct > 0 ? "+" : ""}${h.total_strength_gain_pct}%` : "—"} />
        </div>
        {closings.length >= 2 && <Spark data={closings} />}
      </div>

      {/* Medidas corporales antes → después */}
      {hasMeasures && (
        <div className="card p-5">
          <Title icon={Ruler} text="Medidas corporales (antes → después)" />
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {measureRows.map(([label, key]) => (
              <BA key={key} label={`${label} (cm)`} before={h.measures?.[key]?.before ?? null} after={h.measures?.[key]?.after ?? null} lowerBetter={key !== "arm"} />
            ))}
          </div>
        </div>
      )}

      {/* Evolución por período (desplegable) */}
      <div className="card p-5">
        <Title icon={TrendingDown} text="Evolución por período" />
        {h.periods.length === 0 ? (
          <p className="mt-2 text-xs text-zinc-500">Aún no hay períodos.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {h.periods.slice().reverse().map((p) => (
              <details key={p.period_index} className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
                <summary className="flex cursor-pointer items-center justify-between px-3 py-2.5 text-sm" style={{ background: "var(--surface-raised)" }}>
                  <span className="flex items-center gap-2">
                    <span className="font-semibold text-zinc-100">Período #{p.period_index}</span>
                    <span className="text-xs text-zinc-500">{p.starts_on} → {p.ends_on}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-xs" style={badge(p.status)}>{STATUS[p.status] ?? p.status}</span>
                    <span className="text-xs text-zinc-400">{p.feedback_id ? (p.feedback_sent ? "FB enviado" : "FB borrador") : ""}</span>
                  </span>
                </summary>
                <div className="px-3 py-3">
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <Stat label="Peso cierre" value={p.closing_weight_kg != null ? `${p.closing_weight_kg} kg${p.weight_delta_kg != null ? ` (${p.weight_delta_kg > 0 ? "+" : ""}${p.weight_delta_kg})` : ""}` : "—"} />
                    <Stat label="Adherencia" value={p.adherence_pct != null ? `${p.adherence_pct}%` : "—"} />
                    <Stat label="Fuerza (e1RM)" value={p.best_e1rm_kg != null ? `${Math.round(p.best_e1rm_kg)} kg` : "—"} />
                    <Stat label="↑ Fuerza período" value={p.strength_gain_pct != null ? `${p.strength_gain_pct > 0 ? "+" : ""}${p.strength_gain_pct}%` : "—"} />
                  </div>
                  <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    <Ruler size={12} /> Cinta (cm)
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-2 text-xs text-zinc-300 sm:grid-cols-4">
                    <span>Cintura: <b>{p.waist_cm ?? "—"}</b></span>
                    <span>Cadera: <b>{p.hip_cm ?? "—"}</b></span>
                    <span>Brazo: <b>{p.arm_cm ?? "—"}</b></span>
                    <span>Muslo: <b>{p.thigh_cm ?? "—"}</b></span>
                  </div>
                </div>
              </details>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Antes → después con delta coloreado. */
function BA({ label, before, after, lowerBetter }: {
  label: string; before: number | null; after: number | null; lowerBetter?: boolean;
}) {
  const delta = before != null && after != null ? Math.round((after - before) * 10) / 10 : null;
  const good = delta != null && (lowerBetter ? delta < 0 : delta > 0);
  const bad = delta != null && delta !== 0 && !good;
  return (
    <div className="rounded-lg p-2.5" style={{ background: "var(--surface-raised)" }}>
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-sm text-zinc-100">
        <span className="text-zinc-400">{before ?? "—"}</span>
        <span className="text-zinc-600">→</span>
        <span className="font-semibold">{after ?? "—"}</span>
        {delta != null && delta !== 0 && (
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#C2453A" : "#7A7060" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

function Title({ icon: Icon, text }: { icon: typeof History; text: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{text}</h4>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg p-3 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-lg font-bold" style={{ color: highlight ? "var(--brand-accent)" : "#26211A" }}>{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function Spark({ data }: { data: number[] }) {
  const w = 280, h = 44, min = Math.min(...data), max = Math.max(...data), range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 4 - ((v - min) / range) * (h - 8)}`).join(" ");
  return (
    <div className="mt-4">
      <div className="mb-1 text-xs text-zinc-500">Peso de cierre por período</div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 56 }} preserveAspectRatio="none">
        <polyline points={pts} fill="none" stroke="var(--brand-accent)" strokeWidth="2" />
      </svg>
    </div>
  );
}
