import { useCallback, useEffect, useState } from "react";
import { Sparkles, MessageSquare, Mail, Download, Target, TrendingUp, BarChart3, CheckCircle2, Pencil, Save, X, Copy } from "lucide-react";
import { api, getToken } from "../lib/api";
import { feedbackBody } from "../lib/feedbackText";
import { pkg } from "../lib/packages";
import { ExpandableArea, Spinner, useToast } from "./ui";
import type { ClientOut } from "../types";

interface Period {
  id: number;
  period_index: number;
  starts_on: string;
  ends_on: string;
  status: string;
  closing_weight_kg: number | null;
  measured_at: string | null;
  closing_waist_cm: number | null;
  closing_hip_cm: number | null;
  closing_arm_cm: number | null;
  closing_thigh_cm: number | null;
  feedback_id: number | null;
  feedback_sent?: boolean;
  /** Seguimiento continuo: días registrados y los que había al generar el informe */
  days_logged?: number;
  logs_at_feedback?: number | null;
}

/** Días registrados NUEVOS desde que se generó el informe (seguimiento continuo). */
function nuevosDesdeInforme(p: Period): number {
  if (p.logs_at_feedback == null) return 0;
  return Math.max(0, (p.days_logged ?? 0) - p.logs_at_feedback);
}

/**
 * Feedback — el informe del cliente.
 *
 * El seguimiento es CONTINUO: el informe se pone al día con lo que el cliente
 * lleva registrado, en cualquier momento, y el coach lo envía cuando lo ve
 * listo. El análisis lo redacta la IA sobre las métricas que calcula el backend
 * (la IA nunca calcula).
 */
export function ClientFeedbackTab({ client, onClientChanged }: { client: ClientOut; onClientChanged?: () => void }) {
  const toast = useToast();
  const [periods, setPeriods] = useState<Period[] | null>(null);
  const [contents, setContents] = useState<Record<number, any>>({});
  const [generating, setGenerating] = useState<number | null>(null);
  const [editingFb, setEditingFb] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Record<number, any>>({});
  const [loadingMetrics, setLoadingMetrics] = useState<number | null>(null);
  // Paquete del cliente: decide qué bloques del informe tienen sentido
  // (la fuerza solo si entrena). La entrega es SIEMPRE por email.
  const info = pkg(client.package_tier);

  /** Carga el resumen de métricas de un período (se muestra SIEMPRE, sin botón:
   *  al cargar la pestaña para el período actual y al desplegar los antiguos). */
  async function loadMetrics(periodId: number) {
    setLoadingMetrics((prev) => prev ?? periodId);
    try {
      const m = await api.getPeriodMetrics(periodId);
      setMetrics((prev) => ({ ...prev, [periodId]: m }));
    } catch {
      /* sin resumen: el período se muestra igualmente con sus datos de cierre */
    } finally {
      setLoadingMetrics((prev) => (prev === periodId ? null : prev));
    }
  }

  const load = useCallback(() => {
    api.listPeriods(client.id)
      .then(async (ps) => {
        setPeriods(ps);
        // El resumen del período ACTUAL se carga solo (los antiguos, al desplegarlos)
        const latest = ps.reduce<Period | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
        if (latest) loadMetrics(latest.id);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client.id]);

  useEffect(load, [load]);

  async function generate(periodId: number) {
    if (generating != null) return;
    setGenerating(periodId);
    try {
      await api.generateFeedback(periodId);
      toast.push("Feedback generado. Revísalo y envíalo por email.");
      load();
      onClientChanged?.(); // el aviso "Ir a Feedback" del perfil desaparece
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo generar el feedback", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setGenerating(null);
    }
  }

  /** Seguimiento continuo sin período aún: lo abre y genera el informe. */
  async function refreshInforme() {
    if (generating != null) return;
    setGenerating(-1);
    try {
      await api.refreshClientFeedback(client.id);
      toast.push("Informe generado. Revísalo y envíaselo cuando lo veas listo.");
      load();
      onClientChanged?.();
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo generar el informe", "error");
    } finally {
      setGenerating(null);
    }
  }

  /** Descarga el informe en Word. El endpoint exige JWT, así que no vale un
   *  <a href>: se pide con fetch y se guarda el blob. */
  function downloadWord(feedbackId: number) {
    fetch(api.feedbackDocumentUrl(feedbackId), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        // Sin esto, un 401/500 guardaba un archivo corrupto con el JSON del error.
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `informe_${client.full_name.replace(/\s+/g, "_").toLowerCase()}.docx`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar el informe", "error"));
  }

  function copyAll(content: any) {
    navigator.clipboard.writeText(feedbackBody(content))
      .then(() => toast.push("Feedback copiado al portapapeles"))
      .catch(() => toast.push("No se pudo copiar", "error"));
  }

  /** Entrega el informe al cliente POR EMAIL (única vía en los tres servicios).
   *  La primera vez marca el feedback como enviado (el ciclo avanza a "activo");
   *  se puede reenviar cuantas veces haga falta. */
  async function deliverFeedback(feedbackId: number, alreadySent: boolean) {
    try {
      const r = await api.sendFeedbackEmail(feedbackId);
      // El backend marca "enviado" y avanza el ciclo ANTES del email: si el
      // email falló, decir "enviado" sin más dejaba al cliente sin informe
      // y a nadie enterado (auditoría del ciclo).
      if (r.email_status === "sent") {
        toast.push(alreadySent ? "Feedback reenviado por email" : "Feedback enviado por email al cliente");
      } else {
        toast.push(
          r.email_status === "disabled"
            ? "El ciclo ha avanzado pero los EMAILS ESTÁN DESACTIVADOS: revisa la configuración de correo"
            : "El ciclo ha avanzado pero el EMAIL FALLÓ: vuelve a intentar el envío",
          "error",
        );
      }
      load();
      onClientChanged?.();
    } catch {
      toast.push("No se pudo enviar el email", "error");
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
          Aún no hay seguimiento. Al publicar su planificación se abre solo: el
          cliente registra su día a día en el portal y aquí tendrás su informe,
          que pones al día cuando quieras y le envías cuando lo veas listo.
        </p>
        <button className="btn btn-ghost mt-3" disabled={generating != null}
          onClick={refreshInforme}
          title="Abre el seguimiento y analiza lo que el cliente lleve registrado">
          <Sparkles size={15} /> {generating != null ? "Generando…" : "Generar informe ahora"}
        </button>
      </div>
    );
  }

  const maxIdx = periods.reduce((mx, p) => Math.max(mx, p.period_index), 0);

  return (
    <div className="space-y-4">
      {[...periods].sort((a, b) => b.period_index - a.period_index).map((p) => {
        const fb = p.feedback_id ? contents[p.feedback_id] : null;
        const content = fb?.content;
        const sent: string | null = fb?.sent_at ?? null;
        // Basta con que el cliente lleve datos suficientes (el backend exige
        // un mínimo de 5 días registrados).
        const registrados = p.days_logged ?? 0;
        const canGenerate = registrados >= 5;
        const nuevos = nuevosDesdeInforme(p);
        // El resumen sale en cuanto hay datos que resumir.
        const ready = p.status !== "open" || registrados >= 1;
        const m = metrics[p.id];
        const isCurrent = p.period_index === maxIdx;
        return (
          // Solo el período ACTUAL está desplegado; los anteriores quedan
          // plegados y cargan su resumen al abrirlos.
          <details
            key={p.id}
            name="feedback-periodos"
            className="card p-5"
            open={isCurrent}
            onToggle={(e) => {
              if ((e.currentTarget as HTMLDetailsElement).open && ready && !metrics[p.id]) loadMetrics(p.id);
            }}
          >
            <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold text-zinc-100">
                    Seguimiento
                  </h3>
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={badge(p.status)}>
                    {STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  {sent && (
                    <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" }}>
                      <CheckCircle2 size={12} /> Feedback enviado
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-zinc-500">
                  desde el {p.starts_on}
                </p>
              </div>
              <div className="flex gap-2" onClick={(e) => e.preventDefault()}>
                {p.feedback_id && content && !sent && (
                  <button onClick={() => deliverFeedback(p.feedback_id as number, false)} className="btn btn-primary">
                    <Mail size={15} /> Enviar por email
                  </button>
                )}
                {canGenerate && !p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary">
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : "Generar informe"}
                  </button>
                )}
                {/* El informe se pone al día con lo que el cliente haya
                    registrado desde la última vez. Si el anterior ya se envió,
                    sale un borrador NUEVO (no se toca el que recibió). */}
                {canGenerate && p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id}
                    className={nuevos >= 5 ? "btn btn-primary" : "btn btn-ghost"}
                    title="Vuelve a analizar todo lo que el cliente lleva registrado">
                    <Sparkles size={15} />
                    {generating === p.id ? "Actualizando…"
                      : nuevos > 0 ? `Poner al día (${nuevos} días nuevos)` : "Poner al día"}
                  </button>
                )}
              </div>
            </summary>

            {p.status === "open" && (
              <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5 text-xs"
                style={{ background: "color-mix(in srgb, var(--brand-accent) 10%, transparent)", color: "var(--text-dim)" }}>
                <TrendingUp size={14} />
                {registrados === 0
                  ? "El cliente aún no ha registrado nada en su portal."
                  : canGenerate
                    ? `${registrados} días registrados. El informe se pone al día cuando quieras y se envía cuando lo veas listo.`
                    : `${registrados} días registrados: con 5 ya se puede generar un informe fiable.`}
              </div>
            )}

            {/* Últimas medidas que el CLIENTE apuntó desde "Evolución" (van
                sobre el período abierto: aquí no se cierra nada). */}
            {(p.closing_weight_kg != null || p.closing_waist_cm != null
              || p.closing_hip_cm != null || p.closing_arm_cm != null
              || p.closing_thigh_cm != null) && (
              <div className="mt-3">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  Sus últimas medidas
                  {p.measured_at && (
                    <span className="ml-2 font-normal normal-case tracking-normal text-zinc-600">
                      actualizadas el {new Date(p.measured_at).toLocaleDateString("es-ES")}
                    </span>
                  )}
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {p.closing_weight_kg != null && <Stat label="Peso" value={`${p.closing_weight_kg} kg`} />}
                  {p.closing_waist_cm != null && <Stat label="Cintura" value={`${p.closing_waist_cm} cm`} />}
                  {p.closing_hip_cm != null && <Stat label="Cadera" value={`${p.closing_hip_cm} cm`} />}
                  {p.closing_arm_cm != null && <Stat label="Brazo" value={`${p.closing_arm_cm} cm`} />}
                  {p.closing_thigh_cm != null && <Stat label="Muslo" value={`${p.closing_thigh_cm} cm`} />}
                </div>
              </div>
            )}

            {/* Fotos de progreso: el coach las VE aquí al generar el informe. */}
            <PeriodPhotos clientId={client.id} periodId={p.id} />

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo.
                Se muestra SIEMPRE, ya cargado — sin botones que pulsar. */}
            {!m && loadingMetrics === p.id && (
              <p className="mt-4 flex items-center gap-2 border-t pt-4 text-xs text-zinc-500" style={{ borderColor: "var(--line)" }}>
                <Spinner /> Calculando el resumen…
              </p>
            )}
            {m && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  <BarChart3 size={13} /> Resumen del seguimiento
                </div>
                {/* Antes → ahora: peso del primer registro contra el último */}
                <div className="mt-3">
                  <SubTitle icon={TrendingUp}
                    text={`Antes → ahora (${registrados} días registrados)`} />
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {/* Bajar peso solo es "bueno" si el objetivo lo pide */}
                    <BAStat label="Peso (kg)" before={m.weight?.start_kg} after={m.weight?.end_kg} lowerBetter={client.goal_type !== "muscle_gain"} />
                    {p.closing_waist_cm != null && <BAStat label="Cintura (cm)" before={null} after={p.closing_waist_cm} lowerBetter />}
                    {p.closing_hip_cm != null && <BAStat label="Cadera (cm)" before={null} after={p.closing_hip_cm} lowerBetter />}
                    {p.closing_arm_cm != null && <BAStat label="Brazo (cm)" before={null} after={p.closing_arm_cm} />}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <Stat label="Δ peso corporal" value={fmtDelta(m.weight?.delta_kg, "kg")} />
                  <Stat label="Peso actual" value={m.body_weight_now_kg != null ? `${m.body_weight_now_kg} kg` : "—"} />
                  <Stat label="A su objetivo" value={m.distance_to_goal_kg != null ? `${Math.abs(m.distance_to_goal_kg)} kg` : "—"} />
                  <Stat
                    label="Adherencia dieta"
                    value={`${m.adherence?.diet_pct ?? 0}% · ${(m.adherence?.diet_days_yes ?? 0) + (m.adherence?.diet_days_partial ?? 0)} de ${m.adherence?.period_days ?? 0} días`}
                  />
                  <Stat label="Días registrados" value={`${m.adherence?.days_logged ?? 0}/${m.adherence?.period_days ?? 0}`} />
                  <Stat label="Ritmo semanal" value={fmtDelta(m.weight?.weekly_rate_kg, "kg/sem")} />
                </div>
                {info.hasTraining && Array.isArray(m.strength) && m.strength.length > 0 && (
                  <div>
                    <SubTitle icon={TrendingUp}
                      text="Fuerza por grupo muscular" />
                    <ul className="space-y-1 text-sm">
                      {m.strength.map((s: any, i: number) => (
                        <li key={i} className="rounded-lg px-3 py-2" style={{ background: "var(--surface-raised)" }}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="flex min-w-0 items-center gap-2">
                              {s.muscle && (
                                <span
                                  className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                                  style={{ background: "color-mix(in srgb, var(--brand-accent-2) 15%, transparent)", color: "var(--brand-accent-2)" }}
                                >
                                  {s.muscle}
                                </span>
                              )}
                              <span className="truncate text-zinc-300">{s.name}</span>
                            </span>
                            <span className="whitespace-nowrap text-zinc-400">
                              e1RM {Math.round(s.e1rm_kg)} kg
                              {s.delta_kg != null && (
                                <span style={{ color: s.delta_kg >= 0 ? "var(--brand-accent)" : "#F0716A" }}>
                                  {" "}{s.delta_kg >= 0 ? "▲" : "▼"} {Math.abs(s.delta_kg)} kg
                                  {s.pct != null ? ` (${s.pct >= 0 ? "+" : ""}${s.pct}%)` : ""}
                                </span>
                              )}
                            </span>
                          </div>
                          <div className="mt-0.5 text-xs text-zinc-500">
                            {s.avg_weight_kg != null && (
                              <>
                                Peso medio {s.avg_weight_kg} kg
                                {s.avg_weight_delta_kg != null && (
                                  <span style={{ color: s.avg_weight_delta_kg >= 0 ? "var(--brand-accent)" : "#F0716A" }}>
                                    {" "}({s.avg_weight_delta_kg >= 0 ? "+" : ""}{s.avg_weight_delta_kg} kg)
                                  </span>
                                )}
                              </>
                            )}
                            {s.avg_reps != null && <> · {s.avg_reps} reps de media</>}
                            {s.delta_kg == null && <> · primeros datos de este ejercicio</>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {info.hasTraining && (!m.strength || m.strength.length === 0) && (
                  <p className="mt-2 text-xs text-zinc-500">Sin series registradas aún para calcular la fuerza.</p>
                )}
              </div>
            )}

            {/* Feedback: edición o vista */}
            {content && editingFb === p.feedback_id && (
              <FeedbackEditor
                docId={p.feedback_id as number}
                content={content}
                sentAt={sent}
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
                      onClick={() => deliverFeedback(p.feedback_id as number, !!sent)}
                      className="flex items-center gap-1 text-xs font-medium hover:opacity-80"
                      style={{ color: "var(--brand-accent)" }}
                    >
                      <Mail size={13} /> Enviar por email
                    </button>
                    <button onClick={() => downloadWord(p.feedback_id as number)}
                      className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                      <Download size={13} /> Descargar Word
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
                    <SubTitle icon={Target} text="Próximos objetivos" />
                    <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                      {content.next_objectives.map((o: string, i: number) => <li key={i}>{o}</li>)}
                    </ul>
                  </div>
                )}
                {content.closing_message && <p className="text-sm italic text-zinc-400">{content.closing_message}</p>}
              </div>
            )}
          </details>
        );
      })}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = { open: "Abierto", closed: "Cerrado", analyzed: "Analizado" };

function badge(status: string): React.CSSProperties {
  if (status === "analyzed") return { background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" };
  if (status === "closed") return { background: "rgba(154,107,21,0.14)", color: "#E5B94E" };
  return { background: "rgba(38,33,26,0.08)", color: "#948C7D" };
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
          <span className="text-xs" style={{ color: good ? "var(--brand-accent)" : bad ? "#F0716A" : "#948C7D" }}>
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

function FeedbackEditor({ docId, content, sentAt, onCancel, onSaved }: {
  docId: number; content: any; sentAt?: string | null; onCancel: () => void; onSaved: () => void;
}) {
  const toast = useToast();
  // Ajustes propuestos a la planificación: editables ANTES de "Adaptar" (el
  // backend ya lo soportaba pero la interfaz no lo cableaba — auditoría).
  const initialAdjustments: { area?: string; change?: string; reason?: string }[] =
    Array.isArray(content?.plan_adjustments) ? content.plan_adjustments : [];
  const [d, setD] = useState<Record<string, string>>({
    natural_analysis: content?.natural_analysis ?? "",
    changes_bullets: (content?.changes_bullets ?? []).join("\n"),
    answers: content?.answers ?? "",
    next_objectives: (content?.next_objectives ?? []).join("\n"),
    closing_message: content?.closing_message ?? "",
    plan_adjustments: initialAdjustments
      .map((a) => (a?.change ?? "").toString().trim()).filter(Boolean).join("\n"),
  });
  const [saving, setSaving] = useState(false);
  const set = (k: string, v: string) => setD((p) => ({ ...p, [k]: v }));

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      // Cada línea es el TEXTO del cambio; área y motivo se conservan por
      // posición (las líneas nuevas entran como "general").
      const adjLines = d.plan_adjustments.split("\n").map((s) => s.trim()).filter(Boolean);
      const adjustments = adjLines.map((line, i) => ({
        area: initialAdjustments[i]?.area ?? "general",
        change: line,
        reason: initialAdjustments[i]?.reason ?? "",
      }));
      await api.editFeedback(docId, {
        natural_analysis: d.natural_analysis,
        changes_bullets: d.changes_bullets.split("\n").map((s) => s.trim()).filter(Boolean),
        answers: d.answers.trim() || null,
        next_objectives: d.next_objectives.split("\n").map((s) => s.trim()).filter(Boolean),
        closing_message: d.closing_message,
        ...(adjLines.length || initialAdjustments.length ? { plan_adjustments: adjustments } : {}),
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
      {sentAt && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-600">
          Este feedback YA SE ENVIÓ el {new Date(sentAt).toLocaleDateString("es-ES")}: el cliente
          recibió aquella versión por email. Si lo editas, reenvíaselo para que le llegue la nueva.
        </p>
      )}
      <FbArea label="Análisis" value={d.natural_analysis} onChange={(v) => set("natural_analysis", v)} rows={4} />
      <FbArea label="Cambios en el plan (uno por línea)" value={d.changes_bullets} onChange={(v) => set("changes_bullets", v)} />
      <FbArea label="Respuesta a sus dudas" value={d.answers} onChange={(v) => set("answers", v)} />
      <FbArea label="Próximos objetivos (uno por línea)" value={d.next_objectives} onChange={(v) => set("next_objectives", v)} />
      <FbArea label="Mensaje de cierre" value={d.closing_message} onChange={(v) => set("closing_message", v)} rows={2} />
      <FbArea
        label="Ajustes propuestos a la planificación (uno por línea — se aplican al pulsar «Adaptar»)"
        value={d.plan_adjustments} onChange={(v) => set("plan_adjustments", v)} />
    </div>
  );
}

function FbArea({ label, value, onChange, rows = 3 }: { label: string; value: string; onChange: (v: string) => void; rows?: number }) {
  return <ExpandableArea label={label} value={value} onChange={onChange} rows={rows} />;
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
      {/* Icono en azul de marca: los subtítulos son estructura, no acción */}
      <Icon size={13} style={{ color: "var(--brand-accent-2)" }} /> {text}
    </div>
  );
}

const KIND_LABEL: Record<string, string> = {
  front: "Frente", side: "Perfil", back: "Espalda", detail: "Detalle",
};

/** Fotos de progreso del período (fetch con JWT → blob: las fotos de clientes
 *  NO son públicas). Muestra miniaturas; un toque abre la foto a tamaño real. */
function PeriodPhotos({ clientId, periodId }: { clientId: number; periodId: number }) {
  const [photos, setPhotos] = useState<{ id: number; kind: string; url: string }[] | null>(null);

  useEffect(() => {
    let alive = true;
    const urls: string[] = [];
    api.listClientPhotos(clientId)
      .then(async (all) => {
        const mine = all.filter((p) => p.period_id === periodId);
        const loaded: { id: number; kind: string; url: string }[] = [];
        for (const p of mine.slice(0, 8)) {
          try {
            const r = await fetch(api.clientPhotoUrl(clientId, p.id), {
              headers: { Authorization: `Bearer ${getToken()}` },
            });
            if (!r.ok) continue;
            const url = URL.createObjectURL(await r.blob());
            urls.push(url);
            loaded.push({ id: p.id, kind: p.kind, url });
          } catch { /* una foto ilegible no rompe la tira */ }
        }
        if (alive) setPhotos(loaded);
      })
      .catch(() => alive && setPhotos([]));
    return () => {
      alive = false;
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [clientId, periodId]);

  if (!photos || photos.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Fotos de progreso del período
      </p>
      <div className="flex flex-wrap gap-2">
        {photos.map((p) => (
          <a key={p.id} href={p.url} target="_blank" rel="noopener noreferrer" className="group relative">
            <img src={p.url} alt={KIND_LABEL[p.kind] ?? p.kind}
              className="h-24 w-20 rounded-lg border border-zinc-700 object-cover transition group-hover:opacity-80" />
            <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 text-[10px] text-white">
              {KIND_LABEL[p.kind] ?? p.kind}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}
