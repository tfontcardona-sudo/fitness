import { useEffect, useRef, useState } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell, Target, AlertTriangle, Check, ChevronDown, ChevronUp, PlayCircle } from "lucide-react";
import { api } from "../lib/api";
import {
  GOAL_RULES, goalTargets, kcalOf, macrosForKcal, macrosScaledToKcal, rescaledFrom, redistributeMacro,
  deficitLabel, deficitOptions, deficitSelectValue, kcalFromDeficit, macroPct, gramsFromPct,
  MACRO_TOTAL_TOLERANCE, MAX_DEFICIT_PCT, MAX_SURPLUS_PCT,
  type MacroTargets,
} from "../lib/nutritionTargets";
import { GOAL_LABEL } from "../lib/format";
import { CANONICAL_MEALS, mealKeysFromNames, restructureNutritionMeals } from "../lib/meals";
import { Spinner, useToast } from "./ui";
import type { ClientOut, ExerciseOut } from "../types";

let _uidCounter = 0;
/** Id de fila SOLO del editor (no se persiste): estable ante reorden/borrado. */
const newUid = () => `ex-${++_uidCounter}-${Date.now().toString(36)}`;

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
  const [draft, setDraft] = useState(() => {
    const d = {
      nutrition: structuredClone(plan.nutrition ?? {}),
      training: structuredClone(plan.training ?? {}),
      education: structuredClone(plan.education ?? {}),
    };
    // Identidad ESTABLE por fila de ejercicio (_uid, solo del editor; se quita
    // al guardar): con key por índice, reordenar/quitar dejaba el <details>
    // abierto en la POSICIÓN y el formulario pasaba a mostrar OTRO ejercicio.
    for (const sess of d.training?.sessions ?? []) {
      for (const ex of sess?.exercises ?? []) {
        if (ex && ex._uid == null) ex._uid = newUid();
      }
    }
    return d;
  });
  const [saving, setSaving] = useState(false);
  // Biblioteca de ejercicios para el desplegable de variantes, el vídeo y el
  // botón "+ Añadir ejercicio". CON archivados: un plan puede referenciar un
  // ejercicio ya archivado y su nombre/vídeo deben seguir resolviéndose; el
  // desplegable y el alta, en cambio, solo ofrecen ACTIVOS.
  const [library, setLibrary] = useState<ExerciseOut[]>([]);
  useEffect(() => {
    api.listExercises({ include_archived: true }).then(setLibrary).catch(() => {});
  }, []);
  const activeLibrary = library.filter((e) => !e.archived);

  function mutate(fn: (d: typeof draft) => void) {
    setDraft((d) => { const n = structuredClone(d); fn(n); return n; });
  }

  /** Reordena un ejercicio dentro de su sesión (↑/↓): el portal y el documento
   *  siguen el orden del array, así que el cambio llega tal cual al cliente. */
  function moveExercise(si: number, ei: number, dir: -1 | 1) {
    mutate((d) => {
      const list = d.training.sessions?.[si]?.exercises;
      const j = ei + dir;
      if (!Array.isArray(list) || j < 0 || j >= list.length) return;
      [list[ei], list[j]] = [list[j], list[ei]];
    });
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

  // Editar los GRAMOS de un macro mantiene FIJAS las calorías objetivo (como la
  // IA): el macro editado toma ese valor y el "colchón" (carbohidratos, o grasa
  // si editas carbohidratos) absorbe la diferencia. Así todo cuadra al 100% y la
  // proteína, prioritaria, se preserva. Sin kcal objetivo aún, el macro define la
  // energía (no hay ancla que mantener).
  function setMacro(key: "protein_g" | "carbs_g" | "fat_g", v: number | null) {
    const target = draft.nutrition.target_kcal ?? 0;
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const cur = { protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0 };
      const grams = clampMacro(v ?? 0);
      if (target > 0) {
        applyTotals(d, redistributeMacro(target, cur, key, grams));
      } else {
        const next = { ...cur, [key]: grams };
        applyTotals(d, { kcal: kcalOf(next.protein_g, next.carbs_g, next.fat_g), ...next });
      }
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

  // % de un macro (estilo MyFitnessPal): fija sus gramos para que ocupe ese % de
  // las calorías objetivo, y el colchón absorbe el resto para que el total siga
  // cuadrando al 100% sobre las MISMAS kcal (mantiene la coherencia). Se puede
  // teclear decimal. Reescala comidas y banco como cualquier otro cambio.
  function setMacroPct(key: "protein_g" | "carbs_g" | "fat_g", pct: number | null) {
    const target = draft.nutrition.target_kcal ?? 0;
    if (pct == null || !target) return;
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const cur = { protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0 };
      applyTotals(d, redistributeMacro(target, cur, key, clampMacro(gramsFromPct(pct, target, key))));
    });
  }

  // "Cuadrar por objetivo": rehace el reparto de macros a las calorías objetivo
  // ACTUALES según la evidencia del objetivo del cliente (proteína y grasa por
  // kg de peso, carbohidratos el resto) — el mismo criterio que usa la IA. Así el
  // botón nunca produce combinaciones ilógicas. Sin objetivo/peso, rellena con
  // carbohidratos y, si proteína+grasa se pasan, las baja en proporción (carbos a
  // 0) para que SIEMPRE cuadre y nunca sea un no-op.
  function cuadrar() {
    const target = draft.nutrition.target_kcal ?? 0;
    if (!target) return;
    mutate((d) => {
      if (goal && weight) {
        applyTotals(d, macrosForKcal(goal, weight, target));
        return;
      }
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
      applyTotals(d, { kcal: kcalOf(p, c, f), protein_g: p, carbs_g: c, fat_g: f });
    });
  }

  // Recomendación por objetivo (evidencia): TDEE del plan + peso de referencia
  const rec = goal && weight && draft.nutrition.tdee_kcal
    ? goalTargets(goal, weight, draft.nutrition.tdee_kcal)
    : null;

  // Estructura de comidas del día (nº de tomas) SIN regenerar: al marcar/quitar
  // una toma se reparten las MISMAS kcal y macros del cliente entre las elegidas
  // (las que se quedan conservan sus proporciones; la nueva entra con su peso
  // típico) y el banco se renumera. La toma nueva no trae recetario: se crea con
  // "Regenerar con estas comidas" en Planificación o se explica a mano.
  const mealKeys = mealKeysFromNames(
    (draft.nutrition.meals ?? []).map((m: any) => m?.name ?? ""),
  );
  function toggleMeal(key: string) {
    const has = mealKeys.includes(key);
    if (has && mealKeys.length <= 2) {
      toast.push("El día necesita al menos 2 comidas", "error");
      return;
    }
    const next = has ? mealKeys.filter((k) => k !== key) : [...mealKeys, key];
    mutate((d) => {
      restructureNutritionMeals(d.nutrition, next);
      // Las ediciones de kcal/macros reescalan desde el baseline: tras cambiar
      // la estructura, el baseline pasa a ser ESTA estructura (si no, teclear
      // unas kcal desharía el cambio de comidas).
      baseline.current = structuredClone(d.nutrition);
    });
  }

  async function save() {
    if (saving) return;
    setSaving(true);
    try {
      // El _uid es identidad de fila SOLO del editor: fuera antes de persistir.
      const training = structuredClone(draft.training);
      for (const sess of training?.sessions ?? []) {
        for (const ex of sess?.exercises ?? []) {
          if (ex && "_uid" in ex) delete ex._uid;
        }
      }
      const r = await api.updatePlan(plan.id, {
        nutrition_json: draft.nutrition,
        training_json: training,
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

  // No se puede guardar con las calorías vacías o a 0: sería un plan incoherente
  // (macros y comidas reales con "0 kcal"). El coach debe teclear un objetivo.
  const kcalInvalid = !(nut.target_kcal && nut.target_kcal > 0);

  return (
    <div className="space-y-4">
      <div className="card sticky top-2 z-10 flex items-center justify-between p-4">
        <h3 className="text-base font-semibold text-zinc-100">Editar plan · Mes {plan.month_index}</h3>
        <div className="flex items-center gap-2">
          {kcalInvalid && (
            <span className="hidden text-xs text-[#9A6B15] sm:inline">Pon las calorías objetivo para guardar</span>
          )}
          <button onClick={onCancel} className="btn btn-ghost"><X size={15} /> Cancelar</button>
          <button onClick={save} disabled={saving || kcalInvalid} className="btn btn-primary"
            title={kcalInvalid ? "Introduce las calorías objetivo" : undefined}>
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
            {(() => {
              const p = deficitSelectValue(tdee, nut.target_kcal ?? 0);
              if (p >= -MAX_DEFICIT_PCT && p <= MAX_SURPLUS_PCT) return null;
              return (
                <span className="inline-flex items-center gap-1 font-semibold" style={{ color: "#9A6B15" }}>
                  <AlertTriangle size={12} />
                  {p < 0 ? `déficit >${MAX_DEFICIT_PCT}%` : `superávit >${MAX_SURPLUS_PCT}%`}: agresivo, revisa
                </span>
              );
            })()}
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

        {/* Total de los % (MyFitnessPal): verde si cuadra, ámbar si no. El botón
            de cuadrar por objetivo está siempre disponible como reinicio a un
            reparto con sentido. */}
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
            <span className="text-zinc-500">
              {mp.total > 100 ? "te pasas de las calorías objetivo" : "no llegas a las calorías objetivo"}
            </span>
          )}
          {(nut.target_kcal ?? 0) > 0 && (
            <button onClick={cuadrar} className="btn btn-ghost px-2 py-1 text-xs"
              title={goal && weight
                ? "Rehace el reparto de macros a estas calorías según el objetivo del cliente"
                : "Rellena con carbohidratos hasta cuadrar las calorías objetivo"}>
              {goal && weight ? "Cuadrar por objetivo" : "Cuadrar a 100%"}
            </button>
          )}
        </div>

        <p className="mt-2 text-xs text-zinc-500">
          Las <b className="text-zinc-400">calorías</b> son el ancla: al cambiarlas, los tres macros se
          ajustan en proporción. Al cambiar los <b className="text-zinc-400">gramos</b> o el{" "}
          <b className="text-zinc-400">%</b> de un macro se mantienen esas calorías y los carbohidratos
          (o la grasa) cuadran el resto, preservando la proteína. Los objetivos por comida y los gramos
          del banco se reescalan en tiempo real (tabla de abajo).
        </p>

        {/* Nº de comidas del día SIN regenerar: mismas kcal/macros, otro reparto */}
        <div className="mt-4">
          <p className="text-xs font-medium text-zinc-400">Comidas del día</p>
          <p className="mt-0.5 text-[11px] text-zinc-500">
            Marca las tomas que hará: sus kcal y macros se reparten entre ellas al
            momento (los totales no cambian). Una toma nueva entra con su peso típico
            y sin recetario — créalo con “Regenerar con estas comidas” o explícalo a mano.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {CANONICAL_MEALS.map((m) => {
              const on = mealKeys.includes(m.key);
              return (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => toggleMeal(m.key)}
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
        </div>

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
            <Num label="Carga %" value={w.load_pct} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].load_pct = v ?? 0))} />
            <Text label="RIR" value={w.rir_target ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].rir_target = v))} />
            <Text label="Volumen" value={w.volume_note ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].volume_note = v))} />
          </div>
        ))}

        <Subhead text="Sesiones (desplegables por día)" />
        {tr.sessions.map((s: any, si: number) => (
          <details key={si} name="editor-sesiones" className="mt-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
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
              <details key={ex._uid ?? ei} name={`editor-ejercicios-${si}`} className="mt-2 rounded-md p-2" style={{ background: "var(--surface)" }}>
                <summary className="flex cursor-pointer items-center justify-between gap-2">
                  <span className="min-w-0 text-xs font-medium text-zinc-200">
                    {exMap[ex.exercise_id] ?? library.find((e) => e.id === ex.exercise_id)?.canonical_name ?? `Ejercicio #${ex.exercise_id}`}
                    <span className="ml-1.5 font-normal text-zinc-500">
                      {ex.sets}×{ex.rep_range}{ex.rir ? ` · RIR ${ex.rir}` : ""}
                    </span>
                  </span>
                  {/* Acciones del ejercicio: reordenar (↑/↓), ver su vídeo y quitar.
                      preventDefault: que el clic no pliegue/despliegue el detalle. */}
                  <span className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={(e) => { e.preventDefault(); moveExercise(si, ei, -1); }}
                      disabled={ei === 0}
                      aria-label="Subir ejercicio"
                      className="p-0.5 text-zinc-500 hover:text-zinc-200 disabled:opacity-25"
                    >
                      <ChevronUp size={15} />
                    </button>
                    <button
                      onClick={(e) => { e.preventDefault(); moveExercise(si, ei, 1); }}
                      disabled={ei === (s.exercises ?? []).length - 1}
                      aria-label="Bajar ejercicio"
                      className="p-0.5 text-zinc-500 hover:text-zinc-200 disabled:opacity-25"
                    >
                      <ChevronDown size={15} />
                    </button>
                    {(() => {
                      // Mismo re-filtro que el portal: una URL legada sin http(s)
                      // no puede abrirse (se resolvería como ruta de la app o algo peor).
                      const rawUrl = (library.find((e) => e.id === ex.exercise_id)?.video_url ?? "").trim();
                      const video = /^https?:\/\//i.test(rawUrl) ? rawUrl : null;
                      return video ? (
                        <button
                          onClick={(e) => { e.preventDefault(); window.open(video, "_blank", "noopener"); }}
                          aria-label="Ver vídeo del ejercicio"
                          title="Ver vídeo del ejercicio"
                          className="p-0.5 hover:opacity-80"
                          style={{ color: "var(--brand-accent-2)" }}
                        >
                          <PlayCircle size={15} />
                        </button>
                      ) : null;
                    })()}
                    <button
                      onClick={(e) => { e.preventDefault(); mutate((d) => d.training.sessions[si].exercises.splice(ei, 1)); }}
                      aria-label="Quitar ejercicio"
                      className="p-0.5 text-zinc-500 hover:text-red-400"
                    >
                      <Trash2 size={14} />
                    </button>
                  </span>
                </summary>
                {/* Cambiar el ejercicio por una variante o por otro del mismo
                    grupo muscular — o por cualquiera de la biblioteca. */}
                <div className="mt-2">
                  <ExerciseSelect
                    library={activeLibrary}
                    lookup={library}
                    value={ex.exercise_id}
                    fallbackName={exMap[ex.exercise_id] ?? `Ejercicio #${ex.exercise_id}`}
                    onChange={(id) => mutate((d) => (d.training.sessions[si].exercises[ei].exercise_id = id))}
                  />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = v ?? 0))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = v ?? 0))} />
                </div>
                <Text label="Progresión" value={ex.progression_rule ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].progression_rule = v))} />
                <Text label="Cue técnica" value={ex.technique_cue ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].technique_cue = v))} />
                <Area
                  label="Indicaciones personalizadas (capacidades, limitaciones, adaptación)"
                  value={ex.coach_notes ?? ""}
                  onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].coach_notes = v.trim() ? v : null))}
                />
              </details>
            ))}
            {/* Rutina personalizable: añade el ejercicio que quieras y luego
                cámbialo con el desplegable de variantes/grupo muscular. */}
            <button
              type="button"
              className="btn btn-ghost mt-2 !px-3 !py-1.5 text-xs"
              disabled={activeLibrary.length === 0}
              onClick={() =>
                mutate((d) => {
                  const list = d.training.sessions[si].exercises ?? (d.training.sessions[si].exercises = []);
                  list.push({
                    _uid: newUid(),
                    exercise_id: activeLibrary[0]?.id ?? 1,
                    sets: 3, rep_range: "8-12", rir: "2", tempo: null, rest_sec: 90,
                    start_weight_hint_kg: null,
                    progression_rule: "Añade repeticiones hasta el tope del rango y sube peso",
                    technique_cue: "", biomech_cue: "", coach_notes: null,
                  });
                })
              }
            >
              <Plus size={14} /> Añadir ejercicio
            </button>
            <Area label="Vuelta a la calma" value={s.cooldown ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].cooldown = v))} />
          </details>
        ))}

        <Subhead text="Cardio y descarga" />
        <div className="grid grid-cols-2 gap-2">
          <Num label="Pasos diarios" value={tr.cardio.daily_steps} onChange={(v) => mutate((d) => (d.training.cardio.daily_steps = v ?? 0))} />
        </div>
        <Area label="Instrucciones de deload" value={tr.deload_instructions ?? ""} onChange={(v) => mutate((d) => (d.training.deload_instructions = v))} />
      </div>

      <p className="text-xs text-zinc-500">
        El banco de comidas no se edita aquí; para cambiar un ejercicio por otro usa el "swap" de la biblioteca.
      </p>
    </div>
  );
}

/** Input numérico que NO se "pega" a un dígito al borrar. Mientras editas muestra
 *  EXACTAMENTE lo que tecleas (incluido el vacío) con estado local; solo vuelve a
 *  seguir el valor del modelo al salir del campo (blur). Así borrar todos los
 *  dígitos deja el campo vacío en lugar de saltar a 0/1/3 por el recálculo en
 *  cadena. Emite null cuando queda vacío y el número en cualquier otro caso. */
function NumberInput({ value, onChange, className, ariaLabel, min = 0, max, step }: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  className?: string; ariaLabel?: string; min?: number; max?: number; step?: number;
}) {
  const [raw, setRaw] = useState<string | null>(null);
  // Último valor EMITIDO por este input: si el prop `value` cambia sin pasar por
  // aquí (reorden de filas, recálculo, tope aplicado), el buffer local ya no
  // representa este campo y se descarta — en Safari/Firefox un clic en un botón
  // no roba el foco, así que el blur no llega y el buffer sobreviviría pegado
  // al ejercicio equivocado.
  const lastEmitted = useRef<number | null | undefined>(undefined);
  if (raw !== null && lastEmitted.current !== undefined && value !== lastEmitted.current) {
    setRaw(null);
    lastEmitted.current = undefined;
  }
  const shown = raw !== null ? raw : (value ?? "");
  return (
    <input
      type="number" inputMode="decimal" min={min} max={max} step={step}
      value={shown}
      onChange={(e) => {
        const s = e.target.value;
        setRaw(s);
        if (s === "") { lastEmitted.current = null; onChange(null); return; }
        const n = Number(s);
        const emitted = Number.isFinite(n) ? n : null;
        lastEmitted.current = emitted;
        onChange(emitted);
      }}
      onBlur={() => { setRaw(null); lastEmitted.current = undefined; }}
      className={className}
      aria-label={ariaLabel}
    />
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
          <NumberInput value={gramValue} max={max} onChange={onGram}
            className="input w-full pr-6" ariaLabel={`${label} en gramos`} />
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-zinc-500">g</span>
        </div>
        <div className="relative w-[74px] shrink-0">
          <NumberInput value={Number.isFinite(pct) ? pct : null} max={100} step={0.1} onChange={onPct}
            className="input w-full px-2 pr-5 text-center" ariaLabel={`${label} en porcentaje`} />
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
      <NumberInput value={value} max={max} onChange={onChange} className="input w-full" ariaLabel={label} />
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

/** Desplegable para CAMBIAR el ejercicio: primero las VARIANTES (mismo patrón de
 *  movimiento), luego el MISMO GRUPO MUSCULAR y por último el resto de la
 *  biblioteca — así el coach ajusta la rutina a su antojo sin salir del editor. */
function ExerciseSelect({ library, lookup, value, fallbackName, onChange }: {
  library: ExerciseOut[];          // solo ACTIVOS: candidatos del desplegable
  lookup?: ExerciseOut[];          // biblioteca completa (con archivados) para resolver el actual
  value: number;
  fallbackName: string;
  onChange: (id: number) => void;
}) {
  const byName = (a: ExerciseOut, b: ExerciseOut) => a.canonical_name.localeCompare(b.canonical_name);
  const cur = (lookup ?? library).find((e) => e.id === value);
  const variants = cur
    ? library.filter((e) => e.id !== value && e.movement_pattern === cur.movement_pattern).sort(byName)
    : [];
  const sameMuscle = cur
    ? library
        .filter((e) => e.id !== value && e.movement_pattern !== cur.movement_pattern && e.muscle_primary === cur.muscle_primary)
        .sort(byName)
    : [];
  const shown = new Set([value, ...variants.map((e) => e.id), ...sameMuscle.map((e) => e.id)]);
  const rest = library.filter((e) => !shown.has(e.id)).sort(byName);
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">Ejercicio (elige variante o cámbialo)</span>
      <select className="input w-full" value={value} onChange={(e) => onChange(Number(e.target.value))}>
        <option value={value}>{cur ? cur.canonical_name : fallbackName}</option>
        {variants.length > 0 && (
          <optgroup label="Variantes — mismo patrón de movimiento">
            {variants.map((e) => (
              <option key={e.id} value={e.id}>{e.canonical_name}</option>
            ))}
          </optgroup>
        )}
        {sameMuscle.length > 0 && (
          <optgroup label={`Mismo grupo muscular (${cur?.muscle_primary ?? ""})`}>
            {sameMuscle.map((e) => (
              <option key={e.id} value={e.id}>{e.canonical_name}</option>
            ))}
          </optgroup>
        )}
        {rest.length > 0 && (
          <optgroup label="Resto de la biblioteca">
            {rest.map((e) => (
              <option key={e.id} value={e.id}>{e.canonical_name} · {e.muscle_primary}</option>
            ))}
          </optgroup>
        )}
      </select>
    </label>
  );
}
