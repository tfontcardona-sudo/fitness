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

/** Todas las etiquetas <button …> y <Link …className="btn…"> del código.
 *
 *  ⚠️ Esto buscaba la etiqueta con `<button[^>]*>`, y el `>` de la PRIMERA
 *  flecha (`onClick={() => …}`) la cortaba ahí mismo: el `className` se
 *  quedaba fuera y el guardián daba por bueno cualquier botón que tuviera un
 *  manejador antes de su clase — o sea, casi todos. Se falsificó y no lo cazó.
 *  Ahora la etiqueta se cierra contando LLAVES: el `>` que cuenta es el que
 *  está fuera de `{…}` y fuera de comillas.
 */
function controles(fuente) {
  const out = [];
  const re = /<(?:button|Link|a)\b/g;
  let m;
  while ((m = re.exec(fuente)) !== null) {
    let i = m.index + m[0].length, llaves = 0, comilla = null;
    for (; i < fuente.length; i++) {
      const c = fuente[i];
      if (comilla) { if (c === comilla) comilla = null; continue; }
      if (c === '"' || c === "'" || c === "`") { comilla = c; continue; }
      if (c === "{") llaves++;
      else if (c === "}") llaves--;
      else if (c === ">" && llaves === 0) break;
    }
    const tag = fuente.slice(m.index, i + 1);
    if (/className="[^"]*\bbtn\b/.test(tag) || tag.startsWith("<button")) out.push(tag);
  }
  return out;
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

t("todo botón lleva una clase de botón que EXISTE", () => {
  // El fallo que motivó esta comprobación: tres botones del panel —el del
  // SWITCH DE MARCA entre ellos— llevaban `btn-secondary`, una clase que no
  // estaba definida en ninguna parte. No dan error, no rompen el build y no
  // salen en ninguna prueba: simplemente se pintan como un botón gris del
  // navegador, sin color de marca, sin borde y sin altura de dedo. Es la forma
  // más silenciosa que hay de tener un botón mal marcado.
  const css = readFileSync("src/index.css", "utf8");
  const definidas = new Set(
    [...css.matchAll(/\.(btn-[a-z0-9-]+)\s*[,{:]/g)].map((m) => m[1]));
  const malos = [];
  for (const f of FICHEROS) {
    const fuente = readFileSync(f, "utf8");
    for (const tag of controles(fuente)) {
      const clases = /className="([^"]*)"/.exec(tag)?.[1] ?? "";
      for (const c of clases.split(/\s+/)) {
        if (/^btn-/.test(c) && !definidas.has(c)) {
          malos.push(`${f}: «${c}» no existe en index.css`);
        }
      }
    }
  }
  assert.deepEqual([...new Set(malos)], [],
    `clases de botón inventadas (el botón sale sin estilo):\n  ${[...new Set(malos)].join("\n  ")}`);
});

for (const n of ok) console.log(`✓ ${n}`);
console.log(`\nBotones OK · ${ok.length} comprobaciones`);
