import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Save, X, Plus, Trash2, Utensils, Dumbbell, Target, AlertTriangle, Check, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "../lib/api";
import {
  GOAL_RULES, goalTargets, kcalOf, macrosForKcal, macrosScaledToKcal, rescaledFrom, targetBounds,
  deficitLabel, deficitOptions, deficitSelectValue, kcalFromDeficit, macroPct, gramsFromPct,
  MAX_DEFICIT_PCT, MAX_SURPLUS_PCT,
  type MacroTargets,
} from "../lib/nutritionTargets";
import { GOAL_LABEL } from "../lib/format";
import { CANONICAL_MEALS, mealKeysFromNames, restructureNutritionMeals } from "../lib/meals";
import { useDismiss } from "../lib/useDismiss";
import { ExpandableArea, Spinner, useToast } from "./ui";
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
  plan, exMap, onSaved, onCancel, client, refWeightKg, initialFocus,
}: {
  plan: PlanData;
  exMap: Record<number, string>;
  onSaved: (p: PlanData) => void;
  onCancel: () => void;
  client?: ClientOut;
  refWeightKg?: number | null;
  /** Bloque desde el que se abrió el editor (botón Editar de ese bloque):
   *  se hace scroll hasta él y se resalta un instante para saber QUÉ se edita. */
  initialFocus?: "nutrition" | "training" | "supplements" | null;
}) {
  const toast = useToast();
  // Foco por bloque: refs de cada sección + destello al abrir.
  const focusRefs = {
    nutrition: useRef<HTMLDivElement>(null),
    training: useRef<HTMLDivElement>(null),
    supplements: useRef<HTMLDivElement>(null),
  };
  // Modo UN SOLO BLOQUE: abierto desde el "Editar" de un bloque, solo se ve
  // ese bloque en pantalla hasta salir (o ampliar a "ver plan completo").
  const [only, setOnly] = useState<"nutrition" | "training" | null>(
    initialFocus === "training" ? "training" : initialFocus ? "nutrition" : null,
  );
  const [flash, setFlash] = useState<string | null>(null);
  useEffect(() => {
    if (!initialFocus) return;
    const el = focusRefs[initialFocus]?.current;
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setFlash(initialFocus);
    const t = window.setTimeout(() => setFlash(null), 1800);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialFocus]);
  const flashStyle = (key: string): CSSProperties =>
    flash === key
      ? { boxShadow: "0 0 0 2px var(--brand-accent), 0 0 24px color-mix(in srgb, var(--brand-accent) 35%, transparent)", transition: "box-shadow .3s" }
      : { transition: "box-shadow .6s" };
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

  // Escribir un ejercicio a mano desde el buscador: se crea en la biblioteca
  // (reutilizable en todos los planes, gestionable en Recursos) y se devuelve
  // su id para seleccionarlo al momento en la rutina.
  async function createExercise(name: string, muscle: string, pattern: string): Promise<number | null> {
    try {
      const created = await api.createExercise({
        canonical_name: name,
        muscle_primary: muscle,
        movement_pattern: pattern,
        equipment: ["maquina"],
        level_min: 1,
      });
      setLibrary((prev) => [...prev, created]);
      toast.push(`Ejercicio «${created.canonical_name}» creado`);
      return created.id;
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo crear el ejercicio", "error");
      return null;
    }
  }

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

  // clamp=false: en el editor los topes de seguridad NUNCA reescriben en
  // silencio lo tecleado — se muestran como AVISO bloqueante (más abajo). El
  // backend re-acota igualmente al guardar (última red).
  function applyTotals(d: typeof draft, next: MacroTargets) {
    const scaled = rescaledFrom(baseline.current, next, refWeightKg, false);
    d.nutrition.target_kcal = scaled.target_kcal;
    d.nutrition.macros = scaled.macros;
    d.nutrition.meals = scaled.meals;
    d.nutrition.meal_bank = scaled.meal_bank;
  }

  // ---- EDICIÓN LIBRE ------------------------------------------------------
  // El coach mueve calorías, gramos o % COMO QUIERA (incluido 0 o vaciar el
  // campo): NINGÚN campo se reescribe mientras teclea ni al cuadrar. Si los
  // números no cuadran (o violan un tope de seguridad), un AVISO PERSISTENTE
  // explica exactamente qué pasa y con cuánto, hasta que todo tenga relación
  // entre sí; mientras tanto no se puede guardar. En cuanto cuadra y es
  // seguro, comidas y banco se reescalan solos desde la versión base.
  const KCAL_TOL_PCT = 2; // única tolerancia: chip, reescalado y bloqueo

  // ¿El coach ha TOCADO la nutrición en esta sesión de edición? Un plan legado
  // que ya venía descuadrado no debe bloquear guardar cambios de entreno.
  const nutTouched = useRef(false);

  /** Comprobación pura sobre un borrador: cuadre 4/4/9 y topes de seguridad. */
  function checkTotals(n: any): { coherent: boolean; safe: boolean } {
    const target = n.target_kcal ?? 0;
    const m = n.macros ?? {};
    const p = m.protein_g ?? 0, c = m.carbs_g ?? 0, f = m.fat_g ?? 0;
    if (target <= 0) return { coherent: false, safe: false };
    const coherent = Math.abs(kcalOf(p, c, f) - target) <= (KCAL_TOL_PCT / 100) * target;
    const b = targetBounds(n.tdee_kcal, refWeightKg ?? client?.start_weight_kg ?? null);
    const safe = p >= b.pLo && p <= b.pHi && f >= b.fLo && f <= b.fHi
      && target >= b.kLo && target <= b.kHi;
    return { coherent, safe };
  }

  /** Si los totales del borrador cuadran Y respetan los topes, reescala
   *  comidas y banco a esos totales. Si no, deja los números tal cual los puso
   *  el coach (el aviso persistente y el guardado bloqueado hacen el resto). */
  function rescaleIfCoherent(d: typeof draft) {
    const { coherent: okC, safe: okS } = checkTotals(d.nutrition);
    if (!okC || !okS) return;
    const m = d.nutrition.macros ?? {};
    applyTotals(d, {
      kcal: d.nutrition.target_kcal,
      protein_g: m.protein_g ?? 0, carbs_g: m.carbs_g ?? 0, fat_g: m.fat_g ?? 0,
    });
  }

  // En Safari/Firefox un clic en un botón NO roba el foco del input: el buffer
  // de lo tecleado sobreviviría y taparía el valor recalculado por el botón.
  // Antes de cualquier acción que reescribe macros, se suelta el foco.
  function blurActive() {
    (document.activeElement as HTMLElement | null)?.blur?.();
  }

  function setKcal(v: number | null) {
    nutTouched.current = true;
    mutate((d) => {
      if (v == null) { d.nutrition.target_kcal = null; return; }
      if (v <= 0) { d.nutrition.target_kcal = 0; return; } // nunca negativas
      // Cambiar las CALORÍAS escala los tres macros en proporción — desde el
      // mix ACTUAL del borrador (no desde la versión base: eso destruía los
      // macros retocados en esta misma sesión de edición).
      const kcal = clampKcal(v);
      applyTotals(d, macrosScaledToKcal(
        { macros: d.nutrition.macros ?? {}, target_kcal: d.nutrition.target_kcal }, kcal));
    });
  }

  // Editar los GRAMOS de un macro: el valor SE RESPETA tal cual (también 0 o
  // vacío) y NO se toca ningún otro campo. Si el conjunto deja de cuadrar con
  // las calorías objetivo, el aviso persistente lo canta con el detalle.
  function setMacro(key: "protein_g" | "carbs_g" | "fat_g", v: number | null) {
    nutTouched.current = true;
    mutate((d) => {
      d.nutrition.macros = d.nutrition.macros ?? {};
      d.nutrition.macros[key] = v == null ? v : clampMacro(v);
      rescaleIfCoherent(d);
    });
  }

  const tdee = draft.nutrition.tdee_kcal ?? null;

  // Déficit/superávit: al elegir un % del desplegable, las kcal objetivo se
  // recalculan sobre el TDEE y los macros se rehacen óptimos para el objetivo.
  function setDeficit(signedPct: number) {
    if (!tdee) return;
    blurActive();
    nutTouched.current = true;
    const kcal = clampKcal(kcalFromDeficit(tdee, signedPct));
    mutate((d) => {
      if (goal && weight) applyTotals(d, macrosForKcal(goal, weight, kcal));
      else applyTotals(d, macrosScaledToKcal(
        { macros: d.nutrition.macros ?? {}, target_kcal: d.nutrition.target_kcal }, kcal));
    });
  }

  // % de un macro (estilo MyFitnessPal): traduce el % a gramos sobre las
  // calorías objetivo y los fija — SIN tocar los otros macros (edición libre:
  // si el total ya no suma 100%, el aviso persistente lo explica). Vaciar el
  // campo no borra nada: el % es una vista de los gramos.
  function setMacroPct(key: "protein_g" | "carbs_g" | "fat_g", pct: number | null) {
    const target = draft.nutrition.target_kcal ?? 0;
    if (pct == null || !target) return;
    nutTouched.current = true;
    mutate((d) => {
      d.nutrition.macros = d.nutrition.macros ?? {};
      d.nutrition.macros[key] = clampMacro(gramsFromPct(Math.min(100, Math.max(0, pct)), target, key));
      rescaleIfCoherent(d);
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
    blurActive();
    nutTouched.current = true;
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

  // Recomendación por objetivo: la calcula el BACKEND (misma fórmula que la
  // generación, con tramos por % graso). La TS local queda solo de fallback
  // si la petición falla (auditoría: dos fórmulas divergentes).
  const [backendRec, setBackendRec] = useState<{ kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null>(null);
  useEffect(() => {
    let alive = true;
    if (client?.id) {
      api.macroRecommendation(client.id)
        .then((r) => { if (alive && r.available && r.kcal) setBackendRec({ kcal: r.kcal, protein_g: r.protein_g!, carbs_g: r.carbs_g!, fat_g: r.fat_g! }); })
        .catch(() => { /* fallback local */ });
    }
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client?.id]);
  const rec = backendRec ?? (goal && weight && draft.nutrition.tdee_kcal
    ? goalTargets(goal, weight, draft.nutrition.tdee_kcal)
    : null);

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
    // La reestructuración reparte los TOTALES actuales entre las tomas y los
    // adopta como nueva base: hacerlo con números descuadrados envenenaría el
    // baseline (p. ej. proteína 0 repartida → luego todo el macro caería en
    // una sola comida). Primero cuadrar, después reestructurar.
    const { coherent: okC, safe: okS } = checkTotals(draft.nutrition);
    if (!okC || !okS) {
      toast.push("Cuadra antes las calorías y macros (mira el aviso) y luego cambia las comidas", "error");
      return;
    }
    blurActive();
    nutTouched.current = true;
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
      // Las reglas de flexibilidad se editan con líneas vacías intermedias
      // (para no comerse el Enter al teclear): se limpian solo al persistir.
      const nutrition = structuredClone(draft.nutrition);
      if (Array.isArray(nutrition.flexibility_rules)) {
        nutrition.flexibility_rules = nutrition.flexibility_rules
          .map((s: string) => (s ?? "").trim()).filter(Boolean);
      }
      const r = await api.updatePlan(plan.id, {
        nutrition_json: nutrition,
        training_json: training,
        education_json: draft.education,
        // Concurrencia optimista: si otra pestaña (o una adaptación) guardó
        // después de abrir este editor, el backend responde 409 con el motivo.
        base_rev: (plan.nutrition as any)?.rev ?? 0,
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

  // Descuadre PERSISTENTE (edición libre): compara las calorías objetivo con la
  // suma real de los macros (P·4 + C·4 + G·9) y contra los TOPES de seguridad.
  // Mientras algo no cuadre, el aviso de abajo lo explica con cifras exactas.
  const macroSumKcal = kcalOf(nut.macros.protein_g ?? 0, nut.macros.carbs_g ?? 0, nut.macros.fat_g ?? 0);
  const kcalDiff = macroSumKcal - (nut.target_kcal ?? 0); // + = los macros se pasan
  const { coherent, safe } = checkTotals(nut);
  const bounds = targetBounds(nut.tdee_kcal, weight);
  const totalsOk = !kcalInvalid && coherent && safe;
  // Bloqueo de guardado SOLO cuando se edita nutrición Y el coach la ha tocado:
  // un plan legado que ya venía descuadrado no bloquea guardar su entreno (al
  // guardar, el servidor lo cuadra solo y el aviso lo explica).
  const nutritionBlocked = only !== "training" && nutTouched.current && !totalsOk;

  // Cuadre rápido desde el aviso: los carbohidratos absorben la diferencia
  // (proteína y grasa se respetan tal cual las dejó el coach).
  function cuadrarConCarbohidratos() {
    const target = nut.target_kcal ?? 0;
    if (!target) return;
    blurActive();
    nutTouched.current = true;
    mutate((d) => {
      const m = d.nutrition.macros ?? {};
      const p = m.protein_g ?? 0, f = m.fat_g ?? 0;
      m.carbs_g = Math.max(0, Math.round((target - p * 4 - f * 9) / 4));
      d.nutrition.macros = m;
      rescaleIfCoherent(d);
    });
  }

  return (
    <div className="space-y-4">
      {/* Cabecera FIJA por encima de la barra de pestañas (z-20 > z-10) y a
          top-0: sin hueco por el que se vea contenido cortado al hacer scroll. */}
      <div className="card sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 p-4">
        <h3 className="text-base font-semibold text-zinc-100">
          {only === "training" ? "Editar entrenamiento" : only ? "Editar nutrición" : "Editar plan"} · Mes {plan.month_index}
          {only && (
            <button onClick={() => setOnly(null)}
              className="ml-2 text-xs font-normal underline-offset-2 hover:underline"
              style={{ color: "var(--brand-accent-2)" }}>
              ver plan completo
            </button>
          )}
        </h3>
        <div className="flex items-center gap-2">
          {nutritionBlocked && (
            <span className="hidden text-xs text-[#E5B94E] sm:inline">
              {kcalInvalid ? "Pon las calorías objetivo para guardar" : "Los números no cuadran: mira el aviso de Nutrición"}
            </span>
          )}
          <button onClick={onCancel} className="btn btn-ghost"><X size={15} /> Cancelar</button>
          <button onClick={save} disabled={saving || nutritionBlocked} className="btn btn-primary"
            title={nutritionBlocked
              ? (kcalInvalid ? "Introduce las calorías objetivo"
                 : "Calorías y macros no cuadran: corrige el descuadre (aviso en Nutrición) para guardar")
              : undefined}>
            {saving ? <Spinner /> : <Save size={15} />} Guardar cambios
          </button>
        </div>
      </div>

      {/* Nutrición */}
      {only !== "training" && (
      <div ref={focusRefs.nutrition} className="card p-5" style={flashStyle("nutrition")}>
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
              onClick={() => { blurActive(); nutTouched.current = true; mutate((d) => applyTotals(d, rec)); }}
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
                <span className="inline-flex items-center gap-1 font-semibold" style={{ color: "#E5B94E" }}>
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
            onGram={(v) => setMacro("protein_g", v)} onPct={(v) => setMacroPct("protein_g", v)}
            max={MAX_MACRO} pctDisabled={kcalInvalid} />
          <MacroField label="Carbohidratos" gramValue={nut.macros.carbs_g} pct={mp.carbs}
            onGram={(v) => setMacro("carbs_g", v)} onPct={(v) => setMacroPct("carbs_g", v)}
            max={MAX_MACRO} pctDisabled={kcalInvalid} />
          <MacroField label="Grasas" gramValue={nut.macros.fat_g} pct={mp.fat}
            onGram={(v) => setMacro("fat_g", v)} onPct={(v) => setMacroPct("fat_g", v)}
            max={MAX_MACRO} pctDisabled={kcalInvalid} />
        </div>

        {/* Estado SIEMPRE visible: % de macros + déficit/superávit real de la
            dieta (también tras ediciones manuales). Verde si cuadra. */}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {/* Un ÚNICO veredicto: el chip usa el mismo booleano que el aviso y
              el bloqueo de guardado (nunca un "✓ verde" con el guardado
              bloqueado a la vez). */}
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold"
            style={totalsOk
              ? { background: "color-mix(in srgb, #4CC38A 14%, transparent)", color: "#4CC38A" }
              : { background: "color-mix(in srgb, #E5B94E 16%, transparent)", color: "#E5B94E" }}
          >
            {totalsOk ? <Check size={12} /> : <AlertTriangle size={12} />}
            Macros: {mp.total}%
          </span>
          {tdee && (nut.target_kcal ?? 0) > 0 ? (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-semibold"
              style={{ background: "color-mix(in srgb, var(--brand-accent-2) 12%, transparent)", color: "var(--brand-accent-2)" }}
              title={`Calorías objetivo (${Math.round(nut.target_kcal)}) sobre tu gasto (TDEE ${Math.round(tdee)} kcal)`}
            >
              {deficitLabel(tdee, nut.target_kcal ?? 0)} sobre el TDEE
            </span>
          ) : null}
          {(nut.target_kcal ?? 0) > 0 && (
            <button onClick={cuadrar} className="btn btn-ghost px-2 py-1 text-xs"
              title={goal && weight
                ? "Rehace el reparto de macros a estas calorías según el objetivo del cliente"
                : "Rellena con carbohidratos hasta cuadrar las calorías objetivo"}>
              {goal && weight ? "Cuadrar por objetivo" : "Cuadrar a 100%"}
            </button>
          )}
        </div>

        {/* AVISO PERSISTENTE: qué no cuadra (o qué tope de seguridad se viola),
            con cuánto, y cómo arreglarlo en un clic. No desaparece hasta que
            todo tenga relación entre sí; mientras tanto el guardado queda
            bloqueado (si el coach ha tocado la nutrición). */}
        {!totalsOk && (
          <div className="mt-2 rounded-lg border p-3 text-xs"
            style={{ background: "color-mix(in srgb, #E5B94E 10%, transparent)", borderColor: "color-mix(in srgb, #E5B94E 40%, transparent)", color: "#E5B94E" }}>
            <div className="flex items-start gap-2">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <div>
                {kcalInvalid ? (
                  <p><b>Faltan las calorías objetivo.</b> Ponlas (o elige un déficit/superávit arriba) para que el plan tenga sentido.</p>
                ) : !coherent ? (
                  <>
                    <p>
                      <b>No cuadra:</b> proteína {Math.round(nut.macros.protein_g ?? 0)} g + carbohidratos{" "}
                      {Math.round(nut.macros.carbs_g ?? 0)} g + grasas {Math.round(nut.macros.fat_g ?? 0)} g ={" "}
                      <b>{macroSumKcal} kcal</b>, pero el objetivo marca <b>{Math.round(nut.target_kcal)} kcal</b>{" "}
                      → {kcalDiff > 0 ? "sobran" : "faltan"} <b>{Math.abs(Math.round(kcalDiff))} kcal</b>{" "}
                      (≈ {Math.round(Math.abs(kcalDiff) / 4)} g de carbohidratos).
                    </p>
                    <p className="mt-1 opacity-80">
                      Ajusta los números tú mismo, o cuadra en un clic. Las comidas y el banco se
                      actualizarán en cuanto todo cuadre.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button onClick={cuadrarConCarbohidratos} className="btn btn-ghost px-2 py-1 text-xs"
                        title="Los carbohidratos absorben la diferencia; tu proteína y tus grasas se respetan tal cual">
                        Cuadrar con carbohidratos
                      </button>
                      {goal && weight && (
                        <button onClick={cuadrar} className="btn btn-ghost px-2 py-1 text-xs"
                          title="Rehace el reparto completo según el objetivo del cliente">
                          Cuadrar por objetivo
                        </button>
                      )}
                    </div>
                    {(nut.macros.protein_g ?? 0) * 4 + (nut.macros.fat_g ?? 0) * 9 > (nut.target_kcal ?? 0) && (
                      <p className="mt-1.5">
                        ⚠ Solo proteína y grasas ya suman{" "}
                        {kcalOf(nut.macros.protein_g ?? 0, 0, nut.macros.fat_g ?? 0)} kcal — ni con 0 g de
                        carbohidratos cuadra: baja proteína o grasas, sube las calorías, o usa «Cuadrar por objetivo».
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <p><b>Fuera de los topes de seguridad</b> (el sistema no reescribe tus números en silencio; te lo dice aquí):</p>
                    <ul className="mt-1 list-disc pl-4">
                      {(nut.macros.protein_g ?? 0) < bounds.pLo && (
                        <li>Proteína {Math.round(nut.macros.protein_g ?? 0)} g &lt; mínimo {bounds.pLo} g{weight ? ` (1,2 g/kg · ${weight} kg)` : ""}.</li>
                      )}
                      {(nut.macros.protein_g ?? 0) > bounds.pHi && (
                        <li>Proteína {Math.round(nut.macros.protein_g ?? 0)} g &gt; máximo {bounds.pHi} g{weight ? ` (3 g/kg)` : ""}.</li>
                      )}
                      {(nut.macros.fat_g ?? 0) < bounds.fLo && (
                        <li>Grasas {Math.round(nut.macros.fat_g ?? 0)} g &lt; mínimo saludable {bounds.fLo} g{weight ? ` (0,6 g/kg)` : ""}.</li>
                      )}
                      {(nut.macros.fat_g ?? 0) > bounds.fHi && (
                        <li>Grasas {Math.round(nut.macros.fat_g ?? 0)} g &gt; máximo {bounds.fHi} g{weight ? ` (2 g/kg)` : ""}.</li>
                      )}
                      {(nut.target_kcal ?? 0) < bounds.kLo && (
                        <li>Calorías {Math.round(nut.target_kcal)} &lt; mínimo {Math.round(bounds.kLo)} kcal{tdee ? ` (déficit máximo ${MAX_DEFICIT_PCT}% del TDEE)` : ""}.</li>
                      )}
                      {(nut.target_kcal ?? 0) > bounds.kHi && (
                        <li>Calorías {Math.round(nut.target_kcal)} &gt; máximo {Math.round(bounds.kHi)} kcal{tdee ? ` (superávit máximo ${MAX_SURPLUS_PCT}% del TDEE)` : ""}.</li>
                      )}
                    </ul>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {goal && weight && (
                        <button onClick={cuadrar} className="btn btn-ghost px-2 py-1 text-xs"
                          title="Rehace el reparto completo a valores seguros según el objetivo del cliente">
                          Cuadrar por objetivo
                        </button>
                      )}
                    </div>
                  </>
                )}
                {!nutTouched.current && (
                  <p className="mt-1.5 opacity-80">
                    Este plan ya venía así guardado. Si no tocas la nutrición puedes guardar
                    igualmente: el sistema la cuadrará sola al guardar.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        <p className="mt-2 text-xs text-zinc-500">
          Edición <b className="text-zinc-400">libre</b>: mueve calorías, gramos o % como quieras
          (incluido 0 o vaciar un campo) — ningún campo se reescribe mientras tecleas. Al cambiar las{" "}
          <b className="text-zinc-400">calorías</b>, los tres macros escalan en proporción como punto de
          partida; los gramos y % se respetan tal cual los dejes. Si algo no cuadra, el aviso de arriba
          te dice exactamente qué y cuánto, y no se guarda hasta que cuadre. Los objetivos por comida y
          los gramos del banco se reescalan solos en cuanto los totales tienen relación entre sí.
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
        {/* Sin trim/filter en vivo: filtrar mientras se teclea se COMÍA el
            Enter (la línea vacía desaparecía y la regla nueva se pegaba a la
            anterior). Las líneas vacías se limpian al GUARDAR. */}
        <Area label="Reglas de flexibilidad (una por línea)" value={(nut.flexibility_rules ?? []).join("\n")}
          onChange={(v) => mutate((d) => (d.nutrition.flexibility_rules = v.split("\n")))} />

        <div ref={focusRefs.supplements} style={flashStyle("supplements")} className="rounded-lg">
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
      </div>
      )}

      {/* Entrenamiento */}
      {only !== "nutrition" && (
      <div ref={focusRefs.training} className="card p-5" style={flashStyle("training")}>
        <Title icon={Dumbbell} text="Entrenamiento" />
        <Text label="Nombre del split" value={tr.split_name ?? ""} onChange={(v) => mutate((d) => (d.training.split_name = v))} />
        <Area label="Justificación del split" value={tr.split_rationale ?? ""} onChange={(v) => mutate((d) => (d.training.split_rationale = v))} />

        <Subhead text="Progresión semanal" />
        {tr.weekly_progression.map((w: any, i: number) => (
          <div key={i} className="mt-2 grid grid-cols-2 gap-2 rounded-lg p-2 sm:grid-cols-4" style={{ background: "var(--surface-raised)" }}>
            <Text label={`Sem ${w.week ?? i + 1} · intención`} value={w.intent ?? ""} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].intent = v))} />
            <Num label="Carga %" value={w.load_pct} onChange={(v) => mutate((d) => (d.training.weekly_progression[i].load_pct = Math.max(0, v ?? 0)))} />
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
                    onCreate={createExercise}
                  />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Num label="Series" value={ex.sets} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].sets = Math.max(0, v ?? 0)))} />
                  <Text label="Reps" value={ex.rep_range ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rep_range = v))} />
                  <Text label="RIR" value={ex.rir ?? ""} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rir = v))} />
                  <Num label="Descanso (s)" value={ex.rest_sec} onChange={(v) => mutate((d) => (d.training.sessions[si].exercises[ei].rest_sec = Math.max(0, v ?? 0)))} />
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
          <Num label="Pasos diarios" value={tr.cardio.daily_steps} onChange={(v) => mutate((d) => (d.training.cardio.daily_steps = Math.max(0, v ?? 0)))} />
        </div>
        <Area label="Instrucciones de deload" value={tr.deload_instructions ?? ""} onChange={(v) => mutate((d) => (d.training.deload_instructions = v))} />
      </div>
      )}

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
function NumberInput({ value, onChange, className, ariaLabel, min = 0, max, step, disabled, title }: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  className?: string; ariaLabel?: string; min?: number; max?: number; step?: number;
  disabled?: boolean; title?: string;
}) {
  const [raw, setRaw] = useState<string | null>(null);
  const focused = useRef(false);
  // Último valor EMITIDO por este input: si el prop `value` cambia sin pasar por
  // aquí (reorden de filas, recálculo, tope aplicado), el buffer local ya no
  // representa este campo y se descarta — en Safari/Firefox un clic en un botón
  // no roba el foco, así que el blur no llega y el buffer sobreviviría pegado
  // al ejercicio equivocado.
  // ⚠️ NUNCA mientras el campo tiene el FOCO: descartar el buffer en mitad del
  // tecleo hacía imposible borrar el campo o escribir "0" (el recálculo lo
  // reescribía en cada pulsación y el input "peleaba" con el coach).
  const lastEmitted = useRef<number | null | undefined>(undefined);
  if (raw !== null && !focused.current
      && lastEmitted.current !== undefined && value !== lastEmitted.current) {
    setRaw(null);
    lastEmitted.current = undefined;
  }
  const shown = raw !== null ? raw : (value ?? "");
  return (
    <input
      type="number" inputMode="decimal" min={min} max={max} step={step}
      value={shown}
      disabled={disabled}
      title={title}
      onFocus={() => { focused.current = true; }}
      onChange={(e) => {
        const s = e.target.value;
        setRaw(s);
        if (s === "") { lastEmitted.current = null; onChange(null); return; }
        const n = Number(s);
        const emitted = Number.isFinite(n) ? n : null;
        lastEmitted.current = emitted;
        onChange(emitted);
      }}
      onBlur={() => { focused.current = false; setRaw(null); lastEmitted.current = undefined; }}
      className={className}
      aria-label={ariaLabel}
    />
  );
}

/** Macro con gramos + su % de la dieta (editable, estilo MyFitnessPal). El %
 *  se traduce a gramos sobre las calorías objetivo: sin ellas queda
 *  deshabilitado (con el porqué en el título), no un campo que "no responde". */
function MacroField({ label, gramValue, pct, onGram, onPct, max, pctDisabled }: {
  label: string; gramValue: number | null | undefined; pct: number;
  onGram: (v: number | null) => void; onPct: (v: number | null) => void; max?: number;
  pctDisabled?: boolean;
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
            disabled={pctDisabled}
            title={pctDisabled ? "Pon primero las calorías objetivo: el % se calcula sobre ellas" : undefined}
            className="input w-full px-2 pr-5 text-center disabled:opacity-40"
            ariaLabel={`${label} en porcentaje`} />
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
/** Área de texto larga (justificación, reglas de flexibilidad…): usa el modal
 *  expandible compartido (components/ui.tsx) — en 2 líneas no se lee ni edita
 *  bien; al enfocarla se abre grande y "Hecho"/Esc/fuera la cierra. */
function Area({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return <ExpandableArea label={label} value={value} onChange={onChange} className="mt-2" />;
}

/** Selector de ejercicio con BUSCADOR y agrupado por GRUPO MUSCULAR: primero las
 *  VARIANTES (mismo patrón de movimiento) y después toda la biblioteca separada
 *  por músculo (orden alfabético). Teclear filtra por nombre o por músculo — el
 *  coach encuentra y cambia cualquier ejercicio en segundos. */
// Grupos musculares elegibles al crear un ejercicio a mano, con el patrón de
// movimiento por defecto de cada uno (el backend lo exige; alimenta guardrails
// y la agrupación de "Variantes" del propio selector).
const MUSCLE_CHOICES: [string, string, string][] = [
  ["pecho", "Pecho", "horizontal_push"],
  ["espalda", "Espalda", "horizontal_pull"],
  ["hombros", "Hombros", "shoulder_abduction"],
  ["biceps", "Bíceps", "elbow_flexion"],
  ["triceps", "Tríceps", "elbow_extension"],
  ["cuadriceps", "Cuádriceps", "squat"],
  ["isquios", "Isquios", "knee_flexion"],
  ["gluteos", "Glúteos", "hip_extension"],
  ["gemelos", "Gemelos", "plantar_flexion"],
  ["core", "Core", "core_flexion"],
  ["antebrazos", "Antebrazos", "elbow_flexion"],
  ["trapecio", "Trapecio", "scapular_elevation"],
  ["aductores", "Aductores", "hip_adduction"],
  ["cardio", "Cardio", "cardio"],
];

function ExerciseSelect({ library, lookup, value, fallbackName, onChange, onCreate }: {
  library: ExerciseOut[];          // solo ACTIVOS: candidatos del selector
  lookup?: ExerciseOut[];          // biblioteca completa (con archivados) para resolver el actual
  value: number;
  fallbackName: string;
  onChange: (id: number) => void;
  // Crear un ejercicio A MANO desde el buscador: devuelve el id nuevo o null.
  onCreate?: (name: string, muscle: string, pattern: string) => Promise<number | null>;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false); // muestra el selector de grupo muscular
  const [saving, setSaving] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  useDismiss(boxRef, () => setOpen(false), open); // fuera/ESC → se cierra

  // Al abrir: buscador limpio y con el foco puesto (a teclear directamente).
  useEffect(() => {
    if (open) {
      setQ("");
      setCreating(false);
      searchRef.current?.focus();
    }
  }, [open]);

  const cur = (lookup ?? library).find((e) => e.id === value);
  const currentName = cur?.canonical_name ?? fallbackName;

  const norm = (s: string) =>
    (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const nq = norm(q.trim());
  const matches = (e: ExerciseOut) =>
    !nq || norm(e.canonical_name).includes(nq) || norm(e.muscle_primary).includes(nq);
  const byName = (a: ExerciseOut, b: ExerciseOut) => a.canonical_name.localeCompare(b.canonical_name);

  // Variantes (mismo patrón) arriba del todo; el resto, POR GRUPO MUSCULAR.
  const variants = cur
    ? library.filter((e) => e.id !== value && e.movement_pattern === cur.movement_pattern && matches(e)).sort(byName)
    : [];
  const variantIds = new Set(variants.map((e) => e.id));
  const byMuscle = new Map<string, ExerciseOut[]>();
  for (const e of library) {
    if (e.id === value || variantIds.has(e.id) || !matches(e)) continue;
    const g = e.muscle_primary || "otros";
    if (!byMuscle.has(g)) byMuscle.set(g, []);
    byMuscle.get(g)!.push(e);
  }
  const groups = [...byMuscle.entries()]
    .map(([g, list]) => [g, list.sort(byName)] as const)
    .sort((a, b) => a[0].localeCompare(b[0]));
  const total = variants.length + groups.reduce((s, [, l]) => s + l.length, 0);

  function pick(id: number) {
    onChange(id);
    setOpen(false);
  }

  const createName = q.trim();
  const canCreate = !!onCreate && createName.length >= 3;

  async function doCreate(muscle: string, pattern: string) {
    if (!onCreate || saving) return;
    setSaving(true);
    const id = await onCreate(createName, muscle, pattern);
    setSaving(false);
    if (id != null) pick(id);
  }

  const GroupHeader = ({ text }: { text: string }) => (
    <div
      className="sticky top-0 z-[1] px-3 py-1 text-[10px] font-bold uppercase tracking-wider"
      style={{ background: "var(--surface-raised)", color: "var(--brand-accent-2)" }}
    >
      {text}
    </div>
  );
  const Item = ({ e }: { e: ExerciseOut }) => (
    <button
      type="button"
      onClick={() => pick(e.id)}
      className="block w-full truncate px-3 py-1.5 text-left text-xs text-zinc-200 hover:bg-zinc-500/10"
    >
      {e.canonical_name}
    </button>
  );

  return (
    <div ref={boxRef} className="relative block">
      <span className="mb-0.5 block text-xs text-zinc-500">Ejercicio (busca y cámbialo)</span>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="input flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="truncate">{currentName}</span>
        <ChevronDown size={14} className={`shrink-0 text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-lg border shadow-xl"
          style={{ background: "var(--surface)", borderColor: "var(--line-strong)" }}
        >
          <div className="border-b p-2" style={{ borderColor: "var(--line)" }}>
            <input
              ref={searchRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nombre o músculo…"
              aria-label="Buscar ejercicio"
              className="input w-full !py-1.5 text-xs"
            />
          </div>
          <div className="max-h-64 overflow-y-auto overscroll-contain" role="listbox">
            {variants.length > 0 && (
              <>
                <GroupHeader text="Variantes — mismo patrón" />
                {variants.map((e) => <Item key={e.id} e={e} />)}
              </>
            )}
            {groups.map(([g, list]) => (
              <div key={g}>
                <GroupHeader text={g} />
                {list.map((e) => <Item key={e.id} e={e} />)}
              </div>
            ))}
            {total === 0 && !canCreate && (
              <p className="px-3 py-3 text-xs text-zinc-500">
                Sin resultados para «{q}».
              </p>
            )}
          </div>
          {/* Escribir un ejercicio A MANO: crea en la biblioteca y lo selecciona.
              Aparece siempre que el texto tenga entidad (≥3 letras), también
              cuando hay resultados parecidos pero no el que el coach quiere. */}
          {canCreate && (
            <div className="border-t p-2" style={{ borderColor: "var(--line)" }}>
              {!creating ? (
                <button
                  type="button"
                  onClick={() => setCreating(true)}
                  className="block w-full rounded-md px-3 py-1.5 text-left text-xs font-semibold hover:bg-zinc-500/10"
                  style={{ color: "var(--brand-accent-2)" }}
                >
                  ＋ Crear «{createName}» como ejercicio nuevo
                </button>
              ) : (
                <div>
                  <p className="px-1 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                    ¿Grupo muscular de «{createName}»?
                  </p>
                  <div className="grid grid-cols-2 gap-1">
                    {MUSCLE_CHOICES.map(([slug, label, pattern]) => (
                      <button
                        key={slug}
                        type="button"
                        disabled={saving}
                        onClick={() => doCreate(slug, pattern)}
                        className="rounded-md px-2 py-1 text-left text-xs text-zinc-200 hover:bg-zinc-500/10 disabled:opacity-50"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
