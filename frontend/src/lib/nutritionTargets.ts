/** Objetivos de calorías y macros POR OBJETIVO del cliente, según la evidencia
 *  actual, y recálculo automático encadenado del plan al editar a mano.
 *
 *  Reglas (espejo de backend/services/metrics.py — cambiar allí y aquí a la vez):
 *  · Déficit moderado 15-25% preserva masa magra y adherencia (Helms 2014).
 *  · Superávit 5-12% minimiza la ganancia de grasa (Iraki 2019).
 *  · Recomposición ≈ mantenimiento con proteína alta 2,2-2,6 g/kg (Barakat 2020).
 *  · Lesión: mantenimiento a −5% y proteína 2,0-2,5 g/kg contra la atrofia
 *    (Tipton 2015). Nunca superávit ni déficit fuerte.
 *  · Proteína general 1,6-2,2 g/kg (Morton 2018); grasa mínima ~0,6 g/kg para
 *    función hormonal; carbohidratos = el resto de las calorías.
 */

import type { GoalType } from "../types";

export interface GoalRule {
  kcalFactor: number;   // multiplicador sobre TDEE (punto medio del rango)
  proteinPerKg: number; // g/kg de peso corporal
  fatPerKg: number;     // g/kg
  summary: string;      // explicación corta para el coach
}

export const GOAL_RULES: Record<GoalType, GoalRule> = {
  fat_loss: {
    kcalFactor: 0.80, proteinPerKg: 2.2, fatPerKg: 0.8,
    summary: "Déficit moderado (−20%) con proteína alta para conservar músculo.",
  },
  muscle_gain: {
    kcalFactor: 1.085, proteinPerKg: 1.9, fatPerKg: 0.9,
    summary: "Superávit ligero (+8,5%) — suficiente para construir sin acumular grasa.",
  },
  recomp: {
    kcalFactor: 1.0, proteinPerKg: 2.4, fatPerKg: 0.9,
    summary: "Calorías de mantenimiento; la proteína muy alta dirige la recomposición.",
  },
  maintenance: {
    kcalFactor: 1.0, proteinPerKg: 1.9, fatPerKg: 1.0,
    summary: "Mantenimiento: consolidar el peso y los hábitos actuales.",
  },
  injury_recovery: {
    kcalFactor: 0.975, proteinPerKg: 2.25, fatPerKg: 1.0,
    summary: "Mantenimiento ligero y proteína alta: la reparación necesita energía.",
  },
};

export interface MacroTargets {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export const kcalOf = (p: number, c: number, f: number): number =>
  Math.round(p * 4 + c * 4 + f * 9);

/** Macros óptimos para unas calorías dadas: proteína y grasa por peso corporal
 *  (según el objetivo), carbohidratos = el resto. Si no caben, la grasa baja
 *  hasta su mínimo saludable (0,6 g/kg) antes de recortar carbohidratos. */
export function macrosForKcal(goal: GoalType | null | undefined, weightKg: number, kcal: number): MacroTargets {
  const r = GOAL_RULES[goal ?? "maintenance"] ?? GOAL_RULES.maintenance;
  let protein = Math.round(weightKg * r.proteinPerKg);
  let fat = Math.round(weightKg * r.fatPerKg);
  const fatMin = Math.round(weightKg * 0.6);
  const proteinMin = Math.round(weightKg * 1.6);  // suelo de preservación de masa
  let carbs = Math.round((kcal - protein * 4 - fat * 9) / 4);
  if (carbs < 0) {
    // 1º baja la grasa hasta su mínimo saludable
    fat = Math.max(fatMin, Math.round((kcal - protein * 4) / 9));
    carbs = Math.round((kcal - protein * 4 - fat * 9) / 4);
  }
  if (carbs < 0) {
    // 2º si proteína+grasa mínimas aún superan las kcal, recorta la proteína
    // hasta su suelo: así los macros NUNCA declaran unas kcal que no cumplen.
    protein = Math.max(proteinMin, Math.round((kcal - fat * 9) / 4));
    carbs = Math.max(0, Math.round((kcal - protein * 4 - fat * 9) / 4));
  }
  return { kcal: Math.round(kcal), protein_g: protein, carbs_g: carbs, fat_g: fat };
}

/** Recomendación completa por objetivo a partir del TDEE y el peso. */
export function goalTargets(goal: GoalType | null | undefined, weightKg: number, tdee: number): MacroTargets {
  const r = GOAL_RULES[goal ?? "maintenance"] ?? GOAL_RULES.maintenance;
  return macrosForKcal(goal, weightKg, tdee * r.kcalFactor);
}

/** Redistribuye los macros al EDITAR uno de ellos MANTENIENDO FIJAS las calorías
 *  objetivo — igual que la IA, donde las kcal son el ancla y un macro "colchón"
 *  absorbe el cambio, de modo que P·4 + C·4 + G·9 siempre cuadra con las kcal.
 *
 *  Se edita `key` a `grams`. El colchón es CARBOHIDRATOS, salvo cuando se editan
 *  los propios carbohidratos: entonces absorbe la GRASA. Así la proteína
 *  (prioritaria por objetivo) se preserva siempre que se pueda. Si el colchón se
 *  quedaría negativo, se fija a 0 y las kcal reales bajan (nunca hay macros que
 *  declaren unas calorías que no cumplen). */
export function redistributeMacro(
  targetKcal: number,
  cur: { protein_g: number; carbs_g: number; fat_g: number },
  key: "protein_g" | "carbs_g" | "fat_g",
  grams: number,
): MacroTargets {
  let p = cur.protein_g, c = cur.carbs_g, f = cur.fat_g;
  if (key === "protein_g") {
    p = grams;
    c = Math.max(0, Math.round((targetKcal - p * 4 - f * 9) / 4));
  } else if (key === "fat_g") {
    f = grams;
    c = Math.max(0, Math.round((targetKcal - p * 4 - f * 9) / 4));
  } else {
    c = grams;
    f = Math.max(0, Math.round((targetKcal - p * 4 - c * 4) / 9));
  }
  return { kcal: kcalOf(p, c, f), protein_g: p, carbs_g: c, fat_g: f };
}

// ---- Déficit / superávit -----------------------------------------------------
// El cálculo de la dieta parte del TDEE: kcal = TDEE ± un porcentaje. Aquí lo
// exponemos de forma directa (nada de números complejos) para verlo y editarlo.

/** % con signo aplicado sobre el TDEE: -20 = déficit del 20%, +8 = superávit. */
export function signedDeficitPct(tdee: number, kcal: number): number {
  if (!tdee) return 0;
  return Math.round((kcal / tdee - 1) * 100);
}

/** Texto directo del cálculo aplicado ("Déficit del 20% sobre tu gasto"). Sin
 *  calorías objetivo (campo vacío) devuelve "—", para no mostrar "Déficit del
 *  100%" cuando kcal=0 y contradecir al desplegable (que cae a Mantenimiento). */
export function deficitLabel(tdee: number, kcal: number): string {
  if (!kcal || kcal <= 0) return "—";
  const p = signedDeficitPct(tdee, kcal);
  if (p < 0) return `Déficit del ${-p}%`;
  if (p > 0) return `Superávit del ${p}%`;
  return "Mantenimiento (0%)";
}

/** kcal objetivo para un % con signo sobre el TDEE. */
export function kcalFromDeficit(tdee: number, signedPct: number): number {
  return Math.round(tdee * (1 + signedPct / 100));
}

/** Texto de un % con signo ("Déficit 20%" / "Superávit 10%" / "Mantenimiento"). */
function deficitOptionLabel(p: number): string {
  if (p < 0) return `Déficit ${-p}%`;
  if (p > 0) return `Superávit ${p}%`;
  return "Mantenimiento (0%)";
}

/** Opciones del desplegable: mantenimiento + déficit/superávit de 5 en 5%
 *  (mín. 5%, máx. 50%). Si se pasa `current` y su % exacto no cae en la rejilla
 *  de 5% (p. ej. un plan IA con +8%), se añade como opción para que el
 *  desplegable no se desincronice ni "salte" al redondear. */
// Límites de seguridad (mismos que los guardrails del backend): déficit máx 30%,
// superávit máx 15%. No se ofrecen valores más agresivos en el desplegable.
export const MAX_DEFICIT_PCT = 30;
export const MAX_SURPLUS_PCT = 15;

export function deficitOptions(current?: number | null): { value: number; label: string }[] {
  const opts: { value: number; label: string }[] = [];
  for (let p = MAX_DEFICIT_PCT; p >= 5; p -= 5) opts.push({ value: -p, label: `Déficit ${p}%` });
  opts.push({ value: 0, label: "Mantenimiento (0%)" });
  for (let p = 5; p <= MAX_SURPLUS_PCT; p += 5) opts.push({ value: p, label: `Superávit ${p}%` });
  if (current != null && Number.isFinite(current)) {
    const c = Math.max(-95, Math.min(95, Math.round(current)));
    if (!opts.some((o) => o.value === c)) {
      opts.push({ value: c, label: deficitOptionLabel(c) });
      opts.sort((a, b) => a.value - b.value);
    }
  }
  return opts;
}

/** Valor del desplegable coherente con la etiqueta: el % exacto aplicado,
 *  acotado a un rango con sentido (evita blancos si las kcal quedan a 0). */
export function deficitSelectValue(tdee: number, kcal: number): number {
  if (!tdee || !kcal) return 0;
  return Math.max(-95, Math.min(95, signedDeficitPct(tdee, kcal)));
}

// ---- Porcentaje de cada macro (estilo MyFitnessPal) --------------------------
export const KCAL_PER_G = { protein_g: 4, carbs_g: 4, fat_g: 9 } as const;

/** Tolerancia (en puntos %) para dar los macros por "cuadrados" al 100%. Absorbe
 *  el redondeo de cada macro por separado (p. ej. 30+40+31 = 101 es correcto).
 *  Único origen: editor y vista usan el mismo umbral para no dar dos veredictos. */
export const MACRO_TOTAL_TOLERANCE = 2;

/** % que ocupa cada macro sobre las CALORÍAS OBJETIVO (no sobre la suma real):
 *  así, si se editan gramos y no cuadran, el total sale 95%/105% y avisa. */
export function macroPct(macros: { protein_g?: number; carbs_g?: number; fat_g?: number },
                         targetKcal: number): { protein: number; carbs: number; fat: number; total: number } {
  // Sin calorías objetivo (campo vacío) no hay porcentaje que calcular: 0, no
  // porcentajes disparatados (150 g / 1 kcal = 60000%).
  if (!targetKcal || targetKcal <= 0) return { protein: 0, carbs: 0, fat: 0, total: 0 };
  const k = targetKcal;
  const p = (macros.protein_g ?? 0) * 4, c = (macros.carbs_g ?? 0) * 4, f = (macros.fat_g ?? 0) * 9;
  return {
    protein: Math.round((p / k) * 100),
    carbs: Math.round((c / k) * 100),
    fat: Math.round((f / k) * 100),
    total: Math.round(((p + c + f) / k) * 100),
  };
}

/** Gramos de un macro para que ocupe cierto % de las calorías objetivo. */
export function gramsFromPct(pct: number, targetKcal: number, key: keyof typeof KCAL_PER_G): number {
  return Math.max(0, Math.round((pct / 100 * targetKcal) / KCAL_PER_G[key]));
}

/** Al EDITAR las calorías, los TRES macros suben o bajan EN PROPORCIÓN al mix
 *  del plan (la dieta ya está adaptada al cliente; no se re-ancla nada): P y G
 *  escalan por el ratio de calorías y los carbohidratos cuadran el 4/4/9
 *  exacto. Espejo de `macros_scaled_to_kcal` en services/nutrition_scale.py. */
export function macrosScaledToKcal(baseNut: any, kcal: number): MacroTargets {
  const m = baseNut?.macros ?? {};
  const p0 = m.protein_g ?? 0, c0 = m.carbs_g ?? 0, f0 = m.fat_g ?? 0;
  const old = kcalOf(p0, c0, f0) || baseNut?.target_kcal || kcal;
  const r = old > 0 ? kcal / old : 1;
  const protein = Math.round(p0 * r);
  const fat = Math.round(f0 * r);
  const carbs = Math.max(0, Math.round((kcal - protein * 4 - fat * 9) / 4));
  return { kcal: Math.round(kcal), protein_g: protein, carbs_g: carbs, fat_g: fat };
}

const scale = (v: any, f: number): any => (typeof v === "number" ? Math.round(v * f) : v);
const scaleG = (v: any, f: number): any => (typeof v === "number" ? Math.max(0, Math.round((v * f) / 5) * 5) : v); // gramos a múltiplos de 5

/** Reescala las cantidades DENTRO de un texto de equivalencias ("140 g crudo =
 *  380 g cocido"). Solo números con unidad g/gr/ml; "2 huevos" queda igual.
 *  Espejo de `_scale_amount_text` en services/nutrition_scale.py. */
function scaleAmountText(text: any, f: number): any {
  if (typeof text !== "string" || f === 1) return text;
  return text.replace(/(\d+(?:[.,]\d+)?)\s*(g|gr|ml)\b/g, (_m, num: string, unit: string) => {
    const v = parseFloat(num.replace(",", ".")) * f;
    const scaled = v >= 25 ? Math.round(v / 5) * 5 : Math.max(1, Math.round(v));
    return `${scaled} ${unit}`;
  });
}

/** Ratio del eje que corresponde a un grupo de equivalencias por su nombre. */
function equivRatio(name: any, rK: number, rP: number, rC: number, rF: number): number {
  const n = String(name ?? "").toLowerCase();
  if (n.includes("prote")) return rP;
  if (n.includes("gras")) return rF;
  if (["hidrat", "carb", "cereal", "almid", "frut"].some((k) => n.includes(k))) return rC;
  return rK;
}

/** Reescala TODO el plan de nutrición a los totales nuevos: objetivos por
 *  comida (cada eje por su propio ratio, así los totales cuadran) y banco de
 *  comidas (macros de cada opción + gramos de cada ingrediente, por el ratio
 *  de calorías, redondeados a 5 g para que las raciones sean cocinables). */
/** Topes FISIOLÓGICOS de los objetivos (ESPEJO de nutrition_scale.clamp_targets
 *  del backend — cambiar ambos a la vez): una edición absurda (CH 800 g, grasa
 *  0 g, +77% de superávit) se corrige al momento, en vivo y al guardar. */
export function clampTargets(next: MacroTargets, tdee?: number | null, weightKg?: number | null): MacroTargets {
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
  const w = weightKg && weightKg > 0 ? weightKg : 0;
  const pLo = w ? Math.round(w * 1.2) : 60;
  const pHi = w ? Math.round(w * 3.0) : 280;
  const fLo = w ? Math.max(20, Math.round(w * 0.6)) : 20;
  const fHi = w ? Math.round(w * 2.0) : 160;
  const p = Math.round(clamp(next.protein_g || 0, pLo, pHi));
  const f = Math.round(clamp(next.fat_g || 0, fLo, fHi));
  let kLo = 1100;
  let kHi = 4500;
  if (tdee && tdee > 0) {
    kLo = Math.max(1100, tdee * (1 - MAX_DEFICIT_PCT / 100));
    kHi = Math.min(4500, tdee * (1 + MAX_SURPLUS_PCT / 100));
    if (kLo > kHi) { kLo = 1100; kHi = 4500; }
  }
  const kcal = Math.round(clamp(next.kcal || kcalOf(p, next.carbs_g || 0, f), kLo, kHi));
  // Los carbohidratos cuadran el 4/4/9 con los valores ya acotados. Si no
  // caben (P y G acotadas superan las kcal), cede la grasa hasta su suelo y
  // después la proteína — MISMA cascada que reconcile_nutrition del backend:
  // lo que muestra el editor es EXACTAMENTE lo que se guardará.
  let pF = p;
  let fF = f;
  let carbs = Math.round((kcal - pF * 4 - fF * 9) / 4);
  if (carbs < 0) {
    fF = Math.max(fLo, Math.round((kcal - pF * 4) / 9));
    carbs = Math.round((kcal - pF * 4 - fF * 9) / 4);
  }
  if (carbs < 0) {
    const pMin = w ? Math.round(w * 1.6) : 60;
    pF = Math.max(pMin, Math.round((kcal - fF * 9) / 4));
    carbs = Math.max(0, Math.round((kcal - pF * 4 - fF * 9) / 4));
  }
  return { kcal, protein_g: pF, carbs_g: carbs, fat_g: fF };
}

export function rescaleNutrition(nut: any, next: MacroTargets, weightKg?: number | null): void {
  // Topes sanos SIEMPRE, vengan de donde vengan los objetivos.
  next = clampTargets(next, nut?.tdee_kcal, weightKg);
  const prev: MacroTargets = {
    kcal: nut.target_kcal ?? 0,
    protein_g: nut.macros?.protein_g ?? 0,
    carbs_g: nut.macros?.carbs_g ?? 0,
    fat_g: nut.macros?.fat_g ?? 0,
  };
  const ratio = (a: number, b: number) => (b > 0 ? a / b : 1);
  const rK = ratio(next.kcal, prev.kcal);
  const rP = ratio(next.protein_g, prev.protein_g);
  const rC = ratio(next.carbs_g, prev.carbs_g);
  const rF = ratio(next.fat_g, prev.fat_g);

  nut.macros = { ...(nut.macros ?? {}), protein_g: next.protein_g, carbs_g: next.carbs_g, fat_g: next.fat_g };
  // Una sola verdad numérica también en la vista en vivo del editor: el objetivo
  // ES exactamente la suma de sus macros (4/4/9), igual que persiste el backend
  // (reconcile_nutrition). Como los enteros no siempre alcanzan un objetivo
  // redondo (p. ej. 1800), el objetivo cede ≤2 kcal antes que descuadrar. Las
  // comidas ya recalculan sus kcal desde sus macros más abajo → todo cuadra.
  nut.target_kcal = kcalOf(next.protein_g, next.carbs_g, next.fat_g);

  for (const m of nut.meals ?? []) {
    if (!m?.target) continue;
    m.target = {
      ...m.target,
      kcal: scale(m.target.kcal, rK),
      protein_g: scale(m.target.protein_g, rP),
      carbs_g: scale(m.target.carbs_g, rC),
      fat_g: scale(m.target.fat_g, rF),
    };
  }
  // Resto de redondeo a la comida mayor de cada eje: la suma de las comidas
  // CUADRA EXACTA con los totales (espejo de services/nutrition_scale.py).
  const axes: [keyof MacroTargets, number][] = [
    ["kcal", next.kcal], ["protein_g", next.protein_g],
    ["carbs_g", next.carbs_g], ["fat_g", next.fat_g],
  ];
  for (const [key, total] of axes) {
    const targets = (nut.meals ?? [])
      .map((m: any) => m?.target)
      .filter((t: any) => t && typeof t[key] === "number");
    if (!targets.length) continue;
    const diff = Math.round(total) - targets.reduce((s: number, t: any) => s + t[key], 0);
    if (diff) {
      const biggest = targets.reduce((a: any, b: any) => (b[key] > a[key] ? b : a));
      biggest[key] = Math.max(0, biggest[key] + diff);
    }
  }
  // Cada comida cuadra SOLA: sus kcal salen de sus propios macros (4/4/9). Como
  // kcalOf es lineal, la suma sigue cuadrando con target_kcal. Deja la vista del
  // editor idéntica a lo que persiste el backend (reconcile_nutrition): sin saltos
  // al guardar.
  for (const m of nut.meals ?? []) {
    if (m?.target) {
      m.target.kcal = kcalOf(m.target.protein_g ?? 0, m.target.carbs_g ?? 0, m.target.fat_g ?? 0);
    }
  }

  // Cada plato queda COHERENTE CONSIGO MISMO (espejo de _scale_dish del
  // backend): macros por eje, kcal del plato = 4/4/9 de SUS macros, y los
  // gramos siguen la energía real del plato (no un ratio ajeno).
  const scaleDish = (o: any) => {
    if (!o) return;
    let rDish = rK;
    if (o.macros) {
      const oldK = typeof o.macros.kcal === "number" ? o.macros.kcal : 0;
      const nP = scale(o.macros.protein_g, rP);
      const nC = scale(o.macros.carbs_g, rC);
      const nF = scale(o.macros.fat_g, rF);
      const nK = [nP, nC, nF].every((x) => typeof x === "number")
        ? kcalOf(nP, nC, nF)
        : scale(o.macros.kcal, rK);
      o.macros = { ...o.macros, kcal: nK, protein_g: nP, carbs_g: nC, fat_g: nF };
      if (oldK > 0 && typeof nK === "number" && nK > 0) rDish = nK / oldK;
    }
    for (const ing of o.ingredients ?? []) {
      ing.grams = scaleG(ing.grams, rDish);
      // La medida casera ("1 taza ≈ 80 g") también lleva gramos dentro
      ing.household = scaleAmountText(ing.household, rDish);
    }
  };
  const bank = nut.meal_bank;
  if (bank?.mode === "flexible_7") {
    for (const slot of bank.slots ?? []) {
      for (const o of slot.options ?? []) scaleDish(o);
      // Equivalencias (comida/cena): cantidades en TEXTO, cada grupo por su eje
      const eq = slot.equivalences;
      if (eq) {
        eq.intro = scaleAmountText(eq.intro, rC);
        for (const g of eq.groups ?? []) {
          const r = equivRatio(g?.name, rK, rP, rC, rF);
          g.note = scaleAmountText(g.note, r);
          for (const it of g.items ?? []) it.amount = scaleAmountText(it.amount, r);
        }
      }
    }
  } else if (bank?.mode === "strict") {
    for (const d of bank.days ?? []) for (const m of d.meals ?? []) scaleDish(m?.dish);
  }
}

/** Copia de la nutrición BASE reescalada a los totales nuevos. El editor la usa
 *  en cada cambio para que comidas y gramos se recalculen SIEMPRE desde la
 *  versión original (idempotente): teclear "2" y luego "2500" no corrompe nada
 *  porque nunca se reescala sobre valores intermedios ya redondeados. */
export function rescaledFrom(baseNut: any, next: MacroTargets, weightKg?: number | null): any {
  const n = structuredClone(baseNut ?? {});
  rescaleNutrition(n, next, weightKg);
  return n;
}
