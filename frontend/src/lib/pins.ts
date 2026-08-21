/**
 * RECORDATORIOS ANCLADOS ("pins") — la web se acuerda de lo que ibas a hacer.
 *
 * Idea del dueño: un aviso dice "la dieta de Carla lleva legumbres y no las
 * tolera". Pulsas, la web te lleva al sitio EXACTO, te lo MARCA, y te deja un
 * recordatorio a la vista de qué tienes que cambiar. Cuando lo cambias, el
 * recordatorio se va SOLO: nadie tiene que acordarse de tacharlo.
 *
 * Cómo se borra solo (la parte importante): un pin NO se "completa", se
 * DESVANECE. Cada fuente de problemas del sistema (los avisos del backend, los
 * hallazgos de un plan, los conflictos de la ficha…) publica periódicamente la
 * lista de sus problemas VIVOS con `syncScope(ámbito, clavesVivas)`. Todo pin
 * de ese ámbito cuya clave ya no está en la lista se elimina. Así el pin hereda
 * la verdad del backend en vez de inventarse un estado paralelo que se
 * desincroniza (que es exactamente el bug que tendría un "marcar como hecho").
 *
 * Un ámbito solo se sincroniza cuando su fuente está EN PANTALLA y ha cargado
 * bien; si la petición falla o el componente no está montado, no se sincroniza
 * y los pins se quedan (mejor un recordatorio de más que perder uno vivo).
 */

const CLAVE = "dqr.pins.v1";
const TOPE = 30; // más que esto no es una lista de tareas, es un vertedero

export interface Pin {
  /** Estable y derivada del problema: el mismo problema nunca se ancla dos veces. */
  id: string;
  /** Ámbito de la fuente que decide si sigue vivo: "alerts" | `plan:${planId}`… */
  scope: string;
  /** Clave del problema DENTRO de su ámbito (la que publica `syncScope`). */
  key: string;
  clientId: number;
  clientName: string;
  /** Qué hay que hacer, en pocas palabras. */
  label: string;
  /** Cómo se arregla — se enseña pegado al elemento marcado. */
  hint?: string;
  /** A dónde lleva el clic. */
  href: string;
  /** Ancla del elemento a marcar (ver lib/anchors.ts). */
  target?: string;
  severity: "alta" | "media";
  createdAt: number;
}

type Escucha = (pins: Pin[]) => void;

let pins: Pin[] = cargar();
const escuchas = new Set<Escucha>();
/** Ámbitos que YA han sincronizado al menos una vez en esta sesión: un pin de
 *  un ámbito que nunca ha hablado no se toca. */
const ambitosVivos = new Set<string>();

function cargar(): Pin[] {
  try {
    const raw = localStorage.getItem(CLAVE);
    if (!raw) return [];
    const datos = JSON.parse(raw);
    if (!Array.isArray(datos)) return [];
    return datos.filter((p) => p && typeof p.id === "string" && typeof p.scope === "string");
  } catch {
    return []; // modo privado, cuota llena, JSON corrupto: se empieza limpio
  }
}

function guardar() {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(pins));
  } catch {
    /* sin almacenamiento: los pins viven solo en memoria, no es un error */
  }
}

function emitir() {
  guardar();
  for (const fn of escuchas) fn(pins);
}

export function subscribePins(fn: Escucha): () => void {
  escuchas.add(fn);
  fn(pins);
  return () => { escuchas.delete(fn); };
}

// Dos pestañas abiertas del panel: lo que se arregla en una desaparece en la
// otra. Sin esto, la segunda pestaña seguía enseñando recordatorios muertos
// hasta recargarla.
if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key !== CLAVE) return;
    pins = cargar();
    for (const fn of escuchas) fn(pins);
  });
}

export function getPins(): Pin[] {
  return pins;
}

/** Ancla un problema. Idempotente: repetir el mismo clic no duplica nada,
 *  solo refresca el texto (el aviso puede haber cambiado de redacción). */
export function pin(nuevo: Omit<Pin, "createdAt"> & { createdAt?: number }): void {
  const anterior = pins.find((p) => p.id === nuevo.id);
  const fila: Pin = { ...nuevo, createdAt: anterior?.createdAt ?? nuevo.createdAt ?? Date.now() };
  pins = [fila, ...pins.filter((p) => p.id !== nuevo.id)].slice(0, TOPE);
  emitir();
}

/** Quita un pin a mano (el coach decide que no le interesa). */
export function unpin(id: string): void {
  const antes = pins.length;
  pins = pins.filter((p) => p.id !== id);
  if (pins.length !== antes) emitir();
}

/**
 * La fuente de un ámbito publica sus problemas VIVOS. Todo pin de ese ámbito
 * que ya no aparece se borra: el problema está resuelto.
 *
 * `clavesVivas` debe ser la lista COMPLETA del ámbito. Si la fuente no pudo
 * cargar, NO llames a esto (borrarías pins vivos).
 */
export function syncScope(scope: string, clavesVivas: Iterable<string>): void {
  const vivas = new Set(clavesVivas);
  ambitosVivos.add(scope);
  const antes = pins.length;
  pins = pins.filter((p) => p.scope !== scope || vivas.has(p.key));
  if (pins.length !== antes) emitir();
}

/** ¿Este ámbito ya ha dado señales de vida? (para no prometer auto-borrado
 *  donde todavía nadie está mirando). */
export function scopeSincronizado(scope: string): boolean {
  return ambitosVivos.has(scope);
}

/** Pins de un cliente concreto (para resaltarlos en su ficha). */
export function pinsDeCliente(clientId: number): Pin[] {
  return pins.filter((p) => p.clientId === clientId);
}

/** Identidad estable de un problema: el mismo problema, el mismo id. */
export function pinId(scope: string, key: string): string {
  return `${scope}::${key}`;
}
