/** Identidad de marca de ESTA instancia white-label — ÚNICA fuente de verdad
 *  del frontend. Espejo de `backend/app/branding.py` (si cambias uno, cambia
 *  el otro).
 *
 *  El producto es el mismo motor de asesorías; entre instancias (cada
 *  gimnasio/empresa a la que se vende) solo cambia la marca: nombre, logo,
 *  paleta (defaults de index.css, sobreescritos en runtime por brand_config),
 *  catálogo público y el slug de la página de enlaces.
 *
 *  Instancia actual: PROFESSIONAL (Girona) — Centre Salut & Fitness, by Lidia
 *  Miralpeix & Toni Pérez (professionalgirona.com). Identidad: serif blanco +
 *  dorado sobre negro, laurel como emblema.
 */

export const BRAND_NAME = "Professional Girona";
export const BRAND_SHORT = "Professional";
export const BRAND_TAGLINE = "Centre Salut & Fitness · by Lidia Miralpeix & Toni Pérez";

/** Logo empaquetado (fallback cuando brand_config no tiene logo subido). */
export const LOGO_SRC = "/brand-logo.png";

/** Slug de la página pública de enlaces (el link del perfil de Instagram):
 *  {origen}/{PUBLIC_SLUG}. Espejo de PUBLIC_SLUG del backend. */
export const PUBLIC_SLUG = "professional";

/** Tiers con venta ONLINE self-serve (espejo de branding.PUBLIC_TIERS del
 *  backend, que además VETA el checkout de los demás). El resto del catálogo
 *  se contrata en el centro (reserva por WhatsApp, cobro presencial). */
export const PUBLIC_TIERS: ReadonlyArray<string> = ["full"];

/** Tema del portal del cliente ANTES de cargar la marca (login del portal,
 *  pantallas de error): la identidad de Professional es oscura. Espejo de
 *  branding.PORTAL_THEME del backend. */
export const PORTAL_THEME: "dark" | "light" = "dark";

/** Funciones del motor APAGADAS en esta instancia (espejo de los FEATURE_* del
 *  backend). El motor las conserva; la marca quiere la web solo para el ciclo
 *  esencial: subir anamnesis → generar plan → portal → revisiones. */
export const FEATURE_RESOURCES: boolean = true;    // TIENDA (portal + enlaces)

// --- El centro (de professionalgirona.com) ----------------------------------
export const CENTER_ADDRESS = "Carretera Pierre Vilar, 2 · 17002 Girona";
export const CENTER_WHATSAPP_DISPLAY = "640 756 220";
export const CENTER_EMAIL = "professionalsaludifitness@gmail.com";
export const CENTER_SCHEDULE: ReadonlyArray<readonly [string, string]> = [
  ["Lunes a viernes", "06:00 – 23:00"],
  ["Sábado y domingo", "08:00 – 18:00"],
];

