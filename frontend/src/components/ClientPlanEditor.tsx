import { useState } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell, Target } from "lucide-react";
import { api } from "../lib/api";
import { GOAL_RULES, goalTargets, kcalOf, macrosForKcal, rescaleNutrition } from "../lib/nutritionTargets";
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
  // · Cambias CALORÍAS → macros óptimos para el objetivo (proteína y grasa por
  //   kg según evidencia, carbohidratos el resto) + comidas y gramos del banco.
  // · Cambias un MACRO → calorías reales (4/4/9) + comidas y gramos del banco.
  const goal = client?.goal_type ?? null;
  const weight = refWeightKg ?? client?.start_weight_kg ?? null;

  function setKcal(v: number | null) {
    mutate((d) => {
      if (v == null || v <= 0) { d.nutrition.target_kcal = v; return; }
      if (goal && weight) {
        rescaleNutrition(d.nutrition, macrosForKcal(goal, weight, v));
      } else {
        // Sin objetivo/peso de referencia: se mantiene el mix actual de macros
        const m = d.nutrition.macros ?? {};
        const p = m.protein_g ?? 0, c = m.carbs_g ?? 0, f = m.fat_g ?? 0;
        const old = kcalOf(p, c, f) || d.nutrition.target_kcal || v;
        const r = v / old;
        rescaleNutrition(d.nutrition, {
          kcal: v, protein_g: Math.round(p * r), carbs_g: Math.round(c * r), fat_g: Math.round(f * r),
        });
      }
    });
  }

  function setMacro(key: "protein_g" | "carbs_g" | "fat_g", v: number | null) {
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const next = {
        protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0,
        [key]: v ?? 0,
      } as { protein_g: number; carbs_g: number; fat_g: number };
      rescaleNutrition(d.nutrition, {
        kcal: kcalOf(next.protein_g, next.carbs_g, next.fat_g), ...next,
      });
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
              onClick={() => mutate((d) => rescaleNutrition(d.nutrition, rec))}
              className="btn btn-ghost"
            >
              Aplicar recomendación
            </button>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Num label="Calorías objetivo" value={nut.target_kcal} onChange={setKcal} />
          <Num label="Proteína (g)" value={nut.macros.protein_g} onChange={(v) => setMacro("protein_g", v)} />
          <Num label="Carbohidratos (g)" value={nut.macros.carbs_g} onChange={(v) => setMacro("carbs_g", v)} />
          <Num label="Grasas (g)" value={nut.macros.fat_g} onChange={(v) => setMacro("fat_g", v)} />
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          Todo se recalcula solo: al cambiar las <b className="text-zinc-400">calorías</b> se ajustan los
          macros al objetivo del cliente; al cambiar un <b className="text-zinc-400">macro</b> se ajustan
          las calorías (4/4/9). Los objetivos por comida y los gramos del banco de comidas se
          reescalan automáticamente en ambos casos.
        </p>
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

        <Subhead text="Sesiones" />
        {tr.sessions.map((s: any, si: number) => (
          <div key={si} className="mt-2 rounded-lg p-3" style={{ background: "var(--surface-raised)" }}>
            <div className="grid grid-cols-2 gap-2">
              <Text label="Día" value={s.day ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].day = v))} />
              <Text label="Nombre" value={s.name ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].name = v))} />
            </div>
            <Area label="Calentamiento" value={s.warmup ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].warmup = v))} />
            {(s.exercises ?? []).map((ex: any, ei: number) => (
              <div key={ei} className="mt-2 rounded-md p-2" style={{ background: "var(--surface)" }}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">{exMap[ex.exercise_id] ?? `Ejercicio #${ex.exercise_id}`}</span>
                  <button onClick={() => mutate((d) => d.training.sessions[si].exercises.splice(ei, 1))} className="text-zinc-500 hover:text-red-400"><Trash2 size={14} /></button>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = v))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = v))} />
                  <Text label="Tempo" value={ex.tempo ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].tempo = v))} />
                  <Num label="Peso sug. (kg)" value={ex.start_weight_hint_kg} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].start_weight_hint_kg = v))} />
                </div>
                <Text label="Progresión" value={ex.progression_rule ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].progression_rule = v))} />
                <Text label="Cue técnica" value={ex.technique_cue ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].technique_cue = v))} />
              </div>
            ))}
            <Area label="Vuelta a la calma" value={s.cooldown ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].cooldown = v))} />
          </div>
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
function Num({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (v: number | null) => void }) {
  return (
    <label className="block">
      <span className="mb-0.5 block text-xs text-zinc-500">{label}</span>
      <input type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} className="input w-full" />
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
