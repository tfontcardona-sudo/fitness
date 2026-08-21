/** Comprobación de `src/lib/findings.ts`: que los hallazgos LARGOS que la IA
 *  escribió antes de acotar su contrato sigan resumiéndose en una etiqueta
 *  corta, con su categoría y su acción.
 *
 *  Uso: npm run check:avisos
 */
import { build } from "esbuild";
import { strict as assert } from "node:assert";

const { outputFiles } = await build({
  entryPoints: ["src/lib/findings.ts"],
  bundle: true, write: false, format: "esm", logLevel: "error",
});
const mod = await import(
  "data:text/javascript;base64," + Buffer.from(outputFiles[0].text).toString("base64")
);

const CASOS = [
  { d: "Aversiones alimentarias no respetadas en el plan. La anamnesis declara explícitamente 'Leche', 'Coco', 'Gluten' y 'Lactosa' como aversiones.",
    cat: "Seguridad alimentaria" },
  { d: "Lesiones/contraindicaciones declaradas no abordadas. La anamnesis lista 8 zonas con restricción: 'cadera', 'codo', 'cuello'.",
    cat: "Lesiones" },
  { d: "Historial de trastorno alimentario (TCA) no abordado en el plan ni en las precauciones. La anamnesis declara que sí.",
    cat: "Salud" },
  { d: "Plan de entrenamiento completamente ausente. La anamnesis declara: 'Nivel: intermediate'.",
    cat: "Entrenamiento" },
  { d: "Presupuesto y disponibilidad de compra no reflejados en el plan de alimentos.",
    cat: "Contexto del cliente" },
];

let fallos = 0;
for (const { d, cat } of CASOS) {
  const a = mod.toAviso({ severity: "bloqueante", description: d });
  const palabras = a.titulo.split(/\s+/).length;
  const ok = a.categoria === cat && palabras <= 7 && a.accion && a.detalle === d;
  if (!ok) {
    fallos++;
    console.error(`✗ ${d.slice(0, 50)}…`);
    console.error(`   categoría: ${a.categoria} (esperada ${cat}) · ${palabras} palabras · acción "${a.accion}"`);
  } else {
    console.log(`✓ [${a.categoria}] ${a.titulo} → ${a.accion}`);
  }
}
// El título nunca puede quedarse vacío: sin él la fila del aviso no dice nada.
const vacio = mod.toAviso({ severity: "menor", description: "" });
if (vacio.accion === "") { fallos++; console.error("✗ un hallazgo vacío se queda sin acción"); }

// --- FUSIÓN: ocho revisores señalando lo mismo = UNA línea ------------------
const MISMO_PROBLEMA = [
  "El plan NO aborda explícitamente las múltiples lesiones declaradas.",
  "Múltiples lesiones y restricciones no pueden ser verificadas.",
  "Cliente tiene lesiones múltiples (rodilla, hombro, lumbar, cadera).",
  "Múltiples lesiones articulares (rodilla, hombro, lumbar) no contempladas.",
  "Restricciones de lesiones NO reflejadas",
  "El plan NO aborda las múltiples lesiones/contraindicaciones",
];
const fusionados = mod.fusionar(MISMO_PROBLEMA.map((d) =>
  mod.toAviso({ severity: "bloqueante", description: d })));
if (fusionados.length !== 1 || fusionados[0].veces !== MISMO_PROBLEMA.length) {
  fallos++;
  console.error(`✗ los ${MISMO_PROBLEMA.length} avisos de lesiones no se fusionaron en 1 (salen ${fusionados.length})`);
} else {
  console.log(`✓ ${MISMO_PROBLEMA.length} avisos de lesiones → 1 línea ×${fusionados[0].veces}: ${fusionados[0].titulo}`);
}
// Al fusionar se conserva el detalle de TODOS (es donde está la información).
for (const d of MISMO_PROBLEMA) {
  if (!fusionados[0]?.detalle.includes(d)) {
    fallos++; console.error(`✗ al fusionar se perdió un detalle: ${d.slice(0, 40)}…`);
    break;
  }
}

// --- JERGA: los avisos del guardarraíl, en lenguaje del coach --------------
const FLAGS = [
  "violation:opción slot 1 'A': fat_g 13 fuera de ±5% del objetivo 14",
  "violation:opción slot 3 'A': fat_g 6 fuera de ±5% del objetivo 7",
  "violation:opción slot 3 'B': fat_g 6 fuera de ±5% del objetivo 7",
  "retenido: guardado como BORRADOR — revisa y activa tú",
];
const traducidos = mod.traducirFlags(FLAGS);
// Los 3 desvíos de grasas se agrupan en 1, y "retenido" sobrevive traducido:
// descartarlo dejaba planes retenidos SIN ningún aviso rojo visible.
const sinJerga = !/fat_g|violation|±|BORRADOR/.test(traducidos.join(" "));
const conRetenido = traducidos.some((t) => /borrador/i.test(t));
if (traducidos.length !== 2 || !sinJerga || !conRetenido) {
  fallos++; console.error(`✗ traducción de avisos técnicos: ${JSON.stringify(traducidos)}`);
} else {
  console.log(`✓ ${FLAGS.length} avisos técnicos → ${traducidos.length} en español: ${traducidos.join(" · ")}`);
}

// La NEGACIÓN nunca se pierde: sin ella el título afirma lo contrario.
const neg = mod.toAviso({
  severity: "bloqueante",
  description: "El plan de entrenamiento no está adaptado a la lesión de rodilla.",
});
if (!/^no\b/i.test(neg.titulo)) {
  fallos++; console.error(`✗ se perdió la negación: "${neg.titulo}"`);
} else {
  console.log(`✓ negación conservada: "${neg.titulo}"`);
}

// No se fusionan avisos DISTINTOS que comparten una palabra ("restricción").
const distintos = mod.fusionar([
  mod.toAviso({ severity: "bloqueante", description: "Lesión de rodilla no contemplada en el plan." }),
  mod.toAviso({ severity: "bloqueante", description: "Restricción calórica del 35% excesiva." }),
]);
if (distintos.length !== 2) {
  fallos++; console.error(`✗ dos bloqueantes distintos se fusionaron en ${distintos.length}`);
} else {
  console.log("✓ dos bloqueantes distintos siguen siendo 2 líneas");
}

// --- PROSA GUARDADA: la nota de la semana cabe en una línea -----------------
const nota = "Semana de referencia. Deja cargas donde completes todas las series con 2-3 repeticiones en reserva y sin dolor articular. Anota pesos.";
const corto = mod.resumenCorto(nota);
if (corto !== "Semana de referencia") {
  fallos++; console.error(`✗ resumenCorto devolvió "${corto}"`);
} else {
  console.log(`✓ nota de ${nota.split(/\s+/).length} palabras → "${corto}"`);
}

if (fallos) { console.error(`\n${fallos} fallo(s)`); process.exit(1); }
console.log("\nAvisos OK");
