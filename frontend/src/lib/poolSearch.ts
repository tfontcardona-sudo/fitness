/** Buscador INTELIGENTE del pool de rutinas — determinista y al instante.
 *
 *  El entrenador escribe lo que piensa ("adelgazar barriga 3 dias", "señora
 *  50 años espalda", "volumen brazos en casa") y el buscador encuentra la
 *  rutina aunque las palabras no coincidan con el título:
 *   - normaliza tildes y mayúsculas,
 *   - expande SINÓNIMOS del vocabulario real de gimnasio (adelgazar→grasa,
 *     tonificar→mantenimiento, novato→principiante, lumbago→lumbar…),
 *   - tolera erratas (distancia de edición ≤1 en palabras largas),
 *   - y puntúa por dónde aparece: título > caso del cliente > carpeta/metadatos.
 *  Busca SIEMPRE en las 6 carpetas a la vez.
 */
import type { TemplateListItem } from "../types";

export function normalize(s: string): string {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9ñ\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Grupos de términos intercambiables (ya normalizados, sin tildes). El
 *  vocabulario con el que se habla en la sala, no el técnico. */
const GROUPS: string[][] = [
  // objetivos
  ["grasa", "adelgazar", "adelgace", "perder", "peso", "definir", "definicion",
   "quemar", "deficit", "barriga", "tripa", "panza", "michelines", "cintura",
   "abdomen", "flacidez"],
  ["musculo", "masa", "volumen", "hipertrofia", "crecer", "ganar", "grande",
   "tamano", "corpulento"],
  ["fuerza", "basicos", "powerlifting", "sentadilla", "press", "banca",
   "peso muerto", "dominadas", "rendimiento", "explosivo", "potencia"],
  ["tono", "tonificar", "tonificacion", "mantener", "mantenimiento", "forma",
   "definido", "marcado", "habito", "salud general"],
  ["salud", "molestia", "molestias", "dolor", "lesion", "patologia",
   "recuperacion", "rehabilitacion", "postura", "postural"],
  // zonas y casos clinicos comunes
  ["espalda", "lumbar", "lumbago", "lumbalgia", "hernia", "ciatica", "dorsal"],
  ["cervical", "cervicalgia", "cuello", "pantallas"],
  ["rodilla", "menisco", "rotula", "artrosis"],
  ["hombro", "manguito", "tendinitis"],
  ["gluteo", "gluteos", "culo", "pierna", "piernas", "femoral"],
  ["brazo", "brazos", "biceps", "triceps"],
  ["pecho", "pectoral", "torso"],
  ["core", "abdominales", "plancha", "faja"],
  ["embarazo", "embarazada", "gestacion", "prenatal"],
  ["posparto", "postparto", "cesarea", "suelo pelvico"],
  ["hipertension", "hipertenso", "tension alta"],
  ["diabetes", "diabetico", "glucosa"],
  ["osteoporosis", "hueso", "densidad osea"],
  ["escoliosis", "cifosis", "chepa"],
  ["menopausia", "climaterio"],
  ["obesidad", "sobrepeso", "impacto bajo"],
  ["corredor", "runner", "correr", "carrera", "maraton"],
  ["padel", "tenis", "futbol", "futbolista", "ciclista", "bici", "escalada",
   "nadador", "natacion", "deporte", "deportista"],
  ["oposicion", "opositor", "bombero", "policia", "militar", "pruebas fisicas"],
  // perfil / situación
  ["principiante", "novato", "empezar", "empiezo", "primer dia", "nunca",
   "cero", "iniciacion", "primeros pasos", "miedo"],
  ["vuelta", "volver", "retomar", "paron", "anos sin", "regreso", "retorno",
   "vacaciones", "descolgado"],
  ["mayor", "senior", "50", "55", "60", "65", "edad", "abuelo", "jubilado",
   "nietos"],
  ["adolescente", "joven", "16", "17", "estudiante", "universitario"],
  ["mujer", "chica", "senora", "ella", "femenino"],
  ["hombre", "chico", "senor", "masculino"],
  ["poco tiempo", "rapida", "rapido", "expres", "corta", "30 min", "40 min",
   "45 min", "ocupado", "agenda", "ejecutivo", "padres", "madre", "padre",
   "minimo"],
  ["turnos", "noche", "nocturno", "horario variable"],
  ["viaje", "viajes", "viajante", "hotel", "hoteles", "comercial"],
  ["estres", "ansiedad", "sueno", "dormir", "cansado", "fatiga"],
  // lugar y material
  ["casa", "domicilio", "hogar", "sin material", "sin equipo", "salon"],
  ["bandas", "gomas", "elasticos"],
  ["mancuernas", "pesas"],
  ["gimnasio", "gym", "sala", "maquinas", "centro"],
  ["peso corporal", "autocarga", "calistenia", "sin pesas"],
  // dias por semana
  ["2", "dos"], ["3", "tres"], ["4", "cuatro"], ["5", "cinco"], ["6", "seis"],
];

const STOPWORDS = new Set([
  "de", "la", "el", "los", "las", "un", "una", "que", "con", "para", "por",
  "en", "y", "o", "a", "al", "del", "se", "su", "mi", "quiero", "quiere",
  "busco", "busca", "cliente", "clienta", "rutina", "rutinas", "plan",
  "entrenamiento", "entreno", "entrenar", "dias", "dia", "semana", "anos",
  "ano", "solo", "sola", "tiene", "hacer", "algo", "mas", "muy", "poco",
  "sin", "necesita", "pide",
]);

/** Distancia de edición acotada a 1 (suficiente para erratas de teclado). */
function lev1(a: string, b: string): boolean {
  if (a === b) return true;
  const la = a.length, lb = b.length;
  if (Math.abs(la - lb) > 1) return false;
  let i = 0, j = 0, edits = 0;
  while (i < la && j < lb) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++edits > 1) return false;
    if (la === lb) { i++; j++; } else if (la > lb) { i++; } else { j++; }
  }
  return edits + (la - i) + (lb - j) <= 1;
}

function tokenMatchesWord(token: string, word: string): boolean {
  if (word.includes(token) && token.length >= 3) return true;
  if (token.includes(word) && word.length >= 4) return true;
  if (token.length >= 5 && word.length >= 5 && lev1(token, word)) return true;
  return token === word;
}

/** Objetivo (carpeta) que implica cada grupo y cuánto lo refuerza. Nombrar una
 *  DOLENCIA es un filtro casi duro (si dice "lumbago" quiere rutinas de espalda,
 *  no una de grasa que mencione "oficina"), así que pesa más que un objetivo
 *  general. Los índices siguen el orden de GROUPS. */
const GROUP_GOAL: Record<number, [string, number]> = {
  0: ["perdida_grasa", 1.6], 1: ["ganancia_muscular", 1.6], 2: ["fuerza", 1.6],
  3: ["mantenimiento", 1.6],
  // dolencias y condiciones clínicas
  4: ["salud_espalda", 2.2], 5: ["salud_espalda", 2.2], 6: ["salud_espalda", 2.2],
  7: ["salud_espalda", 2.2], 8: ["salud_espalda", 2.2], 13: ["salud_espalda", 2.2],
  14: ["salud_espalda", 2.2], 15: ["salud_espalda", 2.2], 16: ["salud_espalda", 2.2],
  17: ["salud_espalda", 2.2], 18: ["salud_espalda", 2.2], 20: ["salud_espalda", 1.8],
  19: ["mantenimiento", 1.8],
  // situación de partida
  24: ["principiantes", 1.8], 25: ["principiantes", 1.8],
};

interface Term { t: string; w: number }

/** Expande un token a su grupo de sinónimos. El término tecleado pesa 1; los
 *  sinónimos 0,5: así «lumbago» no se lo lleva una rutina de hipertrofia solo
 *  porque lleve «espalda» en el título. Devuelve también el objetivo implícito. */
function expand(token: string): { terms: Term[]; goals: [string, number][] } {
  const map = new Map<string, number>([[token, 1]]);
  const goals: [string, number][] = [];
  GROUPS.forEach((group, i) => {
    if (!group.some((w) => tokenMatchesWord(token, w))) return;
    const goal = GROUP_GOAL[i];
    if (goal) goals.push(goal);
    for (const w of group) {
      // «defincion» no es un sinónimo de «definición»: es la MISMA palabra mal
      // escrita, así que pesa casi como el literal (0,9) y no como sinónimo.
      const peso = w.length >= 5 && token.length >= 5 && lev1(token, w) ? 0.9 : 0.5;
      if ((map.get(w) ?? 0) < peso) map.set(w, peso);
    }
  });
  map.set(token, 1);
  return { terms: [...map].map(([t, w]) => ({ t, w })), goals };
}

export interface RankedTemplate extends TemplateListItem {
  _score: number;
}

/** Ordena TODAS las rutinas por afinidad con lo que escribió el entrenador. */
export function rankTemplates(
  items: TemplateListItem[],
  catLabels: Map<string, string>,
  query: string,
): RankedTemplate[] {
  const tokens = normalize(query).split(" ").filter(
    (t) => t.length >= 2 && !STOPWORDS.has(t));
  if (tokens.length === 0) return [];

  const expanded = tokens.map(expand);
  // Objetivos implícitos en la consulta ("adelgazar" → pérdida de grasa;
  // "lumbago" → salud). Si dos grupos apuntan a la misma carpeta, manda el
  // refuerzo más alto.
  const goals = new Map<string, number>();
  for (const [cat, boost] of expanded.flatMap((e) => e.goals)) {
    goals.set(cat, Math.max(goals.get(cat) ?? 0, boost));
  }
  const out: RankedTemplate[] = [];
  for (const t of items) {
    const ftitle = normalize(t.title);
    const fcase = normalize(t.case_note ?? "");
    const wtitle = new Set(ftitle.split(" "));
    const wcase = new Set(fcase.split(" "));
    const fmeta = normalize([
      catLabels.get(t.category) ?? t.category,
      t.level === "beginner" ? "principiante" : t.level === "intermediate" ? "intermedio" : t.level === "advanced" ? "avanzado" : "",
      t.training_place === "home" ? "casa" : "gimnasio",
      t.days_per_week != null ? `${t.days_per_week}` : "",
    ].join(" "));
    const caseWords = fcase.split(" ");
    const wmeta = new Set(fmeta.split(" "));
    // Términos CORTOS (<4) y números: solo palabra completa — "el"/"50"/"2"
    // como subcadena casarían con "nivel" o "150" y ensuciarían el ranking.
    const hitIn = (term: string, field: string, words: Set<string>): boolean =>
      term.length >= 4 || term.includes(" ") ? field.includes(term) : words.has(term);

    let score = 0;
    let matched = 0;
    for (const { terms } of expanded) {
      let best = 0;
      for (const { t: term, w } of terms) {
        if (hitIn(term, ftitle, wtitle)) { best = Math.max(best, 5 * w); continue; }
        if (hitIn(term, fcase, wcase)) { best = Math.max(best, 3.5 * w); continue; }
        if (hitIn(term, fmeta, wmeta)) { best = Math.max(best, 2 * w); continue; }
        // erratas contra las palabras del caso ("lumbalgia"~"lumbalgias")
        if (term.length >= 5 && best < 1.5 * w
            && caseWords.some((x) => x.length >= 5 && lev1(term, x))) {
          best = Math.max(best, 1.5 * w);
        }
      }
      if (best > 0) matched++;
      score += best;
    }
    if (score <= 0) continue;
    // El OBJETIVO manda: las rutinas de la carpeta que pide la consulta suben
    // en bloque, pero MULTIPLICANDO — así, dentro de la carpeta correcta, sigue
    // ganando la que mejor encaja con las palabras (no se aplana el ranking).
    const boost = goals.get(t.category);
    if (boost) score *= boost;
    // Cobertura: encontrar TODOS los conceptos pedidos vale más que repetir uno.
    score *= matched / tokens.length;
    out.push({ ...t, _score: score });
  }
  out.sort((a, b) => b._score - a._score || a.title.localeCompare(b.title));
  return out.slice(0, 40);
}
