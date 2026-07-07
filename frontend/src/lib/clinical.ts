/** Clasificación de la información clínica de la anamnesis.
 *
 *  La IA extrae los datos como listas en puntos ("- Lesión de rodilla…").
 *  Aquí distinguimos lo REALMENTE relevante (para marcar en rojo o mostrar en
 *  el resumen) de lo que es una NEGACIÓN ("Sin lesiones"), un CERO
 *  ("Embarazos: 0") o un valor tranquilizador ("Ciclo regular"). Se usa igual
 *  en Puntos importantes (Planificación) y en Notas clínicas (Resumen), para
 *  que ambos coincidan siempre.
 */

// Guion/viñeta al inicio: hay que quitarlo ANTES de evaluar la negación.
const BULLET = /^[\s\-•*·]+/;

// Empieza por una negación → no es un problema ("Sin lesión de hombro…").
const NEG_START = /^(no|sin|ning[uú]n[oa]?|nunca|jam[aá]s|ausencia)\b/i;

// Palabra que denota un problema REAL a respetar en dieta o entrenamiento.
// (NO incluye "suplement": la suplementación habitual —creatina, omega-3— no
//  es un riesgo; sale en el resumen pero sin marcarse en rojo.)
const CRITICAL =
  /lesi[oó]n|hernia|protrus|pinzamiento|rotura|desgarr|f[ií]sura|luxaci|esguince|cirug|operaci|pr[oó]tesis|tendinit|condromalac|fascit|bursit|artros|artrit|lumbalg|ci[aá]tic|escoliosis|lordosis|cifosis|dolor|molesti|alerg|intoleran|cel[ií]ac|gluten|lactosa|fructosa|sorbitol|fodmap|diab[eé]t|hipertens|hipotiro|hipertiro|tiroid|tirox|levotirox|asma|epilep|anticoagul|card[ií]ac|arritmia|reflujo|gastritis|colon irritable|\bsii\b|\bsibo\b|hinchaz|diarrea|estre[nñ]im|malestar|sangrad|abundante|anemia|migra[nñ]|trastorno (alimentari|de (la )?conducta)|\btca\b|anorexia|bulimia|atrac[oó]n|embaraz|lactanc|menopaus|\bsop\b|endometri/i;

// Ya RESUELTO / superado → deja de ser crítico ("molestia ya resuelta"),
// salvo que sea "no resuelta" (ahí sigue siendo un problema activo).
const RESOLVED = /\bresuelt[oa]s?\b|\bsuperad[oa]s?\b|\bde la infancia\b/i;
const NOT_RESOLVED = /\bno\s+(resuelt|superad)/i;

/** "clave: valor" cuyo VALOR es nulo (0, no, ninguno) → no es un problema.
 *  Ej.: "Embarazos: 0; partos: 0; abortos: 0" o "Menopausia: no". */
function isNullValue(core: string): boolean {
  const colon = core.indexOf(":");
  if (colon < 0) return false;
  const value = core.slice(colon + 1);
  const stripped = value
    .replace(/\b(no|s[ií]|ning[uú]n[oa]?|0|partos?|abortos?|embarazos?|menopausia|peri)\b/gi, "")
    .replace(/[\s;,.:\-–—/()]/g, "");
  return stripped === "";
}

// Descriptor tranquilizador: "regular", "normal", "sin problemas"…
const REASSURING = /\b(regular|normal|correct[oa]|adecuad[oa]|estable|sin (problemas|alteraciones|novedad|s[ií]ntomas|dolor)|no aplica|dentro de la normalidad)\b/i;

/** ¿Es una línea clínica CRÍTICA (a vigilar, marcar en rojo)? */
export function isCriticalLine(line: string): boolean {
  const core = line.replace(BULLET, "").trim();
  if (!core) return false;
  // Una negación al inicio SIEMPRE gana ("Sin roturas fibrilares…").
  if (NEG_START.test(core)) return false;
  if (!CRITICAL.test(core)) return false;
  // Tiene palabra crítica pero el valor es nulo o tranquilizador.
  if (isNullValue(core)) return false;
  // Lesión/molestia YA RESUELTA no es crítica (pero "no resuelta" sí lo es).
  if (RESOLVED.test(core) && !NOT_RESOLVED.test(core)) return false;
  if (REASSURING.test(core) && !/dolor|sangrad|abundante/i.test(core)) return false;
  return true;
}

/** ¿Merece salir en el resumen clínico? Relevante = no es puro "no/0/negación".
 *  Deja pasar lo informativo (deposiciones, Bristol…) y todo lo crítico. */
export function isRelevantClinical(line: string): boolean {
  const core = line.replace(BULLET, "").trim();
  if (!core) return false;
  if (isCriticalLine(core)) return true;
  if (NEG_START.test(core)) return false;
  if (isNullValue(core)) return false;
  // Frases puramente tranquilizadoras sin dato ("Ciclo regular", "Menopausia: no")
  if (REASSURING.test(core) && core.split(/\s+/).length <= 4) return false;
  return true;
}
