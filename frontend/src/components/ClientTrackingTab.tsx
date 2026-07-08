import { useEffect, useRef, useState } from "react";
import { api, REFRESH_MS } from "../lib/api";
import type { ClientOut } from "../types";

type Tracking = Awaited<ReturnType<typeof api.getClientTracking>>;

/**
 * Seguimiento del cliente EN TIEMPO REAL para el coach. Hace polling cada 3 s:
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
    timer.current = window.setInterval(load, REFRESH_MS); // polling → tiempo real
    return () => {
      alive = false;
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [client.id]);

  if (err) return <div className="card p-5 text-sm text-red-400">No se pudo cargar el seguimiento: {err}</div>;
  if (!data) return <div className="card p-5 text-sm opacity-60">Cargando seguimiento…</div>;
  if (!data.has_period)
    return (
      <div className="card p-5 text-sm opacity-60">
        El cliente aún no tiene un período activo. Se abre solo al activarse la
        planificación, al enviar el feedback o cuando el cliente entra en su portal.
      </div>
    );

  const p = data.period!;
  const daily = data.daily ?? [];
  const avg = data.daily_averages;
  const quincenals = data.quincenals ?? [];
  const pct = p.days_total ? Math.min(100, Math.round((p.days_elapsed / p.days_total) * 100)) : 0;

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
                    <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ background: "color-mix(in srgb, var(--brand-accent-2, #2E5E8C) 25%, transparent)", color: "#3D6E9E" }}>
                      {q.feelings_score_10}/10
                    </span>
                  )}
                  <span className="text-xs text-emerald-400">{q.analyzed ? "analizada" : "recibida"}</span>
                </span>
              </summary>
              <div className="space-y-4 border-t border-white/5 px-4 py-3.5">
                {/* Análisis automático: lo crítico, arriba y sin que el coach lo busque */}
                <Vigilar
                  q={q}
                  goal={client.goal_type}
                  extras={i === 0 ? {
                    daysLogged: data.days_logged ?? null,
                    daysTotal: data.period?.days_total ?? 14,
                    sleep: avg?.sleep_hours ?? null,
                    satiety: avg?.satiety_1_10 ?? null,
                  } : undefined}
                />

                <section>
                  <MiniTitle>Medidas · antes → después</MiniTitle>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {/* Bajar peso solo es "bueno" si el objetivo lo pide */}
                    <BeforeAfter label="Peso (kg)" before={q.weight_before} after={q.weight_after} lowerBetter={client.goal_type !== "muscle_gain"} />
                    <BeforeAfter label="Cintura (cm)" before={q.waist_before} after={q.waist_after} lowerBetter />
                    <BeforeAfter label="Cadera (cm)" before={q.hip_before} after={q.hip_after} lowerBetter />
                    <BeforeAfter label="Brazo (cm)" before={q.arm_before} after={q.arm_after} />
                    <BeforeAfter label="Muslo (cm)" before={q.thigh_before} after={q.thigh_after} />
                  </div>
                </section>

                <section>
                  <MiniTitle>Adherencia y valoración</MiniTitle>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <ScoreStat label="Dieta" value={q.adherence_diet} />
                    <ScoreStat label="Entreno" value={q.adherence_training} />
                    <ScoreStat label="Sensaciones" value={q.feelings_score_10} />
                    <CountStat label="Comidas libres" value={q.free_meals} />
                  </div>
                </section>

                {q.feelings && (
                  <section>
                    <MiniTitle>Sensaciones (1 = muy mal · 5 = excelente)</MiniTitle>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(q.feelings).map(([k, v]) => (
                        <FeelingChip key={k} name={k} value={Number(v)} />
                      ))}
                    </div>
                  </section>
                )}

                {(q.changes || q.hardest || q.next_goal || q.questions) && (
                  <section>
                    <MiniTitle>En palabras del cliente</MiniTitle>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <TextCard label="Cambios que nota" text={q.changes} />
                      <TextCard label="Lo que más le cuesta" text={q.hardest} />
                      <TextCard label="Su objetivo" text={q.next_goal} />
                      <TextCard label="Dudas para ti" text={q.questions} highlight />
                    </div>
                  </section>
                )}
              </div>
            </details>
          ))
        )}
      </div>
    </div>
  );
}

/* ---------- Análisis automático de la revisión quincenal ------------------
   Reglas deterministas sobre los datos que ya tenemos: lo crítico sale solo,
   sin que el coach tenga que rebuscar. */

type Aviso = { sev: "alto" | "medio"; text: string };
const SEV_COLOR: Record<Aviso["sev"], string> = { alto: "#C2453A", medio: "#9A6B15" };
// Claves REALES que envía el portal (PortalClose.FEELINGS) + variantes de
// datos antiguos/semilla: todas con etiqueta bonita.
const FEELING_LABEL: Record<string, string> = {
  energia: "Energía", hambre: "Hambre", sueno: "Sueño",
  recuperacion: "Recuperación", animo: "Ánimo", digestiones: "Digestiones",
  estres: "Estrés", motivacion: "Motivación", digestion: "Digestión",
};

function avisosQuincenal(
  q: any,
  goal: string | null | undefined,
  extras?: { daysLogged: number | null; daysTotal: number; sleep: number | null; satiety: number | null },
): Aviso[] {
  const out: Aviso[] = [];

  // Ritmo de cambio de peso (kg/semana sobre las 2 semanas del período)
  if (q.weight_before != null && q.weight_after != null && q.weight_after > 0) {
    const perWeek = (q.weight_after - q.weight_before) / 2;
    const pct = (Math.abs(perWeek) / q.weight_after) * 100;
    const v = `${perWeek > 0 ? "+" : ""}${perWeek.toFixed(2)} kg/sem`;
    if (goal === "muscle_gain") {
      if (perWeek <= 0) out.push({ sev: "medio", text: `No sube de peso (${v}): revisa kcal si el objetivo es ganar músculo.` });
      else if (pct > 0.5) out.push({ sev: "medio", text: `Sube demasiado rápido (${v}): riesgo de acumular grasa.` });
    } else if (goal === "recomp" || goal === "maintenance" || goal === "injury_recovery") {
      // Objetivos de peso ESTABLE: recomposición, mantenimiento y lesión
      if (pct > 0.5) {
        const motivo = goal === "recomp" ? "recomponer con el peso estable"
          : goal === "maintenance" ? "mantener el peso"
          : "recuperarse sin perder masa";
        out.push({ sev: "medio", text: `El peso se mueve rápido (${v}) y el objetivo es ${motivo}: revisa kcal.` });
      }
    } else {
      if (perWeek >= 0) out.push({ sev: "alto", text: `Sin pérdida de peso en el período (${v}): revisa kcal y adherencia real.` });
      else if (pct > 1) out.push({ sev: "alto", text: `Ritmo de pérdida muy rápido (${v}, >1% del peso): protege masa muscular y energía.` });
      else if (pct < 0.25) out.push({ sev: "medio", text: `Ritmo de pérdida lento (${v}): valora ajustar el déficit o los pasos.` });
    }
  }

  if (q.adherence_diet != null && q.adherence_diet < 6) out.push({ sev: "alto", text: `Adherencia a la dieta baja (${q.adherence_diet}/10): simplifica antes de apretar.` });
  else if (q.adherence_diet != null && q.adherence_diet < 8) out.push({ sev: "medio", text: `Adherencia a la dieta mejorable (${q.adherence_diet}/10).` });
  if (q.adherence_training != null && q.adherence_training < 6) out.push({ sev: "alto", text: `Adherencia al entreno baja (${q.adherence_training}/10): revisa la rutina o su agenda.` });
  else if (q.adherence_training != null && q.adherence_training < 8) out.push({ sev: "medio", text: `Adherencia al entreno mejorable (${q.adherence_training}/10).` });
  if (q.free_meals != null && q.free_meals >= 4) out.push({ sev: "medio", text: `${q.free_meals} comidas libres/saltadas en 2 semanas: puede frenar el progreso.` });

  for (const [k, v] of Object.entries(q.feelings ?? {})) {
    if (typeof v === "number" && v <= 2) {
      out.push({ sev: "alto", text: `${FEELING_LABEL[k] ?? k} en zona roja (${v}/5): trátalo en el feedback.` });
    }
  }

  if (extras) {
    if (extras.daysLogged != null && extras.daysTotal - extras.daysLogged > 3)
      out.push({ sev: "medio", text: `Solo ${extras.daysLogged}/${extras.daysTotal} días registrados: los datos pueden quedarse cortos.` });
    if (extras.sleep != null && extras.sleep < 6.5)
      out.push({ sev: "medio", text: `Media de sueño baja (${extras.sleep} h): afecta a recuperación y hambre.` });
    if (extras.satiety != null && extras.satiety < 5)
      out.push({ sev: "medio", text: `Saciedad media baja (${extras.satiety}/10): sube volumen de comida o proteína.` });
  }

  if (q.questions) out.push({ sev: "medio", text: "Tiene una duda pendiente: respóndela en el feedback." });
  return out;
}

function Vigilar({ q, goal, extras }: {
  q: any; goal: string | null | undefined;
  extras?: { daysLogged: number | null; daysTotal: number; sleep: number | null; satiety: number | null };
}) {
  const items = avisosQuincenal(q, goal, extras);
  const ok = items.length === 0;
  return (
    <div
      className="rounded-xl border p-3"
      style={ok
        ? { borderColor: "rgba(27,127,77,0.35)", background: "rgba(27,127,77,0.05)" }
        : { borderColor: "rgba(194,69,58,0.35)", background: "rgba(194,69,58,0.04)" }}
    >
      <p className="mb-1.5 text-[11px] font-bold uppercase tracking-wide" style={{ color: ok ? "#1B7F4D" : "#C2453A" }}>
        {ok ? "Período sólido" : "Puntos a vigilar"}
      </p>
      {ok ? (
        <p className="text-xs text-zinc-400">Sin señales de alarma: ritmo, adherencia y sensaciones en orden.</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-xs leading-relaxed text-zinc-300">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: SEV_COLOR[a.sev] }} />
              <span>{a.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MiniTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
      {/* Barrita azul de marca: guía visual de estructura */}
      <span aria-hidden className="h-3 w-1 rounded-full" style={{ background: "var(--brand-accent-2)" }} />
      {children}
    </p>
  );
}

function scoreTone(v: number | null | undefined, of = 10): string {
  if (v == null) return "#7A7060";
  const pct = v / of;
  return pct >= 0.8 ? "#1B7F4D" : pct >= 0.6 ? "#9A6B15" : "#C2453A";
}

function ScoreStat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg p-2.5 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-base font-bold" style={{ color: scoreTone(value) }}>
        {value ?? "—"}<span className="text-xs font-medium text-zinc-500">/10</span>
      </div>
      <div className="text-[11px] text-zinc-500">{label}</div>
    </div>
  );
}

function CountStat({ label, value }: { label: string; value: number | null }) {
  const tone = value == null ? "#7A7060" : value <= 2 ? "#1B7F4D" : value <= 3 ? "#9A6B15" : "#C2453A";
  return (
    <div className="rounded-lg p-2.5 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-base font-bold" style={{ color: tone }}>{value ?? "—"}</div>
      <div className="text-[11px] text-zinc-500">{label}</div>
    </div>
  );
}

function FeelingChip({ name, value }: { name: string; value: number }) {
  const tone = value >= 4 ? "#1B7F4D" : value === 3 ? "#9A6B15" : "#C2453A";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
      style={{ borderColor: `${tone}55`, color: "#3D362B" }}
    >
      {FEELING_LABEL[name] ?? name}
      <b style={{ color: tone }}>{value}/5</b>
    </span>
  );
}

function TextCard({ label, text, highlight }: { label: string; text: string | null; highlight?: boolean }) {
  if (!text) return null;
  return (
    <div
      className="rounded-lg border p-2.5"
      style={highlight
        ? { borderColor: "rgba(154,107,21,0.4)", background: "rgba(154,107,21,0.06)" }
        : { borderColor: "var(--line)", background: "var(--surface-raised)" }}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: highlight ? "#9A6B15" : "#7A7060" }}>
        {label}
      </p>
      <p className="mt-1 text-sm leading-relaxed text-zinc-200">{text}</p>
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
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#C2453A" : "#7A7060" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}
