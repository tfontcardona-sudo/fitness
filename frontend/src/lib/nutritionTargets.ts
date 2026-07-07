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
    kcalFactor: 0.975, proteinPerKg: 2.2, fatPerKg: 1.0,
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
  const protein = Math.round(weightKg * r.proteinPerKg);
  let fat = Math.round(weightKg * r.fatPerKg);
  const fatMin = Math.round(weightKg * 0.6);
  let carbs = Math.round((kcal - protein * 4 - fat * 9) / 4);
  if (carbs < 0) {
    fat = Math.max(fatMin, Math.round((kcal - protein * 4) / 9));
    carbs = Math.max(0, Math.round((kcal - protein * 4 - fat * 9) / 4));
  }
  return { kcal: Math.round(kcal), protein_g: protein, carbs_g: carbs, fat_g: fat };
}

/** Recomendación completa por objetivo a partir del TDEE y el peso. */
export function goalTargets(goal: GoalType | null | undefined, weightKg: number, tdee: number): MacroTargets {
  const r = GOAL_RULES[goal ?? "maintenance"] ?? GOAL_RULES.maintenance;
  return macrosForKcal(goal, weightKg, tdee * r.kcalFactor);
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

/** Reescala TODO el plan de nutrición a los totales nuevos: objetivos por
 *  comida (cada eje por su propio ratio, así los totales cuadran) y banco de
 *  comidas (macros de cada opción + gramos de cada ingrediente, por el ratio
 *  de calorías, redondeados a 5 g para que las raciones sean cocinables). */
export function rescaleNutrition(nut: any, next: MacroTargets): void {
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

  nut.target_kcal = next.kcal;
  nut.macros = { ...(nut.macros ?? {}), protein_g: next.protein_g, carbs_g: next.carbs_g, fat_g: next.fat_g };

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

  const scaleDish = (o: any) => {
    if (!o) return;
    if (o.macros) {
      o.macros = {
        ...o.macros,
        kcal: scale(o.macros.kcal, rK),
        protein_g: scale(o.macros.protein_g, rP),
        carbs_g: scale(o.macros.carbs_g, rC),
        fat_g: scale(o.macros.fat_g, rF),
      };
    }
    for (const ing of o.ingredients ?? []) {
      ing.grams = scaleG(ing.grams, rK);
    }
  };
  const bank = nut.meal_bank;
  if (bank?.mode === "flexible_7") {
    for (const slot of bank.slots ?? []) for (const o of slot.options ?? []) scaleDish(o);
  } else if (bank?.mode === "strict") {
    for (const d of bank.days ?? []) for (const m of d.meals ?? []) scaleDish(m?.dish);
  }
}

/** Copia de la nutrición BASE reescalada a los totales nuevos. El editor la usa
 *  en cada cambio para que comidas y gramos se recalculen SIEMPRE desde la
 *  versión original (idempotente): teclear "2" y luego "2500" no corrompe nada
 *  porque nunca se reescala sobre valores intermedios ya redondeados. */
export function rescaledFrom(baseNut: any, next: MacroTargets): any {
  const n = structuredClone(baseNut ?? {});
  rescaleNutrition(n, next);
  return n;
}
