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

> **Hardening v2 en curso** (rama `hardening/asesorias-v2`, sin mergear). Ver
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
> - **Criterio de coach**: `CRITERIOS_ASESORIA.md` (rellenar `[PENDIENTE TONI]`).
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
1. ANAMNESIS (1 vez)  → "Camí A": el coach descarga el PDF oficial de DQ
   (GET /api/anamnesis-template), lo envía por correo manualmente, el cliente
   lo rellena y lo devuelve. El coach lo sube al perfil del cliente.
   · Al subirlo, la IA lo LEE automáticamente y rellena la ficha.
   · Una sola anamnesis por cliente (subir otra reemplaza la anterior).
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

**Decisión de diseño (Camí A):** la anamnesis oficial es el PDF de DQ. NO se usa
un formulario digital largo en el portal; el PDF es el documento maestro. La IA
lo lee, pero el coach revisa antes de generar (seguridad > automatización ciega).

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

- **99 tests en verde** en base de datos limpia.
- Los tests pueden **inyectar un AIClient falso** (scripted) para probar todo el
  pipeline sin llamar a la API real (ver `tests/test_ai_service.py`). Útil porque
  la API real necesita la clave y cuesta dinero/tiempo.
- ✅ El test antes frágil (`tests/test_phase2.py::test_export_with_accented_name`)
  ya usa un email único con uuid; pasa aunque la BD arrastre datos previos.
- ⚠️ **Los tests de integración escriben en la MISMA BD de desarrollo** y dejan
  clientes `@example.com` (p. ej. los del checklist A.3). Tras correr `pytest`,
  aparecen en el panel. Pendiente: aislarlos (transacción con rollback o BD de
  test aparte). Mientras tanto, se limpian borrando los `@example.com`.

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

1. ✅ **Edición del plan en la web** (`ClientPlanEditor` + `PATCH /api/plans/{id}`):
   se edita nutrición (kcal/macros/suplementos/reglas), entreno (sesiones,
   ejercicios, progresión, cardio, deload) y se guarda. Pendiente menor: editar el
   **banco de comidas** (28 opciones) y cambiar ejercicio (eso es el `swap`).
   NOTA: el contenido/estructura/colores de la planificación se rehará a partir de
   un **PDF de ejemplo** que subirá el dueño; la IA generará siguiéndolo. El
   contenido educativo se omite en la UI.
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
5. **Aislar los tests de integración de la BD de desarrollo** (ver §7): hoy
   ensucian `clients` con `@example.com` en cada `pytest`.
6. **Subir el PDF de ejemplo de planificación** y ajustar el prompt/estructura del
   plan para que la IA lo replique (estructura, contenido, colores).
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
