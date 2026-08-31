import { useEffect, useRef, useState } from "react";
import { Sparkles, ChevronRight, Download, Send, AlertTriangle, Dumbbell, Utensils, Pill, CalendarDays, MessageCircle, Mail, MoreHorizontal, Pencil, PlayCircle, Save, X, Flag, Copy, Archive, FileText, FileUp } from "lucide-react";
import { grupo } from "../lib/accordion";
import { useDismiss, useModalFocus } from "../lib/useDismiss";
import { ancla, hrefCliente } from "../lib/anchors";
import { copiarConAviso } from "../lib/clipboard";
import { pin, pinId, syncScope } from "../lib/pins";
import { api, getToken } from "../lib/api";
import type { PlanSummary } from "../lib/api";
import { manualUpdateMessage, openWhatsApp, planAndFeedbackMessage, planMessage, waPhone, waUrl } from "../lib/whatsapp";
import { pkg } from "../lib/packages";
import { CANONICAL_MEALS, mealKeysFromNames } from "../lib/meals";
import { GOAL_LABEL, goalDays, goalReviewDue, planMonthLabel } from "../lib/format";
import { deficitLabel, macroPct, MACRO_TOTAL_TOLERANCE } from "../lib/nutritionTargets";
import { isCriticalLine } from "../lib/clinical";
import { ExpandableArea, ProseClamp, Spinner, useToast } from "./ui";
import type { Destino } from "../lib/findings";
import { agrupar, resumirDetalle, resumenCorto, toAviso, traducirFlags } from "../lib/findings";
import { MemoDetails } from "./MemoDetails";
import { ClientPlanEditor } from "./ClientPlanEditor";
import type { ClientOut, ExerciseOut, GoalType } from "../types";

interface PlanReview {
  color?: "verde" | "ambar" | "rojo" | null;
  icp?: number | null;
  escalated?: boolean;
  findings?: { severity: string; description: string; title?: string; action?: string; correccion_propuesta?: string }[];
  // Revisores IA caídos (no_ejecutado): la revisión está DEGRADADA y el coach
  // debe saberlo (antes moría en el JSON sin llegar a la interfaz).
  degraded_reviewers?: string[];
}

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  review?: PlanReview | null;
  nutrition: any;
  training: any;
  education: any;
  created_at?: string | null;
  published_at?: string | null;
}

/** El plan VIGENTE de la lista: el PUBLICADO si existe y, si no, el más nuevo
 *  por id. El backend ordena por (mes DESC, versión DESC), así que `plans[0]`
 *  podía ser un plan SUSTITUIDO de un mes posterior generado y descartado —
 *  el coach veía (y enviaba) una versión que el cliente no tiene (auditoría). */
function vigente(plans: PlanSummary[]): PlanSummary | null {
  if (!plans.length) return null;
  return plans.find((p) => p.status === "published")
    ?? [...plans].sort((a, b) => (b.id ?? 0) - (a.id ?? 0))[0];
}

/** Normaliza un plan venga de generatePlan (nutrition/...) o de listPlans (nutrition_json/...). */
function normalize(p: any): PlanData {
  return {
    id: p.id,
    month_index: p.month_index,
    version: p.version,
    status: p.status,
    guardrail_flags: p.guardrail_flags ?? [],
    review: p.review ?? p.review_json ?? null,
    nutrition: p.nutrition ?? p.nutrition_json ?? null,
    training: p.training ?? p.training_json ?? null,
    education: p.education ?? p.education_json ?? null,
    created_at: p.created_at ?? null,
    published_at: p.published_at ?? null,
  };
}

// GENERACIONES EN VUELO por cliente (a nivel de módulo): tardan ~1 minuto y el
// componente se REMONTA al cambiar de pestaña — sin esto, al volver se perdía
// el "Generando…" (parecía que no pasaba nada y se podía relanzar → doble
// gasto de créditos).
const enVuelo = new Map<number, Promise<unknown>>();

/**
 * Planificación: genera el plan mensual con IA a partir de la anamnesis, lo
 * PERSISTE (al volver a la pestaña se recarga el último plan guardado), muestra
 * la info del plan (nutrición, entrenamiento, puntos del cliente, suplementos)
 * y queda ACTIVO al generarse/adaptarse/editarse — sin paso de publicar.
 */
export function ClientPlanPanel({ client, onClientChanged, onEditingChange, onGoTab }: {
  client: ClientOut; onClientChanged?: () => void;
  // Avisa al perfil de que el EDITOR está abierto (guard de "cambios sin
  // guardar" al cambiar de pestaña o cerrar el navegador).
  onEditingChange?: (editing: boolean) => void;
  /** Saltar a otra pestaña del perfil (los avisos llevan a donde se actúa). */
  onGoTab?: (tab: string) => void;
}) {
  const toast = useToast();
  // Paquete del cliente: Start es solo nutrición (sin entreno) y la entrega va
  // por email; Full por email; Pro por WhatsApp.
  const info = pkg(client.package_tier);
  const hasTraining = info.hasTraining;
  const hasNutrition = info.hasNutrition;
  const byEmail = info.delivery === "email";
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [exMap, setExMap] = useState<Record<number, string>>({});
  // Vídeo de cada ejercicio (biblioteca): botón directo en la rutina.
  const [exVideo, setExVideo] = useState<Record<number, string>>({});
  // La biblioteca ENTERA, tal cual llegó: se le pasa al editor para que no la
  // vuelva a descargar (son ~100 KB y ya está aquí desde el montaje).
  const [exList, setExList] = useState<ExerciseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(() => enVuelo.has(client.id));
  const [publishing, setPublishing] = useState(false);
  const [editing, setEditing] = useState(false);
  // El perfil se entera de que el editor está abierto (guard de navegación).
  useEffect(() => { onEditingChange?.(editing); }, [editing, onEditingChange]);
  // Bloque desde el que se pulsó "Editar": el editor abre enfocado en él.
  const [editFocus, setEditFocus] = useState<"nutrition" | "training" | "supplements" | null>(null);
  const [sendingUpd, setSendingUpd] = useState(false);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [periods, setPeriods] = useState<{
    id: number; period_index: number; plan_id: number | null; starts_on: string; ends_on: string; status: string;
    feedback_id?: number | null;
    plan_adjustments?: { area: string; change: string; reason: string }[] | null;
    // Decisión de la revisión automática (§8): "Adaptar" debe ofrecerse aunque
    // la IA no propusiera ajustes de texto (p. ej. solo un diet break).
    biweekly_decision?: { action?: string; kcal_delta_pct?: number; rationale?: string } | null;
  }[]>([]);
  // Todas las versiones, RESUMIDAS (archivo de planificaciones anteriores por
  // objetivo). El contenido completo solo se pide de la versión que se enseña:
  // esta lista se repide tras cada acción y con los cuatro JSONB de cada
  // versión un cliente con un año de asesoría arrastraba megas por cada clic.
  const [allPlans, setAllPlans] = useState<PlanSummary[]>([]);
  // Último feedback generado (para poder enviarlo junto al plan por WhatsApp).
  const [fb, setFb] = useState<{ id: number; content: any; sent: boolean } | null>(null);
  // Edición de los "Cambios aplicados" tras adaptar: texto/porqué o quitar filas.
  const [adjDraft, setAdjDraft] = useState<{ area: string; main: string; reason: string; orig: any }[] | null>(null);
  const [savingAdj, setSavingAdj] = useState(false);
  // Tras EDITAR el plan: recordatorio de descargar el PDF de nuevo (la versión
  // editada ya está guardada; el PDF descargado antes se queda antiguo).
  const [needsDownload, setNeedsDownload] = useState(false);
  // Tras descargar el Word editable, la VUELTA ("Subir Word editado") sale a
  // primera fila — antes vivía solo dentro de «Más» y costaba encontrarla.
  const [wordDescargado, setWordDescargado] = useState(false);
  // Historial de versiones (§4): instantáneas guardadas antes de cada edición,
  // restaurables si un cambio salió mal.
  const [histOpen, setHistOpen] = useState(false);
  const [hist, setHist] = useState<Awaited<ReturnType<typeof api.planHistory>> | null>(null);
  const [reverting, setReverting] = useState<number | null>(null);

  // Al montar O AL CAMBIAR DE CLIENTE: carga el último plan + ejercicios +
  // períodos. El estado se RESETEA primero — sin esto, al saltar del cliente A
  // al B (alerta/panel con la misma pestaña abierta) B heredaba el plan, el
  // feedback y el editor abierto de A (incluso el WhatsApp salía con el
  // feedback de A).
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setPlan(null);
    setFb(null);
    setNeedsDownload(false);
    setEditing(false);
    setEditFocus(null);
    setAdjDraft(null);
    setMissing(null);
    Promise.all([
      api.listPlanSummaries(client.id),
      api.listExercises({ include_archived: true }),
      api.listPeriods(client.id),
    ])
      .then(async ([plans, exs, pds]) => {
        if (!alive) return;
        const map: Record<number, string> = {};
        const vids: Record<number, string> = {};
        exs.forEach((e) => {
          map[e.id] = e.canonical_name;
          // Solo URLs http(s): una legada sin esquema se renderizaría como
          // ruta relativa de la app (mismo re-filtro que el portal).
          const v = (e.video_url ?? "").trim();
          if (/^https?:\/\//i.test(v)) vids[e.id] = v;
        });
        setExMap(map);
        setExVideo(vids);
        setExList(exs);
        setPeriods(pds);
        setAllPlans(plans);
        const v = vigente(plans);
        // Solo la versión que se ENSEÑA se pide entera.
        if (v) {
          const completo = await api.getPlan(v.id).catch(() => null);
          if (alive && completo) setPlan(normalize(completo));
        }
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

  /** Recarga el archivo de versiones (resumido) y deja a la vista UNA de ellas,
   *  pedida entera: `preferido` si se indica, si no la vigente. Es el único
   *  camino de recarga del panel — antes cada acción repetía la lista COMPLETA
   *  de versiones con todo su contenido. */
  async function recargarPlanes(preferido?: number | null): Promise<PlanSummary[]> {
    const resumen = await api.listPlanSummaries(client.id).catch(() => null);
    if (!resumen) return allPlans;
    setAllPlans(resumen);
    const elegido = (preferido != null ? resumen.find((p) => p.id === preferido) : null)
      ?? vigente(resumen);
    if (elegido) {
      const completo = await api.getPlan(elegido.id).catch(() => null);
      if (completo) setPlan(normalize(completo));
    }
    return resumen;
  }

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
    // Abrimos la pestaña YA, dentro del gesto de clic: si esperáramos al await de
    // planPdfUrl(), Safari/iOS bloquearían el window.open y el botón no haría nada.
    const win = window.open("", "_blank");
    try {
      const pdfUrl = await planPdfUrl();
      const adaptedIdx = plan?.nutrition?.applied_adjustments?.period_index ?? null;
      const url = waUrl(phone, planMessage(client.full_name, pdfUrl, adaptedIdx, plan?.month_index ?? 1));
      if (win) win.location.href = url; else openWhatsApp(phone, planMessage(client.full_name, pdfUrl, adaptedIdx, plan?.month_index ?? 1));
      // El enlace genera el PDF al abrirse → el cliente recibe la versión
      // vigente: el aviso de re-descarga queda resuelto.
      setNeedsDownload(false);
      toast.push("WhatsApp abierto con el plan");
    } catch {
      if (win) win.close();
      toast.push("Sin enlace del plan", "error");
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
    const win = window.open("", "_blank"); // ver nota en sendPlanWhatsApp
    try {
      const pdfUrl = await planPdfUrl();
      const adaptedIdx = plan?.nutrition?.applied_adjustments?.period_index ?? null;
      const url = waUrl(phone, planAndFeedbackMessage(client.full_name, fb.content, pdfUrl, adaptedIdx));
      if (win) win.location.href = url; else openWhatsApp(phone, planAndFeedbackMessage(client.full_name, fb.content, pdfUrl, adaptedIdx));
      setNeedsDownload(false); // el enlace enviado sirve la versión vigente
      toast.push("WhatsApp: plan y feedback");
      if (!fb.sent) {
        // Solo se marca enviado si el backend LO REGISTRÓ: antes el catch mudo
        // dejaba la UI en "enviado" con el ciclo sin avanzar (auditoría).
        try {
          await api.sendFeedback(fb.id);
          setFb({ ...fb, sent: true });
          onClientChanged?.();
        } catch {
          toast.push("Envío sin registrar", "error");
        }
      }
    } catch {
      if (win) win.close();
      toast.push("No se pudo preparar el envío", "error");
    }
  }

  /** Entrega la planificación POR EMAIL (paquetes Start/Full): el backend adjunta
   *  el PDF y enlaza el portal. Equivale al envío por WhatsApp de Pro. */
  async function sendPlanByEmail() {
    if (!plan) return;
    try {
      const r = await api.sendPlanEmail(plan.id);
      if (r.email_status === "sent") {
        setNeedsDownload(false); // el cliente ya tiene la versión vigente
        toast.push(r.attached_pdf ? "Plan enviado por email (PDF adjunto)" : "Plan enviado por email");
      } else if (r.email_status === "disabled") {
        toast.push("Email desactivado: no se envió", "error");
      } else {
        toast.push("Email no enviado", "error");
      }
    } catch {
      toast.push("Fallo al enviar por email", "error");
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
      // La respuesta trae el rev incrementado por el backend: guardarla evita
      // que la SIGUIENTE edición muera con un 409 falso de "otra pestaña"
      // (auditoría crítica). Mismo patrón que el save del editor.
      const r = await api.updatePlan(plan.id, { nutrition_json: nutrition });
      // OJO: `normalize` prefiere la clave `nutrition` a `nutrition_json`, y
      // `plan` ya trae la suya (la vieja). Escribiendo en `nutrition_json` lo
      // guardado NO se veía: la pantalla seguía enseñando lo anterior aunque el
      // backend ya lo tuviera.
      setPlan(normalize({ ...plan, nutrition: r.nutrition_json ?? nutrition }));
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

  // ¿La operación en curso es la base sin IA? (para el texto de progreso)
  const [scaffolding, setScaffolding] = useState(false);

  // Reengancha una generación EN VUELO tras un remount (cambio de pestaña):
  // al terminar refresca el plan y apaga el "Generando…".
  useEffect(() => {
    const enCurso = enVuelo.get(client.id);
    if (!enCurso) return;
    setGenerating(true);
    let vivo = true;
    enCurso.finally(async () => {
      if (!vivo) return;
      setGenerating(false);
      try {
        await recargarPlanes();
      } catch { /* la carga normal del montaje ya lo enseña */ }
    });
    return () => { vivo = false; };
  }, [client.id]);

  async function generate(meals?: string[]) {
    if (generating) return;
    // Cliente avanzado: la IA es la vía EXCEPCIONAL y además auto-activa — se
    // confirma siempre para que el gasto y el envío no pillen por sorpresa.
    if (client.level === "advanced" &&
        !window.confirm("¿Generar? Gasta créditos · queda ACTIVO")) {
      return;
    }
    setGenerating(true);
    setScaffolding(false);
    setMissing(null);
    const peticion = api.generatePlan(client.id, null, meals);
    enVuelo.set(client.id, peticion.catch(() => undefined));
    try {
      const p = await peticion;
      setPlan(normalize(p));
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      setNeedsDownload(false); // versión nueva: el aviso de re-descarga ya no aplica
      onClientChanged?.(); // resincroniza sidebar (Dieta), badges y carpetas
      // Toast HONESTO: si los guardarraíles lo retuvieron, no se canta victoria.
      if ((p as any).retained) {
        toast.push("Borrador RETENIDO por avisos: revísalo y actívalo tú (el cliente no ve nada)", "error");
      } else {
        toast.push(`Plan generado y ACTIVO`);
      }
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push([detail?.message ?? e?.message ?? "No se pudo generar el plan", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      enVuelo.delete(client.id);
      setGenerating(false);
    }
  }

  async function adapt() {
    if (generating) return;
    setGenerating(true);
    const peticion = api.adaptPlan(client.id);
    enVuelo.set(client.id, peticion.catch(() => undefined));
    try {
      const r = await peticion;
      // La adaptación puede quedar RETENIDA (borrador) conviviendo con el plan
      // activo: la que hay que enseñar es ELLA, no la vigente.
      const resumen = await recargarPlanes(r.id);
      const full = resumen.find((pl) => pl.id === r.id) ?? vigente(resumen);
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      setNeedsDownload(false); // versión nueva activa: el aviso de la edición anterior caduca
      onClientChanged?.(); // resincroniza sidebar (Dieta) y estados
      // Igual que al generar: una adaptación retenida NO se anuncia como activa.
      if ((full ?? r).status !== "published") {
        toast.push(`Adaptación v${r.version} en BORRADOR retenido: revísala antes de activar`, "error");
      } else {
        toast.push(`Adaptado y ACTIVO · v${r.version}`);
      }
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push([detail?.message ?? e?.message ?? "No se pudo adaptar el plan", detail?.error].filter(Boolean).join(" — "), "error");
    } finally {
      enVuelo.delete(client.id);
      setGenerating(false);
    }
  }

  /** Plan BASE sin IA (cliente avanzado): borrador determinista con los números
   *  ya hechos, listo para que el coach lo remate en el editor. 0 créditos.
   *  NO se activa al editar: solo con el botón Activar. */
  // Copiar desde la biblioteca (otro cliente o un modelo): 0 créditos. El
  // backend recalcula las cifras del destino y devuelve los avisos de
  // seguridad, que aquí se enseñan y quedan en los flags del borrador.
  const [biblioteca, setBiblioteca] = useState(false);
  async function aplicarDeBiblioteca(source: { plan_id?: number; template_id?: number }) {
    if (generating) return;
    setGenerating(true);
    setBiblioteca(false);
    try {
      const p = await api.applyFromLibrary(client.id, source);
      // Con un plan ya activo, la copia entra como borrador y se anuncia en la
      // banda de "sin activar": el cliente sigue viendo el actual. Sin plan,
      // la copia pasa a ser lo que se enseña.
      if (plan && plan.status === "published") {
        await recargarPlanes();
      } else {
        setPlan(normalize(p));
      }
      onClientChanged?.();
      if (p.warnings?.length) {
        toast.push(`Copia lista · ${p.warnings.length} aviso${p.warnings.length === 1 ? "" : "s"} a revisar`, "error");
      } else {
        toast.push("Copia lista · cifras recalculadas para este cliente");
      }
    } catch (e: any) {
      const detail = e?.detail;
      // Anamnesis incompleta: el MISMO recuadro accionable que "Generar", no
      // un toast que se va a los cuatro segundos.
      if (detail?.missing) setMissing(detail.missing);
      else toast.push(detail?.message ?? detail ?? e?.message ?? "No se pudo copiar", "error");
    } finally {
      setGenerating(false);
    }
  }

  async function scaffold(meals?: string[]) {
    if (generating) return;
    setGenerating(true);
    setScaffolding(true);
    setMissing(null);
    try {
      const p = await api.scaffoldPlan(client.id, null, meals);
      setPlan(normalize(p));
      setEditing(true); // directo al editor: la base ya está masticada
      onClientChanged?.();
      toast.push("Base lista · 0 créditos");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push(detail?.message ?? e?.message ?? "No se pudo preparar la base", "error");
    } finally {
      setGenerating(false);
      setScaffolding(false);
    }
  }

  /** Para BORRADORES ANTIGUOS (de antes de la activación automática) y para la
   *  BASE SIN IA del cliente avanzado: los demás quedan activos al generarse. */
  async function activateLegacy() {
    if (!plan || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(plan.id);
      setPlan({ ...plan, status: "published" });
      setPeriods(await api.listPeriods(client.id).catch(() => periods));
      onClientChanged?.(); // el sidebar (Dieta) pasa a mostrar este plan
      toast.push("Activa · la ve el cliente");
    } catch {
      toast.push("No se pudo activar", "error");
    } finally {
      setPublishing(false);
    }
  }

  function downloadDocument(format: "pdf" | "docx" = "pdf") {
    if (!plan) return;
    const url0 = api.planDocumentUrl(plan.id) + (format === "docx" ? "?format=docx" : "");
    fetch(url0, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => {
        // Sin esto, un 401/500 guardaba un archivo corrupto con el JSON del error.
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `plan_${client.full_name.replace(/\s+/g, "_").toLowerCase()}_mes${plan.month_index}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
        setNeedsDownload(false); // ya tiene la versión actualizada
        if (format === "docx") setWordDescargado(true); // la vuelta, a mano
      })
      .catch(() => toast.push("No se pudo descargar", "error"));
  }

  const downloadPdf = () => downloadDocument("pdf");

  // ---- Ida y VUELTA del Word editable: subir el .docx editado, ver los
  // cambios detectados y aplicarlos por el MISMO camino que el editor web.
  const [importPreview, setImportPreview] = useState<{
    changes: string[]; warnings: string[]; base_rev: number;
    nutrition_json: any; training_json: any; education_json?: any | null;
  } | null>(null);
  const [importing, setImporting] = useState(false);
  const [applyingImport, setApplyingImport] = useState(false);

  async function onWordPicked(file: File | null | undefined) {
    if (!file || !plan || importing) return;
    setImporting(true);
    try {
      const r = await api.importPlanWord(plan.id, file);
      if (!r.has_changes && !r.warnings.length) {
        toast.push("Ese Word no trae cambios");
      } else {
        setImportPreview(r);
      }
    } catch (e: any) {
      toast.push(e?.message ?? "Word ilegible o ajeno", "error");
    } finally {
      setImporting(false);
    }
  }

  async function applyImport() {
    if (!plan || !importPreview || applyingImport) return;
    setApplyingImport(true);
    try {
      const patch: any = { base_rev: importPreview.base_rev };
      if (importPreview.nutrition_json) patch.nutrition_json = importPreview.nutrition_json;
      if (importPreview.training_json) patch.training_json = importPreview.training_json;
      // El educativo (píldoras/técnica/FAQ) también va y vuelve en el Word:
      // solo viaja si el importador detectó cambios en sus cajas.
      if (importPreview.education_json) patch.education_json = importPreview.education_json;
      const r = await api.updatePlan(plan.id, patch);
      setPlan(normalize({
        ...plan,
        // Mismo motivo que arriba: la clave que manda es `nutrition`/`training`.
        nutrition: r.nutrition_json ?? importPreview.nutrition_json ?? plan.nutrition,
        training: r.training_json ?? importPreview.training_json ?? plan.training,
        education: r.education_json ?? importPreview.education_json ?? plan.education,
      }));
      setImportPreview(null);
      setNeedsDownload(true); // el documento cambió: toca re-descargar el PDF
      toast.push("Word aplicado al plan");
    } catch (e: any) {
      const msg = String(e?.message ?? "");
      toast.push(
        msg.includes("409") || msg.toLowerCase().includes("versión")
          ? "El plan cambió mientras editabas"
          : (msg || "No se pudieron aplicar los cambios"),
        "error",
      );
    } finally {
      setApplyingImport(false);
    }
  }

  // ⚠️ HOOKS SIEMPRE ANTES de los return tempranos (cargando / sin plan /
  // edición). Este efecto vivía más abajo y violaba las Rules of Hooks: al
  // cargar el plan cambiaba el número de hooks entre renders y React tumbaba
  // TODA la app EN BLANCO al abrir esta pestaña (auditoría 26-08).
  // Ámbito de los recordatorios nacidos de los avisos del PLAN. Se ancla al
  // CLIENTE, no a la versión: al regenerar cambia el id del plan y los
  // recordatorios de la versión anterior no se retirarían nunca.
  const ambitoPlan = `plan:${client.id}`;
  // Los avisos VIVOS de este plan, ahora mismo. Todo recordatorio de este
  // ámbito que ya no esté aquí es que se arregló: se borra solo.
  const avisosVivos = (() => {
    const c = plan?.review?.color;
    const fs = (c === "rojo" || c === "ambar") ? (plan?.review?.findings ?? []) : [];
    return agrupar(fs.map(toAviso))
      .flatMap((g) => g.items)
      .map((a) => clavePlan(a.destino, a.titulo));
  })();
  const avisosFirma = avisosVivos.join("|");
  useEffect(() => {
    // Solo con el plan cargado: sin plan no se puede afirmar que no haya avisos.
    if (plan) syncScope(ambitoPlan, avisosFirma ? avisosFirma.split("|") : []);
  }, [plan, ambitoPlan, avisosFirma]);

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
              {client.level === "advanced"
                ? "La montas tú, sin IA"
                : `Genera con IA · queda ACTIVO`}
            </p>

            {missing && (
              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "rgba(154,107,21,0.45)", background: "rgba(154,107,21,0.09)" }}>
                <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <AlertTriangle size={15} /> Faltan datos en la anamnesis
                </div>
                <p className="mt-1 text-xs text-zinc-400">
                  Bloquean la generación del plan
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

            {/* TRES caminos, siempre los tres, con su coste a la vista.
                Para el avanzado el orden cambia (su plan lo monta el coach),
                pero las opciones son las mismas: la web ya no esconde el
                "a mano" ni el "copiar" a nadie. */}
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {(client.level === "advanced"
                ? (["mano", "copiar", "ia"] as const)
                : (["ia", "mano", "copiar"] as const)
              ).map((camino, i) => {
                const principal = i === 0;
                const boton = principal ? "btn btn-primary w-full" : "btn btn-ghost w-full";
                if (camino === "ia") {
                  return (
                    <div key={camino} className="well flex flex-col gap-2 p-3.5">
                      <p className="text-sm font-semibold text-zinc-100">Con IA</p>
                      <p className="flex-1 text-xs text-zinc-500">
                        El sistema lo genera entero y queda activo. Gasta créditos.
                      </p>
                      <button onClick={() => generate()} disabled={generating}
                        className={boton} {...ancla("plan.generar")}>
                        <Sparkles size={15} />
                        {generating && !scaffolding ? "Generando…" : "Generar"}
                      </button>
                    </div>
                  );
                }
                if (camino === "mano") {
                  return (
                    <div key={camino} className="well flex flex-col gap-2 p-3.5">
                      <p className="text-sm font-semibold text-zinc-100">A mano · 0 créditos</p>
                      <p className="flex-1 text-xs text-zinc-500">
                        El sistema deja los números, comidas y sesiones preparados;
                        tú lo terminas en el editor o en Word y lo activas.
                      </p>
                      <button onClick={() => void scaffold()} disabled={generating}
                        className={boton}>
                        <Pencil size={15} />
                        {scaffolding ? "Preparando…" : "Preparar base"}
                      </button>
                    </div>
                  );
                }
                return (
                  <div key={camino} className="well flex flex-col gap-2 p-3.5">
                    <p className="text-sm font-semibold text-zinc-100">Desde otro plan · 0 créditos</p>
                    <p className="flex-1 text-xs text-zinc-500">
                      Copia un modelo guardado o el plan de otro cliente; las
                      cifras se recalculan para este.
                    </p>
                    <button onClick={() => setBiblioteca(true)} disabled={generating}
                      className={boton}>
                      <Archive size={15} /> Elegir base
                    </button>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-zinc-500">
              Nada llega al cliente hasta que pulses <b>Activar</b> (salvo la
              generación con IA, que activa sola). ¿Dieta hecha fuera? Prepara
              la base, descárgala en Word, rellénala y súbela: se aplica sin IA.
            </p>
            {biblioteca && (
              <SelectorDeBiblioteca
                clienteId={client.id}
                onElegir={aplicarDeBiblioteca}
                onCerrar={() => setBiblioteca(false)}
              />
            )}
            {generating && (
              <p className="mt-2 text-xs text-zinc-500">
                {scaffolding
                  ? "Preparando base sin IA…"
                  : "Creando el plan · 1-2 min"}
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
        library={exList}
        client={client}
        refWeightKg={(client as any).reference_weight_kg ?? lastClosing?.closing_weight_kg ?? client.start_weight_kg ?? null}
        initialFocus={editFocus}
        onSaved={(p) => {
          // Solo avisar de "reenvía la actualización" si REALMENTE cambió algo:
          // abrir el editor por un bloque y guardar sin tocar nada (o entrar y
          // salir) no debe disparar el aviso — se compara con lo que había
          // antes de este guardado.
          const changed = JSON.stringify(plan.nutrition) !== JSON.stringify(p.nutrition)
            || JSON.stringify(plan.training) !== JSON.stringify(p.training)
            || JSON.stringify(plan.education) !== JSON.stringify(p.education);
          setPlan(p);
          setEditing(false);
          setEditFocus(null);
          if (changed) {
            // El PDF descargado antes ya NO refleja esta edición: avisar hasta
            // que el coach lo vuelva a descargar (o lo reenvíe por WhatsApp).
            setNeedsDownload(true);
            toast.push("Guardado · sin enviar al cliente");
          } else {
            toast.push("Sin cambios que guardar");
          }
        }}
        onCancel={() => { setEditing(false); setEditFocus(null); }}
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

  /** Un clic en el aviso lleva a donde se resuelve: el editor abierto por la
   *  sección correcta, la pestaña Anamnesis, o el botón de generar. Y deja un
   *  RECORDATORIO de lo que ibas a arreglar, que se borra solo cuando el aviso
   *  desaparece del plan. */
  function irADestino(destino: Destino, aviso?: { titulo: string; accion: string; detalle?: string }) {
    // El recordatorio guarda el MISMO destino al que se va: antes nacía sin
    // ancla (al volver por el dock no marcaba nada) y con el enlace a
    // Planificación aunque el hallazgo mandara a la Anamnesis.
    const pestana = destino === "anamnesis" ? "anamnesis" : "planificacion";
    const anclaDestino = destino === "anamnesis" ? "anamnesis.revision"
      : destino === "nutricion" ? "nutricion.macros"
      : destino === "entreno" ? "entreno.sesiones"
      : "plan.acciones";
    if (aviso) {
      pin({
        id: pinId(ambitoPlan, clavePlan(destino, aviso.titulo)),
        scope: ambitoPlan,
        key: clavePlan(destino, aviso.titulo),
        clientId: client.id,
        clientName: client.full_name,
        label: aviso.titulo,
        hint: aviso.accion,
        href: hrefCliente(client.id, pestana, anclaDestino),
        target: anclaDestino,
        severity: "alta",
      });
    }
    if (destino === "anamnesis") { onGoTab?.("anamnesis"); return; }
    setEditing(true);
    // Mapa EXPLÍCITO: un ternario mandaba todo lo que no fuese nutrición al
    // editor de entrenamiento, incluso en un cliente de solo nutrición.
    // "generar" (falta el entrenamiento) también aterriza en esa sección: es
    // donde se completa; llevar a la fila de botones era un callejón sin salida.
    const id =
      destino === "nutricion" ? "editor-nutricion"
      : (destino === "entreno" || destino === "generar") && hasTraining ? "editor-entreno"
      : hasTraining ? "editor-entreno" : "editor-nutricion";
    // El editor se monta tras el re-render: el salto a su sección va después.
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 120);
  }

  // UN SOLO recuento de puntos a corregir, compartido por el chip de estado y
  // el bloque de avisos: son las líneas que el coach VE (avisos ya fusionados
  // entre revisores + avisos del guardarraíl ya traducidos y agrupados).

  const nRojoTotal = (() => {
    // Mismo filtro por color que el bloque: sin él salía una caja roja vacía
    // con la cabecera "Retenido · 1 punto a corregir".
    const c = plan?.review?.color;
    const bloq = (c === "rojo" || c === "ambar")
      ? (plan?.review?.findings ?? []).filter((f) => f.severity === "bloqueante")
      : [];
    const flags = traducirFlags((plan?.guardrail_flags ?? [])
      .filter((f) => f.startsWith("violation:") || f.startsWith("retenido")));
    return agrupar(bloq.map(toAviso)).reduce((n, g) => n + g.items.length, 0) + flags.length;
  })();

  // Adaptación que quedó RETENIDA por los guardarraíles: es más nueva que el
  // plan que se está enseñando y sigue sin activar.
  // Si conviven una adaptación RETENIDA (violaciones) y una copia nueva, la
  // banda enseña primero la retenida: sus vetos de seguridad no pueden quedar
  // tapados por una copia posterior.
  const borradoresNuevos = allPlans.filter(
    (p) => p.status === "draft" && (p.id ?? 0) > (plan?.id ?? 0));
  const retenido =
    borradoresNuevos.find((p) => (p.guardrail_flags ?? [])
      .some((f: string) => f.startsWith("violation:") || f.startsWith("retenido")))
    ?? borradoresNuevos[0];
  const motivosRetencion = retenido
    ? traducirFlags((retenido.guardrail_flags ?? [])
        .filter((f: string) => f.startsWith("violation:") || f.startsWith("retenido")))
    : [];

  async function activarRetenido() {
    if (!retenido || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(retenido.id);
      await recargarPlanes();
      onClientChanged?.();
      toast.push("Activa · la ve el cliente");
    } catch {
      toast.push("No se pudo activar", "error");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="space-y-4">
      {biblioteca && (
        <SelectorDeBiblioteca
          clienteId={client.id}
          onElegir={aplicarDeBiblioteca}
          onCerrar={() => setBiblioteca(false)}
        />
      )}
      {retenido && (() => {
        const esCopia = (retenido.guardrail_flags ?? [])
          .some((f: string) => f.startsWith("copiado de"));
        return (
        <div className="card p-4" {...ancla("plan.activar")}
          style={{ borderColor: `color-mix(in srgb, ${esCopia ? "var(--brand-accent-2)" : "#C2453A"} 45%, transparent)` }}>
          <p className="text-sm font-semibold" style={{ color: esCopia ? "var(--brand-accent-2)" : "#B91C1C" }}>
            {esCopia
              ? `Copia v${retenido.version} sin activar · el cliente sigue con la anterior`
              : `▲ Adaptación v${retenido.version} retenida · el cliente sigue con la anterior`}
          </p>
          {motivosRetencion.length > 0 && (
            <ul className="mt-2 space-y-1">
              {motivosRetencion.slice(0, 6).map((m, i) => (
                <li key={i} className="text-xs text-zinc-400">· {m}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-zinc-500">
            {esCopia
              ? "Adáptala a este cliente y actívala cuando esté lista."
              : "Los guardarraíles la pararon: revísala y corrige lo señalado, o actívala si estás de acuerdo tal cual."}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {/* Con retención por seguridad lo PRIMERO es revisar: el botón
                destacado es "Ver este borrador"; activar sin corregir queda en
                segundo plano y pide confirmación. En una copia normal, al revés. */}
            <button onClick={() => { void recargarPlanes(retenido.id); }}
              className={esCopia ? "btn btn-ghost text-xs" : "btn btn-primary text-xs"}>
              Ver este borrador
            </button>
            <button
              onClick={() => {
                if (!esCopia && !window.confirm(
                  "Este borrador está RETENIDO por avisos de seguridad. "
                  + "¿Activarlo de todas formas? El cliente lo verá al momento.")) return;
                activarRetenido();
              }}
              disabled={publishing}
              className={esCopia ? "btn btn-primary text-xs" : "btn btn-ghost text-xs"}>
              {publishing ? "Activando…" : esCopia ? "Activar" : "Activar de todas formas"}
            </button>
            <button
              onClick={async () => {
                if (!window.confirm(`¿Descartar el borrador v${retenido.version}? No se puede deshacer desde aquí (queda en Planificaciones anteriores).`)) return;
                try {
                  await api.discardPlan(retenido.id);
                  await recargarPlanes();
                  toast.push("Borrador descartado");
                } catch (e: any) {
                  toast.push(e?.message ?? "No se pudo descartar", "error");
                }
              }}
              className="btn btn-ghost text-xs text-zinc-500"
              title="La copia o base deja de estar pendiente; el plan activo no se toca"
            >
              Descartar
            </button>
          </div>
        </div>
        );
      })()}

      {/* Viendo un borrador que NO es el plan activo: salida clara de vuelta
          (antes el coach se quedaba "atrapado" mirando el borrador). */}
      {plan && (() => {
        const v = vigente(allPlans);
        if (!v || v.id === plan.id) return null;
        return (
          <button onClick={() => { void recargarPlanes(v.id); }} className="btn btn-ghost text-xs">
            ← Volver al plan activo (v{v.version})
          </button>
        );
      })()}

      {/* Cabecera con acciones */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              {/* Un solo recuento para el chip y para el bloque de avisos. */}
              <h3 className="text-base font-semibold text-zinc-100">
                Planificación · {planMonthLabel(plan.published_at ?? plan.created_at)}
              </h3>
              {/* UN chip de estado (antes "Activa · v3" + "● En uso por el
                  cliente" decían casi lo mismo en dos chips distintos). */}
              <span
                className="rounded-full px-2 py-0.5 text-xs font-semibold"
                style={
                  plan.status === "published"
                    ? { background: "rgba(22,163,74,0.12)", color: "#2E7D46" }
                    : { background: "rgba(38,33,26,0.08)", color: "#7A7060" }
                }
              >
                {plan.status === "published"
                  ? "● Activa para el cliente"
                  : plan.guardrail_flags?.some((f) => f.startsWith("base sin IA"))
                    ? "Base del coach — sin activar"
                    : plan.guardrail_flags?.some((f) => f.startsWith("copiado de"))
                      ? "Copia — adáptala y actívala"
                      : "Borrador antiguo"} · v{plan.version}
              </span>
              {/* §9: semáforo del panel de supervisión + ICP (confianza del plan). */}
              {plan.review?.color && (() => {
                const c = plan.review.color;
                const style = c === "rojo"
                  ? { background: "rgba(220,38,38,0.12)", color: "#B91C1C" }
                  : c === "verde"
                    ? { background: "rgba(22,163,74,0.12)", color: "#15803D" }
                    : { background: "rgba(217,119,6,0.12)", color: "#B45309" };
                // MISMO recuento que el bloque de abajo (antes el chip contaba
                // solo los hallazgos y el bloque hallazgos + flags: 19 vs 24).
                const label = c === "rojo"
                  ? (nRojoTotal ? `${nRojoTotal} a corregir` : "Revisar")
                  : c === "verde" ? "Revisión OK" : "Con avisos";
                return (
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold"
                    style={style}
                    title={typeof plan.review.icp === "number"
                      ? `Confianza de la revisión automática: ${Math.round(plan.review.icp)}/100`
                      : undefined}>
                    {c === "rojo" ? "▲ " : "● "}{label}
                  </span>
                );
              })()}
            </div>
            {/* AVISOS en dos niveles: lo BLOQUEANTE (rojo) siempre a la vista —
                es la razón de que el plan no llegue al cliente —; el resto
                (ámbar) plegado con contador para no apilar ~10 líneas. */}
            {(() => {
              const findings = (plan.review?.color === "rojo" || plan.review?.color === "ambar")
                ? (plan.review?.findings ?? []) : [];
              const flags = (plan.guardrail_flags ?? [])
                // El aviso "base sin IA" es del ciclo de PREPARACIÓN: con el
                // plan ya activado dejaría un estado falso en ámbar eterno.
                .filter((f) => plan.status !== "published" || !f.startsWith("base sin IA"));
              const rojoFindings = findings.filter((f) => f.severity === "bloqueante");
              // Jerga fuera: "violation:… fat_g … ±5%" → "Grasas fuera de rango".
              const rojoFlags = traducirFlags(
                flags.filter((f) => f.startsWith("violation:") || f.startsWith("retenido")));
              const ambarFindings = findings.filter((f) => f.severity !== "bloqueante");
              const ambarFlags = traducirFlags(
                flags.filter((f) => !f.startsWith("violation:") && !f.startsWith("retenido")));
              const degraded = plan.review?.degraded_reviewers?.length ?? 0;
              const nAmbar = agrupar(ambarFindings.map(toAviso))
                .reduce((n, g) => n + g.items.length, 0)
                + ambarFlags.length + (degraded > 0 ? 1 : 0);
              const nRojo = nRojoTotal;
              return (
                <>
                  {nRojo > 0 && (
                    <AvisosBlock
                      tono="rojo"
                      // El coach necesita saber POR QUÉ está en rojo y qué pasa
                      // si no lo toca: antes solo veía párrafos sin contexto.
                      cabecera={plan.status === "published"
                        ? `${nRojo} punto${nRojo === 1 ? "" : "s"} a corregir en el plan activo`
                        : `Retenido · ${nRojo} punto${nRojo === 1 ? "" : "s"} a corregir antes de enviarlo`}
                      findings={rojoFindings}
                      flags={rojoFlags}
                      onIr={irADestino}
                    />
                  )}
                  {nAmbar > 0 && (
                    <AvisosBlock
                      tono="ambar"
                      cabecera={`${nAmbar} aviso${nAmbar === 1 ? "" : "s"} · no bloquean el envío`}
                      findings={ambarFindings}
                      flags={ambarFlags}
                      onIr={irADestino}
                      degraded={degraded}
                      plegado
                    />
                  )}
                </>
              );
            })()}
            {/* REGISTRO de qué versión es esta: su origen (IA / adaptación a
                revisión #N) y si lleva cambios manuales sin enviar. */}
            <p className="mt-0.5 text-xs text-zinc-500">
              {(() => {
                const adj = (nut as any)?.applied_adjustments;
                const manual = ((nut as any)?.manual_changes?.items ?? []).length;
                const esBase = plan.guardrail_flags?.some((f) => f.startsWith("base sin IA"));
                const esCopiaLinea = plan.guardrail_flags?.some((f) => f.startsWith("copiado de"));
                const origen = adj?.period_index != null
                  ? `Adaptada a la revisión quincenal #${adj.period_index}`
                  : esBase
                    ? "Base sin IA, rematada por ti"
                    : esCopiaLinea
                      ? "Copiada de la biblioteca · cifras recalculadas"
                      : "Generada con IA · anamnesis";
                return (
                  <>
                    Mes {plan.month_index} de asesoría · {origen}
                    {manual > 0 && (
                      <span className="font-medium" style={{ color: "var(--brand-accent)" }}>
                        {" "}· {manual} cambios sin enviar
                      </span>
                    )}
                  </>
                );
              })()}
            </p>
          </div>
          {/* Acciones: en móvil ocupan todo el ancho (2 columnas) sin cortarse;
              en escritorio van en fila. */}
          <div id="plan-acciones" {...ancla("plan.acciones")}
            className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
            <button onClick={() => setEditing(true)} className="btn btn-ghost">
              <Pencil size={15} /> Editar
            </button>
            <button onClick={downloadPdf} className="btn btn-ghost">
              <Download size={15} /> Descargar PDF
            </button>
            {/* La VUELTA del Word: tras descargar el editable, subirlo está a
                un clic (no escondido dentro de «Más»). */}
            {wordDescargado && (
              <label className="btn btn-ghost cursor-pointer"
                title="Revisar cambios antes de aplicarlos">
                {importing ? <Spinner /> : <FileUp size={15} />} Subir Word editado
                <input
                  type="file"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  disabled={importing}
                  onChange={(e) => {
                    onWordPicked(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </label>
            )}
            {/* Las acciones poco frecuentes viven en un menú: la botonera pasa
                de 6-7 botones del mismo peso a 3-4 (lo frecuente destaca). */}
            <details className="relative"
              onKeyDown={(e) => {
                if (e.key !== "Escape") return;
                e.currentTarget.removeAttribute("open");
                e.stopPropagation();
              }}>
              <summary className="btn btn-ghost w-full cursor-pointer list-none sm:w-auto">
                <MoreHorizontal size={15} /> Más
              </summary>
              {/* Fondo invisible: clic fuera del menú lo cierra. */}
              <div
                className="fixed inset-0 z-10"
                onClick={(e) => e.currentTarget.closest("details")?.removeAttribute("open")}
              />
              <div
                className="absolute right-0 z-20 mt-1 w-60 rounded-xl border p-1 shadow-lg"
                style={{ borderColor: "var(--line-strong)", background: "var(--surface)" }}
              >
                <button
                  onClick={(e) => {
                    e.currentTarget.closest("details")?.removeAttribute("open");
                    setHistOpen(true);
                    setHist(null);
                    api.planHistory(plan.id).then(setHist).catch(() => setHist([]));
                  }}
                  className="btn btn-ghost w-full justify-start"
                  title="Restaurar una versión anterior"
                >
                  <Archive size={15} /> Historial de versiones
                </button>
                <button
                  onClick={(e) => {
                    e.currentTarget.closest("details")?.removeAttribute("open");
                    // El título lo pone el coach; sin datos del cliente salvo
                    // que él quiera nombrarlo. Reutilizable desde "Elegir base"
                    // de cualquier ficha, a 0 créditos.
                    const titulo = window.prompt(
                      "Nombre del modelo (p. ej. «Planificación base»):");
                    if (!titulo?.trim()) return;
                    api.saveTemplate(plan.id, titulo.trim())
                      .then((t) => toast.push(`Modelo «${t.title}» guardado — en «Elegir base» de cualquier cliente`))
                      .catch((err: any) => toast.push(err?.message ?? "No se pudo guardar", "error"));
                  }}
                  className="btn btn-ghost w-full justify-start"
                  title="Reutilizarlo como base para otros clientes (0 créditos)"
                >
                  <Copy size={15} /> Guardar como modelo
                </button>
                <button
                  onClick={(e) => {
                    e.currentTarget.closest("details")?.removeAttribute("open");
                    setBiblioteca(true);
                  }}
                  className="btn btn-ghost w-full justify-start"
                  title="Crea un borrador desde un modelo u otro cliente; el actual sigue activo hasta que actives el nuevo"
                >
                  <Archive size={15} /> Empezar desde otro plan
                </button>
                <button
                  onClick={(e) => {
                    e.currentTarget.closest("details")?.removeAttribute("open");
                    downloadDocument("docx");
                  }}
                  className="btn btn-ghost w-full justify-start"
                  title="Editar el plan en Word"
                >
                  <FileText size={15} /> Word editable
                </button>
                <label
                  className="btn btn-ghost w-full cursor-pointer justify-start"
                  title="Revisar cambios antes de aplicarlos"
                >
                  {importing ? <Spinner /> : <FileUp size={15} />} Subir Word editado
                  <input
                    type="file"
                    accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    className="hidden"
                    disabled={importing}
                    onChange={(e) => {
                      e.currentTarget.closest("details")?.removeAttribute("open");
                      onWordPicked(e.target.files?.[0]);
                      e.target.value = ""; // permite volver a subir el mismo archivo
                    }}
                  />
                </label>
              </div>
            </details>
            {plan.status === "published" && byEmail && (
              <button onClick={sendPlanByEmail} className="btn btn-primary col-span-2 sm:col-span-1">
                <Mail size={15} /> Enviar plan por email
              </button>
            )}
            {plan.status === "published" && !byEmail && (
              <button onClick={sendPlanWhatsApp} className={`${fb ? "btn btn-ghost" : "btn btn-primary"} col-span-2 sm:col-span-1`}>
                <MessageCircle size={15} /> Enviar plan por WhatsApp
              </button>
            )}
            {plan.status === "published" && !byEmail && fb && (
              <button onClick={sendPlanAndFeedbackWhatsApp} className="btn btn-primary col-span-2 sm:col-span-1">
                <MessageCircle size={15} /> Enviar plan + feedback
              </button>
            )}
            {plan.status !== "published" && (
              <button onClick={activateLegacy} disabled={publishing} className="btn btn-primary col-span-2 sm:col-span-1"
                {...ancla("plan.activar")}>
                <Send size={15} /> {publishing ? "Activando…" : "Activar"}
              </button>
            )}
          </div>
        </div>

        {/* Historial de versiones (§4): instantáneas guardadas antes de cada
            edición. Restaurar recupera aquella versión (y guarda la actual
            primero, así el propio revert también es reversible). */}
        {histOpen && (
          <div className="mt-3 rounded-lg border border-zinc-700/60 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">Historial de versiones</span>
              <button onClick={() => setHistOpen(false)} className="btn btn-ghost !px-2 !py-1">
                <X size={14} />
              </button>
            </div>
            {hist === null ? (
              <div className="py-3"><Spinner /></div>
            ) : hist.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aún no hay versiones guardadas: se crean automáticamente cada vez
                que editas el plan.
              </p>
            ) : (
              <ul className="space-y-2">
                {hist.map((v) => (
                  <li key={v.index} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-zinc-800/40 px-3 py-2">
                    <div className="text-xs">
                      <span className="font-medium">
                        {v.at ? new Date(v.at).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" }) : "—"}
                      </span>
                      <span className="text-zinc-500"> · {v.label}</span>
                      {v.summary?.target_kcal != null && (
                        <span className="text-zinc-500">
                          {" "}· {v.summary.target_kcal} kcal · P {v.summary.protein_g ?? "—"} g ·
                          C {v.summary.carbs_g ?? "—"} g · G {v.summary.fat_g ?? "—"} g
                        </span>
                      )}
                    </div>
                    <button
                      disabled={reverting !== null}
                      onClick={async () => {
                        if (!window.confirm("¿Restaurar? La actual se guarda")) return;
                        setReverting(v.index);
                        try {
                          const p = await api.revertPlan(plan.id, v.index);
                          setPlan(normalize(p));
                          setNeedsDownload(true);
                          setHistOpen(false);
                          toast.push("Versión restaurada");
                        } catch (e: any) {
                          toast.push(e?.message || "No se pudo restaurar la versión", "error");
                        } finally {
                          setReverting(null);
                        }
                      }}
                      className="btn btn-ghost !px-2 !py-1 text-xs"
                    >
                      {reverting === v.index ? "Restaurando…" : "Restaurar"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Vista previa de la IMPORTACIÓN del Word editado: el coach ve qué
            detectó el sistema y confirma antes de aplicar (mismo camino que el
            editor: sanitizado, reconcile, historial y rev). */}
        {importPreview && (
          <div className="mt-3 rounded-lg border p-3" style={{ borderColor: "var(--brand-accent)" }}>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">
                Cambios en tu Word · {importPreview.changes.length}
              </span>
              <button onClick={() => setImportPreview(null)} className="btn btn-ghost !px-2 !py-1">
                <X size={14} />
              </button>
            </div>
            {importPreview.changes.length > 0 ? (
              // Tope de altura con scroll propio: con 40 cambios, los botones
              // Aplicar/Descartar seguían fuera de pantalla.
              <ul className="mb-2 max-h-64 space-y-1 overflow-y-auto pr-1">
                {importPreview.changes.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-zinc-300">
                    <Pencil size={12} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent)" }} />
                    {c}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mb-2 text-xs text-zinc-500">
                Sin cambios aplicables
              </p>
            )}
            {importPreview.warnings.length > 0 && (
              <div className="mb-2 rounded-md border border-amber-700/50 bg-amber-900/20 p-2">
                {importPreview.warnings.map((w, i) => (
                  <p key={i} className="flex items-start gap-2 text-xs text-amber-300">
                    <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {w}
                  </p>
                ))}
              </div>
            )}
            <p className="mb-2 text-[11px] text-zinc-500">
              Se importa TODO el contenido editable del Word: kcal y macros, tomas
              (hora/nombre/estrategia), recetas del banco («Opción N…») y menú cerrado
              por días (con macros recalculados por el sistema), ejercicios con sus
              series/RIR/descansos/textos, calentamientos, progresión, cardio,
              suplementos, deload, margen de maniobra, «Por qué este enfoque» y el
              educativo. Solo las EQUIVALENCIAS de comida/cena quedan fuera
              (se regeneran o cambian con el swap).
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setImportPreview(null)} className="btn btn-ghost !py-1.5 text-xs">
                Descartar
              </button>
              <button
                onClick={applyImport}
                disabled={applyingImport || importPreview.changes.length === 0}
                className="btn btn-primary !py-1.5 text-xs"
              >
                {applyingImport ? <Spinner /> : <Save size={13} />} Aplicar {importPreview.changes.length} cambio{importPreview.changes.length === 1 ? "" : "s"}
              </button>
            </div>
          </div>
        )}

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
              <span
                className="flex flex-wrap items-center gap-2 text-xs text-zinc-400"
                title="14 días · se renueva solo"
              >
                Seguimiento activo · {currentPeriod.starts_on} → {currentPeriod.ends_on}
                <span className="rounded-full px-2 py-0.5 font-semibold" style={{ background: "color-mix(in srgb, var(--brand-accent-2) 15%, transparent)", color: "var(--brand-accent-2)" }}>
                  {currentPeriod.status === "open" ? "abierto" : currentPeriod.status === "closed" ? "cerrado" : "analizado"}
                </span>
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

      {/* Estructura de comidas del día: desplegable para elegir qué tomas hace el
          cliente (desayuno, media mañana, comida, snack, cena, pre-cama). Se
          inicializa con las comidas del plan actual; al cambiarlas y regenerar,
          toda la planificación (macros, estructura, PDF, portal) se readapta.
          Solo con NUTRICIÓN contratada: en un plan solo-entreno no hay comidas. */}
      {hasNutrition && (
      <MealStructureCard
        currentNames={(Array.isArray(nut.meals) ? nut.meals : []).map((m: any) => m?.name ?? "")}
        generating={generating}
        // Cliente AVANZADO: regenerar con otras comidas rehace la BASE sin IA
        // (0 créditos, sigue en borrador); al resto se lo regenera la IA.
        onRegenerate={(keys) => (client.level === "advanced" ? void scaffold(keys) : generate(keys))}
        // La base sin IA del avanzado es gratis y no pisa nada publicado; en el
        // resto, regenerar GASTA créditos y sustituye la versión actual.
        confirmText={client.level === "advanced" ? null
          : "¿Regenerar el plan con estas comidas? Gasta créditos de IA y sustituye "
            + "la versión actual, ediciones manuales incluidas (queda en el historial)."}
      />
      )}

      {/* CAMBIOS MANUALES detectados al editar (diff exacto): el sistema sabe
          que esta versión es un ajuste esporádico del coach → aviso con la
          lista de lo cambiado y envío por WhatsApp/email que LO EXPLICA. */}
      {(() => {
        const manualItems: string[] = ((nut as any)?.manual_changes?.items ?? []) as string[];
        if (!manualItems.length) return null;
        const refreshPlans = () => recargarPlanes().catch(() => {});
        const sendWa = async () => {
          const phone = waPhone(client.phone);
          if (!phone) {
            toast.push("Sin teléfono en la ficha", "error");
            return;
          }
          const win = window.open("", "_blank"); // anti-bloqueo de popups en iOS
          try {
            const pdfUrl = await planPdfUrl();
            const url = waUrl(phone, manualUpdateMessage(client.full_name, manualItems, pdfUrl));
            if (win) win.location.href = url;
            else openWhatsApp(phone, manualUpdateMessage(client.full_name, manualItems, pdfUrl));
            await api.ackManualChanges(plan.id);
            setNeedsDownload(false);
            refreshPlans();
            toast.push("WhatsApp abierto con los cambios");
          } catch {
            win?.close();
            toast.push("No se pudo preparar el envío", "error");
          }
        };
        const sendEmail = async () => {
          if (sendingUpd) return;
          setSendingUpd(true);
          try {
            const r = await api.sendPlanUpdateEmail(plan.id);
            if (r.sent) {
              toast.push("Email enviado · PDF al día");
              setNeedsDownload(false);
              refreshPlans();
            } else {
              toast.push("Email no enviado", "error");
            }
          } catch (e: any) {
            toast.push(e?.message ?? "No se pudo enviar", "error");
          } finally {
            setSendingUpd(false);
          }
        };
        const dismiss = async () => {
          await api.ackManualChanges(plan.id).catch(() => {});
          refreshPlans();
        };
        return (
          <div className="card border p-4"
            style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 8%, transparent)" }}>
            <div className="flex items-start gap-2">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent)" }} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-zinc-100">
                  Cambios manuales sin enviar
                </p>
                <ul className="mt-1.5 space-y-0.5 text-xs text-zinc-400">
                  {manualItems.slice(0, 6).map((it, i) => <li key={i}>· {it}</li>)}
                  {manualItems.length > 6 && (
                    <li className="text-zinc-500">…y {manualItems.length - 6} cambios más</li>
                  )}
                </ul>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button onClick={sendWa} className="btn btn-primary !px-3 !py-1.5 text-xs">
                    <MessageCircle size={13} /> Enviar por WhatsApp
                  </button>
                  <button onClick={sendEmail} disabled={sendingUpd} className="btn btn-ghost !px-3 !py-1.5 text-xs">
                    <Mail size={13} /> {sendingUpd ? "Enviando…" : "Enviar por email"}
                  </button>
                  <button onClick={downloadPdf} className="btn btn-ghost !px-3 !py-1.5 text-xs">
                    <Download size={13} /> PDF actualizado
                  </button>
                  <button
                    onClick={() => {
                      if (window.confirm("¿Descartar sin avisar al cliente?")) dismiss();
                    }}
                    className="ml-auto text-xs text-zinc-500 underline-offset-2 hover:underline">
                    Descartar aviso
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Tras editar: el PDF que se descargó antes queda ANTIGUO — recordatorio
          claro hasta que se vuelva a descargar (la edición ya está guardada). */}
      {needsDownload && !((nut as any)?.manual_changes?.items?.length) && (
        <div
          className="card flex flex-wrap items-center justify-between gap-3 border p-4"
          style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 8%, transparent)" }}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent)" }} />
            <p className="text-sm text-zinc-300">
              PDF antiguo sin tu edición
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
          await recargarPlanes();
          setPeriods(await api.listPeriods(client.id).catch(() => periods));
        }}
      />

      {/* Cambios PROPUESTOS por la última revisión quincenal: se ven ANTES de
          adaptar (qué cambia y por qué, dieta y entreno) y el botón va dentro.
          También sale cuando la IA no propuso texto pero la revisión automática
          SÍ decidió algo aplicable (ajuste de kcal o diet break): antes esa
          decisión se quedaba sin botón que la aplicara. */}
      {(() => {
        const decision = review?.biweekly_decision ?? null;
        const decisionAccionable = ["adjust_kcal", "diet_break"].includes(decision?.action ?? "");
        const nAjustes = review?.plan_adjustments?.length ?? 0;
        if (!review || alreadyAdapted || (!nAjustes && !decisionAccionable)) return null;
        return (
        <details open name="plan-secciones" className="card p-5" {...ancla("plan.adaptar")}
          style={{ borderColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)" }}>
          <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
            Propuestas · revisión #{review.period_index}
            <span className="ml-2 text-xs font-normal text-zinc-500">
              {nAjustes > 0
                ? `${nAjustes} ajustes · ${hasTraining ? "dieta y entrenamiento" : "dieta"}`
                : "ajuste automático de la revisión"}
            </span>
          </summary>
          <div className="mt-3 space-y-2">
            {decisionAccionable && decision && (
              <AdjustmentRow
                area="dieta"
                main={decision.action === "diet_break"
                  ? "Diet break: 7-10 días comiendo a mantenimiento"
                  : `Calorías ${(decision.kcal_delta_pct ?? 0) > 0 ? "+" : ""}${decision.kcal_delta_pct ?? 0}% (revisión automática)`}
                reason={decision.rationale ?? "Regla fija de la revisión automática sobre tu progreso real."}
              />
            )}
            {(review.plan_adjustments ?? []).map((a, i) => (
              <AdjustmentRow key={i} area={a.area} main={a.change} reason={a.reason} />
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }}>
            <p className="text-xs text-zinc-500">
              Adaptar activa la versión nueva
            </p>
            <button onClick={adapt} disabled={generating} className="btn btn-primary">
              {generating ? "Adaptando…" : `Adaptar a la revisión #${review.period_index}`}
            </button>
          </div>
        </details>
        );
      })()}

      {/* Cambios APLICADOS en esta versión (tras adaptar): antes→después + porqué.
          Queda visible también una vez publicado, como registro de la versión, y
          es EDITABLE por si el coach quiere matizar el texto o quitar un ajuste. */}
      {appliedBlock?.items?.length ? (
        <details open={plan.status !== "published"} name="plan-secciones" className="card p-5">
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
                  <ExpandableArea
                    label="Por qué"
                    value={d.reason}
                    onChange={(v) => setAdjDraft(adjDraft.map((x, j) => (j === i ? { ...x, reason: v } : x)))}
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

      {/* Nutrición (los planes Train no la incluyen: sin tarjeta de ceros) */}
      {hasNutrition && (
      <div className="card p-5">
        <SectionTitle icon={Utensils} title="Nutrición" ancla="nutricion.macros"
          onEdit={() => { setEditFocus("nutrition"); setEditing(true); }} />
        {/* Cálculo aplicado, directo: déficit/superávit sobre el TDEE */}
        {nut.tdee_kcal ? (
          <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <span
              className="rounded-full px-2.5 py-1 font-semibold"
              style={{ background: "color-mix(in srgb, var(--brand-accent) 14%, transparent)", color: "var(--brand-accent)" }}
            >
              {deficitLabel(nut.tdee_kcal, nut.target_kcal ?? 0)}
            </span>
            <span className="text-zinc-500">TDEE {Math.round(nut.tdee_kcal)} kcal</span>
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Calorías" value={`${Math.round(nut.target_kcal ?? 0)}`} />
          <Stat label="Proteína" value={`${Math.round(macros.protein_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.protein}%` : undefined} />
          <Stat label="Carbohid." value={`${Math.round(macros.carbs_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.carbs}%` : undefined} />
          <Stat label="Grasas" value={`${Math.round(macros.fat_g ?? 0)} g`} sub={(nut.target_kcal ?? 0) > 0 ? `${mp.fat}%` : undefined} />
        </div>
        {mpTotalOff && (
          <p className="mt-1.5 text-xs" style={{ color: "#9A6B15" }}>
            Macros suman {mp.total}%, no 100%
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
      )}

      {/* El BANCO DE COMIDAS no ocupa pantalla por defecto (va completo en el
          PDF del cliente), pero SÍ existe plegado: cuando un aviso señala una
          toma concreta ("hay lentejas en la toma 2"), el desplegable se abre
          solo y esa toma queda marcada. Sin eso, el coach leía el problema y
          no tenía dónde verlo. */}
      {hasNutrition && <BancoDeComidas nut={nut} />}

      {/* Entrenamiento — azul de marca (como sus chips de ajustes).
          El paquete Start es solo nutrición: no se muestra el entrenamiento. */}
      {hasTraining && (
      <div className="card p-5">
        <SectionTitle icon={Dumbbell} title={`Entrenamiento${tr.split_name ? ` · ${tr.split_name}` : ""}`} accent="var(--brand-accent-2)" ancla="entreno.sesiones"
          onEdit={() => { setEditFocus("training"); setEditing(true); }} />
        {tr.split_rationale && (
          <details className="mb-3 text-sm">
            <summary className="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">Sobre esta estructura</summary>
            <div className="mt-2 text-zinc-400"><ProseClamp text={tr.split_rationale} lines={2} /></div>
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
                  {w.volume_note && (() => {
                    const corto = resumenCorto(w.volume_note);
                    // Con `title` a secas el resto era inalcanzable en móvil:
                    // si hay más texto, se abre tocando.
                    return corto === w.volume_note.replace(/\s*\.$/, "") ? (
                      <div className="mt-0.5 text-zinc-500">{corto}</div>
                    ) : (
                      <details className="mt-0.5 text-zinc-500">
                        <summary className="cursor-pointer">{corto}</summary>
                        <p className="mt-1">{w.volume_note}</p>
                      </details>
                    );
                  })()}
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
                  const hasDetail = ex.progression_rule || ex.technique_cue || ex.biomech_cue || ex.coach_notes;
                  return (
                    // Sin name compartido: abrir un ejercicio ya NO cierra el
                    // anterior (el acordeón exclusivo queda para secciones).
                    <details key={j} className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
                      <summary className="cursor-pointer">
                        <span className="font-medium text-zinc-200">{exName(ex.exercise_id)}</span>
                        <span className="ml-1 text-zinc-400">
                          · {ex.sets}×{ex.rep_range} · RIR {ex.rir} · {ex.rest_sec}s
                          {ex.tempo ? ` · tempo ${ex.tempo}` : ""}
                          {ex.start_weight_hint_kg != null ? ` · ~${ex.start_weight_hint_kg} kg` : ""}
                        </span>
                        {exVideo[ex.exercise_id] && (
                          <a
                            href={exVideo[ex.exercise_id]}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            aria-label={`Ver vídeo de ${exName(ex.exercise_id)}`}
                            title="Ver vídeo del ejercicio"
                            className="ml-1.5 inline-flex translate-y-[2px] hover:opacity-80"
                            style={{ color: "var(--brand-accent-2)" }}
                          >
                            <PlayCircle size={14} />
                          </a>
                        )}
                      </summary>
                      {hasDetail && (
                        <div className="mt-1.5 space-y-0.5 border-t pt-1.5 pl-1 text-zinc-500" style={{ borderColor: "var(--line)" }}>
                          {ex.progression_rule && <p><b className="text-zinc-400">Progresión:</b> {ex.progression_rule}</p>}
                          {ex.technique_cue && <p><b className="text-zinc-400">Técnica:</b> {ex.technique_cue}</p>}
                          {ex.biomech_cue && <p><b className="text-zinc-400">Biomecánica:</b> {ex.biomech_cue}</p>}
                          {ex.coach_notes && (
                            <p style={{ color: "var(--brand-accent)" }}>
                              <b>Indicaciones personalizadas:</b> {ex.coach_notes}
                            </p>
                          )}
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
          <div className="mt-3 text-xs text-zinc-400">
            <b className="text-zinc-300">Descarga (deload)</b>{" "}
            <ProseClamp text={tr.deload_instructions} lines={1} />
          </div>
        )}
      </div>
      )}

      {/* PUNTOS IMPORTANTES del cliente (anamnesis): lo que condiciona el plan */}
      <ImportantPointsCard client={client} onGoTab={onGoTab} />

      {/* Suplementación */}
      {Array.isArray(nut.supplements) && nut.supplements.length > 0 && (
        <div className="card p-5">
          <SectionTitle icon={Pill} title="Suplementación" ancla="plan.suplementos"
            onEdit={() => { setEditFocus("supplements"); setEditing(true); }} />
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
        <details name="plan-secciones" className="card p-5">
          <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-zinc-100">
            <Archive size={15} style={{ color: "var(--brand-accent-2)" }} />
            Planificaciones anteriores
            <span className="text-xs font-normal text-zinc-500">{allPlans.length - 1}</span>
          </summary>
          <div className="mt-3 space-y-2">
            {archivedPlans(allPlans, plan.id).map((p) => (
              <details key={p.id} name="planes-anteriores" className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
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
                  <span>Calorías: <b className="text-zinc-200">{Math.round(p.target_kcal ?? 0)}</b></span>
                  <span>P/C/G: <b className="text-zinc-200">
                    {Math.round(p.protein_g ?? 0)}/
                    {Math.round(p.carbs_g ?? 0)}/
                    {Math.round(p.fat_g ?? 0)} g
                  </b></span>
                  {hasTraining && <span>Split: <b className="text-zinc-200">{p.split_name ?? "—"}</b></span>}
                  {hasTraining && <span>Sesiones: <b className="text-zinc-200">{p.sessions_count ?? 0}</b></span>}
                </div>
                {/* Por qué se adaptó o cambió esta versión */}
                {(p.whyChanged?.length || p.whyLabel) && (
                  <div className="border-t px-3 py-3 text-xs" style={{ borderColor: "var(--line)" }}>
                    <div className="mb-1 font-semibold uppercase tracking-wide text-zinc-500">Por qué cambió</div>
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
function archivedPlans(all: PlanSummary[], currentId: number): any[] {
  const asc = [...all].sort((a, b) => String(a.created_at ?? "").localeCompare(String(b.created_at ?? "")));
  return asc
    .map((p, i) => {
      const from = p.created_at ? new Date(p.created_at) : null;
      const siguiente = asc[i + 1]?.created_at;
      const next = siguiente ? new Date(siguiente) : new Date();
      const days = from ? Math.max(1, Math.round((next.getTime() - from.getTime()) / 86400000)) : null;
      const applied = p.applied_adjustments?.items;
      const whyChanged = (applied ?? [])
        .filter((it) => it?.change || it?.detail)
        .map((it) => ({ change: (it.detail ?? it.change) as string, reason: it.reason ?? "" }));
      const rationale: string | null = p.rationale ?? null;
      const whyLabel = whyChanged.length
        ? `Adaptación a la revisión #${p.applied_adjustments?.period_index}:`
        : rationale
          ? rationale.split("\n")[0].slice(0, 180)
          : p.generated_by === "ai"
            ? "Generado con IA · anamnesis"
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
function ImportantPointsCard({ client, onGoTab }: { client: ClientOut; onGoTab?: (tab: string) => void }) {
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
  add("Objetivo en sus palabras", client.lifestyle_notes);
  if (!blocks.length) return null;
  const RED = "#B3261E";
  const hasTraining = pkg(client.package_tier).hasTraining;
  return (
    <div className="card p-5">
      <SectionTitle icon={AlertTriangle} title="Puntos importantes del cliente" />
      <div className="mb-2 flex flex-wrap items-baseline gap-x-2 text-xs">
        <span className="text-zinc-500">Respetar en {hasTraining ? "dieta y entreno" : "dieta"}</span>
        {/* Un clic para ir a corregirlo: salen de la anamnesis y hasta ahora
            había que buscar la pestaña a mano. */}
        {onGoTab && (
          <button type="button" onClick={() => onGoTab("anamnesis")}
            className="font-medium text-zinc-500 underline decoration-dotted underline-offset-2 hover:text-zinc-300">
            → Editar en Anamnesis
          </button>
        )}
      </div>
      <div className="space-y-2">
        {blocks.map((b) => {
          const nCrit = b.lines.filter(isCriticalLine).length;
          return (
            <MemoDetails
              key={b.label}
              memoKey={`imp:${client.id}:${b.label}`}
              defaultOpen={false}
              className="rounded-lg border-l-2 px-3 py-2"
              style={{
                background: "var(--surface-raised)",
                borderLeftColor: nCrit > 0 ? RED : "transparent",
              }}
              summary={
                <span className="flex flex-1 items-center gap-2 text-xs font-semibold text-zinc-300">
                  <span className="min-w-0 flex-1">{b.label}</span>
                  {nCrit > 0 && (
                    <span
                      className="shrink-0 whitespace-nowrap rounded-full px-1.5 py-0.5 text-[10px] font-bold text-white"
                      style={{ background: RED }}
                    >
                      {nCrit} a vigilar
                    </span>
                  )}
                </span>
              }
            >
              {/* RESUMIDO: al abrir se ve solo lo crítico; el resto queda tras
                  "ver todo" para no ahogar la lectura. */}
              <div className="mt-1 space-y-0.5 text-xs">
                {b.lines.filter(isCriticalLine).map((l, i) => (
                  <p key={i} className="font-medium" style={{ color: RED }}>{l}</p>
                ))}
                {(() => {
                  const resto = b.lines.filter((l) => !isCriticalLine(l));
                  if (!resto.length) return null;
                  if (!b.lines.some(isCriticalLine)) {
                    // Sin nada crítico: se muestra el contenido directamente.
                    return resto.map((l, i) => <p key={i} className="text-zinc-400">{l}</p>);
                  }
                  return (
                    <details className="pt-1">
                      <summary className="cursor-pointer text-[11px] font-medium text-zinc-500 hover:text-zinc-300">
                        ver todo ({resto.length} más)
                      </summary>
                      <div className="mt-1 space-y-0.5">
                        {resto.map((l, i) => <p key={i} className="text-zinc-400">{l}</p>)}
                      </div>
                    </details>
                  );
                })()}
              </div>
            </MemoDetails>
          );
        })}
      </div>
    </div>
  );
}

/** Selector de la estructura de comidas del día. El cliente declara sus tomas en
 *  la anamnesis y la IA reparte los macros entre ellas, pero desde aquí el coach
 *  puede rehacer ese reparto: marca qué comidas quiere (mín. 2) y "Regenerar"
 *  vuelve a generar el plan con esa estructura — toda la info (macros, comidas,
 *  PDF y portal) se readapta. Se inicializa con las comidas del plan vigente. */
function MealStructureCard({
  currentNames,
  generating,
  onRegenerate,
  confirmText,
}: {
  currentNames: string[];
  generating: boolean;
  onRegenerate: (keys: string[]) => void;
  /** Confirmación previa (gasto de créditos + pisa ediciones); null = directo. */
  confirmText?: string | null;
}) {
  const currentKeys = mealKeysFromNames(currentNames);
  const [sel, setSel] = useState<string[]>(currentKeys);
  // Al regenerar el plan cambian las comidas: resincroniza la selección con la
  // estructura vigente para que el desplegable no quede desfasado.
  const sig = currentKeys.join(",");
  useEffect(() => {
    setSel(currentKeys);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig]);

  const orderedKeys = CANONICAL_MEALS.map((m) => m.key).filter((k) => sel.includes(k));
  const changed = orderedKeys.join(",") !== sig;
  const tooFew = orderedKeys.length < 2;

  function toggle(key: string) {
    setSel((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  return (
    <details name="plan-secciones" className="card p-5">
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 text-sm font-semibold text-zinc-100">
        <span className="flex items-center gap-2">
          <Utensils size={16} style={{ color: "var(--brand-accent-2)" }} />
          Estructura de comidas del día
        </span>
        <span className="text-xs font-normal text-zinc-500">
          {orderedKeys.length} {orderedKeys.length === 1 ? "toma" : "tomas"}
        </span>
      </summary>

      <p className="mt-2 text-xs text-zinc-500">
        Marca qué comidas hace el cliente. Al regenerar, la IA reparte los macros
        entre las tomas elegidas y toda la planificación se readapta.
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        {CANONICAL_MEALS.map((m) => {
          const on = sel.includes(m.key);
          return (
            <button
              key={m.key}
              type="button"
              onClick={() => toggle(m.key)}
              aria-pressed={on}
              className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
              style={
                on
                  ? {
                      background: "color-mix(in srgb, var(--brand-accent-2) 16%, transparent)",
                      borderColor: "color-mix(in srgb, var(--brand-accent-2) 55%, transparent)",
                      color: "var(--brand-accent-2)",
                    }
                  : { background: "var(--surface-raised)", borderColor: "var(--line)", color: "#8A8172" }
              }
            >
              {m.name}
              <span className="ml-1.5 opacity-60">{m.time}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => {
            if (confirmText && !window.confirm(confirmText)) return;
            onRegenerate(orderedKeys);
          }}
          disabled={generating || tooFew || !changed}
          className="btn btn-primary"
        >
          <Sparkles size={15} /> {generating ? "Regenerando…" : "Regenerar con estas comidas"}
        </button>
        {tooFew ? (
          <span className="text-xs text-zinc-500">Selecciona al menos 2 comidas.</span>
        ) : !changed ? (
          <span className="text-xs text-zinc-500">Estructura actual del plan</span>
        ) : (
          <span className="text-xs" style={{ color: "var(--brand-accent-2)" }}>
            Rehará el plan · {orderedKeys.length} tomas
          </span>
        )}
      </div>
    </details>
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
  const info = pkg(client.package_tier);
  const hasTraining = info.hasTraining;
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
      toast.push("Mantenido · revisión en 45 días");
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
      toast.push(`Objetivo ${GOAL_LABEL[newGoal as GoalType]} · generando plan…`);
      onClientChanged?.();
      if (client.level === "advanced") {
        // Avanzado: el objetivo nuevo rehace la BASE sin IA (0 créditos) y
        // queda en borrador — el coach la termina y la activa.
        await api.scaffoldPlan(client.id, currentMonth + 1);
        await onRegenerated();
        toast.push("Base del objetivo nuevo lista");
      } else {
        await api.generatePlan(client.id, currentMonth + 1);
        await onRegenerated();
        toast.push(`Plan del objetivo nuevo ACTIVO`);
      }
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
      name="plan-secciones"
      className="card p-5"
      {...ancla("plan.objetivo")}
      style={due != null ? { borderColor: "color-mix(in srgb, var(--brand-accent) 55%, transparent)" } : undefined}
    >
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 text-sm font-semibold text-zinc-100">
        <span className="flex flex-wrap items-center gap-2">
          <Flag size={15} style={{ color: "var(--brand-accent-2)" }} />
          Objetivo: {client.goal_type ? GOAL_LABEL[client.goal_type] : "—"}
          {days != null && <span className="text-xs font-normal text-zinc-500">{days} días en esta etapa</span>}
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
            ? `${due} días con este objetivo`
            : "Cambio de objetivo cuando toque"}
        </p>

        {analysis === null ? (
          <button onClick={generateAnalysis} disabled={analyzing} className="btn btn-ghost">
            <Sparkles size={14} /> {analyzing ? "Generando análisis…" : "Generar análisis de la etapa"}
          </button>
        ) : (
          <div className="rounded-lg border p-3" style={{ borderColor: "color-mix(in srgb, var(--brand-accent-2) 25%, transparent)", background: "color-mix(in srgb, var(--brand-accent-2) 5%, transparent)" }}>
            <p className="whitespace-pre-line text-sm text-zinc-300">{analysis}</p>
            <button
              onClick={() => void copiarConAviso(analysis, toast, "Análisis copiado")}
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
            Se cambiará el objetivo, se generará una planificación completamente nueva ({hasTraining ? "dieta y entrenamiento" : "dieta"}) con todo su historial en cuenta, y la actual quedará archivada abajo
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

/**
 * Las comidas de cada toma, PLEGADAS.
 *
 * El coach no las necesita en pantalla el 99% del tiempo (van completas en el
 * PDF del cliente), así que por defecto ocupan una línea. Pero tienen que
 * EXISTIR: cuando un aviso dice "hay lentejas en la toma 2 y es alérgica", el
 * desplegable se abre solo y esa toma queda marcada — antes el coach leía el
 * problema y no tenía dónde mirarlo.
 *
 * Solo lectura: el banco se cambia regenerando o subiendo el Word editado.
 */
function BancoDeComidas({ nut }: { nut: any }) {
  const bank = nut?.meal_bank;
  const nombres = new Map<number, string>(
    (Array.isArray(nut?.meals) ? nut.meals : [])
      .map((m: any) => [m?.slot, m?.time ? `${m.name} · ${m.time}` : m?.name]),
  );

  // Las dos formas del banco se aplanan a lo mismo: toma → líneas de texto.
  const porToma = new Map<number, string[]>();
  if (bank?.mode === "strict" && Array.isArray(bank.days)) {
    for (const d of bank.days) {
      for (const m of d?.meals ?? []) {
        if (m?.slot == null) continue;
        const t = (m.dish?.title ?? "").trim();
        if (!t) continue;
        const lista = porToma.get(m.slot) ?? [];
        lista.push(`${String(d?.day ?? "").slice(0, 3)}: ${t}`);
        porToma.set(m.slot, lista);
      }
    }
  } else if (Array.isArray(bank?.slots)) {
    for (const sb of bank.slots) {
      if (sb?.slot == null) continue;
      const lista: string[] = [];
      for (const opt of sb.options ?? []) {
        const t = (opt?.title ?? "").trim();
        if (t) lista.push(t);
      }
      for (const g of sb.equivalences?.groups ?? []) {
        const t = (g?.label ?? g?.name ?? "").trim();
        if (t) lista.push(t);
      }
      if (lista.length) porToma.set(sb.slot, lista);
    }
  }
  if (!porToma.size) return null;

  const tomas = [...porToma.keys()].sort((a, b) => a - b);
  const total = [...porToma.values()].reduce((n, l) => n + l.length, 0);

  return (
    <details name="plan-secciones" className="card p-5">
      <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
        Comidas de cada toma
        <span className="ml-2 text-xs font-normal text-zinc-500">
          {tomas.length} tomas · {total} opciones · solo lectura
        </span>
      </summary>
      <div className="mt-3 space-y-2">
        {tomas.map((slot) => (
          <div key={slot} {...ancla(`nutricion.comida.${slot}`)}
            className="well px-3 py-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
              {nombres.get(slot) ?? `Toma ${slot}`}
            </p>
            <ul className="mt-1 space-y-0.5">
              {porToma.get(slot)!.map((t, i) => (
                <li key={i} className="text-xs text-zinc-400">· {t}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Para cambiarlas: regenera el plan, o descarga el Word, edítalo y súbelo.
      </p>
    </details>
  );
}

function SectionTitle({ icon: Icon, title, accent, onEdit, ancla: nombreAncla }: {
  icon: typeof Utensils; title: string; accent?: string;
  /** Edición POR BLOQUE: abre el editor enfocado y resaltado en esta sección. */
  onEdit?: () => void;
  /** Ancla del apartado: un aviso puede señalarlo y quedará marcado. */
  ancla?: string;
}) {
  const c = accent ?? "var(--brand-accent)";
  return (
    <div className="mb-3 flex items-center gap-2.5"
      {...(nombreAncla ? ancla(nombreAncla) : {})}>
      {onEdit && (
        <button
          onClick={onEdit}
          className="btn btn-ghost order-last ml-auto !px-2.5 !py-1 text-xs"
          title={`Editar ${title.toLowerCase()}`}
        >
          <Pencil size={12} /> Editar
        </button>
      )}
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

/** Avisos del plan agrupados por tema, cada uno como "TÍTULO CORTO → acción".
 *
 *  Sustituye al muro de párrafos rojos: el coach ve de un vistazo cuántos hay,
 *  de qué tipo son y qué tiene que hacer con cada uno. El texto completo del
 *  hallazgo queda como detalle, a un clic. */
/**
 * El selector de la biblioteca: los MODELOS guardados y el plan de cada
 * cliente, cada uno con su resumen de una línea, para elegir sin abrir nada.
 * Elegir crea un BORRADOR para este cliente con las cifras recalculadas.
 */
function SelectorDeBiblioteca({ clienteId, onElegir, onCerrar }: {
  clienteId: number;
  onElegir: (source: { plan_id?: number; template_id?: number }) => void;
  onCerrar: () => void;
}) {
  const [lib, setLib] = useState<Awaited<ReturnType<typeof api.planLibrary>> | null>(null);
  const [fallo, setFallo] = useState(false);
  const [intento, setIntento] = useState(0);
  const caja = useRef<HTMLDivElement>(null);
  useDismiss(caja, onCerrar, true);
  useModalFocus(caja, true);

  useEffect(() => {
    setFallo(false);
    api.planLibrary().then(setLib).catch(() => setFallo(true));
  }, [intento]);

  const otros = (lib?.client_plans ?? []).filter((p) => p.client_id !== clienteId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div ref={caja} role="dialog" aria-modal="true" aria-label="Elegir base"
        className="card w-full max-w-lg p-5" style={{ background: "var(--surface-raised)" }}>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">Elegir base</h3>
            <p className="mt-0.5 text-xs text-zinc-500">
              Se copia la estructura; kcal y macros se recalculan para este cliente.
            </p>
          </div>
          <button onClick={onCerrar} aria-label="Cerrar" className="tap -m-1 p-1 text-zinc-500 hover:text-zinc-300">
            <X size={16} />
          </button>
        </div>

        {fallo ? (
          <div className="mt-4 text-center">
            <p className="text-sm text-zinc-400">No se pudo cargar la biblioteca.</p>
            <button onClick={() => setIntento((n) => n + 1)} className="btn btn-ghost mt-2 text-xs">
              Reintentar
            </button>
          </div>
        ) : lib === null ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : (
          <div className="mt-3 max-h-[55vh] space-y-4 overflow-y-auto">
            <section>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Modelos guardados · {lib.templates.length}
              </p>
              {lib.templates.length === 0 ? (
                <p className="text-xs text-zinc-500">
                  Aún no hay: abre el plan de un cliente → menú «Más» → «Guardar como modelo».
                </p>
              ) : (
                <ul className="space-y-1.5">
                  {lib.templates.map((t) => (
                    <li key={t.id}>
                      <button onClick={() => onElegir({ template_id: t.id })}
                        className="well w-full px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface)]">
                        <span className="block text-sm font-medium text-zinc-100">{t.title}</span>
                        <span className="mt-0.5 block text-xs text-zinc-500">{t.summary ?? ""}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Planes de tus clientes · {otros.length}
              </p>
              {otros.length === 0 ? (
                <p className="text-xs text-zinc-500">Ningún otro cliente tiene plan todavía.</p>
              ) : (
                <ul className="space-y-1.5">
                  {otros.map((p) => (
                    <li key={p.plan_id}>
                      <button onClick={() => onElegir({ plan_id: p.plan_id })}
                        className="well w-full px-3 py-2.5 text-left transition-colors hover:bg-[var(--surface)]">
                        <span className="flex items-center gap-2 text-sm font-medium text-zinc-100">
                          {p.client_name}
                          {p.status !== "published" && (
                            <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                              style={{ background: "rgba(38,33,26,0.08)", color: "#7A7060" }}>
                              borrador
                            </span>
                          )}
                        </span>
                        <span className="mt-0.5 block text-xs text-zinc-500">{p.summary}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

/** Identidad estable de un aviso del plan: destino + título normalizado. No
 *  hay id en el backend, pero el par destino/título sí sobrevive a que el
 *  revisor reformule el detalle. */
function clavePlan(destino: string, titulo: string): string {
  return `${destino}|${titulo.toLowerCase().replace(/\s+/g, " ").trim()}`;
}

function AvisosBlock({ tono, cabecera, findings, flags, onIr, degraded = 0, plegado = false }: {
  tono: "rojo" | "ambar";
  cabecera: string;
  onIr: (destino: Destino, aviso?: { titulo: string; accion: string }) => void;
  findings: { severity: string; description: string; title?: string; action?: string; correccion_propuesta?: string }[];
  flags: string[];
  degraded?: number;
  plegado?: boolean;
}) {
  const [abierto, setAbierto] = useState(!plegado);
  const color = tono === "rojo" ? "#B91C1C" : "#B45309";
  const grupos = agrupar(findings.map(toAviso));

  return (
    <div className="mt-2 rounded-lg border-l-2 px-3 py-2"
      style={{ borderLeftColor: color, background: `color-mix(in srgb, ${color} 6%, transparent)` }}>
      <button
        type="button"
        onClick={() => setAbierto((o) => !o)}
        className="flex w-full items-center gap-1.5 text-left text-xs font-semibold"
        style={{ color }}
      >
        <ChevronRight size={13} className="shrink-0 transition-transform"
          style={{ transform: abierto ? "rotate(90deg)" : "none" }} />
        {tono === "rojo" ? "▲ " : ""}{cabecera}
      </button>

      {abierto && (
        <div className="mt-1.5 space-y-2">
          {/* Cada grupo, una TARJETA propia: sin separación real, los bloques
              se leían como una lista continua imposible de escanear. */}
          {grupos.map((g) => (
            <div key={g.categoria} className="rounded-md p-2"
              style={{ background: "var(--surface)" }}>
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wider"
                style={{ color, opacity: 0.75 }}>
                {g.categoria} <span className="opacity-60">· {g.items.length}</span>
              </p>
              <ul className="space-y-1.5">
                {g.items.map((a, i) => (
                  <li key={i} className="border-l-2 pl-2"
                    style={{ borderLeftColor: `color-mix(in srgb, ${color} 35%, transparent)` }}>
                    <details {...grupo("avisos-del-plan")}>
                      <summary className="cursor-pointer text-xs leading-snug">
                        <span className="font-semibold" style={{ color }}>{a.titulo}</span>
                        {a.veces > 1 && (
                          <span className="ml-1 rounded px-1 text-[10px] font-bold"
                            style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}
                            title={`${a.veces} revisores señalaron lo mismo`}>
                            ×{a.veces}
                          </span>
                        )}
                        {/* La acción LLEVA al sitio: un clic y estás donde se
                            arregla, sin buscar la pestaña ni el botón. */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault(); e.stopPropagation();
                            onIr(a.destino, { titulo: a.titulo, accion: a.accion });
                          }}
                          className="ml-1 font-medium text-zinc-500 underline decoration-dotted underline-offset-2 hover:text-zinc-300"
                        >
                          → {a.accion}
                        </button>
                      </summary>
                      {/* Detalle YA RESUMIDO: al fusionar varios revisores el
                          texto repetía lo mismo tres veces. */}
                      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-zinc-500">
                        {resumirDetalle(a.detalle).map((f, j) => <li key={j}>{f}</li>)}
                      </ul>
                      {/* El resumen elige; el original SIEMPRE queda accesible. */}
                      <details className="mt-1 pl-4">
                        <summary className="cursor-pointer text-[11px] text-zinc-500">texto completo</summary>
                        <p className="mt-1 whitespace-pre-line text-[11px] text-zinc-500">{a.detalle}</p>
                      </details>
                    </details>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {flags.length > 0 && (
            <ul className="space-y-0.5 text-xs" style={{ color }}>
              {flags.map((f, i) => <li key={i}>• {f}</li>)}
            </ul>
          )}
          {degraded > 0 && (
            <p className="text-xs" style={{ color }}>
              Revisión incompleta ({degraded} sin ejecutar) → repásalo tú
            </p>
          )}
        </div>
      )}
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
      <div className="whitespace-nowrap text-lg font-bold tabular-nums" style={{ color: "var(--brand-accent)" }}>{value}</div>
      <div className="mt-0.5 flex flex-wrap items-center justify-center gap-x-1.5 text-xs text-zinc-500">
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
