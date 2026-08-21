/**
 * ACORDEÓN GLOBAL — abrir uno cierra el hermano que estuviera abierto.
 *
 * Petición del dueño: "en todos los desplegables y combinaciones posibles, si
 * hay uno abierto y abres otro, que se cierre el anterior, para que no se
 * quede muy sucia la página".
 *
 * Se resuelve UNA vez en el DOM en lugar de desplegable por desplegable:
 * - `<details>` nativos: al abrirse uno, se cierran sus HERMANOS directos.
 *   (El atributo `name` de HTML hace esto solo en navegadores recientes; esto
 *   funciona en todos y además agrupa por contenedor, sin tener que bautizar
 *   cada grupo a mano.)
 * - Desplegables de estado (MemoDetails y compañía): se marcan con
 *   `data-open` y un botón `[data-desplegable-toggle]`; al abrirse uno, se
 *   pulsa el toggle de los hermanos abiertos para cerrarlos.
 *
 * Hermano = mismo elemento padre. Un desplegable ANIDADO dentro de otro no es
 * hermano, así que abrirlo no cierra al que lo contiene (si no, sería
 * imposible usarlos).
 */

const NO_EXCLUSIVO = "data-acordeon-libre";

/** Marca un desplegable (o un contenedor entero) como NO exclusivo: se queda
 *  abierto aunque se abra un hermano. Para las pocas listas donde comparar dos
 *  cosas a la vez es justo lo que se quiere. */
export function libre(): Record<string, string> {
  return { [NO_EXCLUSIVO]: "true" };
}

function exento(el: Element | null): boolean {
  return !!el?.closest(`[${NO_EXCLUSIVO}]`);
}

function hermanos(el: Element): Element[] {
  const padre = el.parentElement;
  if (!padre) return [];
  return Array.from(padre.children).filter((h) => h !== el);
}

function cerrarHermanos(el: Element): void {
  if (exento(el)) return;
  for (const h of hermanos(el)) {
    if (exento(h)) continue;
    if (h instanceof HTMLDetailsElement) {
      if (h.open) h.open = false;
      continue;
    }
    // Desplegable de estado ya abierto: se cierra pulsando SU toggle, que es
    // quien conoce su estado de React (tocarle el DOM a mano no serviría).
    if (h.getAttribute("data-open") === "true") {
      const toggle = h.querySelector<HTMLElement>("[data-desplegable-toggle]");
      if (toggle && !exento(toggle)) toggle.click();
    }
  }
}

let activo = false;

/** Se llama una vez por aplicación (panel y portal). Devuelve el limpiador. */
export function activarAcordeon(): () => void {
  if (activo) return () => {};
  activo = true;

  // `toggle` NO burbujea: hay que escuchar en fase de captura.
  const alAlternar = (e: Event) => {
    const el = e.target;
    if (el instanceof HTMLDetailsElement && el.open) cerrarHermanos(el);
  };
  document.addEventListener("toggle", alAlternar, true);

  // Desplegables de estado: se detecta que uno pasa a abierto.
  const obs = new MutationObserver((cambios) => {
    for (const c of cambios) {
      const el = c.target;
      if (el instanceof HTMLElement && el.getAttribute("data-open") === "true") {
        cerrarHermanos(el);
      }
    }
  });
  obs.observe(document.body, {
    subtree: true, attributes: true, attributeFilter: ["data-open"],
  });

  return () => {
    document.removeEventListener("toggle", alAlternar, true);
    obs.disconnect();
    activo = false;
  };
}
