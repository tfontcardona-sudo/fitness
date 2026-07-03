# TRASPASO — Sistema de Asesorías Fitness (DQ)

> **Documento único de traspaso.** Si eres una IA o un dev que recoge este
> proyecto: lee esto entero antes de tocar nada. Es autocontenido. **El código es
> la fuente de verdad**: cuando dudes de un detalle, ábrelo y verifícalo.
> (En la raíz del repo también existe `CLAUDE (1).md`, con info equivalente.)

---

## Contenido de esta carpeta de traspaso (súbela entera — 7 archivos)

- **TRASPASO.md** — este documento: estado, arquitectura, flujo, gotchas, pendientes.
- **CODIGO-BACKEND.md** — TODO el código del backend (53 archivos) en un solo doc.
- **CODIGO-FRONTEND.md** — TODO el código del frontend (36 archivos) en un solo doc.
- **README.md** — visión general + **despliegue en producción** (VPS/Caddy/SMTP/backups).
- **anamnesis-oficial-en-blanco.pdf** — el dosier oficial que rellena el cliente.
- **anamnesis-ejemplo-rellena.pdf** — ejemplo relleno (lo que la IA lee y extrae).
- **feedback-ejemplo.docx** — ejemplo del informe de feedback generado (la salida).

> Los dos `CODIGO-*.md` son una **foto del código** del día del traspaso. Si vas a
> editar el proyecto en vivo, abre el repo real; estos sirven para que la IA tenga
> todo el contexto si solo puede leer documentos.

---

## 0. Qué es (resumen en 30 s)

Software **single-tenant** para un coach de fitness/nutrición (David Quiceno,
marca "DQ"). Automatiza el ciclo de asesoría **cliente ↔ coach**:

1. El coach da de alta al cliente y le envía el **dosier** (PDF de anamnesis o el
   enlace del portal).
2. El cliente rellena la anamnesis (PDF); la **IA la lee** y pre-rellena la ficha.
3. El coach **genera un plan mensual** (dieta + entreno) con IA, lo **revisa/edita**,
   lo **publica** y lo **descarga en Word** para enviarlo.
4. El coach **inicia el período de seguimiento**; el cliente, en su **portal**,
   registra cada día (peso, entreno con series/reps, dieta, diario). Todo se
   **autoguarda en el backend** y el coach lo ve en tiempo real.
5. A los **14 días** el cliente **cierra** el período (peso final, perímetros,
   fotos, valoración). El coach recibe una **notificación**.
6. El coach **genera el feedback** (IA + métricas + Word), lo revisa y lo **envía
   al cliente**, que lo ve en su pestaña **"Progreso"**. Vuelve al paso 4.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.0 / Alembic · APScheduler ·
React + TypeScript + Vite + Tailwind · Caddy · Docker · **API de Anthropic**.
**Modelos:** `claude-opus-4-8` (pesado: generación/visión/feedback),
`claude-haiku-4-5` (ligero). **Idioma del proyecto:** español (UI y comentarios).

---

## 1. Cómo arrancar (desarrollo)

Proyecto en `C:\Users\Usuari\Desktop\fitness-system` (Windows + Docker Desktop).

```bash
# Arrancar todo (backend + frontend + Postgres + mailpit) con hot-reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# Sin reconstruir
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
# Parar
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

| Servicio | URL |
|---|---|
| Panel del coach (web) | http://localhost:5173 |
| API + Swagger | http://localhost:8000/api/docs |
| Portal del cliente | http://localhost:5173/p/{token} |
| Mailpit (emails de prueba) | http://localhost:8025 |

**Login del coach:** `ADMIN_1_USER` / `ADMIN_1_PASS` del `.env`.

`.env` (no se versiona) tiene: `ANTHROPIC_API_KEY`, `MODEL_HEAVY`, `MODEL_LIGHT`,
`JWT_SECRET`, `PORTAL_TOKEN_SECRET`, `ADMIN_1_*`, `ADMIN_2_*`, `BASE_URL`,
`EMAILS_ENABLED`, `TZ`, `DATABASE_URL`, `AUTO_PILOT_DEFAULT`.

⚠️ **Si la IA falla con "balance is too low": no hay crédito** en la cuenta de
Anthropic. Recarga en console.anthropic.com. Sin crédito, Leer anamnesis /
Generar plan / Generar feedback devuelven **502 con mensaje legible** (no 500).

---

## 2. Arquitectura

### Backend (`backend/app/`)
```
main.py            FastAPI: routers, CORS, scheduler en lifespan, health.
config.py          Settings (pydantic-settings, lee .env).
db.py              engine + SessionLocal + Base.
models.py          Modelos SQLAlchemy (tablas abajo).
security.py        JWT (coach) + tokens de portal firmados (itsdangerous).
deps.py            get_current_user (JWT), get_client_by_token (portal).
routers/
  auth.py          login, me.
  clients.py       CRUD clientes, documentos (PDF anamnesis), FOTOS (coach),
                   leer-anamnesis (IA), generar-plan (IA).
  exercises.py     biblioteca de ejercicios.
  plans.py         planes (editar/publicar/Word), PERÍODOS, FEEDBACK (generar/
                   enviar/descargar), métricas-resumen, swap, plantilla anamnesis.
  brand.py         configuración de marca.
  portal_public.py endpoints PÚBLICOS del portal (token, sin login).
schemas/
  entities.py      schemas Pydantic de API (espejados en frontend/src/types.ts).
  ai.py            contratos de la salida de IA del plan (Plan/Meals/Education).
services/
  ai/
    client.py      AIClient: wrapper Anthropic con retry + validación. Métodos
                   generate_json(), read_pdf_json() (PDF nativo). MAX_TOKENS=16000.
                   Traduce errores de la API a AIGenerationError (→502 legible).
    extraction.py  AnamnesisExtraction + extract_anamnesis_from_pdf(): la IA lee
                   el PDF y extrae TODAS las secciones (estructurado + resúmenes).
    generator.py   generate_monthly_plan(ctx, ai): 3 llamadas orquestadas.
    feedback.py    generate_feedback_analysis(): parte CUALITATIVA del feedback.
    prompts.py     prompts del plan.
  feedback_service.py  build_period_feedback() (métricas+IA+Word+persistir) y
                       compute_period_summary() (métricas SIN IA para el "Resumen").
  metrics.py       TODA la aritmética: BMR/TDEE/kcal, e1RM, tendencia peso, adherencia.
  guardrails.py    validación de seguridad de la salida de IA (E.4/F.4).
  state_machine.py estados del cliente/período.
  scheduler.py + jobs.py   APScheduler (mantenimiento diario).
  email_service.py + email_templates.py   SMTP con marca + log.
  portal.py        lógica del portal: build_today_view, build_training_sessions…
  swap.py          intercambio de ejercicios.
  storage.py       ficheros en disco {STORAGE_PATH}/clients/{id}/{photos|documents|
                   uploads|feedback}. save_photo (quita EXIF), save_document (PDF),
                   list_documents (SOLO PDF, oculta sidecar _*).
  docs/            Word con marca: plan_doc, feedback_doc, charts (matplotlib).
  audit.py         log_event().
seeds/             150 ejercicios + marca + 2 admins (idempotente).
```

**Tablas (`models.py`):** `User`, `Client`, `Plan`, `Period`, `DailyLog`,
`WorkoutLog`, `Exercise`, `ProgressPhoto`, `FeedbackDoc`, `BrandConfig`,
`EmailLog`, `ChangeRequest`, `AuditLog`.
- `Client` tiene los campos de anamnesis (estructurados + columnas de notas:
  `medical_notes`, `medication_notes`, `current_supplements`, `sport_history`,
  `lifestyle_notes`, `injuries_notes`) + `status`.
- `FeedbackDoc`: `content_json`, `docx_path`, **`sent_at`** (clave: borrador vs enviado).
- `Period`: datos de cierre (`closing_weight_kg`, perímetros, rating…), `status`
  (open/closed/analyzed), `metrics_json`, `ai_analysis_json`.

### Frontend (`frontend/src/`)
```
pages/
  LoginPage · DashboardPage · ClientsPage · BrandPage
  ClientProfilePage.tsx   Perfil con pestañas Resumen/Anamnesis/Planificación/
                          Feedback. Banner de notificación (cliente cerró →
                          feedback). Sidebar: "Abrir/copiar enlace del portal".
components/
  ClientSummaryTab · ClientAnamnesisTab (todos los campos del PDF + "Leer con IA"
    + "Ver PDF") · ClientPlanPanel (genera/persiste/ver/edita/publica/Word +
    "Iniciar seguimiento") · ClientPlanEditor (editor del plan → PATCH) ·
    ClientFeedbackTab (períodos, Resumen, Generar/Enviar feedback, fotos) ·
    ClientDocuments (subir PDF) · ui.
lib/  api.ts (cliente HTTP coach) · format.ts
portal/  App SEPARADA del cliente (token en la URL, sin login):
  PortalApp (tabs: Hoy·Plan·Entreno·Diario·Cierre·Progreso) · PortalToday
  (medidor de días + checklist diario + comidas + entreno) · PortalWorkout
  (registro de series, selector de sesión, autosave) · PortalDiary · PortalPlan ·
  PortalClose (cierre + fotos) · PortalFeedback ("Progreso": informes ENVIADOS,
  con contenido) · portalApi.ts
types.ts  espejo manual de los schemas Pydantic (mantener en el mismo commit).
```

---

## 3. El pipeline de IA — PRINCIPIO DE SEGURIDAD

**La IA NUNCA calcula números.** El backend calcula todo lo cuantitativo
(BMR, TDEE, kcal, macros, e1RM, adherencia, tendencias) en `metrics.py`, filtra
ejercicios de forma determinista en `guardrails.py`, y revalida cada salida de IA.
La IA solo rellena lo cualitativo **dentro** de esos límites.

- **Generar plan** (`routers/clients.py` → `generator.generate_monthly_plan`): valida
  anamnesis completa (422 si faltan campos) → calcula métricas → filtra biblioteca
  (en gimnasio NO restringe por equipo) → **3 llamadas IA** (núcleo, comidas,
  educativo), cada una validada contra su schema con 1 reintento → guardrails →
  persiste como **borrador** (`status="draft"`).
- **Leer anamnesis** (`extraction.py`): `read_pdf_json` manda el PDF como bloque
  `document` (base64) a Anthropic. Extrae estructurado + resúmenes por sección +
  `deep_analysis`. Pre-rellena la ficha (no pisa con null).
- **Feedback** (`feedback_service.build_period_feedback`): reúne diario/cierre,
  calcula métricas, llama a la IA SOLO para lo cualitativo (`ai/feedback.py`),
  genera el Word (`docs/feedback_doc.py` con gráficas) y persiste el `FeedbackDoc`
  como **borrador** (`sent_at=None`).

---

## 4. El flujo cliente ↔ coach (estado: COMPLETO y probado con IA real)

```
COACH                                   CLIENTE (portal, token en URL)
─────                                   ──────────────────────────────
Alta cliente
Enviar dosier (PDF anamnesis o link) ─► rellena la anamnesis (PDF)
Subir PDF → IA lee y pre-rellena
Revisar/corregir Anamnesis
Generar plan (IA) → revisar/EDITAR
Publicar plan → Descargar Word ───────► (lo recibe)
"Iniciar seguimiento" (crea período) ─► PORTAL: cada día registra
                                        · peso, sueño, ánimo (Diario)
                                        · series/reps por ejercicio (Entreno)
                                        · dieta seguida / comidas elegidas
                                        (todo AUTOSAVE al backend, en vivo)
(ve el progreso en tiempo real)         medidor "Día X/14" + checklist
                              día 14 ──► Cierre: peso final, perímetros, FOTOS,
                                        valoración → cliente = review_pending
NOTIFICACIÓN en el perfil ◄─────────────┘
pestaña Feedback:
 · "Resumen" (métricas SIN IA)
 · "Generar feedback" (IA → borrador + Word, ve fotos)
 · revisar
 · "Enviar al cliente" ────────────────► PORTAL "Progreso": ve el informe
   (sent_at + review_pending→active        (peso, adherencia, análisis,
    + cierra notificación + email)          cambios, objetivos)
→ vuelve a generar plan del mes siguiente
```

**Clave del feedback:** es **borrador hasta que el coach pulsa "Enviar"**. El
portal (`/p/{token}/feedback`) filtra `sent_at IS NOT NULL`; el cliente NO ve
borradores. Mismo patrón "revisar antes de publicar" que anamnesis y plan.

**Autosave del portal:** `PUT /p/{token}/diary` es un **upsert PARCIAL**
(`exclude_unset`): cada pantalla guarda solo lo suyo (comidas / diario / series).

---

## 5. Endpoints clave (verifica en /api/docs)

```
POST  /api/auth/login                         Login coach → JWT
GET/POST/PATCH /api/clients[/{id}]            CRUD cliente (PATCH = anamnesis editable)
POST  /api/clients/{id}/documents             Subir anamnesis PDF (+ IA lee)
POST  /api/clients/{id}/read-anamnesis        Leer PDF con IA
POST  /api/clients/{id}/generate-plan         Generar plan (IA, borrador)
GET   /api/clients/{id}/photos[/{photo_id}]   Fotos del cliente (ver/descargar)
PATCH /api/plans/{id}                          Editar plan a mano
POST  /api/plans/{id}/publish                  Publicar plan
GET   /api/plans/{id}/document                 Plan en Word
POST  /api/clients/{id}/periods                Iniciar período (plan publicado)
GET   /api/clients/{id}/periods                Listar períodos + cierre + feedback
GET   /api/periods/{id}/metrics                Resumen SIN IA (peso/adherencia/fuerza/objetivo)
POST  /api/periods/{id}/feedback               Generar feedback (IA, borrador) → Word
GET   /api/feedback/{id}                        Contenido + sent_at
POST  /api/feedback/{id}/send                   ENVIAR al cliente (sent_at + estado + email)
GET   /api/feedback/{id}/document               Feedback en Word
GET   /api/anamnesis-template                    Plantilla PDF en blanco
# Portal (público, token):
GET   /api/p/{token}/state | today | training | plan
PUT   /api/p/{token}/diary                       Autosave parcial (diario/series/comidas)
POST  /api/p/{token}/close [+ /close/photos]     Cierre + fotos
GET   /api/p/{token}/feedback                     "Progreso": feedbacks ENVIADOS
```
Descargas con JWT en el frontend: `fetch → blob → download` con header
`Authorization: Bearer`.

---

## 6. ⚠️ GOTCHAS CRÍTICOS (resueltos; NO reintroducir)

0. **[DEV/WINDOWS] Vite no detecta cambios en el bind mount de Docker.** Síntoma:
   "no veo ningún cambio" pese a editar. FIX aplicado: `server.watch.usePolling:true`
   en `frontend/vite.config.ts`. Si sigue, reinicia el contenedor `web` y haz
   **Ctrl+Shift+R** en el navegador.
1. **`from __future__ import annotations` ROMPE FastAPI/Pydantic** en archivos con
   endpoints/schemas de ruta (ForwardRef sin resolver). Eliminado de `routers/`,
   `schemas/`, `deps.py`. No lo añadas ahí.
2. **`temperature` está deprecado en `claude-opus-4-8`** → 400. No lo pases.
3. **`VITE_API_URL` = `http://api:8000`** (nombre del servicio Docker) en dev, no localhost.
4. **`email-validator` en `requirements.txt`** (lo necesita `EmailStr`).
5. **`UploadFile` en listas:** `Annotated[List[UploadFile], File(...)]`.
6. **El enlace del portal usa el ORIGEN del navegador** (`window.location.origin`)
   para funcionar en dev (:5173) y prod. No uses `BASE_URL` para el botón del coach.
7. **Errores 500 → el Traceback está en el log del contenedor `api`** (`api-1 |`).
8. **`ClientUpdate` (PATCH) debe incluir TODO campo editable de la pestaña Anamnesis;**
   Pydantic descarta extras en silencio (el coach cree que guardó y no).
9. **Un 500 al Leer/Generar suele ser API sin crédito** → ya sale como 502 legible
   (`client._translate_api_error`).
10. **Schemas de salida de IA: lista los subcampos en el prompt** (si no, la IA los
    omite y la validación tumba todo) y deja `MAX_TOKENS` holgado (banco de comidas
    grande). `MealSlot`/`Supplement` tienen defaults tolerantes.
11. **`PUT /p/{token}/diary` es upsert PARCIAL:** no mandes `workout_sets:[]` desde
    diario/comidas o **borras las series** del cliente.
12. **El feedback es BORRADOR hasta `send`:** el portal filtra `sent_at IS NOT NULL`.
    No quites ese filtro.

---

## 7. Estado actual (qué está hecho y verificado)

- ✅ Anamnesis: extracción cubre TODAS las secciones del PDF; pestaña muestra todo;
  subir PDF auto-lee y auto-rellena en vivo; "Ver PDF".
- ✅ Plan: generar (3 llamadas IA + guardrails), **persiste**, ver, **editar**
  (`ClientPlanEditor`), publicar, **descargar Word**. Educativo OCULTO en UI.
- ✅ Período: "Iniciar seguimiento".
- ✅ Portal: medidor de días + checklist diario; Entreno (series + selector de
  sesión + autosave); Diario; Cierre (+fotos); Progreso (informes enviados con contenido).
- ✅ Feedback: Resumen (sin IA), Generar (IA → borrador + Word), **fotos** (ver/
  descargar en el coach), **Enviar al cliente** (sent_at + review_pending→active +
  email + cierra notificación). **Probado end-to-end con IA real** (cliente ss).
- ✅ Tests unitarios en verde; test frágil robustecido.

**Datos de prueba:** cliente **ss** (id 2) tiene plan publicado, período cerrado con
14 días simulados, un feedback **generado pero SIN enviar** (para probar el botón
"Enviar"), y 2 fotos de ejemplo. Su token de portal está en la BD (`clients.portal_token`).

---

## 8. Trabajo pendiente / próximos pasos

1. **PDF de ejemplo de planificación (lo siguiente que quiere el dueño):** subirá un
   PDF con cómo debe ser el plan mensual (estructura, contenido, colores). La IA debe
   **generar siguiendo ese ejemplo**. Tocará `generator.py` (prompts/estructura) y
   posiblemente `docs/plan_doc.py` (estilo del Word). El dueño trabaja la CALIDAD
   interna (dieta/entreno) aparte.
2. **Editor del plan: banco de comidas** (28 opciones) y **swap de ejercicio** dentro
   del editor (hoy el swap es por la biblioteca, `swap.py`).
3. **Aislar los tests de integración de la BD de desarrollo:** hoy crean clientes
   `@example.com` en cada `pytest` (usar transacción con rollback o BD de test).
4. **Probar el ciclo con un cliente real** (no simulado) de punta a punta.

---

## 9. Convenciones y cómo trabajar

- **Idioma:** UI y comentarios en español. El dueño se comunica en catalán/castellano.
- **Estilo del dueño:** pasos pequeños con checkpoints; feedback honesto sin adular;
  no romper nada del proceso. Comunicación visual/concreta.
- **Seguridad:** mantener "la IA no calcula". Todo número desde `metrics.py`.
- **Sin migraciones innecesarias:** se reaprovechan columnas/sidecars antes de migrar.
- **`types.ts` espeja `schemas/entities.py`** — actualízalos en el mismo commit.
- **Tras editar:** en dev recarga solo (con el polling del gotcha 0). Si tocas
  dependencias/Dockerfile, reconstruye. Para depurar 500, lee el log de `api`.
- **El código manda:** este doc resume el estado; si algo no cuadra, verifica en los
  archivos.
```
