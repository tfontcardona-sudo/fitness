# CLAUDE.md — Sistema de Asesorías Fitness (DQ)

> **Documento de traspaso.** Si eres Claude Code y este archivo está en la raíz
> del repositorio, se carga automáticamente como contexto. Léelo entero antes de
> tocar nada. **El código es la fuente de verdad**: cuando dudes de un detalle
> concreto, ábrelo y verifícalo en lugar de asumir.

---

## 0. Resumen en 30 segundos

Software **single-tenant** para un coach de fitness/nutrición (David Quiceno,
marca "DQ"). Automatiza el ciclo de asesoría: el cliente rellena una anamnesis
(PDF), la IA la lee y extrae los datos, el coach genera un **plan mensual** de
dieta + entrenamiento con IA, lo revisa, lo publica (el cliente lo ve en su
portal) y el cliente registra su seguimiento diario hasta el cierre quincenal.

- **Backend:** FastAPI + PostgreSQL + SQLAlchemy + Alembic + APScheduler.
- **Frontend:** React + TypeScript + Vite + Tailwind.
- **Infra:** Docker / Docker Compose. Caddy como reverse proxy en producción.
- **IA:** API de Anthropic (`claude-opus-4-8` pesado, `claude-haiku-4-5` ligero).
- **Estado:** desplegado y funcionando. Suite en verde.
- **Idioma del proyecto:** comentarios y textos de UI en **español**.

> **Hardening v2 YA FUSIONADO en `main`** (la rama `hardening/asesorias-v2` es historia). Ver
> **`INFORME_HARDENING.md`** para el detalle. Convenciones y módulos nuevos que
> hay que respetar:
> - **Una sola verdad de objetivos calóricos**: el backend manda
>   (`services/nutrition_scale.py`, `services/metrics.py`); el editor
>   (`frontend/src/lib/nutritionTargets.ts`) debe coincidir. Está blindado por
>   `shared/nutrition_contract.json` + `tests/test_nutrition_parity.py` (si tocas
>   uno, regenera el contrato con `scripts/gen_nutrition_contract.py` y corre el
>   test). **Redondeo half-up (`_rhu`) en todo el sistema** (= `Math.round` del
>   front), nunca `round()` bancario para valores que ve/persiste el usuario.
> - **La IA NO calcula**: BMR/TDEE/kcal, ajuste individualizado y **reparto
>   completo de macros** los computa el backend (`metrics.energy_targets`,
>   `metrics.macro_targets`) y se los entrega como CONTRATO. Nunca metas fórmulas
>   de cálculo en `prompts.py`.
> - **Validador determinista** (`guardrails.validate_plan_deterministic`): el
>   "Revisor 0" con veto (Atwater, Σ comidas = día, tolerancias del contrato,
>   alérgenos en subingredientes, patrón dietético, porciones). Úsalo/extiéndelo
>   al montar el panel de supervisión del §9.
> - **Base de alimentos + solver** (`models.Food` mig. 0028, `seeds/foods_data.py`,
>   `services/portion_solver.py`): la IA selecciona alimentos; el backend fija los
>   gramos con `solve_portions` (scipy). `filter_foods` quita alérgenos/patrón ANTES
>   del prompt. Requiere `numpy`/`scipy` (en requirements).
> - **Motor quincenal determinista** (`services/biweekly_engine.decide_biweekly`):
>   reglas fijas para la revisión (no criterio del modelo); pendiente de enchufar al
>   cierre de período real.
> - **Golden set** (`app/golden_set.py`, `tests/test_golden_set.py`): gate de CI de la
>   capa determinista; rangos `POR_VALIDAR`.
> - **Panel de supervisión + ICP + semáforo** (`services/review_panel.py`,
>   `services/safety_gate.py`): revisor 0 determinista + roles IA con contexto AISLADO
>   + árbitro (no anula vetos) + ICP + lista roja/semáforo + **bucle de reparación**
>   (`run_panel_with_repair`, máx 3) + `make_ai_reviewer`. Revisores IA inyectables.
> - **Más módulos del hardening v2** (todos con tests; integración al flujo IA en vivo
>   pendiente, ver INFORME_HARDENING.md): `diet_training_coherence` (§6),
>   `plan_quality` (§10 simulación/estrés/best-of-N/checklist/canario),
>   `anamnesis_extraction` (§5 contradicciones/cobertura/doble pase), `plan_state`
>   (§4 versionado + propagación), `biweekly_engine` (§8), `continuous_learning` (§13),
>   `progressive_unlock` (§12), `plan_stability` (§11/§14). Migraciones 0028 (foods),
>   0029 (plan_edits, segment_unlock).
> - **Criterio de coach**: `CRITERIOS_ASESORIA.md` — COMPLETO (agosto 2026):
>   la anamnesis manda (§0), arranque en el extremo conservador (también en
>   `metrics.individualized_energy_adjustment`), sin alimentos/estructuras
>   predefinidos (todo sale de la anamnesis), tono único serio-profesional-
>   cercano, y patologías comunes añadidas a la lista roja (`safety_gate`).
> - **Historia antigua**: `docs/HISTORICO.md` (referencia, NO fuente de verdad viva).

---

## 1. Cómo arrancar (desarrollo)

El proyecto vive en `C:\Users\Usuari\Desktop\fitness-system` (máquina del dueño).

```bash
# Arrancar todo (backend + frontend + Postgres + mailpit) con hot-reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Sin reconstruir (si solo cambió código Python/TS, que recarga solo)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Parar
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

URLs en desarrollo:
- **Panel del coach (web):** http://localhost:5173
- **API:** http://localhost:8000
- **Docs interactivas (Swagger):** http://localhost:8000/api/docs
- **Mailpit (ver emails de prueba):** http://localhost:8025

El **Dockerfile** del backend hace `COPY . .`, así que cualquier archivo nuevo
dentro de `backend/` se incluye al reconstruir. En dev, el frontend usa el
servidor de Vite con HMR.

### Variables de entorno (`.env` en la raíz)

Los valores reales están en el `.env` existente (NO se versionan, NO los
escribas en commits ni en este documento). Variables que existen:

```
ANTHROPIC_API_KEY      # clave real de Anthropic (sk-ant-api03-…)
MODEL_HEAVY            # claude-opus-4-8        (generación de planes, lectura PDF)
MODEL_LIGHT            # claude-haiku-4-5-…     (tareas ligeras)
JWT_SECRET             # firma de tokens del coach
PORTAL_TOKEN_SECRET    # firma de los enlaces del portal del cliente
ADMIN_1_USER / _PASS   # credenciales del coach (login del panel)
ADMIN_2_USER / _PASS   # segundo admin
BASE_URL               # http://localhost en dev (en prod, el dominio)
EMAILS_ENABLED         # false en dev
TZ                     # zona horaria
```

---

## 2. Arquitectura

### Backend (`backend/app/`)

```
main.py            App FastAPI, monta routers, CORS, middlewares.
config.py          Settings (lee el .env vía pydantic-settings).
db.py              Engine, SessionLocal, get_db.
deps.py            Dependencias (get_current_user, etc.).
security.py        Hash de contraseñas (bcrypt), JWT.
models.py          Modelos SQLAlchemy (ver tablas abajo).

routers/
  auth.py          POST /api/auth/login, GET /api/auth/me.
  clients.py       CRUD de clientes + documentos + lectura IA + generación de plan.
  exercises.py     Biblioteca de ejercicios.
  plans.py         Planes: publicar, descargar Word, plantilla de anamnesis.
  brand.py         Configuración de marca (logo, colores, textos).
  portal_public.py Endpoints PÚBLICOS del portal del cliente (token, sin login).

schemas/
  entities.py      Schemas Pydantic de entrada/salida.
  ai.py            Schemas del plan generado por IA.

services/
  ai/
    client.py      AIClient: wrapper de la API de Anthropic con reintento +
                   validación. Métodos: generate_json(), read_pdf_json() (lee PDF).
    generator.py   generate_monthly_plan(ctx, ai): orquesta las llamadas a IA.
                   Define ClientContext (datos que alimentan los prompts).
    extraction.py  extract_anamnesis_from_pdf(): la IA lee el PDF de la anamnesis
                   y extrae datos estructurados + resumen por sección + análisis.
    feedback.py    generate_feedback_analysis(): la IA redacta SOLO la parte
                   cualitativa del feedback (análisis, cambios, objetivos).
    prompts.py     Prompts del sistema/usuario.
  feedback_service.py  build_period_feedback(): orquesta el feedback de un período
                   cerrado (métricas + IA + documento Word + persistencia).
  metrics.py       TODO el cálculo numérico: bmr, tdee, energy_targets,
                   protein_target_g, e1RM, tendencia de peso, adherencia…
  guardrails.py    Filtrado determinista de ejercicios + validación del plan.
  storage.py       Ficheros en disco: {STORAGE_PATH}/clients/{id}/{photos|documents|uploads}
                   y /brand/. save_document(), list_documents(), save_photo()…
  docs/            Generación de documentos Word (python-docx) con marca DQ.
  state_machine.py Estados del cliente/periodo.
  scheduler.py     APScheduler (recordatorios, cierres automáticos…).
  swap.py          Lógica de equivalencias / intercambio de ejercicios.
  portal.py        Tokens del portal del cliente.
  audit.py         log_event(): registro de auditoría (diffs, acciones).
```

**Tablas (models.py):** `User`, `Client`, `Plan`, `Period`, `DailyLog`,
`WorkoutLog`, `Exercise`, `ProgressPhoto`, `FeedbackDoc`, `BrandConfig`.

### Frontend (`frontend/src/`)

```
App.tsx, main.tsx          Bootstrap + router.
pages/
  LoginPage.tsx            Login del coach.
  DashboardPage.tsx        Panel "Hoy" (métricas, colas de atención).
  ClientsPage.tsx          Lista de clientes.
  ClientProfilePage.tsx    Perfil con pestañas: Resumen / Anamnesis / Planificación /
                           Feedback (sidebar: solo "Abrir/copiar enlace del portal").
  BrandPage.tsx            Configuración de marca.
components/
  ClientSummaryTab.tsx     Pestaña Resumen.
  ClientAnamnesisTab.tsx   Pestaña Anamnesis: TODOS los campos + "Leer con IA" + "Ver PDF".
  ClientPlanPanel.tsx      Pestaña Planificación: genera / persiste / ver / publica /
                           descarga Word + "Iniciar seguimiento" (crea el período).
  ClientPlanEditor.tsx     Editor manual del plan (nutrición/entreno/educativo) → PATCH.
  ClientFeedbackTab.tsx    Pestaña Feedback: períodos + cierre + "Resumen" (métricas sin
                           IA) + generar feedback (IA) + descargar Word. Cierra el ciclo.
  ClientDocuments.tsx      Subir/descargar la anamnesis PDF (sidebar del perfil).
  ui.tsx                   Primitivas de UI (toast, spinner, etc.).
lib/
  api.ts                   Cliente HTTP del panel (request() + métodos).
  format.ts                Etiquetas y formateadores (GOAL_LABEL, etc.).
portal/                    App SEPARADA del cliente (PortalApp + Today, Plan, Workout
                           [registro de series, selector de sesión], Diary, Close,
                           Feedback) + portalApi.ts. Autosave al backend.
types.ts                   Tipos compartidos (ClientOut, GoalType, Level…).
```

---

## 3. El pipeline de IA (entiéndelo bien antes de tocarlo)

**Principio de seguridad central: la IA NUNCA calcula números.** El backend
calcula todo lo cuantitativo (BMR, TDEE, calorías objetivo, macros) en
`metrics.py`, y filtra los ejercicios de forma determinista en `guardrails.py`.
La IA solo rellena la parte cualitativa del plan, **dentro** de esos límites, y
después el plan pasa por validación de guardrails. Si rompes esto, comprometes
la seguridad del sistema (dietas/ejercicios mal calculados).

### Flujo de `generate-plan` (en `routers/clients.py`)

1. Valida que la anamnesis estructurada del cliente esté completa. Si faltan
   campos, devuelve **422** con la lista de campos que faltan.
2. Calcula métricas con `metrics.energy_targets(...)` (BMR/TDEE/target_kcal).
3. Filtra la biblioteca de ejercicios con `guardrails.filter_exercises_for_client(...)`.
   ⚠️ **En gimnasio NO se restringe por equipamiento** (se asume gimnasio
   completo); en casa/exterior sí se respeta el material declarado.
4. Construye un `ClientContext` (incluye `deep_analysis` si existe) y llama a
   `generate_monthly_plan(ctx, AIClient())`.
5. `generate_monthly_plan` hace **3 llamadas** a la IA: núcleo (entrenamiento +
   macros), comidas (según el modo de dieta), y educativo. Cada salida se valida
   contra su schema; reintenta 1 vez con el error inyectado si falla.
6. Persiste el plan como **borrador** (`status="draft"`). El coach lo revisa,
   publica (`POST /api/plans/{id}/publish`) y descarga (Word).

### Lectura de la anamnesis con IA (`extraction.py` + `clients.py`)

- `AIClient.read_pdf_json()` envía el PDF como **bloque `document`** (base64) a
  la API de Anthropic (lectura nativa de PDF) y valida la salida.
- `extract_anamnesis_from_pdf()` mapea el PDF a un `AnamnesisExtraction`. El
  esquema **refleja las secciones del PDF oficial**: campos estructurados (sexo,
  antropometría, objetivo, nivel, entrenamiento, `equipment`, dieta, preferencias)
  + un **resumen por sección cualitativa**, cada uno a su columna existente:
  `injuries_notes` (lesiones), `medical_notes` (clínica + digestivo + salud
  femenina), `medication_notes`, `current_supplements`, `sport_history`
  (experiencia + otros deportes), `lifestyle_notes` (hábitos, sueño, estrés,
  conducta alimentaria, motivo/objetivos) + `deep_analysis` (síntesis).
  Se reusan columnas que ya existían → **sin migración Alembic**.
- ⚠️ El prompt obliga a rellenar los enums estructurados *infiriéndolos* del PDF
  (p. ej. `goal_type` desde "Motivo y objetivos", que no tiene casilla). `MealSlot`
  tiene los campos opcionales y se autocompletan (`slot`/`name`), para que un
  capricho de formato de la IA **no descarte toda la extracción**.
- El endpoint pre-rellena la ficha (no pisa con null) y guarda `deep_analysis` +
  `injuries_notes` como **sidecar JSON** en
  `clients/{id}/documents/_anamnesis_analysis.json`. En `generate-plan` ese
  análisis se carga y se pasa al prompt del núcleo para personalizar el plan.
- **Al subir el PDF, la ficha se rellena en vivo sin recargar:** la subida lee con
  IA y `ClientDocuments` llama a `onUploaded` → el perfil refetchea el cliente y
  la pestaña Anamnesis muestra los campos al instante.

---

## 4. El flujo de negocio (el ciclo de asesoría)

```
1. ANAMNESIS (1 vez)  → el cliente abre /anamnesis/{token} (email/WhatsApp de
   arranque) y rellena el FORMULARIO DIGITAL por pasos (vía oficial desde
   agosto 2026, decisión del dueño): los datos van directos a la ficha, se
   firma el consentimiento RGPD (PDF generado) y puede subir fotos iniciales.
   · Alternativa (plegada en la misma página): descargar el PDF oficial,
     rellenarlo y subirlo — la IA lo LEE automáticamente y rellena la ficha.
   · Una sola anamnesis por cliente (el formulario responde 409 tras enviarse;
     subir otro PDF reemplaza el anterior).
2. REVISIÓN          → el coach revisa los datos extraídos en la pestaña
   Anamnesis (la IA puede equivocarse con texto manuscrito) y corrige.
3. PLAN              → pestaña Planificación → Generar → revisar → Publicar +
   Descargar Word para enviar.
4. PORTAL CLIENTE    → el cliente ve su plan ("Hoy") y registra el DIARIO
   (peso, sueño, adherencia…) durante ~14 días.
5. CIERRE            → el cliente cierra el periodo (peso final, perímetros,
   fotos, valoración).
6. FEEDBACK          → el coach genera feedback + el siguiente plan → vuelve a 4.
```

**Decisión de diseño (agosto 2026 — sustituye al "Camí A"):** la vía oficial es
el FORMULARIO DIGITAL del portal (el PDF de 10 páginas no era rellenable y
obligaba a imprimir); el PDF sigue disponible como alternativa. En ambas vías
el coach REVISA la ficha antes de generar (seguridad > automatización ciega).
"Anamnesis recibida" = `consent_signed_at` (formulario) O un PDF subido.

---

## 5. ⚠️ GOTCHAS CRÍTICOS (lecciones aprendidas — léelas o las repetirás)

Estos bugs ya costaron horas. Están resueltos; **no los reintroduzcas**:

1. **`from __future__ import annotations` ROMPE FastAPI/Pydantic.** Convierte los
   type hints en strings (ForwardRef) que Pydantic no resuelve para modelos de
   request/response, y revienta con `PydanticUserError: ... is not fully defined`
   o 422 raros. Se ELIMINÓ de **todos** los archivos de `routers/`, `schemas/` y
   `deps.py`. **No lo añadas** a ningún archivo con endpoints FastAPI o schemas
   Pydantic usados en rutas.

2. **`temperature` está deprecado para `claude-opus-4-8`.** Pasarlo provoca
   `BadRequestError: 400 - 'temperature' is deprecated for this model`. Se quitó
   de las llamadas en `services/ai/client.py`. **No pases `temperature`** a este
   modelo.

3. **`VITE_API_URL` debe ser `http://api:8000`** (nombre del servicio Docker) en
   `docker-compose.dev.yml`, **no** `localhost:8000`. Dentro de Docker,
   "localhost" es el propio contenedor del frontend, no la API. Síntoma si está
   mal: `ECONNREFUSED` / "No se pudo conectar" en el login.

4. **`email-validator` debe estar en `requirements.txt`.** El `EmailStr` de
   Pydantic lo necesita; si falta, la app no arranca.

5. **`UploadFile` en listas:** usa `Annotated[List[UploadFile], File(...)]`, no
   `list[UploadFile]` suelto (vuelve al problema del ForwardRef).

6. **El enlace del portal usa `BASE_URL`.** En dev es `http://localhost`, así que
   al abrirlo a mano hay que añadir el puerto: `http://localhost:5173/p/...`. En
   prod con dominio es correcto automáticamente.

7. **Errores 500 → el detalle está en el TERMINAL** (líneas `api-1 |` con
   Traceback), no en el navegador. Para depurar, mira el log del contenedor `api`.

8. **`ClientUpdate` (PATCH) debe incluir TODO campo editable en la pestaña
   Anamnesis.** Pydantic ignora campos extra en silencio: si el frontend manda un
   campo que no está en `ClientUpdate`, el PATCH **lo descarta sin error** y el
   coach cree que guardó. Pasó con `sex`/`birth_date`/`height_cm`/`start_weight_kg`/
   `body_fat_pct`/`sport_history` (ya añadidos). Si añades un campo nuevo a la
   pestaña, añádelo también a `ClientUpdate`.

9. **Un 500 al "Leer" o "Generar" suele ser la API sin crédito.** Los errores de
   la API de Anthropic (saldo, rate limit, clave) se capturan en `client.py`
   (`_translate_api_error`) y se traducen a `AIGenerationError` → el endpoint
   responde **502 con mensaje legible**. Si ves "La API de Anthropic devolvió un
   error: …balance is too low…", **recarga crédito** en console.anthropic.com.

10. **Schemas de salida de IA: no exijas subcampos sin listarlos en el prompt.**
    Si el contrato Pydantic requiere un subcampo (p. ej. `supplements.evidence_note`,
    `weekly_progression.intent`) pero el prompt no lo nombra, la IA lo omite y la
    validación tumba TODO. Lista los subcampos en el prompt y/o pon defaults
    (como en `MealSlot`/`Supplement`). `MAX_TOKENS` (client.py) debe dar margen al
    banco de comidas (4×7 opciones) para no truncar el JSON.

11. **El `PUT /p/{token}/diary` es un upsert PARCIAL (`exclude_unset`).** Cada
    pantalla del portal guarda solo lo suyo: HOY (comidas) manda `chosen_options_json`,
    Diario manda escalares, Entreno manda `workout_sets`. Si una pantalla envía
    `workout_sets: []` "para rellenar", **borra las series** del cliente. Regla: no
    mandes un campo que no estás editando. El backend solo reemplaza las series si
    `workout_sets` viene en la petición.

12. **El feedback es BORRADOR hasta que el coach lo ENVÍA.** `build_period_feedback`
    crea el `FeedbackDoc` con `sent_at=None` (solo lo ve el coach). El cliente lo ve en
    su "Progreso" SOLO si `sent_at` está puesto — `portal_feedback` filtra por
    `sent_at IS NOT NULL`. No quites ese filtro o el cliente vería borradores. Enviar
    (`POST /api/feedback/{id}/send`) pone `sent_at`, pasa `review_pending→active` y
    cierra la notificación del perfil. Mismo patrón "revisar antes de publicar" que
    anamnesis y plan.

---

## 6. Endpoints clave (verifica en Swagger: /api/docs)

```
POST /api/auth/login                       Login del coach → JWT.
GET  /api/clients                          Lista de clientes.
POST /api/clients                          Crear cliente.
GET  /api/clients/{id}                     Ficha del cliente.
PATCH /api/clients/{id}                    Editar ficha (registra diff en auditoría).

POST /api/clients/{id}/documents           Subir anamnesis PDF (borra anterior +
                                           la LEE con IA automáticamente).
GET  /api/clients/{id}/documents           Listar documentos.
GET  /api/clients/{id}/documents/{name}    Descargar un documento (requiere JWT).
POST /api/clients/{id}/read-anamnesis      Leer el PDF con IA y rellenar la ficha.
POST /api/clients/{id}/generate-plan       Generar el plan mensual con IA (borrador).

GET  /api/anamnesis-template               Descargar la plantilla PDF en blanco.
POST /api/plans/{id}/publish               Publicar plan (visible en el portal).
GET  /api/plans/{id}/document              Descargar el plan en Word.

PATCH /api/plans/{id}                      Editar el plan (núcleo/comidas/educativo) a mano.
POST /api/clients/{id}/periods             Iniciar período de seguimiento (plan publicado).
GET  /api/clients/{id}/periods             Listar períodos + datos de cierre + feedback.
GET  /api/periods/{id}/metrics             Resumen SIN IA: peso, adherencia, fuerza, objetivo.
POST /api/periods/{id}/feedback            Generar el feedback del período (IA, borrador) → Word.
GET  /api/feedback/{id}                    Contenido + sent_at del feedback (pestaña coach).
POST /api/feedback/{id}/send               ENVIAR al cliente: sent_at + review_pending→active + email.
GET  /api/feedback/{id}/document           Descargar el feedback en Word.
GET  /api/clients/{id}/photos              Fotos de progreso del cliente (metadatos).
GET  /api/clients/{id}/photos/{photo_id}   Servir/ver/descargar una foto (JWT).

GET  /api/payments                         Feed de cobros (libro de caja): limit/offset,
                                           filtro status=paid|failed|refunded, client_id.
GET  /api/payments/summary                 Cabecera: mes, mes anterior, sin leer, fallidos, huérfanos.
POST /api/payments/seen                    Sella lo leído ({ids} o todos) → apaga el badge.
POST /api/payments/sync                    Repesca de Stripe lo que falte (histórico + webhooks perdidos).

GET  /api/p/{token}/training               (Portal) todas las sesiones con nombres (selector Entreno).
GET  /api/p/{token}/feedback               (Portal) feedbacks ENVIADOS (sent_at) — "Progreso".
```

> Las descargas con JWT en el frontend se hacen con `fetch → blob → download`
> adjuntando el header `Authorization: Bearer`. Patrón ya usado en
> `ClientPlanPanel.tsx` y `ClientDocuments.tsx`.

---

## 7. Cómo testear

```bash
# Dentro del contenedor o con un Postgres local apuntado por DATABASE_URL:
cd backend && python -m pytest tests/ -q
```

- **~370 tests en verde** en base de datos limpia y migrada a head.
- ⚠️ En un entorno nuevo exporta `ADMIN_1_USER`/`ADMIN_1_PASS` y corre los seeds
  antes: varios tests de integración hacen login real del coach (sin admin
  sembrado fallan con 401, y no es un bug del código).
- Los tests pueden **inyectar un AIClient falso** (scripted) para probar todo el
  pipeline sin llamar a la API real (ver `tests/test_ai_service.py`). Útil porque
  la API real necesita la clave y cuesta dinero/tiempo. ⚠️ Por eso mismo, la
  suite NO detecta errores de parámetros de la API real (p. ej. el gotcha del
  `temperature`): ahora el filtro vive en `AIClient._effective_temperature`.
- ✅ El test antes frágil (`tests/test_phase2.py::test_export_with_accented_name`)
  ya usa un email único con uuid; pasa aunque la BD arrastre datos previos.
- ✅ **Los tests de integración escriben en la MISMA BD** que apunte
  `DATABASE_URL`, pero `tests/conftest.py` limpia al FINAL de la suite los
  clientes de dominios de prueba (`@example.com`, `@test.local`, `@x.com`) con
  todas sus filas dependientes y archivos: `pytest` ya no deja rastro en el
  panel. No uses esos dominios para clientes reales.

---

## 8. Convenciones

- **Idioma:** textos de UI y comentarios de código en **español**. El dueño se
  comunica en catalán/castellano.
- **Estilo de trabajo del dueño:** prefiere pasos pequeños con checkpoints,
  feedback crítico y honesto (sin adular), y que NO se rompa nada del proceso.
- **Seguridad:** mantén el principio "la IA no calcula". Todo número viene de
  `metrics.py`; los ejercicios se filtran en `guardrails.py`.
- **Sin migraciones innecesarias:** el análisis cualitativo se guarda como
  sidecar JSON precisamente para evitar tocar Alembic. Si necesitas un campo
  nuevo en BD, valora antes si un sidecar o un JSONB existente sirve.
- **Single-tenant:** un solo coach (DQ). No hay multi-cliente a nivel de coach.

---

## 9. Trabajo pendiente / próximos pasos

00000000. ✅ **AVISOS CON TÍTULO + ACCIÓN, Y "MENOS ES MÁS" DE VERDAD (agosto 2026).**
   El dueño, tras la ronda anterior: "has hecho que salga 'ver más', pero eso no
   basta: toda esa información se podría resumir en tres o cuatro palabras…
   ¿quién me quiere decir esa información? Que especifique bien POR QUÉ sale esa
   alerta en rojo para que el coach sepa QUÉ DEBE HACER". Tenía razón: la ronda
   anterior COMPRIMIÓ (clamp) en vez de REDUCIR. Suite (505) + tsc + build +
   `npm run check:avisos` en verde.
   - **Avisos del plan = título corto → acción** (`lib/findings.ts` + `AvisosBlock`):
     los hallazgos que la IA escribió ANTES de acotar su contrato son párrafos de
     40-60 palabras YA GUARDADOS en el plan; acortar el prompt no los arregla.
     `toAviso()` deriva de forma determinista TÍTULO (primera frase, sin las
     coletillas obvias tipo "…en el plan", máx. 7 palabras), CATEGORÍA (reglas
     por palabra clave, con seguridad alimentaria y lesiones primero) y ACCIÓN
     ("Corregir esa comida", "Adaptar los ejercicios"…). El bloque rojo pasa de
     12 párrafos a 6 grupos con etiquetas de 4-6 palabras; el texto íntegro queda
     como detalle a un clic. Regresión: `npm run check:avisos`.
   - **La cabecera explica el POR QUÉ**: "▲ Retenido · N puntos a corregir antes
     de enviarlo" (o "…en el plan activo" si ya está publicado), en vez de un
     chip "ICP 0" que no significaba nada para el coach. El ICP pasa al title.
   - **Contrato nuevo de los revisores** (`ReviewFindingOut`/`ReviewFinding`):
     `titulo` (3-6 palabras) y `accion` (verbo en infinitivo, 3-6 palabras)
     además de la descripción. ⚠️ Ojo: `plan_review.summarize()` NO los
     serializaba y la función entera moría en el backend (la revisión de código
     lo cazó) — si añades un campo al hallazgo, añádelo también AHÍ.
   - **267 reescrituras telegráficas** aplicadas en panel, editores, portal y
     páginas (226 automáticas por sustitución literal + el resto a mano):
     toasts, confirmaciones, ayudas de campo, avisos de descuadre y tooltips.
     Regla: el texto dice el ESTADO, el botón dice la ACCIÓN. Las cifras y los
     datos de seguridad se conservan íntegros.
   - **Correcciones de seguridad de la revisión**: "Sin lesiones declaradas ✓"
     aparecía también con la anamnesis VACÍA (convertía "no hay datos" en un
     visto bueno) → ahora "Anamnesis pendiente" si la ficha no está rellenada;
     `NEG_LIMITACION` marcaba en rojo hábitos normales ("No consume alcohol") →
     acotado a verbos de limitación real y sometido a los filtros de valor nulo.
   - **De la ronda de seguridad anterior**: copiar `.env.example` tal cual daba
     secretos PÚBLICOS que pasaban el control por ser largos (ahora cualquier
     valor que empiece por "cambia-esto" es bloqueante), y la CSP `img-src`
     bloqueaba las imágenes de producto por URL pegada (función anunciada).


0000000. ✅ **TEXTO AL MÍNIMO: telegráfico, por bloques y solo lo necesario
   (agosto 2026).** El dueño, sobre capturas del móvil: "una información que en
   4 palabras se podría transmitir igual que en 30… tiene que ser práctico,
   rápido y sencillo". Barrido de 5 auditores + verificación adversarial sobre
   TODO el sistema (portal, panel, prompts, documentos, emails/push/alertas):
   148 hallazgos. Suite (505) + tsc + build en verde.
   - ⚠️ **HALLAZGO RAÍZ — el schema NO viaja al modelo**: `AIClient.generate_json`
     solo envía `system` y `user`; el schema únicamente hace `model_validate`.
     Todo tope escrito en `Field(description=…)` era **una orden a la nada**. Los
     topes viven ahora en los PROMPTS (`prompts.py`, `generator.py`); las
     descriptions se mantienen como documentación con un aviso en la cabecera de
     `schemas/ai.py` para que nadie repita el error.
   - **DOS REGISTROS en SYSTEM_BASE**: el prompt base ordenaba "frases COMPLETAS
     y bien construidas" para TODO — era literalmente la orden de escribir prosa.
     Ahora: TELEGRÁFICO por defecto (palabras clave y cifras con "·", sin
     explicar ni motivar) y EXPLICATIVO solo en rationale/split_rationale/
     educativo. Topes duros por campo en los dos prompts del núcleo y en los dos
     del educativo: volume_note 12 palabras, deload_instructions 20,
     progression_rule 12, technique_cue/biomech_cue 10, warmup 15, cooldown 12,
     cardio notes 12, rationale 2 frases, flexibility_rules 3-5 × 12 palabras,
     refeed_or_break 15, evidence_note 10, píldoras EXACTAMENTE 3 × 40 palabras,
     faq 3 × 35. Hallazgos del panel §9: descripción 20 palabras, cita 12,
     ubicación 8, corrección 15, máx. 6 hallazgos (eran muros de texto rojo).
   - **SEGURIDAD (coordinado con los topes)**: `_clinical_block` ordenaba
     "explica el motivo en technique_cue/biomech_cue", campos ahora capados a 10
     palabras → contradicción viva sobre información clínica. Resuelto: la nota
     de seguridad va la PRIMERA en technique_cue con EXCEPCIÓN declarada (14
     palabras). Fuera también las dos órdenes del USER prompt que mandaban
     volcar teoría en esos campos.
   - **Fallos visuales de las capturas**: tarjetas de macros con `grid-cols-4`
     en móvil (~80 px/tarjeta) se solapaban ("32%Carbohid."), ahora 2×2 + cifra
     `whitespace-nowrap`; badge "N a vigilar" partido en dos líneas → flex con
     `shrink-0`; línea de déficit que repetía el objetivo de la tarjeta de arriba.
   - **Recorte con medida REAL** (`ProseClamp` en ui.tsx, `TextCard`,
     `PortalClamp`): los planes YA generados llevan los párrafos largos
     guardados, así que el recorte vive también en la vista. El botón "ver más"
     solo aparece si hay desbordamiento real, medido con **ResizeObserver** (una
     medición única daba 0 dentro de un `<details>` cerrado → texto cortado sin
     forma de abrirlo).
   - **Portal (móvil)**: 30+ recortes — cabeceras de pantalla que repetían los
     rótulos de debajo, "Se guarda solo" duplicado con el pie vivo, el mismo
     aviso de pausa redactado de 3 formas en 3 pantallas, protocolo de fotos en
     viñetas, instalación PWA en formato ruta ("Safari → Compartir → Añadir"),
     login, recursos y cuestionario. **3 contradicciones corregidas**: el banner
     decía "Son 2 pasos" y son 6; el subtítulo de la Revisión pedía "rellénala
     al terminar tus 2 semanas" en un bloque que solo aparece cuando YA
     terminaron; Progreso decía "Sube fotos" cuando las fotos se ENVÍAN por
     WhatsApp/email. Y un punto doble ("…en tu plan..") por un "." fuera del join.
   - **Panel**: `EmptyState.hint` pasa a OPCIONAL (obligarlo era el origen de
     media docena de frases de relleno); Dashboard sin los 5 subtítulos que
     repetían su propio botón (la causa del riesgo sube al título para no
     perderla); Clientes, Recursos, SalesKit, AlertsBell y Créditos IA
     telegrafiados.
   - **Emails/push/alertas**: pie de los 16 emails sin la coletilla de marca;
     cuerpos que empezaban repitiendo su titular; `onboarding_pay_anamnesis`
     además estaba DESACTUALIZADO (mandaba descargar el PDF cuando la vía
     oficial es el formulario digital). Push con el QUÉ en el título ("Pendiente
     hoy", "Tu plan del mes 3") y cuerpo de palabras clave — el móvil corta a
     ~40 caracteres y las frases largas no se leían. Alertas: el mensaje dice el
     ESTADO, el botón dice la ACCIÓN (antes lo repetían); en las de alérgenos se
     conserva íntegro el dato de seguridad y se corta solo la instrucción final.
   - **Documentos del cliente**: fuera la sección "Notas del ajuste" (duplicaba
     la celda "Ajuste aplicado" y la tabla de comidas, y pintaba una caja VACÍA
     sin datos); "El plato saludable" de 5 párrafos a 4 líneas; ideas rápidas
     agrupadas manteniendo UNA por línea (el filtro de alérgenos descarta la
     línea entera: agruparlas habría escondido ideas seguras); fuera la trivia
     del cacahuete.
   - **Clasificador clínico**: "No tolera la lactosa" / "No puede flexionar la
     rodilla" se clasificaban como negación irrelevante y se plegaban. Nueva
     excepción `NEG_LIMITACION`: una negación que describe una LIMITACIÓN real
     cuenta como crítica.


000000. ✅ **INFORMACIÓN DEL CLIENTE: menos, mejor y ordenada (agosto 2026).**
   Queja del dueño: "demasiada información mal estructurada, un texto enorme con
   puntos, no se sabe dónde mirar". Inventario UX por 5 auditores (workflow) +
   reestructuración. Principio: NO se pierde ningún dato (la anamnesis manda,
   lo clínico JAMÁS se recorta ni se pliega); se JERARQUIZA la presentación y se
   le ponen topes de ESCRITURA a la IA. Suite (505) + tsc + build en verde.
   - **Prompts de extracción** (`extraction.py`): "lectura exhaustiva, escritura
     selectiva" (excepción sin recorte: lesiones/patologías/alergias/medicación);
     notas por sección en viñetas con PLANTILLA y tope (lifestyle 6 viñetas
     prefijadas por tema empezando por "- Motivo:", medical con prefijos
     Clínica/Digestivo/Salud femenina, sport_history máx 4, suplementos máx 6,
     medicación "Nombre — dosis — frecuencia"); negaciones agrupadas en una
     línea; sin duplicar datos entre secciones; deep_analysis 3-5 puntos de máx
     ~20 palabras (una DECISIÓN por punto). Topes espejados en los Field()
     description (viajan en el schema). Feedback: change ~12 palabras, answers
     2-3 frases/duda, objetivos ~12 palabras. `SYSTEM_PHOTO_ANALYSIS` (huérfano)
     eliminado de prompts.py.
   - **Anamnesis (panel)**: ficha reordenada por lo que el coach necesita —
     chips de seguridad arriba (⚠ alergias + patrón dietético, que NO se
     mostraba: bug), 1ª fila Lesiones+Clínica (lo crítico SIEMPRE visible, nunca
     plegado), Perfil fusionado (datos+antropometría), Medicación+Suplementación
     en una tarjeta, vacíos colapsados ("Sin lesiones declaradas ✓"), notas
     plegadas tras 4 líneas (`VISIBLE_LINES`, orden crítico→relevante→resto con
     lib/clinical), prefijos "Tema:" pintados como subtítulos (`NoteLine`),
     análisis de la IA como lista, toolbar compacta. `DIET_PATTERN_LABEL` en
     lib/format (una verdad para vista+select).
   - **Resumen**: Notas clínicas en DOS niveles (crítico desplegado, informativo
     tras "+N notas informativas").
   - **Seguimiento**: "Puntos a vigilar" de la última revisión PROMOCIONADO a
     bloque fijo arriba (estaba enterrado en el acordeón); MEDIAS del período en
     tarjetas encima de la tabla y la tabla de 14 filas plegada (summary con
     hoy registrado/pendiente); sensaciones solo las ≤3 + chip "Resto en 4-5 ✓";
     "Dudas para ti" primero y a ancho completo; textos largos con line-clamp
     + "Ver más" (con detección real de desbordamiento); peticiones line-clamp-5.
   - **Feedback**: banner "Revisar y adaptar" PRIMERO (encima de videollamada);
     videollamada YA agendada colapsada a una línea (fecha + Unirme); fuera los
     BAStat rotos de perímetros ("— → 92"); rejilla de stats deduplicada (peso
     antes→después + ritmo + a objetivo + adherencia + días); fuerza = línea
     resumen "X de N mejoran" + top 3 + resto plegado (`StrengthRow`); fotos
     plegadas con carga PEREZOSA (`PeriodPhotosFolded`: 0 blobs hasta abrir, y
     avisa "Mostrando 8 de N"); la cuadrícula `plan_adjustments` por fin VISIBLE
     como "Decisiones para la próxima quincena" (antes solo en el Word), bullets
     plegados si hay cuadrícula; dudas del cliente citadas junto a su respuesta
     y destacadas en ámbar; mensaje de cierre plegado.
   - **Planificación**: cabecera con UN chip de estado ("● Activa · la ve el
     cliente"); avisos en dos niveles (bloqueantes rojos siempre visibles;
     ámbar+degraded en details "Avisos de la revisión automática · N" — antes
     ~10 líneas apiladas y los hallazgos >4 se ocultaban SIN contador); "Mes X"
     a la línea de origen; coletillas didácticas fuera (versión más reciente,
     pulsa para cambiar, se renueva solo→title); botonera con menú "Más"
     (Historial/Word/Subir Word, cierra al hacer clic fuera); preview del
     import Word con max-height y botones siempre a la vista; abrir un ejercicio
     ya no cierra el anterior (name compartido quitado); banner re-descarga PDF
     en una línea.

00000. ✅ **SEGURIDAD INTEGRAL (agosto 2026): anti-pirateo / anti-robo /
   anti-copia.** Auditoría de seguridad por 6 dominios con verificación
   adversarial (workflow, 26 hallazgos confirmados/plausibles) + endurecimiento.
   Todo en verde (504 tests). **Ver `SECURITY.md`** para la foto completa y los
   pasos manuales del dueño. Lo implementado en código:
   - **Cabeceras de seguridad HTTP** (`frontend/Caddyfile`): HSTS,
     `X-Frame-Options: DENY` + CSP con `frame-ancestors 'none'` (la web NO se
     puede enmarcar/clonar por iframe), `nosniff`, `Referrer-Policy`,
     `Permissions-Policy` y CSP que solo permite el propio origen + Google Fonts
     + reproductores de vídeo (YouTube-nocookie/Vimeo). La CSP mantiene
     `style-src 'unsafe-inline'` (Tailwind/estilos inline); `script-src 'self'`.
   - **`SecurityHeadersMiddleware`** (ASGI puro en `main.py`, NO BaseHTTPMiddleware
     — para no romper el streaming/Range de los vídeos): `nosniff` en toda la API
     y `Cache-Control: no-store` + `Referrer-Policy: no-referrer` en `/api/p/`
     (portal con datos de salud).
   - **Guardián de secretos** (`config.insecure_secrets()` /
     `blocking_secret_problems()` + gate en `lifespan`): en producción
     (`settings.is_production` = hay dominio) REHÚSA arrancar SOLO si
     `JWT_SECRET`/`PORTAL_TOKEN_SECRET` son los de ejemplo del repo (público). Un
     secreto propio pero <32 solo AVISA (no brickea una prod en marcha). En dev
     todo es aviso. Los tokens de test son cortos pero sin dominio → no bloquea.
   - **`/api/docs` y `/api/openapi.json` ocultos en producción** (docs_url/openapi
     condicionados a `is_production`; redoc off).
   - **CORS**: en producción solo `settings.public_base_url` (localhost solo en
     dev); métodos/cabeceras enumerados (antes `*`).
   - **Manejador 500**: expone el detalle SOLO a coach autenticado
     (`_peticion_de_coach` decodifica el JWT), no por prefijo de ruta — cierra la
     fuga en rutas PRE-login como `/api/auth/login`.
   - **Login sin timing oracle**: `security.dummy_verify` gasta un bcrypt señuelo
     cuando el usuario no existe (mismo tiempo exista o no la cuenta).
   - **`docker-compose.dev.yml`**: todos los puertos a `127.0.0.1` (nunca
     expuestos si se levanta el overlay dev por error en un servidor).
   - **`deploy.yml`**: `git pull` autenticado con `GH_PAT` (cabecera efímera, no
     persiste el token) SI el secreto existe → el repo puede pasar a PRIVADO sin
     romper el auto-deploy; si no existe, pull anónimo como antes.
   - **`.env.example`**: contraseña de Postgres y secretos con instrucciones de
     generación (no valores triviales).
   - Historial de git escaneado: **0 secretos versionados** (seguro para privado).
   - Tests: `tests/test_seguridad.py` (guardián de secretos, gate de arranque,
     CORS, `_peticion_de_coach`, cabecera nosniff, login genérico).
   - **PENDIENTE del dueño (manual, en `SECURITY.md`)**: hacer el repo PRIVADO +
     `GH_PAT`; secretos largos en el `.env`; contraseña real de Postgres; SSH por
     clave + no-root + ufw. Riesgo aceptado documentado: tokens en localStorage
     (mitigado por CSP) y enlaces de portal sin caducidad (revocables a mano).

0000. ✅ **RONDA 3 (agosto 2026): Word de ida y vuelta + créditos al mínimo +
   pulido integral.** Todo en verde (suite completa, tsc, build).
   - **WORD EDITABLE DE IDA Y VUELTA** (petición estrella del dueño): botón
     "Subir Word editado" en Planificación. `services/word_import.py` re-parsea
     el .docx (100% determinista, 0 créditos: el documento lo generamos
     nosotros y sus tablas se reconocen por cabecera + barra de sección):
     kcal/macros del resumen energético (vía `rescale_nutrition` desde la
     base — ANTES de aplicar horas/nombres de tomas, que el rescale
     reconstruye), horas/nombres de tomas (por posición; nº distinto → aviso),
     progresión semanal, tablas de sesión (series/reps/RIR/descanso, celda
     "Clave técnica" des-concatenada en technique_cue / "Indicación para ti" /
     "Cómo progresar", CAMBIO de ejercicio por nombre contra la biblioteca
     canonical+aliases normalizados, altas/bajas de filas), suplementos
     ("Nombre — dosis (momento)", all-or-nothing por caja), deload y pasos.
     `POST /api/plans/{id}/import-word` (multipart, 15 MB, magia PK) devuelve
     PREVIEW {changes (frases de plan_diff + extras), warnings, jsons
     candidatos, base_rev} y NO persiste: el coach confirma en el panel y la
     aplicación va por el MISMO PATCH de siempre (sanitizado, reconcile,
     historial, rev/409, plan_edits→lecciones §13, manual_changes). Lo no
     parseable (recetas del banco, tarjetas, educativo) se avisa → editor web.
     Tests: `tests/test_word_import.py` (e2e con docx real mutado con
     python-docx, rechazo de archivos ajenos, sin-cambios limpio).
   - **CRÉDITOS RONDA 2** (`services/plan_review.review_and_repair` reordenado:
     Revisor 0 gratis primero → reparación determinista ANTES de pagar los
     8-10 roles; banderas rojas del perfil (invariantes) → UNA pasada del
     panel y escalado, adiós al 3× inútil). `max_tokens` POR LLAMADA en
     `AIClient` (whatsapp 300, revisores 2000, lecciones 800, feedback 4000;
     generación conserva 16000). Feedback: payload compacto (sin indent),
     instrucciones muertas de ai_photo_analysis fuera, y `MODEL_FEEDBACK`
     configurable (vacío = pesado; solo redacta, no calcula). Análisis de
     cambio de objetivo cacheado por hash del resumen (sidecar
     `_goal_review.json`; mismo estado → 0 créditos). Ronda WhatsApp: ctx
     compacto + confirmación antes de "Reescribir" (re-paga toda la ronda).
   - **PULIDO INTEGRAL** (36 mejoras verificadas contra el código):
     · PORTAL: objetivo kcal/macros del día en el Diario (api.plan(), estaba
       sin usar); `fmt1`/`shortDate` es-ES en PortalUi (adiós "82.5" y
       "0.30000000000000004"); autosave con pie vivo "Guardando…/Guardado ✓"
       (toast solo errores); "+ Añadir serie" en Entreno (tope 20); aria en
       escalas/adherencia/sensaciones; el cierre dice QUÉ falta exactamente y
       pide confirmación en dos toques; "1 día restante"/"¡toca revisión!";
       hitos de peso celebrados (±1/3/5 kg); login con ojo de contraseña,
       role=alert y autoFocus; fecha corta en el historial de ejercicio.
     · PANEL: pestaña del perfil en la URL (sobrevive a recargar/atrás);
       agenda con "Hoy/Mañana · 17:00" resaltado; estado vacío correcto al
       buscar; Cancelar del alta usa safeClose; tooltips en sidebar contraída;
       "Leer con IA" deshabilitado sin PDF + confirmación de sobrescritura;
       aviso dirty visible en modo ficha; catch con toast al resolver
       peticiones; chip de fallidos de /pagos aplica el filtro; "Ficha act."
       con title honesto; titles en la tabla de registros + fila de hoy
       resaltada; "Cliente desde"/"Último pago" en la ficha.
     · DOCUMENTOS/COMUNICACIÓN: el Word del plan dice MES y fecha de
       generación (month_index no se usaba) y el pie sale de la MARCA (estaba
       hardcodeado); doc_brand pasa tagline/contact_email; bloque de cierre
       "Cualquier duda" con contacto y portal; el informe quincenal lleva
       cabecera/pie/nº de página (setup_branded_pages), portada con FECHAS
       reales del período y objetivo del cliente, y la gráfica de fuerza por
       fin muestra el DELTA vs período anterior (charts ya sabía pintarlo);
       `_fmt_delta` con coma y 1 decimal ("Sin cambios" a 0); email del
       feedback con CTA al portal + INFORME PDF ADJUNTO (gráficas y fotos —
       antes solo texto); push nuevo `notify_feedback_ready` (dq-feedback,
       ?tab=progreso); push del plan personalizado ("Mario, tu plan del mes 3
       ya está listo"); dieta semanal sin filas/tabla vacías; tono unificado
       a primera persona del coach en los recordatorios.

000. ✅ **SIGUIENTE NIVEL DQR · RONDA 2 (agosto 2026)** — el dueño aprobó las 8
   propuestas de la ronda 1 y pidió además aprendizaje de las ediciones del
   coach y recorte del gasto de créditos. Todo implementado y en verde:
   - **Anamnesis DIGITAL como vía oficial** (decisión del dueño — sustituye el
     "Camí A" del §4): `AnamnesisPage.tsx` reescrita como wizard de 6 pasos
     (móvil primero) contra los endpoints que YA existían
     (`POST /api/p/{token}/anamnesis`, consentimiento RGPD con PDF, fotos
     iniciales); nuevo `GET .../anamnesis/prefill` (pre-relleno, 409 tras
     enviar); el PDF queda como alternativa plegada. Unificado "anamnesis
     recibida" en las DOS vías: `consent_signed_at` cuenta en el banner del
     portal, la alerta del panel ("(formulario del portal)"), y los
     recordatorios D+3/D+7; `storage.list_documents` EXCLUYE
     `consentimiento_rgpd.pdf` (se colaba como anamnesis); push 📋 al coach
     también desde el formulario; `send_portal_access` al enviar (alta
     manual); `_links.anamnesis_url` corregida a `/anamnesis/{token}`;
     `daily_activity_level` validado como Literal.
   - **Entreno premium**: temporizador de DESCANSO entre series (píldora
     flotante con cuenta atrás + vibración; arranca al completar peso+reps con
     el `rest_sec` prescrito, que ahora también se muestra) y **récords
     personales** — `GET /p/{token}/workout-history` devuelve `records` (mejor
     e1RM histórico por ejercicio, series ≤15 reps como metrics) y el portal
     celebra 🎉 el PR al registrarlo (sin confeti en la primera sesión: es la
     línea base) y muestra "🏆 Tu récord" bajo el objetivo.
   - **Resumen semanal del coach** (`services/weekly_digest.py` + job lunes
     08:00 + plantilla `coach_weekly_summary`): push 📊 + email con tabla por
     cliente (días registrados /7, Δ peso 14 d, avisos: riesgo/revisión/
     renovación/pago). Idempotente por semana vía EmailLog.
   - **Pagos ronda 2** (mig. 0038): `payments.fee_cents` (comisión de Stripe,
     consultada best-effort SOLO en movimientos nuevos vía
     `_fee_de_cobro`/BalanceTransaction) y `payments.payment_intent`
     (`_cargo_es_nuestro` ahora reconoce cargos por PI → robusto al borrado
     RGPD); resumen con `month_fee_cents` y neto en `/pagos`; **export CSV**
     (`GET /api/payments/export.csv`, BOM+`;` para Excel es-ES, botón
     Exportar); **recordatorio de renovación AL CLIENTE**
     (`services/renewals.py` una sola verdad + email `renewal_reminder` una
     vez por ciclo vía `clients.renewal_reminder_sent_at`, y
     `GET /api/pay/{token}` reabre checkout en ventana de renovación aunque la
     ficha diga paid — antes el CTA moría en /pago-ok).
   - **Aprendizaje del coach (§13 EN VIVO)**: `services/coach_lessons.py`
     destila las filas de `plan_edits` en 3-8 LECCIONES cualitativas (modelo
     ligero; filtro determinista que veta lecciones con cifras — la IA sigue
     sin calcular), sidecar `brand/_coach_lessons.json`, refresco automático
     en el mantenimiento diario (≥5 ediciones nuevas), inyección en el USER
     prompt de los 3 núcleos de generación (no invalida la caché del system), y
     transparencia total: `GET/POST /api/learning/lessons[/refresh]` + pestaña
     "Aprendizaje" en Recursos.
   - **Ahorro de créditos**: PROMPT CACHING transparente
     (`AIClient._system_payload`: system ≥4000 chars → bloque con
     `cache_control`; el PDF de la extracción también se cachea → el reintento
     lee al 10%); el PANEL §9 comparte contexto cacheado entre los 8-10 roles
     (2 bloques: criterio+anamnesis | plan — el bucle de reparación conserva el
     primero); `_record_usage` convierte tokens de caché a equivalentes
     (×1,25/×0,1); el EDUCATIVO baja a `model_light` + caché en sidecar por
     split (`EDUCATION_CACHE_ENABLED`, false en tests) y su fallo ya NO tumba
     el plan full (antes obligaba a repagar núcleo+comidas+panel);
     `_raw_call_with_pdf` con la misma red anti-`temperature` que `_raw_call`.
   - **Auto-despliegue**: `.github/workflows/deploy.yml` — merge a main → SSH
     al VPS → `git pull` + `docker compose up -d --build`. Requiere secretos
     `VPS_HOST`/`VPS_USER`/`VPS_PASSWORD` en GitHub (una vez).
   - **Revisión adversarial del diff (5 confirmados, corregidos)**: subir un
     PDF de anamnesis BORRABA `consentimiento_rgpd.pdf` (prueba legal RGPD
     irrecuperable — excluido del barrido + regresión); errores de la subida
     de fotos del formulario invisibles + contador desincronizado con
     `photos_count`; caché educativa sin versión de prompt (la clave ahora
     hashea los prompts → mejorar el prompt invalida sola); el filtro numérico
     de lecciones podía VACIAR el sidecar pisando las lecciones buenas (ahora
     conserva y reintenta); ventana del resumen semanal era de 8 días ("8/7").
   - Tests: `tests/test_siguiente_nivel2.py` (19) — renovación (ventana, email
     una vez por ciclo, pay_link renovable), resumen semanal (contenido +
     idempotencia), lecciones (destilado, filtro numérico, bloque), caching
     (payload, panel compartido, educativo ligero+caché), récords del portal,
     anamnesis digital (consent no cuenta como anamnesis, banner/alerta/422) y
     pagos (fee+PI, cargo por PI, summary, CSV).

00. ✅ **SIGUIENTE NIVEL DQR (agosto 2026)** — ronda integral sobre el libro de
   caja: Stripe completo en web+móvil, PWA con actualización en caliente,
   auditoría crítica (17 hallazgos confirmados por verificador adversarial +
   triaje manual, TODOS corregidos) y pulido premium. Suite completa en verde,
   `tsc` limpio, build OK.
   - **Stripe visible al 100%**: emoji 💰/💸 en TODOS los push de pagos; la BAJA
     de la suscripción de la oferta ahora es un movimiento del feed
     (`kind=subscription`/`status=canceled`, gris, no suma); un checkout AJENO
     de la misma cuenta (sin `tier` ni `client_id`) se anota como huérfano y NO
     fabrica ficha; **gráfica de ingresos netos de 6 meses** en `/pagos`
     (`GET /api/payments/monthly`, `monthly_series` con meses a cero).
   - **Pagos blindados (triaje de auditoría)**: sin doble resta de devoluciones
     (fila agregada `ch_…` del webhook vs filas `re_…` del sync —
     `record_refunds_of_charge` detecta la agregada y la actualiza);
     `seen` de una devolución por la FECHA DEL REEMBOLSO, no la del cargo
     (`seen_by_age`); contadores de fallidos/huérfanos solo `livemode`;
     `sync_from_stripe` devuelve `partial` si el freno `SYNC_MAX_OBJECTS` cortó
     y **pone al día la ficha** (`_refresca_ficha`: payment_status/paid_at por
     fecha) al repescar un cobro cuyo webhook se perdió; comprar OTRA tarifa por
     el enlace del kit de ventas actualiza `package_tier` (evento de auditoría);
     `checkout.session.async_payment_succeeded` (SEPA/transferencia) se trata
     como `completed` y se suscribe en `ensure_canonical_prices`; rate limit en
     `GET /api/pay/{token}` (cada apertura crea una Checkout Session real).
   - **PWA en caliente** (`frontend/src/lib/appUpdate.ts` + `useAppUpdate` en
     `PortalApp` y `AppShell`): compara el bundle hasheado de `/` (no-store)
     cada 30 min y al volver a primer plano; recarga sola tras ≥5 min oculto o
     muestra banner "✨ actualizado — toca para recargar". El cliente con la
     app instalada recibe cambios SIN reinstalar. El sw.js no cachea assets.
   - **Portal premium**: racha 🔥 de días al día (`portal.streak_days`, cuenta
     solo días CON contenido, hoy vacío no la rompe), anillo de progreso SVG de
     la quincena, refetch de `/state` al volver a primer plano (fecha de negocio
     y videollamada frescas), remount por cambio de fecha de negocio, estado de
     pausa sintético (`review_pending`→closed) en Entreno/Diario/Cierre, CSS
     premium (tabular-nums, stagger de entrada, focus-visible de marca,
     transiciones de botones/nav/chevrons).
   - **Auditoría corregida (lo gordo)**: `CRITERIOS_ASESORIA.md` NO llegaba al
     contenedor (build context `./backend`) → mount en ambos compose +
     `parents[3]` en `prompts.criterios_reference` — sin esto el criterio del
     coach NUNCA se inyectaba en producción; el contenido EDUCATIVO (3ª llamada
     IA) no llegaba al PDF → sección "Aprende con tu plan"/técnica/FAQ en
     `plan_doc` (`_education_section`); recordatorio del día 12 era código
     muerto para `at_risk` (anidado en la rama `active`); el borrador de
     anamnesis de un cliente se FILTRABA al perfil de otro (key del panel de
     pestañas); tolerancias del generador alineadas con el Revisor 0
     (`DET_*`); `check_training` leía `deload` (el schema dice
     `deload_instructions`) → aviso falso siempre; extracción: "mantener" ya
     mapea a `maintenance` (no `recomp`); suelos de macros capados al techo
     calórico DEL OBJETIVO (un cliente pesado en recomp quedaba vetado para
     siempre); textos de objetivo del PDF para maintenance/injury_recovery;
     equivalencias del banco ahora pasan por el Revisor 0 (alérgenos/patrón);
     lista roja con fronteras de palabra ("agotado" ya no dispara GOTA, "sopa"
     no dispara SOP); "cremoso" fuera de los sinónimos de lactosa; separadores
     de miles en `adapt_plan`; commit por iteración al abrir períodos
     (`jobs.py`); alerta `no_logs` cuenta solo días con contenido real;
     `plans[0]`→`vigente()` en el panel de planificación (4 sitios); PATCH del
     plan captura la respuesta del backend; Diario/Cierre del portal: solo
     enteros 0-10, campos de dieta ocultos sin nutrición contratada, banner
     correcto antes del período.
   - Tests nuevos: baja de suscripción en el feed, serie mensual, sync sin
     devoluciones ajenas, checkout ajeno, racha del portal, día 12 at_risk.

0. ✅ **PAGOS: libro de caja de Stripe en la web** (agosto 2026) — el coach ve
   **quién pagó, cuánto y cuándo**, con los cobros como notificaciones tipo app
   de banco. Antes un cobro solo dejaba `payment_status='paid'` + `paid_at`
   (sobrescrito, sin importe): el histórico y las cifras NO existían.
   - **Tabla `payments`** (modelo `Payment`, mig. 0037): un MOVIMIENTO por
     cobro / cobro fallido / devolución, con importe en CÉNTIMOS, moneda,
     `livemode`, fecha REAL de Stripe, cliente (nullable: los pagos huérfanos
     también se anotan) y `seen_at` (NULL = no leído → badge).
     **Idempotencia por `UNIQUE(stripe_object_id, status)`**: una reentrega no
     duplica el ingreso, pero una factura que falla y luego se cobra son dos
     movimientos distintos de la misma factura.
   - **`services/payments.py`**: `record_payment` (best-effort con savepoint —
     la contabilidad NUNCA puede tumbar el webhook), `summary` (mes natural en
     la zona del coach; los pagos de prueba NO suman), `list_payments`,
     `mark_seen`, `anonymize_client` (RGPD) y `sync_from_stripe` (rellena el
     histórico y repesca cobros cuyo webhook se perdió: sesiones de pago único,
     facturas de la oferta y devoluciones).
   - **Webhook ampliado** (`stripe_service`): anota checkout, facturas y el
     evento NUEVO `charge.refunded` (sin él una devolución dejaba saldo falso);
     `ensure_canonical_prices` ya lo da de alta solo en el endpoint de Stripe.
     ⚠️ Las sesiones en modo `subscription` NO se anotan (su dinero llega como
     `invoice.paid`): anotar las dos duplicaría el primer mes de la oferta.
   - **BUG CORREGIDO de raíz**: `_mark_paid` solo escribía si había transición
     `pending→paid`, así que una RENOVACIÓN de pago único no dejaba traza, ni
     aviso, ni refrescaba `paid_at` (y la alerta de renovación contaba desde el
     primer pago para siempre). Ahora el LIBRO decide qué es nuevo
     (`movimiento_nuevo`) y una reentrega sigue sin duplicar avisos.
   - **Panel**: página `/pagos` (`PagosPage.tsx`) con feed agrupado por día
     (Hoy/Ayer/fecha), importes en verde/rojo, chip de "prueba", avisos de
     fallidos y huérfanos, filtros por estado y botón "Sincronizar". Entrada
     "Pagos" en la barra con **badge de no leídos**; al abrir la pantalla se
     sella lo que está A LA VISTA (el resto queda para "Marcar todo como leído").
   - **Push al coach** con el importe en el título (`+129,00 € · Pago recibido`),
     `tag` única por pago (con una tag compartida, dos cobros seguidos se veían
     como una sola notificación) y enlace a `/pagos`.
   - **Revisión adversarial (25 hallazgos → 9 confirmados, todos corregidos)**:
     · devoluciones por REEMBOLSO (`re_…`), no por cargo — `amount_refunded` es
       ACUMULADO y con el id del cargo la segunda parcial se descartaba entera;
     · una devolución de un cobro AJENO de la misma cuenta ya no resta
       (`_cargo_es_nuestro`: simetría con `_invoice_es_de_la_oferta`);
     · `db.commit()` en la rama del impago rezagado (el movimiento se perdía);
     · `client.paid_at` se refresca por FECHA del movimiento, no por "¿escribí
       yo la fila?" (si la sincronización se adelantaba, se quedaba en el pago
       anterior → alerta de renovación eterna);
     · la sincronización deja SIN LEER lo de las últimas 24 h (un cobro reciente
       que aparece por sync = webhook perdido: el coach no se ha enterado);
     · **adopción de huérfanos** (`adopt_orphans`): en el alta self-serve de la
       oferta, Stripe paga la primera factura ANTES de completar el checkout, así
       que el movimiento nacía sin ficha y nadie lo reasociaba (aviso falso
       eterno + el borrado RGPD no llegaba a esa fila);
     · feed: lo que entra mientras miras se resalta y se sella, la fusión
       reordena por fecha real, y tras sincronizar se recarga entero (lo
       recuperado entra POR EN MEDIO, no arriba).
   - Tests: `tests/test_payments.py` (18) — importe/fecha reales, reentrega,
     renovación, huérfano, suscripción sin duplicar, factura fallida+pagada,
     devolución que resta, parciales sucesivas, cargo ajeno, impago rezagado,
     `paid_at` por fecha, sync sin leer, adopción de huérfanos, modo prueba,
     RGPD, feed/marcado/filtro y auth.
   - **De paso**: `tests/conftest.py` no limpiaba nada desde hacía tiempo — el
     `DELETE` de `plans` fallaba por `plan_edits` (FK sin ON DELETE) y el
     `except` mudo hacía rollback de TODA la limpieza. Arreglado y con aviso
     visible si vuelve a fallar.

1. ✅ **Edición del plan en la web** (`ClientPlanEditor` + `PATCH /api/plans/{id}`):
   se edita nutrición (kcal/macros/suplementos/reglas), entreno (sesiones,
   ejercicios, progresión, cardio, deload) y se guarda. Pendiente menor: editar el
   **banco de comidas** (28 opciones) y cambiar ejercicio (eso es el `swap`).
   El contenido educativo se omite en la UI. NOTA (agosto 2026): el dueño
   DESCARTÓ rehacer el diseño desde un PDF de ejemplo — **se queda el diseño
   actual de las planificaciones** como definitivo.
2. ✅ **Lectura de PDF con IA probada contra la API real.** El esquema y el prompt
   de `extraction.py` se ampliaron para cubrir TODAS las secciones del PDF y se
   verificó con un PDF rellenado: extrae los 12 campos obligatorios + las notas por
   sección. Los PDFs reales escritos a mano serán más sucios; vigilar los enums.
3. ✅ **Ciclo completo cableado y probado (con IA real):** publicar plan →
   **"Iniciar seguimiento"** (crea período) → el cliente en el portal registra
   entreno (**Entreno**: series, selector de sesión, autosave), diario (peso/sueño/
   adherencia/ánimo), elige comidas y, en "Hoy", ve un **medidor de días** + checklist;
   al día 14 cierra (peso final, perímetros, valoración, **fotos**) → el cliente pasa a
   `review_pending` y en el **perfil del coach aparece una notificación**. El coach:
   **"Resumen"** (métricas sin IA), **"Generar feedback"** (IA → borrador + Word, ve las
   **fotos**), y **"Enviar al cliente"** → `FeedbackDoc.sent_at` + `review_pending→active`
   (cierra la notificación) + email. Solo al ENVIAR el cliente lo ve en su **"Progreso"**.
4. ✅ **Test frágil robustecido** (email único, ver §7).
5. ✅ **Tests de integración limpian la BD al terminar** (`tests/conftest.py`):
   al final de la suite se borran los clientes de dominios de prueba
   (`@example.com`, `@test.local`, `@x.com`) con TODAS sus filas dependientes y
   sus archivos — `pytest` ya no ensucia el panel de desarrollo.
6. ~~Subir el PDF de ejemplo de planificación~~ **CANCELADO por el dueño**
   (agosto 2026): se mantiene el diseño actual de las planificaciones.
7. ✅ **Videollamadas Pro con Google Calendar / Meet** (guía: `GOOGLE.md`).
   Flujo: el coach conecta su Google UNA vez en **Recursos → Página de enlaces**
   (OAuth). Al **enviar la revisión quincenal**, al cliente Pro le aparece en su
   **portal** un formulario para **PROPONER día y hora**. El coach lo ve en su
   **agenda del Panel** y en la pestaña **Feedback**: puede **ACEPTAR** (crea el
   evento en Google Calendar con **Meet**, invita al cliente por email y le manda
   el enlace) o **MODIFICAR** (abre WhatsApp para acordar otra hora → queda
   *pendiente de agendar a mano* → el coach escribe el día/hora → mismo resultado).
   Estados de `VideoCall`: `proposed → accept|modify → scheduled|pending_manual →
   done`. Recordatorios multicapa (coach y cliente): invitación nativa de Google +
   email de la app (`video_call_scheduled`) + push del portal + **recordatorio el
   día antes y 1 h antes** (`push.run_video_call_reminders`, job cada 15 min) +
   email día antes (`video_call_reminder`, job diario) + tarjeta **"Unirme"** en
   el portal. Reprogramar/cancelar sincroniza el evento en Google.
   - Backend: `services/google_calendar.py` (OAuth + Calendar/Meet vía `httpx`,
     sin librerías pesadas de Google), `routers/google_oauth.py`
     (`/api/google/status|oauth/start|oauth/callback|disconnect`). Coach:
     `POST /clients/{id}/video-calls/{call_id}/accept|modify`,
     `.../schedule-meet` (a mano), `GET /api/video-calls/agenda` (agenda del
     Panel). Portal (público): `GET|POST /api/p/{token}/video-call` (estado +
     proponer). Modelo `GoogleCredential` (fila única con `refresh_token`) +
     columnas en `video_calls` (`scheduled_at`, `duration_min`, `meet_url`,
     `google_event_id`, `google_html_link`); migraciones `0026` (columnas) y
     `0027` (status a VARCHAR(20)). Config: `GOOGLE_CLIENT_ID/SECRET`,
     `GOOGLE_CALENDAR_ID` (gate `settings.google_enabled`, como Stripe).
   - Frontend: "Conectar con Google" en `RecursosPage`; en el portal
     (`PortalApp` → `VideoCallBanner`) el cliente propone/ve estado/"Unirme";
     en `ClientFeedbackTab` (`VideoCallCycle`) el coach acepta/modifica/agenda a
     mano; agenda de videollamadas en `DashboardPage`.
   - Sin claves de Google en el `.env`, la integración queda desactivada (aceptar
     pide conectar Google). Tests: `test_google_calendar.py` (servicio) +
     `test_video_calls.py` (propuesta/aceptar/modificar/agendar, `gcal` mockeado).
   - **Mejoras del ciclo (pulido):**
     · **Reprogramar desde el portal del cliente:** una videollamada YA agendada
       puede reprogramarla el propio cliente si no le va bien la hora
       (`POST /api/p/{token}/video-call/reschedule`, botón "¿No te va bien?
       Reprogramar" en `VideoCallBanner` estado *scheduled*). Cancela el evento en
       Google, vuelve a `proposed` con la nueva fecha, limpia los campos de Meet y
       avisa al coach por push (`notify_coach_video_call_rescheduled`) para que la
       vuelva a confirmar.
     · **Confirmación clara del coach en el portal:** la tarjeta *scheduled* dice
       explícitamente "Tu coach ha confirmado tu videollamada" con la fecha/hora y
       el enlace de Meet pegado; el push al cliente lo confirma igual
       (`notify_video_call_scheduled`).
     · **Aviso al cliente para que proponga su videollamada** si no lo hace: si es
       Pro y su última revisión está cerrada sin propuesta, entra en los
       recordatorios push cada 3 h (`push.videocall_pending` → `pending_for_client`
       → `build_reminder_payload`: "agendar tu videollamada de revisión") hasta que
       la agende.
8. ✅ **Auditoría integral a fondo (julio 2026)** — 6 auditorías por dominio
   (pipeline IA, coherencia nutricional, ciclo quincenal, portal, panel del
   coach, infraestructura) con TODOS los hallazgos confirmados corregidos:
   - **Seguridad:** los sinónimos de alérgenos/lesiones con `"\b"` (backspace,
     no frontera de palabra) NO detectaban "pan"/gluten, "maní", "soja", "LCA",
     "L4" — corregido con raw strings + tests de regresión. `temperature` al
     modelo pesado (gotcha §5.2, reintroducido por §14) filtrado en un único
     sitio (`AIClient._effective_temperature` + reintento sin él). Un plan con
     `violation:` de guardrail o semáforo ROJO ya NO se auto-activa ni avisa al
     cliente (queda en borrador con flag "retenido"). El contrato de macros del
     backend se IMPONE al eco de la IA en el camino bloqueante (desvío → se fija
     al contrato y se reescala). Panel §9: un revisor caído ya no fabrica un
     "aprobado 60" — queda `no_ejecutado` (mayor si tenía veto) y el resumen
     lleva `degraded_reviewers`. Coherencia dieta⇄entreno (§6) integrada en la
     generación viva (flags).
   - **Motor quincenal §8 enchufado de verdad:** la decisión determinista se
     calcula ANTES de la llamada de feedback y viaja en el payload como contrato;
     en `adapt_plan`, si la regla dice no tocar kcal (hold/adherencia/datos) el
     cambio de la IA se VETA, y si dice ajustar X% el número lo pone el motor
     (proteína bloqueada). Editar el texto del feedback ya no borra
     `biweekly_decision`; `plan_adjustments` es editable (FeedbackEditIn).
   - **Coach se entera de TODO:** push inmediato al cerrar una revisión y al
     entrar un pago/alta de Stripe; alertas nuevas `payment_pending` y
     `period_overdue`; la petición de cambio muestra su TEXTO y se puede LEER y
     RESOLVER desde Seguimiento (antes era una alerta eterna sin UI); las fotos
     de progreso del período se VEN en Feedback; videollamadas huérfanas
     (proposed/pending_manual de revisiones anteriores) ya no desaparecen; los
     push de videollamada llevan `?tab=feedback` y el sw.js ya no enfoca
     cualquier pestaña del portal en vez del destino.
   - **Portal:** guardar diario/entreno funciona del día 15 hasta enviar la
     revisión (antes 422 silencioso con pérdida de datos); errores de carga con
     "Reintentar" (antes skeleton infinito) y toasts con el mensaje real; fallo
     de red ya no dice "enlace caducado"; el aviso "plan nuevo" se apaga también
     en Start; el resync automático de push NO roba el dispositivo de otro
     cliente; carrera del primer guardado del día resuelta con savepoint.
   - **Coherencia:** `_rhu` (half-up) también en `clamp_targets`/`reconcile`/
     `rescale_nutrition`/`meal_fallback` (adiós al bancario en valores
     persistidos); portal y PDF deciden el formato del banco por `bank["mode"]`;
     swap activa la versión nueva y respeta "gym sin restricción de material";
     fecha de negocio (`today_local`) en seguimiento, alertas y badge.
   - **Extracción:** enums normalizados con sinónimos ("Hombre"→male,
     "Gimnasio"→gym…); lo irreconocible queda VACÍO (nunca un cálculo corrupto).
     `sport_history` y `goal_weight_kg` ahora llegan al prompt de generación.
   - **Infra:** `SCHEDULER_ENABLED` en Settings y `.env.example`; `freezegun` en
     requirements; caché correcta en Caddy (index/sw revalidan, assets
     inmutables); recordatorio del día 12 incluye a los `at_risk` y hay
     recuperación `at_risk→active`; "en riesgo" ya no cuenta filas de diario
     vacías; sensaciones del cierre acotadas 1–5.
   - **Barrido anti-fallos de EDICIÓN (tras fallos reales encontrados por el
     dueño en el editor):** el editor de nutrición pasó a EDICIÓN LIBRE —
     0/vaciar permitido, ningún campo se reescribe con el foco, aviso
     PERSISTENTE de descuadre con cifras y cuadres de un clic, topes de
     seguridad como AVISO bloqueante (nunca reescritura silenciosa;
     `targetBounds` + `rescaleNutrition(..., clamp=false)` en el editor),
     chip permanente de déficit/superávit, kcal escala desde el mix ACTUAL
     (no el baseline), guard de Safari/Firefox (blur antes de cuadrar),
     reestructurar comidas exige totales cuadrados, y un plan legado
     descuadrado no bloquea guardar entreno (`nutTouched`). En el PORTAL:
     inputs a prueba de móvil (`useDecimalField`: coma o punto, inválido/fuera
     de rango NO viaja — antes "82,5" no reconocido enviaba null y BORRABA el
     peso o la serie guardada), rangos espejo del backend, re-encolado del
     autosave fallido, 422 traducidos con el campo en español, fecha congelada
     a medianoche, maxLength en pasos y rangos exactos en el cierre. En el
     PANEL: campos CSV (¡alergias!) y reglas de flexibilidad ya no se comen
     comas/espacios/Enter al teclear, fecha de nacimiento vaciada → null,
     créditos IA vacío ≠ $0, confirmación al descartar el modal de cliente o
     salir con el editor del plan/anamnesis abiertos (+beforeunload), y fecha
     de videollamada validada con el porqué en el botón.
   - **Auditoría de conectividad + banco de 100 perfiles (agosto 2026):** tres
     auditores de código (ciclo, ediciones, matemática determinista) + un banco
     de 72 perfiles sintéticos ejecutando el pipeline REAL (metrics → macros →
     filtros → banco fallback → Revisor 0 → motor quincenal). Corregido TODO lo
     confirmado:
     · **CRÍTICO — unidades del motor quincenal:** `kcal_delta_pct` emitía la
       FRACCIÓN (0.06) y `adapt_plan` dividía entre 100 → el ajuste ±6% del §8
       se aplicaba como ±0,06% (no-op). Contrato fijado en PUNTOS porcentuales
       (±6.0) + test e2e. Nueva regla `deriva_no_deseada` (mantenimiento/recomp
       con >0,45%/sem). Adherencia 0.0 real ya no se lee como 1.0.
     · **Alérgenos:** lookup inverso de sinónimos roto con términos raw-string
       ("maní" no detectaba cacahuete; "pan" no expandía a trigo/pasta) —
       corregido + regresión. Patrones veganos ⊇ vegetarianos (programático).
       Topes de porción nuevos: cereal seco 300 g crudo, líquidos 1 L.
     · **Banco fallback:** aversiones ahora VETAN igual que el Revisor 0 (antes
       colaba pescado a quien lo odia y el plan entero quedaba retenido);
       plantillas comodín sin los 6 grandes alérgenos (multialérgico cubierto);
       kcal de cada opción = 4/4/9 EXACTO de sus macros; porciones capadas con
       redistribución. El solver también declara kcal=Atwater (adiós vetos
       falsos por la fibra de las etiquetas) y redondea half-up.
     · **Obesidad:** los suelos de macros por kg total invertían el déficit
       (fat_loss en superávit sin aviso) → capado al TDEE + nota; suelo calórico
       ≥ TDEE avisa "esto es mantenimiento". Edad acotada con aviso; e1RM
       ignora series >15 reps; weight_trend descarta outliers (4·MAD).
     · **Adaptación:** cláusulas de macros ya NO puentean el veto de kcal del
       §8 (rebalanceo a las kcal previas); `check_nutrition` corre ANTES de
       auto-activar la adaptación (violación → borrador retenido); "%s" del
       texto de la IA interpretados como relativos (antes −10% = −10 g).
     · **Ciclo:** alerta `adapt_plan` anclada al último período ANALIZADO
       (sobrevive al envío del feedback); push al coach cuando el CLIENTE sube
       su anamnesis (con aviso si la lectura IA falló); `inactive` ya tiene
       salida (botón Reactivar + auto-reactivación por actividad del portal +
       push/alerta al caer); recordatorios D+3/D+7 al onboarding sin anamnesis;
       banner del portal "completa tu anamnesis"; videollamadas `proposed`/
       `pending_manual` se pueden cerrar sin Google ("Marcar hecha");
       change-request con push inmediato; pago huérfano de Stripe avisa;
       `awaiting_feedback` (estado muerto) eliminado; "Al día" excluye at_risk;
       "enviar feedback por email" comprueba `email_status` de verdad.
     · **Ediciones:** PATCH de planes con control de concurrencia optimista
       (`base_rev` + rev en nutrition_json → 409 con mensaje claro; PATCH sobre
       `superseded` → 409); snapshot `gen_inputs` al generar + alertas
       `plan_stale_inputs` (ficha cambiada tras generar) y
       `plan_allergen_conflict`/`plan_dislike_conflict` (alergia añadida con
       plan activo) EN VIVO; `guardrail_flags` y hallazgos ÁMBAR/degraded del
       panel §9 por fin visibles en la UI; editor de feedback avisa si YA se
       envió y permite editar `plan_adjustments` ANTES de Adaptar; "Descartar
       aviso" con confirmación; manifest PWA con el nombre real de la marca;
       etiqueta "Peso actual" corregida a "Peso inicial".
     · **Biblioteca de casa:** +22 ejercicios de peso corporal/bandas
       (seed insert-por-nombre en cada arranque) — un cliente de casa sin
       material pasaba el filtro con 5-11 ejercicios; ahora ≥14 con ≥7 grupos.
       Aviso en generate-plan si la biblioteca filtrada queda fina y si alguna
       toma queda sin opciones seguras. Rama "gym" del filtro fijada como
       "sin restricción de material" real (era una allowlist encubierta).
     · Banco de perfiles reproducible en scratchpad (`audit100/run.py`):
       0 hallazgos tras las correcciones. Suite ampliada con
       `tests/test_auditoria_integral.py`.
   - **Backlog técnico APLICADO (agosto 2026)** — todos los pendientes
     detectados por la auditoría quedaron implementados y testeados:
     · **Patrón dietético real** (`clients.diet_pattern`, mig. 0032, enum
       vegano|vegetariano|pescetariano|sin_cerdo|halal|kosher): select en la
       pestaña Anamnesis → `filter_foods` + prompt + Revisor 0 + banco fallback
       (plantillas veganas propias) + alerta viva sobre el plan publicado.
     · **Peso de referencia único** (`services/periods.reference_weight_kg`:
       último diario > cierre > current > inicio) usado por generate-plan,
       PATCH de planes, adaptación y expuesto en `ClientOut.reference_weight_kg`
       para el editor.
     · **Recomendación de macros unificada**: endpoint
       `GET /clients/{id}/macro-recommendation` (energy_targets+macro_targets
       reales del backend); el editor lo consume y solo cae a su fórmula local
       sin red. Adiós a las "dos fórmulas".
     · **Historial/revert de planes (§4 cableado)**:
       `services/plan_history.py` (sidecar `_plan_{id}_history.json`, tope 20),
       snapshot automático ANTES de cada PATCH,
       `GET /plans/{id}/history` + `POST /plans/{id}/revert` (snapshotea lo
       actual antes de restaurar → revert reversible; sube `rev` → 409 en
       pestañas rancias), botón "Historial" en `ClientPlanPanel`.
     · **Paridad de PLAN COMPLETO**: vectores `rescaledPlan` en el contrato
       (backend `rescale_nutrition`+`reconcile_nutrition(clamp=False)` ⇄ editor
       `rescaledFrom(clamp=false)` byte a byte, banco flexible Y strict); el
       backend ya no inyecta `household: None` (rompía la paridad).
     · **Motor quincenal**: `menstrual_confound` derivado (mujer + repunte
       ≥0,5 kg en los últimos 3 días, ≥5 pesajes); `weeks_in_deficit` solo
       cuenta períodos cuyo plan tenía `target_kcal < tdee_kcal`.
     · **`_align_bank_slots` cubre strict**: el menú semanal también se
       reescala al objetivo de su toma (>5% de desvío).
     · **`check_training`**: volumen por grupo cuenta `muscle_secondary` a 0,5
       y avisa si falta `weekly_progression`/deload declarados.
     · **Portal**: fecha de NEGOCIO (`PortalState.today`, zona del coach) manda
       sobre el reloj del dispositivo en Diario/Entreno (viajes); scope de la
       PWA ampliado a `/p/` (sobrevive a la rotación del token).
     · **Front**: code-splitting por ruta (React.lazy + chunk vendor) — el
       portal baja de ~940 KB a ~290 KB; recharts (~385 KB) solo carga donde
       hay gráficas. `docs_theme` retirado del contrato (control muerto).
     · **"Marcar pagado" a mano** sella `paid_at`; borrado RGPD ya elimina
       `video_calls` (FK NOT NULL sin ON DELETE que reventaba el commit).
     · Regresiones nuevas en `tests/test_auditoria_integral.py` (historial/
       revert, confound, déficit real, strict align).
   - **Auditoría de CALIDAD (agosto 2026)** — 7 dominios auditados por pares
     (buscador + verificador adversarial): PDF/documento del cliente, portal,
     revisión quincenal, panel del coach, alta y pagos, anamnesis y emails.
     72 hallazgos, 70 confirmados. Corregido en dos tandas:
     · **Producto del cliente:** el cliente **Full** recibía el PDF **sin
       entrenamiento** (`plan_delivery` solo lo incluía si NO había nutrición);
       en modo `strict` el menú semanal (gramos, medidas caseras y preparación)
       **no se imprimía**; el filtro de alérgenos del documento no compartía
       criterio con `guardrails` (ni patrón dietético → se colaban huevo/pavo a
       un vegano); tarjetas de plantilla y suplementación por defecto impresas
       aunque el plan no las pautara; los ejercicios no decían **cómo
       progresar**. En el **portal**: el cliente no podía **ver ni descargar su
       plan en PDF** ni sus **revisiones** (ahora `/api/p/{token}/plan.pdf` y
       `/api/p/{token}/feedback/{id}.pdf`). En el **feedback**, la IA inventaba
       un "análisis de fotos" que nunca vio (campo forzado a null).
     · **Facilidad de uso del coach:** cierre de la quincena **por el coach**
       (`POST /periods/{id}/close-by-coach`) — sin él, un cliente que no enviaba
       su revisión **bloqueaba el ciclo entero**; botón para **reenviar el
       cuestionario** por WhatsApp desde la ficha; alerta **`renewal_due`** (los
       planes de 1/3/6 meses se cobran una vez y nadie recordaba renovarlos); el
       **mes de asesoría avanza** con el ciclo (`periods.current_month_index`,
       dos revisiones = un mes) en generar/base/adaptar — antes el PDF decía
       "Mes 1" de por vida; "Generar feedback" aterrizaba en la pestaña
       equivocada; **Cancelar** en el editor ya pide confirmación; y
       `/api/alerts` deja de barrer todos los clientes cada 3 s desde dos sitios
       (refresco propio `ALERTS_REFRESH_MS` = 20 s).
   - **Pendiente menor restante** (sin urgencia): editar el banco de comidas
     opción a opción desde el editor y el `swap` de ejercicios desde la web.
     ~~Decisión pendiente del dueño: anamnesis PDF no rellenable vs formulario
     digital~~ **RESUELTO (agosto 2026)**: el dueño aprobó el formulario
     digital como vía oficial (ver §4 y la ronda 000 de arriba).

---

## 10. Cómo trabajar en este repo con Claude Code (tips prácticos)

- **Antes de un cambio de IA:** recuerda los gotchas de §5 (sobre todo
  `from __future__` y `temperature`).
- **Tras cambiar código:** en dev recarga solo; si tocas dependencias o el
  Dockerfile, reconstruye (`up --build`).
- **Para depurar un 500:** lee el log del contenedor `api` (Traceback completo).
- **Para validar sin gastar API:** usa el AIClient falso de los tests.
- **El código manda:** este documento resume el estado a fecha de traspaso, pero
  si algo no cuadra, la verdad está en los archivos. Verifícalo.
```
