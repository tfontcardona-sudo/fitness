/** Una sola puerta al portapapeles.
 *
 *  `navigator.clipboard` NO existe fuera de contexto seguro (el coach entrando
 *  por la IP de la red local desde la tablet, el navegador embebido de
 *  Instagram en la página pública de enlaces) y puede fallar por permisos.
 *  El patrón que se repetía por toda la web era `writeText(x)` a pelo —o con
 *  un `.catch(() => {})`— seguido de un "Copiado ✓" incondicional: el coach se
 *  iba convencido de llevar el enlace del cliente y pegaba lo que hubiera
 *  antes en el portapapeles.
 *
 *  `src/lib/clipboard.ts` ya resuelve esto (moderno → clásico → decir la
 *  verdad). Esta guarda obliga a pasar por ahí.
 *
 *  Uso: npm run check:portapapeles
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const RAIZ = "src";
const PUERTA = "src/lib/clipboard.ts";

function ficheros(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? ficheros(p) : /\.(ts|tsx)$/.test(p) ? [p] : [];
  });
}

const culpables = ficheros(RAIZ)
  .filter((f) => f.replace(/\\/g, "/") !== PUERTA)
  .flatMap((f) => {
    const lineas = readFileSync(f, "utf8").split("\n");
    return lineas
      .map((l, i) => ({ f, n: i + 1, l }))
      // Los comentarios explican POR QUÉ existe esta guarda: nombrarla no es
      // usarla.
      .filter(({ l }) => !/^\s*(\/\/|\*|\/\*)/.test(l))
      .filter(({ l }) => /navigator\s*\.\s*clipboard/.test(l));
  });

if (culpables.length) {
  console.error(
    "\n✗ Portapapeles a pelo. Usa `copiar` / `copiarConAviso` de src/lib/clipboard.ts:\n" +
    "  (un «Copiado» que no comprueba el resultado hace pegar al coach lo que hubiera antes)\n",
  );
  for (const c of culpables) console.error(`  ${c.f}:${c.n}  ${c.l.trim()}`);
  process.exit(1);
}

console.log(`\n✓ una sola puerta al portapapeles · ${ficheros(RAIZ).length} ficheros revisados`);
