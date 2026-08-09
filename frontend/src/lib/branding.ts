/** Identidad de marca de ESTA instancia white-label — ÚNICA fuente de verdad
 *  del frontend. Espejo de `backend/app/branding.py` (si cambias uno, cambia
 *  el otro).
 *
 *  El producto es el mismo motor de asesorías; entre instancias (cada
 *  gimnasio/empresa a la que se vende) solo cambia la marca: nombre, logo,
 *  paleta (defaults de index.css, sobreescritos en runtime por brand_config)
 *  y el slug de la página pública de enlaces.
 *
 *  Instancia actual: PROFESSIONAL (Girona) — centro de salud y fitness con
 *  más de 25 años (professionalgirona.com).
 *
 *  ⚠️ PROVISIONAL: colores exactos del sitio y tarifas reales pendientes de
 *  confirmar con el cliente; la paleta es una propuesta premium editable desde
 *  la página Marca sin recompilar.
 */

export const BRAND_NAME = "Professional Girona";
export const BRAND_SHORT = "Professional";
export const BRAND_TAGLINE = "Salud y fitness en Girona desde hace más de 25 años";

/** Logo empaquetado (fallback cuando brand_config no tiene logo subido). */
export const LOGO_SRC = "/brand-logo.png";

/** Slug de la página pública de enlaces (el link del perfil de Instagram):
 *  {origen}/{PUBLIC_SLUG}. Espejo de PUBLIC_SLUG del backend. */
export const PUBLIC_SLUG = "professional";
