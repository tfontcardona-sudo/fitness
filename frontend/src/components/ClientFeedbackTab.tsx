import { useCallback, useEffect, useState } from "react";
import { Sparkles, AlertTriangle, MessageSquare, MessageCircle, Mail, Video, Target, TrendingUp, BarChart3, CalendarCheck, CheckCircle2, Pencil, Save, X, Copy } from "lucide-react";
import { api } from "../lib/api";
import { feedbackBody, feedbackMessage, openWhatsApp, videoCallMessage, waPhone } from "../lib/whatsapp";
import { pkg } from "../lib/packages";
import { ExpandableArea, Spinner, useToast } from "./ui";
import type { ClientOut, VideoCallOut } from "../types";

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
  // Paquete del cliente: define cómo se entrega el feedback (email en Start/Full,
  // WhatsApp en Pro) y si hay contacto directo (videollamada de revisión en Pro).
  const info = pkg(client.package_tier);
  const byEmail = info.delivery === "email";
  const directContact = info.directContact;

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

  // Revisión a la que ya está adaptado el último plan (para ocultar el banner
  // "Revisar cambios…" una vez adaptada: el trabajo ya está hecho).
  const [adaptedIdx, setAdaptedIdx] = useState<number | null>(null);

  // Videollamadas quincenales (Pro) + enlace de reservas (marca).
  const [calls, setCalls] = useState<VideoCallOut[]>([]);
  const [meetUrl, setMeetUrl] = useState<string | null>(null);

  const loadCalls = useCallback(() => {
    if (!directContact) return;
    api.listVideoCalls(client.id).then(setCalls).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client.id, directContact]);
  useEffect(loadCalls, [loadCalls]);
  useEffect(() => {
    if (directContact) api.getBrand().then((b) => setMeetUrl(b.meet_url ?? null)).catch(() => {});
  }, [directContact]);

  const load = useCallback(() => {
    api.listPlans(client.id)
      .then((plans) => setAdaptedIdx(plans[0]?.nutrition_json?.applied_adjustments?.period_index ?? null))
      .catch(() => {});
    api.listPeriods(client.id)
      .then(async (ps) => {
        setPeriods(ps);
        // El resumen del período ACTUAL se carga solo (los antiguos, al desplegarlos)
        const latest = ps.reduce<Period | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
        if (latest && latest.status !== "open") loadMetrics(latest.id);
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
      toast.push(`Feedback generado. Revísalo y envíalo por ${byEmail ? "email" : "WhatsApp"}.`);
      load();
      onClientChanged?.(); // el aviso "Ir a Feedback" del perfil desaparece
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

  /** Entrega el feedback al cliente según su paquete:
   *  - Start/Full → por EMAIL (el informe va en el correo; el backend avanza el ciclo).
   *  - Pro → por WhatsApp (abre el chat con el feedback ya escrito).
   *  La primera vez marca el feedback como enviado (el ciclo avanza a "activo");
   *  se puede reenviar cuantas veces haga falta. */
  async function deliverFeedback(feedbackId: number, content: any, alreadySent: boolean, periodIndex = 0) {
    if (byEmail) {
      try {
        await api.sendFeedbackEmail(feedbackId);
        toast.push(alreadySent ? "Feedback reenviado por email" : "Feedback enviado por email al cliente");
        load();
        onClientChanged?.();
      } catch {
        toast.push("No se pudo enviar el email", "error");
      }
      return;
    }
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Añade el teléfono del cliente en su ficha para enviarlo por WhatsApp", "error");
      return;
    }
    openWhatsApp(phone, feedbackMessage(client.full_name, content, periodIndex));
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

  /** Pro: propone la videollamada por WhatsApp (con el enlace de reservas de la
   *  marca) y la deja registrada como PENDIENTE de fecha — el ciclo arranca:
   *  apuntar fecha → recordatorio el día antes → confirmar o reagendar. */
  async function proposeVideoCall(periodIndex: number) {
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Añade el teléfono del cliente en su ficha para la videollamada", "error");
      return;
    }
    openWhatsApp(phone, videoCallMessage(client.full_name, meetUrl));
    try {
      await api.createVideoCall(client.id, periodIndex);
      loadCalls();
    } catch {
      /* el WhatsApp ya está abierto; el registro puede reintentarse */
    }
    toast.push(meetUrl
      ? "WhatsApp abierto con tu enlace de reservas — cuando reserve, apunta aquí la fecha"
      : "WhatsApp abierto para acordar la videollamada");
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
          Aún no hay períodos. El ciclo es automático: al generar la planificación se abre
          el período de 14 días; el cliente registra su diario, lo cierra, y aquí generas
          su feedback.
        </p>
      </div>
    );
  }

  const latestReview = periods
    .filter((p) => p.status === "analyzed")
    .reduce<Period | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
  // El banner desaparece en cuanto la planificación YA está adaptada a esa revisión
  const needsAdapt = latestReview != null && adaptedIdx !== latestReview.period_index;
  const maxIdx = periods.reduce((mx, p) => Math.max(mx, p.period_index), 0);

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
      {[...periods].sort((a, b) => b.period_index - a.period_index).map((p) => {
        const fb = p.feedback_id ? contents[p.feedback_id] : null;
        const content = fb?.content;
        const sent: string | null = fb?.sent_at ?? null;
        const canGenerate = p.status !== "open"; // cerrado o analizado
        const daysElapsed = Math.floor((Date.now() - new Date(p.starts_on + "T00:00:00").getTime()) / 86400000) + 1;
        const ready = p.status !== "open" || daysElapsed >= 14; // resumen disponible a las 2 semanas
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
              <div className="flex gap-2" onClick={(e) => e.preventDefault()}>
                {p.feedback_id && content && !sent && (
                  <button onClick={() => deliverFeedback(p.feedback_id as number, content, false, p.period_index)} className="btn btn-primary">
                    {byEmail ? <><Mail size={15} /> Enviar por email</> : <><MessageCircle size={15} /> Enviar por WhatsApp</>}
                  </button>
                )}
                {canGenerate && !p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary">
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : "Generar feedback"}
                  </button>
                )}
              </div>
            </summary>

            {p.status === "open" && (
              <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5 text-xs" style={{ background: "rgba(154,107,21,0.09)", color: "#9A6B15" }}>
                <AlertTriangle size={14} /> El período aún está abierto: el cliente debe cerrarlo antes de generar el feedback.
              </div>
            )}

            {/* Videollamada quincenal (Pro): ciclo agendar → fecha → confirmar */}
            {directContact && p.status !== "open" && (
              <VideoCallCycle
                clientId={client.id}
                call={calls.find((c) => c.period_index === p.period_index) ?? null}
                meetUrl={meetUrl}
                onPropose={() => proposeVideoCall(p.period_index)}
                onChanged={loadCalls}
              />
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

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo.
                Se muestra SIEMPRE, ya cargado — sin botones que pulsar. */}
            {!m && loadingMetrics === p.id && (
              <p className="mt-4 flex items-center gap-2 border-t pt-4 text-xs text-zinc-500" style={{ borderColor: "var(--line)" }}>
                <Spinner /> Calculando el resumen de las 2 semanas…
              </p>
            )}
            {m && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  <BarChart3 size={13} /> Resumen de las 2 semanas
                </div>
                {/* Antes → después de los datos en 15 días (peso día 1 → día 15) */}
                <div className="mt-3">
                  <SubTitle icon={TrendingUp} text="Antes → después (15 días)" />
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
                    <SubTitle icon={TrendingUp} text="Fuerza por grupo muscular (vs revisiones anteriores)" />
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
                                <span style={{ color: s.delta_kg >= 0 ? "var(--brand-accent)" : "#C2453A" }}>
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
                                  <span style={{ color: s.avg_weight_delta_kg >= 0 ? "var(--brand-accent)" : "#C2453A" }}>
                                    {" "}({s.avg_weight_delta_kg >= 0 ? "+" : ""}{s.avg_weight_delta_kg} kg)
                                  </span>
                                )}
                              </>
                            )}
                            {s.avg_reps != null && <> · {s.avg_reps} reps de media</>}
                            {s.delta_kg == null && <> · primera revisión con datos de este ejercicio</>}
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
                      onClick={() => deliverFeedback(p.feedback_id as number, content, !!sent, p.period_index)}
                      className="flex items-center gap-1 text-xs font-medium hover:opacity-80"
                      style={{ color: "var(--brand-accent)" }}
                    >
                      {byEmail ? <><Mail size={13} /> Enviar por email</> : <><MessageCircle size={13} /> Enviar por WhatsApp</>}
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
          </details>
        );
      })}
    </div>
  );
}

/** Ciclo de la videollamada quincenal (Pro), por período:
 *  sin registro → "Proponer por WhatsApp" (abre el chat con el enlace de reservas)
 *  → pendiente → apuntar la fecha elegida (activa los recordatorios del día antes)
 *  → reservada → confirmar realizada (se cierra) o reagendar (vuelve a empezar). */
const VC_COLOR = "#0EA5E9";
function VideoCallCycle({ clientId, call, meetUrl, onPropose, onChanged }: {
  clientId: number;
  call: VideoCallOut | null;
  meetUrl: string | null;
  onPropose: () => void;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [date, setDate] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>, okMsg: string) {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
      toast.push(okMsg);
      onChanged();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo actualizar la videollamada", "error");
    } finally {
      setBusy(false);
    }
  }

  const fecha = call?.scheduled_for
    ? new Date(call.scheduled_for + "T00:00:00").toLocaleDateString("es-ES", {
        weekday: "long", day: "numeric", month: "long",
      })
    : null;

  return (
    <div className="mt-3 rounded-lg p-3"
      style={{ background: `color-mix(in srgb, ${VC_COLOR} 7%, transparent)`, border: `1px solid color-mix(in srgb, ${VC_COLOR} 25%, transparent)` }}>
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: VC_COLOR }}>
        <Video size={13} /> Videollamada quincenal
        {call?.status === "done" && <CheckCircle2 size={13} style={{ color: "#2E7D46" }} />}
      </div>

      {call === null && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-zinc-400">
            Toca la videollamada de revisión: propónsela por WhatsApp
            {meetUrl ? " con tu enlace de reservas (elige día y hora él mismo)." : "."}
          </p>
          <button onClick={onPropose} className="btn btn-primary !px-3 !py-1.5 text-xs">
            <MessageCircle size={13} /> Proponer por WhatsApp
          </button>
          {!meetUrl && (
            <p className="w-full text-[11px] text-zinc-500">
              Consejo: guarda tu enlace de reservas (Google Calendar/Meet) en{" "}
              <b>Recursos → Página de enlaces</b> y el mensaje lo incluirá solo.
            </p>
          )}
        </div>
      )}

      {call?.status === "pending" && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-400">
            Propuesta enviada. En cuanto el cliente reserve, apunta aquí el día para
            activar los recordatorios (a él y a ti, el día antes).
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <input type="date" className="input !w-auto !py-1.5 text-xs" value={date}
              onChange={(e) => setDate(e.target.value)} />
            <button
              className="btn btn-primary !px-3 !py-1.5 text-xs"
              disabled={!date || busy}
              onClick={() => run(
                () => api.scheduleVideoCall(clientId, call.id, date),
                "Fecha apuntada: os recordaré la videollamada el día antes",
              )}
            >
              <CalendarCheck size={13} /> Apuntar fecha
            </button>
            <button onClick={onPropose} className="text-xs text-zinc-500 hover:text-zinc-300">
              Reenviar WhatsApp
            </button>
          </div>
        </div>
      )}

      {call?.status === "scheduled" && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-300">
            Reservada para el <b>{fecha}</b>.
          </p>
          <p className="text-xs text-zinc-500">¿Se realizó la videollamada?</p>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn btn-primary !px-3 !py-1.5 text-xs"
              disabled={busy}
              onClick={() => run(
                () => api.videoCallDone(clientId, call.id),
                "Videollamada confirmada como realizada",
              )}
            >
              <CheckCircle2 size={13} /> Sí, realizada
            </button>
            <button
              className="btn btn-ghost !px-3 !py-1.5 text-xs"
              disabled={busy}
              onClick={() => run(
                () => api.videoCallReschedule(clientId, call.id),
                "Sin problema: vuelve a proponerla por WhatsApp y apunta la nueva fecha",
              )}
            >
              <X size={13} /> No, reagendar
            </button>
          </div>
        </div>
      )}

      {call?.status === "done" && (
        <p className="mt-1.5 text-xs" style={{ color: "#2E7D46" }}>
          Realizada. La siguiente tocará con la próxima revisión quincenal.
        </p>
      )}
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
