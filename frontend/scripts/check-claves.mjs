/** Comprobación de las CLAVES DE ALMACENAMIENTO DEL PORTAL.
 *
 *  El portal se usa desde móviles que a veces son compartidos (una pareja, el
 *  móvil de casa) y no tiene login: se entra por un enlace con token. Cualquier
 *  cosa que se guarde en `localStorage`/`sessionStorage` sin el token en la
 *  clave es un borrador de un cliente que puede acabar en la ficha de otro —
 *  datos de salud escritos en la persona equivocada.
 *
 *  Ya pasó: la pantalla de cierre lo hacía bien (`DRAFT_KEY(token, …)`) y la
 *  del diario usaba una clave fija. Este guardián existe para que no vuelva a
 *  colarse en una pantalla nueva.
 *
 *  Uso: npm run check:claves
 */
import { strict as assert } from "node:assert";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const DIR = new URL("../src/portal/", import.meta.url).pathname;

/* Claves que NO son de un cliente concreto y por eso no llevan token. Cada
   excepción se justifica aquí: si añades una, explica por qué es global. */
const GLOBALES = new Set([
  // Estado de la propia app, igual para cualquiera que la abra en ese móvil.
  "portal_welcome_done",
  "portal_push_dismissed",
]);

const ficheros = readdirSync(DIR).filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"));
assert.ok(ficheros.length > 0, "no se encontró ningún fichero del portal");

const fallos = [];
for (const nombre of ficheros) {
  const src = readFileSync(join(DIR, nombre), "utf8");
  // Cada uso de storage con una clave que se pueda leer estáticamente.
  const usos = [
    ...src.matchAll(/(?:sessionStorage|localStorage)\.(?:getItem|setItem|removeItem)\(\s*("([^"]+)"|`([^`]*)`)/g),
  ];
  for (const m of usos) {
    const literal = m[2] ?? m[3] ?? "";
    if (!literal) continue;                      // clave calculada: se mira abajo
    if (GLOBALES.has(literal)) continue;
    if (/\$\{/.test(literal)) continue;          // plantilla: lleva algo dentro
    fallos.push(`${nombre}: clave fija «${literal}» sin token`);
  }
  // Y las constantes de clave: o son función (llevan argumento) o son globales.
  for (const m of src.matchAll(/^const (K_[A-Z_]+|[A-Z_]*DRAFT_KEY[A-Z_]*)\s*=\s*(.)/gm)) {
    const [, nombreConst, primerChar] = m;
    if (primerChar === '"' || primerChar === "`") {
      fallos.push(`${nombre}: la constante ${nombreConst} es una clave FIJA; ` +
                  "hazla función del token, como DRAFT_KEY en PortalClose");
    }
  }
}

assert.deepEqual(fallos, [],
  "Claves de almacenamiento del portal sin token (en un móvil compartido, el " +
  "borrador de un cliente acaba en la ficha de otro):\n  " + fallos.join("\n  "));

console.log("✓ toda clave del portal lleva el token del cliente");
console.log(`\nClaves OK · ${ficheros.length} ficheros del portal revisados`);
