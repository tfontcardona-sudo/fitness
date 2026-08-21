/** Avisos del plan: de párrafo a "título corto → acción".
 *
 *  Los hallazgos que la IA escribió ANTES de acotar su contrato son párrafos de
 *  40-60 palabras ("Aversiones alimentarias no respetadas en el plan. La
 *  anamnesis declara explícitamente 'Leche', 'Coco'…"). Están guardados en el
 *  plan, así que no basta con acortar el prompt: aquí se derivan de forma
 *  determinista las tres cosas que el coach necesita ver de un vistazo —
 *  QUÉ pasa, DE QUÉ tipo es y QUÉ hacer— dejando el texto completo como detalle.
 *
 *  Los hallazgos nuevos ya traen `title`/`action` de la IA y se usan tal cual.
 */

export interface RawFinding {
  severity: string;
  description: string;
  title?: string | null;
  action?: string | null;
  correccion_propuesta?: string | null;
}

export interface Aviso {
  severity: string;
  titulo: string;
  accion: string;
  detalle: string;
  categoria: Categoria;
  /** Concepto para fusionar duplicados entre revisores. */
  concepto: string;
  /** Cuántos revisores señalaron lo mismo (1 = solo uno). */
  veces: number;
  /** Dónde tiene que ir el coach para resolverlo (un clic, sin buscar). */
  destino: Destino;
}

/** Sitios a los que puede llevar un aviso. */
export type Destino = "nutricion" | "entreno" | "generar" | "anamnesis" | "plan";

export type Categoria =
  | "Seguridad alimentaria"
  | "Lesiones"
  | "Salud"
  | "Nutrición"
  | "Entrenamiento"
  | "Contexto del cliente"
  | "Otros";

/** Palabra clave → (categoría, acción por defecto). El orden IMPORTA: gana la
 *  primera que casa, así que lo de seguridad va primero. */
const REGLAS: { re: RegExp; cat: Categoria; accion: string }[] = [
  // El ORDEN manda: gana la primera regla que casa. Seguridad primero, y
  // salud/medicación ANTES que nutrición (si no, "toma Simvastatina" caía en
  // Nutrición por la palabra "toma").
  { re: /al[ée]rgen|alergia|intoleran|cel[ií]ac|gluten|lactosa|alimento odiado/i,
    cat: "Seguridad alimentaria", accion: "Corregir esa comida" },
  { re: /(?:aversi[oó]n|detesta|odia|no le gusta|no tolera)[\s\S]{0,40}(?:sentadilla|ejercicio|prensa|abductor|m[áa]quina|entren)/i,
    cat: "Entrenamiento", accion: "Cambiar esos ejercicios" },
  { re: /aversi[oó]n|detesta|odia|no le gusta|no respetad/i,
    cat: "Seguridad alimentaria", accion: "Corregir esa comida" },
  { re: /lesi[oó]n|contraindicaci|articulaci|articular|hombro|rodilla|lumbar|cadera|tobillo|mu[ñn]eca|cervical|restricci\w*\s+(?:de\s+)?(?:lesi|movili|articul)/i,
    cat: "Lesiones", accion: "Adaptar los ejercicios" },
  { re: /\btca\b|\btoc\b|trastorno alimentar|salud mental|depresi|ansiedad|medicaci|simvastatina|f[áa]rmac|anticonceptiv|patolog|colesterol|[áa]cido [úu]rico|lip[íi]dic|di[aá]bet|tiroid|cafe[íi]na|estr[ée]s/i,
    cat: "Salud", accion: "Revisar con el cliente" },
  { re: /trabaj|horario|jornada|turno|empresari|contexto laboral|presupuesto|compra|disponibilidad|tiempo para entrenar|log[ií]stica|sue[nñ]o/i,
    cat: "Contexto del cliente", accion: "Ajustar al día a día" },
  { re: /atwater|kcal|macro|prote[ií]na|carbohidrat|grasa|d[ée]ficit|super[aá]vit|comida|toma\b|men[uú]|picoteo|suplement|creatina|anabolic/i,
    cat: "Nutrición", accion: "Revisar la nutrición" },
  { re: /entrenamiento|entreno|sesi[oó]n|serie|ejercicio|volumen|progresi|deload|split/i,
    cat: "Entrenamiento", accion: "Revisar el entrenamiento" },
];

/** Primera frase del párrafo, que en la práctica ES el resumen: la IA escribía
 *  "<problema>. <justificación larga>". Se corta además por palabras para que
 *  entre en una línea del móvil. */
/** Arranques de relleno: el sujeto SIEMPRE es el mismo (el plan o el cliente)
 *  y el verbo casi siempre es "tiene"/"no aborda". Decirlo en cada línea gasta
 *  la mitad del ancho del móvil sin aportar nada. */
const ARRANQUES = [
  /^(?:el|la|los|las)\s+(?:cliente|clienta|paciente)\s+(?:tiene|presenta|declara|refiere|padece|sufre)\s+/i,
  /^(?:el|la)\s+cliente\s+/i,
  /^cliente\s+(?:tiene|presenta|declara|refiere)\s+/i,
  /^cliente\s+/i,
  // Sin el "no": ese caso va aparte para NO invertir el significado.
  /^(?:el\s+)?plan(?:\s+de\s+\w+)?\s+(?:aborda|contempla|refleja|incluye|considera|especifica|est[áa])\s*(?:expl[íi]citamente\s+)?(?:las?\s+|los?\s+)?/i,
  /^(?:el\s+)?plan\s+/i,
  /^la\s+anamnesis\s+(?:declara|lista|indica|recoge)\s*:?\s*/i,
  /^(?:existe|hay|se\s+observa|se\s+detecta)\s+/i,
  /^m[úu]ltiples\s+/i,
  /^consumo\s+de\s+/i,
  /^historial\s+de\s+/i,
  /^disponibilidad\s+de\s+/i,
  /^suplementaci[óo]n\s+con\s+/i,
];

/** Colas de relleno: "no abordado", "sin adaptación visible", "que el plan
 *  ignora"… Todas dicen lo mismo — que hay algo mal — y eso ya lo dice el
 *  color del aviso. */
const CIERRES = [
  /\s+(?:no|sin)\s+(?:abordad|contemplad|reflejad|adaptad|considerad|verificad|especificad|ajustad|recogid)\w*(?:\s+en\s+[\w\s]+)?$/i,
  /\s+sin\s+(?:adaptaci[óo]n|ajuste|precauciones|especificar)\b[\w\s]*$/i,
  /\s+que\s+el\s+plan\s+(?:no\s+)?\w+\s*$/i,
  /\s+(?:seg[úu]n|declarad[oa]s?\s+en)\s+su\s+anamnesis\s*$/i,
  /\s+no\s+(?:pueden|puede)\s+ser\s+[\w\s]+$/i,
  /\s+en\s+el\s+documento\s+entregado\s*$/i,
];

const COLETILLAS = [
  /\s+(?:ni|y)?\s*en (?:el|la|las|los) (?:plan|planificaci[oó]n|precauciones|estrategia)[^,.]*/i,
  /\s+(?:del|de la) (?:plan|planificaci[oó]n|cliente)\b/i,
  /\s+declarad[oa]s? en (?:la )?anamnesis\b/i,
  /\s+seg[uú]n (?:la )?anamnesis\b/i,
];

/** "El plan NO aborda X": se quita SOLO el sujeto y se conserva la negación
 *  ("No aborda X"). Reconstruirla como "Sin X" salía mal en frases largas y
 *  quitarla del todo afirmaba lo contrario de lo que dice el hallazgo. */
const SUJETO_NEGADO = /^(?:el\s+)?plan(?:\s+de\s+\w+)?\s+(?=no\s)/i;
/** "no está adaptado" → "No adaptado" (el verbo copulativo no aporta). */
const COPULA_NEGADA = /^no\s+(?:est[áa]|son|es|ha\s+sido|han\s+sido)\s+/i;

function primeraFrase(texto: string, maxPalabras = 5, crudo = false): string {
  const limpio = texto.replace(/^[\s•\-*]+/, "").trim();
  // Corta en el primer punto seguido de espacio+mayúscula (no parte "4/4/9" ni "1.5")
  if (crudo) {
    const p = limpio.split(/\s+/);
    return p.length > maxPalabras ? p.slice(0, maxPalabras).join(" ") + "…" : limpio;
  }
  const corte = limpio.search(/\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡'"«])/);
  let frase = corte > 0 ? limpio.slice(0, corte) : limpio;
  frase = frase.replace(/\s*[.:]\s*$/, "");
  // Fuera las coletillas obvias: el coach ya está mirando ESTE plan.
  for (const c of COLETILLAS) frase = frase.replace(c, "");
  // Fuera el sujeto ("El cliente tiene…") y el cierre vacío ("…no abordado").
  // La NEGACIÓN se conserva: perderla afirma lo contrario del hallazgo.
  const negado = SUJETO_NEGADO.test(frase);
  if (negado) {
    frase = frase.replace(SUJETO_NEGADO, "").replace(COPULA_NEGADA, "No ");
  } else {
    for (const a of ARRANQUES) frase = frase.replace(a, "");
  }
  for (const c of CIERRES) frase = frase.replace(c, "");
  frase = frase.replace(/\s*[.:,;]\s*$/, "").trim();
  if (!frase) return primeraFrase(texto.replace(/^[\s•\-*]+/, ""), maxPalabras, true);
  // Mayúscula inicial: al quitar el sujeto la frase empieza en minúscula.
  frase = frase.charAt(0).toUpperCase() + frase.slice(1);
  const palabras = frase.split(/\s+/);
  if (palabras.length > maxPalabras) {
    // Sin conectores colgando: "…como empresario,…" queda como "…como empresario…"
    frase = palabras.slice(0, maxPalabras).join(" ").replace(/(?:[\s,;:+]|\by\b)+$/i, "") + "…";
  }
  return frase;
}

/** Reescrituras directas: recortar "El plan de entrenamiento NO está incluido"
 *  por las reglas genéricas dejaba "Incluido", que dice lo contrario. */
const ESPECIALES: { re: RegExp; titulo: string }[] = [
  { re: /plan de entrenamiento\s+no\s+(?:est[áa] incluido|existe|se incluye)|entrenamiento (?:completamente )?ausente/i,
    titulo: "Sin plan de entrenamiento" },
  { re: /no pueden ser verificad|no se puede verificar/i, titulo: "Sin poder verificar" },
];

/** CONCEPTOS para fusionar duplicados: varios revisores señalan el MISMO
 *  problema con palabras distintas ("lesiones no abordadas", "restricciones no
 *  reflejadas", "lesiones articulares no contempladas"…). Se agrupan por
 *  concepto y se muestra UNA línea con el nº de revisores que lo vieron. */
const CONCEPTOS: { re: RegExp; key: string }[] = [
  { re: /aversi[óo]n|detesta|odia|no le gusta|alimento odiado/i, key: "aversion" },
  { re: /lesi[óo]n|lesiones|contraindicaci|articular|restricci\w*\s+(?:de\s+)?(?:lesi|movili|articul)/i, key: "lesion" },
  { re: /\btca\b|trastorno alimentar/i, key: "tca" },
  { re: /\btoc\b|ansiedad|depresi[óo]n|salud mental/i, key: "salud_mental" },
  { re: /medicaci|simvastatina|f[áa]rmac|anticoncep/i, key: "medicacion" },
  { re: /patolog|colesterol|[áa]cido [úu]rico|lip[íi]dic|diab[eé]t|tiroid/i, key: "patologia" },
  { re: /cafe[íi]na|caf[ée]s/i, key: "cafeina" },
  { re: /estr[ée]s/i, key: "estres" },
  { re: /suplement|creatina|anabolic/i, key: "suplemento" },
  { re: /trabaj|horario|jornada|empresari|turno/i, key: "trabajo" },
  { re: /disponibilidad|tiempo para entrenar/i, key: "tiempo" },
  { re: /atwater|kcal|macro|prote[íi]na|grasa|carbohidrat/i, key: "macros" },
  { re: /sue[nñ]o/i, key: "sueno" },
];

function concepto(texto: string): string {
  return CONCEPTOS.find((c) => c.re.test(texto))?.key ?? "";
}

/** Cuánta INFORMACIÓN concreta lleva un texto (cifras, listas entre paréntesis):
 *  al fusionar duplicados se conserva el que más datos aporta. */
function riqueza(texto: string): number {
  return (texto.match(/\d/g)?.length ?? 0) + (texto.match(/[(),]/g)?.length ?? 0);
}

/** La acción es una ETIQUETA, no una frase: se acota sin partir palabras. */
function acortarAccion(texto: string, maxPalabras = 6): string {
  const p = texto.trim().split(/\s+/);
  return p.length <= maxPalabras ? texto.trim() : p.slice(0, maxPalabras).join(" ") + "…";
}

/** Convierte un hallazgo (nuevo o antiguo) en algo que se lee de un vistazo. */
export function toAviso(f: RawFinding): Aviso {
  const detalle = (f.description ?? "").trim();
  const regla = REGLAS.find((r) => r.re.test(detalle) || r.re.test(f.title ?? ""));
  const especial = ESPECIALES.find((e) => e.re.test(detalle));
  const titulo = (f.title ?? "").trim() || especial?.titulo || primeraFrase(detalle);
  const accionIA = (f.action ?? "").trim();
  const derivada =
    (f.correccion_propuesta ?? "").trim().split(/\.\s/)[0] ||
    regla?.accion ||
    "Revisar el plan";
  // Solo se acota lo DERIVADO de texto libre; la de la IA llega ya acotada.
  const accion = accionIA || acortarAccion(derivada);
  return {
    severity: f.severity,
    titulo,
    accion,
    detalle,
    categoria: regla?.cat ?? "Otros",
    concepto: concepto(f.title ? `${f.title} ${detalle}` : detalle),
    veces: 1,
    destino: "plan",
  };
}

/** Fusiona los avisos que señalan el MISMO concepto: se queda con el que más
 *  datos concretos aporta y anota cuántos revisores lo vieron. Sin esto, ocho
 *  revisores señalando "lesiones sin adaptar" ocupaban ocho líneas idénticas. */
export function fusionar(avisos: Aviso[]): Aviso[] {
  const salida: Aviso[] = [];
  const porClave = new Map<string, number>();   // clave → índice en salida
  for (const a of avisos) {
    // Sin concepto reconocido no se fusiona: puede ser algo único.
    const clave = a.concepto ? `${a.categoria}|${a.concepto}` : "";
    const idx = clave ? porClave.get(clave) : undefined;
    if (idx === undefined) {
      if (clave) porClave.set(clave, salida.length);
      salida.push({ ...a });
      continue;
    }
    const actual = salida[idx];
    actual.veces += 1;
    // Se conserva el título con más datos y se acumula el detalle de ambos.
    if (riqueza(a.titulo) > riqueza(actual.titulo)) actual.titulo = a.titulo;
    if (a.detalle && !actual.detalle.includes(a.detalle)) {
      actual.detalle = `${actual.detalle}\n\n${a.detalle}`;
    }
    if (a.severity === "bloqueante") actual.severity = "bloqueante";
  }
  // El destino se calcula SIEMPRE (nadie más sabe a dónde lleva cada aviso).
  // La acción solo se reescribe si el aviso se FUSIONÓ —ahí el título cambia y
  // la heredada puede contradecirlo— o si no tenía acción propia: una acción
  // concreta de la IA ("Sustituir el pan por tortitas") vale más que un genérico.
  return salida.map((a) => {
    const calc = accionYDestino(a);
    const propia = a.veces === 1 && a.accion && a.accion !== "Revisar el plan";
    return { ...a, destino: calc.destino, accion: propia ? a.accion : calc.accion };
  });
}

/** Acción + destino coherentes con el título FINAL (tras fusionar).
 *
 *  Sin esto, tres avisos fusionados bajo "Sin plan de entrenamiento" heredaban
 *  la acción del primero ("Cambiar esos ejercicios"), que contradecía el
 *  título: si no hay plan, no hay ejercicios que cambiar. */
function accionYDestino(a: Aviso): { accion: string; destino: Destino } {
  const t = a.titulo.toLowerCase();
  if (/sin plan de entrenamiento|entrenamiento ausente|no hay rutina/.test(t)) {
    return { accion: "Generar el entrenamiento", destino: "generar" };
  }
  switch (a.categoria) {
    case "Seguridad alimentaria": return { accion: "Corregir esa comida", destino: "nutricion" };
    case "Nutrición":             return { accion: "Revisar la nutrición", destino: "nutricion" };
    case "Lesiones":              return { accion: "Adaptar los ejercicios", destino: "entreno" };
    case "Entrenamiento":         return { accion: a.accion || "Revisar el entrenamiento", destino: "entreno" };
    case "Salud":                 return { accion: "Ver su anamnesis", destino: "anamnesis" };
    case "Contexto del cliente":  return { accion: "Ver su anamnesis", destino: "anamnesis" };
    default:                      return { accion: a.accion || "Revisar el plan", destino: "plan" };
  }
}

/** Agrupa por categoría conservando el orden de importancia de REGLAS. */
export function agrupar(avisos: Aviso[]): { categoria: Categoria; items: Aviso[] }[] {
  const orden: Categoria[] = [
    "Seguridad alimentaria", "Lesiones", "Salud",
    "Nutrición", "Entrenamiento", "Contexto del cliente", "Otros",
  ];
  const mapa = new Map<Categoria, Aviso[]>();
  for (const a of fusionar(avisos)) {
    const lista = mapa.get(a.categoria);
    if (lista) lista.push(a);
    else mapa.set(a.categoria, [a]);
  }
  return orden
    .filter((c) => mapa.has(c))
    .map((c) => ({ categoria: c, items: mapa.get(c)! }));
}

// --------------------------------------------------- avisos del guardarraíl --

/** Nombres de campo del código → lenguaje del coach. */
const CAMPOS: Record<string, string> = {
  fat_g: "grasas", protein_g: "proteína", carbs_g: "carbohidratos",
  kcal: "kcal", fiber_g: "fibra",
};

/** `violation:opción slot 1 'A': fat_g 13 fuera de ±5% del objetivo 14`
 *  → { campo: "grasas", donde: "toma 1 'A'", texto: "13 g vs 14 g" }
 *  Devuelve null si el aviso no tiene ese formato (se muestra tal cual). */
function parseDesvio(flag: string) {
  const m = /opci[óo]n slot (\d+) '([^']+)':\s*(\w+)\s*([\d.,]+)\s*fuera de ±?\d+%\s*del objetivo\s*([\d.,]+)/i
    .exec(flag);
  if (!m) return null;
  const [, slot, opcion, campo, valor, objetivo] = m;
  return {
    campo: CAMPOS[campo] ?? campo,
    donde: `toma ${slot} '${opcion}'`,
    valor, objetivo,
  };
}

/** Traduce y AGRUPA los avisos técnicos del guardarraíl.
 *
 *  Cuatro líneas `violation:… fat_g … fuera de ±5% …` son el mismo problema en
 *  cuatro opciones: se resumen en una sola con el nº de opciones afectadas. El
 *  aviso "retenido:" se omite porque la cabecera del bloque ya lo dice. */
export function traducirFlags(flags: string[]): string[] {
  const desvios = new Map<string, { n: number; donde: string[] }>();
  const otros: string[] = [];
  for (const f of flags) {
    if (/^retenido/i.test(f)) {
      // No se descarta: puede ser el ÚNICO aviso rojo del plan, y sin él el
      // bloque no se pintaría y nadie sabría que el cliente no lo ha recibido.
      otros.push("Guardado como borrador · el cliente no lo ve");
      continue;
    }
    const d = parseDesvio(f);
    if (d) {
      const e = desvios.get(d.campo) ?? { n: 0, donde: [] };
      e.n += 1;
      if (e.donde.length < 3) e.donde.push(d.donde);
      desvios.set(d.campo, e);
      continue;
    }
    otros.push(f.replace(/^violation:\s*/i, "").replace(/^aviso:\s*/i, ""));
  }
  const salida = [...desvios.entries()].map(([campo, e]) =>
    e.n === 1
      ? `${campo[0].toUpperCase()}${campo.slice(1)} fuera de rango · ${e.donde[0]}`
      : `${campo[0].toUpperCase()}${campo.slice(1)} fuera de rango · ${e.n} opciones`,
  );
  return [...salida, ...otros];
}

/** Resumen de una línea para prosa guardada por la IA (notas de la progresión
 *  semanal, deload…): la primera frase dice lo esencial y el resto es
 *  justificación. El texto íntegro se conserva en el `title` de quien lo pinta. */
export function resumenCorto(texto: string, maxPalabras = 10): string {
  const limpio = (texto ?? "").replace(/^[\s•\-*]+/, "").trim();
  if (!limpio) return "";
  // La PRIMERA frase ("Semana de referencia."); el resto es justificación.
  const corte = limpio.search(/\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡'"«])/);
  let frase = (corte > 0 ? limpio.slice(0, corte) : limpio).replace(/\s*\.\s*$/, "");
  const palabras = frase.split(/\s+/);
  if (palabras.length > maxPalabras) {
    frase = palabras.slice(0, maxPalabras).join(" ").replace(/(?:[\s,;:+]|\by\b)+$/i, "") + "…";
  }
  return frase;
}

// ------------------------------------------------- resumen del detalle ------

/** Frases de VALORACIÓN sin dato: "…la dieta sola es insuficiente", "…el plan
 *  es incompleto e irresponsable". Repiten que algo está mal, que es justo lo
 *  que ya dice el color del aviso. */
const SIN_DATO =
  /^(?:sin|si no|de lo contrario|por (?:lo )?tanto|en consecuencia|esto (?:supone|implica))\b|(?:es|resulta) (?:insuficiente|incompleto|irresponsable|inadecuado|inaceptable|preocupante)|no se puede (?:verificar|comprobar|garantizar)/i;

/** Una frase solo se descarta si ADEMÁS no aporta ningún dato: "…aporta 12 g de
 *  proteína, insuficiente para sus 90 kg" es una valoración, pero lleva las
 *  cifras que el coach necesita. */
function esRelleno(frase: string): boolean {
  return SIN_DATO.test(frase) && datos(frase) === 0;
}

/** Firma de una frase para detectar repeticiones entre revisores: sin acentos,
 *  sin signos y sin palabras vacías, ordenada. Dos frases que dicen lo mismo
 *  con otro orden o con sinónimos de relleno comparten firma. */
const VACIAS = new Set([
  "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o", "a", "al",
  "que", "se", "su", "sus", "con", "por", "para", "no", "es", "son", "esta",
  "estas", "este", "estos", "pero", "cliente", "plan", "anamnesis", "declara",
  "indica", "tiene", "hay",
]);

function firma(frase: string): string {
  return frase
    .toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2 && !VACIAS.has(w))
    .sort()
    .join(" ");
}

/** Solape entre dos conjuntos de palabras (Jaccard): 1 = idénticos. */
function parecido(a: Set<string>, b: Set<string>): number {
  if (!a.size || !b.size) return 0;
  let comunes = 0;
  for (const w of a) if (b.has(w)) comunes++;
  return comunes / (a.size + b.size - comunes);
}

/** ¿Cuánta información concreta aporta la frase? (cifras, listas, paréntesis) */
function datos(frase: string): number {
  return (frase.match(/\d/g)?.length ?? 0) + (frase.match(/[(),:]/g)?.length ?? 0);
}

/** Resume el detalle de un aviso ya fusionado.
 *
 *  Al fusionar N revisores el detalle son N párrafos que repiten lo mismo con
 *  otras palabras. Aquí se parte en frases, se tiran las valoraciones sin dato,
 *  se quitan las repeticiones (misma firma → se conserva la que MÁS datos trae)
 *  y se devuelven como viñetas cortas. Nunca se inventa nada: solo se elige.
 */
export function resumirDetalle(detalle: string, maxFrases = 3): string[] {
  const frases = (detalle ?? "")
    .split(/(?<=[.;])\s+|\n+/)
    .map((f) => f.trim().replace(/^[•\-*\s]+/, "").replace(/\s*[.;]\s*$/, ""))
    .filter((f) => f.length > 12);

  // Dedupe por PARECIDO, no por igualdad: dos revisores describen la misma
  // lista de lesiones con una frase de entrada distinta y la firma exacta no
  // los reconocía como repetición.
  const candidatas: { frase: string; palabras: Set<string> }[] = [];
  for (const f of frases) {
    if (esRelleno(f)) continue;
    const k = firma(f);
    if (!k) continue;
    const palabras = new Set(k.split(" "));
    const gemela = candidatas.find((c) => parecido(c.palabras, palabras) >= 0.6);
    if (!gemela) {
      candidatas.push({ frase: f, palabras });
    } else if (datos(f) > datos(gemela.frase)) {
      // Se conserva la versión con MÁS datos concretos.
      gemela.frase = f;
      gemela.palabras = palabras;
    }
  }

  // Si todo eran valoraciones, mejor la primera frase original que nada.
  const salida = candidatas.map((c) => c.frase);
  if (!salida.length) return frases.slice(0, 1);

  // Las que más datos aportan, primero. NUNCA se descarta una en silencio
  // (podría ser el alérgeno): si sobran, se avisa de cuántas quedan fuera.
  const ordenadas = salida.sort((a, b) => datos(b) - datos(a));
  return ordenadas.length > maxFrases
    ? [...ordenadas.slice(0, maxFrases), `… y ${ordenadas.length - maxFrases} más`]
    : ordenadas;
}
