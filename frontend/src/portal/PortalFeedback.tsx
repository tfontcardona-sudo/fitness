import { useEffect, useState } from "react";
import { LineChart, TrendingDown, Target, Sparkles, MessageSquare } from "lucide-react";
import type { FeedbackDocOut, PortalBrand } from "../types";
import { Empty, Loading } from "./PortalToday";
import type { portalApi } from "./portalApi";

type Api = ReturnType<typeof portalApi>;

/**
 * Tu progreso: informes ENVIADOS por el coach, en formato visual y por puntos:
 * cifras clave + gráfica de peso + análisis breve + cambios y objetivos.
 */
export function PortalFeedback({ api, brand }: { api: Api; brand: PortalBrand }) {
  const [docs, setDocs] = useState<FeedbackDocOut[] | null>(null);
  const accent = brand.color_primary;

  useEffect(() => {
    api.feedback().then(setDocs).catch(() => setDocs([]));
  }, [api]);

  if (docs === null) return <Loading />;
  if (docs.length === 0) {
    return (
      <Empty
        icon={LineChart}
        title="Aún no hay informes"
        hint="Cuando tu coach te envíe tu informe, aquí verás tu progreso con cifras, gráfica y objetivos."
      />
    );
  }

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold">Tu progreso</h2>
      {docs.map((d) => {
        const c = (d.content_json ?? {}) as any;
        const w = c.metrics?.weight ?? {};
        const adh = c.metrics?.adherence ?? {};
        const dietPct = adh.diet_adherence_ratio != null ? Math.round(adh.diet_adherence_ratio * 100) : null;
        const points: [string, number][] = Array.isArray(c.weight_points) ? c.weight_points : [];
        return (
          <div key={d.id} className="space-y-4 rounded-2xl border p-4" style={cardStyle}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">{d.kind === "monthly" ? "Informe mensual" : "Informe quincenal"}</p>
              <span className="text-xs opacity-50">
                {d.sent_at ? new Date(d.sent_at).toLocaleDateString("es-ES", { day: "numeric", month: "long" }) : ""}
              </span>
            </div>

            {/* Cifras clave (grandes, con color) */}
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex items-center gap-1.5 text-xs opacity-50"><TrendingDown size={13} style={{ color: accent }} /> Cambio de peso</div>
                <div className="mt-1 text-2xl font-bold" style={{ color: accent }}>
                  {w.delta_kg != null ? `${w.delta_kg > 0 ? "+" : ""}${w.delta_kg} kg` : "—"}
                </div>
                {w.weekly_rate_kg != null && <div className="text-xs opacity-50">{w.weekly_rate_kg} kg/semana</div>}
              </div>
              <div className="rounded-xl border p-3" style={{ borderColor: "rgba(128,128,128,0.18)" }}>
                <div className="flex items-center gap-1.5 text-xs opacity-50"><Sparkles size={13} style={{ color: accent }} /> Adherencia dieta</div>
                <div className="mt-1 text-2xl font-bold" style={{ color: accent }}>{dietPct != null ? `${dietPct}%` : "—"}</div>
                {dietPct != null && (
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full" style={{ background: "rgba(128,128,128,0.2)" }}>
                    <div className="h-full rounded-full" style={{ width: `${dietPct}%`, background: accent }} />
                  </div>
                )}
              </div>
            </div>

            {/* Gráfica de peso */}
            {points.length >= 2 && <WeightChart points={points} goal={c.goal_weight_kg ?? null} accent={accent} />}

            {/* Análisis (breve) */}
            {c.natural_analysis && <p className="text-sm opacity-90">{c.natural_analysis}</p>}

            {/* Cambios en el plan */}
            {Array.isArray(c.changes_bullets) && c.changes_bullets.length > 0 && (
              <Section icon={Sparkles} title="Cambios en tu plan" accent={accent} items={c.changes_bullets} />
            )}

            {/* Respuesta a dudas */}
            {c.answers && (
              <div>
                <Head icon={MessageSquare} title="Respuesta a tus dudas" accent={accent} />
                <p className="text-sm opacity-90">{c.answers}</p>
              </div>
            )}

            {/* Objetivos */}
            {Array.isArray(c.next_objectives) && c.next_objectives.length > 0 && (
              <Section icon={Target} title="Tus objetivos" accent={accent} items={c.next_objectives} />
            )}

            {c.closing_message && <p className="text-sm font-medium italic" style={{ color: accent }}>{c.closing_message}</p>}
          </div>
        );
      })}
    </div>
  );
}

function Head({ icon: Icon, title, accent }: { icon: typeof Target; title: string; accent: string }) {
  return (
    <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide opacity-60">
      <Icon size={13} style={{ color: accent }} /> {title}
    </p>
  );
}

function Section({ icon, title, accent, items }: { icon: typeof Target; title: string; accent: string; items: string[] }) {
  return (
    <div>
      <Head icon={icon} title={title} accent={accent} />
      <ul className="list-disc space-y-0.5 pl-5 text-sm opacity-90">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}

function WeightChart({ points, goal, accent }: { points: [string, number][]; goal: number | null; accent: string }) {
  const vals = points.map((p) => p[1]);
  const w = 300, h = 90, pad = 10;
  const lo = Math.min(...vals, goal ?? Infinity);
  const hi = Math.max(...vals, goal ?? -Infinity);
  const range = hi - lo || 1;
  const x = (i: number) => pad + (i / (points.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - lo) / range) * (h - 2 * pad);
  const line = points.map((p, i) => `${x(i)},${y(p[1])}`).join(" ");
  const last = points[points.length - 1];
  return (
    <div>
      <Head icon={TrendingDown} title="Evolución de tu peso" accent={accent} />
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 110 }} preserveAspectRatio="none">
        {goal != null && (
          <line x1={pad} y1={y(goal)} x2={w - pad} y2={y(goal)} stroke={accent} strokeWidth="1" strokeDasharray="4 4" opacity="0.4" />
        )}
        <polyline points={line} fill="none" stroke={accent} strokeWidth="2.5" />
        <circle cx={x(points.length - 1)} cy={y(last[1])} r="3.5" fill={accent} />
      </svg>
      <div className="flex justify-between text-xs opacity-50">
        <span>{points[0][0]}: {points[0][1]} kg</span>
        <span>{last[0]}: {last[1]} kg{goal != null ? ` · objetivo ${goal}` : ""}</span>
      </div>
    </div>
  );
}

const cardStyle = {
  background: "var(--portal-card, rgba(255,255,255,0.03))",
  borderColor: "rgba(128,128,128,0.18)",
} as const;
