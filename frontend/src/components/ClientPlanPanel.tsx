import { useEffect, useState } from "react";
import { Sparkles, Download, Send, AlertTriangle, Dumbbell, Utensils, Pill, CalendarDays, Pencil } from "lucide-react";
import { api, getToken } from "../lib/api";
import { Spinner, useToast } from "./ui";
import { ClientPlanEditor } from "./ClientPlanEditor";
import type { ClientOut } from "../types";

interface PlanData {
  id: number;
  month_index: number;
  version: number;
  status: string;
  guardrail_flags: string[];
  nutrition: any;
  training: any;
  education: any;
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
  };
}

/**
 * Planificación: genera el plan mensual con IA a partir de la anamnesis, lo
 * PERSISTE (al volver a la pestaña se recarga el último plan guardado), muestra
 * TODA la info (nutrición, banco de comidas, entrenamiento, educativo) y permite
 * publicarlo y descargarlo en Word.
 */
export function ClientPlanPanel({ client }: { client: ClientOut }) {
  const toast = useToast();
  const [plan, setPlan] = useState<PlanData | null>(null);
  const [exMap, setExMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [startingPeriod, setStartingPeriod] = useState(false);
  const [editing, setEditing] = useState(false);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [periods, setPeriods] = useState<{
    id: number; period_index: number; plan_id: number | null; starts_on: string; ends_on: string; status: string;
    plan_adjustments?: { area: string; change: string; reason: string }[] | null;
  }[]>([]);

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
        if (plans.length) setPlan(normalize(plans[0])); // [0] = versión más reciente
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [client.id]);

  async function startPeriod() {
    if (!plan || startingPeriod) return;
    setStartingPeriod(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api.createPeriod(client.id, plan.id, today, 14);
      setPeriods(await api.listPeriods(client.id));
      toast.push("Seguimiento iniciado (14 días). El cliente ya puede registrar su diario.");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo iniciar el período", "error");
    } finally {
      setStartingPeriod(false);
    }
  }

  async function generate() {
    if (generating) return;
    setGenerating(true);
    setMissing(null);
    try {
      const p = await api.generatePlan(client.id, plan?.month_index ?? 1);
      setPlan(normalize(p));
      toast.push("Planificación generada");
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      if (detail?.missing) setMissing(detail.missing);
      else toast.push(detail?.message ?? e?.message ?? "No se pudo generar el plan", "error");
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
      const full = plans.find((pl) => pl.id === r.id) ?? plans[0]; // listPlans → más reciente primero
      if (full) setPlan(normalize(full));
      toast.push(`Plan adaptado a la revisión (borrador v${r.version}). Revísalo y publícalo.`);
    } catch (e: any) {
      const detail = e?.detail ?? e?.data?.detail;
      toast.push(detail?.message ?? e?.message ?? "No se pudo adaptar el plan", "error");
    } finally {
      setGenerating(false);
    }
  }

  async function publish() {
    if (!plan || publishing) return;
    setPublishing(true);
    try {
      await api.publishPlan(plan.id);
      setPlan({ ...plan, status: "published" });
      toast.push(
        plan.nutrition?.applied_adjustments
          ? "Plan publicado: el portal ya muestra la rutina nueva y el PDF está actualizado — descárgalo y envíaselo al cliente"
          : "Plan publicado: ya es visible en el portal del cliente",
      );
    } catch {
      toast.push("No se pudo publicar", "error");
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
              anamnesis. Podrás revisarlo, publicarlo y descargarlo.
            </p>

            {missing && (
              <div className="mt-4 rounded-lg border p-3" style={{ borderColor: "#7a5b1a", background: "rgba(247,201,110,0.08)" }}>
                <div className="flex items-center gap-2 text-sm font-medium text-amber-300">
                  <AlertTriangle size={15} /> Faltan datos en la anamnesis
                </div>
                <p className="mt-1 text-xs text-zinc-400">
                  Completa estos campos en la pestaña <b>Anamnesis</b> antes de generar:
                </p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {missing.map((m) => (
                    <li key={m} className="rounded-md px-2 py-0.5 text-xs" style={{ background: "rgba(247,201,110,0.15)", color: "#F7C96E" }}>
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
    return (
      <ClientPlanEditor
        plan={plan}
        exMap={exMap}
        onSaved={(p) => { setPlan(p); setEditing(false); }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  // ---------- Plan generado / guardado: vista completa ----------
  const nut = plan.nutrition ?? {};
  const tr = plan.training ?? {};
  const macros = nut.macros ?? {};
  const mealBank = nut.meal_bank ?? null;
  const exName = (id: number) => exMap[id] ?? `Ejercicio #${id}`;
  const currentPeriod = periods.find((p) => p.plan_id === plan.id);

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
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-zinc-100">Planificación · Mes {plan.month_index}</h3>
              <span
                className="rounded-full px-2 py-0.5 text-xs font-medium"
                style={
                  plan.status === "published"
                    ? { background: "color-mix(in srgb, var(--brand-accent) 15%, transparent)", color: "var(--brand-accent)" }
                    : { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" }
                }
              >
                {plan.status === "published" ? "Publicado" : "Borrador"} · v{plan.version}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-zinc-500">
              Revisa el plan. Cuando esté listo, publícalo (lo verá el cliente) y descárgalo.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setEditing(true)} className="btn btn-ghost">
              <Pencil size={15} /> Editar
            </button>
            <button onClick={downloadPdf} className="btn btn-ghost">
              <Download size={15} /> Descargar PDF
            </button>
            {plan.status !== "published" && (
              <button onClick={publish} disabled={publishing} className="btn btn-primary">
                <Send size={15} /> {publishing ? "Publicando…" : "Publicar"}
              </button>
            )}
          </div>
        </div>

        {/* Seguimiento: tras publicar, iniciar el período para que el cliente
            registre el diario en el portal (cierra el ciclo hacia el feedback). */}
        {plan.status === "published" && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            {currentPeriod ? (
              <span className="flex items-center gap-2 text-xs text-zinc-400">
                <CalendarDays size={14} style={{ color: "var(--brand-accent)" }} />
                Seguimiento activo · {currentPeriod.starts_on} → {currentPeriod.ends_on}
                <span className="rounded-full px-2 py-0.5" style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)", color: "var(--brand-accent)" }}>
                  {currentPeriod.status === "open" ? "abierto" : currentPeriod.status === "closed" ? "cerrado" : "analizado"}
                </span>
              </span>
            ) : (
              <>
                <span className="text-xs text-zinc-500">Inicia el seguimiento para que el cliente registre su diario y, al cerrarlo, puedas generar el feedback.</span>
                <button onClick={startPeriod} disabled={startingPeriod} className="btn btn-ghost">
                  <CalendarDays size={15} /> {startingPeriod ? "Iniciando…" : "Iniciar seguimiento (14 días)"}
                </button>
              </>
            )}
          </div>
        )}
      </div>

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
              Al adaptar se crea un <b className="text-zinc-300">borrador nuevo</b> con los ajustes numéricos ya
              aplicados (macros y cargas). Después podrás verlo, editarlo y publicarlo.
            </p>
            <button onClick={adapt} disabled={generating} className="btn btn-primary">
              {generating ? "Adaptando…" : `Adaptar a la revisión #${review.period_index}`}
            </button>
          </div>
        </details>
      ) : null}

      {/* Cambios APLICADOS en esta versión (tras adaptar): antes→después + porqué.
          Queda visible también una vez publicado, como registro de la versión. */}
      {appliedBlock?.items?.length ? (
        <details open={plan.status !== "published"} className="card p-5">
          <summary className="cursor-pointer text-sm font-semibold text-zinc-100">
            Cambios aplicados en esta versión
            <span className="ml-2 text-xs font-normal text-zinc-500">revisión #{appliedBlock.period_index}</span>
          </summary>
          <div className="mt-3 space-y-2">
            {appliedBlock.items.map((it, i) => (
              <AdjustmentRow
                key={i}
                area={it.area}
                main={it.detail ?? it.change}
                secondary={it.detail ? it.change : undefined}
                reason={it.reason}
                manual={!it.applied}
              />
            ))}
          </div>
          {plan.status !== "published" && (
            <p className="mt-3 border-t pt-3 text-xs text-zinc-500" style={{ borderColor: "var(--line)" }}>
              Revisa cómo ha quedado, <b className="text-zinc-300">edita</b> lo que quieras (los ajustes marcados
              como "a mano" no se aplican solos) y <b className="text-zinc-300">publica</b>: el cliente verá la
              rutina nueva en su portal y el PDF quedará actualizado para enviárselo.
            </p>
          )}
        </details>
      ) : null}

      {/* Nutrición */}
      <div className="card p-5">
        <SectionTitle icon={Utensils} title="Nutrición" />
        <div className="grid grid-cols-4 gap-2">
          {[
            ["Calorías", `${Math.round(nut.target_kcal ?? 0)}`],
            ["Proteína", `${Math.round(macros.protein_g ?? 0)} g`],
            ["Carbohid.", `${Math.round(macros.carbs_g ?? 0)} g`],
            ["Grasas", `${Math.round(macros.fat_g ?? 0)} g`],
          ].map(([label, val]) => (
            <Stat key={label} label={label} value={val} />
          ))}
        </div>
        {nut.tdee_kcal != null && (
          <p className="mt-2 text-xs text-zinc-500">TDEE estimado: {Math.round(nut.tdee_kcal)} kcal</p>
        )}
        {nut.rationale && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-medium text-zinc-400 hover:text-zinc-200">Justificación de la nutrición</summary>
            <p className="mt-2 text-zinc-400">{nut.rationale}</p>
          </details>
        )}
        {nut.refeed_or_break && (
          <p className="mt-2 text-xs text-zinc-400"><b className="text-zinc-300">Recarga / descanso:</b> {nut.refeed_or_break}</p>
        )}

        {Array.isArray(nut.meals) && nut.meals.length > 0 && (
          <div className="mt-4">
            <h5 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Objetivos por comida</h5>
            <div className="space-y-1.5">
              {nut.meals.map((m: any) => (
                <div key={m.slot} className="flex items-center justify-between rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <span className="text-zinc-300">{m.time} · {m.name}</span>
                  <span className="text-zinc-500">
                    {Math.round(m.target?.kcal ?? 0)} kcal · P{Math.round(m.target?.protein_g ?? 0)} / C{Math.round(m.target?.carbs_g ?? 0)} / G{Math.round(m.target?.fat_g ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {Array.isArray(nut.flexibility_rules) && nut.flexibility_rules.length > 0 && (
          <div className="mt-3">
            <h5 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">Reglas de flexibilidad</h5>
            <ul className="list-disc space-y-0.5 pl-5 text-xs text-zinc-400">
              {nut.flexibility_rules.map((r: string, i: number) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
      </div>

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

      {/* Banco de comidas */}
      {mealBank && (
        <div className="card p-5">
          <SectionTitle icon={Utensils} title={`Banco de comidas (${mealBank.mode === "strict" ? "menú cerrado" : "equivalencias"})`} />
          {mealBank.mode === "flexible_7" && Array.isArray(mealBank.slots) ? (
            <div className="space-y-3">
              {mealBank.slots.map((slot: any) => (
                <details key={slot.slot} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-zinc-200">
                    Comida {slot.slot} · {slot.options?.length ?? 0} opciones
                  </summary>
                  <div className="space-y-2 px-3 pb-3">
                    {slot.options?.map((o: any) => <MealOption key={o.key ?? o.title} o={o} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : mealBank.mode === "strict" && Array.isArray(mealBank.days) ? (
            <div className="space-y-3">
              {mealBank.days.map((d: any) => (
                <details key={d.day} className="rounded-lg" style={{ background: "var(--surface-raised)" }}>
                  <summary className="cursor-pointer px-3 py-2 text-sm font-medium capitalize text-zinc-200">{d.day}</summary>
                  <div className="space-y-2 px-3 pb-3">
                    {d.meals?.map((m: any, i: number) => <MealOption key={i} o={m.dish} prefix={`Comida ${m.slot}: `} />)}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500">Sin banco de comidas.</p>
          )}
        </div>
      )}

      {/* Entrenamiento */}
      <div className="card p-5">
        <SectionTitle icon={Dumbbell} title={`Entrenamiento${tr.split_name ? ` · ${tr.split_name}` : ""}`} />
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
                <div key={w.week} className="rounded-lg p-2.5 text-xs" style={{ background: "var(--surface-raised)" }}>
                  <div className="font-semibold text-zinc-200">Sem {w.week} · {w.intent}</div>
                  <div className="text-zinc-500">Carga {w.load_pct}% · RIR {w.rir_target}</div>
                  {w.volume_note && <div className="mt-0.5 text-zinc-500">{w.volume_note}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {(tr.sessions ?? []).map((s: any, i: number) => (
            <div key={i} className="rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
              <div className="text-sm font-medium text-zinc-200">{s.day} · {s.name}</div>
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
            </div>
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

      <button onClick={generate} disabled={generating} className="btn btn-ghost text-xs">
        <Sparkles size={14} /> {generating ? "Regenerando…" : "Regenerar plan (nueva versión)"}
      </button>
    </div>
  );
}

/** Fila de un ajuste de la revisión: chip de área + cambio + porqué. */
function AdjustmentRow({ area, main, secondary, reason, manual }: {
  area: string; main: string; secondary?: string; reason: string; manual?: boolean;
}) {
  const isDiet = /diet|nutri/i.test(area);
  const isTrain = /entren|train/i.test(area);
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
          style={isDiet
            ? { background: "color-mix(in srgb, var(--brand-accent) 18%, transparent)", color: "var(--brand-accent)" }
            : isTrain
              ? { background: "color-mix(in srgb, var(--brand-accent-2, #4C7DB0) 22%, transparent)", color: "var(--brand-accent-2, #7FA8CF)" }
              : { background: "rgba(255,255,255,0.08)", color: "#a1a1aa" }}
        >
          {isDiet ? "Dieta" : isTrain ? "Entreno" : area || "General"}
        </span>
        <span className="text-sm font-medium text-zinc-100">{main}</span>
        {manual && (
          <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: "rgba(247,201,110,0.15)", color: "#F7C96E" }}>
            aplicar a mano
          </span>
        )}
      </div>
      {secondary && <p className="mt-0.5 text-xs text-zinc-500">{secondary}</p>}
      {reason && <p className="mt-1 text-xs text-zinc-400"><b className="text-zinc-500">Por qué:</b> {reason}</p>}
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: typeof Utensils; title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{title}</h4>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-3 text-center" style={{ background: "var(--surface-raised)" }}>
      <div className="text-lg font-bold" style={{ color: "var(--brand-accent)" }}>{value}</div>
      <div className="text-xs text-zinc-500">{label}</div>
    </div>
  );
}

function MealOption({ o, prefix = "" }: { o: any; prefix?: string }) {
  if (!o) return null;
  const m = o.macros ?? {};
  return (
    <div className="rounded-md p-2 text-xs" style={{ background: "var(--surface)" }}>
      <div className="flex flex-wrap items-baseline justify-between gap-1">
        <span className="font-medium text-zinc-200">
          {prefix}{o.key ? `${o.key}. ` : ""}{o.title}
        </span>
        <span className="text-zinc-500">
          {Math.round(m.kcal ?? 0)} kcal · P{Math.round(m.protein_g ?? 0)} / C{Math.round(m.carbs_g ?? 0)} / G{Math.round(m.fat_g ?? 0)}
          {o.prep_minutes != null ? ` · ${o.prep_minutes} min` : ""}
        </span>
      </div>
      {Array.isArray(o.ingredients) && o.ingredients.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-zinc-400">
          {o.ingredients.map((ing: any, i: number) => (
            <li key={i}>{ing.food} · {ing.grams} g <span className="text-zinc-500">({ing.household})</span></li>
          ))}
        </ul>
      )}
      {o.prep && <p className="mt-1 text-zinc-500">{o.prep}</p>}
      {Array.isArray(o.tags) && o.tags.length > 0 && (
        <p className="mt-0.5 text-zinc-600">{o.tags.join(" · ")}</p>
      )}
    </div>
  );
}
