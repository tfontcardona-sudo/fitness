"""Identidad de marca de ESTA instancia white-label — ÚNICA fuente de verdad.

El producto es el mismo motor de asesorías; lo que cambia entre instancias
(cada gimnasio/empresa a la que se vende) es la marca. TODO lo que dependa de
la marca en el backend debe leerse de aquí — nunca hardcodear el nombre, los
colores, el prefijo de Stripe ni el pie de los documentos en otro módulo.

Espejo en el frontend: `frontend/src/lib/branding.ts` (si cambias uno, cambia
el otro). Los colores son solo el DEFAULT inicial: la fila `brand_config` de la
BD (página Marca del panel) manda en runtime y permite afinarlos sin desplegar.

Instancia actual: PROFESSIONAL (Girona) — Centre Salut & Fitness, by Lidia
Miralpeix & Toni Pérez (professionalgirona.com). Identidad del sitio: serif
blanco + dorado sobre negro, con el laurel como emblema. Los colores exactos
pueden afinarse en runtime desde la página Marca (sin desplegar); el logo
definitivo del cliente se sube desde esa misma página.

Catálogo REAL de la marca (de su web):
  - Génesis.99 (99 €/mes): preparación personal COMPLETA (nutrición +
    entrenamiento) → tier interno `full`. Es el producto online del sistema.
  - Entreno Personal (50/60 €/h; pack 10 sesiones 350/450 € socios/no socios):
    sesiones PRESENCIALES en el centro → tier interno `train`. Se reservan por
    WhatsApp y se cobran en el centro (el coach marca pagado a mano); el
    cliente usa el portal de entreno (rutina, series, progreso).
  - No venden asesoría de solo nutrición → el tier `nutri` queda INTERNO
    (el coach puede usarlo a mano, pero no aparece en la página pública ni
    tiene pago online).
"""

# --- Identidad ---------------------------------------------------------------
BRAND_NAME = "Professional Girona"
BRAND_SHORT = "Professional"          # etiqueta corta (PWA, chips, prefijos)
BRAND_WORDMARK = "PROFESSIONAL"       # rótulo del logo (serif + laurel)
BRAND_TAGLINE = "Centre Salut & Fitness · by Lidia Miralpeix & Toni Pérez"

# --- Contacto público (defaults del seed; la página Marca manda) -------------
CONTACT_PHONE = "+34 640 756 220"     # WhatsApp del centro (CTA públicos)
CONTACT_EMAIL = "professionalsaludifitness@gmail.com"
CONTACT_WEB = "https://professionalgirona.com"
CONTACT_ADDRESS = "Carretera Pierre Vilar, 2 · 17002 Girona"

# --- Paleta por defecto (brand_config la sobreescribe en runtime) ------------
# Del sitio real: dorado vivo (chips de tarifas) sobre negro cálido, con
# blanco serif. El secundario es un gris pizarra neutro para datos/estructura.
COLOR_PRIMARY = "#E9A90F"    # dorado (acción/energía)
COLOR_SECONDARY = "#37474F"  # gris pizarra (estructura/datos)
COLOR_BG = "#0F0E0C"         # negro cálido (portal oscuro, theme-color PWA)

# Tema del PORTAL del cliente por defecto: la identidad de la marca es
# oscura (negro/dorado), así que el portal nace en oscuro; la página Marca
# permite cambiarlo en runtime.
PORTAL_THEME = "dark"

# --- Documentos Word / emails ------------------------------------------------
DOC_FOOTER = f"{BRAND_NAME} · Centre Salut & Fitness"
SMTP_FROM_DEFAULT = f"{BRAND_NAME} <{CONTACT_EMAIL}>"

# --- Planes (tiers) ----------------------------------------------------------
# La maquinaria interna (nutri/train/full) es del producto; la marca solo pone
# la etiqueta comercial. Espejo: frontend/src/lib/packages.ts.
TIER_LABELS = {
    "nutri": "Plan Nutrición",        # interno: la marca no lo vende suelto
    "train": "Entreno Personal",      # sesiones presenciales en el centro
    "full": "Génesis.99",             # preparación personal completa (online)
}

# Tiers con VENTA ONLINE self-serve (checkout de Stripe desde la web pública).
# Los demás existen para el coach (alta manual + cobro en el centro), y el
# backend RECHAZA crear un checkout suyo — así un enlace mal construido no
# puede cobrar online un plan que se paga presencialmente.
PUBLIC_TIERS = ("full",)

# Oferta de captación (1 € el primer mes → suscripción). La maquinaria existe
# en el motor, pero esta marca NO la usa: apagada de raíz (sin checkout, sin
# precio/cupón en Stripe, sin botón en el kit de ventas).
OFFER_ENABLED = False

# --- Método del banco de comidas de la marca ---------------------------------
# "options": TODAS las tomas del plan flexible llevan opciones CERRADAS (combos
# completos con gramos) — el método de Professional: sencillo y directo.
# "equivalences": comida/cena por grupos de alimentos intercambiables (el
# método del plan de origen del motor; sigue soportado en validación, escalado,
# portal y documento para planes legado u otras instancias).
MEAL_BANK_STYLE = "options"
MEAL_BANK_OPTIONS = 3  # opciones por toma (el schema admite 1-4)

# --- Dossier del plan (documento Word) ---------------------------------------
# Título comercial, subtítulo y arte de portada del dossier según el tier del
# cliente (assets en backend/app/assets/plan/). El dossier es la ENTREGA
# premium del día 1; el día a día vive en el portal.
DOC_PRODUCTS = {
    "full": ("Génesis.99", "Preparación personal", "cover_full.png"),
    "train": ("Entreno Personal", "Plan de entrenamiento", "cover_train.png"),
    "nutri": ("Plan Nutrición", "Plan de nutrición", "cover_nutri.png"),
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
