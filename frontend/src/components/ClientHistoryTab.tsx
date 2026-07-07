import { useEffect, useState } from "react";
import { TrendingDown, History, Ruler, LineChart } from "lucide-react";
import { api } from "../lib/api";
import { Spinner } from "./ui";
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
 * Resumen global + tabla por período (peso/adherencia/fuerza) + planes.
 * Editable desde sus pestañas.
 */
export function ClientHistoryTab({ client }: { client: ClientOut }) {
  const [h, setH] = useState<Hist | null>(null);

  useEffect(() => {
    api.getClientHistory(client.id).then(setH).catch(() => setH(null));
  }, [client.id]);

  if (!h) {
    return <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500"><Spinner /> Cargando historial…</div>;
  }

  // Misma fuente y fallback que la pestaña Resumen: sin divergencias
  const currentW = h.current_weight_kg ?? client.current_weight_kg ?? null;
  const delta = currentW != null && h.start_weight_kg != null
    ? Math.round((currentW - h.start_weight_kg) * 10) / 10 : null;
  const measureRows: [string, "waist" | "hip" | "arm" | "thigh"][] = [
    ["Cintura", "waist"], ["Cadera", "hip"], ["Brazo", "arm"], ["Muslo", "thigh"],
  ];
  const hasMeasures = measureRows.some(([, k]) => h.measures?.[k]?.before != null || h.measures?.[k]?.after != null);

  return (
    <div className="space-y-4">
      {/* Resumen global + objetivo */}
      <div className="card p-5">
        <div className="mb-3">
          <Title icon={History} text="Resumen del cliente" />
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Stat label="Peso inicial" value={h.start_weight_kg != null ? `${h.start_weight_kg} kg` : "—"} />
          <Stat label="Peso actual" value={currentW != null ? `${currentW} kg` : "—"} />
          <Stat label="Cambio total" value={delta != null ? `${delta > 0 ? "+" : ""}${delta} kg` : "—"} highlight />
          <Stat label="Objetivo" value={h.goal_weight_kg != null ? `${h.goal_weight_kg} kg` : "—"} />
          <Stat label="Le quedan" value={h.remaining_to_goal_kg != null ? `${h.remaining_to_goal_kg} kg` : "—"} highlight />
          <Stat label="Fuerza ganada (total)" value={h.total_strength_gain_pct != null ? `${h.total_strength_gain_pct > 0 ? "+" : ""}${h.total_strength_gain_pct}%` : "—"} />
        </div>
      </div>

      {/* Comparativa entre revisiones quincenales: gráfico + números + % */}
      <ReviewComparison h={h} lowerBetter={client.goal_type !== "muscle_gain"} />

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

function Title({ icon: Icon, text, accent }: { icon: typeof History; text: string; accent?: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={16} style={{ color: accent ?? "var(--brand-accent)" }} />
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

/**
 * Comparativa entre revisiones quincenales: cómo evoluciona el peso revisión a
 * revisión (gráfico de línea con el valor en cada punto) + tabla con números y
 * porcentajes (Δ kg, Δ %, adherencia y fuerza por período) + fila TOTAL.
 */
function ReviewComparison({ h, lowerBetter }: { h: Hist; lowerBetter: boolean }) {
  const rows = h.periods.filter((p) => p.closing_weight_kg != null);
  if (rows.length === 0) return null;

  // Puntos del gráfico: peso inicial ("Inicio") + cierre de cada revisión
  const points: { label: string; value: number }[] = [];
  if (h.start_weight_kg != null) points.push({ label: "Inicio", value: h.start_weight_kg });
  rows.forEach((p) => points.push({ label: `R${p.period_index}`, value: p.closing_weight_kg as number }));

  const pct = (from: number | null, to: number | null) =>
    from != null && to != null && from !== 0 ? Math.round(((to - from) / from) * 1000) / 10 : null;

  const totalDelta = h.start_weight_kg != null && h.current_weight_kg != null
    ? Math.round((h.current_weight_kg - h.start_weight_kg) * 10) / 10 : null;
  const totalPct = pct(h.start_weight_kg, h.current_weight_kg);

  // Peso "antes" de cada revisión = cierre de la anterior (o el inicial)
  const beforeOf = (i: number): number | null =>
    i === 0 ? (h.start_weight_kg ?? null) : (rows[i - 1].closing_weight_kg as number);

  return (
    <div className="card p-5">
      <Title icon={LineChart} text="Evolución tras las revisiones quincenales" accent="var(--brand-accent-2)" />

      {points.length >= 2 && <WeightLine points={points} />}

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide" style={{ color: "var(--brand-accent-2)" }}>
              <th className="py-1.5 pr-3 font-semibold">Revisión</th>
              <th className="py-1.5 pr-3 font-semibold">Peso</th>
              <th className="py-1.5 pr-3 font-semibold">Δ kg</th>
              <th className="py-1.5 pr-3 font-semibold">Δ %</th>
              <th className="py-1.5 pr-3 font-semibold">Adherencia</th>
              <th className="py-1.5 font-semibold">Fuerza</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => {
              const before = beforeOf(i);
              const after = p.closing_weight_kg as number;
              const dKg = before != null ? Math.round((after - before) * 10) / 10 : null;
              const dPct = pct(before, after);
              return (
                <tr key={p.period_index} className="border-t" style={{ borderColor: "var(--line)" }}>
                  <td className="py-2 pr-3 font-medium text-zinc-200">#{p.period_index}</td>
                  <td className="py-2 pr-3 text-zinc-300">{before != null ? `${before} → ` : ""}{after} kg</td>
                  <td className="py-2 pr-3"><DeltaCell v={dKg} unit="kg" lowerBetter={lowerBetter} /></td>
                  <td className="py-2 pr-3"><DeltaCell v={dPct} unit="%" lowerBetter={lowerBetter} /></td>
                  <td className="py-2 pr-3 text-zinc-300">{p.adherence_pct != null ? `${p.adherence_pct}%` : "—"}</td>
                  <td className="py-2 text-zinc-300">
                    {p.strength_gain_pct != null ? `${p.strength_gain_pct > 0 ? "+" : ""}${p.strength_gain_pct}%` : "—"}
                  </td>
                </tr>
              );
            })}
            <tr className="border-t font-semibold" style={{ borderColor: "var(--line)" }}>
              <td className="py-2 pr-3 text-zinc-100">Total</td>
              <td className="py-2 pr-3 text-zinc-200">
                {h.start_weight_kg ?? "—"} → {h.current_weight_kg ?? "—"} kg
              </td>
              <td className="py-2 pr-3"><DeltaCell v={totalDelta} unit="kg" lowerBetter={lowerBetter} /></td>
              <td className="py-2 pr-3"><DeltaCell v={totalPct} unit="%" lowerBetter={lowerBetter} /></td>
              <td className="py-2 pr-3 text-zinc-300">—</td>
              <td className="py-2 text-zinc-300">
                {h.total_strength_gain_pct != null ? `${h.total_strength_gain_pct > 0 ? "+" : ""}${h.total_strength_gain_pct}%` : "—"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Delta con signo y color según si mejora (baja en pérdida / sube en volumen). */
function DeltaCell({ v, unit, lowerBetter }: { v: number | null; unit: string; lowerBetter: boolean }) {
  if (v == null) return <span className="text-zinc-500">—</span>;
  const good = lowerBetter ? v < 0 : v > 0;
  const color = v === 0 ? "#7A7060" : good ? "var(--brand-accent)" : "#C2453A";
  return <span className="font-medium" style={{ color }}>{v > 0 ? "+" : ""}{v} {unit}</span>;
}

/** Línea del peso por revisión: marcas finas, punto con anillo del fondo y el
 *  valor rotulado en cada punto (pocos puntos; si hay muchos, solo los clave). */
function WeightLine({ points }: { points: { label: string; value: number }[] }) {
  const W = 560, H = 150, padX = 30, padTop = 26, padBottom = 24;
  const vals = points.map((p) => p.value);
  const lo0 = Math.min(...vals), hi0 = Math.max(...vals);
  const span = hi0 - lo0 || 1;
  const lo = lo0 - span * 0.15, hi = hi0 + span * 0.15;
  const x = (i: number) => points.length === 1 ? W / 2 : padX + (i / (points.length - 1)) * (W - 2 * padX);
  const y = (v: number) => padTop + (1 - (v - lo) / (hi - lo)) * (H - padTop - padBottom);
  // Con muchos puntos, solo se rotulan los clave (primero, último, mín y máx)
  const labelAll = points.length <= 6;
  const iMin = vals.indexOf(lo0), iMax = vals.indexOf(hi0);
  const showLabel = (i: number) => labelAll || i === 0 || i === points.length - 1 || i === iMin || i === iMax;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full" role="img" aria-label="Evolución del peso por revisión">
      {/* rejilla recesiva */}
      {[0.25, 0.5, 0.75].map((t) => (
        <line key={t} x1={padX - 8} x2={W - padX + 8} y1={padTop + t * (H - padTop - padBottom)} y2={padTop + t * (H - padTop - padBottom)}
          stroke="var(--line)" strokeWidth="1" />
      ))}
      <polyline
        points={points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ")}
        fill="none" stroke="var(--brand-accent)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
      />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={x(i)} cy={y(p.value)} r="4.5" fill="var(--brand-accent)" stroke="var(--surface)" strokeWidth="2">
            <title>{p.label}: {p.value} kg</title>
          </circle>
          {showLabel(i) && (
            <text x={x(i)} y={y(p.value) - 10} textAnchor="middle" fontSize="11" fontWeight="600" fill="#26211A">
              {p.value}
            </text>
          )}
          <text x={x(i)} y={H - 6} textAnchor="middle" fontSize="10" fill="#7A7060">{p.label}</text>
        </g>
      ))}
    </svg>
  );
}
