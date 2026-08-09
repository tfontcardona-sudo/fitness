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

/** Oferta de captación (1 € el primer mes): APAGADA en esta marca — sin botón
 *  en el kit de ventas y sin página /oferta (el backend también la veta). */
export const OFFER_ENABLED = false;

// --- El centro (de professionalgirona.com) ----------------------------------
export const CENTER_ADDRESS = "Carretera Pierre Vilar, 2 · 17002 Girona";
export const CENTER_WHATSAPP_DISPLAY = "640 756 220";
export const CENTER_EMAIL = "professionalsaludifitness@gmail.com";
export const CENTER_SCHEDULE: ReadonlyArray<readonly [string, string]> = [
  ["Lunes a viernes", "06:00 – 23:00"],
  ["Sábado y domingo", "08:00 – 18:00"],
];

/** Tarifas PRESENCIALES de Entreno Personal (catálogo real del sitio).
 *  Informativas: se reservan por WhatsApp y se cobran en el centro. */
export const PT_RATES: ReadonlyArray<{ label: string; price: string }> = [
  { label: "Entreno personal socios", price: "50 €/h" },
  { label: "Entreno personal no socios", price: "60 €/h" },
  { label: "Pack 10 sesiones socios", price: "350 €" },
  { label: "Pack 10 sesiones no socios", price: "450 €" },
];
