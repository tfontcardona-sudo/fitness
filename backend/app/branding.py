"""Identidad de marca de ESTA instancia white-label — ÚNICA fuente de verdad.

El producto es el mismo motor de asesorías; lo que cambia entre instancias
(cada gimnasio/empresa a la que se vende) es la marca. TODO lo que dependa de
la marca en el backend debe leerse de aquí — nunca hardcodear el nombre, los
colores, el prefijo de Stripe ni el pie de los documentos en otro módulo.

Espejo en el frontend: `frontend/src/lib/branding.ts` (si cambias uno, cambia
el otro). Los colores son solo el DEFAULT inicial: la fila `brand_config` de la
BD (página Marca del panel) manda en runtime y permite afinarlos sin desplegar.

Instancia actual: PROFESSIONAL (Girona) — centro de salud y fitness con más de
25 años, de Lídia Miralpeix y Toni Pérez (professionalgirona.com).

⚠️ PROVISIONAL: los colores exactos del sitio web y las tarifas reales de sus
asesorías están pendientes de confirmar con el cliente; la paleta de abajo es
una propuesta premium editable desde la página Marca sin tocar código.
"""

# --- Identidad ---------------------------------------------------------------
BRAND_NAME = "Professional Girona"
BRAND_SHORT = "Professional"          # etiqueta corta (PWA, chips, prefijos)
BRAND_WORDMARK = "PROFESSIONAL"       # rótulo del logo
BRAND_TAGLINE = "Salud y fitness en Girona desde hace más de 25 años"

# --- Contacto público (defaults del seed; la página Marca manda) -------------
CONTACT_PHONE = "+34 972 40 60 51"
CONTACT_WEB = "https://professionalgirona.com"
CONTACT_ADDRESS = "C. de Santa Eugènia, 99 · 17006 Girona"

# --- Paleta por defecto (brand_config la sobreescribe en runtime) ------------
COLOR_PRIMARY = "#C9A227"    # dorado (acción/energía)
COLOR_SECONDARY = "#2C5F73"  # petróleo (estructura/datos)
COLOR_BG = "#0C1216"         # grafito noche (portal oscuro, theme-color PWA)

# --- Documentos Word / emails ------------------------------------------------
DOC_FOOTER = f"{BRAND_NAME} · Entrenamiento & Nutrición"
SMTP_FROM_DEFAULT = f"{BRAND_NAME} <info@professionalgirona.com>"

# --- Planes (tiers) ----------------------------------------------------------
# La maquinaria interna (nutri/train/full) es del producto; la marca solo pone
# la etiqueta comercial. Espejo: frontend/src/lib/packages.ts.
TIER_LABELS = {
    "nutri": f"{BRAND_SHORT} Nutri",
    "train": f"{BRAND_SHORT} Train",
    "full": f"{BRAND_SHORT} Full",
}

# --- Stripe ------------------------------------------------------------------
# Prefijo de los lookup_key de precios ({prefix}_{tier}_{period}) y claves de
# la oferta de captación. Cada instancia usa SU cuenta de Stripe, así que el
# prefijo solo tiene que ser estable dentro de la instancia.
STRIPE_LOOKUP_PREFIX = "pgirona"
STRIPE_TIER_METADATA_KEY = "app_tier"  # metadata que marca el Producto de cada plan
OFFER_LOOKUP = f"{STRIPE_LOOKUP_PREFIX}_full_oferta"
OFFER_COUPON_ID = f"{STRIPE_LOOKUP_PREFIX}_oferta_primer_mes"

# --- Varios ------------------------------------------------------------------
PUSH_TAG_PREFIX = "pg"  # tags de notificaciones push ("pg-plan", "pg-coach"…)
USER_AGENT_BOT = f"{BRAND_SHORT}Bot/1.0"
# Slug de la página pública de enlaces (el link del perfil de Instagram):
# {BASE_URL}/{PUBLIC_SLUG}. Espejo de la ruta en frontend/src/App.tsx.
PUBLIC_SLUG = "professional"
