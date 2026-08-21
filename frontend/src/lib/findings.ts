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
}

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
  { re: /al[ée]rgen|alergia|intoleran|cel[ií]ac|gluten|lactosa|aversi[oó]n|alimento odiado|no respetad/i,
    cat: "Seguridad alimentaria", accion: "Corregir esa comida" },
  { re: /lesi[oó]n|contraindicaci|zona[s]? con restricci|articulaci|hombro|rodilla|lumbar/i,
    cat: "Lesiones", accion: "Adaptar los ejercicios" },
  { re: /\btca\b|trastorno alimentar|salud mental|depresi|ansiedad|medicaci|anticonceptiv|patolog|di[aá]bet|tiroid/i,
    cat: "Salud", accion: "Revisar con el cliente" },
  { re: /sue[nñ]o|turno|jornada|contexto laboral|presupuesto|disponibilidad de compra|log[ií]stica/i,
    cat: "Contexto del cliente", accion: "Ajustar al día a día" },
  { re: /atwater|kcal|macro|prote[ií]na|carbohidrat|grasa|d[ée]ficit|super[aá]vit|comida|toma\b|men[uú]|picoteo/i,
    cat: "Nutrición", accion: "Revisar la nutrición" },
  { re: /entrenamiento|entreno|sesi[oó]n|serie|ejercicio|volumen|progresi|deload|split/i,
    cat: "Entrenamiento", accion: "Revisar el entrenamiento" },
];

/** Primera frase del párrafo, que en la práctica ES el resumen: la IA escribía
 *  "<problema>. <justificación larga>". Se corta además por palabras para que
 *  entre en una línea del móvil. */
const COLETILLAS = [
  /\s+(?:ni|y)?\s*en (?:el|la|las|los) (?:plan|planificaci[oó]n|precauciones|estrategia)[^,.]*/i,
  /\s+(?:del|de la) (?:plan|planificaci[oó]n|cliente)\b/i,
  /\s+declarad[oa]s? en (?:la )?anamnesis\b/i,
  /\s+seg[uú]n (?:la )?anamnesis\b/i,
];

function primeraFrase(texto: string, maxPalabras = 7): string {
  const limpio = texto.replace(/^[\s•\-*]+/, "").trim();
  // Corta en el primer punto seguido de espacio+mayúscula (no parte "4/4/9" ni "1.5")
  const corte = limpio.search(/\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡'"«])/);
  let frase = corte > 0 ? limpio.slice(0, corte) : limpio;
  frase = frase.replace(/\s*[.:]\s*$/, "");
  // Fuera las coletillas obvias: el coach ya está mirando ESTE plan.
  for (const c of COLETILLAS) frase = frase.replace(c, "");
  frase = frase.replace(/\s*[.:,]\s*$/, "").trim();
  const palabras = frase.split(/\s+/);
  if (palabras.length > maxPalabras) frase = palabras.slice(0, maxPalabras).join(" ") + "…";
  return frase;
}

/** Convierte un hallazgo (nuevo o antiguo) en algo que se lee de un vistazo. */
export function toAviso(f: RawFinding): Aviso {
  const detalle = (f.description ?? "").trim();
  const regla = REGLAS.find((r) => r.re.test(detalle) || r.re.test(f.title ?? ""));
  const titulo = (f.title ?? "").trim() || primeraFrase(detalle);
  const accion =
    (f.action ?? "").trim() ||
    (f.correccion_propuesta ?? "").trim().split(/\.\s/)[0] ||
    regla?.accion ||
    "Revisar el plan";
  return {
    severity: f.severity,
    titulo,
    // La acción también se acota: es una etiqueta, no una frase.
    accion: accion.split(/\s+/).slice(0, 6).join(" "),
    detalle,
    categoria: regla?.cat ?? "Otros",
  };
}

/** Agrupa por categoría conservando el orden de importancia de REGLAS. */
export function agrupar(avisos: Aviso[]): { categoria: Categoria; items: Aviso[] }[] {
  const orden: Categoria[] = [
    "Seguridad alimentaria", "Lesiones", "Salud",
    "Nutrición", "Entrenamiento", "Contexto del cliente", "Otros",
  ];
  const mapa = new Map<Categoria, Aviso[]>();
  for (const a of avisos) {
    const lista = mapa.get(a.categoria);
    if (lista) lista.push(a);
    else mapa.set(a.categoria, [a]);
  }
  return orden
    .filter((c) => mapa.has(c))
    .map((c) => ({ categoria: c, items: mapa.get(c)! }));
}
