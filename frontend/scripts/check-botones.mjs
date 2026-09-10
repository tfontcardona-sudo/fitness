/** BOTONES QUE CABEN — «que no haya palabras recortadas, no haya palabras a
 *  medias, y que quepan bien las palabras en los botones».
 *
 *  La comprobación de verdad se hizo en un navegador real (360 px y
 *  escritorio, panel + portal + páginas públicas + modales + editor): cero
 *  recortes. Lo que vive aquí es lo que evita que VUELVA, que es lo que se
 *  puede correr en cada cambio sin levantar medio sistema:
 *
 *   1. la regla global que lo garantiza sigue en su sitio;
 *   2. ningún botón recorta su propia etiqueta con puntos suspensivos;
 *   3. ningún botón fija un ancho y encima prohíbe que el texto salte de línea
 *      (la receta exacta del texto cortado).
 *
 *  Uso: npm run check:botones
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { strict as assert } from "node:assert";

function listar(dir) {
  const out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out.push(...listar(p));
    else if (p.endsWith(".tsx")) out.push(p);
  }
  return out;
}

const ok = [];
const t = (nombre, fn) => { fn(); ok.push(nombre); };

t("la regla que hace que quepan sigue puesta", () => {
  const css = readFileSync("src/index.css", "utf8");
  const i = css.indexOf("BOTONES QUE CABEN");
  assert.ok(i > 0, "desapareció el bloque de botones de index.css");
  // SIN los comentarios: el bloque se explica a sí mismo y nombra sus propias
  // reglas en prosa, así que buscarlas en crudo daba por buena una regla
  // BORRADA cuyo comentario seguía ahí (este mismo guardián se lo tragó).
  const bloque = css.slice(i, i + 2600).replace(/\/\*[\s\S]*?\*\//g, "");
  for (const regla of ["min-width: max-content;", "word-break: keep-all;",
                       "hyphens: none;", "flex-shrink: 0;"]) {
    assert.ok(bloque.includes(regla), `falta «${regla}»: los botones vuelven a poder recortarse`);
  }
  // Y la excepción: un botón a ancho completo NO debe ensanchar su fila.
  assert.ok(/\.btn\.w-full[^{]*\{[^}]*min-width:\s*0/.test(css),
    "sin la excepción de w-full, un botón de ancho completo desborda su fila");
});

const FICHEROS = listar("src");
/** Todas las etiquetas <button …> y <Link …className="btn…"> del código. */
function controles(fuente) {
  return [...fuente.matchAll(/<(?:button|Link|a)\b[^>]*>/gs)]
    .map((m) => m[0])
    .filter((tag) => /className="[^"]*\bbtn\b/.test(tag) || tag.startsWith("<button"));
}

t("ningún botón recorta su etiqueta con puntos suspensivos", () => {
  const malos = [];
  for (const f of FICHEROS) {
    const fuente = readFileSync(f, "utf8");
    for (const tag of controles(fuente)) {
      // `line-clamp-N` en una TARJETA con imagen es otra cosa (un título de dos
      // líneas, no una etiqueta de acción): solo se persigue el recorte en una
      // línea, que es el que parte palabras.
      if (/\btruncate\b|\btext-ellipsis\b/.test(tag)) {
        malos.push(`${f}: ${tag.replace(/\s+/g, " ").slice(0, 90)}`);
      }
    }
  }
  assert.deepEqual(malos, [],
    `estos botones cortan su texto con puntos suspensivos:\n  ${malos.join("\n  ")}`);
});

t("ningún botón fija ancho y a la vez prohíbe saltar de línea", () => {
  const malos = [];
  for (const f of FICHEROS) {
    const fuente = readFileSync(f, "utf8");
    for (const tag of controles(fuente)) {
      const anchoFijo = /\bw-(?:8|10|12|14|16|20|24|28|32|36|40|44|48)\b/.test(tag);
      if (anchoFijo && /\bwhitespace-nowrap\b/.test(tag)) {
        malos.push(`${f}: ${tag.replace(/\s+/g, " ").slice(0, 90)}`);
      }
    }
  }
  assert.deepEqual(malos, [],
    `ancho fijo + texto que no puede saltar de línea = texto cortado:\n  ${malos.join("\n  ")}`);
});

for (const n of ok) console.log(`✓ ${n}`);
console.log(`\nBotones OK · ${ok.length} comprobaciones`);
