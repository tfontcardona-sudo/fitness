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
