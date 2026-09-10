/** Una sola fuente de alertas.
 *
 *  `/api/alerts` recorre la CARTERA ENTERA en cada llamada: es de lo más caro
 *  que sirve el backend. Que dos pantallas lo pidan por su cuenta duplica ese
 *  trabajo por el mismo dato, y no se nota mirando ninguna de las dos.
 *
 *  Ya ha pasado DOS veces: primero la campana y el panel de seguimiento
 *  barriendo cada 3 s a la vez (auditoría de rendimiento), y después la campana
 *  y la barra de "lo siguiente" de la ficha. A la tercera, esta guarda.
 *
 *  `src/lib/alertasCompartidas.ts` tiene UN temporizador y UNA petición en
 *  vuelo; los consumidores se suscriben. Esta guarda obliga a pasar por ahí.
 *
 *  Uso: npm run check:alertas
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const RAIZ = "src";
const FUENTE = "src/lib/alertasCompartidas.ts";
// El cliente HTTP declara el método; declararlo no es llamarlo por tu cuenta.
const PERMITIDOS = new Set([FUENTE, "src/lib/api.ts"]);

function ficheros(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? ficheros(p) : /\.(ts|tsx)$/.test(p) ? [p] : [];
  });
}

const culpables = ficheros(RAIZ)
  .filter((f) => !PERMITIDOS.has(f.replace(/\\/g, "/")))
  .flatMap((f) => {
    const lineas = readFileSync(f, "utf8").split("\n");
    return lineas
      .map((l, i) => ({ f, n: i + 1, l }))
      // Los comentarios explican POR QUÉ existe la guarda: nombrarla no es
      // saltársela.
      .filter(({ l }) => !/^\s*(\/\/|\*|\/\*)/.test(l))
      .filter(({ l }) => /\bapi\s*\.\s*listAlerts\s*\(/.test(l));
  });

if (culpables.length) {
  console.error(
    "\n✗ Hay pantallas pidiendo /api/alerts por su cuenta.\n" +
    "  Ese endpoint recorre la cartera entera: dos barridos = el doble de\n" +
    `  trabajo por el mismo dato. Usa \`useAlertas\` de ${FUENTE}.\n`,
  );
  for (const { f, n, l } of culpables) {
    console.error(`  ${f}:${n}  ${l.trim()}`);
  }
  console.error("");
  process.exit(1);
}

console.log(`\n✓ una sola fuente de alertas · ${ficheros(RAIZ).length} ficheros revisados\n`);
