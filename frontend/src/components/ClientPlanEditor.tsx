import { useRef, useState } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell, Target, AlertTriangle, Check } from "lucide-react";
import { api } from "../lib/api";
import {
  GOAL_RULES, goalTargets, kcalOf, macrosForKcal, macrosScaledToKcal, rescaledFrom,
  deficitLabel, deficitOptions, deficitSelectValue, kcalFromDeficit, macroPct, gramsFromPct,
  MACRO_TOTAL_TOLERANCE,
  type MacroTargets,
} from "../lib/nutritionTargets";
import { GOAL_LABEL } from "../lib/format";
import { Spinner, useToast } from "./ui";
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

/**
 * Editor manual del plan (revisión del coach antes de enviar). Edita nutrición,
 * entrenamiento y educativo y los guarda (PATCH /plans/{id}). El banco de comidas
 * no se edita aquí (se muestra en la vista); cambiar un ejercicio por otro se hace
 * con el "swap". Guarda el JSON tal cual: los guardrails no se re-ejecutan (es
 * edición del coach bajo su criterio).
 */
export function ClientPlanEditor({
  plan, exMap, onSaved, onCancel, client, refWeightKg,
}: {
  plan: PlanData;
  exMap: Record<number, string>;
  onSaved: (p: PlanData) => void;
  onCancel: () => void;
  client?: ClientOut;
  refWeightKg?: number | null;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState(() => ({
    nutrition: structuredClone(plan.nutrition ?? {}),
    training: structuredClone(plan.training ?? {}),
    education: structuredClone(plan.education ?? {}),
  }));
  const [saving, setSaving] = useState(false);

  function mutate(fn: (d: typeof draft) => void) {
    setDraft((d) => { const n = structuredClone(d); fn(n); return n; });
  }

  // ---- Nutrición ENCADENADA: tocar una pieza recalcula todo lo demás ------
  // · Cambias CALORÍAS → los TRES macros suben/bajan EN PROPORCIÓN al mix del
  //   plan (la dieta ya está adaptada al cliente) + comidas y gramos del banco.
  // · Cambias un MACRO → calorías reales (4/4/9) + comidas y gramos del banco.
  // Las comidas y el banco se reescalan SIEMPRE desde la versión BASE (la que
  // se abrió en el editor): así teclear cifras intermedias ("2" → "25" → 2500)
  // nunca corrompe gramos ni raciones por redondeos acumulados.
  const goal = client?.goal_type ?? null;
  const weight = refWeightKg ?? client?.start_weight_kg ?? null;
  // Baseline SANEADO: si el plan venía con cifras corruptas (p. ej. un kcal
  // gigante tecleado antes de validar), se recorta al abrir el editor para que
  // el reescalado parta de valores razonables.
  const baseline = useRef<any>((() => {
    const b = structuredClone(plan.nutrition ?? {});
    if (typeof b.target_kcal === "number") b.target_kcal = Math.min(8000, Math.max(0, b.target_kcal));
    if (b.macros) {
      for (const k of ["protein_g", "carbs_g", "fat_g"] as const)
        if (typeof b.macros[k] === "number") b.macros[k] = Math.min(800, Math.max(0, b.macros[k]));
    }
    return b;
  })());

  // Topes sanos: evitan que un valor absurdo (36.000.000 kcal, tecleado sin
  // querer) reviente el reescalado y corrompa las comidas del plan.
  const MAX_KCAL = 8000, MAX_MACRO = 800;
  const clampKcal = (v: number) => Math.min(MAX_KCAL, Math.max(0, v));
  const clampMacro = (v: number) => Math.min(MAX_MACRO, Math.max(0, v));

  function applyTotals(d: typeof draft, next: MacroTargets) {
    const scaled = rescaledFrom(baseline.current, next);
    d.nutrition.target_kcal = scaled.target_kcal;
    d.nutrition.macros = scaled.macros;
    d.nutrition.meals = scaled.meals;
    d.nutrition.meal_bank = scaled.meal_bank;
  }

  function setKcal(v: number | null) {
    mutate((d) => {
      if (v == null || v <= 0) { d.nutrition.target_kcal = v; return; }
      applyTotals(d, macrosScaledToKcal(baseline.current, clampKcal(v)));
    });
  }

  function setMacro(key: "protein_g" | "carbs_g" | "fat_g", v: number | null) {
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const next = {
        protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0,
        [key]: clampMacro(v ?? 0),
      } as { protein_g: number; carbs_g: number; fat_g: number };
      applyTotals(d, { kcal: kcalOf(next.protein_g, next.carbs_g, next.fat_g), ...next });
    });
  }

  const tdee = draft.nutrition.tdee_kcal ?? null;

  // Déficit/superávit: al elegir un % del desplegable, las kcal objetivo se
  // recalculan sobre el TDEE y los macros se rehacen óptimos para el objetivo.
  function setDeficit(signedPct: number) {
    if (!tdee) return;
    const kcal = clampKcal(kcalFromDeficit(tdee, signedPct));
    mutate((d) => {
      if (goal && weight) applyTotals(d, macrosForKcal(goal, weight, kcal));
      else applyTotals(d, macrosScaledToKcal(baseline.current, kcal));
    });
  }

  // % de un macro (estilo MyFitnessPal): fija sus gramos para que ocupe ese %
  // de las calorías objetivo. NO reescala los otros: así el total puede quedar
  // en 95%/105% y avisar de que hay que cuadrar. Se puede teclear decimal.
  function setMacroPct(key: "protein_g" | "carbs_g" | "fat_g", pct: number | null) {
    const target = draft.nutrition.target_kcal ?? 0;
    if (pct == null || !target) return;
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const next = {
        protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0,
        [key]: clampMacro(gramsFromPct(pct, target, key)),
      } as { protein_g: number; carbs_g: number; fat_g: number };
      // NO cambia target_kcal (el objetivo se mantiene); las comidas siguen los
      // gramos reales para que la tabla refleje lo que come.
      const scaled = rescaledFrom(baseline.current, { kcal: kcalOf(next.protein_g, next.carbs_g, next.fat_g), ...next });
      d.nutrition.macros = next;
      d.nutrition.meals = scaled.meals;
      d.nutrition.meal_bank = scaled.meal_bank;
    });
  }

  // "Cuadrar a 100%": deja los macros sumando justo las calorías objetivo.
  // Normalmente rellena con carbohidratos el resto tras proteína y grasa; pero
  // si proteína+grasa ya se pasan del objetivo, no hay hueco para carbos: en ese
  // caso baja proteína y grasa en proporción hasta encajar (carbos a 0), para
  // que el botón SIEMPRE cuadre y nunca sea un no-op.
  function cuadrar() {
    const target = draft.nutrition.target_kcal ?? 0;
    if (!target) return;
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      let p = m.protein_g ?? 0, f = m.fat_g ?? 0;
      const pfKcal = p * 4 + f * 9;
      let c: number;
      if (pfKcal <= target) {
        c = Math.max(0, Math.round((target - pfKcal) / 4));
      } else {
        const scale = target / pfKcal;
        p = Math.round(p * scale);
        f = Math.round(f * scale);
        c = 0;
      }
      const next = { protein_g: p, carbs_g: c, fat_g: f };
      const scaled = rescaledFrom(baseline.current, { kcal: kcalOf(p, c, f), ...next });
      d.nutrition.macros = next;
      d.nutrition.meals = scaled.meals;
      d.nutrition.meal_bank = scaled.meal_bank;
    });
  }

  // Recomendación por objetivo (evidencia): TDEE del plan + peso de referencia
  const rec = goal && weight && draft.nutrition.tdee_kcal
    ? goalTargets(goal, weight, draft.nutrition.tdee_kcal)
    : null;

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      const r = await api.updatePlan(plan.id, {
        nutrition_json: draft.nutrition,
        training_json: draft.training,
        education_json: draft.education,
      });
      toast.push("Plan actualizado");
      onSaved({
        ...plan,
        nutrition: r.nutrition_json, training: r.training_json, education: r.education_json,
        guardrail_flags: r.guardrail_flags ?? [], status: r.status, version: r.version,
      });
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo guardar el plan", "error");
    } finally {
      setSaving(false);
    }
  }

  const nut = draft.nutrition;
  const tr = draft.training;
  nut.macros = nut.macros ?? {};
  // % de cada macro sobre las calorías objetivo (para las cajas y el total)
  const mp = macroPct(nut.macros, nut.target_kcal ?? 0);
  nut.supplements = nut.supplements ?? [];
  nut.flexibility_rules = nut.flexibility_rules ?? [];
  tr.weekly_progression = tr.weekly_progression ?? [];
  tr.sessions = tr.sessions ?? [];
  tr.cardio = tr.cardio ?? { daily_steps: 0, sessions: [] };

  return (
    <div className="space-y-4">
      <div className="card sticky top-2 z-10 flex items-center justify-between p-4">
        <h3 className="text-base font-semibold text-zinc-100">Editar plan · Mes {plan.month_index}</h3>
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn btn-ghost"><X size={15} /> Cancelar</button>
          <button onClick={save} disabled={saving} className="btn btn-primary">
            {saving ? <Spinner /> : <Save size={15} />} Guardar cambios
          </button>
        </div>
      </div>

      {/* Nutrición */}
      <div className="card p-5">
        <Title icon={Utensils} text="Nutrición" />

        {/* Recomendación por OBJETIVO (evidencia actual) con un clic */}
        {rec && goal && (
          <div
            className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
            style={{
              background: "color-mix(in srgb, var(--brand-accent-2) 6%, transparent)",
              borderColor: "color-mix(in srgb, var(--brand-accent-2) 25%, transparent)",
            }}
          >
            <div className="flex items-start gap-2 text-xs text-zinc-400">
              <Target size={14} className="mt-0.5 shrink-0" style={{ color: "var(--brand-accent-2)" }} />
              <span>
                <b className="text-zinc-200">Recomendado para {GOAL_LABEL[goal]}</b> ({weight} kg ·
                TDEE {Math.round(draft.nutrition.tdee_kcal)} kcal):{" "}
                <b className="text-zinc-200">{rec.kcal} kcal · P {rec.protein_g} · C {rec.carbs_g} · G {rec.fat_g}</b>
                <span className="block text-zinc-500">{GOAL_RULES[goal].summary}</span>
              </span>
            </div>
            <button
              onClick={() => mutate((d) => applyTotals(d, rec))}
              className="btn btn-ghost"
            >
              Aplicar recomendación
            </button>
          </div>
        )}

        {/* Cálculo aplicado: déficit/superávit sobre el TDEE, editable en 5% */}
        {tdee ? (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg px-3 py-2 text-xs" style={{ background: "var(--surface-raised)" }}>
            <span className="text-zinc-500">Cálculo sobre tu gasto (TDEE {Math.round(tdee)} kcal):</span>
            <b className="text-zinc-200">{deficitLabel(tdee, nut.target_kcal ?? 0)}</b>
            <select
              value={deficitSelectValue(tdee, nut.target_kcal ?? 0)}
              onChange={(e) => setDeficit(Number(e.target.value))}
              aria-label="Déficit o superávit"
              className="input w-auto py-1 text-xs"
            >
              {deficitOptions(deficitSelectValue(tdee, nut.target_kcal ?? 0)).map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        ) : null}

        {/* Calorías objetivo en su fila (acotada) y los 3 macros en 3 columnas
            anchas: cada uno con gramos + %, sin cortar cifras de 3 dígitos. */}
        <div className="mb-3 max-w-[200px]">
          <Num label="Calorías objetivo" value={nut.target_kcal} onChange={setKcal} max={MAX_KCAL} />
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <MacroField label="Proteína" gramValue={nut.macros.protein_g} pct={mp.protein}
            onGram={(v) => setMacro("protein_g", v)} onPct={(v) => setMacroPct("protein_g", v)} max={MAX_MACRO} />
          <MacroField label="Carbohidratos" gramValue={nut.macros.carbs_g} pct={mp.carbs}
            onGram={(v) => setMacro("carbs_g", v)} onPct={(v) => setMacroPct("carbs_g", v)} max={MAX_MACRO} />
          <MacroField label="Grasas" gramValue={nut.macros.fat_g} pct={mp.fat}
            onGram={(v) => setMacro("fat_g", v)} onPct={(v) => setMacroPct("fat_g", v)} max={MAX_MACRO} />
        </div>

        {/* Total de los % (MyFitnessPal): verde si cuadra, ámbar si no */}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {(() => {
            const ok = Math.abs(mp.total - 100) <= MACRO_TOTAL_TOLERANCE;
            return (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold"
                style={ok
                  ? { background: "color-mix(in srgb, #1b7f4d 14%, transparent)", color: "#1b7f4d" }
                  : { background: "color-mix(in srgb, #9A6B15 16%, transparent)", color: "#9A6B15" }}
              >
                {ok ? <Check size={12} /> : <AlertTriangle size={12} />}
                Macros: {mp.total}%
              </span>
            );
          })()}
          {Math.abs(mp.total - 100) > MACRO_TOTAL_TOLERANCE && (
            <>
              <span className="text-zinc-500">
                {mp.total > 100 ? "te pasas de las calorías objetivo" : "no llegas a las calorías objetivo"} — ajusta un macro
              </span>
              <button onClick={cuadrar} className="btn btn-ghost px-2 py-1 text-xs">Cuadrar a 100%</button>
            </>
          )}
        </div>

        <p className="mt-2 text-xs text-zinc-500">
          Al cambiar las <b className="text-zinc-400">calorías</b> los tres macros se ajustan en
          proporción; al cambiar los <b className="text-zinc-400">gramos</b> o el{" "}
          <b className="text-zinc-400">%</b> de un macro, su porcentaje se recalcula y el total avisa
          si hay que cuadrar. Los objetivos por comida se reescalan en tiempo real (tabla de abajo).
        </p>

        {/* Reparto por comida EN VIVO: se ve cómo se adapta al teclear */}
        {(nut.meals ?? []).length > 0 && (
          <div className="mt-3 overflow-x-auto rounded-lg border border-zinc-500/15">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-500" style={{ background: "var(--surface-raised)" }}>
                  <th className="px-3 py-1.5 font-medium">Comida</th>
                  <th className="px-3 py-1.5 font-medium">kcal</th>
                  <th className="px-3 py-1.5 font-medium">P (g)</th>
                  <th className="px-3 py-1.5 font-medium">C (g)</th>
                  <th className="px-3 py-1.5 font-medium">G (g)</th>
                </tr>
              </thead>
              <tbody>
                {(nut.meals ?? []).map((m: any, i: number) => (
                  <tr key={i} className="border-t border-zinc-500/10 text-zinc-300">
                    <td className="px-3 py-1.5">{m.name ?? `Toma ${m.slot ?? i + 1}`}{m.time ? ` · ${m.time}` : ""}</td>
                    <td className="px-3 py-1.5 tabular-nums">{m.target?.kcal ?? "—"}</td>
                    <td className="px-3 py-1.5 tabular-nums">{m.target?.protein_g ?? "—"}</td>
                    <td className="px-3 py-1.5 tabular-nums">{m.target?.carbs_g ?? "—"}</td>
                    <td className="px-3 py-1.5 tabular-nums">{m.target?.fat_g ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Area label="Justificación (rationale)" value={nut.rationale ?? ""} onChange={(v) => mutate((d) => (d.nutrition.rationale = v))} />
        <Area label="Reglas de flexibilidad (una por línea)" value={(nut.flexibility_rules ?? []).join("\n")}
          onChange={(v) => mutate((d) => (d.nutrition.flexibility_rules = v.split("\n").map((s) => s.trim()).filter(Boolean)))} />

        <Subhead text="Suplementos" onAdd={() => mutate((d) => d.nutrition.supplements.push({ name: "", dose: "", timing: "", evidence_note: "" }))} />
        {nut.supplements.map((s: any, i: number) => (
          <Row key={i} onRemove={() => mutate((d) => d.nutrition.supplements.splice(i, 1))}>
            <Text label="Nombre" value={s.name} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].name = v))} />
            <Text label="Dosis" value={s.dose} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].dose = v))} />
            <Text label="Momento" value={s.timing} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].timing = v))} />
            <Text label="Nota" value={s.evidence_note ?? ""} onChange={(v) => mutate((d) => (d.nutrition.supplements[i].evidence_note = v))} />
          </Row>
        ))}
      </div>

      {/* Entrenamiento */}
      <div className="card p-5">
        <Title icon={Dumbbell} text="Entrenamiento" />
        <Text label="Nombre del split" value={tr.split_name ?? ""} onChange={(v) => mutate((d) => (d.training.split_name = v))} />
        <Area label="Justificación del split" value={tr.split_rationale ?? ""} onChange={(v) => mutate((d) => (d.training.split_rationale = v))} />

        <Subhead text="Progresión semanal" />
        {tr.weekly_progression.map((w: any, i: number) => (
          <div key={i} className="mt-2 grid grid-cols-2 gap-2 rounded-lg p-2 sm:grid-cols-4" style={{ background: "var(--surface-raised)" }}>
            <Text label={`Sem ${w.week ?? i + 1} · intención`} value={w.intent ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].intent = v))} />
            <Num label="Carga %" value={w.load_pct} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].load_pct = v))} />
            <Text label="RIR" value={w.rir_target ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].rir_target = v))} />
            <Text label="Volumen" value={w.volume_note ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].volume_note = v))} />
          </div>
        ))}

        <Subhead text="Sesiones (desplegables por día)" />
        {tr.sessions.map((s: any, si: number) => (
          <details key={si} className="mt-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm font-medium text-zinc-200">
              <span
                className="rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                style={{ background: "color-mix(in srgb, var(--brand-accent-2) 15%, transparent)", color: "var(--brand-accent-2)" }}
              >
                {s.day || `Sesión ${si + 1}`}
              </span>
              {s.name}
              <span className="text-xs font-normal text-zinc-500">{(s.exercises ?? []).length} ejercicios</span>
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <Text label="Día" value={s.day ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].day = v))} />
              <Text label="Nombre" value={s.name ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].name = v))} />
            </div>
            <Area label="Calentamiento" value={s.warmup ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].warmup = v))} />
            {(s.exercises ?? []).map((ex: any, ei: number) => (
              <details key={ei} className="mt-2 rounded-md p-2" style={{ background: "var(--surface)" }}>
                <summary className="flex cursor-pointer items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">
                    {exMap[ex.exercise_id] ?? `Ejercicio #${ex.exercise_id}`}
                    <span className="ml-1.5 font-normal text-zinc-500">
                      {ex.sets}×{ex.rep_range}{ex.rir ? ` · RIR ${ex.rir}` : ""}
                    </span>
                  </span>
                  <button
                    onClick={(e) => { e.preventDefault(); mutate((d) => d.training.sessions[si].exercises.splice(ei, 1)); }}
                    aria-label="Quitar ejercicio"
                    className="text-zinc-500 hover:text-red-400"
                  >
                    <Trash2 size={14} />
                  </button>
                </summary>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = v))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = v))} />
                </div>
                <Text label="Progresión" value={ex.progression_rule ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].progression_rule = v))} />
                <Text label="Cue técnica" value={ex.technique_cue ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].technique_cue = v))} />
              </details>
            ))}
            <Area label="Vuelta a la calma" value={s.cooldown ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].cooldown = v))} />
          </details>
        ))}

        <Subhead text="Cardio y descarga" />
        <div className="grid grid-cols-2 gap-2">
          <Num label="Pasos diarios" value={tr.cardio.daily_steps} onChange={(v) => mutate((d) => (d.training.cardio.daily_steps = v))} />
        </div>
        <Area label="Instrucciones de deload" value={tr.deload_instructions ?? ""} onChange={(v) => mutate((d) => (d.training.deload_instructions = v))} />
      </div>

      <p className="text-xs text-zinc-500">
        El banco de comidas no se edita aquí; para cambiar un ejercicio por otro usa el "swap" de la biblioteca.
      </p>
    </div>
  );
}

/** Macro con gramos + su % de la dieta (editable, estilo MyFitnessPal). */
function MacroField({ label, gramValue, pct, onGram, onPct, max }: {
  label: string; gramValue: number | null | undefined; pct: number;
  onGram: (v: number | null) => void; onPct: (v: number | null) => void; max?: number;
}) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <div className="flex items-stretch gap-1">
        <div className="relative flex-1">
          <input type="number" min={0} max={max} value={gramValue ?? ""}
            onChange={(e) => onGram(e.target.value === "" ? null : Number(e.target.value))}
            className="input w-full pr-6" aria-label={`${label} en gramos`} />
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-zinc-500">g</span>
        </div>
        <div className="relative w-[74px] shrink-0">
          <input type="number" min={0} max={100} value={Number.isFinite(pct) ? pct : ""}
            onChange={(e) => onPct(e.target.value === "" ? null : Number(e.target.value))}
            className="input w-full px-2 pr-5 text-center" aria-label={`${label} en porcentaje`} />
          <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-zinc-500">%</span>
        </div>
      </div>
    </label>
  );
}

function Title({ icon: Icon, text }: { icon: typeof Utensils; text: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} style={{ color: "var(--brand-accent)" }} />
      <h4 className="text-sm font-semibold text-zinc-200">{text}</h4>
    </div>
  );
}
function Subhead({ text, onAdd }: { text: string; onAdd?: () => void }) {
  return (
    <div className="mt-4 mb-1 flex items-center justify-between">
      <h5 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{text}</h5>
      {onAdd && <button onClick={onAdd} className="flex items-center gap-1 text-xs text-[var(--brand-accent)]"><Plus size={13} /> Añadir</button>}
    </div>
  );
}
function Row({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="mt-2 flex items-start gap-2 rounded-lg p-2" style={{ background: "var(--surface-raised)" }}>
      <div className="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-2">{children}</div>
      <button onClick={onRemove} className="mt-5 text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
    </div>
  );
}
function Text({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="text" value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="input w-full" />
    </label>
  );
}
function Num({ label, value, onChange, max }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void; max?: number }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="number" min={0} max={max} value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
    </label>
  );
}
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="mt-2 block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <textarea value={value ?? ""} onChange={(e) => onChange(e.target.value)} rows={2} className="input w-full resize-y" />
    </label>
  );
}
