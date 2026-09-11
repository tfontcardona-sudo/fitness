/** LA MARCA NO SE ESCRIBE A MANO.
 *
 *  El sistema lleva dos negocios con la misma maquinaria. Cuando la identidad
 *  de uno se escribe dentro de una pantalla —el logo, el naranja de DQ, el
 *  fondo crema— el OTRO negocio la hereda, y nadie se entera hasta que un
 *  cliente abre su portal y ve la marca de una asesoría con la que no ha
 *  contratado nada. Es exactamente lo que pasaba: NUEVE pantallas con
 *  `/dq-logo.png` escrito a mano y una paleta clavada debajo del switch.
 *
 *  Las dos puertas:
 *  · el logo — `components/MarcaLogo.tsx` (que pregunta por la marca y, si no
 *    tiene fichero, pinta SU rótulo, nunca el de la otra);
 *  · el color — las variables de la piel (`var(--brand-accent)`, `--pf-oro`,
 *    `--surface`…), que cambian enteras con `data-piel`.
 *
 *  Qué NO vigila, a propósito: las páginas propias de una marca (el
 *  cuestionario de DQR y el de Professional son dos pantallas distintas por
 *  decisión del dueño, cada una con su paleta dentro) y los colores de
 *  SIGNIFICADO (rojo de error, verde de bien), que son iguales en los dos
 *  negocios. Van en `EXENTOS`, con su motivo.
 *
 *  Uso: npm run check:marca
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const RAIZ = "src";

/** Ficheros que pueden llevar una identidad escrita dentro, y por qué. */
const EXENTOS = new Map([
  ["src/components/MarcaLogo.tsx", "es LA puerta del logo"],
  ["src/lib/marca.ts", "es LA puerta de la piel y los colores por papel"],
  ["src/pages/AnamnesisPage.tsx", "el cuestionario de DQR es una pantalla suya"],
  ["src/pages/AnamnesisProfesional.tsx", "el cuestionario del centro es una pantalla suya"],
  ["src/pages/AnamnesisRouter.tsx", "solo elige entre los dos cuestionarios"],
  ["src/components/ErrorBoundary.tsx", "envuelve a BrandProvider: no puede usar el hook"],
]);

/** El naranja y el azul de DQ, y su crema. Escritos en cualquier variante. */
const COLORES_DE_DQ = [
  /#e8833a/i, /#f2a25f/i, /#c86a24/i, /#d96f2e/i, /#f6a560/i,   // naranja
  /#2e5e8c/i, /#3f77aa/i, /#234b72/i,               // azul
  /#f4eee3/i, /#f6f1e7/i, /#fffdf9/i,               // crema
  /rgba\(\s*232\s*,\s*131\s*,\s*58/i,
  /rgba\(\s*46\s*,\s*94\s*,\s*140/i,
];

function ficheros(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? ficheros(p) : /\.(ts|tsx)$/.test(p) ? [p] : [];
  });
}

const lineasDe = (f) =>
  readFileSync(f, "utf8").split("\n")
    .map((l, i) => ({ f: f.replace(/\\/g, "/"), n: i + 1, l }))
    // Un comentario que EXPLICA por qué existe la guarda no la incumple.
    .filter(({ l }) => !/^\s*(\/\/|\*|\/\*)/.test(l));

const todos = ficheros(RAIZ).filter((f) => !EXENTOS.has(f.replace(/\\/g, "/")));
const fallos = [];

// 1) Ninguna pantalla escribe el logo de una marca.
for (const f of todos) {
  for (const { n, l } of lineasDe(f)) {
    if (/["'`]\/[a-z0-9-]*logo[a-z0-9-]*\.(png|svg|jpg|webp)["'`]/i.test(l)) {
      fallos.push(`${f}:${n} · logo escrito a mano — usa <MarcaLogo>`);
    }
  }
}

// 2) Ninguna pantalla escribe la paleta de DQ.
for (const f of todos) {
  for (const { n, l } of lineasDe(f)) {
    if (COLORES_DE_DQ.some((re) => re.test(l))) {
      fallos.push(`${f}:${n} · color de DQ escrito a mano — usa las variables de la piel`);
    }
  }
}

// 3) La piel se aplica por LA puerta: nadie escribe `data-piel` por su cuenta,
//    o dos pantallas podrían decir pieles distintas en la misma carga.
for (const f of todos) {
  for (const { n, l } of lineasDe(f)) {
    if (/dataset\s*\.\s*piel|setAttribute\(\s*["']data-piel/.test(l)) {
      fallos.push(`${f}:${n} · aplica la piel a mano — usa aplicarPiel() de lib/marca`);
    }
  }
}

// 4) Y las dos pieles existen de verdad en el CSS: un `data-piel` sin reglas
//    detrás deja la pantalla con la paleta de la otra marca y sin avisar.
const css = readFileSync("src/index.css", "utf8");
for (const piel of ["professional"]) {
  const reglas = (css.match(new RegExp(`\\[data-piel="${piel}"\\]`, "g")) || []).length;
  if (reglas < 20) {
    fallos.push(`src/index.css · la piel "${piel}" solo tiene ${reglas} reglas: `
      + "no alcanza para cubrir panel y portal");
  }
}

// 5) La rampa de tinta heredada (text-zinc-*) está remapeada en LAS DOS pieles.
//    En la clara va a tinta oscura; si la oscura no la reescribe, ~640 sitios
//    del panel se quedan en negro sobre negro.
const sinComentarios = css.replace(/\/\*[\s\S]*?\*\//g, "");
for (const clase of ["text-zinc-100", "text-zinc-300", "text-zinc-400", "text-zinc-500"]) {
  const claro = new RegExp(`(^|[^\\]])\\.${clase.replace(/-/g, "-")}\\b`, "m").test(sinComentarios);
  const oscuro = new RegExp(`\\[data-piel="professional"\\][^{]*\\.${clase}\\b`)
    .test(sinComentarios);
  if (claro && !oscuro) {
    fallos.push(`src/index.css · .${clase} se remapea para la piel clara y no para la negra`);
  }
}

if (fallos.length) {
  console.error("✗ La marca escrita a mano se le aparece al OTRO negocio:\n");
  for (const f of fallos) console.error("  " + f);
  console.error(`\n${fallos.length} incumplimiento(s).`);
  process.exit(1);
}
console.log("✓ ninguna pantalla escribe el logo ni la paleta de una marca");
console.log("✓ la piel se aplica por una sola puerta y existe en el CSS");
console.log(`\nMarca OK · ${todos.length} ficheros revisados`);
