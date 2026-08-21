/** Comprobación de los RECORDATORIOS ANCLADOS y del ACORDEÓN global.
 *
 *  Lo que se verifica aquí es justo lo que el dueño pidió y lo que más fácil
 *  se rompe sin que nadie se entere: que un recordatorio se borre SOLO cuando
 *  el problema se resuelve, que no se borre por un fallo de red, y que abrir
 *  un desplegable cierre a su hermano (y no a su padre).
 *
 *  Uso: npm run check:anclas
 */
import { build } from "esbuild";
import { strict as assert } from "node:assert";

/* --------------------------------------------------------- entorno falso --- */
// Un localStorage de mentira ANTES de cargar el módulo (lee al importarse).
const almacen = new Map();
globalThis.localStorage = {
  getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)),
  removeItem: (k) => almacen.delete(k),
};

async function cargar(entrada) {
  const { outputFiles } = await build({
    entryPoints: [entrada], bundle: true, write: false, format: "esm", logLevel: "error",
  });
  return import("data:text/javascript;base64," +
    Buffer.from(outputFiles[0].text).toString("base64"));
}

const pins = await cargar("src/lib/pins.ts");
const anchors = await cargar("src/lib/anchors.ts");

const ok = [];
const t = (nombre, fn) => { fn(); ok.push(nombre); };

/* ------------------------------------------------------------------ pins --- */

const base = {
  scope: "alerts", clientId: 7, clientName: "Carla",
  label: "Corregir planificación", href: "/clientes/7?tab=planificacion",
  severity: "alta",
};

t("anclar dos veces el mismo problema no lo duplica", () => {
  pins.pin({ ...base, id: pins.pinId("alerts", "7:x:y"), key: "7:x:y" });
  pins.pin({ ...base, id: pins.pinId("alerts", "7:x:y"), key: "7:x:y", label: "Otro texto" });
  const míos = pins.getPins().filter((p) => p.key === "7:x:y");
  assert.equal(míos.length, 1, "se duplicó el recordatorio");
  assert.equal(míos[0].label, "Otro texto", "no se refrescó el texto");
});

t("el recordatorio se borra SOLO cuando el problema desaparece", () => {
  pins.pin({ ...base, id: pins.pinId("alerts", "7:a"), key: "7:a" });
  pins.pin({ ...base, id: pins.pinId("alerts", "7:b"), key: "7:b" });
  // El backend ya solo devuelve el problema b: a está resuelto.
  pins.syncScope("alerts", ["7:b"]);
  const claves = pins.getPins().map((p) => p.key);
  assert.ok(!claves.includes("7:a"), "el resuelto seguía ahí");
  assert.ok(claves.includes("7:b"), "se llevó por delante uno vivo");
});

t("sincronizar un ámbito no toca los de otro", () => {
  pins.pin({ ...base, scope: "plan:7", id: pins.pinId("plan:7", "k1"), key: "k1" });
  pins.syncScope("alerts", []);
  assert.ok(pins.getPins().some((p) => p.key === "k1"),
    "sincronizar 'alerts' borró un recordatorio del plan");
});

t("un ámbito vacío borra TODOS los suyos (todo resuelto)", () => {
  pins.syncScope("plan:7", []);
  assert.ok(!pins.getPins().some((p) => p.scope === "plan:7"));
});

t("quitar a mano funciona y no arrastra a los demás", () => {
  pins.pin({ ...base, id: pins.pinId("alerts", "7:c"), key: "7:c" });
  pins.pin({ ...base, id: pins.pinId("alerts", "7:d"), key: "7:d" });
  pins.unpin(pins.pinId("alerts", "7:c"));
  const claves = pins.getPins().map((p) => p.key);
  assert.ok(!claves.includes("7:c") && claves.includes("7:d"));
});

t("un almacenamiento roto no tumba nada", () => {
  const bueno = globalThis.localStorage.setItem;
  globalThis.localStorage.setItem = () => { throw new Error("cuota llena"); };
  pins.pin({ ...base, id: pins.pinId("alerts", "7:e"), key: "7:e" });
  globalThis.localStorage.setItem = bueno;
  assert.ok(pins.getPins().some((p) => p.key === "7:e"),
    "con el almacenamiento bloqueado el recordatorio debe vivir en memoria");
});

t("los recordatorios de un cliente se pueden aislar", () => {
  pins.pin({ ...base, clientId: 9, clientName: "Mario",
             id: pins.pinId("alerts", "9:z"), key: "9:z" });
  assert.equal(pins.pinsDeCliente(9).length, 1);
  assert.ok(pins.pinsDeCliente(7).every((p) => p.clientId === 7));
});

/* --------------------------------------------------------------- anclas --- */

t("el enlace lleva la pestaña Y el ancla", () => {
  const h = anchors.hrefCliente(7, "planificacion", "nutricion.comida.2");
  assert.ok(h.startsWith("/clientes/7?"));
  const q = new URLSearchParams(h.split("?")[1]);
  assert.equal(q.get("tab"), "planificacion");
  assert.equal(q.get("ir"), "nutricion.comida.2");
});

t("sin ancla el enlace no inventa el parámetro", () => {
  const h = anchors.hrefCliente(7, "feedback");
  assert.ok(!h.includes("ir="), "metió un ancla vacía");
});

t("el ancla se pega como atributo, no como clase", () => {
  const props = anchors.ancla("entreno.sesion.3");
  assert.deepEqual(props, { "data-ancla": "entreno.sesion.3" });
});

/* ----------------------------------------------- acordeón (DOM de mentira) --- */
// Sin jsdom: se prueba la REGLA (quién es hermano de quién) con objetos que
// imitan lo justo del DOM. Es la lógica que puede romperse al tocar el código;
// que el navegador dispare `toggle` no hace falta comprobarlo.

function nodo(tipo, hijos = []) {
  const el = {
    tipo, open: false, attrs: {}, children: hijos, parentElement: null,
    getAttribute: (k) => el.attrs[k] ?? null,
    closest: (sel) => {
      const clave = sel.replace(/[[\]]/g, "");
      let n = el;
      while (n) { if (n.attrs[clave] != null) return n; n = n.parentElement; }
      return null;
    },
  };
  for (const h of hijos) h.parentElement = el;
  return el;
}

// Réplica de la regla de lib/accordion.ts: cerrar los HERMANOS abiertos,
// viendo a través del envoltorio (<li>, <div>) que React pone por elemento.
function miembroDeGrupo(el) {
  const padre = el.parentElement;
  if (!padre || !padre.parentElement) return el;
  const propios = padre.children.filter((c) => c.tipo === "details").length;
  return propios === 1 ? padre : el;
}
function cerrarUno(h) {
  if (h.closest("[data-acordeon-libre]")) return;
  if (h.tipo === "details") { if (h.open) h.open = false; return; }
  for (const d of h.children) if (d.tipo === "details") cerrarUno(d);
}
function cerrarHermanos(el) {
  if (el.closest("[data-acordeon-libre]")) return;
  const yo = miembroDeGrupo(el);
  for (const h of yo.parentElement?.children ?? []) {
    if (h === yo) continue;
    cerrarUno(h);
  }
}

t("abrir un desplegable cierra al hermano abierto", () => {
  const a = nodo("details"), b = nodo("details");
  nodo("div", [a, b]);
  a.open = true; b.open = true;
  cerrarHermanos(b);
  assert.equal(a.open, false, "el hermano debía cerrarse");
  assert.equal(b.open, true, "el que se abre debe quedarse abierto");
});

t("un desplegable ANIDADO no cierra al que lo contiene", () => {
  const dentro = nodo("details");
  const fuera = nodo("details", [dentro]);
  nodo("div", [fuera]);
  fuera.open = true; dentro.open = true;
  cerrarHermanos(dentro);
  assert.equal(fuera.open, true, "cerrar al padre haría imposible usarlo");
});

t("un grupo marcado como libre se queda abierto", () => {
  const a = nodo("details"), b = nodo("details");
  const caja = nodo("div", [a, b]);
  caja.attrs["data-acordeon-libre"] = "true";
  a.open = true; b.open = true;
  cerrarHermanos(b);
  assert.equal(a.open, true, "el grupo libre debe permitir varios abiertos");
});

t("el acordeón ve a través del envoltorio de cada elemento de una lista", () => {
  // Patrón de React: cada aviso va en su <li> con su <details> dentro. Como
  // los hermanos son los <li>, comparando hermano a hermano no se cerraba
  // nada y el bloque de avisos se quedaba con cinco desplegables abiertos.
  const d1 = nodo("details"), d2 = nodo("details");
  const li1 = nodo("li", [d1]), li2 = nodo("li", [d2]);
  nodo("ul", [li1, li2]);
  d1.open = true; d2.open = true;
  cerrarHermanos(d2);
  assert.equal(d1.open, false, "el desplegable del otro elemento debía cerrarse");
  assert.equal(d2.open, true);
});

t("desplegables de padres distintos no se estorban", () => {
  const a = nodo("details"), b = nodo("details");
  nodo("div", [a]); nodo("div", [b]);
  a.open = true; b.open = true;
  cerrarHermanos(b);
  assert.equal(a.open, true, "cerró uno de otra sección");
});

/* -------------------------- el backend y la web hablan del mismo sitio --- */
// Si alguien añade un aviso con destino y olvida poner el `data-ancla` en la
// pantalla, el aviso llevaría a la pestaña y no marcaría nada. Esto lo caza.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

function listar(dir) {
  const out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out.push(...listar(p));
    else if (p.endsWith(".tsx") || p.endsWith(".ts")) out.push(p);
  }
  return out;
}

t("cada destino del backend tiene su ancla en la web", () => {
  const alerts = readFileSync("../backend/app/routers/alerts.py", "utf8");
  const mapa = alerts.slice(alerts.indexOf("_DESTINO: dict"), alerts.indexOf("def _alert("));
  const declarados = [...new Set([...mapa.matchAll(/"([a-z][a-z_.]*\.[a-z_.]+)"/g)].map((m) => m[1]))];
  assert.ok(declarados.length >= 10, `se leyeron muy pocos destinos: ${declarados.length}`);

  const fuente = listar("src").map((f) => readFileSync(f, "utf8")).join("\n");
  const huerfanos = declarados.filter((d) => !fuente.includes(`"${d}"`) && !fuente.includes(`\`${d}\``));
  assert.deepEqual(huerfanos, [],
    `estos avisos dicen a dónde ir pero ahí no hay nada que marcar: ${huerfanos.join(", ")}`);
});

for (const nombre of ok) console.log(`✓ ${nombre}`);
console.log(`\nAnclas OK · ${ok.length} comprobaciones`);
