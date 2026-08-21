/**
 * ANCLAS — "llévame al sitio exacto y márcamelo".
 *
 * Un ancla es una cadena estable que identifica UN punto de arreglo dentro de
 * la ficha de un cliente. La pone el backend en el aviso (`target`) y la lleva
 * el elemento en el DOM (`data-ancla`). Gramática:
 *
 *   nutricion.macros                → el bloque de kcal/macros
 *   nutricion.comida.2              → la toma con slot 2
 *   nutricion.suplementos           → la caja de suplementación
 *   entreno.sesion.3                → la sesión 3
 *   entreno.ejercicio.12            → el ejercicio con exercise_id 12
 *   anamnesis.campo.food_allergies  → el campo de alergias de la ficha
 *   plan.generar                    → el botón de generar/regenerar
 *
 * Reglas:
 * - El ancla NO es un selector CSS: se busca por atributo, así que puede llevar
 *   puntos sin escapar.
 * - Un ancla que no existe no rompe nada: se busca durante unos segundos (los
 *   datos llegan por red) y, si no aparece, se abandona en silencio.
 * - Antes de marcar se ABREN los <details> que envuelvan al objetivo: de nada
 *   sirve marcar algo que está plegado.
 */

/** Atributo que hay que poner en el elemento marcable. */
export const ATRIBUTO = "data-ancla";

/** Props listas para el JSX: `<div {...ancla("nutricion.comida.2")}>` */
export function ancla(nombre: string): Record<string, string> {
  return { [ATRIBUTO]: nombre };
}

export function buscarAncla(nombre: string): HTMLElement | null {
  if (!nombre) return null;
  const escapado = (window.CSS && CSS.escape) ? CSS.escape(nombre) : nombre.replace(/"/g, '\\"');
  return document.querySelector<HTMLElement>(`[${ATRIBUTO}="${escapado}"]`);
}

/**
 * Abre todo lo que envuelve al elemento: `<details>` nativos y también los
 * desplegables de estado (MemoDetails y compañía, que se delatan con
 * `data-open` y llevan su botón marcado). Sin esto, marcar algo que vive
 * dentro de un bloque plegado no serviría de nada.
 */
export function abrirContenedores(el: HTMLElement): void {
  let nodo: HTMLElement | null = el;
  while (nodo) {
    if (nodo instanceof HTMLDetailsElement) {
      if (!nodo.open) nodo.open = true;
    } else if (nodo.getAttribute("data-open") === "false") {
      // Se pulsa SU toggle: es quien conoce el estado de React.
      nodo.querySelector<HTMLElement>("[data-desplegable-toggle]")?.click();
    }
    nodo = nodo.parentElement;
  }
}

/**
 * Busca el ancla durante `msMax` (los datos llegan por red y el elemento puede
 * tardar en existir) y resuelve con el elemento o con null.
 */
export function esperarAncla(nombre: string, msMax = 6000): Promise<HTMLElement | null> {
  return new Promise((resolve) => {
    const yaEsta = buscarAncla(nombre);
    if (yaEsta) { resolve(yaEsta); return; }
    const limite = Date.now() + msMax;
    const obs = new MutationObserver(() => {
      const el = buscarAncla(nombre);
      if (el) { fin(el); return; }
      if (Date.now() > limite) fin(null);
    });
    const reloj = window.setInterval(() => {
      const el = buscarAncla(nombre);
      if (el || Date.now() > limite) fin(el);
    }, 250);
    function fin(el: HTMLElement | null) {
      obs.disconnect();
      window.clearInterval(reloj);
      resolve(el);
    }
    obs.observe(document.body, { childList: true, subtree: true });
  });
}

/**
 * Lleva al elemento y lo deja MARCADO. Devuelve una función para quitar la
 * marca. La marca no caduca sola: se quita cuando el problema se resuelve (el
 * pin desaparece) o cuando el coach la cierra — si parpadeara y se fuera, el
 * coach que mira otra pestaña un momento vuelve y ya no sabe dónde era.
 */
export async function irYMarcar(nombre: string, msMax = 6000): Promise<HTMLElement | null> {
  const el = await esperarAncla(nombre, msMax);
  if (!el) return null;
  abrirContenedores(el);
  // Un frame para que el <details> recién abierto ya tenga altura y el scroll
  // caiga donde toca (si no, centra sobre la posición plegada).
  await new Promise((r) => requestAnimationFrame(() => r(null)));
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("ancla-hit");
  return el;
}

export function desmarcar(nombre: string): void {
  const el = buscarAncla(nombre);
  el?.classList.remove("ancla-hit");
}

export function desmarcarTodo(): void {
  document.querySelectorAll<HTMLElement>(".ancla-hit")
    .forEach((el) => el.classList.remove("ancla-hit"));
}

/** Enlace del panel a un punto exacto: /clientes/7?tab=planificacion&ir=… */
export function hrefCliente(clientId: number, tab: string, target?: string): string {
  const q = new URLSearchParams({ tab });
  if (target) q.set("ir", target);
  return `/clientes/${clientId}?${q.toString()}`;
}
