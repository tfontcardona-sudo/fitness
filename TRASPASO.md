# Documento de traspaso — Fitness System (DQ / David Quiceno)

> Objetivo de este doc: que otra sesión de IA (Fable u otra) pueda **continuar el trabajo sin perder contexto**.
> Última actualización: 2026-07-19 (9ª): **embudo de Instagram completo** — landing pública /dq + registro self-serve con datos antes del pago + anamnesis PDF subida por el propio cliente (§10.q). Anterior (8ª y 7ª): Autor del último tramo: Claude — (a) coherencia nutricional TOTAL: `reconcile_nutrition` (kcal ≡ macros 4/4/9 ≡ suma por comida) en generación IA, adaptación y guardado del editor + espejo bit-exacto en el frontend; comando `python -m app.maintenance.reconcile_plans` para planes antiguos. (b) Selector de estructura de comidas en Planificación (regenera con IA) Y en el editor (reparte al instante las MISMAS kcal/macros; sincroniza `client.meal_schedule` al guardar). (c) Pestaña Recursos del portal (vídeos de ejercicios + productos, rama del socio) revisada con workflow adversarial: 13 fallos confirmados y corregidos (PNG paleta corrupto, bomba de píxeles, ExerciseOut que rompía con URLs legadas, PATCH con null → 500, unlink antes del commit, host de YouTube por urlsplit, migración 0017 de remache…). (d) Stripe integrado (checkout + webhook `checkout.session.completed` + página /planes; claves en `.env`). **(8ª, mismo día):** pagos por duración contratada — mensual/trimestral/semestral (9 precios `STRIPE_PRICE_{PLAN}_{1M,3M,6M}`, `clients.billing_period` + migración 0019, selector en /planes y en el alta, fila "Duración" editable en la ficha) + guía operativa **`STRIPE.md`** paso a paso (verificada contra el código). Ver §10.p.
> Anterior (5ª): edición manual de nutrición íntegra por objetivo (inputs sin dígito pegado, "cuadrar por objetivo", kcal como ancla) + suite a 108/108.
> Anterior (4ª): nivel de actividad diaria/NEAT en la anamnesis + TDEE; pautas de diabetes y tiroides en la IA; calidad de PDFs y textos IA (tono serio sin emojis, tablas que paginan sin recortar, escape del texto libre en emails).
> **PRODUCCIÓN:** el sistema está desplegado en `https://app.dqrassessories.com` (VPS Hetzner
> `46.225.57.25`, repo en `/root/fitness`, ver `DEPLOY.md`). Actualizar: `cd /root/fitness && git pull && docker compose up -d --build`.
> Cliente/marca: **David Quiceno (DQ)** — asesoría de fitness. Colores marca: **vino `#8B1A2B`**, **azul `#4A7BA8`**.

---

## 0. TL;DR — dónde nos hemos quedado

- Sistema de **asesoría de fitness** completo: app del **coach** (web con login JWT) + **portal del cliente** (sin login, por token `/p/{token}`) + **backend FastAPI** + IA para generar planes y feedback.
- Acabamos de terminar una **gran feature: portal de seguimiento** (entreno/diario/quincenal) + **seguimiento en tiempo real** del coach + **adaptación del plan** tras cada revisión quincenal. Backend + frontend **aplicados y verificados**.
- **HECHO (2026-07-03): Web Push completo** (§8.1) — PWA instalable por cliente, service worker, suscripciones VAPID, job cada 4 h y badge en el icono. Falta solo generar las claves VAPID en el `.env` (1 comando) y, para móviles reales, tener HTTPS.
- **HECHO (2026-07-04): pulido §8.2** — tema oscuro **"iron obsidiana"** del portal (BrandPage → Portal del cliente → Oscuro) + **pill "HOY"** en el selector de sesión de entreno. Default normalizado a claro (migración `0005`). Verificado con screenshots Playwright (3 pestañas × 2 temas, 0 errores JS).
- **BLOQUEANTE ACTUAL:** la **API de Anthropic no tiene crédito** (`Your credit balance is too low`). Por eso la generación de plan inicial y el feedback IA fallan (502/error). Se **simularon a mano** para el cliente de prueba. La **adaptación de plan NO necesita IA** (es determinista) y funciona.

---

## 1. Stack y arquitectura

| Capa | Tecnología |
|------|-----------|
| Backend | **FastAPI** + **SQLAlchemy** + **Alembic** (migraciones) + **Pydantic** |
| Base de datos | **PostgreSQL** (JSONB para planes/análisis) |
| Frontend | **React + Vite + TypeScript** + Tailwind (clases utilitarias) |
| Documentos | **python-docx** (Word) → **LibreOffice headless** (docx→PDF). En HOST: **PyMuPDF (fitz)** solo para QA de render (NO está en el contenedor) |
| IA | `app/services/ai/` — `AIClient` (Anthropic). `model_heavy` para planes/feedback |
| Infra | **Docker Compose** (`docker-compose.yml` + `docker-compose.dev.yml`) |
| Email | **Mailpit** (dev) |

**Contenedores** (`docker compose ps`): `api`, `db`, `web`, `mailpit`.
- `api`: python:3.11-slim + LibreOffice + fuente Carlito. `entrypoint.sh` corre `alembic upgrade head` al arrancar. Uvicorn con `--reload` (volumen montado).
- `web`: Vite dev server (HMR, volumen montado).

**Dos aplicaciones frontend:**
1. **Coach** — con login JWT. Páginas en `frontend/src/pages/`, componentes en `frontend/src/components/`.
2. **Portal del cliente** — sin login, token en URL `/p/{token}`. Todo en `frontend/src/portal/`. API en `frontend/src/portal/portalApi.ts`.

---

## 2. Modelos de datos clave (`backend/app/models.py`)

- **Client** — ficha del cliente (anamnesis estructurada: sexo, edad, peso, objetivo, alergias, comidas, etc.). `status`: onboarding/active/at_risk/review_pending/awaiting_feedback/inactive. `portal_token`. `start_weight_kg`, `goal_weight_kg`.
- **Plan** — plan mensual. `month_index`, `version`, `status` (draft/published/superseded). `nutrition_json`, `training_json`, `education_json` (JSONB). `generated_by`.
- **Period** — período quincenal (cierre de 2 semanas). Campos de cierre (revisión quincenal):
  - `closing_weight_kg`, `closing_waist_cm`, `closing_hip_cm`, `closing_arm_cm`, `closing_thigh_cm`, `closing_rating`, `closing_hardest`, `closing_questions`
  - **(añadidos en esta feature)** `closing_feelings_json` (dict sensaciones 1-5), `adherence_diet_0_10`, `adherence_training_0_10`, `free_meals_count`, `closing_changes`, `closing_next_goal`
  - `ai_analysis_json` (métricas + `plan_adjustments` del feedback)
  - **`coach_reviewed_at`** (marca cuándo el coach vio la revisión → apaga el "!")
  - `status`: open / closed / analyzed
- **DailyLog** — registro diario. `weight_kg`, `sleep_hours`, `diet_adherence` (yes/partial/no), `energy_1_5`, `mood_1_5`, `fatigue_1_5`, `free_notes` + **(añadidos)** `steps` (String), `satiety_1_10` (Float), `water_liters` (Float).
- **WorkoutLog** — series de entreno (peso+reps) ligadas a un `daily_log_id` y `exercise_id`.
- **Exercise** — biblioteca de ejercicios (patrón, músculos, equipo, nivel, contraindicaciones).
- **ProgressPhoto** — fotos de progreso (ahora se piden por WhatsApp, no se suben).
- **FeedbackDoc** — informe de feedback quincenal.
- **BrandConfig** — marca (nombre, colores, logo, tema portal).

**Migraciones Alembic** (`backend/alembic/versions/`):
- `0002_tracking_fields.py` — campos de tracking en DailyLog + Period.
- `0003_coach_reviewed_at.py` — `periods.coach_reviewed_at`.
- `0009_portal_login.py` — `clients.portal_password_hash`, `portal_access_sent_at`.
- `0010_period_unique.py` — un solo período abierto por cliente + `UNIQUE(client_id, period_index)` (con dedupe previo).
- `0011_daily_activity.py` — `clients.daily_activity_level` (NEAT: sedentary|light|active|very_active). **Idempotente.**
- Se aplican solas al arrancar `api`. Manual: `docker compose exec api sh -c "cd /code && alembic upgrade head"`.

---

## 3. Feature "Portal de seguimiento" — estado COMPLETO

### 3.1 Portal del cliente (`frontend/src/portal/`)
- **Solo 3 pestañas abajo**: **Entreno** / **Diario** / **Quincenal** (se quitaron Hoy/Plan/Progreso). La dieta va en el PDF, no en el portal.
- Tema **CREMA `#F5F0E8`** + colores DQ (vino/azul) + **luces neón** + **botones 3D**. CSS en `frontend/src/index.css` (`.portal-root`, `.portal-btn3d`, `.portal-card`, `.portal-neon-wine/blue`, `.portal-nav`, `.portal-tab-badge`).
- **PortalWorkout.tsx** — registro de series; auto-selecciona la sesión del día ("· hoy"), navegable a otras; historial por ejercicio (`ExHistory`, "última vez" expandible) vía `GET /api/p/{token}/workout-history`.
- **PortalDiary.tsx** — diario con peso/sueño/pasos/saciedad/litros/comentarios. Autosave. Registro por fecha (resetea a las 00:00 al abrir día nuevo).
- **PortalClose.tsx** — **REVISIÓN QUINCENAL** (réplica del PDF del coach). 7 secciones: 1) medidas (peso + cintura/cadera/brazo/muslo), 2) 6 sensaciones (1-5), 3) adherencia dieta/entreno (0-10) + comidas libres, 4) cambios, 5) qué cuesta, 6) objetivo, 7) fotos → nota WhatsApp; + dudas. **Bloqueada hasta el día 15** con contador de días + "Se activa el <fecha>"; badge "!" en la pestaña cuando se puede rellenar.

### 3.2 Coach — pestañas del perfil de cliente (`frontend/src/pages/ClientProfilePage.tsx`)
Tabs: Resumen / Anamnesis / **Planificación** / **Seguimiento** / **Feedback** / **Historial**. Lee `?tab=` de la URL.

- **ClientTrackingTab.tsx** (Seguimiento, tiempo real, polling 10s):
  - Tabla de registros diarios + **fila "Media"** (media de peso/sueño/pasos/saciedad/agua/series/%adherencia).
  - **Revisiones quincenales** como **desplegables** (`<details>`), más reciente primero, con rango de fechas + **valoración /10** en el summary. Dentro: **antes/después** (día 1 → día 15) de peso y cinta, adherencias, sensaciones, textos.
  - Abrir esta pestaña **marca `coach_reviewed_at`** → apaga el "!" de la lista.
- **ClientFeedbackTab.tsx** (Feedback):
  - **Sin** sección de fotos, **sin** "Regenerar feedback", **sin** "Descargar Word".
  - Botón **"Generar feedback"** solo si no existe aún (necesita IA → hoy falla por falta de crédito).
  - **Resumen** con antes/después de 15 días (peso start→end) + métricas + fuerza.
  - Texto de feedback **editable** + botón **"Copiar todo"**.
  - Banner **"! Adaptar planificación a la revisión #N"** (llama a `adaptPlan`, sin IA).
- **ClientHistoryTab.tsx** (Historial):
  - Objetivo: **peso objetivo (kg) + kg restantes**.
  - **Medidas antes/después** (primer vs último período con dato) + **% fuerza total**.
  - **Evolución por período** = **desplegable** por período: cinta (cintura/cadera/brazo/muslo), peso, adherencia, **% fuerza subido en el período**.
  - **Sin** sección "Planes".
  - Nota: con **1 solo** período, antes==después y los % salen "—" (hace falta ≥2 revisiones).
- **ClientPlanPanel.tsx** (Planificación):
  - Genera plan inicial con IA (`generatePlan`, hoy falla por crédito).
  - Botón **"! Adaptar a la revisión #N"** → `adaptPlan` (determinista, sin IA). Crea nueva versión borrador; el coach la revisa y **publica** (el cliente ve la rutina nueva; el PDF de dieta se actualiza).

### 3.3 Backend endpoints clave (`backend/app/routers/clients.py`)
- `GET /api/clients/{id}/tracking` — período + daily + **daily_averages** + **quincenals** (lista acumulada con antes/después + `feelings_score_10`) + flags. Marca `coach_reviewed_at`.
- `GET /api/clients/{id}/history` — resumen + `remaining_to_goal_kg` + `measures{before,after}` + `total_strength_gain_pct` + períodos (con cinta + `strength_gain_pct`).
- `GET /api/clients` (list_clients) — añade `pending_review` / `pending_review_period` (períodos closed/analyzed con `coach_reviewed_at IS NULL`) → **badge "!"** en la lista.
- `POST /api/clients/{id}/generate-plan` — genera plan con IA (dieta+entreno). Inyecta los `plan_adjustments` del último período `analyzed` en `ctx.notes`.
- `POST /api/clients/{id}/adapt-plan` — **NUEVO, sin IA**. Ver 4.2.
- `GET /api/p/{token}/workout-history` — historial por ejercicio para el portal.

### 3.4 Adaptación / feedback IA
- `app/services/ai/feedback.py` — `FeedbackAIOutput` con `plan_adjustments` (lista de `PlanAdjustment{area, change, reason}`) = la **cuadrícula de cambios**.
- `app/services/feedback_service.py` — `build_period_feedback` (payload con registro_diario + revisión_quincenal completa) + `compute_period_summary` (métricas sin IA).
- `app/services/docs/feedback_doc.py` — renderiza la "Cuadrícula de cambios aplicados".
- `app/services/docs/plan_doc.py` — `generate_plan_doc(include_training=False)` → **PDF solo dieta** (clon del ejemplo del coach; ver memoria `plan-example-fidelity`).

---

## 4. El fix del 502 al "Adaptar plan" (IMPORTANTE)

### 4.1 Causa
`POST /generate-plan` → llama a la IA → **sin crédito** → error → **502**. La generación inicial SÍ necesita IA. Pero la **adaptación** no debería (los cambios ya los calculó la IA en el feedback).

### 4.2 Solución (aplicada)
`backend/app/services/adapt_plan.py` → `adapt_plan_from_feedback(db, client_id)`:
- Coge el **último período `analyzed`** (coincide con el banner del coach).
- Coge el **plan publicado** como base.
- Aplica los `plan_adjustments` de forma **DETERMINISTA** con `_parse_change`:
  - Distingue **delta** (`+15`, `subir 15`, `bajar 20`) vs **objetivo absoluto** (`reducir a 150`, `hasta 2000`, `200 g`). "a/hasta N" tiene prioridad sobre el verbo.
  - Dieta: proteína / CH / kcal (con **clamp `>=0`**).
  - Entreno: solo deltas `+X kg` → suma a `start_weight_hint_kg` de todos los ejercicios.
  - Cambios no numéricos/estructurales (p.ej. "añadir 1 serie") se ignoran y quedan en el rationale para que el coach los aplique a mano.
- Crea **nueva versión borrador**. NO llama a la IA → **funciona siempre**.
- Endpoint `POST /clients/{id}/adapt-plan` → `AdaptError` mapea a **409** (nunca 500/502). Ajustes vacíos → copia + nota (no crashea).
- Frontend: botón en ClientPlanPanel + banner en ClientFeedbackTab llaman `api.adaptPlan` (NO `generatePlan`).

**Verificado:** Manuel (34) → proteína 185→**200**, básicos **+2,5 kg**. Cliente 2 (sin ajustes) → copia sin error. Casos límite del parser OK.

---

## 5. CAVEAT crítico — API sin crédito

La API de Anthropic da `Error 400: Your credit balance is too low`. Afecta a:
- **Generar plan inicial** (necesita IA) → falla.
- **Generar feedback** (parte cualitativa) → falla.
- **NO afecta** a "Adaptar plan" (es determinista).

Para el cliente de prueba **Manuel Rodríguez (id 34)** se **simuló a mano** (métricas/gráficas/cuadrícula/PDF son reales; solo el texto IA se escribió a mano): FeedbackDoc borrador, 5 `plan_adjustments`, plan adaptado.

**Acción para el usuario:** recargar crédito en la cuenta Anthropic para que el flujo IA funcione end-to-end. Config de la clave: `backend/app/config.py` (variable de entorno / `.env`).

---

## 6. Datos de prueba

- **Cliente 34 "Manuel Rodríguez"** — el poblado a mano: período #1 (2026-06-18→07-01, backdated), 14 DailyLogs, ~158 series, revisión quincenal completa, feedback simulado, plan v1 publicado + drafts v2/v3.
- **Cliente 35 "Didac"** — cliente de pruebas del desarrollo de la feature.
- **Cliente 2** — tiene período `analyzed` pero **sin `plan_adjustments`** (feedback antiguo) → adaptar hace copia+nota.

Obtener token de portal de un cliente: `GET /api/clients/{id}/portal-link` (con JWT) o mirar `client.portal_token` en la BD.

---

## 7. Cómo arrancar / probar / verificar

> Para publicarlo en internet (link público permanente con HTTPS): ver **`DEPLOY.md`**.

```bash
# Arrancar todo
cd C:/Users/Usuari/Desktop/fitness-system
docker compose up -d            # o: docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

docker compose ps               # ver estado
docker compose logs api --tail 50

# Typecheck frontend
docker compose exec web npx tsc --noEmit

# Import/sanity backend
docker compose exec api python -c "import app.routers.clients; print('OK')"

# Migraciones (se aplican solas al arrancar; manual:)
docker compose exec api sh -c "cd /code && alembic upgrade head"
```

- Coach web: normalmente `http://localhost:5173` (Vite) → login. API en `http://localhost:8000`, OpenAPI en `http://localhost:8000/api/openapi.json`.
- Portal cliente: `http://localhost:5173/p/{token}`.

**Verificación de esta feature (ya hecha, repetible):** hay un workflow guardado en
`.../workflows/scripts/verify-tracking-changes-wf_*.js` (auditoría de requisitos + caza de bugs). Resultado del último run: **20/20 requisitos, 0 bugs graves, 5 medios/bajos → todos corregidos**.

---

## 8. PENDIENTE

### 8.1 Web Push — **HECHO (2026-07-03, Claude Fable 5)**
Implementado completo según la spec original. Mapa de piezas:

**Backend**
- `app/services/push.py` — núcleo: `pending_for_client` (qué falta HOY: diario /
  entreno / quincenal), `build_reminder_payload`, `send_to_client` (pywebpush +
  VAPID; borra suscripciones caducadas 404/410), `run_push_reminders` (el job).
- `app/models.py` → **`PushSubscription`** + migración **`0004_push_subscriptions`**.
- `app/routers/portal_public.py` — 5 endpoints nuevos bajo `/api/p/{token}`:
  `GET /push/public-key`, `POST /push/subscribe`, `POST /push/unsubscribe`,
  `GET /push/pending` (para el badge al abrir) y `GET /manifest.webmanifest`
  (**manifest PWA POR CLIENTE**: `start_url=/p/{token}` → al instalar la app se
  abre directamente SU portal).
- `app/services/scheduler.py` — job `push_reminders` **cada 4 h** en punto
  (CronTrigger `*/4`); el propio job descarta ejecuciones fuera de **08–22**
  (constantes `ACTIVE_FROM/ACTIVE_UNTIL` en push.py) → en la práctica envía a
  las 08/12/16/20 y **solo a quien tenga algo pendiente**.
- `app/config.py` + `.env.example` → `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
  `VAPID_SUBJECT`, `PUSH_ENABLED`. `scripts/generate_vapid_keys.py` las genera.
- `requirements.txt` → `pywebpush==2.3.0`.
- Tests: `tests/test_push.py` (9 tests: puros + integración con PG, envío
  monkeypatcheado). Verificado además con smoke test HTTP de los 5 endpoints.

**Frontend**
- `public/sw.js` — service worker (raíz → scope cubre `/p/*`): muestra la
  notificación, pone `count` en el badge (`navigator.setAppBadge`) y al tocarla
  enfoca/abre el portal. Sin caché offline (a propósito).
- `public/icons/` — icon-192/512, maskable-512 y badge-72 (mancuerna, vino DQ).
- `src/portal/push.ts` — registro del SW, **inyección del manifest por cliente**,
  `enablePush` (permiso + PushManager.subscribe + POST al backend),
  `resyncPushIfGranted` (autocura silenciosa), `refreshBadge`.
- `src/portal/PortalApp.tsx` — `PushBanner` ("¿Te aviso si te falta algo?" con
  botón Activar; en **iOS sin instalar** muestra instrucciones de "Añadir a
  pantalla de inicio", porque en iOS el push solo existe en la app instalada);
  badge sincronizado al cargar y al volver el foco.
- `index.html` — apple-touch-icon + metas PWA.

**Para activarlo (una vez):**
```bash
docker compose exec api python -m scripts.generate_vapid_keys
# pegar las 3 líneas en .env  →  docker compose build api && docker compose up -d
```

**Cómo probar:** en el PC, Chrome en `http://localhost:5173/p/{token}` (localhost
cuenta como contexto seguro): banner → Activar → aceptar permiso → fila en
`push_subscriptions`. Forzar un envío sin esperar al cron:
`docker compose exec api python -c "from app.db import SessionLocal; from app.services.push import run_push_reminders; print(run_push_reminders(SessionLocal()))"`
(dentro de la ventana 08–22 y con algo pendiente). **En móviles reales hace
falta HTTPS** (DOMAIN configurado con Caddy); en iOS además instalar la PWA.

### 8.2 Pulido — **HECHO (2026-07-04)**
- **Look "iron obsidiana"** oscuro vino/azul del portal: la paleta del portal ahora
  vive en variables CSS en `.portal-root` (crema por defecto) y `.portal-root.portal-dark`
  las sobrescribe (fondo obsidiana `#0e0b10`, glows vino/azul más intensos, tarjetas
  metal oscuro, nav oscura). `PortalApp` añade la clase cuando `brand.portal_theme === "dark"`.
  Se activa vía BrandPage → Portal del cliente → **Oscuro**.
- **Default normalizado a claro**: el modelo decía `default="dark"` pero el CSS siempre
  pintaba crema; al honrar de verdad el tema, eso habría oscurecido portales existentes
  por sorpresa. Default en modelo/schema/fallback → `"light"` + **migración `0005`**
  (una vez: `portal_theme 'dark' → 'light'`; conserva lo que el cliente VE).
- **Pill "HOY"** en el selector de sesión de entreno (`.portal-today-pill`, vino + neón)
  y borde tintado en la sesión de hoy cuando no está seleccionada (antes solo "· hoy" en texto).
- El manifest PWA oscuro usa `background_color #0E0B10` (alineado con el nuevo fondo).
- Historial: los antes/después y % de fuerza necesitan **≥2 períodos** para verse; con 1 salen "—" (informativo, no es bug).

### 8.3 Cuando haya crédito de IA
- Probar generar plan inicial + feedback real end-to-end (hoy simulado para Manuel).

---

## 9. Convenciones y "gotchas" (no tropezar dos veces)

- **Docker en este PC** se corrompió una vez por disco lleno (reparse points AF_UNIX en `Docker\run` + `docker-secrets-engine`). Si no arranca: resetear ambos dirs a la vez y arrancar una vez.
- **Render docx→PDF QA**: usar **LibreOffice headless** (no Word COM). **PyMuPDF (fitz)** solo en HOST, no en el contenedor. Ojo disco lleno. Ver memoria `docx-render-tooling`.
- **PDF del plan** debe ser **clon del ejemplo del coach** (PDF `Didad.docx (3).pdf`); solo cambia la info del cliente. Detalles y correcciones de fidelidad (banda translúcida de la comida, plato en PNG sin fondo negro, logo, tablas que no se cortan) en memoria `plan-doc-design` y `plan-example-fidelity`.
- **Edit tool**: hay que **Read** el archivo antes de editar.
- **PowerShell 5.1**: sin `&&`/`||`/ternarios; el clasificador de sandbox se pone nervioso con rutas cerca de `C:\Program Files`.
- **La infra de tracking YA existía** (DailyLog/WorkoutLog/Period/portal) — se **extendió**, no se creó de cero.
- Las **fotos** de progreso se envían por **WhatsApp**, no se suben al portal.
- **Migraciones**: `0001` hace `create_all` desde los modelos ACTUALES → en una
  BD nueva, cualquier migración posterior encuentra sus columnas/tablas ya
  creadas. Por eso **0002–0004 son idempotentes** (comprueban existencia antes
  de añadir) y **toda migración futura debe serlo también**.
- **`SessionLocal` usa `autoflush=False`**: un servicio que hace add/delete y
  luego SELECT en la misma sesión debe hacer `db.flush()` entre medias o no
  verá sus propios cambios (ver `push.save_subscription`).

---

## 10. Memoria persistente de la IA (contexto extra)

En `C:\Users\Usuari\.claude\projects\C--Users-Usuari-Desktop-fitness-system\memory\`:
- `MEMORY.md` — índice.
- `tracking-portal-feature.md` — **estado detallado de esta feature** (fases, decisiones, cambios por prompt). El más importante para continuar.
- `plan-doc-design.md` — diseño del Word/PDF del plan.
- `plan-example-fidelity.md` — el plan IA debe ser clon del PDF ejemplo.
- `docx-render-tooling.md` — cómo renderizar docx→imagen para QA.

---

## 10.b Tramo 2026-07-05 — Rebrand DQ + flujo adaptar-revisión transparente

**Identidad nueva (azul `#2E5E8C` + naranja `#E8833A` + crema `#F6F1E7` + logo DQ):**
- Coach app: tema azul noche (`--bg #0B111C`) con acento naranja; logo DQ en sidebar/login;
  todos los verdes menta antiguos sustituidos por `var(--brand-accent)`.
- Portal: crema suave con acentos naranja (acción) y azul (estructura); tema oscuro = azul noche.
- Iconos PWA regenerados ("DQ." sobre azul noche) · manifest actualizado.
- Migración **`0006_dq_rebrand`** actualiza la fila `brand_config` existente.
  Defaults nuevos en `models.py` / `portal.py`.

**Flujo "adaptar a la revisión" (petición del coach — todo transparente):**
1. Feedback: el banner ya NO adapta a ciegas → lleva a Planificación.
2. Planificación: desplegable **"Cambios propuestos por la revisión #N"** (chips Dieta/Entreno,
   cambio + porqué) con el botón Adaptar dentro. Datos: `PeriodOut.plan_adjustments`
   (de `ai_analysis_json`, en `list_periods`).
3. Al adaptar, `adapt_plan.py` guarda en `nutrition_json.applied_adjustments`
   `{period_index, items:[{area,change,reason,applied,detail}]}` con **antes→después**
   ("Proteína: 185 → 200 g"); lo no numérico queda `applied:false` ("aplicar a mano").
4. El borrador muestra **"Cambios aplicados en esta versión"**; el coach edita y publica.
5. Portal Entreno: desplegable **"Novedades de tu plan"** (GET `/p/{token}/training` →
   `plan_changes`, solo si el plan está publicado). PDF: sección **"Cambios de tu plan ·
   revisión #N"** (tabla Área/Qué cambia/Por qué) tras "Notas del ajuste".
6. **Fix workflow:** `portal.published_plan_for_period` ahora cae a la última versión
   publicada si el plan anclado al período fue supersedido (adaptación a mitad de período).

**QA:** tsc + build + compileall OK; screenshots Playwright con API stubbeada de TODA la web
(login/dashboard/clientes/6 tabs, 2 estados de Planificación) y el portal (3 tabs × 2 temas),
0 errores JS. Scripts en el scratchpad de la sesión (verify-coach.mjs / verify-portal.mjs).

**Iteración 2 (mismo día):**
- **La web del coach ahora es CREMA** (`--bg #F4EEE3`, tarjetas blancas, tinta cálida).
  Las clases zinc (pensadas para fondo oscuro) se remapean a tinta cálida con overrides
  globales al final de `index.css` (el portal no usa zinc). `tailwind.config` apunta a
  las variables CSS. Todos los colores inline oscuros (ámbar/rojo/azules claros/tooltips
  de la gráfica) remapeados a tonos con contraste sobre claro; `STATUS_TONE` oscurecido.
- **Dashboard = cola de acciones**: cada cliente se traduce en su siguiente acción
  ("Revisión quincenal subida → Generar feedback", "Feedback listo → Adaptar
  planificación", "Onboarding → Crear planificación", "Adherencia baja → Ver
  seguimiento", "Esperando cierre") con botón directo a la pestaña del perfil.
  Secciones: Qué toca hacer / En espera del cliente / Al día. (`DashboardPage.tsx`
  reescrito; el mapeo vive en `nextAction()`.)
- **Página "Marca" ELIMINADA** (ruta, nav y archivo). Los colores de marca siguen
  saliendo de `brand_config` en BD (los fijó la migración 0006); si algún día hay que
  cambiarlos: UPDATE a `brand_config` o restaurar la página desde git.

**Iteración 10 — Carpetas de cartera por ciclo + móvil del coach:**
- **Clientes → CARPETAS por punto del ciclo** (no por estado crudo):
  Todos · Activos (plan publicado) · Pendientes (sin plan aún) · Revisión
  pendiente (con su nº: "Revisión #N pendiente") · Objetivo 45 días (sale de
  la carpeta al mantener/cambiar) · Inactivos. Con contadores por chip.
  Backend: list_clients rellena `has_published_plan` y `review_period_index`
  (ClientOut). Filtro en cliente (`inCategory`), búsqueda sigue en servidor.
- **Badges de ciclo** (`CycleBadges`): "Revisión #N pendiente" (violeta,
  punto pulsante) y "Objetivo · Xd" (azul) en tabla y tarjetas.
- **Dashboard**: chip de CATEGORÍA con color+icono en cada acción (Revisión
  morado, Riesgo rojo, Adaptar naranja, Pendiente índigo, Objetivo azul,
  En espera ámbar); el título de revisión lleva su nº; onboarding SIN
  anamnesis → botón "Abrir anamnesis" (tab anamnesis), con anamnesis →
  "Crear planificación" (el botón lleva a LO QUE FALTA).
- **MÓVIL del coach** (la web era incómoda en el teléfono):
  · AppShell: en <768px desaparece la sidebar y hay NAV INFERIOR tipo app
    (Hoy/Clientes/Salir, safe-area, useIsMobile con matchMedia).
  · Clientes: la tabla se convierte en TARJETAS (avatar, objetivo, badges,
    chevron, un toque = perfil).
  · Dashboard: botón de acción a ancho completo (pulgar).
  · Perfil: pestañas DESLIZABLES (.profile-tabs, sin cortar) y arreglo del
    desbordamiento horizontal (min-w-0 en los hijos del grid — las pestañas
    forzaban el ancho de página).
  · CSS `.coach-mobile`: px-6→1rem, inputs a 16px (sin zoom iOS), campana
    abajo a la derecha sobre la nav (no tapa cabeceras), panel de alertas
    abre hacia arriba.
  · QA: `MOBILE=1 node verify-coach.mjs` captura todo a 390px (m-*.png).

**Iteración 9 — Etapas de objetivo (45 días), centro de alertas y BACKTEST:**
- **Etapa del objetivo**: `clients.goal_started_on` (se fija al publicar el
  1er plan / al cambiar objetivo) y `goal_review_snoozed_on` (posponer);
  `plans.goal_type` = snapshot del objetivo que servía cada plan (migración
  0007, idempotente + backfill). A los 45 días → alerta "valorar cambio".
- **Cambiar objetivo** (tarjeta en Planificación, `GoalStageCard`):
  días en la etapa · botón "Generar análisis de la etapa" (IA con respaldo
  determinista — POST /clients/{id}/goal-review/analysis: lo conseguido con
  cifras, proyección si continúa, opciones de objetivo) · "Mantener objetivo
  actual" (snooze 45 días) · selector + confirmación en 2 pasos "Cambiar
  objetivo y regenerar plan" (POST change-goal → generate-plan mes+1 con TODO
  el historial en contexto). Las planificaciones anteriores quedan ARCHIVADAS
  en desplegable con su objetivo como título y su duración.
- **Centro de ALERTAS** (`routers/alerts.py` + campana `AlertsBell` fija
  arriba a la derecha): derivadas del estado real (se autolimpian al resolver)
  — crear/publicar plan, generar feedback, feedback sin enviar, plan sin
  adaptar, borrador sin publicar, sin registros 4+ días, 45 días de objetivo
  (posponible desde la propia campana). Refresco al navegar + cada 2 min.
  Dashboard añade la acción "Valorar objetivo". La pestaña del perfil SIGUE
  la URL (?tab=) → las alertas navegan bien incluso dentro del mismo cliente.
- **IA con contexto profundo**: la generación usa el peso ACTUAL (último
  registro/cierre, no el inicial) para BMR/TDEE y añade al prompt
  `historial_seguimiento` (revisiones: peso, adherencia, fuerza) — clave al
  regenerar por cambio de objetivo.
- **BACKTEST completo** (`scripts/backtest_workflow.py`): Postgres 16 local +
  freezegun + IA mockeada; 5 clientes (un objetivo cada uno) × 92 días contra
  la API real: 6 quincenas completas por cliente, cambio de objetivo (día 46),
  posposiciones que reaparecen a los 45, alerta de inactividad que se apaga al
  volver, adaptación idempotente verificada numéricamente, 1 feedback por
  período, disciplina del ciclo (nunca período nuevo antes del feedback).
  → **1.384 comprobaciones, 0 fallos.** BUG DE PRODUCCIÓN cazado y arreglado:
  con autoflush=False, publicar NO abría el período (ensure_open_period no
  veía el plan recién publicado; ahora hace db.flush() al entrar).
  Cómo repetirlo: initdb PG local → `DATABASE_URL=... python -m
  scripts.backtest_workflow` (sale 1 si algún invariante falla).
- pytest del backend: los 11 fallos existentes son PREEXISTENTES en main
  (fixtures ScriptedClient/push desactualizadas), verificado con worktree.
- QA front nuevo: `goal-test.mjs` (15 asserts: campana, análisis, cambio en
  2 pasos, archivo con título/duración, snooze) + todos los harnesses previos.

**Iteración 8 — Nutrición por objetivo (evidencia) + recálculo encadenado + comidas en anamnesis:**
- **Objetivos ampliados** (backend Literal + tipos front + selector anamnesis +
  avisos quincenales): fat_loss, muscle_gain, recomp, **maintenance**,
  **injury_recovery**. Reglas por evidencia en `services/metrics.py`
  (GOAL_ADJUSTMENT + PROTEIN_RANGE, con referencias: Helms 2014, Morton 2018,
  Iraki 2019, Barakat 2020, Tipton 2015) y su ESPEJO front en
  `lib/nutritionTargets.ts` (GOAL_RULES) — cambiar ambos a la vez.
- **Editor del plan — recálculo ENCADENADO** (`ClientPlanEditor` + panel pasa
  client y refWeightKg = último peso de cierre ?? inicial):
  · cambiar CALORÍAS → macros óptimos del objetivo (proteína/grasa por kg,
    carbos el resto, suelo de grasa 0,6 g/kg);
  · cambiar un MACRO → kcal por 4/4/9;
  · en AMBOS casos `rescaleNutrition` reescala los objetivos por comida (cada
    eje por su ratio) y el banco de comidas (macros por opción + gramos de
    ingredientes a múltiplos de 5).
  · Tarjeta azul "Recomendado para <objetivo>" (peso real + TDEE del plan) con
    botón "Aplicar recomendación".
- **Anamnesis → "Comidas del día"** (`MealsPlanner`): chips Desayuno/Media
  mañana/Comida/Merienda/Cena/Pre-cama — el nº de comidas se DERIVA de las
  elegidas (meal_schedule con horas por defecto) — o botón azul "Lo decidimos
  nosotros" (meals_per_day y meal_schedule → null). Backend: comidas ya NO son
  obligatorias para generar (fuera de _REQUIRED_FIELDS y del check de horario);
  el generador y el prompt dicen a la IA que elija el reparto óptimo (3-5) si
  el cliente lo delega. AnamnesisSubmit relajado igual.
- QA nuevos: `editor-test.mjs` (8 asserts: recomendación con peso real,
  kcal→macros, macro→kcal, aplicar recomendación, PATCH con comidas y gramos
  reescalados) y `anamnesis-test.mjs` (5 asserts del planificador de comidas).

**Iteración 7 — Auditoría profunda del workflow + azul de marca:**
- BUGS BACKEND arreglados (auditoría a fondo del ciclo):
  · `periods.ensure_open_period`: ya NO abre período nuevo con la revisión
    entregada y el feedback pendiente (cliente review_pending o último período
    "closed") — antes el ciclo 2 arrancaba solo y quemaba días mientras el
    coach revisaba. El período nuevo se abre AL ENVIAR el feedback
    (send_feedback llama a ensure_open_period) → ciclo determinista.
  · `adapt_plan`: IDEMPOTENTE. Plan vigente ya adaptado a esa revisión →
    error claro; borrador ya adaptado → se REHACE desde el publicado (los
    deltas nunca se acumulan: proteína 150→165→180 era posible antes).
    Base elegida por (mes, versión) — antes solo versión y podía coger el mes
    equivocado. Guard "mantener": "Mantener proteína en 180 g" ya no toca macros.
  · `feedback_service`: regenerar feedback REEMPLAZA el doc del período (no
    apila un segundo) y lo devuelve a borrador.
  · `update_plan` PATCH: si el editor manda nutrition_json sin
    applied_adjustments pero el plan lo tenía, se conserva (el portal/PDF no
    pierden las "Novedades").
- BUGS PORTAL arreglados:
  · Revisión quincenal con BORRADOR persistente (localStorage por período):
    cambiar de pestaña a mitad ya no borra lo escrito; se limpia al enviar.
  · Fecha local (`PortalUi.localToday`): toISOString daba la fecha UTC y a
    partir de las ~23h los registros caían en el día siguiente.
  · Autosave sin pérdidas: volcado inmediato al ocultar la app/cambiar de
    pestaña (visibilitychange/pagehide/desmontaje) y AVISO si falla la red
    (antes fallaba en silencio bajo "se guarda solo").
  · "días restantes" nunca negativo; tarjeta "vuelta a la calma" con
    .portal-card real (la var --portal-card no existía); nota de Novedades
    condicional por áreas; FEELING_LABEL con las claves reales del portal
    (recuperacion/animo/digestiones) y seed alineado.
- AZUL de marca (azul = estructura/datos/info · naranja = acción):
  coach → foco/inputs en foco, hover de pestañas, subtítulos de Feedback,
  MiniTitle de Seguimiento, fila "Seguimiento activo", chips de día y "Sem N"
  del entrenamiento, cabecera de la comparativa del Historial, barrita de
  "En espera del cliente". Portal → nº "días restantes", campana del banner,
  chip "revisión #N", pill HOY, borde de sesión de hoy, enlace "historial",
  candado quincenal (portal-neon-blue), números de sección, banner de fotos,
  carets de datos. Táctil: inputs de series ≥44px, papelera w-11, banner push.
- QA: `portal-behavior-test.mjs` (7 asserts del borrador quincenal y el envío)
  + los 4 harnesses previos re-pasados (coach, portal light/dark, behavior, wa).

**Iteración 6 — Feedback plegable, ajustes editables y comparativa de revisiones:**
- **Aviso "Ir a Feedback" del perfil**: solo mientras la última revisión cerrada
  NO tenga feedback generado (`ClientProfilePage.feedbackPending`, comprueba
  `listPeriods → feedback_id`); generar el feedback lo apaga al instante
  (generate() llama a onClientChanged).
- **Feedback por períodos plegables**: solo el período ACTUAL sale desplegado;
  los anteriores en `<details>` plegados (orden: más reciente arriba). El botón
  "Resumen" desapareció: las métricas se cargan SOLAS (período actual al entrar,
  antiguos al desplegarlos vía onToggle). Botones del summary con preventDefault
  para no plegar la tarjeta.
- **AdjustmentRow**: fuera el badge "aplicar a mano"; chips de color FIJO por
  área (`AREA_CHIPS`): dieta naranja, entreno azul, sueño violeta #63519E,
  actividad diaria verde #3F7446, hidratación teal #28707C, suplementos ocre.
- **"Cambios aplicados" EDITABLE** (lápiz "Editar cambios" en el summary):
  texto y porqué por fila, quitar filas, guardar → PATCH /plans/{id} con
  nutrition_json.applied_adjustments actualizado (persiste en portal y PDF).
- **Historial → "Evolución tras las revisiones quincenales"**: línea SVG del
  peso (Inicio + cierre de cada revisión, valores rotulados, si >6 puntos solo
  los clave) + tabla con Δ kg, Δ %, adherencia y fuerza por revisión + fila
  TOTAL. Sustituye al viejo sparkline. "Descargar todo" ya estaba fuera.
- QA: `scratchpad/behavior-test.mjs` (11 asserts: plegado/desplegado, carga de
  métricas por onToggle, edición y PATCH con payload verificado) + harness
  visual y wa-test re-pasados.

**Iteración 5 — Envíos por WhatsApp profesionales + teléfono editable:**
- **Teléfono editable** en la ficha del cliente (primera fila de la tarjeta,
  `ClientProfilePage.PhoneRow`): lápiz → input tel → Enter/✓ guarda vía
  `updateClient`; vacío muestra "añádelo para WhatsApp".
- **Mensajes de WhatsApp centralizados y profesionales** en `lib/whatsapp.ts`
  (SIN emojis — se corrompían como `�` — saludo con nombre capitalizado, cuerpo
  con secciones en *negrita* de WhatsApp y cierre serio): `feedbackMessage`,
  `planMessage`, `planAndFeedbackMessage`, `feedbackBody` (también alimenta
  "Copiar todo").
- **Feedback**: enlace naranja "Enviar por WhatsApp" junto a "Copiar todo /
  Editar texto" — permanece tras el envío (reenvíos); solo marca sent la
  primera vez.
- **Planificación** (plan publicado): "Enviar plan por WhatsApp" + botón
  primario "Enviar plan + feedback" (un solo mensaje con informe + enlace al
  PDF). El panel carga el último feedback vía `listPeriods → getFeedback`; el
  envío conjunto marca sent si no lo estaba (prop `onClientChanged` nueva).
- **"Descargar todo" (ZIP) eliminado** del Historial (`exportClientUrl` sigue
  en la API por si se recupera).
- QA: `scratchpad/wa-test.mjs` captura el wa.me real por clic y verifica los
  tres textos (número +34, nombre capitalizado, negritas, enlace PDF).

**Iteración 4 — Asesorías ágiles (WhatsApp + períodos autónomos + análisis quincenal):**
- **Seguimiento → revisión quincenal reestructurada**: bloque "Puntos a vigilar"
  (análisis DETERMINISTA en `ClientTrackingTab.avisosQuincenal`: ritmo kg/sem vs
  objetivo, adherencias <6/<8, sensaciones ≤2, comidas libres ≥4, días sin
  registrar, sueño/saciedad medios, dudas pendientes) + secciones Medidas /
  Adherencia (stats coloreados) / Sensaciones (chips) / "En palabras del cliente".
- **WhatsApp con un clic** (`lib/whatsapp.ts`, 9 dígitos → +34):
  · Feedback: "Enviar por WhatsApp" abre wa.me con el texto completo y marca
    sent (review_pending → active). Ya no se "envía al portal".
  · Plan: "Enviar por WhatsApp" manda el enlace al PDF público
    **`GET /api/p/{token}/plan.pdf`** (nuevo; constructor compartido en
    `services/plan_delivery.py`, usado también por la descarga del coach).
- **Períodos AUTÓNOMOS** (`services/periods.ensure_open_period`, idempotente):
  se abre al publicar un plan, al entrar el cliente al portal (/state), al abrir
  el coach Seguimiento, y red de seguridad en el job diario. **"Iniciar
  seguimiento" eliminado** del panel de Planificación.
- **Botones que desaparecen solos**: banner de Feedback "Revisar cambios…" se
  oculta cuando el último plan ya está adaptado a esa revisión (compara
  applied_adjustments.period_index); la tarjeta "Cambios propuestos"+Adaptar ya
  se ocultaba. **"Regenerar plan (nueva versión)" eliminado.**

**Iteración 3 — UX/UI del portal (navegación en 1 clic, táctil, a11y):**
- **`src/lib/useDismiss.ts`** — hook ÚNICO de cierre de overlays: click/tap fuera
  (en fase de captura → una sola pulsación cierra Y ejecuta el destino), ESC, y
  limpieza al desmontar (cambio de pestaña/ruta). + `useModalFocus` (focus trap +
  devolución del foco al abridor). Aplicado a: "Novedades de tu plan" (details
  controlado), `ConfirmDialog` y `NewClientModal` (con role=dialog/aria-modal).
- **Toasts** (portal y coach): `pointer-events-none` (no roban taps a la nav) +
  `role=status aria-live=polite`.
- **Táctil:** inputs del portal a 16px (adiós zoom iOS), `viewport-fit=cover` +
  `env(safe-area-inset-bottom)` en la nav inferior, `touch-action: manipulation`
  global, estados :active (scale 0.97) y hover en todo lo pulsable del portal,
  papelera de serie con área 44px + aria-label, botones 1-5 con `.tap`.
- **Pestañas del portal en la URL (`?tab=`)**: el botón atrás vuelve a la pestaña
  anterior (no expulsa); transición `animate-rise` al cambiar; `aria-current` en
  la nav. Labels reales en Diario/Quincenal (htmlFor / label envolvente).
- **Código muerto borrado**: PortalToday/PortalPlan/PortalFeedback → `Loading`
  (ahora skeleton) y `Empty` viven en `PortalUi.tsx`.
- **QA de comportamiento**: `ux-tests.mjs` (scratchpad) — 9 asserts Playwright
  (click-fuera, ESC, 1-tap con overlay abierto, botón atrás, aria-current,
  pointer-events del toast, 16px, safe-area, sin scroll horizontal) → 9/9 PASS.

## 10.c Tramo 2026-07-07 (2ª parte) — Repaso integral de los prompts del día

Cierre de los flecos detectados al revisar TODO lo pedido el 7 de julio:

- **Recálculo kcal⇄macros en el editor (bug real)**: cambiar calorías no
  adaptaba los 3 macros y teclear valores intermedios corrompía gramos.
  Arreglado con `rescaledFrom()` (`lib/nutritionTargets.ts`): cada cambio se
  reescala SIEMPRE desde la nutrición original (`baseline` ref en
  `ClientPlanEditor.tsx`) → idempotente. La suma de las comidas ahora CUADRA
  EXACTA con los totales (el resto de redondeo va a la comida mayor de cada eje).
- **Reescalado también en el backend** (`services/nutrition_scale.py`, NUEVO,
  espejo del frontend): la adaptación quincenal (`adapt_plan.py`) ya no cambia
  solo los totales — si un ajuste toca kcal o macros, TODO se mueve en bloque
  (kcal⇄macros coherentes 4/4/9 según objetivo/peso, objetivos por comida y
  GRAMOS del banco a múltiplos de 5). El PDF de dieta queda coherente.
- **SIN botón "Publicar"** (`services/plan_activation.py`, NUEVO): la
  planificación queda ACTIVA al generarse, al adaptarse y al editarse (el envío
  es por WhatsApp). `POST /plans/{id}/publish` queda como legado para borradores
  antiguos (botón "Activar"). Etiquetas: "Activa" / "Borrador antiguo".
  Re-adaptar a la misma revisión → 409 con aviso claro (no acumula).
- **Anamnesis (PDF plantilla) sin cortes de página**: el título "MOTIVO Y
  OBJETIVOS" quedaba huérfano al pie de la pág. 1 → movido al inicio de la
  pág. 2 (parche quirúrgico con pypdf+reportlab, estilo idéntico). En pág. 6 se
  añadió "¿Cuáles? (desayuno, media mañana, merienda, pre-cama…)" + casilla
  "Lo decidís vosotros". `extraction.py` actualizado: si delega → 
  `meals_per_day=null` y `meal_schedule=[]`.
- **Objetivo en palabras del cliente → IA**: `ClientContext.goal_in_own_words`
  (se alimenta de `lifestyle_notes`, la sección "Motivo y objetivos" de la
  anamnesis) entra en el prompt de generación con la instrucción de diseñar
  dieta y entreno para ESE fin concreto, no solo para la etiqueta del objetivo.
- **Auto-refresco cada 30 s** (pestaña visible) en Dashboard, Clientes, perfil
  del cliente y campana de alertas: la web se mantiene al día sola.
- **Verificación**: backtest 5 clientes × 92 días → **1529 comprobaciones OK ·
  0 fallos** (incluye: plan activo al generarse, kcal coherentes tras ajuste,
  comidas que cuadran exactas, re-adaptar avisa 409, banco reescalado). Suite
  pytest OK (2 fallos pre-existentes del mock IA, ya fallaban en main). Los 8
  harnesses Playwright OK. Test unitario de `nutrition_scale` OK.

## 10.d Tramo 2026-07-07 (3ª parte) — Proporcionalidad, semana del mesociclo y métricas ricas

- **Kcal → 3 macros EN PROPORCIÓN (bug)**: al editar calorías solo se movían los
  carbohidratos (proteína/grasa iban ancladas por kg). Ahora los TRES macros
  escalan en proporción al mix del plan y los carbohidratos cuadran el 4/4/9:
  `macrosScaledToKcal` (front) ⇄ `macros_scaled_to_kcal` (back, usado por la
  adaptación quincenal cuando el ajuste solo toca kcal). "Aplicar recomendación"
  sigue usando la evidencia por kg (goalTargets). El editor muestra una TABLA de
  comidas EN VIVO que se reescala al teclear.
- **Pestaña Planificación reordenada**: nutrición (kcal/macros + comidas) →
  banco → entrenamiento (sesiones DESPLEGABLES por día) → **Puntos importantes
  del cliente** (lesiones/salud/medicación/alergias/aversiones/objetivo en sus
  palabras, desde la ficha) → suplementación → planificaciones anteriores
  ENRIQUECIDAS (fechas reales "5 jun → 20 jun", duración, objetivo, kcal/macros
  y "Por qué se hizo/cambió" desde applied_adjustments/rationale).
- **Portal: semana del mesociclo** (`current_training_week` en services/portal.py):
  anclada al MIN(published_at) del mes (adaptar no reinicia la semana), cicla en
  oleadas si el mes se alarga. GET /p/{token}/training devuelve `week` (fase,
  carga, RIR, porqué didáctico por intent) y cada ejercicio lleva
  `week_weight_hint_kg` (hint × load_pct/base, redondeado a 0,5 kg). El portal
  muestra el banner "Semana X de Y · FASE" + explicación, y los pesos sugeridos
  (placeholder incluido) ya van ajustados. Prompt del núcleo: periodización por
  objetivo con evidencia (onda 100→102.5→105 + deload; lesión suave; etc.).
- **Fuerza por grupo muscular** (`compute_period_summary`): por cada grupo el
  ejercicio más relevante (mayor e1RM), con peso medio levantado y reps medias,
  comparado con la ÚLTIMA revisión anterior CON DATOS de ese ejercicio (no solo
  la inmediata): Δkg de media, Δe1RM y %. Adherencia ahora también en días:
  "84% · 12 de 15 días" (diet_days_yes/partial).
- **Análisis de cambio de objetivo**: 4 bloques — añade en cada opción QUÉ
  GANARÍA el cliente frente a seguir con el plan actual, y un bloque
  'Veredicto' (mantener vs cambiar, contando si aún no llegó al peso objetivo).
  Respaldo determinista con _GOAL_GAIN + _goal_verdict_fallback.
- **Verificación**: backtest 5×92 días → 1529 OK · 0 fallos; pytest OK; los 8
  harnesses Playwright OK (editor-test ampliado: proporcionalidad + tabla en
  vivo; verify-portal con fixture de semana). Unit del espejo back OK.

## 10.e Tramo 2026-07-07 (4ª parte) — Pulido integral + equivalencias del PDF

- **BUG REAL del PDF**: el banco de comidas de comida/cena usa EQUIVALENCIAS con
  cantidades en TEXTO ("140 g crudo = 380 g cocido") que el reescalado no
  tocaba → tras editar kcal/macros el PDF salía con gramos viejos. Arreglado en
  `nutrition_scale.py` + `nutritionTargets.ts`: `_scale_amount_text` escala los
  números con unidad (g/gr/ml, múltiplos de 5 desde 25) y cada grupo escala por
  SU eje (`_equiv_ratio`: proteína→r_p, hidratos/fruta→r_c, grasas→r_f).
- **Aviso tras editar**: banner naranja + toast "descarga el PDF de nuevo"
  (estado `needsDownload` en ClientPlanPanel; se limpia al descargar).
- **Editor**: fuera los campos Tempo y Peso sug.; sesiones DESPLEGABLES por día
  y cada ejercicio plegado (summary = nombre + series×reps).
- **Panel planificación**: banco de comidas ELIMINADO de la web (solo PDF);
  reglas de flexibilidad en desplegable; "Justificación de la nutrición"
  estructurada por puntos con chips de color (`RationaleView` parsea
  "- [Área] cambio — porqué"); Objetivo con "pulsa para cambiar"; Puntos
  importantes con lo CRÍTICO EN ROJO (#B3261E, secciones lesiones/medicación/
  alergias + palabras clave; negación pura no marca — ojo "no resuelta" SÍ).
- **Ficha (sidebar)**: tarjeta Anamnesis en desplegable (abierta solo si falta);
  botón azul destacado "Diario del cliente" (móvil+checklist) que copia/abre el
  portal; fila Dieta = kcal/macros del PLAN ACTIVO (vacía hasta generar);
  Avatar con degradado naranja→azul (ángulo estable por nombre) y brillo.
- **Resumen**: Notas clínicas SOLO con lo relevante (fuera "No refiere…",
  ": no.", "no aplica" — regex IRRELEVANT_LINE), secciones separadas con color
  (lesiones rojo, salud ámbar, medicación azul, alergias rojo) + Medicación.
- **Pestaña Anamnesis**: por defecto VISTA de solo lectura por secciones de
  color (V_COLORS) — datos, cuerpo+objetivo, entreno, dieta, lesiones (rojo),
  clínica, medicación, suplementos, vida; botón "Editar datos" abre el
  formulario clásico (el PATCH/audit no cambia).
- **Portal**: eliminado "Añadir serie" (las series objetivo ya vienen del plan;
  borrar sí se puede); manifest PWA name="DQR · Assessories", short_name="DQR";
  iconos regenerados (DQR grande + "assessories" naranja debajo) con
  gen-icons.mjs (scratchpad).
- **Verificación**: backtest 1529 OK · 0 fallos; pytest verde; 8 harnesses
  verdes (anamnesis-test ampliado: vista→Editar datos; editor-test cubre la
  proporcionalidad); captura visual de la pestaña Anamnesis nueva OK.

## 10.f Tramo 2026-07-07 (5ª parte) — Auditoría exhaustiva a 0 fallos

Barrido total: 3 agentes de auditoría estática (coach FE / portal FE+BE /
backend) + un E2E NUEVO contra servidor real (uvicorn+Postgres, IA fake,
navegador: login→anamnesis→generar→editar→PDF→objetivo→portal→series) en
`scratchpad/e2e-full.mjs` + `qa-server.py` + `e2e-proxy.mjs` → 27/27 checks.
Arreglos aplicados (todos verificados):

**Críticos**
- `plan_activation.activate_plan` ahora supersede TODOS los planes publicados
  (también de otros meses): antes, tras cambiar objetivo y generar el mes+1
  con período abierto, el portal/PDF servían el plan del MES VIEJO ~14 días.
  Backtest nuevo invariante: "un único plan ACTIVO tras regenerar".
- Sidebar "Dieta"/estado no se resincronizaba tras generar/adaptar/editar:
  `planDiet` depende ahora del objeto `client` (cambia en cada load) y el
  panel llama `onClientChanged` en generate/adapt/activateLegacy.

**Medios**
- Fecha del portal en zona Europe/Madrid (`portal.today_local()`): entre
  las 00:00-02:00 el servidor UTC descuadraba días restantes/cierre/semana.
- Emails: adaptar el plan ya NO reenvía "¡Bienvenido!" — usa
  `plan_republished`; `coach_at_risk` enlazaba a /clients/ (404) → /clientes/;
  `closing_due` (recordatorio de cierre día 14) por fin cableado en
  `run_daily_maintenance` (idempotente por día).
- Regenerar plan tras una revisión sella `applied_adjustments` (la IA ya
  incorporó los ajustes): se apaga la alerta fantasma "sin adaptar" y
  "Adaptar" no puede aplicar los mismos ajustes dos veces (409).
- Colores del peso según objetivo en Feedback/Seguimiento/Resumen
  (muscle_gain: subir = bueno); antes señal invertida.
- `compute_period_summary`: comparación con períodos anteriores en UNA
  consulta (join) en vez de 2×N.
- Cierre quincenal del portal: validación de rangos en el móvil (peso 30-300,
  perímetros 20-250, comidas libres 0-50) con aviso del campo concreto.
- Portal con revisión enviada (período cerrado): Entreno y Diario muestran
  "registro en pausa" y no aceptan datos que el backend rechazaría (409).

**Leves**
- needsDownload coherente: se limpia al enviar por WhatsApp/generar/adaptar y
  se activa también al editar los "Cambios aplicados".
- "Regenerar enlace del portal" accesible (estado/diálogo estaban muertos).
- Textos obsoletos ("publicarlo", "créalo en Planificación", hint de
  Feedback, docstrings) actualizados al flujo sin botón Publicar.
- `household` ("1 taza (80 g)") también se reescala (back+front).
- Detalle "Carbohidratos: X→Y" recuadrado cuando kcal+carbs se tocan a la vez.
- `week_weight_hint_kg` añadido al schema TodayExercise (espejo types.ts);
  `_session_for_today` aplica el factor de semana (coherencia de servicio).
- Peso actual con la misma fuente/fallback en Resumen e Historial; nº de
  revisión unificado en ClientsPage; aria-labels; guardas de división por 0;
  borrador del cierre se recarga al cambiar de período; migración 0008
  (published_at/strict_free_meal_enabled/option_feedback_json idempotentes);
  state_machine admite active→review_pending (cierre directo).

**Verificación final**: E2E real 27/27 · backtest 1530 OK/0 fallos · pytest
verde · 8 harnesses verdes · tsc/vite OK. QA server E2E reutilizable:
`qa-server.py` (patches IA del backtest + admin DQR/e2e-password-123).

## 10.g Tramo 2026-07-07 (6ª parte) — Premium + clasificador clínico + super-auditoría

- **Clasificador clínico compartido** (lib/clinical.ts): arregla el bug de las
  capturas (marcaba en rojo "Sin lesión de hombro", "Sin cirugías",
  "Embarazos: 0"). Quita el guion antes de evaluar; negación al inicio gana;
  valores nulos (":" interno también se limpia); "ya resuelta" no crítico pero
  "no resuelta" sí; "suplement" FUERA de crítico (creatina no va en rojo).
  Usado en Puntos importantes y Notas clínicas, coherentes.
- **Números corruptos (36M kcal)**: topes en editor (kcal<=8000, macro<=800,
  baseline saneado, inputs con max) + _sanitize_nutrition en update_plan.
- **IA con contexto clínico fuerte** (generator._clinical_block +
  ClientContext.clinical_notes): lesiones/patologías/medicación/suplementos
  SIEMPRE explícitos con reglas duras; prompt de comidas también.
- **Título por MES real** ("Planificación · Julio de 2026") + "Mes N de
  asesoría"; sidebar Dieta con nº comidas/día. generate devuelve las fechas.
- **MemoDetails**: desplegables con memoria (localStorage), animación grid,
  no persiste en montaje (lo crítico se auto-expande).
- **Diseño premium** (index.css): paleta con relieve, sombras por capas, textura
  de papel, botones con gradiente/halo, pestañas animadas, Stat/SectionTitle
  con relieve. Reparto por comida en tabla; equivalencias+household reescalados.
- **Verificación**: E2E real 33/33 · 0 fallos; backtest 1530 OK/0; pytest verde;
  8 harnesses verdes; agente de auditoría con 4 hallazgos, los 4 corregidos.

## 10.h Tramo 2026-07-08 — Cálculo de dieta directo (déficit % + % por macro) + móvil + orden + IA por evidencia

Objetivo: que el coach vea y edite el **cálculo** de la dieta sin números
complejos, con el estilo de MyFitnessPal, y una web más ordenada y móvil.

- **Déficit/superávit % editable** (`lib/nutritionTargets.ts`): `signedDeficitPct`
  (kcal↔TDEE), `deficitLabel` ("Déficit del 20%"), `kcalFromDeficit`,
  `deficitOptions(current?)` (mantenimiento + 5→50% ambos lados; si el % real no
  es múltiplo de 5 —p. ej. un plan IA con +8%— **inyecta** su valor exacto para
  que el desplegable no se desincronice), `deficitSelectValue` (valor del select
  coherente con la etiqueta, acotado a ±95). En vista (`ClientPlanPanel`) chip
  naranja "Déficit del X% · sobre tu gasto (TDEE)"; en editor (`ClientPlanEditor`)
  desplegable de 5% que recalcula kcal y rehace macros óptimos por objetivo.
- **% por macro estilo MyFitnessPal**: `macroPct` (% de cada macro sobre las
  CALORÍAS OBJETIVO, no sobre la suma real → puede salir 95/105% y avisar),
  `gramsFromPct`. En vista, badge azul con el % junto a cada macro. En editor,
  cada macro tiene **gramos + %** editables; `setMacroPct` fija los gramos por %
  sin tocar el objetivo (permite descuadre); badge total verde/ámbar y botón
  **"Cuadrar a 100%"** (`cuadrar`) que rellena carbos con el resto y, si proteína
  +grasa ya se pasan, baja P y G en proporción — **siempre** cuadra, nunca no-op.
- **Tolerancia única** `MACRO_TOTAL_TOLERANCE = 2` (editor y vista) para no dar
  dos veredictos con el redondeo (30+40+31 = 101% es correcto, no alarma).
- **"Total día"** de la tabla suma las **filas reales** de comidas (siempre cuadra
  con lo que se ve, con plan generado o tras editar; antes ponía el objetivo).
- **Editor sin cifras cortadas**: "Calorías objetivo" en su fila y los 3 macros en
  3 columnas anchas (los gramos de 3 dígitos ya no se recortan).
- **Repaso móvil** (`ClientProfilePage`): grid con orden móvil identidad → Diario
  → **pestañas** → contenido → extras (antes había que bajar toda la barra
  lateral); pestañas **sticky**; sin overflow horizontal en ninguna vista
  (clientes/plan/resumen/dashboard a 390px → scrollW == clientW).
- **IA por evidencia** (`generator.py`): bloque de entrenamiento basado en
  evidencia (volumen 10-20 series/grupo/sem — Schoenfeld/Krieger, frecuencia ≥2,
  RIR 1-3, selección por biomecánica/ROM, sobrecarga progresiva, ajustes por
  objetivo y descansos) + nota de dieta razonada. Solo texto del prompt: no toca
  el contrato JSON (verificado con backtest y E2E, generación intacta).
- **Auditoría 7-8 jul** (agente): 7 hallazgos; corregidos los 3 MEDIO (select sin
  selección fuera de ±50 → `deficitOptions`+`deficitSelectValue`; "Cuadrar" no-op
  → `cuadrar` reproporciona; kcal del total inconsistente → suma de filas) y 3
  LEVE (dos tolerancias → una; etiqueta vs desplegable → coherentes; `sub`% sin
  target → gateado). El nº7 (barra sticky bajo la campana) sin conflicto real.
- **Verificación**: tsc/vite OK; **E2E real 48/48** (33 + 15 nuevos de déficit/
  macro%) · 0 errores JS; **móvil sin overflow**; **backtest 1530 OK/0**; pytest
  sin fallos NUEVOS (los 11 rojos son previos: fixtures IA con JSON scripted +
  push, idénticos con `generator.py` a HEAD — verificado por stash).

## 10.i Tramo 2026-07-08 (2ª) — Backups automáticos + progreso del cliente + login del portal

Tres mejoras pedidas tras la del cálculo de dieta:

- **Backups automáticos** (`deploy/backup.sh`, `restore.sh`, `install-backups.sh`):
  copia diaria (cron 04:00) de la BD (pg_dump comprimido, con chequeo de sanidad
  y rotación de 14) y de `./storage` (fotos/PDFs), a `/root/fitness-backups`
  (fuera del repo). `install-vps.sh` lo programa solo en despliegues nuevos.
  Restauración guiada y protegida. Round-trip verificado en local.
- **Portal · "Mi progreso"** (`GET /p/{token}/progress` + `/photos/{id}` +
  `PortalProgress.tsx`, nueva pestaña): el cliente ve su peso (gráfica), fuerza
  (1RM primera vs mejor), medidas y adherencia por período, y sus fotos antes/
  ahora. Deriva de lo que ya registra; seguro con datos vacíos.
- **Login del portal + email de acceso** (usuario = email + contraseña):
  - Modelo: `clients.portal_password_hash`, `portal_access_sent_at` (mig. 0009).
  - Al subir el coach la anamnesis (`POST /clients/{id}/documents`) se genera la
    contraseña y se envía por email el acceso (`portal_access` template) UNA vez
    (`portal_access_sent_at`). Botón del coach "Reenviar acceso" (regenera y
    devuelve la clave por si el email no llega). `send_portal_access` en
    `services/portal_access.py`.
  - Login `POST /api/p/login` {email, password} → devuelve el `portal_token` (el
    mecanismo interno). Rate-limit 15/min, error genérico, email case-insensitive.
  - Front: ruta `/portal` → `PortalLogin` (recordarme = guarda token+email en
    localStorage y autoentra; logout en el portal). El enlace por token
    (`/p/:token`) sigue funcionando en paralelo (retrocompat, WhatsApp).
- **Verificación**: login backend 8/8 casos (ok, clave mala, email inexistente,
  sin acceso, mayúsculas, reenvío invalida la anterior); auto-trigger fija hash+
  fecha y no reenvía en re-subida; front 9/9 (login, error, redirección,
  recordarme, autoentrada, logout) · 0 errores JS; plantilla de email OK;
  E2E 50/50; mig. 0009 idempotente; pytest sin fallos nuevos.

## 10.j Tramo 2026-07-08 (3ª) — Gran auditoría: seguridad clínica, evidencia, integridad y hardening

Cuatro auditores en paralelo (entrenamiento, nutrición, workflow, seguridad).
Arreglados los reales (críticos + alto valor); verificado todo junto.

**Seguridad del cliente (CRÍTICO):**
- **Lesiones → contraindicaciones REALES** (`services/injuries.py` nuevo): las
  lesiones de la anamnesis (texto libre, respetando negaciones/"resuelta") se
  mapean a etiquetas articulares (`hombro`, `lumbar`, `rodilla`…). Antes
  `client_contraindications=set()` fijo en 3 sitios → el filtro y el guardrail
  NUNCA excluían por lesión. Ahora un cliente con hernia lumbar no recibe
  sentadilla/peso muerto/remo (22 ejercicios excluidos, verificado). Cableado en
  `clients.py` (filtro + ClientContext) y `swap.py` (alternativas + rechazo duro
  del destino contraindicado).
- **Guardrail de alérgenos** (`guardrails.check_meal_options`): comprueba los
  ingredientes de cada comida contra `food_allergies` (con sinónimos: lactosa→
  leche/yogur/queso…, gluten→trigo/pan…, frutos secos, marisco…) → violación
  prominente. Antes NADA revisaba los ingredientes (solo el prompt).
- **Suelo calórico en `energy_targets`** (`metrics.py`): nunca por debajo de
  BMR/1600♂/1400♀. Antes una mujer ligera sedentaria en fat_loss recibía un
  target < BMR que el guardrail rechazaba → NO se podía generar su plan.

**Integridad de datos:**
- **`periods`: índice único parcial** (un solo período abierto por cliente) +
  `UNIQUE(client_id, period_index)` (migración 0010 con dedupe previo).
  `ensure_open_period` usa savepoint y reutiliza el período si hay carrera.
- **Fechas a hora local** (Europe/Madrid) en períodos, semana del mesociclo,
  plato del día y `goal_started_on` (antes UTC → descuadres a medianoche).

**Calidad por evidencia:**
- Desplegable de déficit acotado a **≤30% / superávit ≤15%** (límites de los
  guardrails) + aviso si se supera; el prompt de comidas ya no prohíbe los
  alimentos que **gustan** al cliente; piso de volumen (aviso <6 series/grupo);
  proteína reconciliada (los macros nunca declaran kcal que no cumplen);
  `macroPct` con calorías vacías = 0% (no 60000%).

**Hardening (seguridad del código nuevo):**
- Rate-limit **por IP real** (Caddy `X-Real-IP` + `app/ratelimit.py`) en vez de
  un cubo global; login en **tiempo constante** (anti-enumeración); acceso al
  portal solo se sella si el email SALIÓ (reintenta si falla); email en
  minúsculas al crear; `first_name` sin `IndexError`; escape HTML en el email;
  backup con `KEEP`≥1, `chmod 700`, y snapshot previo a `restore`.
- Alerta "objetivo cambiado sin regenerar" (`objetivo cliente ≠ plan activo`).

**Verificación:** backend imports OK; **backtest 1530/0**; **E2E 51/51 · 0
errores JS**; pytest sin fallos nuevos; migración 0010 idempotente; filtro de
lesión y guardrail de alérgenos probados; login y unicidad de email OK.

## 10.k Tramo 2026-07-08 (4ª) — Actividad diaria (NEAT), diabetes/tiroides y calidad de PDFs/textos IA

Tres frentes pedidos por DQ: (A) nivel de actividad DIARIA entendible en la
anamnesis y que afine el TDEE; (B) pautas específicas de diabetes y tiroides en
la generación IA; (C) que PDFs (anamnesi/planificación/revisión) y textos IA
(revisión, planificación, feedback, WhatsApp, email del portal) queden bien
escritos, con tono profesional/serio, sin cortar párrafos/tablas y limpios.

**A. Nivel de actividad diaria (NEAT) → TDEE más real:**
- `clients.daily_activity_level` (`sedentary|light|active|very_active`) — migración
  `0011` idempotente. Antes el TDEE salía SOLO de los días de entreno; ahora
  separa la actividad de la OCUPACIÓN (NEAT) del ejercicio.
- `services/metrics.py`: `NEAT_FACTORS` (1.25/1.40/1.55/1.70) + `activity_factor()`
  = base NEAT + 0.03 × días de entreno (tope 1.95). `tdee()` y `energy_targets()`
  aceptan `daily_activity`. Si es nulo, cae al mapeo por días de siempre (retro-
  compatible; el suelo calórico sigue vigente).
- Anamnesis: `AnamnesisSubmit`/`ClientUpdate`/`ClientOut` + extracción IA
  (`extraction.py`) + `ClientAnamnesisTab.tsx` (desplegable con descripciones
  entendibles: "Sedentaria (oficina)"…, y fila en la ficha) + `format.ts`
  (`ACTIVITY_LABEL`) + `types.ts`.

**B. Diabetes y tiroides (IA):**
- `services/ai/generator._pathology_rules(clinical_notes)` — normaliza el texto
  (sin tildes) y detecta diabetes (`diabet`, `glucemia`, `insulina`, `metformina`,
  `hba1c`, `prediabet`, `resistencia a la insulina`), hipotiroidismo (`hipotiroid`,
  `levotirox`, `eutirox`, `tiroides`) e hipertiroidismo. Añade directivas concretas
  al bloque clínico del prompt: diabetes → carbohidratos de IG bajo, repartidos y
  acompañados de proteína/grasa/fibra, sin refinados, sin ayunos; hipotiroidismo →
  déficit conservador, proteína alta, nota de levotiroxina en ayunas separada de
  café/calcio/hierro/soja, micronutrientes; hipertiroidismo → sin déficits
  agresivos. Integrado en `_clinical_block` (se suma a lesiones/medicación que ya
  iban SIEMPRE).

**C. Calidad de PDFs y textos IA** (auditoría a nivel de código + `document.xml`):
- **Recorte de texto en cajas/tablas del PDF (era pérdida de contenido):** una
  tabla de UNA fila con `w:cantSplit` que superaba el alto de página **recortaba**
  el sobrante (no paginaba). `word_base.open_box`/`info_box` ahora **NO** marcan
  `cantSplit` por defecto (se parten conservando el sombreado); `clean_table` gana
  `cant_split_rows`/`keep_together`/`font_pt`. En `plan_doc`/`feedback_doc` las
  tablas potencialmente altas (Alimentos por grupos, Cambios del plan, Estructura
  diaria, semanal, progresión, ejercicios, cuadrícula de cambios) paginan sin
  recortar.
- **Cabecera repetida:** `clean_table` marca la fila 0 como `w:tblHeader` → si la
  tabla se parte entre páginas, la cabecera de color reaparece (antes: 0 tablas la
  repetían; filas huérfanas sin encabezado). Tabla semanal a `Pt(8)` para que 8
  columnas no desborden.
- **Tono profesional/serio + sin emojis:** `prompts.SYSTEM_BASE` y `feedback._SYSTEM`
  refuerzan castellano cuidado, frases completas (no cortadas), sin emojis ni
  símbolos decorativos (corrompen PDF/WhatsApp) ni exclamaciones en cadena. Saneo
  DEFENSIVO de emojis en la salida de feedback (`feedback._clean_text`) porque va
  verbatim a PDF y WhatsApp.
- **Emails:** escape HTML del texto libre del cliente/coach + `\n`→`<br>` en
  `email_templates` (`coach_change_request`, `plan_republished`, `coach_at_risk`) y
  del nombre en todas las plantillas de cliente (antes un `<`/`&` o un mensaje de
  varias líneas rompía el maquetado). Limpieza del no-op de color en la pareja de
  fotos antes/después (gris real) + `cantSplit` para que rótulo y foto no se
  separen.

**Verificación:** backend imports OK; `activity_factor`/`energy_targets` con NEAT
y `_pathology_rules` probados; **PDF de estrés** (6 comidas, equivalencias grandes,
tabla semanal 8 col, cuadrículas de texto largo) → docx válido, `tblHeader` presente
y `cantSplit` reducido (ya no recorta); saneo de emojis y escape de emails probados;
frontend `tsc -b` + `vite build` OK; **backtest 1530/0**; **pytest 97 pasan, 11 fallos
PRE-EXISTENTES idénticos con y sin mis cambios** (fixtures IA scripted + timing de
push, no relacionados); migración 0011 idempotente aplicada a head.

## 10.l Tramo 2026-07-08 (5ª) — Edición manual de nutrición íntegra + suite a 108/108

Dos frentes: (A) que TODO el ajuste manual de la dieta esté relacionado entre sí
de forma coherente (como la IA); (B) dejar la batería de tests en verde.

**A. Edición manual coherente (`ClientPlanEditor.tsx` + `nutritionTargets.ts`):**
- **Bug del dígito pegado (0/1/3):** los inputs de kcal/macros/% saltaban a un
  valor al borrar (el recálculo en cadena reescribía el campo a media edición).
  Nuevo `NumberInput` con estado local `raw`: mientras editas muestra EXACTAMENTE
  lo que tecleas (incluido vacío) y solo vuelve a seguir el modelo al salir del
  campo (blur). Borrar deja el campo vacío; ya no hay que "hacer movimientos de
  más". Usado en `Num` y `MacroField`.
- **Las kcal son el ANCLA (igual que la IA):** al editar los GRAMOS o el % de un
  macro se MANTIENEN las calorías objetivo y un "colchón" (carbohidratos, o grasa
  si editas carbohidratos) absorbe la diferencia, preservando la proteína. Antes
  editar % no tocaba nada más y el total se iba al 95/105% (incoherente). Nuevo
  `redistributeMacro(target, cur, key, grams)` en `nutritionTargets.ts`. Editar
  las kcal sigue escalando el mix; siempre se reescalan comidas y gramos del banco.
- **"Cuadrar por objetivo":** el botón de cuadrar ahora rehace el reparto según la
  EVIDENCIA del objetivo del cliente (proteína/grasa por kg, carbohidratos el
  resto) — `macrosForKcal(goal, weight, target)` — en vez de combinaciones
  ilógicas. Siempre disponible; sin objetivo/peso, rellena con carbohidratos.
- Verificado con 22 comprobaciones de coherencia (kcal fija, total 100%, colchón
  nunca negativo, split por objetivo válido para los 5 objetivos) + simulación del
  input que prueba que el viejo se quedaba en "0" y el nuevo llega a vacío.

**B. Suite de tests a 108/108 (antes 97 pasaban, 11 fallaban):**
- **Fixtures obsoletas (10 tests):** `_flexible_meals_json` generaba 7 opciones por
  slot pero el esquema exige 1-4 (objetivo 3). `tests/test_ai_service.py` "ABCDEFG"
  → "ABC"; asserts que fijaban `== 7` → `== 3` en `test_portal.py` y
  `test_integration_a3.py`. No se tocaron guardrails ni esquema (son estrictos a
  propósito).
- **Fecha fija (1 test):** `test_push` fijaba `datetime(2026,7,3,...)` cuando la
  fixture es relativa a `date.today()`. Ahora deriva el "ahora" de hoy.
- **BUG REAL de producción encontrado al pasar los tests:** el endpoint POST
  `/clients/{id}/periods` (`create_period`) insertaba un período abierto sin
  comprobar si ya había otro → violaba `uq_period_one_open` (índice único de un
  solo período abierto, mig. 0010) con un **500**. Como publicar el plan ya abre
  el período 1 solo, el endpoint ahora es IDEMPOTENTE: si hay uno abierto lo
  devuelve. Los tests que retro-fechaban el período vía este endpoint ahora lo
  hacen en la BD (helper `_backdate_open_period`).

**Verificación:** pytest **108/108**; **backtest 1530/0**; frontend `tsc -b` +
`vite build` OK; 22 checks de coherencia de edición + simulación del input.

## 10.m Tramo 2026-07-08 (6ª) — Auditoría profunda: 4 agentes + web real (Playwright)

DQ seguía encontrando fallos "solo usando la web". Se lanzaron 4 auditores en
paralelo (coach front, portal front, backend API, coherencia de flujo/docs) y
además se CONDUJO la web de verdad con Playwright (login, editor, portal). ~22
bugs REALES corregidos, con tests de regresión.

**Crashes (500 / la web "se rompe"):**
- Borrado RGPD de un cliente con suscripción push → 500 (faltaba borrar
  `push_subscriptions`, FK NOT NULL). Corregido en `clients.delete_client`.
- Vista de seguimiento del coach → 500 si "pasos" llevaba puntos de miles
  ('1.234.567'): `_steps_num` ahora es a prueba de fallos y entiende los miles.
- `create_period`: 500 por concurrencia y "huérfano" un período cerrado sin
  feedback → ahora rechaza (409) si hay período abierto O cerrado + savepoint.
- Job diario abortaba TODAS las transiciones si un cliente tenía el nombre en
  blanco (`full_name.split()[0]`) → helper `_first_name` robusto (y en 2 sitios más).

**Seguridad / coherencia clínica:**
- **Alérgeno que llegaba al cliente:** la IA podía colar un alimento con alergia
  y no se bloqueaba, ni se filtraba del PDF, ni lo veía el coach. Ahora el banco
  se SANEA en generación (`_strip_allergens_from_bank` + `guardrails.option_allergen`
  /`food_allergen`): se retira la opción/alimento con alérgeno si queda alternativa
  segura; si no, el flag ⚠ ALÉRGENO queda para el coach.
- **TDEE/déficit mostrado incoherente:** se persistía el `tdee_kcal` que ECHABA la
  IA, no el real del backend → el PDF/panel podían decir "Mantenimiento 0%" en un
  plan de pérdida. Ahora se fuerza `nutrition["tdee_kcal"] = round(et.tdee)`.
- Etiqueta del PDF ("Superávit/Déficit") ahora la manda el SIGNO del delta, no el
  objetivo (evita "Superávit +-150 kcal"). Barra de "adherencia entreno" del PDF
  reetiquetada a "Registro" (era el ratio de registro, no de entreno).
- `adapt_plan`: aplicaba el PRIMER número a TODOS los macros nombrados ("subir P a
  180 y bajar grasa a 55" ponía 180 en ambos) → ahora parsea por cláusula; y honra
  los carbohidratos si el coach los fija explícitamente.
- Proteína de `injury_recovery` alineada front (2.25) ↔ back.

**Portal del cliente (lo que sufre el cliente):**
- **Bloqueo de login:** un token recordado ya caducado atrapaba al cliente en una
  pantalla de error sin salida → botón "Volver a iniciar sesión" que limpia la
  sesión.
- **Pérdida del último dato al salir:** los autosaves usaban `fetch` sin
  `keepalive` → al mandar la app a segundo plano se perdía lo tecleado. Ahora los
  guardados JSON llevan `keepalive` (las fotos FormData no).
- **Diario en pausa que engañaba:** con el período cerrado el diario aceptaba
  escritura y decía "se guarda automáticamente" pero descartaba todo → ahora no
  admite cambios ni muestra ese texto.
- **Cierre** mostraba la cuenta atrás "se desbloquea en 2 semanas" tras enviar la
  revisión (contradecía a las otras pestañas) → estado propio "Revisión enviada".
- **Progreso** pedía registrar un peso ya registrado con 1 solo dato → vacío solo
  si NO hay ningún dato.
- **Entreno**: borrar la última serie dejaba el ejercicio irrecuperable (no hay
  "añadir serie") → siempre queda al menos una fila.

**Coach (edición):**
- Botón "Enviar plan por WhatsApp" se abría tras un `await` → lo bloqueaba
  Safari/iOS y parecía no hacer nada → ahora abre la pestaña dentro del gesto.
- Calorías vacías/0 dejaban un plan incoherente que se podía guardar → "Guardar"
  se deshabilita y el déficit muestra "—".
- Cambiar de pestaña con cambios de anamnesis sin guardar los perdía → aviso de
  confirmación. Cliente que no carga → antes spinner infinito, ahora mensaje con
  vuelta a Clientes. Toast verde-rojo confuso al guardar corregido. Campos
  numéricos de entreno ya no persisten `null`.

**Verificación:** pytest **113/113** (108 + 5 de regresión de la auditoría);
**backtest 1530/0**; frontend `tsc -b` + `vite build` OK; editor conducido con
Playwright (borrar kcal → "Guardar" deshabilitado, sin errores de consola);
22 checks de coherencia de edición.

## 10.n Tramo 2026-07-08 (7ª) — Correo de acceso al portal + refresco de 3 s sin parpadeo

Dos cosas que DQ pidió tras usar la web:

**1) El correo de acceso al portal no llegaba.** El flujo del código ya era
correcto (al subir la anamnesis se autoenvía el acceso — usuario = email +
contraseña + enlace — una sola vez; `portal_access.send_portal_access`). El
problema era de CONFIGURACIÓN de producción: `deploy/install-vps.sh` dejaba
`EMAILS_ENABLED=false` porque no había SMTP real. Ahora:
- El instalador pregunta la **contraseña de aplicación de Gmail** y, si se da,
  configura el envío REAL desde **david.dqr57@gmail.com** (`SMTP_HOST/PORT/USER/
  PASS/FROM` + `EMAILS_ENABLED=true`). Sin clave, avisa y los correos quedan
  desactivados (se puede reejecutar el instalador para activarlos).
- `config.py`: remitente por defecto `David Quiceno <david.dqr57@gmail.com>` y
  `emails_enabled=True` por defecto. `.env.example` documenta que `SMTP_PASS` es
  una contraseña de aplicación de Google (16 letras), NO la contraseña normal.
- **La contraseña de aplicación es un SECRETO: no se commitea.** DQ la genera en
  Cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de
  aplicaciones, y la mete al instalar (o en el `.env` del VPS). Sin ella el correo
  no sale (queda `disabled`).
- **El coach ahora SE ENTERA del resultado.** Al subir la anamnesis y al pulsar
  "Reenviar acceso", `ClientDocuments.tsx` muestra un aviso claro para CADA estado
  (`sent` / `disabled` / `failed` / `error` / `no_email`) con la acción de
  reenvío; antes `failed`/`error`/`no_email` se tragaban en silencio. En el
  endpoint de subida, un fallo de envío marca `access_status="error"` (antes se
  silenciaba). Verificado E2E: subir anamnesis → correo desde David con
  usuario+contraseña+enlace y `portal_access_sent_at` sellado; reenvío `sent` y
  `disabled` (muestra la clave para dictársela al cliente).

**2) Refresco de 3 s sin parpadeo ni desincronización.** El polling reemplazaba
el objeto entero cada 3 s aunque nada hubiera cambiado → re-render y re-fetch
inútiles (la "Dieta" y el aviso de feedback se recargaban solos cada 3 s). Ahora:
- Helper `keepIfSame`/`sameData` en `lib/api.ts`: los setState del polling solo
  cambian la referencia si los datos cambiaron DE VERDAD. Aplicado en panel,
  clientes, ficha, seguimiento y campana → sin parpadeo.
- En la ficha, la recarga por ACCIÓN del coach (editar/adaptar/generar plan,
  guardar anamnesis, subir doc) usa `reload` (sube un contador `reloadKey`) para
  re-sincronizar "Dieta"/feedback aunque la fila del cliente no cambie; el
  polling de 3 s NO sube ese contador (no re-consulta si nada cambió).
- El polling de la ficha **se PAUSA mientras se edita la anamnesis** (borrador
  sin guardar): así un refresco a media edición no puede despistar ni desincronizar.

**Verificación:** pytest **113/113**; frontend `tsc -b` + `vite build` OK; envío
de correo conducido E2E con transporte simulado (remitente David, contenido y
enlace correctos, sellado y reenvío).

## 10.o Tramo 2026-07-08 (8ª) — Acceso al portal enviado AL CREAR el cliente

DQ pidió que, al dar de alta un cliente (nombre + email + teléfono), se le mande
automáticamente su acceso al portal por email, y que el modal "Cliente creado" lo
refleje. Antes el autoenvío solo ocurría al registrar la anamnesis.

- **`create_client`** (`routers/clients.py`): tras crear y confirmar el cliente,
  llama a `send_portal_access` en su PROPIO try/except (rollback → `error`); el
  alta NUNCA se bloquea si el correo falla o está desactivado. Devuelve el estado
  en `ClientCreatedOut.portal_access` (nuevo campo del schema).
- Como `portal_access_sent_at` solo se sella si el correo SALE, el autoenvío al
  subir la anamnesis sigue de **fallback** (reintenta si al crear no salió) y no
  duplica el correo si ya salió.
- **Modal "Cliente creado"** (`ClientsPage.tsx`): guarda la respuesta completa y
  muestra `<PortalAccessResult>` (verde "enviado a {email}" / ámbar-rojo si
  desactivado/falló/sin email) + botón **"Reenviar correo"** que, si el correo no
  sale, revela la contraseña para dársela a mano. Se mantiene el enlace de la
  anamnesis por si el coach quiere mandarlo también por WhatsApp.

**Verificación:** pytest **113/113**; `tsc -b` + `vite build` OK; E2E: al crear
un cliente sale el correo desde David (usuario+contraseña+enlace+CTA) y se sella
`portal_access_sent_at`; la subida posterior de anamnesis NO reenvía (0 correos
extra); con correo desactivado el alta sigue OK (`disabled`, sin sellar) y con
SMTP caído el alta sigue OK (`failed`); email duplicado → 409.

## 10.p Tramo 2026-07-16 (8ª) — Stripe: duración contratada + guía STRIPE.md

El coach vende cada plan (Start/Full/Pro) en 3 duraciones: **mensual,
trimestral y semestral** → 3 × 3 = **9 precios de Stripe**.

- **`.env`**: `STRIPE_PRICE_{START|FULL|PRO}_{1M|3M|6M}` (sustituyen a los 3
  `STRIPE_PRICE_*` antiguos). `config.stripe_price_for(tier, period)`;
  `main.py` avisa al arrancar de CUÁL de los 9 falta.
- **`clients.billing_period`** ("1m"|"3m"|"6m", default "1m") — migración
  **0019** (idempotente; la 0018 la ocupó el código de descuento de Recursos).
  En `ClientCreate/Update/Out` (`BillingPeriod` en entities.py y types.ts).
- **Checkout**: `create_checkout_url(db, tier, period, client=…)` valida ambos
  y mete `billing_period` en la metadata; el webhook la guarda en la ficha
  (alta manual Y self-serve; la duración pagada de verdad manda).
- **`/planes`**: conmutador Mensual/Trimestral/Semestral común a las 3
  tarjetas (`period` en `POST /api/public/checkout`).
- **Alta manual**: selector de duración en el modal; `GET /api/pay/{token}`
  cobra el plan × duración de la ficha; fila **"Duración"** editable en el
  perfil (patrón PlanRow) y el botón verde indica qué cobra.
- **Tests**: `test_stripe.py` cubre `billing_period` en metadata (3/3 OK);
  suite completa comparada contra `main` en worktree → mismos fallos
  preexistentes, 0 regresiones. `tsc` + `vite build` OK.
- **`STRIPE.md`** (raíz): guía operativa completa para el coach (cuenta,
  9 precios, webhook, .env del VPS, pruebas con tarjeta 4242, paso a live,
  problemas típicos). Verificada afirmación-por-afirmación contra el código
  con un workflow de 5 agentes adversariales (53 checks, 6 correcciones).
  PENDIENTE del usuario: crear productos/precios en Stripe y rellenar el .env
  del VPS (estaba en ello guiado por el chat).

## 10.q Tramo 2026-07-19 — Landing de Instagram + registro self-serve completo

El link del perfil de Instagram de David lleva TODO el embudo: landing → planes
→ datos → email con anamnesis (PDF editable) → pago Stripe → ingesta automática.

- **Landing pública `/dq`** (`pages/LinksPage.tsx`): foto del coach de fondo
  (con velo para legibilidad; sin foto, degradado de marca), logo/nombre/tagline
  y 2 accesos: "Trabaja conmigo" → `/planes` y "Suplementos ESN" (tienda del
  partner) + chip del código de descuento (toca para copiar). Datos de
  `GET /api/public/landing` (routers/public_site.py, rate-limited).
- **Config de la landing** en `brand_config` (migración **0020**):
  `links_photo_path` (POST /api/brand/links-photo), `partner_store_url`,
  `partner_discount_code` (validados en BrandConfigIn). Se gestiona en
  **Recursos → pestaña "Página de enlaces"** (`LinksPageManager` en
  RecursosPage): copiar el enlace /dq, subir la foto y guardar tienda+código.
- **Registro self-serve ANTES del pago** (`POST /api/public/register`):
  en `/planes`, al elegir plan+duración se abre un mini-formulario (nombre,
  email, teléfono) → crea el cliente (payment pending, token firmado, evento
  `client_created by:self`), envía el **email de arranque** y devuelve la URL
  de Stripe ligada al client_id (StripeError → url null y aviso suave: el
  email ya lleva su enlace de pago). Reintento con mismo email → actualiza la
  MISMA ficha; email ya pagado → 409. El webhook marca el pago (flujo alta
  manual); el alta por webhook sin registro previo sigue existiendo (fallback).
- **Anamnesis en PDF por el PROPIO cliente**: el email/WhatsApp de arranque ya
  NO enlaza al portal sino a **`/anamnesis/{token}`** (`pages/AnamnesisPage.tsx`):
  paso 1 descargar la plantilla editable (`GET /api/p/{token}/anamnesis-template`),
  paso 2 subir el PDF relleno (`POST /api/p/{token}/anamnesis-pdf`, 5/min).
  La subida usa la MISMA ingesta que el coach — `ingest_anamnesis_pdf()`
  extraída en routers/clients.py (guardar reemplazando, leer con IA, enviar
  acceso al portal 1ª vez) — y solo se permite en estado `onboarding` (después,
  409 "escribe a tu coach"). El coach ve al cliente con anamnesis lista →
  dashboard "Crear planificación" (flujo existente); en Pro el envío por
  WhatsApp sigue siendo el botón del coach.
- **Emails/WhatsApp**: `onboarding_pay_anamnesis` reescrito (botón azul
  "Rellenar mi anamnesis" → página del PDF); servicio compartido
  `services/onboarding.py::send_onboarding_email` (coach + registro público);
  `whatsapp.onboardingMessage` enlaza a /anamnesis/{token}.
- **Tests**: `tests/test_public_register.py` (registro pendiente + reuso sin
  duplicar + 409 pagado + plantilla y subida públicas + 422 no-PDF + cierre
  post-onboarding + landing). Suite completa = mismos fallos preexistentes que
  main (0 regresiones); tsc + vite build OK.
- **GOTCHA**: en un router con `@limiter.limit(...)` de slowapi NO usar
  `from __future__ import annotations` — las anotaciones-string no se resuelven
  a través del wrapper y FastAPI convierte el body Pydantic en query param
  (422 "Field required in query"). public_site.py lo documenta.

## 10.r Tramo 2026-07-19 (2ª) — Precios reales, código único, vídeos subidos, hipermedia

- **Precios REALES en /planes** (`GET /api/public/plan-prices`,
  `stripe_service.get_plan_prices` con caché 10 min): cada tarjeta muestra el
  TOTAL de la combinación elegida y, en trimestral/semestral, "sale a X €/mes".
  También en el mini-formulario. Sin Stripe → la página funciona sin precios.
- **Código de descuento ÚNICO** (brand.partner_discount_code): manda sobre el
  de cada producto en el portal (`build_resources`), sale en la landing /dq y
  en los productos de la landing. El form de producto ya no pide código (nota:
  "se configura en Página de enlaces"). Fallback: sin código global, se usa el
  del producto (compat con datos existentes).
- **Landing /dq con casi-tienda**: catálogo de productos activos (imagen, título,
  Comprar · código X) debajo de los botones. `LandingOut.products`.
- **Vídeos de ejercicios SUBIDOS como archivo** (cualquier formato habitual):
  `exercises.video_path` + `POST/DELETE /api/exercises/{id}/video`
  (storage.save_exercise_video, escritura por trozos, 300 MB máx). PRIORIDAD
  sobre video_url en portal y rutina. **Portada GLOBAL** única
  (brand.video_cover_path, `POST /api/brand/video-cover`) como miniatura de
  todos los vídeos. Migración **0021**. Recursos → Vídeos: tarjeta "Portada"
  arriba + botón "Subir vídeo"/“Cambiar”/“Quitar” por ejercicio (chip verde).
- **GOTCHA de producción**: Caddy solo proxyea `/api/*` → los archivos bajo
  `/storage/...` NO se sirven en producción. Todo lo público nuevo vive en
  `storage/media/**` montado como **StaticFiles en `/api/media`** (con soporte
  Range → el vídeo se puede adelantar). La foto de la landing pasó a media/
  (re-subir si se subió antes de este tramo); `storage.media_url()` construye
  la URL pública.
- **Hipermedia**: en la ficha del cliente, las filas Objetivo/Nivel/Entreno/
  Dieta son CLICABLES (chevron + hover) y llevan a su pestaña (Planificación /
  Anamnesis). Dashboard y alertas ya navegaban.
- **Desplegables EXCLUSIVOS** (abrir uno cierra el hermano) con el atributo
  nativo `name` de `<details>`: quincenales (Seguimiento), períodos de
  Feedback, historial, secciones de Planificación ("plan-secciones": cambios
  propuestos, plan, comidas, objetivo, archivo), planes anteriores, sesiones y
  ejercicios del editor. Ojo: 2 `open` con el mismo name → el navegador deja
  solo el primero.
- **Coherencia entreno⇄dieta**: auditada — sigue garantizada por
  `reconcile_nutrition` en PATCH de plan + adaptación (kcal ≡ macros ≡ comidas
  ≡ banco, §10.p/§10.c) y `week_weight_hint` derivado en vivo en el portal.
- Tests 7/7 (público+Stripe) · migración 0021 aplicada · tsc + vite build OK.

## 10.s Tramo 2026-07-19 (3ª) — Portal conectado a la planificación + cambios manuales explicados

- **Portal, desplegable de PRIMERA VISITA** (`WelcomeSetup` en PortalApp,
  sustituye a PushBanner): cerrado por defecto ("Configura tu portal (1 min)"),
  con 2 pasos con check: instalar como app (instrucciones según iPhone/Android,
  detecta si ya está instalada) y activar notificaciones (en iOS exige paso 1).
  Desaparece al completarse o con "No volver a mostrar" (compat con el
  `portal_push_dismissed` antiguo).
- **Productos ⇄ planificación** (`services/product_match.py`: normalización +
  sinónimos ES⇄EN — creatina/creatine, proteína/whey…):
  · Portal: sección "**De tu planificación**" (productos que corresponden a los
    suplementos pautados, chip "En tu plan") y luego "Recomendados".
  · Clic en producto → `buy_url`: patrón **/discount/CODE?redirect=** (tiendas
    Shopify como ESN) con el código YA aplicado — solo si el producto es del
    dominio de la tienda del partner; además el código se copia solo al abrir.
    En la landing /dq el código se muestra pero NO se aplica (pedido así).
  · **Alerta al coach** (alerts.py, kind `missing_products`): suplementos del
    plan activo sin producto en Recursos → "súbelo para que le salga".
- **Cambios manuales del plan DETECTADOS y explicados**
  (`services/plan_diff.py`, determinista — no depende de crédito IA):
  al guardar el editor, PATCH compara antes/después (kcal, macros, comidas,
  suplementos, ejercicios añadidos/quitados, series×reps, peso, descanso, RIR)
  y ACUMULA frases humanas en `nutrition_json.manual_changes` (se preservan
  entre ediciones; tope 20). El panel muestra el aviso con la lista y botones:
  **WhatsApp** (`manualUpdateMessage`: "he ajustado: …" + PDF) · **email**
  (`POST /plans/{id}/send-update-email`, plantilla `plan_manual_update`, adjunta
  PDF, limpia el aviso al enviarse) · descartar (`POST …/manual-changes/ack`).
- **Edición POR BLOQUE**: botón "Editar" en las cabeceras Nutrición /
  Entrenamiento / Suplementación del panel → el editor abre con **scroll y
  destello** en ese bloque (`initialFocus` en ClientPlanEditor).
- Tests nuevos `tests/test_today_features.py` (match, buy_url, diff) → 10/10
  con público+Stripe; suite completa = fallos idénticos a main (0 regresiones);
  tsc + vite build OK. Fix de auditoría: los pendientes de manual_changes se
  leen del plan ANTERIOR (una 2ª edición ya no borra los no enviados).

## 10.t Tramo 2026-07-19 (4ª) — FIX CRÍTICO de coherencia + venta y organización

- **FIX CRÍTICO (caso real: PDF con CH 800 g / grasa 0 g / +77% superávit y
  comidas que no cuadraban con los totales)**, cerrado en la RAÍZ
  (`nutrition_scale.py`):
  · `clamp_targets()` — topes FISIOLÓGICOS antes de reconciliar: proteína
    1,2–3,0 g/kg, grasa 0,6–2,0 g/kg (suelo 20 g), kcal ∈ [TDEE−30%, TDEE+15%]
    (espejo de MAX_DEFICIT/SURPLUS del editor) y siempre 1100–4500.
  · `reconcile_nutrition()` ahora también reescala el **BANCO** (recetario +
    equivalencias) por los mismos ratios que las comidas — CUALQUIER camino de
    edición deja PDF/portal/web en armonía; con datos coherentes es no-op.
  · Espejo frontend: `clampTargets()` en nutritionTargets.ts, aplicado en
    `rescaleNutrition` (el editor enseña en vivo los valores ya acotados).
  · **`clamp=False` SOLO en la generación IA pre-guardrails** (generator.py):
    los guardrails deben VER los números reales de la IA y bloquear, no
    recibirlos corregidos en silencio (lo cazó `test_pipeline_blocks_core…`).
  · Tests: `test_reconcile_edicion_extrema_queda_sana_y_coherente` (el caso del
    PDF roto: topes + comidas ≡ totales ≡ banco + idempotencia) y
    `test_reconcile_no_toca_un_plan_sano`.
- **/planes vendedora**: foto de fondo PROPIA (brand.plans_photo_path,
  migración **0022**, se sube en Recursos → Página de enlaces → "Foto de los
  planes"), precios SIEMPRE visibles en grande, chip verde "Ahorra N%"
  (trimestral/semestral vs mensual), plan Full destacado "⭐ El más elegido",
  fila de confianza (✓ personalizado ✓ revisión quincenal ✓ app ✓ pago seguro)
  y CTA "Empezar ahora".
- **Portal**: chip verde NEÓN "En tu planificación" (con glow) en los productos
  pautados; el resto bajo "Productos seleccionados por {marca}".
- **Campana de alertas AGRUPADA por ámbito** (AlertsBell.GROUPS): Arranque /
  Revisión quincenal / Planificación / Seguimiento / Objetivo / Recursos +
  "Otras" (kinds no mapeados), cabecera de grupo con color y contador.
- **Carpetas de clientes por LO QUE FALTA** (ClientsPage): Todos · Falta
  anamnesis (índigo) · Falta planificación (naranja) · Falta revisión
  (violeta) · Falta pago (verde) · Al día (azul), cada una con icono y color;
  un cliente puede estar en varias.
- **Editor**: modo **UN SOLO BLOQUE** — al entrar por el "Editar" de un bloque
  solo se ve ese bloque (con "ver plan completo" para ampliar); cabecera del
  editor sticky top-0 z-20 (ya no se descuadra con la barra de pestañas).
- Verificación: 21/21 (ai_service + features + público + Stripe); los fallos
  restantes son los preexistentes de main. tsc + vite build OK. OJO entorno de
  pruebas local: el PG temporal en /tmp muere entre runs — rearrancar antes de
  fiarse de skips masivos "Requiere PostgreSQL".

## 10.u Tramo 2026-07-19 (5ª) — Legibilidad, texto IA conciso, edición cómoda y avisos precisos

- **`/planes` legible sobre cualquier foto**: velo del fondo más marcado
  (0,62→0,8→0,9 en vez de 0,45→0,72→0,85) + halo claro (`textShadow`) en la
  cabecera — el texto se lee pase lo que pase debajo.
- **Texto de IA más conciso** (mismo contenido, menos relleno):
  `ai/generator.py` (rationale 2-3 frases cortas, flexibility_rules 1 frase por
  regla) y `ai/feedback.py` (`PlanAdjustment.reason` ≤18 palabras + párrafo
  CONCISIÓN nuevo en el system prompt: dato→conclusión, sin reformular ni
  relleno tipo "cabe señalar"). Afecta a generación, feedback y adaptación
  (los `reason` de `plan_adjustments` alimentan el `rationale` de adapt_plan).
- **Textareas largos → modal expandible** (`components/ui.tsx::ExpandableArea`,
  NUEVO, compartido): justificación/reglas de flexibilidad del editor de plan,
  "por qué" de cada cambio aplicado (panel), campos del feedback IA y de la
  Anamnesis — todos usaban una versión casi idéntica del mismo textarea de
  2-3 líneas donde no se podía leer ni editar bien; ahora al enfocarlos se abre
  un modal grande con el texto entero (Esc/click fuera/"Hecho" cierra), mismo
  value/onChange que el compacto (sin borrador aparte).
- **Aviso "planificación editada" solo si CAMBIÓ algo de verdad**: antes,
  `onSaved` del editor marcaba `needsDownload=true` SIEMPRE (aunque el coach
  entrara y guardara sin tocar nada); ahora compara `plan.{nutrition,training,
  education}` antes/después (JSON) y solo avisa si hay diferencia real; si no,
  toast "Sin cambios que guardar".
- **Fotos de progreso del portal**: el icono del aviso (antes SIEMPRE
  WhatsApp) ahora coincide con el texto — WhatsApp o Mail según el canal real
  del cliente (`directContact` = Pro).
- Verificación: `test_ai_service` + `test_today_features` + `test_public_register`
  + `test_stripe` en verde; los 2 fallos de `test_nutrition_coherence` son
  preexistentes en `main` (confirmado contra el baseline). tsc + vite build OK.

## 10.v Tramo 2026-07-20 — Videollamadas Pro, push del coach, autorrelleno de productos y push cada 3 h

- **Videollamadas quincenales (Pro), ciclo completo**:
  - Modelo `VideoCall` (`video_calls`, unique client+period_index; status
    pending|scheduled|done) + migración **`0023_video_calls_coach_push.py`**
    (también: `push_subscriptions.client_id` nullable + `is_coach`, y
    `brand_config.meet_url`).
  - `BrandConfig.meet_url` = enlace de reservas del coach (Google Calendar con
    Meet, Calendly…), editable en **Recursos → Página de enlaces** (tarjeta
    "Videollamadas (plan Pro)").
  - Endpoints en `routers/clients.py`: GET/POST `/clients/{id}/video-calls`
    (crear = propuesta enviada, idempotente), PATCH `/{call_id}` (apuntar
    fecha), POST `/{call_id}/done` y `/{call_id}/reschedule` (vuelve a
    pendiente sin fecha: el ciclo empieza de nuevo).
  - Alertas (`routers/alerts.py`, solo Pro con la última revisión cerrada):
    `video_call_schedule` (sin registro o pendiente de fecha),
    `video_call_tomorrow` (alta, reservada para mañana) y `video_call_confirm`
    (alta, fecha pasada: "¿se realizó?"). Grupo propio "Videollamada"
    (#0EA5E9, icono Video) en la campana Y en el panel diario.
  - UI del ciclo en `ClientFeedbackTab.tsx::VideoCallCycle` (por período, Pro):
    "Proponer por WhatsApp" (mensaje `videoCallMessage` CON el enlace de
    reservas si está configurado) → input de fecha "Apuntar fecha" →
    "Sí, realizada" / "No, reagendar".
  - Recordatorio al CLIENTE el día antes: dentro de `run_push_reminders`
    (solo primera franja del día, tag `dq-videollamada`). Al coach se lo
    recuerda la alerta alta + su resumen push.
- **Push al MÓVIL del COACH**: router nuevo **`routers/coach_push.py`**
  (`/api/coach/push/{public-key,subscribe,unsubscribe}`, JWT) +
  `save/remove_coach_subscription` y `send_to_coach` en `services/push.py`;
  job **`run_coach_digest`** cada 3 h (scheduler, minuto :05, horario 08–22):
  agrega `client_alerts` de todos los clientes no inactivos y envía "N
  pendientes de tus clientes" (3 líneas + "…y X más", tag `dq-coach`).
  Frontend: **`lib/coachPush.ts`** (NUEVO; registra `/sw.js`, suscribe contra
  la API del coach, flag local `coach_push_off` para apagar) + interruptor
  "Avisos en el móvil" al pie de la campana (`AlertsBell.tsx`). En iPhone
  requiere añadir la web a la pantalla de inicio (mensaje ya lo explica).
- **Autorrelleno de productos desde la URL**: endpoint
  `POST /api/resources/products/scrape` (JWT, límite 10/min, guarda SSRF:
  resuelve el host y rechaza IPs privadas/loopback; lee 400 KB máx y parsea
  OpenGraph/twitter/title). En `RecursosPage.tsx::ProductEditor`, al pegar el
  enlace (blur) se rellenan solos los campos VACÍOS (título, descripción,
  imagen) y el botón "Rellenar desde el enlace" fuerza el relleno.
- **Push del portal cada 3 h + interruptor**: `PUSH_EVERY_HOURS = 3`
  (scheduler) y TTL 3 h; campana en la cabecera del portal
  (`PortalApp.tsx::PushToggle`): activadas ↔ desactivadas. Al apagar se borra
  la suscripción (backend + navegador) y queda el flag local
  `portal_push_off` que la resuscripción automática respeta
  (`push.ts::turnPushOn/turnPushOff/pushIsOn`).
- Tests nuevos: **`tests/test_video_calls.py`** (ciclo completo de alertas de
  la videollamada, solo-Pro, upsert de suscripción del coach y saltos del
  digest). OJO stub local de pywebpush (scratchpad): `WebPushException` debe
  aceptar `response=` como la librería real o `test_push.py` falla en falso.
- Verificación: alembic 0001→0023 en BD limpia OK; suite completa con el mismo
  set de fallos preexistentes que `main` (auth fixture sin ADMIN_* env, 4 de
  `test_machines_and_word` del PR #65 por lo mismo); `test_push.py` y
  `test_video_calls.py` en verde; tsc + vite build OK.

## 11. Mapa rápido de archivos tocados en el último tramo

**Pulido §8.2 (2026-07-04)**
- `frontend/src/index.css` — paleta del portal en variables + `.portal-dark`
  (iron obsidiana) + `.portal-today-pill`.
- `frontend/src/portal/PortalApp.tsx` — clase `portal-dark` según tema; nav idle
  con `var(--p-nav-idle)`.
- `frontend/src/portal/PortalWorkout.tsx` — pill "HOY" + borde tintado en la
  sesión de hoy.
- `backend/app/models.py`, `schemas/entities.py`, `services/portal.py` —
  default `portal_theme="light"`.
- `backend/alembic/versions/0005_portal_theme_light.py` — **NUEVO** (normaliza
  'dark'→'light' una vez).
- `backend/app/routers/portal_public.py` — manifest oscuro `#0E0B10`.

**Web Push (2026-07-03)**
- `backend/app/services/push.py` — **NUEVO** (núcleo Web Push).
- `backend/app/models.py` — `PushSubscription`.
- `backend/alembic/versions/0004_push_subscriptions.py` — **NUEVO**.
- `backend/alembic/versions/0002/0003` — hechas idempotentes (BD nueva no rompía).
- `backend/app/routers/portal_public.py` — 5 endpoints push/manifest.
- `backend/app/schemas/entities.py` — `PushKeyOut`, `PushSubscribeIn`, `PushPendingOut`…
- `backend/app/services/scheduler.py` — job `push_reminders` cada 4 h.
- `backend/app/config.py`, `.env.example`, `backend/requirements.txt` (pywebpush).
- `backend/scripts/generate_vapid_keys.py`, `backend/tests/test_push.py` — **NUEVOS**.
- `frontend/public/sw.js`, `frontend/public/icons/*` — **NUEVOS**.
- `frontend/src/portal/push.ts` — **NUEVO**; `PortalApp.tsx` (banner + badge),
  `portalApi.ts`, `types.ts`, `index.html`.

**Backend (tramo anterior)**
- `app/services/adapt_plan.py` — **NUEVO** (adaptación determinista).
- `app/routers/clients.py` — endpoints tracking/history reescritos + adapt-plan + list_clients con `pending_review`.
- `app/models.py` — Period `coach_reviewed_at` (+ campos tracking previos).
- `alembic/versions/0003_coach_reviewed_at.py` — **NUEVO**.

**Frontend**
- `src/lib/api.ts` — tipos tracking/history + `adaptPlan`.
- `src/types.ts` — `ClientOut.pending_review`.
- `src/pages/ClientsPage.tsx` — badge "!".
- `src/pages/ClientProfilePage.tsx` — lee `?tab=`.
- `src/components/ClientTrackingTab.tsx` — media + quincenales desplegables + `BeforeAfter`.
- `src/components/ClientFeedbackTab.tsx` — quita fotos/regenerar/word, antes/después, copiar todo, banner adaptar.
- `src/components/ClientHistoryTab.tsx` — objetivo+restantes, medidas, % fuerza, desplegables, quita Planes.
- `src/components/ClientPlanPanel.tsx` — `adapt()` + botón "Adaptar a la revisión #N".

---

_Fin del traspaso. Si algo no está aquí, mirar la memoria (§10) y el git/estado actual del código, que es la fuente de verdad._
