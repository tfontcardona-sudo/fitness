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

if (fallos) { console.error(`\n${fallos} fallo(s)`); process.exit(1); }
console.log("\nAvisos OK");
