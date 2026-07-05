import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ClientOut } from "../types";

type Tracking = Awaited<ReturnType<typeof api.getClientTracking>>;

/**
 * Seguimiento del cliente EN TIEMPO REAL para el coach. Hace polling cada 10 s:
 * lo que el cliente registra (diario con series, y revisión quincenal) aparece
 * en cuanto guarda; lo que falta se muestra como "pendiente".
 */
export function ClientTrackingTab({ client }: { client: ClientOut }) {
  const [data, setData] = useState<Tracking | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .getClientTracking(client.id)
        .then((d) => alive && setData(d))
        .catch((e) => alive && setErr(e?.message ?? "Error"));
    load();
    timer.current = window.setInterval(load, 10000); // polling → tiempo real
    return () => {
      alive = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [client.id]);

  if (err) return <div className="card p-5 text-sm text-red-400">No se pudo cargar el seguimiento: {err}</div>;
  if (!data) return <div className="card p-5 text-sm opacity-60">Cargando seguimiento…</div>;
  if (!data.has_period)
    return <div className="card p-5 text-sm opacity-60">El cliente aún no tiene un período activo. Créalo en Planificación.</div>;

  const p = data.period!;
  const daily = data.daily ?? [];
  const avg = data.daily_averages;
  const quincenals = data.quincenals ?? [];
  const pct = Math.min(100, Math.round((p.days_elapsed / p.days_total) * 100));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">Seguimiento en tiempo real</h3>
        <span className="text-xs text-zinc-500">se actualiza solo · período {p.index}</span>
      </div>

      <div className="card p-4">
        <div className="flex justify-between text-xs text-zinc-400">
          <span>{p.starts_on} → {p.ends_on}</span>
          <span>día {p.days_elapsed}/{p.days_total}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded" style={{ background: "var(--surface-raised)" }}>
          <div className="h-full rounded" style={{ width: `${pct}%`, background: "var(--brand-accent)" }} />
        </div>
        <div className="mt-2 text-xs text-zinc-300">
          Días registrados: <b>{data.days_logged ?? 0}</b> ·{" "}
          Hoy:{" "}
          {data.today_logged
            ? <span className="text-emerald-400">registrado</span>
            : <span className="text-amber-400">pendiente</span>}
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="border-b border-white/5 px-4 py-2 text-xs font-semibold text-zinc-300">Registros diarios</div>
        {daily.length === 0 ? (
          <p className="p-4 text-sm text-amber-400">Sin registros todavía (pendiente).</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-zinc-500">
                <tr className="text-left">
                  <th className="px-3 py-2">Fecha</th><th>Peso</th><th>Sueño</th>
                  <th>Pasos</th><th>Sac.</th><th>Agua</th><th>Dieta</th><th>Series</th>
                </tr>
              </thead>
              <tbody className="text-zinc-200">
                {daily.map((d) => (
                  <tr key={d.date} className="border-t border-white/5">
                    <td className="px-3 py-2">{d.date}</td>
                    <td>{fmt1(d.weight_kg)}</td>
                    <td>{fmt1(d.sleep_hours)}</td>
                    <td className="max-w-[130px] truncate">{d.steps ?? "—"}</td>
                    <td>{d.satiety_1_10 ?? "—"}</td>
                    <td>{fmt1(d.water_liters)}</td>
                    <td>{ADHERENCE_LABEL[d.diet_adherence ?? ""] ?? d.diet_adherence ?? "—"}</td>
                    <td>{d.workout_sets || "—"}</td>
                  </tr>
                ))}
              </tbody>
              {avg && (
                <tfoot>
                  <tr className="border-t border-white/10 font-semibold text-zinc-100" style={{ background: "var(--surface-raised)" }}>
                    <td className="px-3 py-2">Media</td>
                    <td>{fmt1(avg.weight_kg)}</td>
                    <td>{fmt1(avg.sleep_hours)}</td>
                    <td className="max-w-[130px] truncate">{avg.steps != null ? Math.round(avg.steps) : "—"}</td>
                    <td>{avg.satiety_1_10 ?? "—"}</td>
                    <td>{avg.water_liters ?? "—"}</td>
                    <td>{avg.diet_adherence_pct != null ? `${avg.diet_adherence_pct}%` : "—"}</td>
                    <td>{avg.workout_sets ?? "—"}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-zinc-100">Revisiones quincenales</span>
          <span className="text-xs text-zinc-500">{quincenals.length} recibida{quincenals.length === 1 ? "" : "s"}</span>
        </div>
        {quincenals.length === 0 ? (
          <div className="card p-4 text-xs text-amber-400">Aún no hay revisiones quincenales (pendiente).</div>
        ) : (
          quincenals.map((q, i) => (
            <details key={q.period_index} className="card overflow-hidden p-0" open={i === 0}>
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm">
                <span className="font-semibold text-zinc-100">
                  Revisión #{q.period_index} · <span className="text-zinc-400">{q.starts_on} → {q.ends_on}</span>
                </span>
                <span className="flex items-center gap-2">
                  {q.feelings_score_10 != null && (
                    <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ background: "color-mix(in srgb, var(--brand-accent-2, #2E5E8C) 25%, transparent)", color: "#8FB4D6" }}>
                      {q.feelings_score_10}/10
                    </span>
                  )}
                  <span className="text-xs text-emerald-400">{q.analyzed ? "analizada" : "recibida"}</span>
                </span>
              </summary>
              <div className="border-t border-white/5 px-4 py-3">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <BeforeAfter label="Peso (kg)" before={q.weight_before} after={q.weight_after} lowerBetter />
                  <BeforeAfter label="Cintura (cm)" before={q.waist_before} after={q.waist_after} lowerBetter />
                  <BeforeAfter label="Cadera (cm)" before={q.hip_before} after={q.hip_after} lowerBetter />
                  <BeforeAfter label="Brazo (cm)" before={q.arm_before} after={q.arm_after} />
                  <BeforeAfter label="Muslo (cm)" before={q.thigh_before} after={q.thigh_after} />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs text-zinc-300">
                  <span>Adherencia dieta: <b>{q.adherence_diet ?? "—"}/10</b></span>
                  <span>Adherencia entreno: <b>{q.adherence_training ?? "—"}/10</b></span>
                  <span>Comidas libres: <b>{q.free_meals ?? "—"}</b></span>
                  <span>Valoración sensaciones: <b>{q.feelings_score_10 ?? "—"}/10</b></span>
                  {q.feelings && (
                    <span className="col-span-2">
                      Sensaciones: {Object.entries(q.feelings).map(([k, v]) => `${k} ${v}/5`).join(" · ")}
                    </span>
                  )}
                  {q.changes && <span className="col-span-2">Cambios: {q.changes}</span>}
                  {q.hardest && <span className="col-span-2">Le cuesta: {q.hardest}</span>}
                  {q.next_goal && <span className="col-span-2">Objetivo: {q.next_goal}</span>}
                  {q.questions && <span className="col-span-2">Dudas: {q.questions}</span>}
                </div>
              </div>
            </details>
          ))
        )}
      </div>
    </div>
  );
}

/** Peso/sueño/agua con un decimal como mucho (evita 83.60000000000001). */
function fmt1(v: number | null | undefined): string | number {
  return v == null ? "—" : Math.round(v * 10) / 10;
}

const ADHERENCE_LABEL: Record<string, string> = { yes: "sí", partial: "parcial", no: "no" };

/** Antes → después con delta coloreado. */
function BeforeAfter({ label, before, after, lowerBetter }: {
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
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#F77E7E" : "#a1a1aa" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}
