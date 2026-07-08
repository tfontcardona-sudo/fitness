import { useEffect, useState } from "react";
import { Sparkles, Download, Send, AlertTriangle, Dumbbell, Utensils, Pill, CalendarDays, MessageCircle, Pencil, Save, X, Flag, Copy, Archive } from "lucide-react";
import { api, getToken } from "../lib/api";
import { openWhatsApp, planAndFeedbackMessage, planMessage, waPhone } from "../lib/whatsapp";
import { GOAL_LABEL, goalDays, goalReviewDue, planMonthLabel } from "../lib/format";
import { deficitLabel, macroPct, MACRO_TOTAL_TOLERANCE } from "../lib/nutritionTargets";
import { isCriticalLine } from "../lib/clinical";
import { Spinner, useToast } from "./ui";
import { MemoDetails } from "./MemoDetails";
import { ClientPlanEditor } from "./ClientPlanEditor";
import type { ClientOut, GoalType } from "../types";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
  created_at?: string | null;
  published_at?: string | null;
}

/** Normaliza un plan venga de generatePlan (nutrition/...) o de listPlans (nutrition_json/...). */
function normalize(p: any): PlanData {
  return {
    id: p.id,
    month_index: p.month_index,
    version: p.version,
    status: p.status,
    guardrail_flags: p.guardrail_flags ?? [],
    nutrition: p.nutrition ?? p.nutrition_json ?? null,
    training: p.training ?? p.training_json ?? null,
    education: p.education ?? p.education_json ?? null,
    created_at: p.created_at ?? null,
    published_at: p.published_at ?? null,
  };
}

/**
 * Planificación: genera el plan mensual con IA a partir de la anamnesis, lo
 * PERSISTE (al volver a la pestaña se recarga el último plan guardado), muestra
 * la info del plan (nutrición, entrenamiento, puntos del cliente, suplementos)
 * y queda ACTIVO al generarse/adaptarse/editarse — sin paso de publicar.
 */
export function ClientPlanPanel({ client, onClientChanged }: { client: ClientOut; onClientChanged?: () => void }) {
  const toast = useToast();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [exMap, setExMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [periods, setPeriods] = useState<{
    id: number; period_index: number; plan_id: number | null; starts_on: string; ends_on: string; status: string;
    feedback_id?: number | null;
    plan_adjustments?: { area: string; change: string; reason: string }[] | null;
  }[]>([]);
  // Todas las versiones (archivo de planificaciones anteriores por objetivo)
  const [allPlans, setAllPlans] = useState<any[]>([]);
  // Último feedback generado (para poder enviarlo junto al plan por WhatsApp).
  const [fb, setFb] = useState<{ id: number; content: any; sent: boolean } | null>(null);
  // Edición de los "Cambios aplicados" tras adaptar: texto/porqué o quitar filas.
  const [adjDraft, setAdjDraft] = useState<{ area: string; main: string; reason: string; orig: any }[] | null>(null);
  const [savingAdj, setSavingAdj] = useState(false);
  // Tras EDITAR el plan: recordatorio de descargar el PDF de nuevo (la versión
  // editada ya está guardada; el PDF descargado antes se queda antiguo).
  const [needsDownload, setNeedsDownload] = useState(false);

  // Al montar: carga el último plan guardado + el mapa de ejercicios + los períodos.
  useEffect(() => {
    let alive = true;
    Promise.all([
      api.listPlans(client.id),
      api.listExercises({ include_archived: true }),
      api.listPeriods(client.id),
    ])
      .then(([plans, exs, pds]) => {
        if (!alive) return;
        const map: Record<number, string> = {};
        exs.forEach((e) => (map[e.id] = e.canonical_name));
        setExMap(map);
        setPeriods(pds);
        setAllPlans(plans);
        if (plans.length) setPlan(normalize(plans[0])); // [0] = versión más reciente
        // Feedback más reciente (si existe): habilita el envío conjunto.
        const withFb = pds
          .filter((p: any) => p.feedback_id)
          .reduce<any>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
        if (withFb?.feedback_id) {
          api.getFeedback(withFb.feedback_id)
            .then((f) => alive && setFb({ id: withFb.feedback_id, content: f.content, sent: !!f.sent_at }))
            .catch(() => {});
        }
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [client.id]);

  /** Enlace público al PDF del plan (endpoint por token — sin login). */
  async function planPdfUrl(): Promise<string> {
    const link = await api.portalLink(client.id);
    return `${window.location.origin}/api/p/${link.portal_token}/plan.pdf`;
  }

  /** Un clic: abre WhatsApp del cliente con el mensaje profesional del plan
   *  y el enlace directo a su PDF. */
  async function sendPlanWhatsApp() {
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Añade el teléfono del cliente en su ficha para enviarlo por WhatsApp", "error");
      return;
    }
    try {
      const pdfUrl = await planPdfUrl();
      const adaptedIdx = plan?.nutrition?.applied_adjustments?.period_index ?? null;
      openWhatsApp(phone, planMessage(client.full_name, pdfUrl, adaptedIdx, plan?.month_index ?? 1));
      // El enlace genera el PDF al abrirse → el cliente recibe la versión
      // vigente: el aviso de re-descarga queda resuelto.
      setNeedsDownload(false);
      toast.push("WhatsApp abierto con el enlace del plan — dale a enviar");
    } catch {
      toast.push("No se pudo obtener el enlace del plan", "error");
    }
  }

  /** Un clic: plan + feedback juntos en un solo WhatsApp (mensaje profesional).
   *  Si el feedback aún no constaba como enviado, se marca (el ciclo avanza). */
  async function sendPlanAndFeedbackWhatsApp() {
    if (!fb) return;
    const phone = waPhone(client.phone);
    if (!phone) {
      toast.push("Añade el teléfono del cliente en su ficha para enviarlo por WhatsApp", "error");
      return;
    }
    try {
      const pdfUrl = await planPdfUrl();
      const adaptedIdx = plan?.nutrition?.applied_adjustments?.period_index ?? null;
      openWhatsApp(phone, planAndFeedbackMessage(client.full_name, fb.content, pdfUrl, adaptedIdx));
      setNeedsDownload(false); // el enlace enviado sirve la versión vigente
      toast.push("WhatsApp abierto con el plan y el feedback — dale a enviar");
      if (!fb.sent) {
        await api.sendFeedback(fb.id).catch(() => {});
        setFb({ ...fb, sent: true });
        onClientChanged?.();
      }
    } catch {
      toast.push("No se pudo preparar el envío", "error");
    }
  }

  /** Guarda la edición de los cambios aplicados (persisten en portal y PDF,
   *  que leen applied_adjustments del propio plan). */
  async function saveAdjustments(appliedBlock: { period_index: number; items: any[] }) {
    if (!plan || !adjDraft || savingAdj) return;
    setSavingAdj(true);
    try {
      const items = adjDraft.map((d) =>
        d.orig.detail != null
          ? { ...d.orig, detail: d.main, reason: d.reason }
          : { ...d.orig, change: d.main, reason: d.reason },
      );
      const nutrition = { ...plan.nutrition, applied_adjustments: { ...appliedBlock, items } };
      await api.updatePlan(plan.id, { nutrition_json: nutrition });
      setPlan({ ...plan, nutrition });
      setAdjDraft(null);
      // Estos cambios también salen en el PDF ("Novedades de tu plan"):
      // el descargado antes queda antiguo.
      setNeedsDownload(true);
      toast.push("Cambios de la revisión actualizados");
    } catch {
      toast.push("No se pudieron guardar los cambios", "error");
    } finally {
      setSavingAdj(false);
    }
  }

  async function generate() {
    if (generating) return;
    setGenerating(true);
    setMissing(null);
    try {
      const p = await api.generatePlan(client.id, plan?.month_index ?? 1);
      setPlan(normalize(p));
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      setNeedsDownload(false); // versión nueva: el aviso de re-descarga ya no aplica
      onClientChanged?.(); // resincroniza sidebar (Dieta), badges y carpetas
      toast.push("Planificación generada y ACTIVA — revísala y envíasela por WhatsApp");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push([detail?.message ?? e?.message ?? "No se pudo generar el plan", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setGenerating(false);
    }
  }

  async function adapt() {
    if (generating) return;
    setGenerating(true);
    try {
      const r = await api.adaptPlan(client.id);
      const plans = await api.listPlans(client.id);
      setAllPlans(plans);
      const full = plans.find((pl) => pl.id === r.id) ?? plans[0]; // listPlans → más reciente primero
      if (full) setPlan(normalize(full));
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      setNeedsDownload(false); // versión nueva activa: el aviso de la edición anterior caduca
      onClientChanged?.(); // resincroniza sidebar (Dieta) y estados
      toast.push(`Plan adaptado y ACTIVO (v${r.version}): portal y PDF ya muestran la versión nueva.`);
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo adaptar el plan", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setGenerating(false);
    }
  }

  /** Solo para BORRADORES ANTIGUOS (de antes de la activación automática):
   *  los planes nuevos quedan activos al generarse o adaptarse. */
  async function activateLegacy() {
    if (!plan || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(plan.id);
      setPlan({ ...plan, status: "published" });
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      onClientChanged?.(); // el sidebar (Dieta) pasa a mostrar este plan
      toast.push("Planificación activada: el portal y el PDF ya muestran esta versión");
    } catch {
      toast.push("No se pudo activar", "error");
    } finally {
      setPublishing(false);
    }
  }

  function downloadPdf() {
    if (!plan) return;
    fetch(api.planDocumentUrl(plan.id), { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `plan_${client.full_name.replace(/\s+/g, "_").toLowerCase()}_mes${plan.month_index}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        setNeedsDownload(false); // ya tiene la versión actualizada
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  if (loading) {
    return (
      <div className="card flex items-center justify-center gap-2 p-8 text-sm text-zinc-500">
        <Spinner /> Cargando planificación…
      </div>
    );
  }

  // ---------- Sin plan generado todavía ----------
  if (!plan) {
    return (
      <div className="card p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl p-2.5" style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)" }}>
            <Sparkles size={20} style={{ color: "var(--brand-accent)" }} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-semibold text-zinc-100">Planificación mensual</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Genera el plan de dieta y entrenamiento con IA a partir de los datos de la
              anamnesis. Queda ACTIVO al momento: revísalo, edítalo si quieres y envíaselo
              por WhatsApp.
            </p>

            {missing && (
              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "rgba(154,107,21,0.45)", background: "rgba(154,107,21,0.09)" }}>
                <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <AlertTriangle size={15} /> Faltan datos en la anamnesis
                </div>
                <p className="mt-1 text-xs text-zinc-400">
                  Completa estos campos en la pestaña <b>Anamnesis</b> antes de generar:
                </p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {missing.map((m) => (
                    <li key={m} className="rounded-md px-2 py-0.5 text-xs" style={{ background: "rgba(154,107,21,0.14)", color: "#9A6B15" }}>
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button onClick={generate} disabled={generating} className="btn btn-primary mt-4">
              <Sparkles size={16} />
              {generating ? "Generando… (puede tardar 1-2 min)" : "Generar planificación"}
            </button>
            {generating && (
              <p className="mt-2 text-xs text-zinc-500">
                La IA está creando el plan (núcleo, comidas y contenido educativo). No cierres la página.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------- Modo edición ----------
  if (editing) {
    // Peso de referencia para proteína/grasa por kg: el último cierre
    // quincenal (peso real actual) o, si no hay, el peso inicial.
    const lastClosing = periods
      .filter((p: any) => p.closing_weight_kg != null)
      .reduce<any>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
    return (
      <ClientPlanEditor
        plan={plan}
        exMap={exMap}
        client={client}
        refWeightKg={lastClosing?.closing_weight_kg ?? client.start_weight_kg ?? null}
        onSaved={(p) => {
          setPlan(p);
          setEditing(false);
          // El PDF descargado antes ya NO refleja esta edición: avisar hasta
          // que el coach lo vuelva a descargar (o lo reenvíe por WhatsApp).
          setNeedsDownload(true);
          toast.push("Cambios guardados — descarga el PDF de nuevo para el cliente", "error");
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  // ---------- Plan generado / guardado: vista completa ----------
  const nut = plan.nutrition ?? {};
  const tr = plan.training ?? {};
  const macros = nut.macros ?? {};
  // % de cada macro sobre las calorías objetivo (para verlo junto a los gramos)
  const mp = macroPct(macros, nut.target_kcal ?? 0);
  const mpTotalOff = (nut.target_kcal ?? 0) > 0 && Math.abs(mp.total - 100) > MACRO_TOTAL_TOLERANCE;
  const exName = (id: number) => exMap[id] ?? `Ejercicio #${id}`;
  // El período abierto puede seguir anclado al plan anterior (adaptación a
  // mitad de ciclo): el seguimiento activo es el período ABIERTO, sea del plan
  // que sea; el portal ya enseña siempre la última versión publicada.
  const currentPeriod = periods.find((p) => p.status === "open") ?? periods.find((p) => p.plan_id === plan.id);

  // Última revisión quincenal analizada + estado de la adaptación:
  // - Si este plan aún NO está adaptado a ella → tarjeta de PROPUESTA (cambios
  //   y porqués, desplegados) con el botón "Adaptar" dentro.
  // - Si ya está adaptado → tarjeta de CAMBIOS APLICADOS (antes→después).
  const review = periods
    .filter((p) => p.status === "analyzed")
    .reduce<(typeof periods)[number] | null>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
  const appliedBlock: { period_index: number; items: { area: string; change: string; reason: string; applied: boolean; detail: string | null }[] } | null =
    nut.applied_adjustments ?? null;
  const alreadyAdapted = review != null && appliedBlock?.period_index === review.period_index;

  return (
    <div className="space-y-4">
      {/* Cabecera con acciones */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-zinc-100">
                Planificación · {planMonthLabel(plan.published_at ?? plan.created_at)}
              </h3>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={{ background: "color-mix(in srgb, var(--brand-accent-2) 14%, transparent)", color: "var(--brand-accent-2)" }}
              >
                Mes {plan.month_index} de asesoría
              </span>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={
                  plan.status === "published"
                    ? { background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" }
                    : { background: "rgba(38,33,26,0.08)", color: "#7A7060" }
                }
              >
                {plan.status === "published" ? "Activa" : "Borrador antiguo"} · v{plan.version}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-zinc-500">
              La planificación queda ACTIVA al generarla o adaptarla: revísala, edítala si
              quieres y envíasela por WhatsApp.
            </p>
          </div>
          {/* Acciones: en móvil ocupan todo el ancho (2 columnas) sin cortarse;
              en escritorio van en fila. */}
          <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
            <button onClick={() => setEditing(true)} className="btn btn-ghost">
              <Pencil size={15} /> Editar
            </button>
            <button onClick={downloadPdf} className="btn btn-ghost">
              <Download size={15} /> Descargar PDF
            </button>
            {plan.status === "published" && (
              <button onClick={sendPlanWhatsApp} className={`${fb ? "btn btn-ghost" : "btn btn-primary"} col-span-2 sm:col-span-1`}>
                <MessageCircle size={15} /> Enviar plan por WhatsApp
              </button>
            )}
            {plan.status === "published" && fb && (
              <button onClick={sendPlanAndFeedbackWhatsApp} className="btn btn-primary col-span-2 sm:col-span-1">
                <MessageCircle size={15} /> Enviar plan + feedback
              </button>
            )}
            {plan.status !== "published" && (
              <button onClick={activateLegacy} disabled={publishing} className="btn btn-primary col-span-2 sm:col-span-1">
                <Send size={15} /> {publishing ? "Activando…" : "Activar"}
              </button>
            )}
          </div>
        </div>

        {/* Seguimiento AUTÓNOMO: el período de 14 días se abre al activarse el
            plan y se renueva solo tras cada feedback — nada manual. */}
        {plan.status === "published" && (
          // Azul de marca: información del ciclo (estructura), no una acción
          <div
            className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border p-3"
            style={{
              background: "color-mix(in srgb, var(--brand-accent-2) 6%, transparent)",
              borderColor: "color-mix(in srgb, var(--brand-accent-2) 25%, transparent)",
            }}
          >
            <CalendarDays size={14} style={{ color: "var(--brand-accent-2)" }} />
            {currentPeriod ? (
              <span className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
                Seguimiento activo · {currentPeriod.starts_on} → {currentPeriod.ends_on}
                <span className="rounded-full px-2 py-0.5 font-semibold" style={{ background: "color-mix(in srgb, var(--brand-accent-2) 15%, transparent)", color: "var(--brand-accent-2)" }}>
                  {currentPeriod.status === "open" ? "abierto" : currentPeriod.status === "closed" ? "cerrado" : "analizado"}
                </span>
                <span className="text-zinc-500">se renueva solo tras cada feedback</span>
              </span>
            ) : (
              <span className="text-xs text-zinc-500">
                El seguimiento se activa solo: al enviar el feedback (o al entrar el cliente en su
                portal) se abre su período de 14 días.
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tras editar: el PDF que se descargó antes queda ANTIGUO — recordatorio
          claro hasta que se vuelva a descargar (la edición ya está guardada). */}
      {needsDownload && (
        <div
          className="card flex flex-wrap items-center justify-between gap-3 border p-4"
          style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 8%, transparent)" }}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent)" }} />
            <p className="text-sm text-zinc-300">
              <b className="text-zinc-100">Planificación editada y guardada.</b> El PDF descargado
              antes ya no vale: descárgalo de nuevo (o reenvía el enlace por WhatsApp) para que el
              cliente reciba la versión actualizada.
            </p>
          </div>
          <button onClick={downloadPdf} className="btn btn-primary shrink-0">
            <Download size={15} /> Descargar PDF actualizado
          </button>
        </div>
      )}

      {/* ETAPA DEL OBJETIVO: a los 45 días la web sugiere valorarlo. Análisis
          automático profesional, mantener (pospone) o cambiar y regenerar TODO. */}
      <GoalStageCard
        client={client}
        currentMonth={plan.month_index}
        onClientChanged={onClientChanged}
        onRegenerated={async () => {
          const plans = await api.listPlans(client.id).catch(() => null);
          if (plans) {
            setAllPlans(plans);
            if (plans.length) setPlan(normalize(plans[0]));
          }
          setPeriods(await api.listPeriods(client.id).catch(() => periods));
        }}
      />

      {/* Cambios PROPUESTOS por la última revisión quincenal: se ven ANTES de
          adaptar (qué cambia y por qué, dieta y entreno) y el botón va dentro. */}
      {review?.plan_adjustments?.length && !alreadyAdapted ? (
        <details open className="card p-5" style={{ borderColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)" }}>
          <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
            Cambios propuestos por la revisión #{review.period_index}
            <span className="ml-2 text-xs font-normal text-zinc-500">
              {review.plan_adjustments.length} ajustes · dieta y entrenamiento
            </span>
          </summary>
          <div className="mt-3 space-y-2">
            {review.plan_adjustments.map((a, i) => (
              <AdjustmentRow key={i} area={a.area} main={a.change} reason={a.reason} />
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }}>
            <p className="text-xs text-zinc-500">
              Al adaptar, la versión nueva queda <b className="text-zinc-300">ACTIVA al momento</b> (portal y
              PDF actualizados), con calorías, macros, comidas y gramos reescalados en bloque.
              Puedes editarla después y enviarla por WhatsApp.
            </p>
            <button onClick={adapt} disabled={generating} className="btn btn-primary">
              {generating ? "Adaptando…" : `Adaptar a la revisión #${review.period_index}`}
            </button>
          </div>
        </details>
      ) : null}

      {/* Cambios APLICADOS en esta versión (tras adaptar): antes→después + porqué.
          Queda visible también una vez publicado, como registro de la versión, y
          es EDITABLE por si el coach quiere matizar el texto o quitar un ajuste. */}
      {appliedBlock?.items?.length ? (
        <details open={plan.status !== "published"} className="card p-5">
          <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 text-sm font-semibold text-zinc-100">
            <span>
              Cambios aplicados en esta versión
              <span className="ml-2 text-xs font-normal text-zinc-500">revisión #{appliedBlock.period_index}</span>
            </span>
            {adjDraft === null && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  setAdjDraft(appliedBlock.items.map((it) => ({ area: it.area, main: it.detail ?? it.change, reason: it.reason, orig: it })));
                }}
                className="flex items-center gap-1 text-xs font-normal text-zinc-400 hover:text-zinc-200"
              >
                <Pencil size={13} /> Editar cambios
              </button>
            )}
          </summary>

          {adjDraft === null ? (
            <div className="mt-3 space-y-2">
              {appliedBlock.items.map((it, i) => (
                <AdjustmentRow
                  key={i}
                  area={it.area}
                  main={it.detail ?? it.change}
                  secondary={it.detail ? it.change : undefined}
                  reason={it.reason}
                />
              ))}
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {adjDraft.map((d, i) => (
                <div key={i} className="space-y-1.5 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
                  <div className="flex items-center justify-between gap-2">
                    <AreaChip area={d.area} />
                    <button
                      onClick={() => setAdjDraft(adjDraft.filter((_, j) => j !== i))}
                      aria-label="Quitar este cambio"
                      className="p-1 text-zinc-500 hover:text-zinc-200"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <input
                    value={d.main}
                    onChange={(e) => setAdjDraft(adjDraft.map((x, j) => (j === i ? { ...x, main: e.target.value } : x)))}
                    className="input w-full text-sm"
                    placeholder="Cambio"
                    aria-label="Cambio"
                  />
                  <textarea
                    value={d.reason}
                    onChange={(e) => setAdjDraft(adjDraft.map((x, j) => (j === i ? { ...x, reason: e.target.value } : x)))}
                    rows={2}
                    className="input w-full resize-y text-xs"
                    placeholder="Por qué"
                    aria-label="Por qué"
                  />
                </div>
              ))}
              <div className="flex justify-end gap-2 pt-1">
                <button onClick={() => setAdjDraft(null)} className="btn btn-ghost">
                  <X size={14} /> Cancelar
                </button>
                <button onClick={() => saveAdjustments(appliedBlock)} disabled={savingAdj} className="btn btn-primary">
                  <Save size={14} /> {savingAdj ? "Guardando…" : "Guardar cambios"}
                </button>
              </div>
            </div>
          )}

          {plan.status !== "published" && adjDraft === null && (
            <p className="mt-3 border-t pt-3 text-xs text-zinc-500" style={{ borderColor: "var(--line)" }}>
              Este borrador es de una versión antigua: revísalo y pulsa <b className="text-zinc-300">Activar</b>
              para que el portal y el PDF lo muestren.
            </p>
          )}
        </details>
      ) : null}

      {/* Nutrición */}
      <div className="card p-5">
        <SectionTitle icon={Utensils} title="Nutrición" />
        {/* Cálculo aplicado, directo: déficit/superávit sobre el TDEE */}
        {nut.tdee_kcal ? (
          <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <span
              className="rounded-full px-2.5 py-1 font-semibold"
              style={{ background: "color-mix(in srgb, var(--brand-accent) 14%, transparent)", color: "var(--brand-accent)" }}
            >
              {deficitLabel(nut.tdee_kcal, nut.target_kcal ?? 0)}
            </span>
            <span className="text-zinc-500">sobre tu gasto (TDEE {Math.round(nut.tdee_kcal)} kcal)</span>
            {client.goal_type && <span className="text-zinc-500">· {GOAL_LABEL[client.goal_type]}</span>}
          </div>
        ) : null}
        <div className="grid grid-cols-4 gap-2">
          <Stat label="Calorías" value={`${Math.round(nut.target_kcal ?? 0)}`} />
          <Stat label="Proteína" value={`${Math.round(macros.protein_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.protein}%` : undefined} />
          <Stat label="Carbohid." value={`${Math.round(macros.carbs_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.carbs}%` : undefined} />
          <Stat label="Grasas" value={`${Math.round(macros.fat_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.fat}%` : undefined} />
        </div>
        {mpTotalOff && (
          <p className="mt-1.5 text-xs" style={{ color: "#9A6B15" }}>
            Los macros suman {mp.total}% de las calorías objetivo — al editar, usa "Cuadrar a 100%".
          </p>
        )}
        {nut.tdee_kcal != null && (
          <p className="mt-2 text-xs text-zinc-500">
            {Array.isArray(nut.meals) && nut.meals.length > 0 ? `${nut.meals.length} comidas/día` : ""}
          </p>
        )}

        {/* Objetivos por comida: TABLA clara con los macros correctos */}
        {Array.isArray(nut.meals) && nut.meals.length > 0 && (
          <div className="mt-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Reparto por comida</h5>
            <div className="overflow-x-auto rounded-lg border" style={{ borderColor: "var(--line)" }}>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-zinc-500" style={{ background: "var(--surface-raised)" }}>
                    <th className="px-3 py-1.5 font-medium">Comida</th>
                    <th className="px-3 py-1.5 text-right font-medium">kcal</th>
                    <th className="px-3 py-1.5 text-right font-medium">P</th>
                    <th className="px-3 py-1.5 text-right font-medium">C</th>
                    <th className="px-3 py-1.5 text-right font-medium">G</th>
                  </tr>
                </thead>
                <tbody>
                  {nut.meals.map((m: any, i: number) => (
                    <tr key={m.slot ?? i} className="border-t text-zinc-300" style={{ borderColor: "var(--line)" }}>
                      <td className="px-3 py-1.5">{m.time ? `${m.time} · ` : ""}{m.name}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(m.target?.kcal ?? 0)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(m.target?.protein_g ?? 0)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(m.target?.carbs_g ?? 0)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(m.target?.fat_g ?? 0)}</td>
                    </tr>
                  ))}
                  {/* "Total día" = suma REAL de las filas de comidas (siempre cuadra con
                      lo que se ve arriba, tanto en el plan generado como tras editar). */}
                  <tr className="border-t font-semibold text-zinc-200" style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}>
                    <td className="px-3 py-1.5">Total día</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(nut.meals.reduce((s: number, m: any) => s + (m.target?.kcal ?? 0), 0))}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(nut.meals.reduce((s: number, m: any) => s + (m.target?.protein_g ?? 0), 0))}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(nut.meals.reduce((s: number, m: any) => s + (m.target?.carbs_g ?? 0), 0))}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{Math.round(nut.meals.reduce((s: number, m: any) => s + (m.target?.fat_g ?? 0), 0))}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {nut.rationale && (
          <MemoDetails
            memoKey={`nut-why:${client.id}`}
            className="mt-3"
            summaryClassName="py-1"
            summary={<span className="text-sm font-medium text-zinc-400">Justificación de la nutrición</span>}
          >
            <RationaleView text={nut.rationale} />
          </MemoDetails>
        )}
        {nut.refeed_or_break && (
          <div className="mt-2 rounded-lg border-l-2 px-3 py-2 text-xs text-zinc-400" style={{ background: "var(--surface-raised)", borderLeftColor: "var(--brand-accent-2)" }}>
            <b className="text-zinc-300">Recarga / descanso:</b> {nut.refeed_or_break}
          </div>
        )}

        {Array.isArray(nut.flexibility_rules) && nut.flexibility_rules.length > 0 && (
          <MemoDetails
            memoKey={`nut-flex:${client.id}`}
            className="mt-3"
            summaryClassName="py-1"
            summary={
              <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Reglas de flexibilidad · {nut.flexibility_rules.length}
              </span>
            }
          >
            <div className="mt-1.5 grid gap-1.5 sm:grid-cols-2">
              {nut.flexibility_rules.map((r: string, i: number) => <FlexRule key={i} text={r} />)}
            </div>
          </MemoDetails>
        )}
      </div>

      {/* El BANCO DE COMIDAS ya no se muestra aquí (el coach no lo necesita en
          pantalla): va completo en el PDF que recibe el cliente. */}

      {/* Entrenamiento — azul de marca (como sus chips de ajustes) */}
      <div className="card p-5">
        <SectionTitle icon={Dumbbell} title={`Entrenamiento${tr.split_name ? ` · ${tr.split_name}` : ""}`} accent="var(--brand-accent-2)" />
        {tr.split_rationale && (
          <details className="mb-3 text-sm">
            <summary className="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">Sobre esta estructura</summary>
            <p className="mt-2 text-zinc-400">{tr.split_rationale}</p>
          </details>
        )}

        {Array.isArray(tr.weekly_progression) && tr.weekly_progression.length > 0 && (
          <div className="mb-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Progresión semanal</h5>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {tr.weekly_progression.map((w: any) => (
                <div
                  key={w.week}
                  className="rounded-lg border-l-2 p-2.5 text-xs"
                  style={{ background: "var(--surface-raised)", borderColor: "var(--brand-accent-2)" }}
                >
                  <div className="font-semibold text-zinc-200">
                    <span style={{ color: "var(--brand-accent-2)" }}>Sem {w.week}</span> · {w.intent}
                  </div>
                  <div className="text-zinc-500">Carga {w.load_pct}% · RIR {w.rir_target}</div>
                  {w.volume_note && <div className="mt-0.5 text-zinc-500">{w.volume_note}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {(tr.sessions ?? []).map((s: any, i: number) => (
            <MemoDetails
              key={i}
              memoKey={`tr-day:${client.id}:${i}`}
              className="rounded-lg p-3"
              style={{ background: "var(--surface-raised)" }}
              summary={
                <span className="flex flex-wrap items-center gap-2 text-sm font-medium text-zinc-200">
                  <span
                    className="rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                    style={{ background: "color-mix(in srgb, var(--brand-accent-2) 15%, transparent)", color: "var(--brand-accent-2)" }}
                  >
                    {s.day}
                  </span>
                  {s.name}
                  <span className="text-xs font-normal text-zinc-500">{(s.exercises ?? []).length} ejercicios</span>
                </span>
              }
            >
              {s.warmup && <p className="mt-1 text-xs text-zinc-500"><b>Calentamiento:</b> {s.warmup}</p>}
              <div className="mt-2 space-y-1.5">
                {(s.exercises ?? []).map((ex: any, j: number) => {
                  const hasDetail = ex.progression_rule || ex.technique_cue || ex.biomech_cue;
                  return (
                    <details key={j} className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
                      <summary className="cursor-pointer">
                        <span className="font-medium text-zinc-200">{exName(ex.exercise_id)}</span>
                        <span className="ml-1 text-zinc-400">
                          · {ex.sets}×{ex.rep_range} · RIR {ex.rir} · {ex.rest_sec}s
                          {ex.tempo ? ` · tempo ${ex.tempo}` : ""}
                          {ex.start_weight_hint_kg != null ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                        </span>
                      </summary>
                      {hasDetail && (
                        <div className="mt-1.5 space-y-0.5 border-t pt-1.5 pl-1 text-zinc-500" style={{ borderColor: "var(--line)" }}>
                          {ex.progression_rule && <p><b className="text-zinc-400">Progresión:</b> {ex.progression_rule}</p>}
                          {ex.technique_cue && <p><b className="text-zinc-400">Técnica:</b> {ex.technique_cue}</p>}
                          {ex.biomech_cue && <p><b className="text-zinc-400">Biomecánica:</b> {ex.biomech_cue}</p>}
                        </div>
                      )}
                    </details>
                  );
                })}
              </div>
              {s.cooldown && <p className="mt-2 text-xs text-zinc-500"><b>Vuelta a la calma:</b> {s.cooldown}</p>}
            </MemoDetails>
          ))}
        </div>

        {tr.cardio && (
          <div className="mt-3 rounded-lg p-3 text-xs" style={{ background: "var(--surface-raised)" }}>
            <div className="flex items-center gap-1.5 font-medium text-zinc-200"><CalendarDays size={13} /> Cardio y NEAT</div>
            <p className="mt-1 text-zinc-400">Pasos diarios objetivo: {tr.cardio.daily_steps}</p>
            {(tr.cardio.sessions ?? []).map((cs: any, i: number) => (
              <p key={i} className="text-zinc-500">{cs.type?.toUpperCase()} · {cs.minutes} min × {cs.times_per_week}/sem{cs.notes ? ` · ${cs.notes}` : ""}</p>
            ))}
          </div>
        )}
        {tr.deload_instructions && (
          <p className="mt-3 text-xs text-zinc-400"><b className="text-zinc-300">Descarga (deload):</b> {tr.deload_instructions}</p>
        )}
      </div>

      {/* PUNTOS IMPORTANTES del cliente (anamnesis): lo que condiciona el plan */}
      <ImportantPointsCard client={client} />

      {/* Suplementación */}
      {Array.isArray(nut.supplements) && nut.supplements.length > 0 && (
        <div className="card p-5">
          <SectionTitle icon={Pill} title="Suplementación" />
          <div className="space-y-1.5">
            {nut.supplements.map((s: any, i: number) => (
              <div key={i} className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                <span className="font-medium text-zinc-200">{s.name}</span>
                <span className="text-zinc-500"> · {s.dose} · {s.timing}</span>
                {s.evidence_note && <p className="mt-0.5 text-zinc-500">{s.evidence_note}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ARCHIVO: planificaciones anteriores, como las revisiones — plegadas,
          con el objetivo que servían y cuánto duraron. */}
      {allPlans.length > 1 && (
        <details className="card p-5">
          <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-zinc-100">
            <Archive size={15} style={{ color: "var(--brand-accent-2)" }} />
            Planificaciones anteriores
            <span className="text-xs font-normal text-zinc-500">{allPlans.length - 1}</span>
          </summary>
          <div className="mt-3 space-y-2">
            {archivedPlans(allPlans, plan.id).map((p) => (
              <details key={p.id} className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
                <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 px-3 py-2.5 text-sm" style={{ background: "var(--surface-raised)" }}>
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-zinc-100">{p.monthLabel}</span>
                    <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium" style={{ background: "color-mix(in srgb, var(--brand-accent-2) 12%, transparent)", color: "var(--brand-accent-2)" }}>
                      Mes {p.month_index} de asesoría
                    </span>
                    <span className="text-xs text-zinc-500">
                      {GOAL_LABEL[(p.goal_type as GoalType)] ?? "objetivo no registrado"}
                      {" · "}{p.rangeLabel ? `${p.rangeLabel} · ` : ""}{p.durationLabel} · v{p.version}
                    </span>
                  </span>
                  <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "rgba(38,33,26,0.08)", color: "#7A7060" }}>
                    {p.status === "superseded" ? "sustituida" : p.status === "published" ? "publicada" : "borrador antiguo"}
                  </span>
                </summary>
                <div className="grid grid-cols-2 gap-2 px-3 py-3 text-xs text-zinc-400 sm:grid-cols-4">
                  <span>Calorías: <b className="text-zinc-200">{Math.round(p.nutrition_json?.target_kcal ?? 0)}</b></span>
                  <span>P/C/G: <b className="text-zinc-200">
                    {Math.round(p.nutrition_json?.macros?.protein_g ?? 0)}/
                    {Math.round(p.nutrition_json?.macros?.carbs_g ?? 0)}/
                    {Math.round(p.nutrition_json?.macros?.fat_g ?? 0)} g
                  </b></span>
                  <span>Split: <b className="text-zinc-200">{p.training_json?.split_name ?? "—"}</b></span>
                  <span>Sesiones: <b className="text-zinc-200">{(p.training_json?.sessions ?? []).length}</b></span>
                </div>
                {/* Por qué se adaptó o cambió esta versión */}
                {(p.whyChanged?.length || p.whyLabel) && (
                  <div className="border-t px-3 py-3 text-xs" style={{ borderColor: "var(--line)" }}>
                    <div className="mb-1 font-semibold uppercase tracking-wide text-zinc-500">Por qué se hizo / cambió</div>
                    {p.whyLabel && <p className="text-zinc-400">{p.whyLabel}</p>}
                    {(p.whyChanged ?? []).map((w: { change: string; reason: string }, i: number) => (
                      <p key={i} className="mt-1 text-zinc-400">
                        · {w.change}{w.reason ? <span className="text-zinc-500"> — {w.reason}</span> : null}
                      </p>
                    ))}
                  </div>
                )}
              </details>
            ))}
          </div>
        </details>
      )}

    </div>
  );
}

const fmtDay = (d: Date) =>
  d.toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });

/** Planes archivados (todos menos el vigente) con las fechas en que se usaron
 *  (desde su creación hasta el plan siguiente), la duración y el PORQUÉ del
 *  cambio (ajustes aplicados de la revisión o justificación del plan). */
function archivedPlans(all: any[], currentId: number): any[] {
  const asc = [...all].sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
  return asc
    .map((p, i) => {
      const from = p.created_at ? new Date(p.created_at) : null;
      const next = asc[i + 1]?.created_at ? new Date(asc[i + 1].created_at) : new Date();
      const days = from ? Math.max(1, Math.round((next.getTime() - from.getTime()) / 86400000)) : null;
      const applied = p.nutrition_json?.applied_adjustments?.items as any[] | undefined;
      const whyChanged = (applied ?? [])
        .filter((it) => it?.change || it?.detail)
        .map((it) => ({ change: it.detail ?? it.change, reason: it.reason ?? "" }));
      const rationale: string | null = p.nutrition_json?.rationale ?? null;
      const whyLabel = whyChanged.length
        ? `Adaptación a la revisión #${p.nutrition_json?.applied_adjustments?.period_index}:`
        : rationale
          ? rationale.split("\n")[0].slice(0, 180)
          : p.generated_by === "ai"
            ? "Plan generado con IA a partir de la anamnesis."
            : null;
      return {
        ...p,
        monthLabel: planMonthLabel(p.published_at ?? p.created_at),
        durationLabel: days != null ? `${days} día${days === 1 ? "" : "s"}` : "—",
        rangeLabel: from ? `${fmtDay(from)} → ${fmtDay(next)}` : null,
        whyChanged,
        whyLabel,
      };
    })
    .filter((p) => p.id !== currentId)
    .reverse(); // más reciente primero
}

/** Puntos IMPORTANTES del cliente (anamnesis) que condicionan la planificación:
 *  lesiones, salud, medicación, alergias, aversiones y objetivo en sus palabras.
 *  Lo crítico se resalta EN ROJO para que no se pase por alto (clasificador
 *  compartido en lib/clinical — mismas reglas que las Notas clínicas). */
function ImportantPointsCard({ client }: { client: ClientOut }) {
  const blocks: { label: string; lines: string[] }[] = [];
  const add = (label: string, v: string | string[] | null | undefined) => {
    const text = Array.isArray(v) ? v.filter(Boolean).join(", ") : (v ?? "").trim();
    if (text) blocks.push({ label, lines: text.split("\n").filter((l) => l.trim()) });
  };
  add("Lesiones y movilidad", client.injuries_notes);
  add("Salud (clínica y digestiva)", client.medical_notes);
  add("Medicación", client.medication_notes);
  add("Alergias e intolerancias", client.food_allergies);
  add("Alimentos que evita", client.food_dislikes);
  add("Objetivo y contexto en sus palabras", client.lifestyle_notes);
  if (!blocks.length) return null;
  const RED = "#B3261E";
  return (
    <div className="card p-5">
      <SectionTitle icon={AlertTriangle} title="Puntos importantes del cliente" />
      <p className="mb-2 text-xs text-zinc-500">
        De su anamnesis: lo que hay que respetar en dieta y entrenamiento.
        <span className="font-medium" style={{ color: RED }}> Lo crítico, en rojo.</span>
      </p>
      <div className="space-y-2">
        {blocks.map((b) => {
          const nCrit = b.lines.filter(isCriticalLine).length;
          return (
            <MemoDetails
              memoKey={`imp:${client.id}:${b.label}`}
              defaultOpen={nCrit > 0}
              className="rounded-lg border-l-2 px-3 py-2"
              style={{
                background: "var(--surface-raised)",
                borderLeftColor: nCrit > 0 ? RED : "transparent",
              }}
              summary={
                <span className="text-xs font-semibold text-zinc-300">
                  {b.label}
                  {nCrit > 0 && (
                    <span className="ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold text-white" style={{ background: RED }}>
                      {nCrit} a vigilar
                    </span>
                  )}
                </span>
              }
            >
              <div className="mt-1 space-y-0.5 text-xs">
                {b.lines.map((l, i) =>
                  isCriticalLine(l) ? (
                    <p key={i} className="font-medium" style={{ color: RED }}>{l}</p>
                  ) : (
                    <p key={i} className="text-zinc-400">{l}</p>
                  ),
                )}
              </div>
            </MemoDetails>
          );
        })}
      </div>
    </div>
  );
}

/** Etapa del objetivo: días transcurridos, análisis automático profesional,
 *  "Mantener objetivo" (pospone la alerta 45 días) y "Cambiar objetivo y
 *  regenerar la planificación" (dieta + entreno nuevos; la antigua se archiva). */
function GoalStageCard({ client, currentMonth, onClientChanged, onRegenerated }: {
  client: ClientOut;
  currentMonth: number;
  onClientChanged?: () => void;
  onRegenerated: () => Promise<void>;
}) {
  const toast = useToast();
  const days = goalDays(client);
  const due = goalReviewDue(client);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [newGoal, setNewGoal] = useState<string>("");
  const [changing, setChanging] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function generateAnalysis() {
    if (analyzing) return;
    setAnalyzing(true);
    try {
      const r = await api.goalReviewAnalysis(client.id);
      setAnalysis(r.text);
    } catch {
      toast.push("No se pudo generar el análisis", "error");
    } finally {
      setAnalyzing(false);
    }
  }

  async function keepGoal() {
    try {
      await api.snoozeGoalReview(client.id);
      toast.push("Objetivo mantenido: se volverá a valorar en 45 días");
      onClientChanged?.();
    } catch {
      toast.push("No se pudo posponer", "error");
    }
  }

  async function changeAndRegenerate() {
    if (!newGoal || changing) return;
    setChanging(true);
    try {
      await api.changeGoal(client.id, { goal_type: newGoal });
      toast.push(`Objetivo cambiado a ${GOAL_LABEL[newGoal as GoalType]}. Generando la planificación nueva…`);
      onClientChanged?.();
      await api.generatePlan(client.id, currentMonth + 1);
      await onRegenerated();
      toast.push("Planificación nueva generada y ACTIVA para el objetivo nuevo — envíasela por WhatsApp.");
      setConfirming(false);
      setNewGoal("");
      setAnalysis(null);
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo completar el cambio", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      setChanging(false);
    }
  }

  return (
    <details
      open={due != null}
      className="card p-5"
      style={due != null ? { borderColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)" } : undefined}
    >
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 text-sm font-semibold text-zinc-100">
        <span className="flex flex-wrap items-center gap-2">
          <Flag size={15} style={{ color: "var(--brand-accent-2)" }} />
          Objetivo: {client.goal_type ? GOAL_LABEL[client.goal_type] : "—"}
          {days != null && <span className="text-xs font-normal text-zinc-500">{days} días en esta etapa</span>}
          <span className="text-xs font-normal" style={{ color: "var(--brand-accent-2)" }}>· pulsa para cambiar</span>
        </span>
        {due != null && (
          <span className="rounded-full px-2 py-0.5 text-xs font-bold text-white" style={{ background: "var(--brand-accent)" }}>
            Valorar cambio de objetivo
          </span>
        )}
      </summary>

      <div className="mt-3 space-y-3">
        <p className="text-xs text-zinc-500">
          {due != null
            ? `Lleva ${due} días con este objetivo. Genera el análisis de la etapa para valorar con el cliente si toca cambiarlo, o mantenlo 45 días más.`
            : "Cambia aquí el objetivo si el cliente lo pide o la etapa lo aconseja: el análisis resume lo conseguido y las opciones."}
        </p>

        {analysis === null ? (
          <button onClick={generateAnalysis} disabled={analyzing} className="btn btn-ghost">
            <Sparkles size={14} /> {analyzing ? "Generando análisis…" : "Generar análisis de la etapa"}
          </button>
        ) : (
          <div className="rounded-lg border p-3" style={{ borderColor: "color-mix(in srgb, var(--brand-accent-2) 25%, transparent)", background: "color-mix(in srgb, var(--brand-accent-2) 5%, transparent)" }}>
            <p className="whitespace-pre-line text-sm text-zinc-300">{analysis}</p>
            <button
              onClick={() => { navigator.clipboard.writeText(analysis).catch(() => {}); toast.push("Análisis copiado"); }}
              className="mt-2 flex items-center gap-1 text-xs font-medium hover:opacity-80"
              style={{ color: "var(--brand-accent-2)" }}
            >
              <Copy size={12} /> Copiar análisis
            </button>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }}>
          <select
            value={newGoal}
            onChange={(e) => { setNewGoal(e.target.value); setConfirming(false); }}
            className="input w-auto"
            aria-label="Nuevo objetivo"
          >
            <option value="">Nuevo objetivo…</option>
            {(Object.keys(GOAL_LABEL) as GoalType[])
              .filter((g) => g !== client.goal_type)
              .map((g) => <option key={g} value={g}>{GOAL_LABEL[g]}</option>)}
          </select>
          {!confirming ? (
            <button onClick={() => setConfirming(true)} disabled={!newGoal || changing} className="btn btn-primary">
              <Sparkles size={14} /> Cambiar objetivo y regenerar plan
            </button>
          ) : (
            <button onClick={changeAndRegenerate} disabled={changing} className="btn btn-primary">
              {changing ? "Cambiando y generando… (1-2 min)" : `Confirmar: ${newGoal ? GOAL_LABEL[newGoal as GoalType] : ""} y regenerar TODO`}
            </button>
          )}
          {due != null && (
            <button onClick={keepGoal} disabled={changing} className="btn btn-ghost">
              Mantener objetivo actual
            </button>
          )}
        </div>
        {confirming && !changing && (
          <p className="text-xs text-zinc-500">
            Se cambiará el objetivo, se generará una planificación completamente nueva (dieta y
            entrenamiento) con todo su historial en cuenta, y la actual quedará archivada abajo
            con su objetivo y duración.
          </p>
        )}
      </div>
    </details>
  );
}

/** Color fijo por ÁREA del ajuste (identidad estable: el mismo área siempre
 *  lleva el mismo color, en tonos oscuros legibles sobre el fondo crema). */
const AREA_CHIPS: { match: RegExp; label: string; bg: string; fg: string }[] = [
  { match: /diet|nutri|calor|comid/i, label: "Dieta", bg: "color-mix(in srgb, var(--brand-accent) 18%, transparent)", fg: "var(--brand-accent)" },
  { match: /entren|train|fuerza|pesas/i, label: "Entreno", bg: "color-mix(in srgb, var(--brand-accent-2, #2E5E8C) 22%, transparent)", fg: "var(--brand-accent-2, #3D6E9E)" },
  { match: /sue|sleep|descans/i, label: "Sueño", bg: "rgba(107,90,168,0.15)", fg: "#63519E" },
  { match: /activ|pasos|neat|cardio|steps/i, label: "Actividad diaria", bg: "rgba(71,124,78,0.15)", fg: "#3F7446" },
  { match: /hidrat|agua|water/i, label: "Hidratación", bg: "rgba(46,126,138,0.15)", fg: "#28707C" },
  { match: /suplement/i, label: "Suplementos", bg: "rgba(154,107,21,0.15)", fg: "#8A6212" },
];

function areaChip(area: string) {
  const hit = AREA_CHIPS.find((c) => c.match.test(area));
  return hit ?? { label: area || "General", bg: "rgba(38,33,26,0.08)", fg: "#7A7060" };
}

function AreaChip({ area }: { area: string }) {
  const c = areaChip(area);
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.fg }}
    >
      {c.label}
    </span>
  );
}

/** Fila de un ajuste de la revisión: chip de área + cambio + porqué. */
function AdjustmentRow({ area, main, secondary, reason }: {
  area: string; main: string; secondary?: string; reason: string;
}) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
      <div className="flex flex-wrap items-center gap-2">
        <AreaChip area={area} />
        <span className="text-sm font-medium text-zinc-100">{main}</span>
      </div>
      {secondary && <p className="mt-0.5 text-xs text-zinc-500">{secondary}</p>}
      {reason && <p className="mt-1 text-xs text-zinc-400"><b className="text-zinc-500">Por qué:</b> {reason}</p>}
    </div>
  );
}

function SectionTitle({ icon: Icon, title, accent }: { icon: typeof Utensils; title: string; accent?: string }) {
  const c = accent ?? "var(--brand-accent)";
  return (
    <div className="mb-3 flex items-center gap-2.5">
      {/* Icono en chip tintado: da jerarquía y quita el aspecto plano */}
      <span
        className="flex h-7 w-7 items-center justify-center rounded-lg"
        style={{ background: `color-mix(in srgb, ${c} 14%, transparent)`, boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${c} 22%, transparent)` }}
      >
        <Icon size={15} style={{ color: c }} />
      </span>
      <h4 className="text-sm font-semibold text-zinc-200">{title}</h4>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div
      className="rounded-xl p-3 text-center"
      style={{
        background: "linear-gradient(180deg, #fffefb, var(--surface-raised))",
        boxShadow: "var(--hairline-top), 0 1px 3px rgba(38,33,26,0.05)",
        border: "1px solid var(--line)",
      }}
    >
      <div className="text-lg font-bold tabular-nums" style={{ color: "var(--brand-accent)" }}>{value}</div>
      <div className="mt-0.5 flex items-center justify-center gap-1.5 text-xs text-zinc-500">
        <span>{label}</span>
        {sub && (
          <span className="rounded px-1 font-semibold tabular-nums" style={{ background: "color-mix(in srgb, var(--brand-accent-2) 12%, transparent)", color: "var(--brand-accent-2)" }}>
            {sub}
          </span>
        )}
      </div>
    </div>
  );
}

/** Justificación de la nutrición ESTRUCTURADA: si el texto viene de una
 *  adaptación ("- [Área] cambio — porqué"), se renderiza por puntos con el chip
 *  de color de cada área; si no, texto normal. Se entiende de un vistazo. */
function RationaleView({ text }: { text: string }) {
  // Formato de ADAPTACIÓN ("- [Área] cambio — porqué"): chips de color.
  const idx = text.indexOf("- [");
  if (idx !== -1) {
    const header = text.slice(0, idx).trim().replace(/:$/, "");
    const items = [...text.slice(idx).matchAll(/- \[([^\]]+)\]\s*([\s\S]*?)(?=\n?\s*- \[|$)/g)].map((m) => {
      const [main, ...rest] = m[2].split(" — ");
      return { area: m[1], main: main.trim(), reason: rest.join(" — ").trim() };
    });
    return (
      <div className="mt-2 space-y-2">
        {header && <p className="text-xs font-semibold text-zinc-300">{header}</p>}
        {items.map((it, i) => <AdjustmentRow key={i} area={it.area} main={it.main} reason={it.reason} />)}
      </div>
    );
  }
  // Prosa de un plan nuevo: se separa en frases-punto para leer rápido.
  const points = text
    .split(/\n+|(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])/)
    .map((s) => s.replace(/^[-•*]\s*/, "").trim())
    .filter(Boolean);
  if (points.length <= 1) return <p className="mt-2 whitespace-pre-line text-sm text-zinc-400">{text}</p>;
  return (
    <ul className="mt-2 space-y-1 text-sm text-zinc-400">
      {points.map((p, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full" style={{ background: "var(--brand-accent-2)" }} />
          <span>{p}</span>
        </li>
      ))}
    </ul>
  );
}

/** Regla de flexibilidad como tarjeta: si tiene "tema: detalle", el tema va
 *  en negrita para escanear rápido. */
function FlexRule({ text }: { text: string }) {
  const m = text.match(/^([^:]{2,32}):\s*(.+)$/s);
  return (
    <div className="rounded-lg border-l-2 px-3 py-2 text-xs text-zinc-400" style={{ background: "var(--surface-raised)", borderLeftColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)" }}>
      {m ? (<><b className="text-zinc-200">{m[1]}:</b> {m[2]}</>) : text}
    </div>
  );
}
