/**
 * LA PIEL DE LA MARCA — una sola puerta en el frontend.
 *
 * El switch de marca cambiaba TRES colores (`--brand-accent`,
 * `--brand-accent-2` y poco más) sobre una piel de DQR clavada en el CSS: el
 * panel seguía siendo crema, el portal seguía siendo el azul noche de DQR con
 * un brillo naranja abajo y las páginas públicas seguían imprimiendo el logo
 * de DQ. Y había algo peor que "poco": el `color_secondary` de Professional es
 * un NEGRO (#161616), y ese color pinta el anillo de foco del panel y el
 * anillo de progreso del portal — negro sobre negro, invisible.
 *
 * Una identidad no son tres colores: es el fondo, la tinta, las superficies,
 * las líneas, las luces, las formas y la tipografía. Eso es la PIEL, viene del
 * backend como un dato de la marca (`skin`, mig. 0053) y se aplica de una vez
 * poniendo `data-piel` en la raíz. El CSS hace el resto.
 *
 * Dos preguntas distintas, las mismas que en el backend:
 * · El PANEL y las páginas públicas llevan la piel de la marca ACTIVA.
 * · El PORTAL y el cuestionario llevan la piel de la marca DEL CLIENTE — la
 *   sellada en su ficha. Que el coach cambie el switch no puede cambiarle el
 *   portal a quien ya está pagando.
 */

import type { FuncionDeMarca } from "../types";

export type Piel = "dqr" | "professional";

const PIELES: readonly Piel[] = ["dqr", "professional"] as const;

/** Normaliza lo que venga del backend. Una piel desconocida cae en la de DQR:
 *  un negocio nuevo mal configurado se ve como siempre, nunca sin estilo. */
export function pielDe(skin: string | null | undefined): Piel {
  const v = (skin ?? "").trim().toLowerCase();
  return (PIELES as readonly string[]).includes(v) ? (v as Piel) : "dqr";
}

/**
 * Aplica la piel a TODA la página (panel, login, páginas públicas).
 *
 * Va en `<html>` y no en un contenedor porque el fondo, la textura y la barra
 * de desplazamiento cuelgan de `body`/`:root`: pintarlo más abajo dejaba el
 * borde de la ventana con el color del otro negocio.
 */
export function aplicarPiel(piel: Piel): void {
  const raiz = document.documentElement;
  raiz.dataset.piel = piel;
  // El color del chrome del navegador (barra de estado en móvil) también es de
  // la marca: en negro con una barra crema, la app parece recortada.
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", piel === "professional" ? "#151515" : "#f4eee3");
}

/**
 * EL LOGO. `logo_url` es el fichero que el dueño haya subido en
 * Recursos → Marca; mientras no lo suba, cada marca tiene su MARCA
 * TIPOGRÁFICA propia (ver `MarcaLogo`), nunca el logo de la otra.
 *
 * DQR tiene su PNG empaquetado; Professional todavía no tiene fichero, y
 * caer en `/dq-logo.png` era enseñarle al cliente de un negocio el logo del
 * otro — en su portal, en su cuestionario y en su página pública.
 */
export function logoDeMarca(logoUrl: string | null | undefined, piel: Piel): string | null {
  if (logoUrl) return logoUrl;
  return piel === "professional" ? null : "/dq-logo.png";
}

/* ------------------------------------------------------- lo que usa la marca --
 * QUÉ APARTADOS TIENE ESTE NEGOCIO.
 *
 * La piel cambiaba cómo se VE el panel y no lo que ENSEÑA: con el centro
 * activo seguían ahí el catálogo de afiliación, la página de enlaces del
 * perfil de Instagram, la conexión con Google y los tres planes de DQR en el
 * alta. Un negocio no es solo una identidad, también es un modo de trabajar.
 *
 * La respuesta la da el BACKEND (`usa` en el contrato de marca), que junta lo
 * declarado con lo que ya dicen otros datos suyos. Aquí no se deduce nada: si
 * el panel dedujera por su cuenta, el día que cambie una regla diría una cosa
 * el servidor y otra la pantalla.
 */

/** ¿Este negocio usa esto? Sin respuesta —la marca aún no ha llegado— vale
 *  que SÍ: es lo que había antes de que esto existiera, y hacer desaparecer un
 *  apartado a mitad de carga es peor que enseñarlo. */
export function usaLaMarca(
  usa: Partial<Record<FuncionDeMarca, boolean>> | null | undefined,
  clave: FuncionDeMarca,
): boolean {
  return usa?.[clave] !== false;
}

/* ------------------------------------------------------------------ colores --
 * LOS DOS COLORES, RESUELTOS POR SU PAPEL.
 *
 * El portal pinta con los hexadecimales de la marca EN LÍNEA en 74 sitios
 * (`style={{ color: brand.color_secondary }}`, `${brand.color_secondary}30`
 * para el alfa…). Por eso la piel no llegaba hasta ahí: el CSS puede cambiar
 * un token, pero no un color escrito dentro del componente.
 *
 * Y con Professional el resultado era grave, no feo: su `color_secondary` es
 * un NEGRO (#161616) porque en su identidad el negro es la ESTRUCTURA, no un
 * acento. Ese color pintaba el anillo de progreso de la quincena y el número
 * de días que quedan — negro sobre negro. El cliente no veía cuánto le
 * faltaba para su revisión.
 *
 * Así que los colores se resuelven UNA vez, al cargar el portal, y bajan ya
 * con el papel que les toca en esta piel. Siguen siendo hexadecimales, así
 * que el truco del alfa (`${color}30`) sigue funcionando tal cual.
 */

/** Mezcla sRGB, la misma cuenta que `color-mix(in srgb, base p%, mezcla)`.
 *  Es lo que mantiene el oro claro del TypeScript y el del CSS en el mismo
 *  tono aunque el dueño retoque su dorado en Recursos. */
export function mezclar(base: string, pct: number, mezcla = "#ffffff"): string {
  const hex = (c: string) => {
    const v = c.replace("#", "").trim();
    const full = v.length === 3 ? v.split("").map((x) => x + x).join("") : v;
    const n = parseInt(full.slice(0, 6), 16);
    return Number.isNaN(n) ? null : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  const a = hex(base), b = hex(mezcla);
  if (!a || !b) return base;                       // color ilegible: se deja
  const p = Math.max(0, Math.min(1, pct / 100));
  const c = a.map((v, i) => Math.round(v * p + b[i] * (1 - p)));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

export interface ColoresDeMarca {
  /** Acción: lo que se pulsa, lo que destaca. */
  primary: string;
  /** Estructura y dato: anillos, escalas, iconos de información. */
  secondary: string;
}

/**
 * El papel de cada color en esta piel.
 * · dqr — tal cual los guarda la marca: naranja acción, azul estructura.
 * · professional — el oro es la acción y el ORO CLARO hace de estructura. El
 *   negro de la marca se queda donde le toca (el fondo y las superficies, que
 *   los pone la piel), nunca pintando un dato sobre un fondo negro.
 */
export function coloresDeMarca(
  piel: Piel, colorPrimary: string, colorSecondary: string,
): ColoresDeMarca {
  if (piel !== "professional") return { primary: colorPrimary, secondary: colorSecondary };
  return { primary: colorPrimary, secondary: mezclar(colorPrimary, 72) };
}

/**
 * UN COLOR DE CATEGORÍA QUE SE LEA EN ESTA PIEL.
 *
 * El panel usa paletas de CATEGORÍA escritas a mano (los grupos de la campana
 * de avisos, los bloques de la anamnesis): son etiquetas de significado, no
 * colores de marca, así que se conservan igual en los dos negocios — pero
 * están afinadas para leerse sobre CREMA. Sobre el negro de Professional, el
 * ámbar (#9A6B15) en un rótulo de 11 px se queda en 2,9:1, por debajo de AA.
 *
 * Esto no reinventa la paleta: sube el color hacia el blanco solo LO JUSTO
 * para llegar a 4,5:1 sobre el fondo de la piel. El tono se mantiene, así que
 * la categoría se sigue reconociendo; lo que cambia es que se lee.
 */
export function colorLegible(hex: string, piel: Piel): string {
  if (piel !== "professional") return hex;
  const FONDO = 0.008;                        // luminancia relativa de #151515
  const lum = (c: string): number | null => {
    const v = c.replace("#", "").trim();
    const full = v.length === 3 ? v.split("").map((x) => x + x).join("") : v;
    const n = parseInt(full.slice(0, 6), 16);
    if (Number.isNaN(n)) return null;
    const canal = (x: number) => {
      const s = x / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * canal((n >> 16) & 255) + 0.7152 * canal((n >> 8) & 255)
      + 0.0722 * canal(n & 255);
  };
  let actual = hex;
  for (let i = 0; i < 12; i++) {
    const l = lum(actual);
    if (l === null) return hex;               // color ilegible: se deja
    if ((l + 0.05) / (FONDO + 0.05) >= 4.5) return actual;
    actual = mezclar(actual, 88);             // un 12 % hacia el blanco por paso
  }
  return actual;
}

/* ------------------------------------------------------- valores por defecto --
 * Los colores de arranque, cuando la marca todavía no ha llegado del servidor
 * (una página pública en su primer pintado). Viven AQUÍ y no repetidos en cada
 * pantalla: escritos a mano, un negocio heredaba los de otro en cuanto alguien
 * se olvidaba de cambiar uno.
 */
export const MARCA_POR_DEFECTO = {
  primary: "#E8833A",
  secondary: "#2E5E8C",
  bg: "#0B111C",
} as const;

/** El acento de la marca tal y como lo está pintando el navegador ahora mismo.
 *  Para lo que necesita un COLOR DE VERDAD y no una `var()`: las gráficas de
 *  recharts, que dibujan en canvas/SVG con el valor literal. */
export function acentoDeMarca(): string {
  try {
    const v = getComputedStyle(document.documentElement)
      .getPropertyValue("--brand-accent").trim();
    return v || MARCA_POR_DEFECTO.primary;
  } catch {
    return MARCA_POR_DEFECTO.primary;         // sin DOM (pruebas, SSR)
  }
}
