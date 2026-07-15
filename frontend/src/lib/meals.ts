/** Estructura de comidas del día (canónica) para el selector de la planificación.
 *  Fuente única compartida con el backend (services/meal_structure.py). */

export interface MealOption {
  key: string;
  name: string;
  time: string;
}

export const CANONICAL_MEALS: MealOption[] = [
  { key: "desayuno", name: "Desayuno", time: "08:00" },
  { key: "media_manana", name: "Media mañana", time: "11:00" },
  { key: "comida", name: "Comida", time: "14:00" },
  { key: "snack", name: "Snack", time: "17:00" },
  { key: "cena", name: "Cena", time: "21:00" },
  { key: "precama", name: "Pre-cama", time: "23:00" },
];

const norm = (s: string) =>
  (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

/** Peso típico de cada toma sobre el día (para dar objetivos a una comida
 *  NUEVA sin regenerar): desayuno 25%, media mañana 10%, comida 30%, snack 10%,
 *  cena 20%, pre-cama 5%. Solo son el punto de partida — el coach puede editar. */
export const MEAL_WEIGHTS: Record<string, number> = {
  desayuno: 0.25,
  media_manana: 0.1,
  comida: 0.3,
  snack: 0.1,
  cena: 0.2,
  precama: 0.05,
};

/** Clave canónica de UNA comida por su nombre (o null si no se reconoce). */
export function mealKeyFromName(name: string): string | null {
  const found = mealKeysFromNames([name]);
  return found.length ? found[0] : null;
}

/** Cambia la ESTRUCTURA de comidas del plan SIN regenerar: reparte las MISMAS
 *  kcal y macros del cliente entre las tomas elegidas. Las comidas que se quedan
 *  conservan sus proporciones entre sí (solo ceden el hueco de las nuevas, que
 *  entran con su peso típico); las quitadas devuelven su parte al resto. La suma
 *  por eje queda EXACTA a los totales (resto de redondeo a la comida mayor) y las
 *  kcal de cada comida salen de sus macros (misma invariante que el backend).
 *  El banco de comidas se re-numera para las tomas que siguen; una toma nueva
 *  queda sin recetario (se crea con "Regenerar con estas comidas" o a mano).
 *  Muta `nut`. */
export function restructureNutritionMeals(nut: any, keys: string[]): void {
  const selected = CANONICAL_MEALS.map((m) => m.key).filter((k) => keys.includes(k));
  if (selected.length < 1) return;

  const oldMeals: any[] = Array.isArray(nut.meals) ? nut.meals : [];
  const oldByKey = new Map<string, any>();
  for (const m of oldMeals) {
    const k = mealKeyFromName(m?.name ?? "");
    if (k && !oldByKey.has(k)) oldByKey.set(k, m);
  }
  const kept = selected.filter((k) => oldByKey.has(k));
  const added = selected.filter((k) => !oldByKey.has(k));
  const wSel = selected.reduce((s, k) => s + (MEAL_WEIGHTS[k] ?? 0.1), 0);
  const shareAdded = added.reduce((s, k) => s + (MEAL_WEIGHTS[k] ?? 0.1), 0) / wSel;

  // Totales del cliente (los que "le pertocan"): macros del plan; las kcal de
  // cada comida se derivan al final (4/4/9) para que todo cuadre solo.
  const totals: Record<string, number> = {
    protein_g: nut.macros?.protein_g ?? 0,
    carbs_g: nut.macros?.carbs_g ?? 0,
    fat_g: nut.macros?.fat_g ?? 0,
  };

  // Nuevo listado en el orden natural del día, slots 1..N. Las que se quedan
  // conservan su nombre y hora reales; las nuevas entran con los canónicos.
  const canonical = new Map(CANONICAL_MEALS.map((m) => [m.key, m]));
  const meals = selected.map((k, i) => {
    const prev = oldByKey.get(k);
    const c = canonical.get(k)!;
    return {
      slot: i + 1,
      name: prev?.name ?? c.name,
      time: prev?.time ?? c.time,
      target: { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 } as Record<string, number>,
    };
  });

  for (const axis of ["protein_g", "carbs_g", "fat_g"] as const) {
    const T = totals[axis];
    const poolKept = kept.reduce((s, k) => s + (oldByKey.get(k)?.target?.[axis] ?? 0), 0);
    for (let i = 0; i < selected.length; i++) {
      const k = selected[i];
      let v: number;
      if (oldByKey.has(k) && poolKept > 0) {
        // proporcional a lo que ya tenía, dentro del hueco que no ocupan las nuevas
        v = ((oldByKey.get(k).target?.[axis] ?? 0) * T * (1 - shareAdded)) / poolKept;
      } else {
        // comida nueva (o plan sin reparto previo): su peso típico sobre el total
        v = (T * (MEAL_WEIGHTS[k] ?? 0.1)) / wSel;
      }
      meals[i].target[axis] = Math.max(0, Math.round(v));
    }
    // Resto de redondeo a la comida mayor: la suma queda EXACTA al total.
    const diff = Math.round(T) - meals.reduce((s, m) => s + m.target[axis], 0);
    if (diff) {
      const biggest = meals.reduce((a, b) => (b.target[axis] > a.target[axis] ? b : a));
      biggest.target[axis] = Math.max(0, biggest.target[axis] + diff);
    }
  }
  for (const m of meals) {
    m.target.kcal = Math.round(m.target.protein_g * 4 + m.target.carbs_g * 4 + m.target.fat_g * 9);
  }
  nut.meals = meals;

  // Banco de comidas: renumera los slots de las tomas que SIGUEN y descarta los
  // de las quitadas. Una toma añadida queda sin bloque (portal y PDF lo toleran).
  const newSlotByKey = new Map(selected.map((k, i) => [k, i + 1]));
  const oldSlotToKey = new Map<number, string>();
  for (const m of oldMeals) {
    const k = mealKeyFromName(m?.name ?? "");
    if (k && !([...oldSlotToKey.values()].includes(k))) oldSlotToKey.set(m.slot, k);
  }
  const bank = nut.meal_bank;
  if (bank?.mode === "flexible_7" && Array.isArray(bank.slots)) {
    bank.slots = bank.slots
      .filter((s: any) => {
        const k = oldSlotToKey.get(s.slot);
        return k != null && newSlotByKey.has(k);
      })
      .map((s: any) => ({ ...s, slot: newSlotByKey.get(oldSlotToKey.get(s.slot)!)! }))
      .sort((a: any, b: any) => a.slot - b.slot);
  } else if (bank?.mode === "strict" && Array.isArray(bank.days)) {
    for (const d of bank.days) {
      d.meals = (d.meals ?? [])
        .filter((m: any) => {
          const k = oldSlotToKey.get(m.slot);
          return k != null && newSlotByKey.has(k);
        })
        .map((m: any) => ({ ...m, slot: newSlotByKey.get(oldSlotToKey.get(m.slot)!)! }))
        .sort((a: any, b: any) => a.slot - b.slot);
    }
  }
}

/** Deduce las claves canónicas a partir de los nombres de las comidas de un plan
 *  (o del meal_schedule de la anamnesis), para inicializar el selector. */
export function mealKeysFromNames(names: string[]): string[] {
  const found = new Set<string>();
  for (const raw of names || []) {
    const n = norm(raw);
    if (n.includes("desayuno")) found.add("desayuno");
    else if (n.includes("media") || n.includes("almuerzo")) found.add("media_manana");
    else if (n.includes("merienda") || n.includes("snack")) found.add("snack");
    else if (n.includes("precama") || n.includes("pre-cama") || n.includes("recena") || n.includes("antes de dormir"))
      found.add("precama");
    else if (n.includes("cena")) found.add("cena");
    else if (n.includes("comida") || n.includes("almuerzo")) found.add("comida");
  }
  // Devuelve en el ORDEN natural del día.
  return CANONICAL_MEALS.map((m) => m.key).filter((k) => found.has(k));
}
