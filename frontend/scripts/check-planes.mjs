/** LOS DOS CAMINOS DEL PLAN, PARA CUALQUIER CLIENTE.
 *
 *  El dueño: «que el hecho de hacer con o sin IA los planes se pueda aplicar a
 *  todos los clientes en función de su nivel, no solo avanzados».
 *
 *  Lo que pasaba: el MISMO botón hacía una cosa u otra según `client.level`, y
 *  sin decirlo. A un cliente "avanzado" se le preparaba la base a mano (0
 *  créditos, borrador) y a los demás se les generaba el plan entero con IA y se
 *  les PUBLICABA — con la misma pulsación y sin preguntar. El nivel del cliente
 *  describe a quién entrena, no cómo trabaja el coach: puede RECOMENDAR un
 *  camino, nunca elegirlo por él.
 *
 *  Esta guarda vigila justo eso: que en el panel de planificación el nivel solo
 *  se use para recomendar. Cualquier otro uso —decidir qué endpoint se llama,
 *  qué botón se pinta, si se confirma o no— vuelve a esconderle al coach lo que
 *  va a pasar cuando pulse.
 *
 *  Uso: npm run check:planes
 */
import { readFileSync } from "node:fs";
import { strict as assert } from "node:assert";

const F = "src/components/ClientPlanPanel.tsx";
const fuente = readFileSync(F, "utf8");
const ok = [];
const t = (nombre, fn) => { fn(); ok.push(nombre); };

/** Líneas que miran el nivel del cliente, sin comentarios. */
const usos = fuente.split("\n")
  .map((l, i) => ({ n: i + 1, l }))
  .filter(({ l }) => !/^\s*(\/\/|\*|\/\*)/.test(l))
  .filter(({ l }) => /client\.level/.test(l));

t("el nivel del cliente solo RECOMIENDA, no decide", () => {
  const malos = usos.filter(({ l }) => !/\brecomendado\b/.test(l));
  assert.deepEqual(malos.map(({ n, l }) => `${F}:${n} ${l.trim().slice(0, 84)}`), [],
    "el nivel vuelve a decidir por el coach en vez de recomendarle un camino");
});

t("los cuatro caminos se ofrecen siempre, en el mismo orden", () => {
  assert.ok(/\["ia", "mano", "copiar", "documento"\] as const\)\.map/.test(fuente),
    "el orden de los caminos volvió a depender de algo: se ofrecen los cuatro igual a todos");
});

t("rehacer el plan con otras comidas pregunta por dónde", () => {
  // `onRegenerate(keys, conIa)`: el que llama elige, no lo deduce el panel.
  assert.ok(/onRegenerate: \(keys: string\[\], conIa: boolean\) => void/.test(fuente),
    "«Regenerar con estas comidas» volvió a decidir solo si gasta créditos");
  assert.ok(/Rehacer a mano · 0 créditos/.test(fuente),
    "desapareció el camino sin IA de la estructura de comidas");
});

t("cambiar de objetivo también deja elegir", () => {
  assert.ok(/changeAndRegenerate\(conIa: boolean\)/.test(fuente),
    "el cambio de objetivo volvió a elegir el camino por su cuenta");
  assert.ok(/Confirmar y generar con IA/.test(fuente)
    && /Confirmar y prepararla a mano/.test(fuente),
    "faltan los dos botones del cambio de objetivo");
});

t("generar con IA se confirma SIEMPRE", () => {
  // Gasta créditos y publica el plan: es el mismo gasto y el mismo envío para
  // cualquier cliente, así que preguntar solo a unos era arbitrario.
  const i = fuente.indexOf("async function generate(");
  const cuerpo = fuente.slice(i, i + 900);
  assert.ok(/window\.confirm\(/.test(cuerpo) && !/client\.level/.test(cuerpo),
    "la confirmación de «Generar con IA» volvió a depender del nivel del cliente");
});

for (const n of ok) console.log(`✓ ${n}`);
console.log(`\nPlanes OK · ${ok.length} comprobaciones`);
