# BRANDING.md — Guía white-label (vender el sistema a otra marca)

Este repositorio es la **instancia white-label** del motor de asesorías para
**PROFESSIONAL (Girona)**. El producto (anamnesis con IA → plan → portal →
seguimiento → revisión quincenal → feedback) es idéntico al original; lo único
que cambia entre instancias es la **marca**. Esta guía lista TODO lo que hay
que tocar para montar la siguiente instancia (otro gimnasio/empresa).

> Regla de oro: **nunca** escribas el nombre de la marca, sus colores, sus
> tarifas o su prefijo de Stripe en un módulo cualquiera. Todo vive en los dos
> módulos de marca (backend y frontend) y en los assets. Si un texto de marca
> aparece en otro sitio, es un bug de white-label.
>
> Catálogo actual de la instancia: **Génesis.99** (full, 99 €/mes, online) +
> **Entreno Personal** (sesiones presenciales, tarifas en `PT_RATES`, cobro en
> el centro) + `nutri` interno sin venta pública.

---

## 1. Los dos módulos de marca (espejo uno del otro)

| Lado | Archivo | Qué define |
|---|---|---|
| Backend | `backend/app/branding.py` | Nombre, tagline, contacto, paleta por defecto, etiquetas de los planes, prefijo de lookup de Stripe, claves de la oferta, pie de los Word, remitente SMTP por defecto, prefijo de tags push, User-Agent, slug público |
| Frontend | `frontend/src/lib/branding.ts` | Nombre, nombre corto, ruta del logo empaquetado, slug público |

Cambia los valores de ambos y el 95 % del rebrand está hecho.

## 2. Assets (se generan/sustituyen a mano)

- `frontend/public/brand-logo.png` — logo horizontal (~2,76:1, opaco: se ve
  sobre fotos y fondos oscuros). Aparece en login, panel, portal, páginas
  públicas.
- `backend/app/assets/plan/brand_logo.png` — el mismo logo para la cabecera de
  los documentos Word.
- `frontend/public/icons/icon-192.png`, `icon-512.png`, `icon-maskable-512.png`,
  `badge-72.png` — iconos PWA (portal instalable) y badge de notificaciones.
- `backend/app/assets/plan/cover_full.png`, `cover_train.png`, `cover_nutri.png`
  — portadas del DOSSIER del plan (una por producto; mapeo en
  `branding.DOC_PRODUCTS`). La entrega del día 1 es el dossier con esta
  portada + el enlace al portal (día a día).

## 3. Paleta CSS por defecto

`frontend/src/index.css` define los tokens (`--brand-accent`, hi/lo,
`--brand-accent-2`, hi/lo). En runtime la página **Marca** del panel los
sobreescribe desde `brand_config` (BD) sin recompilar; los del CSS son solo el
primer arranque. Los derivados hi/lo (luz/sombra de los gradientes) no vienen
de la BD: ajústalos en el CSS al tono nuevo. Hay fallbacks del mismo tono
repartidos como literales en componentes — búscalos por hex antes de entregar
(`grep -rniE "#e9a90f|#37474f|#0f0e0c" frontend/src` con los hex de la
  instancia actual).

## 4. Tarifas, catálogo y venta

- Importes canónicos de Stripe: `CANONICAL_AMOUNTS` en
  `backend/app/services/stripe_service.py` (céntimos, por plan × duración).
- Espejo visual: `priceMonthEur` en `frontend/src/lib/packages.ts`; tarifas
  presenciales informativas (por sesión/pack) en `PT_RATES` de `branding.ts`.
- **`PUBLIC_TIERS`** (ambos módulos de marca): qué planes tienen venta ONLINE.
  El backend **veta el checkout** del resto (se contratan/cobran en el local) y
  el endpoint público de precios no los expone. En esta instancia: solo `full`
  (Génesis.99, 99 €/mes); el Entreno Personal se reserva por WhatsApp y se
  cobra en el centro (alta manual + "Marcar pagado").
- **`OFFER_ENABLED`**: la oferta de captación (1 € el primer mes) del motor.
  Apagada aquí: sin checkout, sin precio/cupón en Stripe, sin botón en el kit
  de ventas y `/oferta` redirige a `/planes`.
- Cada instancia usa **su propia cuenta de Stripe**: con la clave en el `.env`,
  `scripts/setup_stripe_prices.py` (o el auto-alta) crea productos y precios
  con el prefijo de la marca. Cambiar un importe = editar `CANONICAL_AMOUNTS`
  y ejecutar el script (reprecia Stripe de forma idempotente).

## 5. Configuración por instancia (`.env`)

Credenciales y dominio propios: `DOMAIN`, `BASE_URL`, `ADMIN_*`, `JWT_SECRET`,
`PORTAL_TOKEN_SECRET`, `ANTHROPIC_API_KEY`, `SMTP_*`, `STRIPE_*`, `GOOGLE_*`,
claves VAPID nuevas (`scripts/generate_vapid_keys.py`). Ver `.env.example`.

## 6. Datos sembrados

`backend/app/seeds/run.py` crea la fila `brand_config` con los defaults del
modelo (que ya leen de `branding.py`) y rellena el teléfono de contacto
(`branding.CONTACT_PHONE`) si está vacío. La página **Marca** del panel permite
al dueño ajustar nombre, logo, colores, tagline y contacto en runtime.

## 7. Checklist de entrega de una instancia nueva

1. Duplicar el repo (o crear rama larga) — nunca tocar la instancia de otro cliente.
2. Editar `backend/app/branding.py` + `frontend/src/lib/branding.ts`.
3. Sustituir los 6 assets (§2) y los tokens/fallbacks CSS (§3).
4. Fijar tarifas (§4) y `.env` propio (§5).
5. `docker compose up --build`, sembrar admins, conectar Stripe/Google.
6. `pytest` completo + `npm run build` en verde.
7. Revisar con el cliente la página Marca (colores finos en runtime).
