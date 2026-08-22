/**
 * ACORDEÓN GLOBAL — abrir uno cierra el que estaba abierto.
 *
 * Petición del dueño: "en todos los desplegables, si hay uno abierto y abres
 * otro, que se cierre el anterior, para que no se quede sucia la página".
 *
 * La agrupación es EXPLÍCITA, nunca deducida de la forma del DOM. Un primer
 * intento la infería ("si el desplegable es el único de su contenedor, el
 * grupo es el contenedor") y salía impredecible: con dos revisiones abrir una
 * cerraba solo a las otras, pero con UNA sola cerraba también la tabla de
 * registros de al lado. La misma acción hacía cosas distintas según cuántos
 * datos tuviera el cliente.
 *
 * Reglas, por orden:
 *  1. `data-acordeon="grupo"` → exclusivo con todo lo que lleve ese mismo
 *     grupo, esté donde esté. Es lo que hay que usar cuando cada elemento va
 *     envuelto en su propio <li> o <div>.
 *  2. `<details name="…">` → el navegador ya lo hace exclusivo por su cuenta;
 *     aquí no se toca.
 *  3. Sin nada declarado → exclusivo solo con sus HERMANOS DIRECTOS. Sin
 *     promociones al contenedor de arriba.
 *
 * `libre()` deja fuera a un desplegable (y a todo lo que contenga): ni cierra
 * ni se cierra. Es para superficies de TRABAJO, no de consulta — una tarjeta
 * con un editor abierto o una descarga en curso no puede plegarse porque
 * alguien abra otra cosa.
 *
 * Los desplegables de ESTADO (MemoDetails) se cierran con un evento
 * `acordeon:cerrar`, no pulsando su botón: pulsarlo persistía en localStorage
 * una decisión que el coach no había tomado.
 */

const NO_EXCLUSIVO = "data-acordeon-libre";
const GRUPO = "data-acordeon";
export const EVENTO_CERRAR = "acordeon:cerrar";
/** Lo pide el ancla al llegar: hay que ABRIR este bloque para poder marcar lo
 *  que lleva dentro. Aquí sí es una decisión del coach (pulsó el aviso), así
 *  que el desplegable puede recordarla. */
export const EVENTO_ABRIR = "acordeon:abrir";

/** Marca un desplegable (o un contenedor entero) como NO exclusivo. */
export function libre(): Record<string, string> {
  return { [NO_EXCLUSIVO]: "true" };
}

/** Declara el grupo de un desplegable: todos los del mismo grupo son
 *  mutuamente excluyentes aunque no sean hermanos en el DOM. */
export function grupo(nombre: string): Record<string, string> {
  return { [GRUPO]: nombre };
}

function exento(el: Element | null): boolean {
  return !!el?.closest(`[${NO_EXCLUSIVO}]`);
}

function esDesplegable(el: Element): boolean {
  return el instanceof HTMLDetailsElement || el.hasAttribute("data-open");
}

/** Cierra un desplegable respetando su naturaleza. */
function cerrar(el: Element): void {
  if (exento(el)) return;
  if (el instanceof HTMLDetailsElement) {
    if (el.open) el.open = false;
    return;
  }
  if (el.getAttribute("data-open") === "true") {
    // Evento, NO clic en su botón: el clic hacía que el componente guardara
    // "cerrado" en localStorage como si lo hubiera decidido el coach.
    el.dispatchEvent(new CustomEvent(EVENTO_CERRAR, { bubbles: false }));
  }
}

function companeros(el: Element): Element[] {
  const nombreGrupo = el.getAttribute(GRUPO);
  if (nombreGrupo) {
    return Array.from(document.querySelectorAll(`[${GRUPO}="${CSS.escape(nombreGrupo)}"]`))
      .filter((h) => h !== el);
  }
  // Sin grupo declarado: solo los hermanos directos, y solo los que tampoco
  // declaran grupo (si lo declaran, mandan sus compañeros de grupo).
  const padre = el.parentElement;
  if (!padre) return [];
  return Array.from(padre.children)
    .filter((h) => h !== el && esDesplegable(h) && !h.hasAttribute(GRUPO));
}

function cerrarCompaneros(el: Element): void {
  if (exento(el)) return;
  for (const h of companeros(el)) cerrar(h);
}

let activo = false;

/** Se llama una vez por aplicación (panel y portal). Devuelve el limpiador. */
export function activarAcordeon(): () => void {
  if (activo) return () => {};
  activo = true;

  // `toggle` NO burbujea: hay que escuchar en fase de captura.
  const alAlternar = (e: Event) => {
    const el = e.target;
    if (el instanceof HTMLDetailsElement && el.open) cerrarCompaneros(el);
  };
  document.addEventListener("toggle", alAlternar, true);

  // Desplegables de estado: se detecta que uno pasa a abierto.
  const obs = new MutationObserver((cambios) => {
    for (const c of cambios) {
      const el = c.target;
      if (el instanceof HTMLElement && el.getAttribute("data-open") === "true") {
        cerrarCompaneros(el);
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
