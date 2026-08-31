import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { libre } from "../lib/accordion";
import { ancla } from "../lib/anchors";
import { Sparkles, AlertTriangle, MessageSquare, MessageCircle, Mail, Video, Target, TrendingUp, BarChart3, CheckCircle2, Pencil, Save, X, Copy } from "lucide-react";
import { selloAdaptacion } from "./ClientPlanPanel";
import { api, getToken } from "../lib/api";
import { feedbackBody, feedbackMessage, openWhatsApp, videoCallModifyMessage, videoCallScheduledMessage, waPhone } from "../lib/whatsapp";
import { copiarConAviso } from "../lib/clipboard";
import { pkg } from "../lib/packages";
import { useBrand } from "../hooks/useBrand";
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
  const { brand } = useBrand();   // para el enlace de reservas del coach
  const [periods, setPeriods] = useState<Period[] | null>(null);
  const [contents, setContents] = useState<Record<number, any>>({});
  const [generating, setGenerating] = useState<number | null>(null);
  const [closing, setClosing] = useState<number | null>(null);
  const [enviando, setEnviando] = useState(false);
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

  // Videollamadas quincenales (Pro): el cliente propone → el coach acepta/modifica.
  // Se necesita Google conectado para crear el evento con Meet.
  const [calls, setCalls] = useState<VideoCallOut[]>([]);
  const [googleConnected, setGoogleConnected] = useState(false);

  const loadCalls = useCallback(() => {
    if (!directContact) return;
    api.listVideoCalls(client.id).then(setCalls).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client.id, directContact]);
  useEffect(loadCalls, [loadCalls]);
  useEffect(() => {
    if (!directContact) return;
    api.googleStatus().then((s) => setGoogleConnected(s.connected)).catch(() => {});
  }, [directContact]);

  function _whenLabel(call: VideoCallOut): string {
    return call.scheduled_at
      ? new Date(call.scheduled_at).toLocaleString("es-ES", {
          weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
        })
      : "";
  }

  /** Pro: comparte por WhatsApp la videollamada YA agendada (fecha + Meet). */
  function shareMeetWhatsApp(call: VideoCallOut) {
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Falta su teléfono", "error");
      return;
    }
    openWhatsApp(phone, videoCallScheduledMessage(client.full_name, _whenLabel(call), call.meet_url ?? ""));
  }

  /** Pro: MODIFICAR la propuesta → abre WhatsApp para acordar el nuevo día/hora y
   *  deja la videollamada pendiente de agendar a mano. */
  async function modifyVideoCall(call: VideoCallOut) {
    const phone = waPhone(client.phone);
    if (phone) {
      openWhatsApp(phone, videoCallModifyMessage(
        client.full_name, _whenLabel(call), brand?.meet_url ?? null));
    }
    try {
      await api.modifyVideoCall(client.id, call.id);
      loadCalls();
      // SIN teléfono no se ha abierto ningún WhatsApp: decir "acuerda el día
      // por WhatsApp" mandaba al coach a mirar una ventana que no existe.
      toast.push(phone
        ? "Acuerda el día por WhatsApp"
        : "Pendiente de agendar · sin teléfono, escríbele por email");
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo modificar", "error");
    }
  }

  const load = useCallback(() => {
    // LIGERO: esta pantalla solo mira el sello de la adaptación, no necesita
    // el banco de recetas ni el educativo de cada versión.
    api.listPlans(client.id, { ligero: true })
      .then((plans) => {
        // El plan VIGENTE (publicado; si no, el más nuevo), no `plans[0]`: con
        // un borrador retenido de un mes superior, ese no es el activo. Y el
        // sello puede vivir en el entreno (plan solo-entrenamiento): sin eso,
        // para todo el tier `train` el banner de "revisar y adaptar" era
        // eterno y el botón devolvía 409.
        const vigente = plans.find((p: any) => p.status === "published")
          ?? [...plans].sort((a: any, b: any) => (b.id ?? 0) - (a.id ?? 0))[0];
        setAdaptedIdx(selloAdaptacion(vigente)?.period_index ?? null);
      })
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
      toast.push(`Feedback listo`);
      load();
      onClientChanged?.(); // el aviso "Ir a Feedback" del perfil desaparece
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo generar el feedback", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setGenerating(null);
    }
  }

  /** Cierra la quincena EL COACH cuando el cliente no la envía: el ciclo se
   *  quedaba bloqueado (sin cierre no hay feedback ni período nuevo) y la única
   *  salida era insistirle. Pide confirmación porque cierra datos reales. */
  async function closeByCoach(periodId: number, index: number) {
    if (closing != null) return;
    if (!window.confirm(
      `¿Cerrar tú la revisión #${index}?\n\nSe usará como peso final el último ` +
      "pesaje que tenga registrado. Podrás generar su feedback al momento.",
    )) return;
    setClosing(periodId);
    try {
      const r = await api.closePeriodByCoach(periodId);
      toast.push(`Revisión #${r.period_index} cerrada (peso final ${r.closing_weight_kg} kg). Ya puedes generar su feedback.`);
      load();
      onClientChanged?.();
    } catch (e: any) {
      toast.push(e?.message ?? "Revisión no cerrada", "error");
    } finally {
      setClosing(null);
    }
  }

  function copyAll(content: any) {
    void copiarConAviso(feedbackBody(content), toast, "Feedback copiado al portapapeles");
  }

  /** Entrega el feedback al cliente según su paquete:
   *  - Start/Full → por EMAIL (el informe va en el correo; el backend avanza el ciclo).
   *  - Pro → por WhatsApp (abre el chat con el feedback ya escrito).
   *  La primera vez marca el feedback como enviado (el ciclo avanza a "activo");
   *  se puede reenviar cuantas veces haga falta. */
  async function deliverFeedback(feedbackId: number, content: any, alreadySent: boolean, periodIndex = 0) {
    // Con la web lenta el coach pulsa dos veces y el cliente recibe el informe
    // por duplicado. El candado va aquí, no en cada botón.
    if (enviando) return;
    setEnviando(true);
    try {
      await _deliverFeedback(feedbackId, content, alreadySent, periodIndex);
    } finally {
      setEnviando(false);
    }
  }

  async function _deliverFeedback(feedbackId: number, content: any, alreadySent: boolean, periodIndex = 0) {
    if (byEmail) {
      try {
        const r = await api.sendFeedbackEmail(feedbackId);
        // El backend marca "enviado" y avanza el ciclo ANTES del email: si el
        // email falló, decir "enviado" sin más dejaba al cliente sin informe
        // y a nadie enterado (auditoría del ciclo).
        if (r.email_status === "sent") {
          toast.push(alreadySent ? "Feedback reenviado por email" : "Feedback enviado por email");
        } else {
          toast.push(
            r.email_status === "disabled"
              ? "Emails desactivados · ciclo avanzado"
              : "Email fallido · ciclo avanzado",
            "error",
          );
        }
        load();
        onClientChanged?.();
      } catch {
        toast.push("No se pudo enviar el email", "error");
      }
      return;
    }
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Falta su teléfono", "error");
      return;
    }
    openWhatsApp(phone, feedbackMessage(client.full_name, content, periodIndex));
    if (alreadySent) {
      toast.push("WhatsApp abierto");
      return;
    }
    try {
      await api.sendFeedback(feedbackId);
      toast.push("WhatsApp abierto");
      load();
      onClientChanged?.();
    } catch {
      // EL CATCH MUDO otra vez (ya se corrigió en el panel de Planificación,
      // no aquí): el WhatsApp se abre igual, pero si el backend no registra el
      // envío el ciclo NO avanza — el feedback sigue sin `sent_at`, el cliente
      // no lo ve en su Progreso y el cliente se queda en `review_pending`. Sin
      // aviso, el coach da por hecho que ya está y nadie vuelve a mirarlo.
      toast.push("WhatsApp abierto, pero el envío no quedó registrado · "
                 + "vuelve a pulsar Enviar para que el ciclo avance", "error");
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

  // Videollamada (Pro): se ancla a la ÚLTIMA revisión cerrada/analizada (igual
  // que la alerta). Se muestra ARRIBA del todo y SIEMPRE visible — antes vivía
  // dentro del período, que queda plegado, así que al pulsar la notificación
  // el coach no veía los botones de aceptar/modificar.
  const lastReviewIdx = periods
    .filter((p) => p.status === "closed" || p.status === "analyzed")
    .reduce((mx, p) => Math.max(mx, p.period_index), 0);
  const callForLastReview = calls.find((c) => c.period_index === lastReviewIdx) ?? null;
  const showVideoCall = directContact && lastReviewIdx > 0 && callForLastReview?.status !== "done";
  // Videollamadas VIVAS de revisiones ANTERIORES. El backend avisa de ellas a
  // propósito (una propuesta sin responder no puede esfumarse), pero el panel
  // solo pintaba la de la última revisión: el coach recibía el aviso, pulsaba,
  // y aterrizaba en una pantalla sin los botones para resolverla.
  const huerfanas = calls.filter((c) =>
    c.period_index !== lastReviewIdx
    && (c.status === "proposed" || c.status === "pending_manual" || c.status === "scheduled"));

  return (
    <div className="space-y-4">
      {/* La DECISIÓN pendiente va primera: adaptar el plan a la revisión es la
          acción que cierra el ciclo. La videollamada va después. */}
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
            <Sparkles size={14} /> Revisar y adaptar el plan
          </button>
        </div>
      )}
      {huerfanas.map((vc) => (
        <div key={vc.id} className="card p-3.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Videollamada pendiente de la revisión #{vc.period_index}
          </p>
          <VideoCallCycle
            clientId={client.id}
            periodIndex={vc.period_index}
            call={vc}
            googleConnected={googleConnected}
            onModify={modifyVideoCall}
            onShareMeet={shareMeetWhatsApp}
            onChanged={loadCalls}
          />
        </div>
      ))}

      {/* Videollamada quincenal (Pro). Si YA está agendada (nada que hacer),
          se colapsa a una línea; desplegada solo cuando pide acción del coach. */}
      {showVideoCall && (callForLastReview?.status === "scheduled" ? (
        <details className="card p-3.5">
          <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm text-zinc-300">
            <Video size={15} style={{ color: VC_COLOR }} />
            <span className="font-medium" style={{ color: VC_COLOR }}>Videollamada confirmada</span>
            {callForLastReview.scheduled_at && <span className="text-zinc-400">· {_whenLabel(callForLastReview)}</span>}
            {callForLastReview.meet_url && (
              <a href={callForLastReview.meet_url} target="_blank" rel="noreferrer"
                 onClick={(e) => e.stopPropagation()}
                 className="ml-auto text-xs font-semibold underline" style={{ color: VC_COLOR }}>
                Unirme
              </a>
            )}
          </summary>
          <div className="mt-3">
            <VideoCallCycle
              clientId={client.id}
              periodIndex={lastReviewIdx}
              call={callForLastReview}
              googleConnected={googleConnected}
              onModify={modifyVideoCall}
              onShareMeet={shareMeetWhatsApp}
              onChanged={loadCalls}
            />
          </div>
        </details>
      ) : (
        <VideoCallCycle
          clientId={client.id}
          periodIndex={lastReviewIdx}
          call={callForLastReview}
          googleConnected={googleConnected}
          onModify={modifyVideoCall}
          onShareMeet={shareMeetWhatsApp}
          onChanged={loadCalls}
        />
      ))}
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
            {...libre()}
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
                  <button onClick={() => deliverFeedback(p.feedback_id as number, content, false, p.period_index)}
                    disabled={enviando} className="btn btn-primary"
                    {...ancla("feedback.enviar")}>
                    {byEmail ? <><Mail size={15} /> Enviar por email</> : <><MessageCircle size={15} /> Enviar por WhatsApp</>}
                  </button>
                )}
                {canGenerate && !p.feedback_id && (
                  <button onClick={() => generate(p.id)} disabled={generating === p.id} className="btn btn-primary"
                    {...ancla("feedback.generar")}>
                    <Sparkles size={15} />
                    {generating === p.id ? "Generando…" : "Generar feedback"}
                  </button>
                )}
              </div>
            </summary>

            {p.status === "open" && (
              <div className="mt-3 rounded-lg p-2.5 text-xs" style={{ background: "rgba(154,107,21,0.09)", color: "#9A6B15" }}>
                <div className="flex items-center gap-2">
                  <AlertTriangle size={14} /> Período abierto: falta su cierre
                </div>
                {/* Vencido y sin enviar: el ciclo se bloqueaba esperándole para
                    siempre. El coach puede cerrarlo él y seguir (auditoría). */}
                {daysElapsed > 14 && (
                  <button
                    onClick={() => closeByCoach(p.id, p.period_index)}
                    disabled={closing === p.id}
                    {...ancla("feedback.cerrar")}
                    className="btn btn-ghost mt-2 text-xs"
                  >
                    {closing === p.id ? "Cerrando…" : "Venció · cerrarla yo"}
                  </button>
                )}
              </div>
            )}

            {/* La videollamada quincenal (Pro) se muestra ARRIBA del todo, no
                dentro del período (que queda plegado). Ver `showVideoCall`. */}

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
            {/* La voz del cliente es oro para la asesoría: tamaño normal y las
                dudas destacadas en ámbar (exigen respuesta en la revisión). */}
            {p.closing_hardest && <p className="mt-2 text-sm text-zinc-300"><b>Lo más difícil:</b> {p.closing_hardest}</p>}
            {p.closing_questions && (
              <p className="mt-1 rounded-lg border-l-2 py-1 pl-2 text-sm text-zinc-300"
                 style={{ borderColor: "#9A6B15", background: "color-mix(in srgb, #9A6B15 8%, transparent)" }}>
                <b style={{ color: "#9A6B15" }}>Dudas para ti:</b> {p.closing_questions}
              </p>
            )}

            {/* Fotos de progreso del período: plegadas y con carga PEREZOSA —
                las imágenes solo se descargan si el coach abre el desplegable
                (8 blobs en mitad de la columna interrumpían la lectura). */}
            {p.status !== "open" && <PeriodPhotosFolded clientId={client.id} periodId={p.id} />}

            {/* Resumen de métricas (sin IA): fuerza, peso, adherencia, objetivo.
                Se muestra SIEMPRE, ya cargado — sin botones que pulsar. */}
            {!m && loadingMetrics === p.id && (
              <p className="mt-4 flex items-center gap-2 border-t pt-4 text-xs text-zinc-500" style={{ borderColor: "var(--line)" }}>
                <Spinner /> Calculando resumen…
              </p>
            )}
            {m && (
              <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
                <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  <BarChart3 size={13} /> Resumen de las 2 semanas
                </div>
                {/* EVOLUCIÓN, sin duplicados: el peso con su antes→después real
                    (los perímetros ya están arriba en "Datos del cierre"; aquí
                    con before=null pintaban "— → 92" y parecían datos rotos). */}
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {/* Bajar peso solo es "bueno" si el objetivo lo pide */}
                  <BAStat label="Peso (kg)" before={m.weight?.start_kg} after={m.weight?.end_kg} lowerBetter={client.goal_type !== "muscle_gain"} />
                  <Stat label="Ritmo semanal" value={fmtDelta(m.weight?.weekly_rate_kg, "kg/sem")} />
                  <Stat label="A su objetivo" value={m.distance_to_goal_kg != null ? `${Math.abs(m.distance_to_goal_kg)} kg` : "—"} />
                  <Stat
                    label="Adherencia dieta"
                    // Sin un solo registro de dieta no es un 0 %: es que no
                    // hay dato (un cliente de solo entreno ni ve ese campo).
                    value={m.adherence?.diet_pct == null
                      ? "Sin datos"
                      : `${m.adherence.diet_pct}% · ${(m.adherence?.diet_days_yes ?? 0) + (m.adherence?.diet_days_partial ?? 0)} de ${m.adherence?.period_days ?? 0} días`}
                  />
                  <Stat label="Días registrados" value={`${m.adherence?.days_logged ?? 0}/${m.adherence?.period_days ?? 0}`} />
                </div>
                {info.hasTraining && Array.isArray(m.strength) && m.strength.length > 0 && (
                  <div>
                    <SubTitle icon={TrendingUp} text="Fuerza (vs revisiones anteriores)" />
                    {/* Señal primero: cuántos mejoran. Top 3 a la vista; el
                        detalle completo, plegado (para la asesoría bastan 2-3
                        señales, no 8 filas de datos crudos). */}
                    {(() => {
                      const withDelta = m.strength.filter((s: any) => s.delta_kg != null);
                      const up = withDelta.filter((s: any) => s.delta_kg > 0).length;
                      return withDelta.length > 0 ? (
                        <p className="mb-1.5 text-xs text-zinc-400">
                          {up}/{withDelta.length} ejercicios mejoran
                        </p>
                      ) : null;
                    })()}
                    <ul className="space-y-1 text-sm">
                      {m.strength.slice(0, 3).map((s: any, i: number) => <StrengthRow key={i} s={s} />)}
                    </ul>
                    {m.strength.length > 3 && (
                      <details className="mt-1">
                        <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-300">
                          Ver los {m.strength.length} ejercicios
                        </summary>
                        <ul className="mt-1 space-y-1 text-sm">
                          {m.strength.slice(3).map((s: any, i: number) => <StrengthRow key={i} s={s} />)}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
                {info.hasTraining && (!m.strength || m.strength.length === 0) && (
                  <p className="mt-2 text-xs text-zinc-500">Fuerza: sin series registradas</p>
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
                {/* LAS DECISIONES primero: la cuadrícula que se aplicará al
                    plan, en tabla legible (antes solo existía en el Word). */}
                {Array.isArray(content.plan_adjustments) && content.plan_adjustments.length > 0 && (
                  <div>
                    <SubTitle icon={Sparkles} text="Decisiones para la próxima quincena" />
                    <div className="space-y-1 text-sm">
                      {content.plan_adjustments.map((a: any, i: number) => (
                        <div key={i} className="rounded-lg px-3 py-2" style={{ background: "var(--surface-raised)" }}>
                          <div className="flex flex-wrap items-baseline gap-2">
                            {a.area && (
                              <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                                style={{ background: "color-mix(in srgb, var(--brand-accent) 14%, transparent)", color: "var(--brand-accent)" }}>
                                {a.area}
                              </span>
                            )}
                            <span className="font-medium text-zinc-200">{a.change}</span>
                          </div>
                          {a.reason && <p className="mt-0.5 text-xs text-zinc-500">{a.reason}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {/* La narrativa de los cambios repite las decisiones con más
                    palabras: visible solo si NO hay cuadrícula; si la hay, plegada. */}
                {Array.isArray(content.changes_bullets) && content.changes_bullets.length > 0 && (
                  (Array.isArray(content.plan_adjustments) && content.plan_adjustments.length > 0) ? (
                    <details>
                      <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-300">
                        Explicación de los cambios ({content.changes_bullets.length})
                      </summary>
                      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                        {content.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                      </ul>
                    </details>
                  ) : (
                    <div>
                      <SubTitle icon={Sparkles} text="Cambios en el plan" />
                      <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-400">
                        {content.changes_bullets.map((b: string, i: number) => <li key={i}>{b}</li>)}
                      </ul>
                    </div>
                  )
                )}
                {content.answers && (
                  <div>
                    <SubTitle icon={MessageSquare} text="Respuesta a sus dudas" />
                    {/* La duda del cliente citada junto a su respuesta: antes
                        estaban a 60 líneas de distancia. */}
                    {p.closing_questions && (
                      <p className="mb-1 border-l-2 pl-2 text-xs italic text-zinc-500" style={{ borderColor: "var(--line-strong)" }}>
                        «{p.closing_questions}»
                      </p>
                    )}
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
                {content.closing_message && (
                  <details>
                    <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-300">
                      Mensaje de cierre al cliente
                    </summary>
                    <p className="mt-1 text-sm italic text-zinc-400">{content.closing_message}</p>
                  </details>
                )}
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

/** Fecha de HOY local en formato YYYY-MM-DD (para el min del selector). */
function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function VideoCallCycle({ clientId, periodIndex, call, googleConnected, onModify, onShareMeet, onChanged }: {
  clientId: number;
  periodIndex: number;
  call: VideoCallOut | null;
  googleConnected: boolean;
  onModify: (call: VideoCallOut) => void;
  onShareMeet: (call: VideoCallOut) => void;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [gDate, setGDate] = useState("");       // agendar a mano: día
  const [gTime, setGTime] = useState("17:00");  // …hora
  const [gDur, setGDur] = useState(30);         // …duración (min)
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>, okMsg: string) {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
      toast.push(okMsg);
      onChanged();
    } catch (e: any) {
      toast.push(e?.message ?? "Videollamada no actualizada", "error");
    } finally {
      setBusy(false);
    }
  }

  async function copyLink(url: string) {
    await copiarConAviso(url, toast, "Enlace de Meet copiado");
  }

  const cuando = call?.scheduled_at
    ? new Date(call.scheduled_at).toLocaleString("es-ES", {
        weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
      })
    : null;

  const durationSelect = (
    <select className="input !w-auto !py-1.5 text-xs" value={gDur}
      onChange={(e) => setGDur(Number(e.target.value))}>
      <option value={30}>30 min</option>
      <option value={45}>45 min</option>
      <option value={60}>60 min</option>
    </select>
  );

  const notConnectedNote = !googleConnected ? (
    <p className="text-[11px]" style={{ color: "#9A6B15" }}>
      Sin Google no hay Meet.{" "}
      <Link to="/recursos?tab=enlaces" className="font-semibold underline underline-offset-2">
        Conectar Google →
      </Link>
    </p>
  ) : null;

  // Bloque "agendar a mano" (día + hora + duración → crea el evento con Meet).
  // `min` del picker no impide teclear una fecha pasada a mano: se valida.
  const gDatePast = gDate !== "" && gDate < localToday();
  const manualScheduler = (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <input type="date" className="input !w-auto !py-1.5 text-xs" value={gDate}
          min={localToday()} onChange={(e) => setGDate(e.target.value)} />
        <input type="time" className="input !w-auto !py-1.5 text-xs" value={gTime}
          onChange={(e) => setGTime(e.target.value)} />
        {durationSelect}
        <button
          className="btn btn-primary !px-3 !py-1.5 text-xs"
          disabled={!gDate || !gTime || busy || !googleConnected || gDatePast}
          title={!googleConnected ? "Conecta Google en Recursos → Página de enlaces"
            : !gDate || !gTime ? "Elige el día y la hora"
            : gDatePast ? "Fecha pasada · elige otra" : undefined}
          onClick={() => run(
            () => api.scheduleVideoCallMeet(clientId, periodIndex, `${gDate}T${gTime}`, gDur),
            "Videollamada agendada en Meet y enlace enviado al cliente",
          )}
        >
          <Video size={13} /> Agendar con Meet
        </button>
      </div>
      {gDatePast && (
        <p className="text-[11px]" style={{ color: "#C2453A" }}>La fecha elegida ya pasó.</p>
      )}
      {notConnectedNote}
    </div>
  );

  return (
    <div className="mt-3 rounded-lg p-3"
      {...ancla(call ? `feedback.videollamada.${call.id}` : "feedback.videollamada")}
      style={{ background: `color-mix(in srgb, ${VC_COLOR} 7%, transparent)`, border: `1px solid color-mix(in srgb, ${VC_COLOR} 25%, transparent)` }}>
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: VC_COLOR }}>
        <Video size={13} /> Videollamada quincenal
        {call?.status === "done" && <CheckCircle2 size={13} style={{ color: "#2E7D46" }} />}
      </div>

      {/* Sin propuesta aún: al cliente le aparece en su portal al enviar la
          revisión. El coach también puede agendarla a mano. */}
      {call === null && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-400">
            El cliente aún no ha propuesto día/hora (le aparece en su portal al enviar
            la revisión). Si lo prefieres, agéndala tú a mano:
          </p>
          {manualScheduler}
        </div>
      )}

      {/* Propuesta del cliente: aceptar tal cual, modificar (WhatsApp) o darla
          por hecha. Este último botón faltaba: el backend admite cerrar desde
          `proposed` y `pending_manual` justamente para que sin Google (o si la
          llamada se hizo por teléfono) la propuesta tenga salida, pero la web
          no lo ofrecía y su alerta ALTA sonaba para siempre. */}
      {call?.status === "proposed" && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-300">
            El cliente propuso: <b>{cuando}</b>. Acéptala o modifícala.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {durationSelect}
            <button
              className="btn btn-primary !px-3 !py-1.5 text-xs"
              disabled={busy || !googleConnected}
              onClick={() => run(
                () => api.acceptVideoCall(clientId, call.id, gDur),
                "Videollamada agendada en Meet y enlace enviado al cliente",
              )}
            >
              <CheckCircle2 size={13} /> Aceptar y crear Meet
            </button>
            <button className="btn btn-ghost !px-3 !py-1.5 text-xs" disabled={busy}
              onClick={() => onModify(call)}>
              <Pencil size={13} /> Modificar (WhatsApp)
            </button>
            <button className="btn btn-ghost !px-3 !py-1.5 text-xs" disabled={busy}
              onClick={() => run(
                () => api.videoCallDone(clientId, call.id),
                "Videollamada marcada como hecha",
              )}
              title="Si ya la hicisteis por teléfono o WhatsApp, o no vas a usar Meet">
              <CheckCircle2 size={13} /> Ya está hecha
            </button>
          </div>
          {notConnectedNote}
        </div>
      )}

      {/* Pendiente de agendar a mano (tras Modificar): acordado por WhatsApp. */}
      {(call?.status === "pending_manual" || call?.status === "pending") && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-400">
            Pendiente de agendar a mano. Acuerda el día con el cliente por WhatsApp y
            escríbelo aquí:
          </p>
          {manualScheduler}
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn btn-ghost !px-3 !py-1.5 text-xs" disabled={busy}
              onClick={() => run(
                () => api.videoCallDone(clientId, call.id),
                "Videollamada marcada como hecha",
              )}
              title="Si ya la hicisteis por teléfono o WhatsApp, o no vas a usar Meet">
              <CheckCircle2 size={13} /> Ya está hecha
            </button>
          </div>
          <button className="text-[11px] text-zinc-500 hover:text-zinc-300"
            onClick={() => onModify(call)}>
            Reenviar WhatsApp al cliente
          </button>
        </div>
      )}

      {call?.status === "scheduled" && (
        <div className="mt-2 space-y-2">
          <p className="text-xs text-zinc-300">
            Agendada para el <b>{cuando}</b>
            {call.duration_min ? <span className="text-zinc-500"> ({call.duration_min} min)</span> : null}.
          </p>
          {call.meet_url && (
            <div className="flex flex-wrap gap-2">
              <a href={call.meet_url} target="_blank" rel="noopener noreferrer"
                className="btn btn-primary !px-3 !py-1.5 text-xs">
                <Video size={13} /> Unirme a Meet
              </a>
              <button className="btn btn-ghost !px-3 !py-1.5 text-xs" onClick={() => copyLink(call.meet_url!)}>
                <Copy size={13} /> Copiar enlace
              </button>
              <button className="btn btn-ghost !px-3 !py-1.5 text-xs" onClick={() => onShareMeet(call)}>
                <MessageCircle size={13} /> Enviar por WhatsApp
              </button>
            </div>
          )}
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
                "Evento cancelado en Google",
              )}
            >
              <X size={13} /> No, reagendar
            </button>
          </div>
        </div>
      )}

      {call?.status === "done" && (
        <p className="mt-1.5 text-xs" style={{ color: "#2E7D46" }}>
          Realizada · próxima revisión quincenal
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
          recibió aquella versión por WhatsApp/email. Si lo editas, reenvíaselo para que le llegue la nueva.
        </p>
      )}
      <FbArea label="Análisis" value={d.natural_analysis} onChange={(v) => set("natural_analysis", v)} rows={4} />
      <FbArea label="Cambios (uno por línea)" value={d.changes_bullets} onChange={(v) => set("changes_bullets", v)} />
      <FbArea label="Respuesta a sus dudas" value={d.answers} onChange={(v) => set("answers", v)} />
      <FbArea label="Objetivos (uno por línea)" value={d.next_objectives} onChange={(v) => set("next_objectives", v)} />
      <FbArea label="Mensaje de cierre" value={d.closing_message} onChange={(v) => set("closing_message", v)} rows={2} />
      <FbArea
        label="Ajustes al plan (uno por línea)"
        value={d.plan_adjustments} onChange={(v) => set("plan_adjustments", v)} />
    </div>
  );
}

function FbArea({ label, value, onChange, rows = 3 }: { label: string; value: string; onChange: (v: string) => void; rows?: number }) {
  return <ExpandableArea label={label} value={value} onChange={onChange} rows={rows} />;
}

/** Fila de fuerza de un ejercicio (e1RM + delta + detalle). Compartida entre
 *  el top 3 visible y la lista completa plegada. */
function StrengthRow({ s }: { s: any }) {
  return (
    <li className="rounded-lg px-3 py-2" style={{ background: "var(--surface-raised)" }}>
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
        {s.delta_kg == null && <> · primera vez con datos</>}
      </div>
    </li>
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
/** Envoltorio plegado de las fotos: consulta solo el NÚMERO (metadatos, barato)
 *  y no descarga ninguna imagen hasta que el coach abre el desplegable. */
export function PeriodPhotosFolded({ clientId, periodId, label }: {
  clientId: number;
  /** `null` = las fotos INICIALES de la anamnesis (sin período): el "antes" de
   *  la primera revisión, que hasta ahora no se veía en ninguna pantalla del
   *  coach pese a pedírselas al cliente con un "solo las ve tu coach". */
  periodId: number | null;
  label?: string;
}) {
  const [count, setCount] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let alive = true;
    api.listClientPhotos(clientId)
      .then((all) => { if (alive) setCount(all.filter((p) => p.period_id === periodId).length); })
      .catch(() => { if (alive) setCount(0); });
    return () => { alive = false; };
  }, [clientId, periodId]);
  if (!count) return null;
  return (
    <details className="mt-2" {...libre()}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer text-xs font-medium text-zinc-500 hover:text-zinc-300">
        {label ?? "Fotos del período"} ({count})
      </summary>
      {open && <PeriodPhotos clientId={clientId} periodId={periodId} />}
    </details>
  );
}

function PeriodPhotos({ clientId, periodId }: { clientId: number; periodId: number | null }) {
  const [photos, setPhotos] = useState<{ id: number; kind: string; url: string }[] | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let alive = true;
    const urls: string[] = [];
    api.listClientPhotos(clientId)
      .then(async (all) => {
        const mine = all.filter((p) => p.period_id === periodId);
        if (alive) setTotal(mine.length);
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
      {total > photos.length && (
        <p className="mt-1 text-[11px] text-zinc-500">
          {photos.length} de {total} · resto en su ficha
        </p>
      )}
    </div>
  );
}
