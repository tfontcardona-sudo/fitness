import { useCallback, useEffect, useState } from "react";
import { Sparkles, AlertTriangle, MessageSquare, MessageCircle, Target, TrendingUp, BarChart3, CheckCircle2, Pencil, Save, X, Copy } from "lucide-react";
import { api } from "../lib/api";
import { feedbackBody, feedbackMessage, openWhatsApp, waPhone } from "../lib/whatsapp";
import { Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

interface Period {
  id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  status: string;
  closing_weight_kg: number | null;
  closing_rating: number | null;
  closing_hardest: string | null;
  closing_questions: string | null;
  closing_waist_cm: number | null;
  closing_hip_cm: number | null;
  closing_arm_cm: number | null;
  closing_thigh_cm: number | null;
  feedback_id: number | null;
}

/**
 * Feedback: cierra el ciclo de la asesoría. Cuando el cliente cierra un período
 * (peso final, perímetros, valoración, dudas), el coach genera aquí el informe
 * de feedback con IA (análisis + recomendaciones) sobre las métricas calculadas
 * por el backend, lo revisa, y lo descarga en Word para enviarlo.
 */
export function ClientFeedbackTab({ client, onClientChanged, onGoPlan }: { client: ClientOut; onClientChanged?: () => void; onGoPlan?: () => void }) {
  const toast = useToast();
  const [periods, setPeriods] = useState<Period[] | null>(null);
  const [contents, setContents] = useState<Record<number, any>>({});
  const [generating, setGenerating] = useState<number | null>(null);
  const [editingFb, setEditingFb] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Record<number, any>>({});
  const [loadingMetrics, setLoadingMetrics] = useState<number | null>(null);

  async function loadMetrics(periodId: number) {
    if (loadingMetrics != null) return;
    setLoadingMetrics(periodId);
    try {
      const m = await api.getPeriodMetrics(periodId);
      setMetrics((prev) => ({ ...prev, [periodId]: m }));
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo cargar el resumen", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setLoadingMetrics(null);
    }
  }

  // Revisión a la que ya está adaptado el último plan (para ocultar el banner
  // "Revisar cambios…" una vez adaptada: el trabajo ya está hecho).
  const [adaptedIdx, setAdaptedIdx] = useState<number | null>(null);

  const load = useCallback(() => {
    api.listPlans(client.id)
      .then((plans) => setAdaptedIdx(plans[0]?.nutrition_json?.applied_adjustments?.period_index ?? null))
      .catch(() => {});
    api.listPeriods(client.id)
      .then(async (ps) => {
        setPeriods(ps);
        // Carga el contenido de los feedbacks ya existentes para mostrarlo.
        const withFb = ps.filter((p) => p.feedback_id);
        const entries = await Promise.all(
          withFb.map((p) =>
            api.getFeedback(p.feedback_id as number)
              .then((f) => [p.feedback_id, { content: f.content, sent_at: f.sent_at }] as const)
              .catch(() => null),
          ),
        );
        const map: Record<number, any> = {};
        entries.forEach((e) => e && (map[e[0] as number] = e[1]));
        setContents(map);
      })
      .catch(() => setPeriods([]));
  }, [client.id]);

  useEffect(load, [load]);

  async function generate(periodId: number) {
    if (generating != null) return;
    setGenerating(periodId);
    try {
      await api.generateFeedback(periodId);
      toast.push("Feedback generado. Revísalo y descárgalo.");
      load();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo generar el feedback", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setGenerating(null);
    }
  }

  function copyAll(content: any) {
    navigator.clipboard.writeText(feedbackBody(content))
      .then(() => toast.push("Feedback copiado al portapapeles"))
      .catch(() => toast.push("No se pudo copiar", "error"));
  }

  /** Un clic: abre WhatsApp del cliente con el feedback ya escrito (entrada,
   *  informe y cierre profesionales) y, la primera vez, lo marca como enviado
   *  (el ciclo avanza a "activo"). Se puede reenviar cuantas veces haga falta. */
  async function sendWhatsApp(feedbackId: number, content: any, alreadySent: boolean) {
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Añade el teléfono del cliente en su ficha para enviarlo por WhatsApp", "error");
      return;
    }
    openWhatsApp(phone, feedbackMessage(client.full_name, content));
    if (alreadySent) {
      toast.push("WhatsApp abierto con el feedback — dale a enviar");
      return;
    }
    try {
      await api.sendFeedback(feedbackId);
      toast.push("WhatsApp abierto con el feedback listo — dale a enviar");
      load();
      onClientChanged?.();
    } catch {
      /* el WhatsApp ya está abierto; el marcado puede reintentarse */
    }
  }

  if (periods === null) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando feedback…
      </div>
    );
  }

  if (periods.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-base font-semibold text-zinc-100">Feedback</h3>
        <p className="mt-1 text-sm text-zinc-400">
          Aún no hay períodos. El feedback se genera cuando el cliente cierra un período
          (publica un plan, crea el período y el cliente registra su diario y lo cierra).
        </p>
      </div>
    );
  }

  const latestReview = periods
    .filter((p) => p.status === "analyzed")
    .reduce<Period | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
  // El banner desaparece en cuanto la planificación YA está adaptada a esa revisión
  const needsAdapt = latestReview != null && adaptedIdx !== latestReview.period_index;

  return (
    <div className="space-y-4">
      {latestReview && needsAdapt && (
        <div
          className="card flex flex-wrap items-center justify-between gap-2 p-3.5"
          style={{ borderColor: "var(--brand-accent)", borderWidth: 1 }}
        >
          <span className="flex items-center gap-2 text-sm text-zinc-200">
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white"
              style={{ background: "var(--brand-accent)" }}
            >
              !
            </span>
            Revisión quincenal #{latestReview.period_index} lista — {latestReview.ends_on}
          </span>
          {/* Lleva a Planificación: allí se ven los cambios propuestos y su
              porqué ANTES de adaptar (ya no se adapta a ciegas desde aquí). */}
          <button onClick={() => onGoPlan?.()} className="btn btn-primary">
            <Sparkles size={14} /> Revisar cambios y adaptar la planificación
          </button>
        </div>
      )}
      {periods.map((p) => {
        const fb = p.feedback_id ? contents[p.feedback_id] : null;
        const content = fb?.content;
        const sent: string | null = fb?.sent_at ?? null;
        const canGenerate = p.status !== "open"; // cerrado o analizado
        const daysElapsed = Math.floor((Date.now() - new Date(p.starts_on + "T00:00:00").getTime()) / 86400000) + 1;
        const ready = p.status !== "open" || daysElapsed >= 14; // resumen disponible a las 2 semanas
        const m = metrics[p.id];
        return (
          <div key={p.id} className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-zinc-100">Período {p.period_index}</h3>
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={badge(p.status)}>
                    {STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  {sent && (
                    <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" }}>
                      <CheckCircle2 size={12} /> Feedback enviado
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-zinc-500">{p.starts_on} → {p.ends_on}</p>
              </div>
              <div className="flex gap-2">
                {ready && (
                  <button onClick={() => loadMetrics(p.id)} disabled={loadingMetrics === p.id} className="btn btn-ghost">
                    <BarChart3 size={15} /> {loadingMetrics === p.id ? "Calculando…" : "Resumen"}
                  </button>
                )}
                {p.feedback_id && content && !sent && (
                  <button onClick={() => sendWhatsApp(p.feedback_id as number, content, false)} className="btn btn-primary">
                    <MessageCircle size={15} /> Enviar por WhatsApp
                  </button>
                )}
                {canGenerate && !p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary">
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : "Generar feedback"}
                  </button>
                )}
              </div>
            </div>

            {p.status === "open" && (
              <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5 text-xs" style={{ background: "rgba(154,107,21,0.09)", color: "#9A6B15" }}>
                <AlertTriangle size={14} /> El período aún está abierto: el cliente debe cerrarlo antes de generar el feedback.
              </div>
            )}

            {/* Datos del cierre */}
            {p.status !== "open" && (
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {p.closing_weight_kg != null && <Stat label="Peso final" value={`${p.closing_weight_kg} kg`} />}
                {p.closing_rating != null && <Stat label="Valoración" value={`${p.closing_rating}/5`} />}
                {p.closing_waist_cm != null && <Stat label="Cintura" value={`${p.closing_waist_cm} cm`} />}
                {p.closing_hip_cm != null && <Stat label="Cadera" value={`${p.closing_hip_cm} cm`} />}
                {p.closing_arm_cm != null && <Stat label="Brazo" value={`${p.closing_arm_cm} cm`} />}
                {p.closing_thigh_cm != null && <Stat label="Muslo" value={`${p.closing_thigh_cm} cm`} />}
              </div>
            )}
            {p.closing_hardest && <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Lo más difícil:</b> {p.closing_hardest}</p>}
            {p.closing_questions && <p className="mt-1 text-xs text-zinc-400"><b className="text-zinc-300">Dudas:</b> {p.closing_questions}</p>}

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo — colapsable */}
            {m && (
              <details open className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <summary className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  <BarChart3 size={13} /> Resumen de las 2 semanas
                </summary>
                {/* Antes → después de los datos en 15 días (peso día 1 → día 15) */}
                <div className="mt-3">
                  <SubTitle icon={TrendingUp} text="Antes → después (15 días)" />
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <BAStat label="Peso (kg)" before={m.weight?.start_kg} after={m.weight?.end_kg} lowerBetter />
                    {p.closing_waist_cm != null && <BAStat label="Cintura (cm)" before={null} after={p.closing_waist_cm} lowerBetter />}
                    {p.closing_hip_cm != null && <BAStat label="Cadera (cm)" before={null} after={p.closing_hip_cm} lowerBetter />}
                    {p.closing_arm_cm != null && <BAStat label="Brazo (cm)" before={null} after={p.closing_arm_cm} />}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <Stat label="Δ peso corporal" value={fmtDelta(m.weight?.delta_kg, "kg")} />
                  <Stat label="Peso actual" value={m.body_weight_now_kg != null ? `${m.body_weight_now_kg} kg` : "—"} />
                  <Stat label="A su objetivo" value={m.distance_to_goal_kg != null ? `${Math.abs(m.distance_to_goal_kg)} kg` : "—"} />
                  <Stat label="Adherencia dieta" value={`${m.adherence?.diet_pct ?? 0}%`} />
                  <Stat label="Días registrados" value={`${m.adherence?.days_logged ?? 0}/${m.adherence?.period_days ?? 0}`} />
                  <Stat label="Ritmo semanal" value={fmtDelta(m.weight?.weekly_rate_kg, "kg/sem")} />
                </div>
                {Array.isArray(m.strength) && m.strength.length > 0 && (
                  <div>
                    <SubTitle icon={TrendingUp} text="Fuerza ganada (e1RM)" />
                    <ul className="space-y-1 text-sm">
                      {m.strength.map((s: any, i: number) => (
                        <li key={i} className="flex items-center justify-between rounded-lg px-3 py-1.5" style={{ background: "var(--surface-raised)" }}>
                          <span className="truncate text-zinc-300">{s.name}</span>
                          <span className="whitespace-nowrap text-zinc-400">
                            {Math.round(s.e1rm_kg)} kg
                            {s.delta_kg != null && (
                              <span style={{ color: s.delta_kg >= 0 ? "var(--brand-accent)" : "#C2453A" }}>
                                {" "}{s.delta_kg >= 0 ? "▲" : "▼"} {Math.abs(s.delta_kg)}
                              </span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(!m.strength || m.strength.length === 0) && (
                  <p className="mt-2 text-xs text-zinc-500">Sin series registradas aún para calcular la fuerza.</p>
                )}
              </details>
            )}

            {/* Feedback: edición o vista */}
            {content && editingFb === p.feedback_id && (
              <FeedbackEditor
                docId={p.feedback_id as number}
                content={content}
                onCancel={() => setEditingFb(null)}
                onSaved={() => { setEditingFb(null); load(); }}
              />
            )}
            {content && editingFb !== p.feedback_id && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <div className="flex items-center justify-between">
                  <SubTitle icon={TrendingUp} text="Feedback" />
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => sendWhatsApp(p.feedback_id as number, content, !!sent)}
                      className="flex items-center gap-1 text-xs font-medium hover:opacity-80"
                      style={{ color: "var(--brand-accent)" }}
                    >
                      <MessageCircle size={13} /> Enviar por WhatsApp
                    </button>
                    <button onClick={() => copyAll(content)} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                      <Copy size={13} /> Copiar todo
                    </button>
                    <button onClick={() => setEditingFb(p.feedback_id as number)} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                      <Pencil size={13} /> Editar texto
                    </button>
                  </div>
                </div>
                {content.natural_analysis && (
                  <div>
                    <p className="text-sm text-zinc-300">{content.natural_analysis}</p>
                  </div>
                )}
                {Array.isArray(content.changes_bullets) && content.changes_bullets.length > 0 && (
                  <div>
                    <SubTitle icon={Sparkles} text="Cambios en el plan" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                    </ul>
                  </div>
                )}
                {content.answers && (
                  <div>
                    <SubTitle icon={MessageSquare} text="Respuesta a sus dudas" />
                    <p className="text-sm text-zinc-300">{content.answers}</p>
                  </div>
                )}
                {Array.isArray(content.next_objectives) && content.next_objectives.length > 0 && (
                  <div>
                    <SubTitle icon={Target} text="Objetivos próximas 2 semanas" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.next_objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>
                )}
                {content.closing_message && <p className="text-sm italic text-zinc-400">{content.closing_message}</p>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };
function badge(status: string): React.CSSProperties {
  if (status === "analyzed") return { background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" };
  if (status === "closed") return { background: "rgba(154,107,21,0.14)", color: "#9A6B15" };
  return { background: "rgba(38,33,26,0.08)", color: "#7A7060" };
}

function fmtDelta(v: number | null | undefined, unit: string): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v} ${unit}`;
}

/** Antes → después para el resumen de feedback (día 1 → día 15). */
function BAStat({ label, before, after, lowerBetter }: {
  label: string; before: number | null | undefined; after: number | null | undefined; lowerBetter?: boolean;
}) {
  const b = before ?? null, a = after ?? null;
  const delta = b != null && a != null ? Math.round((a - b) * 10) / 10 : null;
  const good = delta != null && (lowerBetter ? delta < 0 : delta > 0);
  const bad = delta != null && delta !== 0 && !good;
  return (
    <div className="rounded-lg p-2.5" style={{ background: "var(--surface-raised)" }}>
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-sm text-zinc-100">
        <span className="text-zinc-400">{b ?? "—"}</span>
        <span className="text-zinc-600">→</span>
        <span className="font-semibold">{a ?? "—"}</span>
        {delta != null && delta !== 0 && (
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#C2453A" : "#7A7060" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

function FeedbackEditor({ docId, content, onCancel, onSaved }: {
  docId: number; content: any; onCancel: () => void; onSaved: () => void;
}) {
  const toast = useToast();
  const [d, setD] = useState<Record<string, string>>({
    natural_analysis: content?.natural_analysis ?? "",
    changes_bullets: (content?.changes_bullets ?? []).join("\n"),
    answers: content?.answers ?? "",
    next_objectives: (content?.next_objectives ?? []).join("\n"),
    closing_message: content?.closing_message ?? "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setD((p) => ({ ...p, [k]: v }));

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      await api.editFeedback(docId, {
        natural_analysis: d.natural_analysis,
        changes_bullets: d.changes_bullets.split("\n").map((s) => s.trim()).filter(Boolean),
        answers: d.answers.trim() || null,
        next_objectives: d.next_objectives.split("\n").map((s) => s.trim()).filter(Boolean),
        closing_message: d.closing_message,
      });
      toast.push("Feedback actualizado");
      onSaved();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
      <div className="flex items-center justify-between">
        <SubTitle icon={Pencil} text="Editar feedback" />
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn btn-ghost"><X size={14} /> Cancelar</button>
          <button onClick={save} disabled={saving} className="btn btn-primary"><Save size={14} /> {saving ? "Guardando…" : "Guardar"}</button>
        </div>
      </div>
      <FbArea label="Análisis" value={d.natural_analysis} onChange={(v) => set("natural_analysis", v)} rows={4} />
      <FbArea label="Cambios en el plan (uno por línea)" value={d.changes_bullets} onChange={(v) => set("changes_bullets", v)} />
      <FbArea label="Respuesta a sus dudas" value={d.answers} onChange={(v) => set("answers", v)} />
      <FbArea label="Objetivos próximas 2 semanas (uno por línea)" value={d.next_objectives} onChange={(v) => set("next_objectives", v)} />
      <FbArea label="Mensaje de cierre" value={d.closing_message} onChange={(v) => set("closing_message", v)} rows={2} />
    </div>
  );
}

function FbArea({ label, value, onChange, rows = 3 }: { label: string; value: string; onChange: (v: string) => void; rows?: number }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-zinc-500">{label}</span>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} className="input w-full resize-y" />
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-2.5 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-sm font-bold text-zinc-100">{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function SubTitle({ icon: Icon, text }: { icon: typeof Target; text: string }) {
  return (
    <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
      <Icon size={13} /> {text}
    </div>
  );
}
