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
- **LECTOR UNIVERSAL (septiembre 2026):** la anamnesis ya NO tiene que ser el
  PDF oficial. Cualquier fichero (PDF, Word, fotos —varias = un documento—,
  Excel, texto) pasa por `services/document_reader.normalizar[_varios]` →
  `AIClient.read_document_json` → `extraction.extract_anamnesis_from_document`
  (prompt por SIGNIFICADO + doble pase de verificación). La subida LEE antes de
  guardar y desvía a ADJUNTO lo que no es un cuestionario. Los adjuntos también
  se leen (`services/attachments.py`) y entran en las notas de la ficha y en el
  contexto de generación. Un plan AJENO se importa con `services/plan_import.py`
  (la IA transcribe, el backend pone las cifras). Ver §9, entrada 02/03-09-2026.
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

POST /api/clients/{id}/documents           Subir anamnesis (PDF/Word/fotos/Excel/texto; `file` o `files`;
                                           LEE antes de reemplazar; desvía a adjunto lo que no es cuestionario)
                                           o `kind=adjunto` (se LEE también).
GET  /api/clients/{id}/documents           Listar documentos.
GET  /api/clients/{id}/documents/{name}    Descargar un documento (requiere JWT).
POST /api/clients/{id}/read-anamnesis      Leer la anamnesis (cualquier formato) con IA y rellenar la ficha.
POST /api/clients/{id}/documents/{name}/read  (Re)leer un documento: adjunto → ficha; anamnesis → como arriba.
DELETE /api/clients/{id}/documents/{name}  Borrar documento (un adjunto leído retira su bloque de la ficha).
GET  /api/clients/{id}/attachments         Adjuntos LEÍDOS: resumen, alertas, marcadores fuera de rango.
GET  /api/clients/{id}/anamnesis-analysis  Síntesis + contradicciones + verificación 2º pase + inventario + adjuntos.
POST /api/clients/{id}/plans/import-document          PREVIEW de un plan desde un documento ajeno (IA transcribe).
POST /api/clients/{id}/plans/import-document/confirm  Crea el borrador (camino de copiar_a_cliente).
POST /api/p/{token}/adjuntos               (Portal) el cliente sube analítica/informes; se leen; push al coach.
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

- **793 tests en verde** en base de datos limpia y migrada a head, y también
  **en orden inverso** (`ls tests/test_*.py | sort -r`): correrlos al revés es
  la forma barata de destapar tests que solo pasan por lo que corrió antes
  (destapó dos fallos reales de aislamiento).
- `tests/test_migraciones.py` comprueba el arranque DESDE CERO: crea una base
  temporal y corre `alembic upgrade head` entera (el camino del día que se
  pierda el VPS, que estaba roto y nadie veía).
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

**Y el frontend** (obligatorio antes de fusionar nada de `frontend/`):

```bash
cd frontend && npx tsc --noEmit && npm run build
npm run lint:hooks          # Rules of Hooks: un hook tras un return temprano
                            # deja la app EN BLANCO en runtime. Debe dar 0/0.
npm run check:anclas        # cada destino del backend tiene su ancla en la web
npm run check:avisos        # los avisos del panel, en español y sin duplicar
npm run check:claves        # toda clave guardada del portal lleva el token
npm run check:portapapeles  # una sola puerta al portapapeles (`lib/clipboard`)
```

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

0000000000000000000000. ✅ **LECTOR UNIVERSAL DE DOCUMENTOS (02/03-09-2026).** Petición
   del dueño: cualquier camino de DQR que lea información tiene que leer
   CUALQUIER documento, con la estructura que sea, y hacer después lo que toque
   (ficha, planificación, análisis). Hasta aquí la lectura estaba atada a dos
   formas conocidas (el PDF oficial de la anamnesis y el Word que generamos) y
   todo lo demás se rechazaba en la puerta («Solo se admiten archivos PDF») o
   ni se leía (los adjuntos). Implementado y en verde:
   - **`services/document_reader.py`** — normaliza CUALQUIER fichero a bloques
     que la IA lee en su forma nativa: PDF → bloque `document` (troceado a 100
     págs con pypdf); Word/ODT/RTF/DOC → LibreOffice a PDF (`office_bytes_to_pdf`,
     tablas intactas) con RESERVA de texto de python-docx si la conversión falla;
     fotos → enderezadas por EXIF, ≤1568 px, JPEG ≤5 MB, **varias fotos = UN
     documento** (se guardan como un PDF de N páginas); Excel → tabla de texto
     (openpyxl; Calc no está en la imagen); texto/CSV/MD tal cual. **La magia
     manda sobre el nombre.** HEIC e ilegibles → `DocumentoIlegible` con mensaje
     para humanos. Deps nuevas: `pypdf`, `openpyxl`.
   - **`AIClient.read_document_json`** (+ `_raw_call_with_blocks`): la ÚNICA ruta
     real para leer documentos (image/document/text), `cache_control` en el
     último bloque, mismo trato del corte por longitud que `generate_json`.
     `read_pdf_json`/`_raw_call_with_pdf` son ya atajos de esta.
   - **Anamnesis desde cualquier forma** (`ai/extraction.py`): el prompt busca
     INFORMACIÓN, no casillas (cuestionario de otro profesional, fotos de una
     hoja manuscrita, WhatsApp pegado, Excel…); `document_kind`,
     `source_inventory` (qué contenía), `unmapped_info` (lo sin casilla → va a
     `lifestyle_notes` como «Otros datos del documento», no se pierde) y
     `confidence` por campo crítico. **DOBLE PASE §5 por fin cableado**
     (`verificar_extraccion` + `comparar_pases`, flag `EXTRACTION_DOUBLE_PASS`):
     una relectura del MISMO documento (cacheado → ~10 %) comprueba los campos
     críticos; las discrepancias se ENSEÑAN al coach (`verification` en la
     respuesta, el sidecar y `GET /anamnesis-analysis`), nunca se resuelven
     solas; dos lecturas que coinciden suben la confianza. La duda dice EN QUÉ
     campo (`low_confidence_labels` + `resumen_de_dudas`, espejo `resumenDudas`
     en `lib/documentos.ts`): desajustes, confianza baja y datos echados en falta,
     cada motivo con su nombre.
   - **LEER ANTES DE GUARDAR + DESVÍO** (`ingest_anamnesis_document`): la subida
     de la anamnesis lee el documento ANTES de tocar la anterior; si la IA lo
     clasifica como analítica/informe/plan (`_KINDS_NO_ANAMNESIS`) se guarda
     como ADJUNTO y se lee como tal (`redirected_to: "adjunto"`, aviso, push al
     coach si vino del portal) — así una analítica subida por el botón
     equivocado ni borra el cuestionario ni pisa la historia clínica. El 2º pase
     no se paga en esos casos. «Leer con IA» sobre el fichero ya guardado
     conserva el aviso `document_warning`.
   - **Adjuntos LEÍDOS** (`services/attachments.py`): la analítica/informe que
     antes se guardaba y nadie leía se transcribe (`AttachmentExtraction`:
     marcadores con rango y bandera, clínica, lesiones, medicación, suplementos,
     pautas previas, ALERTAS) y se fusiona en las notas de la ficha con un
     BLOQUE MARCADO `[Adjunto: stem]` por adjunto — idempotente al releer, se
     retira al borrar, nunca pisa lo del coach; la analítica va compacta (fuera
     de rango una línea por marcador; normales agrupados). Sidecar
     `_adjunto_<stem>.json`; `attachment_context()` entra en `deep_analysis`
     de `generate-plan` (y por las notas, en el panel §9 y `safety_gate`).
   - **Plan desde un documento AJENO** (`services/plan_import.py`): la IA
     TRANSCRIBE (`PlanDocumentExtraction`); el backend pone las cifras — kcal/
     macros del CONTRATO (`_contrato_del_destino`; si el documento declara
     otras, se avisa), ejercicios contra la biblioteca (canónico+alias+palabras
     clave, único candidato; lo demás se avisa y no entra), alimentos contra la
     base con macros recalculados (sin gramos → se conserva lo escrito + aviso,
     tag `macros_por_revisar`), tomas con hora por NOMBRE, «2 min» → 120 s,
     menú por días → `strict`. PREVIEW sin persistir + CONFIRM → borrador por
     `copiar_a_cliente` (reescala, completa, avisos de seguridad; cazó el
     alérgeno «leche» de un cliente con lactosa en el primer smoke test).
   - **Endpoints**: `POST /clients/{id}/documents` acepta `file` o `files` y
     cualquier formato (kind anamnesis|adjunto; el adjunto SE LEE, best-effort);
     `POST /clients/{id}/documents/{name}/read`; `DELETE /clients/{id}/documents/{name}`;
     `GET /clients/{id}/attachments`; `GET /clients/{id}/documents/{name}` sirve
     el MIME real; `GET /anamnesis-analysis` devuelve verificación/inventario/
     sin casilla/adjuntos; `POST /clients/{id}/plans/import-document` (+
     `/confirm`); portal: `POST /p/{token}/anamnesis-pdf` acepta `files` (fotos)
     y `POST /p/{token}/adjuntos` (cualquier estado salvo inactivo, tope 12,
     push al coach con lo hallado).
   - **Frontend**: `lib/documentos.ts` (lista de aceptación compartida), subida
     multi-fichero en `ClientDocuments` (badge de formato, resumen/alertas/
     fuera de rango por adjunto, «Leer con IA», «Borrar»), pestaña Anamnesis con
     discrepancias del 2º pase, aviso de documento, inventario y adjuntos
     leídos; «Importar desde documento» en Planificación (preview + «Crear
     borrador»); portal: anamnesis en PDF/Word/fotos y bloque «Analítica o
     informes».
   - **Tests**: `tests/test_lector_universal.py` — normalización de cada
     formato, cliente IA con reintento, anamnesis desde notas de WhatsApp,
     doble pase (coincidencia/discrepancia/fallo), desvío a adjunto, adjuntos
     (fusión idempotente, borrado, contexto), endpoints de ficha y portal, plan
     ajeno (cifras del contrato, ejercicios sin biblioteca, alérgeno cazado,
     menú strict, 422s).
   - **Tres fallos de PÉRDIDA DE DATOS que destapó la verificación adversarial**
     (los tres con regresión): (1) el bloque `[Adjunto: …]` no tenía CIERRE y se
     añade al final de la columna, así que se comía todo lo que el coach
     escribiera debajo — releer o borrar el adjunto le borraba sus notas; ahora
     va delimitado (`- [/Adjunto: stem]`, con backreference en el regex) y se
     retira exactamente lo escrito (los bloques sin cierre también se saben
     retirar). (2) La lectura de la anamnesis y el FORMULARIO DIGITAL sustituyen
     las columnas de notas enteras y se llevaban los bloques de los adjuntos ya
     leídos —la glucosa alta, el «evitar sentadilla profunda» del fisio—, que
     además alimentan el filtro de ejercicios y la lista roja; ahora
     `attachments.reaplicar_sidecars` los vuelve a escribir tras cada lectura.
     (3) Con la IA caída no se puede clasificar el documento, así que el desvío
     a adjunto no actuaba y una analítica subida por el botón de la anamnesis
     BORRABA el cuestionario; ahora la anterior se CONSERVA como adjunto y se
     avisa.
   - **Seis fallos más del importador de planes, confirmados y corregidos**: el
     plan importado NO estaba en la lista de borradores «en construcción», así
     que el primer guardado del editor lo PUBLICABA al cliente y `activate_plan`
     borraba de paso los avisos de «copia:» (incluido el del ALÉRGENO) — ahora
     hay UNA lista compartida (`plan_library.BORRADORES_EN_CONSTRUCCION`) que
     usan la activación, el aprendizaje §13 y la alerta de «sin adaptar», y las
     violaciones del Revisor determinista viajan al borrador con el prefijo
     `violation:` que lo retiene. Los macros de un plato sin gramos se copiaban
     del OBJETIVO de la toma (números que no salían de ningún alimento, y que
     arrastraban el reescalado de las opciones buenas): ahora los gramos los
     fija el `portion_solver` —el camino oficial— y, si algún alimento no está
     en la base, el plato NO entra y se dice cuál. Un documento MIXTO (comidas
     con día + sueltas) descartaba media dieta en silencio: el modo lo decide la
     mayoría y no se tira nada. Un menú cerrado incompleto dejaba al cliente sin
     comidas esos días: se completa la semana rotando y se avisa. Los topes (3
     opciones por toma, 6 tomas) recortaban sin decirlo: 4 opciones y avisos de
     todo lo que se queda fuera. Y la progresión, el cardio sin minutos y la
     descarga que no encajan ya no se sustituyen en silencio.
   - ⚠️ Gotchas nuevos: en tests, la IA falsa para documentos sustituye
     `AIClient._raw_call_with_blocks` y debe poner `settings.anthropic_api_key`
     (el constructor corta sin clave); `_convierte` se sigue llamando con la
     firma vieja para `.docx` (los tests lo sustituyen así); en este sandbox
     LibreOffice no carga ficheros (la reserva de texto cubre) — en la imagen
     Docker sí.

000000000000000000000. ✅ **FUSIÓN DE LAS CINCO SESIONES + VERIFICACIÓN
   ADVERSARIAL DEL RESULTADO (31-08-2026). INVENTARIO A CERO.** Las ocho tandas
   de `docs/HALLAZGOS_POR_VERIFICAR.md` se repartieron entre cinco sesiones
   paralelas; esta las fusionó TODAS en una sola rama, reconcilió a mano lo que
   dos sesiones habían escrito por separado y verificó el conjunto.
   - **Reconciliaciones de la fusión** (misma necesidad, dos soluciones): la
     tanda 7 estaba hecha por partida doble — se quedó `ExerciseListOut` con su
     exclusión extra, el endpoint de RESUMEN de planes por encima del recorte
     por parámetro, las DOS mitades de la optimización de fotos, UNA sola
     corrección del N+1 y los DOS avisos del cliente que no se pesa combinados
     en uno (`no_diet_logs` bajo su guarda de nutrición, `sin_pesajes` para
     todos los paquetes, sin duplicar el mensaje).
   - **Las dos decisiones que quedaban, aplicadas**: el panel de supervisión §9
     ya revisa también la REVISIÓN QUINCENAL (`adapt_plan`), y solo paga los
     8-10 roles cuando el Revisor 0 —que es gratis— encuentra algo; y el embudo
     self-serve de `/planes` se CONECTÓ en vez de retirarse: "Contratar ahora"
     abre Stripe directamente, con el precio real a la vista.
   - **Verificación adversarial de 46 agentes** sobre el árbol ya fusionado, dos
     lentes por hallazgo (reproducir / refutar): 19 en crudo → **11 confirmados
     y 6 disputados, los 17 resueltos**. TRES de los confirmados eran errores
     MÍOS al fusionar: la repesca de Stripe anotaba las facturas sin su
     suscripción (el programa de la oferta no se cerraba y Stripe cobraba un mes
     de más), el aviso `sin_pesajes` quedó encerrado en la guarda de nutrición y
     perdió justo al DQR Train, y el contracargo se guardaba con un tipo que no
     existía en `KINDS` (en el libro parecía un cobro más).
   - **Y los seis disputados** (hechos ciertos en los seis, ver el último
     apartado de `docs/HALLAZGOS_POR_VERIFICAR.md`): una sola regla de "día
     registrado" en Seguimiento (`push.dias_registrados`, contaba filas y el
     autosave las crea vacías), biblioteca de ejercicios montada una sola vez
     (viaja en el system cacheado), `exercise_id` no entero ya no tumba la
     pantalla de Entreno, cupo de la repesca repartido entre las CINCO fuentes
     que hay, rótulo real en las fotos iniciales de la anamnesis y
     `?ligero` RETIRADO del listado de planes (quedan dos formas: la de por
     defecto y `todo=true`).
   - **Cómo se verificó**: suite completa **en los dos órdenes** (el inverso
     destapó dos fallos reales de aislamiento), `tsc`, build, arranque desde una
     base VACÍA hasta la última migración y las cinco guardas —`check:anclas`,
     `check:avisos`, `check:claves`, `check:portapapeles` y `lint:hooks`, esta
     última ahora en 0/0 (el guardián enciende UNA regla a propósito, así que ya
     no marca como "sin usar" los `eslint-disable` de `exhaustive-deps`).
   - ⚠️ **NO fusionada a propósito**: la rama `claude/dqr-white-label-*` es otro
     producto (marca blanca) y borra los materiales de venta de DQ. Es una
     decisión del dueño, no un descuido.

00000000000000000000. ✅ **LA TANDA 3 DE `HALLAZGOS_POR_VERIFICAR`: EL CICLO —
   AUTOMATISMOS, AVISOS Y RECORDATORIOS (30-08-2026).** Trabajo en PARALELO con
   otras dos sesiones (tanda 1: los graves + Stripe · tanda 2: pagos y altas);
   el reparto está escrito en la cabecera de `docs/HALLAZGOS_POR_VERIFICAR.md`
   para que nadie pise a nadie. Cada hallazgo se verificó de forma adversarial
   (un refutador + un reproductor) ANTES de tocar nada, y cada arreglo lleva su
   regresión, comprobada de la única forma que vale: **falla sin el arreglo**.
   - **Un correo que FALLA contaba como enviado.** La dedup y el cupo miraban
     `email_log` sin su `status`: con el SMTP caído, los intentos fallidos
     gastaban el tope de 3 avisos y el cliente se quedaba sin recordatorio de
     cierre el resto de la quincena —y sin el del día 12 para siempre— aunque el
     correo volviera esa misma tarde. Ahora solo cuentan `sent` y `disabled`.
     ⚠️ Esto destapó que el fixture `_no_real_email` sustituía el transporte pero
     NO configuraba el SMTP: `EmailService` cortaba antes y **en los tests todos
     los correos se registraban como fallidos**, lo contrario de lo que el
     fixture simulaba.
   - **La vigilancia de automatismos solo miraba el mantenimiento diario**: los
     recordatorios del cliente, el resumen del coach y los avisos de
     videollamada podían llevar días muertos con el panel diciendo que todo iba
     bien. Ahora se vigilan todos, con margen ancho para los secundarios (una
     vuelta perdida no alarma). Y la rama de "terminó con errores" devolvía
     ANTES de mirar la antigüedad, así que un trabajo que falló y además se paró
     se quedaba para siempre en un mensaje que suena a que sigue corriendo.
   - **El resumen del coach se silenciaba justo cuando había novedades**: su
     huella de dedup se guardaba en crudo y `record_job` la recorta a 300
     caracteres; con ~10 alertas abiertas, dos conjuntos DISTINTOS se leían como
     iguales. Ahora se guarda un sha256.
   - **Dos videollamadas el mismo día se veían como una** en el móvil del coach
     (tag fija `dq-vc-coach`) — el mismo fallo de tags compartidas que ya se
     había corregido en otros avisos.
   - **"Escribir a mi coach" caía en un agujero**: la alerta vivía detrás de los
     `return` de "sin plan publicado" e "inactivo", justo los dos clientes que
     más escriben. Ahora se evalúa lo PRIMERO, antes de cualquier salida.
   - **La racha del portal no consumía la "única verdad"** que su propio
     comentario prometía: su predicado en SQL (`is_not(None)`) daba por bueno lo
     que el motor descarta (`free_notes` vacío, `chosen_options_json` sin elegir
     — filas que el autosave crea al abrir la pantalla) y premiaba días que para
     el coach no existían.
   - **Un push sin `count` APAGABA el badge del coach**: `Number(undefined)||0`
     llamaba a `clearAppBadge()`, así que el resumen semanal y el aviso de
     cliente inactivo —los dos emisores que no lo mandaban— borraban el "N pagos
     sin leer" sin que se leyera nada. "Sin count" ya no es "count 0".
   - **El punto ciego de "día registrado" (aviso `sin_pesajes` NUEVO).** Contar
     las series y las comidas como registro es DELIBERADO y está blindado con
     test (un DQR Train que entrena a diario no puede salir "en riesgo"): **no se
     tocó**. Pero detrás había un hueco real: quien elige su comida cada día
     cuenta como registrado, va verde en todas las pantallas, y al cerrar la
     quincena el motor determinista se encuentra con 0-1 pesajes, responde
     `dato_insuficiente` y no hay con qué ajustar — catorce días perdidos que el
     coach descubría tarde. Ahora se avisa pasada la mitad del período, sin una
     sola consulta extra en el barrido (sale de las filas que el lote ya trae).
   - ⚠️ **La suite era dependiente del estado**: `pytest` dos veces seguidas daba
     resultados distintos. La caché del contenido educativo vive en un sidecar
     del storage y SOBREVIVE entre ejecuciones: el primer pase la poblaba y el
     siguiente se saltaba la llamada de IA que los tests del pipeline cuentan.
     Se apaga en los tests (lo que este documento ya daba por hecho). Con eso
     desaparecen los dos fallos que arrastraba `test_ai_service`.
   - **652 tests en verde** (dos pases seguidos, reproducible), `tsc` limpio,
     build OK, `check:anclas` y `check:avisos` OK.

0000000000000000000. ⚠️ **SEGUNDA VUELTA A LA AUDITORÍA (30-08-2026): lo que
   la primera NO hizo.** Al preguntarle el dueño si de verdad no quedaba nada
   por mejorar, la respuesta honesta fue que no: la auditoría anterior había
   dejado cuatro huecos. Esto es lo que se hizo con cada uno.

   - **PRUEBAS EN NAVEGADOR DE VERDAD (hecho).** Cero navegador en la ronda
     anterior, pese a que el §10 lo exige. Montado un banco real (uvicorn +
     Vite + cliente demo sembrado + Playwright/Chromium) y recorridos el panel
     (escritorio y móvil 390 px), el portal, el cuestionario y el editor del
     plan. Encontró y se arregló lo que ningún test veía:
     · **dos 500 que rompían pantallas enteras**: un `kind` de movimiento
       inesperado tumbaba el feed de pagos COMPLETO (`PaymentOut` validaba la
       salida como enum), y un ejercicio con una clave de menos dejaba la
       pantalla de Entreno del cliente EN BLANCO (se leía con corchete);
     · un período de menos de 14 días dejaba al cliente sin poder enviar nunca
       su revisión ("se activa el <fecha que ya pasó>");
     · `/pagos` pintaba "0,00 € · 0 cobros" mientras cargaba, con la autoridad
       de una cifra real;
     · en el MÓVIL del coach: dos pestañas de Recursos y los chips de filtro de
       Pagos fuera de la pantalla (solo alcanzables arrastrando la página
       entera de lado), el menú "Más" de Planificación empezando 44 px fuera
       del borde izquierdo, y botones de 21×21 px y enlaces de 16 px de alto;
     · el login sin `name`/`autocomplete` (los gestores de contraseñas no lo
       reconocían) y la marca del coach sin cargar en la pantalla de login.
     Guiones en el scratchpad; se pueden rehacer.
   - **OPTIMIZACIÓN MEDIDA (hecho, parcial).** Con 60 fichas sintéticas,
     `/api/alerts` hacía **431 consultas y 355 ms** por refresco —siete por
     cliente, y el panel lo pide cada 20 s—: ahora **8 consultas y 85 ms**, con
     el mismo resultado exacto y dos regresiones que lo vigilan. La tipografía
     Inter deja de venir de Google (la IP de cada cliente del portal viajaba a
     un tercero en cada carga, y era una hoja de estilo externa BLOQUEANTE
     antes del primer pintado): se sirve del propio dominio, la CSP se estrecha
     y Caddy cachea `/fonts` e `/icons` 30 días. Quedan medidos y sin tocar
     varios N+1 más (ver el documento de hallazgos).
   - **VERIFICACIÓN ADVERSARIAL Y LOS DOS DOMINIOS QUE FALTABAN (a medias —
     LEER ESTO).** Se lanzaron los dos barridos, pero de 146 agentes
     terminaron 25: el resto murió contra el límite de sesión y con ellos casi
     toda la fase de verificación. Lo que sí llegó a comprobarse en firme, más
     lo que verifiqué a mano, está arreglado (abajo). El resto —**~85 pistas
     con fichero y línea, SIN verificar**— está en
     **`docs/HALLAZGOS_POR_VERIFICAR.md`**. No son hechos: hay falsos positivos
     garantizados. **El siguiente paso natural del proyecto es volver a lanzar
     esa verificación con presupuesto suficiente** y arreglar lo que sobreviva.
   - **Arreglado de esa cosecha, todo comprobado a mano antes de tocar nada:**
     · **la segunda contratación de la oferta se cancelaba tras cobrar 1 €** —
       el recuento de "¿está cobrado entero?" miraba TODAS las facturas del
       cliente de siempre, así que las tres del programa anterior ya sumaban:
       tres meses de asesoría por un euro. Cada factura queda sellada con SU
       suscripción (mig. 0042, con relleno de las que están en curso);
     · **los 8-10 revisores IA no veían la comida ni la cena**: las
       equivalencias se leían de `meal_bank["equivalences"]`, una clave que el
       esquema no declara — código muerto. Y en flexible_7 el prompt manda
       COMIDA y CENA como equivalencias (sus `options` llegan vacías), así que
       las dos tomas principales no aportaban una línea al texto del panel. La
       seguridad dura nunca estuvo comprometida (el Revisor 0 determinista las
       recorre por su cuenta); lo ciego era el juicio cualitativo de pago. El
       test que lo blindaba fabricaba una forma de banco que el sistema no
       produce: validaba el bug. Reescrito con la forma real;
     · **el token del portal seguía en claro en el log** en `/api/pay/{token}`
       (el enlace de cobro lleva el mismo token que el portal);
     · **el contador de fotos del cierre** vivía solo en memoria: al volver a la
       pantalla reetiquetaba desde "frontal" —el "antes y ahora" del informe
       comparaba ángulos distintos— y ofrecía huecos que el servidor no tenía;
     · **videollamadas**: sin Google conectado, una propuesta no tenía NINGUNA
       salida (el endpoint `done` lo admitía desde siempre, pero ningún botón lo
       llamaba) y su alerta alta sonaba para siempre; y el `db.rollback()` del
       endpoint de agendar resucitaba la credencial que Google acababa de
       revocar, dejando el sistema atascado en "conectado" con todo fallando.
   - Suite completa en verde (~640), `tsc` limpio, build OK, `check:anclas` y
     `check:avisos` OK. Migración nueva: **0042** (`payments.subscription_id`).
   - ⚠️ **Aviso de entorno**: el contenedor de esta sesión se restauró a una
     instantánea vieja CUATRO veces, llevándose el árbol de trabajo y la base de
     pruebas. Si algo no cuadra, `git log --oneline -1` primero; se recupera con
     `git fetch origin <rama> && git reset --hard origin/<rama>` y
     `alembic upgrade head` contra la base de pruebas.

000000000000000000. ✅ **AUDITORÍA INTEGRAL DE TODO EL SISTEMA (30-08-2026).**
   Petición del dueño: "una auditoría de absolutamente todo el sistema DQR…
   que todo funcione en orden, optimizado, sin ningún error ni bug, en ningún
   aspecto". 14 dominios auditados en paralelo (ciclo, IA/planes, revisión,
   portal, panel, anamnesis, pagos, documentos, avisos, datos, seguridad,
   rendimiento) con ~50 hallazgos; TODOS los confirmados corregidos y con
   regresión. 627 tests + tsc + build + `check:anclas` + `check:avisos` +
   `lint:hooks` en verde. Lo importante, por bloques:
   - **LA IA REVISABA A CIEGAS**: el texto que reciben los 8-10 revisores del
     panel §9 (incluido el clínico CON VETO) no llevaba NI UN PLATO —
     `_plan_text` leía `option["name"]` y el esquema usa `title`, y el menú
     strict (`bank["days"]`) ni se miraba. Ahora ven platos, ingredientes,
     menú cerrado y equivalencias. Y el **patrón dietético** (vegano, halal,
     kosher…) por fin viaja al prompt que ELIGE los alimentos: antes se
     proponía pollo a un vegano y el Revisor 0 vetaba el plan entero DESPUÉS
     de pagarlo. ⚠️ Los revisores corren ahora EN PARALELO (mismo orden, mismo
     veredicto, ni un crédito más): eran 8-24 llamadas encadenadas dentro de
     la petición que espera el coach.
   - **PRIMERO REPARAR, DESPUÉS JUZGAR** (`generator`): el informe del banco se
     calculaba ANTES de retirar alérgenos y de cuadrar los platos, así que el
     plan se retenía por un aviso fantasma ("contiene leche" en una opción que
     ya se había quitado) y por desvíos que el propio backend sabe corregir.
   - **"DÍA REGISTRADO" ES LO MISMO EN TODO EL SISTEMA** (`push.dias_con_registro`):
     el motor de "en riesgo" solo miraba el diario, así que un DQR Train que
     registraba TODAS sus series salía con 0 días, se marcaba `at_risk` con
     "adherencia 0 %" y la racha del portal le decía 0. Lo consumen el job
     diario, la alerta del panel, el resumen semanal y la racha.
   - **EL CANAL CLIENTE→COACH ESTABA MUERTO**: "Solicitar ajuste" existía
     entero en el backend (push ✋, email, alerta, tarjeta en Seguimiento) y no
     había pantalla que lo llamara. Ahora hay "Escribir a mi coach" en el
     portal. Además: el Diario ya no pierde lo tecleado sin cobertura
     (sessionStorage + reintento al volver la conexión, como Entreno), el
     cuestionario de 6 pasos guarda BORRADOR, las fotos de la revisión se
     suben desde el propio cierre (el endpoint existía y nadie lo usaba) y las
     notas diarias del cliente por fin se ven en la tabla del coach.
   - **DINERO**: la baja RGPD no cancelaba la suscripción de Stripe (se seguía
     cobrando a alguien que ya no existe, con el cargo entrando como
     huérfano); una devolución podía restar DOS veces (el guard solo cubría un
     sentido y las versiones nuevas de la API ya no mandan `charge.refunds`);
     un cobro a mano mal tecleado no se podía borrar; y "Sincronizar" decía
     "sin cobros pendientes" aunque el barrido se hubiera cortado (ahora hay
     cupo por fuente: las sesiones abandonadas ya no se comen el presupuesto
     de facturas y devoluciones).
   - **RECUPERACIÓN ANTE DESASTRE**: `alembic upgrade head` sobre una base
     VACÍA moría en 0036 y 0041 y dejaba la base sin una sola tabla (Alembic
     corre la cadena en una transacción) → el contenedor en crashloop. Nadie
     lo veía porque en producción la cadena ya estaba sellada. Guarda de
     idempotencia + `tests/test_migraciones.py`, que crea una base temporal y
     corre la cadena entera (verificado: falla sin el arreglo).
   - **RGPD DE VERDAD**: el borrado dejaba intacto `audit_log`, donde cada
     PATCH guarda el antes/después de lesiones, patologías, medicación y
     alergias (art. 9), y "Descargar todo" no incluía ni el diario ni una sola
     serie de entreno — con el flujo natural (exportar → borrar), ese
     historial se perdía para siempre.
   - **AVISOS QUE INSISTEN SIN ACOSAR**: "Pendiente hoy · Fotos" salía 5 veces
     al día PARA SIEMPRE (ahora caduca y se apaga al enviarse el informe); una
     quincena sin cerrar mandaba ~31 emails y ~150 push (tope de 3 avisos y
     una semana); el resumen del coach sonaba cada 3 h con el mismo texto
     (ahora solo con novedades + uno de cortesía al día); y las tags
     compartidas hacían que dos clientes que cerraban la misma tarde se vieran
     como UNA sola notificación.
   - **DOCUMENTO DEL CLIENTE**: la adaptación quincenal machacaba "Por qué
     este enfoque" con texto interno (del mes 2 en adelante el cliente no
     volvía a leer el argumentario); "Adherencia dieta 0 %" se le reprochaba a
     quien no ha contratado dieta; la lista de la compra del menú cerrado
     estaba hecha y con tests y no la recibía nadie; la fecha de la cabecera
     era la de DESCARGA; y el educativo era la única sección sin filtro de
     alérgenos (y con contenido cacheado por split, o sea compartido).
   - **SEGURIDAD**: los tokens del portal —credencial permanente al historial
     clínico— se escribían EN CLARO en el access log de uvicorn, con logs sin
     rotar en el VPS; no había tope de tamaño de cuerpo en ningún punto; el
     formulario público podía vaciar la cuota diaria de email del coach
     (cupo `PUBLIC_SIGNUPS_PER_DAY`); y cada PDF del portal arrancaba un
     LibreOffice de ~300 MB sin caché ni cola (10-30/min permitidos).
   - **RENDIMIENTO**: las alertas cargaban TODAS las versiones de TODOS los
     planes con sus 4 JSONB por cliente y por barrido; Seguimiento rehacía el
     histórico entero cada 3 s (y sin comprobar `document.hidden`); la ficha
     pedía dos veces todos los planes completos (nuevo `?ligero=true`); y
     recharts (~106 KB gzip) viajaba en la primera carga del portal.
   - **Y ADEMÁS**: el cuestionario ya no se puede reescribir una vez recibido
     (por PDF o con el plan en marcha); las contradicciones de la anamnesis se
     ven sin volver a pagar la lectura; los adjuntos (analítica) ya no cuentan
     como anamnesis; las fotos iniciales son el "antes" del primer informe; el
     cierre por el coach no inventa un segundo pesaje (anulaba el guardarraíl
     y aplicaba un −6 % real); el informe de un DQR Train no habla de dieta;
     el aviso de sistema "automatismos parados" se ve en Hoy (y no lleva a
     /clientes/0); un cliente caído en el mantenimiento ya no cuenta como
     ejecución correcta; los avisos de día exacto (día 12, D+3/D+7) son
     umbrales y no se pierden si el job se salta un día; y cambiar el plan o
     la duración de un cliente pide confirmación.
0000000000000000000000. ✅ **TANDA 7 DEL INVENTARIO: OPTIMIZACIÓN — LO QUE EL
   PANEL PEDÍA DE MÁS (31-08-2026).** Trabajo en PARALELO con la sesión de
   Stripe (que lleva la tanda 6, portal y anamnesis): el reparto está escrito en
   `docs/HALLAZGOS_POR_VERIFICAR.md` con los ficheros que toca cada uno. Todos
   los hallazgos se abrieron y se reprodujeron antes de tocar nada; cada
   arreglo lleva su regresión en `tests/test_optimizacion.py` (11), y las 11
   FALLAN con el código anterior. 613 tests en verde, `tsc` limpio, build,
   `lint:hooks` sin errores, `check:anclas` y `check:avisos` OK.
   - **La lista de versiones del plan era el agujero grande.** El panel de
     Planificación pedía `GET /clients/{id}/plans` — TODAS las versiones con sus
     cuatro JSONB, banco de comidas incluido — en el montaje **y otra vez tras
     cada acción** (generar, adaptar, activar, descartar, copiar, aplicar el
     Word…), para pintar cuatro cifras por versión. Ahora hay
     `GET /clients/{id}/plans/summary` (una línea por versión: kcal, macros,
     split, nº de sesiones, por qué cambió) y `GET /plans/{id}` para la ÚNICA
     versión que se enseña y se edita. En el panel todo pasa por un solo
     `recargarPlanes(preferido?)`. La ficha (chip de dieta) y la pestaña
     Feedback (nº de revisión ya adaptada) también usan el resumen.
     ⚠️ Si añades un dato del plan al archivo de "Planificaciones anteriores",
     añádelo a `PlanSummaryOut` — el archivo ya NO tiene los JSON.
   - **Cazado al refactorizar (no estaba en el inventario)**: `normalize()`
     prefiere la clave `nutrition` a `nutrition_json`, y dos sitios le pasaban
     `{...plan, nutrition_json: nuevo}` — como `plan` YA trae `nutrition`
     (la vieja), lo recién guardado NO se veía: editar los "Cambios de tu plan"
     o aplicar el Word decía "guardado" y la pantalla seguía con lo anterior
     hasta recargar. El backend sí lo tenía. Corregido en los dos (y el Word
     refresca también el educativo).
   - **Historial cuadrático**: `compute_period_summary` compara cada revisión
     con las anteriores, así que calcular el historial releía las series de las
     previas una vez por revisión (doce revisiones = 78 barridos). Nuevo
     `sets_por_periodo_de_cliente` (UNA consulta) que se pasa como caché
     opcional; sin ella el comportamiento es el de siempre. De paso, el
     historial dejó de traer los cuatro JSONB de todos los planes para imprimir
     cuatro escalares, y los feedbacks van en una consulta y no una por período.
   - **N+1 sueltos**: `GET /clients/{id}/periods` hacía una consulta de feedback
     POR revisión; la pantalla de Entreno del portal resolvía el plan DOS veces
     (el endpoint y `build_training_sessions`) y consultaba la biblioteca una
     vez POR SESIÓN; "Elegir base" leía el plan ENTERO de todos los clientes
     para pintar una línea de cada uno (ahora dos pasos: escalares para elegir,
     contenido solo de los elegidos).
   - **Peso por la red**: la biblioteca de ejercicios ya no manda
     `technique_notes`/`biomechanics_notes` en la LISTA (36 de sus ~141 KB, y
     ninguna pantalla del panel las pinta; la ficha individual las conserva) y
     el editor la recibe del panel en vez de volver a descargarla al abrirse;
     `GET /clients?light=1` deja fuera las notas largas de la anamnesis en Hoy y
     Clientes, que se refrescan solas cada 3 s y no leen ninguna (la FICHA nunca
     se recorta); las fotos del período se piden UNA vez por cliente (cada
     tarjeta pedía la lista entera), se bajan EN PARALELO y en miniatura
     (`?w=` con Pillow y `draft()`), y al pulsar una se abre la original.
   - **Vídeos de ejercicio (279 filas)**: portada de YouTube `mqdefault` en vez
     de `hqdefault` para un hueco de 56 px, `loading="lazy"`, fila memoizada
     (se repintaban las 279 con cada tecla), buscador con `useDeferredValue` y
     `content-visibility` (`.fila-diferida`) para no maquetar lo que no se ve.
   - **Un clásico**: el aviso de "Sin conexión" del panel móvil estaba montado
     DOS veces (líneas seguidas, copia y pega).

000000000000000000000. ✅ **TANDA 3 (SEGUNDA MANO): LO QUE QUEDABA DEL CICLO, Y
   LA SUITE QUE MENTÍA (30-08-2026).** Trabajo en PARALELO con otras dos
   sesiones sobre el inventario `docs/HALLAZGOS_POR_VERIFICAR.md` (que vive en
   la rama de la tanda 1). El PR #113 cerró cuatro de esta tanda mientras yo
   verificaba; esto es lo que quedaba. Cada hallazgo se verificó de forma
   adversarial (un refutador + un reproductor) ANTES de tocar nada.
   - ⚠️ **LOS DOS FALLOS DE `test_ai_service` NO ERAN "PREEXISTENTES DE MAIN":
     era la suite, que dependía del estado.** `pytest` dos veces seguidas daba
     resultados distintos. La caché del contenido educativo se guarda en un
     sidecar del storage y SOBREVIVE entre ejecuciones: el primer pase la
     poblaba y el siguiente se saltaba la llamada de IA que los tests del
     pipeline están CONTANDO (`assert len(client.calls) == 3` → 2). Las tres
     sesiones lo estaban dando por bueno como "ya venía roto". Se apaga en los
     tests (lo que este documento ya daba por hecho) y **la suite queda entera
     en verde, dos pases seguidos**. Si añades un caché con sidecar, apágalo en
     `tests/conftest.py` o volverás a envenenar la suite.
   - **Aviso NUEVO `sin_pesajes` — el punto ciego de "día registrado".** Contar
     las series y las comidas elegidas como registro es DELIBERADO y está
     blindado con test (quien entrena a diario no puede salir "en riesgo"): NO
     se toca. Pero detrás había un hueco real: el cliente que elige su comida
     cada día cuenta como registrado, va verde en todas las pantallas y no
     dispara nada… y al cerrar la quincena el motor determinista se encuentra
     con 0-1 pesajes, responde `dato_insuficiente` y no hay con qué ajustar el
     plan. Catorce días perdidos que el coach descubría cuando ya no tenían
     arreglo. Ahora se avisa pasada la mitad del período, y sale de las filas
     que el bloque de `no_logs` ya carga: ni una consulta más en el barrido.
   - ⏸️ **HECHO Y ESPERANDO A LA TANDA 1** (rama
     `claude/tanda3-pendiente-de-tanda1`): la vigilancia de automatismos que
     solo miraba el mantenimiento diario, la escalada a "lleva N horas" que era
     inalcanzable tras un fallo, la huella del resumen del coach truncada a 300
     caracteres (silenciaba el aviso justo cuando había novedades), el cupo de
     avisos de cierre que contaba los correos FALLIDOS y la racha del portal que
     no consume la "única verdad". Todo ello vive en código que aún no está en
     `main` (`job_state.py`, `_enviados_desde`, la dedup del resumen,
     `dias_registrados`): arreglarlo aquí a medias solo crearía un conflicto con
     su fusión. **Cuando la tanda 1 entre en `main`, fusiona esa rama.**
   - 602 tests en verde (dos pases), `tsc` limpio, `check:anclas` y
     `check:avisos` OK.

00000000000000000. ✅ **OFERTA = PROGRAMA CERRADO DE 3 MESES (28-08-2026).**
   Decisión del dueño: la oferta es UNA — 3 meses de DQR Full con permanencia
   (1 € el primer mes + 120 € el 2º + 120 € el 3º = 241 €) — y sus DOS formas
   de pago son solo maneras de pagar lo mismo: en 3 plazos (`oferta`, con el
   gancho del euro) o en 2 plazos de 120,50 € (`oferta2`). La forma del 1 €
   dejó de ser suscripción abierta:
   - `OFFER_CHARGES=3` + `OFFER_CHARGES_BY_PERIOD` (stripe_service); el corte
     se generalizó: `pagos_oferta_cobrados(db, client, periodo)` cuenta las
     facturas cobradas del LIBRO (la del 1 € también es la 1ª de las 3) y
     `detener_suscripcion_oferta(..., periodo=…)` cancela en Stripe al llegar
     a las requeridas (webhook `_handle_invoice_event` + backstop diario en
     `jobs.py`, ahora sobre AMBOS periodos, summary `ofertas_detenidas`). Los
     antiguos `pagos_2pagos_completados`/`detener_suscripcion_2pagos` ya no
     existen.
   - En la forma del 1 € el corte con éxito manda PUSH informativo al coach
     ("Oferta completada: cobros detenidos… en un mes le llegará el aviso de
     renovación"): los suscriptores ANTIGUOS de la oferta abierta que ya
     pasaran de 3 facturas se cortan también al desplegarse (backstop) — el
     push hace visible esa transición.
   - Baja tras completar (2 o 3 cobros según forma) = `subscription_completed`
     (sigue "pagado", feed "Oferta (1 € + 120 € + 120 €) completada"); baja
     ANTES = impago. Renovación: `BILLING_DAYS["oferta"]=30` (el programa
     acaba ~30 días tras el 3er cobro; con la suscripción viva no avisa).
   - `payments.describe`: "oferta (pago 1 de 3 · 1 €)" / "(pago 2 o 3 de 3)".
     Checkout con `custom_text.submit` explicando el programa y el corte (el
     checkout de Stripe enseña "120 €/mes" y sin ese texto parecía abierta);
     bot preview actualizado.
   - Front: OfertaPage (fuera "sin permanencia/cancelas cuando quieras" → "3
     meses, se detiene solo, sin renovación automática"), SalesKit (mensajes y
     chips), packages.ts (OFFER_CHARGES/OFFER_TOTAL_EUR, billingLabel "Oferta
     3 pagos (1 €)"), alta y ficha.
   - Tests nuevos en `tests/test_stripe.py`: corte a la 3ª factura, baja
     temprana = impago, ventana de renovación +30, describe.

0000000000000000. ✅ **INGESTA PERFECTA (27-08-2026)** — petición del dueño:
   "al subir Words, PDFs o planificaciones ya hechas, o al hacerlas a mano, no
   se aplican al completo… haz que se apliquen y lean todos a la perfección
   sin fallos". Auditoría de 3 dominios (Word / anamnesis / a mano, 32
   hallazgos) + implementación completa, verificada EN VIVO (28 asserts contra
   el stack local, flexible y strict) y con regresiones nuevas
   (`tests/test_word_import.py` ×12, `tests/test_ingesta_perfecta.py` ×8).
   - **WORD DE IDA Y VUELTA AL COMPLETO** (`services/word_import.py`
     reescrito): ahora también van y vuelven las RECETAS del banco flexible
     («Opción N. Título — Alimento 000 g (medida), …» + preparación) y el
     MENÚ CERRADO por días del modo strict — los MACROS de cada plato editado
     los RECALCULA el backend desde `foods` (Atwater 4/4/9, half-up,
     `_resolver_food` exacto+alias+difuso con candidato único; alimento
     desconocido → se aplica el contenido y se AVISA de revisar macros). Y
     además: reparto de macros en CUALQUIER orden/etiqueta (`_parse_reparto`:
     P/prot, CH/C/HC/hidratos, G/gr/grasas; parcial permitido con aviso),
     ESTRATEGIA de cada toma (columna 3, comparada contra lo impreso),
     descanso «2 min»/«1,5 min»/«1 min 30» (`_parse_rest`) con aviso si es
     ilegible, series «4X12»/«4*12» y aviso al capar >10, enfoque de la
     progresión en minúsculas/sinónimos (`_INTENT_MAP`, descarga→Deload) y
     aviso en filas de semanas nuevas o cargas ilegibles, ejercicios por
     nombre DIFUSO (`_fuzzy_exercise`: palabras clave sin artículos, único
     candidato → se acepta y se dice; varios → aviso con la lista), RENAME de
     la sesión desde su barra (si el día tiene una sola), calentamiento y
     vuelta a la calma, «Estructura ·» (split_rationale), «Por qué este
     enfoque» (rationale), «Tu margen de maniobra» (reglas + recarga),
     CARDIO completo (pasos aunque se reescriba la etiqueta + sesiones por
     posición), deload VACIABLE (borrar el texto lo quita), rejilla «Ejemplo
     de dieta semanal» (flexible → weekly_examples de 7 celdas; en strict es
     resumen derivado → aviso de editar los días), tabla «Cambios de tu plan»
     por posición, comida libre semanal, y el EDUCATIVO (píldoras/técnica/FAQ
     por posición → `education_json` viaja en el import y el PATCH). Cabecera
     de tabla retocada → AVISO «restaura la cabecera» (antes la tabla entera
     se saltaba muda). `_num` entiende «2,150» como millar y `_aplicar_energia`
     rechaza kcal <500 con aviso (antes 2,15 kcal reescalaban el plan a la
     nada). ⚠️ ORDEN INTERNO: todo lo que vive en meals/meal_bank se aplica
     DESPUÉS de `_aplicar_energia` (rescale reconstruye ambos desde la base).
     Solo quedan fuera las EQUIVALENCIAS de comida/cena (formato libre).
   - **PDF/plan_doc**: la celda «Clave técnica» imprime también «Clave
     biomecánica:» y «Tempo:» (y `_parse_cue_cell` los re-lee); la columna
     Estrategia imprime `meal.strategy` si existe; el menú strict imprime la
     caja «Tu comida libre semanal».
   - **ANAMNESIS**: extracción del PDF con `diet_pattern` (¡un vegano por la
     vía PDF recibía pollo!), `goal_deadline`, `phone`, perímetros iniciales
     (cintura/cadera/brazo/muslo → columnas nuevas, mig. **0041**),
     sinónimos de `injury_recovery` (antes IMPOSIBLE por PDF), ejercicios
     favoritos/vetados → `sport_history`, hora habitual de entrenar →
     `lifestyle_notes`, y regla «enum irreconocible → null PERO el texto va a
     la nota de su sección». **Adjuntos** (`kind=adjunto` en
     `POST /clients/{id}/documents`, prefijo `adjunto_`): subir la analítica
     ya NO borra la anamnesis ni se lee como cuestionario
     (`storage.anamnesis_documents()` es lo que miran los flujos de
     «anamnesis recibida» y la lectura IA). **§5 POR FIN CABLEADO**:
     `detect_contradictions` corre al leer el PDF (respuesta + sidecar +
     tarjeta ámbar en la pestaña Anamnesis) y al enviar el formulario (va en
     el push al coach); `client_portrait` alimenta `deep_analysis` cuando no
     hay sidecar (vía formulario). **Formulario digital**: pregunta perímetros,
     ejercicios favoritos/vetados y horarios de comida (texto libre →
     etiquetado en notas); `meal_schedule=[]` YA NO pisa el horario del alta.
     `strict_free_meal_enabled` POR FIN SE CONSUME (prompt strict condicional,
     pauta determinista en la base a mano, caja en el PDF, visible/editable en
     la pestaña Anamnesis); `goal_deadline` llega al prompt (gestión de
     expectativas, NUNCA acelera el déficit). Perímetros iniciales = el
     «antes» de la PRIMERA revisión (métricas y gráficas del informe).
   - **PLANES A MANO**: el scaffold asigna DÍAS REALES de la semana
     (`_REPARTO_SEMANAL`; "Día 1" hacía que el portal jamás detectara la
     sesión de HOY); strict imposible ya no deja `meal_bank=None` (banco
     flexible con aviso EXPLÍCITO); `ensure_bank_slots(diet_mode=…)` no
     fabrica banco flexible a un cliente strict; PATCH con guard simétrico de
     `training_json` (un plan solo-dieta ya no gana un entreno fantasma al
     guardar el editor); editor con SESIONES DE CARDIO editables y textos
     honestos (el banco se edita vía Word); `restructureNutritionMeals`
     CONSERVA las tomas con nombre no canónico y su recetario (antes
     «Post-entreno» desaparecía al tocar la estructura); copiar de la
     biblioteca AVISA del choque de modos (strict⇄flexible).
   - **PORTAL**: `progression_rule`, `biomech_cue` y `tempo` por fin llegan al
     cliente (payload + tarjetas en Entreno); tarjeta «Cardio y pasos»
     (`/p/{token}/training` devuelve `cardio`); el fallback de una toma sin
     banco filtra por `diet_pattern` (a un vegano le salían pavo/huevo).

000000000000000. ✅ **AUDITORÍA DE FUNCIONAMIENTO EN VIVO (26-08-2026)** — el
   socio del dueño sufría "pantalla en blanco / no carga / no hace lo que
   debería" en producción. Auditoría REAL: stack completo levantado en la
   sesión (Postgres + uvicorn + dist servido con réplica de Caddy) y navegado
   con Chromium headless (playwright-core) capturando consola, pageerrors y
   pantallazos, más 5 auditores de código en paralelo. DOS CAUSAS RAÍZ
   confirmadas y reproducidas:
   - **Hook condicional en `ClientPlanPanel`** (entró con los recordatorios
     anclados): un `useEffect` declarado DESPUÉS de los return tempranos
     (cargando / sin plan / edición) → Rules of Hooks rotas → al abrir la
     pestaña Planificación de un cliente CON plan React tumbaba TODA la app
     en blanco, 100 % reproducible. Movido antes de los returns. **Guardián
     permanente**: `frontend/eslint.config.mjs` + `npm run lint:hooks`
     (react-hooks/rules-of-hooks como error) — DEBE estar en verde antes de
     fusionar frontend.
   - **Chunks purgados por cada deploy**: pestaña/PWA abierta de antes navega
     a una ruta lazy no visitada → su chunk hasheado ya no existe → import()
     falla → blanco (reproducido con navegador). Arreglos: listener de
     `vite:preloadError` → recarga automática UNA vez (`lib/recarga.ts`, freno
     15 s anti-bucle) + **ErrorBoundary global** (`components/ErrorBoundary.tsx`)
     que ante cualquier crash enseña pantalla de marca con «Recargar la
     aplicación» en vez del vacío.
   - Defensa en profundidad (auditores): **Caddyfile** — /assets/* ya NO cae
     al index.html (404 real; antes servía HTML con `immutable` de 1 AÑO bajo
     la URL del chunk → caché envenenada, y un revert rompía la app incluso
     con F5) y TODO el HTML va con no-cache (antes solo /, /index.html y
     /sw.js: las rutas profundas quedaban en caché heurística); validado con
     `caddy validate` (modo producción). **Dockerfile frontend** — `npm ci`
     con package-lock (antes `npm install` de solo package.json: builds no
     reproducibles y churn total de hashes al perder la caché de Docker).
     **useAuth** — un 502/red caída durante un deploy ya no borra el token
     (solo el 401 desloguea; antes cada deploy podía expulsar al coach al
     login). **api.ts** — localStorage con try/catch (Safari "bloquear
     cookies" lanzaba y tumbaba el arranque). **alerts** — aislamiento por
     cliente en `list_alerts` (un cliente con datos rotos tumbaba campana y
     colas de TODO el panel en silencio). **JWT** 12 h → 72 h (la pestaña
     eterna del coach; single-tenant).
   - Diagnósticos previos de la misma queja: el dominio raíz dqrassessories.com
     NO tiene registro A (Namecheap) — la web vive SOLO en
     app.dqrassessories.com; y el workflow de deploy ahora comprueba vida real
     (API bloqueante + dominio informativo, ver deploy.yml).

00000000000000. ✅ **OFERTA EN 2 PAGOS (agosto 2026).** La oferta Full tiene DOS
   formas de pago en el mismo enlace (/oferta) y ambas son SOLO del plan Full:
   - `billing_period="oferta"`: 1 € el primer mes → 120 €/mes. ⚠️ SUPERSEDIDO
     (28-08-2026, decisión del dueño): ya NO es suscripción abierta — es el
     MISMO programa cerrado de 3 meses que la oferta2, pagado en 3 plazos
     (1 € + 120 € + 120 € = 241 €), y el webhook la CANCELA al cobrarse la 3ª
     factura. Ver la entrada "OFERTA = PROGRAMA CERRADO" más arriba.
   - `billing_period="oferta2"` (NUEVA): 2 pagos de 120,50 € (total 241 €,
     igual que 1+120+120). Suscripción mensual de 120,50 €
     (`dqr_full_oferta2`, sin cupón) que el webhook CANCELA en Stripe al
     cobrarse la 2ª factura (`detener_suscripcion_2pagos`; cuenta sobre el
     LIBRO de pagos, no sobre billing_reason; si Stripe falla → push al coach
     con el enlace directo a la suscripción). Backstop en el mantenimiento
     diario (`jobs.py`) por si el webhook se pierde — sin él entraría un 3er
     cargo indebido. La baja tras completar los 2 pagos NO marca pendiente
     (`subscription_completed`; la ficha sigue "pagada" y el feed dice
     "Oferta en 2 pagos completada"); una baja ANTES del 2º cobro sí es
     impago. Renovación: `renewals.BILLING_DAYS["oferta2"]=60` (el programa
     de 3 meses acaba ~60 días tras el 2º pago, con la suscripción ya
     despegada de la ficha). `periodo_de_factura` distingue las dos formas
     (lookup del precio → metadata → ficha); el feed del libro dice
     "pago 1 de 2 / pago 2 de 2".
   - Tocado: `stripe_service` (constantes OFFER2_*, tupla `OFFER_PERIODS`,
     precio idempotente en `ensure_canonical_prices` + `_desalineado`),
     `payments.describe`/sync, `renewals`, validadores (schemas
     `BillingPeriod`, public_site, stripe_router — bot preview propio —,
     clients.py alta+PATCH), `jobs.py`, y front: /oferta (CTA secundaria
     "2 pagos"), kit de ventas (chip "Oferta 2 pagos" + mensaje WhatsApp),
     alta de cliente y ficha (selector). Tests: batería oferta2 en
     `tests/test_stripe.py` (checkout sin cupón, corte al 2º cobro, baja
     temprana = impago, solo-Full, ventana de renovación, describe).
   - ⚠️ Gotcha de tests: cada router tiene SU `Limiter` module-level — para
     esquivar un 429 en un test tardío se apaga `public_site.limiter.enabled`
     (monkeypatch), no `app.state.limiter`.

0000000000000. ✅ **BIBLIOTECA DE PLANIFICACIONES (agosto 2026): copiar,
   modelos y a mano — todo a 0 créditos.** Petición del dueño: copiar la
   planificación de un cliente a otro, guardar modelos ("Planificación base")
   con título editable, hacer dieta/entreno a mano sin créditos, quitar días
   de la rutina y un buzón para la dieta hecha fuera.
   - **El principio que lo conecta todo**: un plan puede nacer de CUATRO
     sitios (IA · a mano · copiado de otro cliente · desde un modelo) y solo
     el primero gasta créditos. **LOS NÚMEROS NUNCA VIAJAN**: al pegar en otro
     cliente, `services/plan_library.copiar_a_cliente` recalcula el contrato
     del DESTINO (`metrics.energy_targets`+`macro_targets`, `mp.kcal` para
     conservar el invariante kcal ≡ 4/4/9) y reescala comidas y banco con
     `rescale_nutrition`+`reconcile_nutrition` (las del editor y el Word).
     Se copia la ESTRUCTURA; las cifras son siempre las del destino.
   - **Avisos de seguridad de la copia** con el MISMO motor del Revisor 0
     (`_iter_options` cubre flexible, strict y equivalencias): alérgenos,
     aversiones y patrón del destino; ejercicios fuera de su biblioteca
     filtrada; más días que los que entrena. Van en `warnings` y en
     `guardrail_flags` (visibles en el panel hasta corregirse).
   - **Lo que pertenece al ciclo del ORIGEN no viaja**: `applied_adjustments`,
     `rev` y `gen_inputs` se limpian; el snapshot se rehace para el destino.
   - **La copia es `generated_by="library"`** y editarla NO la activa (misma
     excepción del PATCH que la base sin IA). Chip propio: "Copia — adáptala
     y actívala".
   - **Modelos** (`models.PlanTemplate`, mig. 0040, SIN datos personales — el
     título lo pone el coach): guardar desde "Más → Guardar como modelo",
     gestionar en Recursos → "Modelos de plan", elegir en el selector.
   - **Router `/api/plan-library`**: GET (modelos + pool del plan vigente de
     cada cliente, cada uno con `resumen_plan` de una línea), POST/PATCH/
     DELETE de modelos, POST /apply (plan_id XOR template_id).
   - **Panel**: la vista "sin plan" pasa a TRES caminos iguales de visibles
     con su coste ("Con IA" · "A mano · 0 créditos" — la base sin IA ya NO se
     esconde a los no avanzados, el backend nunca la restringió — · "Desde
     otro plan · 0 créditos" con el selector). Debajo, el camino de la dieta
     hecha fuera: preparar base → Word → subir (0 créditos, máquina del
     import-word de siempre).
   - **Editor**: "Quitar día" por sesión (confirmación; mínimo 1 día) — el
     complemento natural de copiar un plan con más días de los que entrena
     el destino.
   - Tests: `tests/test_plan_library.py` (13). ⚠️ El contrato usa `mp.kcal`
     (no `et.target_kcal` a secas) y `package_tier` es nutri|train|full.
   - **Revisión adversarial de la ronda (confirmados corregidos)**: CRÍTICO —
     el `tdee_kcal` del DESTINO debe escribirse ANTES de `reconcile_nutrition`
     (con el del origen, `clamp_targets` acotaba las kcal de la copia al TDEE
     del cliente de origen: a una clienta ligera le dejaba +50% de sus kcal);
     `guardrails.option_conflict` es el escáner ÚNICO de alérgenos/aversiones
     con el criterio completo del Revisor 0 (ingredientes + título +
     preparación — «pollo al pesto» avisa a un alérgico a frutos secos) y lo
     usan la copia Y la alerta viva de `routers/alerts.py` (`option_allergen`
     a secas es más laxo: solo ingredientes); a un cliente SOLO-ENTRENO no se
     le exige el contrato calórico para copiarle una rutina.

000000000000. ✅ **RECORDATORIOS ANCLADOS + ACORDEÓN GLOBAL + AUDITORÍA
   (agosto 2026).** El dueño: "pulsas el aviso, te lleva al sitio exacto, te lo
   MARCA, y te deja un recordatorio de lo que ibas a cambiar; cuando lo
   cambias, el recordatorio se va SOLO". Y: "en todos los desplegables, abrir
   uno cierra el que estaba abierto". Suite + tsc + build + `check:avisos` +
   `check:anclas` en verde.
   - **Cada aviso sabe DÓNDE y CÓMO** (`alerts._DESTINO` + `_alert(...,
     target=, fix=, to=)`): `target` es un ANCLA (la misma cadena la lleva el
     elemento en el DOM como `data-ancla`), `fix` es la nota que se enseña
     pegada a la marca, y `key` identifica el PROBLEMA de forma estable. Los
     avisos con dato concreto pasan su ancla en la llamada
     (`nutricion.comida.{slot}`, `feedback.videollamada.{id}`).
   - **`lib/anchors.ts`**: `esperarAncla` (los datos llegan por red),
     `abrirContenedores` (abre `<details>` Y desplegables de estado por su
     `[data-desplegable-toggle]`), `irYMarcar`. ⚠️ **La marca se enciende con
     una REGLA CSS inyectada**, no con una clase: el panel se refresca cada 3 s
     y React reescribe `className` en cada render — con una clase la marca se
     borraba sola a los pocos segundos.
   - **`lib/pins.ts`**: un recordatorio NO se "completa", se DESVANECE. Cada
     fuente publica sus problemas vivos con `syncScope(ámbito, claves)` y todo
     recordatorio suyo que ya no aparece se borra. Si la fuente NO pudo cargar
     no sincroniza (un fallo de red nunca barre uno vivo). Ámbitos: `alerts`
     (lo publica `AlertsBell` en cada carga buena) y `plan:{clientId}` (lo
     publica `ClientPlanPanel`; por CLIENTE, no por plan: al regenerar cambia
     el id y los de la versión anterior no se retirarían nunca). Sincroniza
     entre pestañas por el evento `storage`.
   - **`components/Pins.tsx`**: `PinDock` (píldora abajo a la izquierda con lo
     que queda por arreglar), `MarcadorDeAncla` (lee `?ir=`, centra, marca y
     pega la nota) y `usePins`. La nota va en un portal al body posicionada por
     la caja del elemento: meterla dentro rompería maquetaciones ajenas y React
     la barrería al siguiente render.
   - **Las comidas de cada toma vuelven al panel, PLEGADAS** (`BancoDeComidas`):
     no ocupan pantalla (esa decisión se mantiene) pero existen — "hay lentejas
     en la toma 2" ya tiene dónde mirarse. Solo lectura: el banco se cambia
     regenerando o por el Word. **Pendiente valorado**: editar una opción
     suelta del banco desde la web.
   - **`lib/accordion.ts`**: acordeón global en UN sitio para panel y portal.
     Cubre `<details>` nativos y los de estado (`data-open` +
     `[data-desplegable-toggle]`), y **ve a través del envoltorio** que React
     pone por elemento de lista (si el desplegable es el ÚNICO de su
     contenedor, el que representa al grupo es el contenedor). `libre()` exime
     a un grupo. No entra en bucle: solo reacciona a la apertura.
   - **AUDITORÍA DEL ACORDEÓN — agrupar por la forma del DOM era el error.**
     El primer intento deducía el grupo ("si el desplegable es el único de su
     contenedor, el grupo es el contenedor") y salía IMPREDECIBLE: con dos
     revisiones, abrir una cerraba solo a las otras; con UNA sola, cerraba
     también la tabla de registros de al lado. Ahora la agrupación es
     EXPLÍCITA: `grupo("nombre")` para las listas donde cada elemento va en su
     envoltorio, `<details name>` donde ya lo hace el navegador, y hermanos
     DIRECTOS en el resto. Sin promociones.
     · `libre()` (que estaba exportada y sin usar) marca las superficies de
       TRABAJO: la tarjeta del período —dentro vive el editor del feedback que
       el coach está redactando, y se plegaba al abrir la línea de la
       videollamada— y las fotos del período, que al plegarse ABORTABAN hasta
       ocho descargas con JWT ya en curso.
     · Los desplegables con memoria se cierran con un evento
       (`EVENTO_CERRAR`), no pulsando su botón: pulsarlo persistía "cerrado"
       en localStorage como si lo hubiera decidido el coach, y `defaultOpen`
       dejaba de mandar para siempre. `EVENTO_ABRIR` es el camino inverso, el
       que usa el ancla al llegar.
   - **CALIDAD DE INTERFAZ** (inventario de 19 carencias, corregidas las
     prioritarias): aviso de SIN CONEXIÓN en panel y portal (`lib/offline.ts`);
     candado anti-doble-envío del informe al cliente; los 422 nombran el campo
     en español (`CAMPOS_ES` en `lib/api.ts`); `lib/clipboard.ts` — "enlace
     copiado" MENTÍA fuera de contexto seguro (entrar por la IP de la red
     local) y el coach pegaba lo que tuviera de antes; botón de reintentar en
     "Progreso" del portal y en la configuración de Recursos (se quedaban
     girando para siempre si su petición fallaba); el rango de una serie
     inválida se ve en el móvil (vivía en un `title`, o sea en nada); el
     portal vuelve arriba al cambiar de pestaña; coma decimal en los KPI;
     "Quitar ejercicio" a 44×44 y con confirmación; Escape en el menú "Más".
   - **`npm run check:anclas`** (17 comprobaciones): auto-borrado, aislamiento
     entre ámbitos, almacenamiento roto, reglas del acordeón, y sobre todo que
     **cada destino declarado en el backend tenga su `data-ancla` en la web**.
   - **SEGUNDA AUDITORÍA — el fallo de fondo de las anclas**: varios avisos
     señalaban un punto que NO existe en el estado en que ese aviso salta.
     ⚠️ Regla: **antes de dar un `target` a un aviso, comprueba en qué RAMA de
     la interfaz se renderiza ese elemento y si esa rama es compatible con la
     condición del aviso.** `npm run check:anclas` verifica que el ancla
     exista en el código, no que sea alcanzable.
     · **CRÍTICO**: al pulsar un aviso estando YA dentro de la ficha del
       cliente, el efecto que sigue a la URL llamaba a `changeTab`, que
       reescribía la URL y borraba el `?ir=` en el mismo instante → cambiaba
       de pestaña sin marcar nada. Separado en `aplicarTab` (aplica, no toca
       la URL) y `changeTab` (clic manual: además la reescribe y suelta el
       ancla). El efecto usa `aplicarTab`.
     · `plan.generar` solo existe en la vista "aún no hay plan", y
       `regenerate_goal`/`plan_stale_inputs` exigen plan PUBLICADO → nuevas
       anclas `plan.objetivo` (tarjeta de etapa) y `plan.acciones` (botonera).
     · `goal_review` llevaba al campo de la ficha, que solo hace un PATCH (no
       pospone el aviso ni regenera) y vive dentro del modo edición.
     · `payment_pending`: el ancla estaba puesta AL REVÉS (solo existía si el
       cliente YA había pagado). `renewal_due` marcaba "anotar otro cobro"
       mientras el enlace de renovación estaba oculto por estar pagado → el
       enlace se muestra en la ventana de renovación y quién decide si toca es
       `ClientOut.renewal_due` (= `renewals.is_due`, una sola verdad).
     · `period_overdue` prometía "ciérrala tú desde aquí" y llevaba a
       Seguimiento, donde ese botón no está (está en Feedback).
     · Las dos ramas de `create_plan` no son el mismo problema: la de "falta su
       anamnesis" llevaba junto a un «Leer con IA» deshabilitado por no haber
       PDF; ahora lleva a reclamarla.
     · Las videollamadas de revisiones ANTERIORES se avisaban pero no se
       pintaban: el coach aterrizaba sin botones para resolverlas.
     · Un **borrador retenido** por los guardarraíles desaparecía del panel
       (`vigente()` prefiere el publicado): sin botón de activar, sin sus
       avisos y con el ciclo bloqueado. Banda propia con el motivo, "Ver este
       borrador" y "Activar de todas formas".
     · Si un ancla NO aparece, ahora se enseña igualmente qué hay que hacer
       (`NotaSuelta`): perder el ancla ya no deja al coach sin la indicación.
     · El acordeón no se promueve a `<main>`/`<section>`/`<form>`: iba a
       buscar hermanos por secciones enteras.
   - **AUDITORÍA de las rondas recientes** (6 auditores + refutación
     adversarial). Confirmados y corregidos:
     · **Regresión propia**: la línea guía bajo cada barra del Word suplantaba
       a la barra en el importador y las cajas de *Cardio* y *deload* dejaban
       de importarse EN SILENCIO. `word_import._es_barra` reconoce la barra por
       su SOMBREADO, no por "último párrafo con texto". ⚠️ Si añades prosa
       entre una barra y su caja, esto es lo que la sostiene.
     · Word: un macro a **0** se leía como ausente y se reponía el valor viejo;
       si el reparto no se puede leer ahora se AVISA; el argumentario y las
       reglas de flexibilidad pasan por el filtro de alérgenos; el índice
       promete exactamente lo que se imprime; `_rhu` en el % de ajuste.
     · Cobros: el cobro a mano se **duplicaba con un doble clic** (el id
       llevaba el segundo actual) y **desaparecía en cuanto el cliente estaba
       pagado** — el estado de una RENOVACIÓN en efectivo; fecha futura
       rechazada; fecha por defecto LOCAL (era UTC); un fallo de BD se
       comunicaba como "ya estaba anotado"; el filtro `orphan` usa el criterio
       del contador y el borrado RGPD deja de contarse como huérfano
       (`payments.anonymized_at`, mig. **0039**).
     · Portal: **`animate-rise` con `both` dejaba un transform permanente** y
       un transform crea bloque contenedor — la píldora del descanso
       (`position:fixed`) caía al final del contenido. Ahora `backwards`.
       ⚠️ No vuelvas a poner `both` en una clase que envuelve contenido.
     · Portal: la serie se daba por hecha con el **primer dígito** de las reps
       (el campo emite en cada pulsación); los ejercicios de **peso corporal**
       no contaban nunca; Entreno se podía teclear **sin período abierto**; lo
       no guardado y el descanso en marcha **sobreviven al cambio de pestaña**
       (`sessionStorage`; PortalApp remonta por `key`); la cuenta atrás va por
       RELOJ, no por conteo.
     · Portal/CSS: el atajo `border` de `.portal-card` anulaba `border-l-4`
       (raíles que nunca se pintaban → `.portal-card--rail`); las pantallas de
       error vivían **fuera de `.portal-root`** y sus botones salían sin
       ningún token; `#fff` sobre naranja en cuatro sitios; el anillo de foco
       redondeaba EL ELEMENTO; el hover iluminaba botones deshabilitados; los
       botones compactos salían a 48 px (medidas movidas a `:where()`); la
       regla de tinta no cubría contenedores.

00000000000. ✅ **RONDA PREMIUM (agosto 2026): portal, PDF, cobros manuales y
   panel.** El dueño, sobre una captura del Entreno del portal: descanso por
   ejercicio, ver lo que movió la vez anterior, **series NO editables** (la
   rutina la pauta el coach), tono premium serio "para gente que paga por un
   buen coach", renovación 5 días antes, importe de los cobros de fuera de
   Stripe, PDF más argumentado y clics inteligentes en todo. 514 tests + tsc +
   build + `check:avisos` en verde.
   - **PORTAL · ENTRENO** (`PortalWorkout.tsx`): fuera `addSet`/`removeSet` — las
     filas SOLO salen de `ex.sets`; si el coach sube las series a mitad de
     quincena se completan las que faltan (nunca se recortan: borraría lo
     registrado). Columna **"Anterior"** delante de los campos con el peso × reps
     de ESA serie en la sesión previa, alineada por NÚMERO de serie (por
     posición se corría una fila si la 1 quedó en blanco); el endpoint ya
     excluía el día de hoy. Botón **"Descansar Ns"** por ejercicio con su
     `rest_sec`. Calentamiento/vuelta a la calma en tarjeta con cejilla, pauta
     del día en cifras destacadas y clave técnica con icono + etiqueta.
   - **PORTAL · SISTEMA VISUAL** (`index.css` `.portal-root`): tinta AA
     (`--p-ink`/`-soft`/`-mute`) — la jerarquía deja de darla la OPACIDAD, que
     dejaba texto en 2,6:1; elevación `--p-e-1..4`, radios, espaciado y escala
     tipográfica de 7 escalones (`.p-display`…`.p-eyebrow`); fuera el neón
     (badge/píldora/`portal-ring-blue` con contorno de contacto, botón primario
     plano con `--p-on-accent`); nav de cristal con indicador de 2 px; **un solo
     anillo de foco** (el naranja se redefinía encima del azul y desaparecía
     justo sobre el botón primario, también naranja); **`.portal-note`** como
     única pieza de aviso (color por significado); ritmo vertical en
     `.portal-header`/`.portal-main`; esqueleto con brillo.
     ⚠️ `.portal-note` es `flex` y GANA a la utilidad `block` (va después en la
     hoja): mete los textos dentro de UN solo hijo o saldrán en línea.
   - **COBROS**: `RENEWAL_WARN_DAYS = 5` (`services/renewals.py`);
     **`record_manual_payment`** + `POST /api/payments/manual` (efectivo,
     transferencia, Bizum, otro) con `kind="manual"` en `KINDS` y en el Literal
     `PaymentKind` — sin eso `record_payment` lo degradaba a "checkout"; el
     formulario `CobroManual` sustituye al botón "Marcar como pagado" y los
     ingresos de fuera de Stripe SUMAN en el total del mes. Filtro **`orphan`**
     en `GET /api/payments`: los cobros sin ficha se contaban y no había forma
     de llegar a ellos (chip que aplica el filtro + botón "Sin ficha" solo si
     hay alguno).
   - **PDF DEL PLAN** (`docs/plan_doc.py`): el **`rationale`** (porqué del
     enfoque) y el **margen de maniobra** (`flexibility_rules` +
     `refeed_or_break`) se pautaban y NUNCA llegaban al cliente → tienen su
     sección; **"De dónde sale tu cifra"** (gasto → ajuste → objetivo); reparto
     de macros con su peso en kcal (porcentajes sobre Atwater, el tercero por
     resta → suman 100); mapa del documento y línea de contexto bajo el título;
     `_nota()` guía bajo cada barra de sección; cifras en es-ES ("2.200 kcal"),
     "Déficit de 450 kcal" sin doble signo, "1 día/semana".
     ⚠️ **NO toques las cabeceras de las 4 tablas de datos**: `word_import.py`
     las reconoce por firma (`SIG_ENERGIA`/`SIG_TOMAS`/`SIG_PROGRESION`/
     `SIG_SESION`). El separador de millar sí lo entiende (`_num`).
   - **PANEL DEL COACH**: `SectionHeader` (raíl de color + título + contador) —
     una sola forma de marcar un apartado; `.card--flat/--raised/--rail` y
     `.well` para el subgrupo dentro de una tarjeta; **clics inteligentes**: los
     avisos admiten acción (subir la anamnesis lleva a su pestaña de un clic),
     "Conecta Google en Recursos" es enlace real y la pestaña de Recursos vive
     en la URL (`?tab=`) para poder enlazarla.
   - Tests nuevos: `tests/test_cobro_manual.py` (4), `tests/test_plan_doc_detalle.py`
     (4), filtro de huérfanos en `tests/test_payments.py`.

0000000000. ✅ **DETALLE RESUMIDO Y CLIC QUE LLEVA A LA ACCIÓN (agosto 2026).**
   El dueño: "la agrupación y los desplegables están muy bien… pero cuando se
   despliega quiero que esté MÁS resumido, y que el título casi no haga falta
   abrirlo. Y que al pulsar un aviso te redirija donde tienes que actuar".
   Suite (505) + tsc + build + `check:avisos` (14 comprobaciones) en verde.
   - **`resumirDetalle`**: al fusionar N revisores el detalle son N párrafos que
     repiten lo mismo. Se parte en frases, se tiran las VALORACIONES sin dato
     ("…la dieta sola es insuficiente"), se deduplica por PARECIDO (Jaccard ≥
     0.6 sobre palabras significativas — la firma exacta no reconocía "La
     anamnesis declara lesiones en X" vs "la anamnesis indica lesiones en X") y
     se conserva la versión con MÁS datos. 168 palabras → 65 en 3 viñetas.
     ⚠️ NUNCA se descarta en silencio: si sobran, añade "… y N más", y el
     TEXTO COMPLETO queda siempre en un desplegable (podría ser el alérgeno).
     ⚠️ Una valoración CON cifras no es relleno ("aporta 12 g … insuficiente
     para sus 90 kg"): `esRelleno` exige que además no tenga ningún dato.
   - **Clic que lleva a la acción** (`Destino` + `irADestino`): la acción de
     cada aviso es un botón. Nutrición/seguridad alimentaria → editor abierto
     por su sección (`#editor-nutricion`); lesiones/entrenamiento → `#editor-entreno`;
     salud/contexto → pestaña Anamnesis (`onGoTab`, que ya existía en
     ClientProfilePage). Mapa EXPLÍCITO por destino: un ternario mandaba todo lo
     no-nutrición al editor de entreno, incluso en clientes de SOLO NUTRICIÓN.
     "Puntos importantes" también enlaza a Anamnesis.
   - **Coherencia título↔acción**: tres avisos fusionados bajo "Sin plan de
     entrenamiento" heredaban "Cambiar esos ejercicios" (no hay ejercicios que
     cambiar). `accionYDestino` la recalcula sobre el título DEFINITIVO… pero
     SOLO si el aviso se fusionó: una acción concreta de la IA ("Sustituir el
     pan por tortitas de arroz") no se pisa con un genérico, ni se recorta (ya
     viene acotada por contrato).
   - Cazado por la revisión y cubierto con test: el filtro de relleno sin anclar
     se comía frases con cifras; `resumirDetalle` perdía puntos en silencio; el
     destino "generar" llevaba a una fila de botones sin generar; y la propia
     comprobación de coherencia era VACUA (los dos avisos del caso no
     compartían concepto, así que la rama de error era inalcanzable).


000000000. ✅ **SÍNTESIS REAL DE LOS AVISOS (agosto 2026).** El dueño, sobre la
   captura del bloque ya agrupado: "se ve más ordenado, ok, pero aún así hay
   muchísima información… en una línea se podría decir lo mismo con dos
   palabras, y no se diferencia bien visualmente entre bloque y bloque".
   Suite (505) + tsc + build + `npm run check:avisos` en verde.
   - **FUSIÓN por concepto** (`fusionar` en `lib/findings.ts`): OCHO revisores
     señalaban la MISMA lesión en ocho líneas idénticas. Ahora se agrupan por
     concepto (lesión, medicación, patología, TCA, cafeína, estrés, trabajo…),
     se conserva el título con MÁS datos y se marca `×N` (nº de revisores). El
     detalle de todos se concatena, no se pierde nada. 18 líneas → 11.
   - **Títulos sin relleno**: fuera el sujeto ("El cliente tiene…", "El plan NO
     aborda…") y los cierres vacíos ("…no abordado en el plan"), tope 5
     palabras. ⚠️ La NEGACIÓN se conserva (`SUJETO_NEGADO` + `COPULA_NEGADA`):
     quitarla dejaba "Adaptado a la lesión de rodilla", que afirma lo contrario.
   - **Jerga traducida** (`traducirFlags`): `violation:opción slot 1 'A': fat_g
     13 fuera de ±5% del objetivo 14` ×4 → "Grasas fuera de rango · 4 opciones".
     ⚠️ `retenido:` NO se descarta (lo intenté y la revisión lo cazó): puede ser
     el ÚNICO aviso rojo y sin él el bloque no se pintaba y nadie sabía que el
     cliente no había recibido el plan → "Guardado como borrador · el cliente no
     lo ve".
   - **Recuento único**: el chip decía "19 a corregir" y el bloque "24 puntos"
     (contaban cosas distintas). Ahora ambos usan `nRojoTotal`, que cuenta las
     líneas que el coach VE (fusionadas + flags agrupados) y respeta el filtro
     por color (si no, salía una caja roja vacía).
   - **Separación visual**: cada categoría es su propia tarjeta con fondo, y
     cada aviso lleva barra lateral de color. Antes era una lista continua.
   - **Prosa guardada** (`resumenCorto`): las notas de la progresión semanal y
     el deload muestran la PRIMERA FRASE ("Semana de referencia"), con el texto
     completo en un desplegable — no en un `title`, que en móvil es inalcanzable.
   - **Trampas evitadas** (todas cazadas por la revisión de código, todas con
     regresión en `check:avisos`): `restricción` a secas en el concepto "lesión"
     fusionaba un bloqueante de rodilla con una "restricción calórica" y HACÍA
     DESAPARECER uno de los dos; `[\s,;:+y]+$` se comía la "y" final ("muy alto"
     → "mu…"); y el contador de ámbar seguía en crudo mientras el bloque pintaba
     fusionados.


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

000000. ✅ **VENDER: pantalla de ofertas y enlaces que SÍ abren Stripe (agosto
   2026)** — el dueño pidió que elegir la oferta para mandar el enlace de pago
   fuera más visual e intuitivo, y que el enlace copiado/enviado abra
   DIRECTAMENTE la pasarela ("alguna daba algún error"). Suite en verde, `tsc`
   limpio, build OK.
   - **CAUSA RAÍZ del error (crítica)**: `Price.list` se llamaba con las ONCE
     lookup_keys (9 planes + las 2 formas de pagar la oferta) y **Stripe admite
     10 por llamada**. Desde que se añadió `oferta2` (la clave nº 11) la
     resolución de precios por lookup fallaba entera y los enlaces de la OFERTA
     acababan en `/planes` en vez de en Stripe. Ahora se piden en TANDAS de 10
     (`_prices_by_lookup`, usada por los dos sitios). El `FakeStripe` de los
     tests era más permisivo que Stripe (por eso la suite daba verde): ahora
     impone el límite real.
   - **Más caminos que no llegaban a Stripe** (todos con regresión): enlace
     pegado con puntuación (`…/full/oferta.`) o en mayúsculas → se normaliza
     como el tier; el id de precio VACÍO se cacheaba 10 min (un tropiezo dejaba
     la oferta sin enlace, que no tiene reserva en `.env`) → ya no se cachea;
     **renovar a un cliente de la oferta le revendía la oferta a 1 €** → se le
     cobra su plan MENSUAL; `open_invoice_url` devolvía None al fallar y se le
     decía "¡Pago recibido!" a quien quizá debía dinero → ahora es un error
     explícito; tier legado (`start`/`pro`) en la ficha moría con "Plan
     desconocido"; `STRIPE_MODE` mal escrito tumbaba todos los enlaces de plan;
     `_stripe()` fuera del try salía como 500.
   - **Y cuando falla, se nota**: `/planes?pago=error` con explicación y CTA de
     WhatsApp, **push al coach** (`notify_coach_pay_link_failed`), 429 y 404 de
     `/api/pay/*` en HTML legible (antes JSON crudo), y la vista previa de
     WhatsApp ya no crea sesiones de pago reales ni deja al usuario sin salida
     (botón "Ir al pago seguro", `?ir=1`).
   - **Pantalla VENDER** (`/vender`, entrada propia en la barra; el kit de
     ventas del panel "Hoy" pasa a ser un acceso directo): las dos ofertas en
     tarjetas grandes (lo que paga HOY, nº de cobros, total, "se detiene
     solo"), planes sueltos en rejilla, la elegida con tick y borde, y el
     ENLACE a la vista con **Copiar enlace / Copiar mensaje / WhatsApp /
     Probar**. `SalesKit.tsx` eliminado.
   - **El enlace lo da el BACKEND** (`GET /api/sales/catalog`,
     `services/sales_catalog.py`): dominio público oficial, importes REALES de
     Stripe (una sola consulta troceada) y **semáforo por enlace**
     (`ready`/`issue`): falta el precio, precio archivado, cupón del 1 € roto,
     Stripe sin configurar o en modo PRUEBA. Si no está listo, la tarjeta sale
     en rojo y no deja enviarlo. `GET /api/sales/client-link/{id}` hace lo
     mismo con el enlace de un cliente y dice qué hará al abrirlo (cobra /
     renueva / no cobra porque ya pagó) — la ficha lo muestra bajo el botón.
   - Tests: `tests/test_sales_catalog.py` (6) + 5 regresiones nuevas en
     `tests/test_stripe.py`.

00000. ✅ **AUDITORÍA DE LA PRODUCCIÓN DE PLANIFICACIONES (agosto 2026)** — el
   dueño pidió que crear planes (a mano, subiéndolos, con IA) funcione entero y
   sin errores, que las revisiones/ediciones tengan MEMORIA para aprender, y que
   TODO sea sencillo: saber qué pulsar y por qué. Suite completa en verde, `tsc`
   limpio, build OK.
   - **La generación ya no se cae por un veto**: el núcleo que viola guardrails
     se REINTENTA una vez con los vetos inyectados (full, solo-nutrición y
     solo-entreno). Si el reintento también viola, manda el veto original —
     nunca se afloja el guardarraíl (flag "núcleo: reintentado…").
   - **Activación honesta**: un plan RETENIDO (violación/ROJO) ya NO se
     auto-activaba al guardar cualquier edición — ahora el PATCH RE-VALIDA la
     nutrición editada con el Revisor 0 y solo activa si las violaciones se
     corrigieron; el ROJO del panel §9 es PEGAJOSO (solo lo levanta «Activar»
     explícito, que queda auditado como `plan_activated_with_override`).
   - **ADAPTACIÓN QUINCENAL, arreglada de raíz**:
     · un plan SOLO-ENTRENO ya no sale con una dieta fantasma (`nut.setdefault`
       fabricaba macros sobre `None` → PDF/portal con una dieta en blanco); los
       ajustes de dieta se marcan "No aplicado: este plan no incluye dieta" y el
       sello de Novedades vive en `training_json` (con fallback en portal,
       alertas, email y PDF);
     · el **diet break** del motor §8 se APLICA de verdad (kcal a mantenimiento,
       proteína bloqueada) — antes era solo texto que nadie ejecutaba; el salto
       por diseño no dispara el tope ±15% de recalibración;
     · **aprender del feedback de las rutinas**: las cargas de arranque se
       calibran con el ÚLTIMO peso que registró el cliente (mejor serie de su
       último día, a 0,5 kg) y los ajustes relativos se aplican sobre esa base;
     · Novedades **en cristiano** (fuera «decisión determinista» y claves como
       `dato_insuficiente`), `gen_inputs` refrescado, `manual_changes` del plan
       base no se arrastra, y **no se avisa al cliente si el feedback de la
       revisión sigue sin enviar** (se filtraba por la puerta de atrás).
   - **MEMORIA / APRENDIZAJE (§13) ampliado**: las lecciones del coach llegan
     también a la llamada de COMIDAS (la que ELIGE alimentos) y al feedback;
     un **swap de ejercicio** y la **corrección de los ajustes propuestos** se
     registran en `plan_edits`; el diff de construir un plan a mano
     (scaffold/library) ya NO contamina el aprendizaje; y nueva **memoria de
     vetos** (`brand/_ai_vetos.json`, `record_ai_vetos`/`vetos_reference`): lo
     que el validador tuvo que frenar, si se REPITE, entra como advertencia en
     el prompt de la siguiente generación. El coach puede QUITAR una lección
     desde Recursos → Aprendizaje (`DELETE /api/learning/lessons/{index}`).
   - **Panel §9 más honesto y mejor informado**: si revienta entero deja
     resumen ÁMBAR degradado («Revisión no ejecutada») en vez de parecer un
     plan aprobado, y los revisores IA ven ahora el RESUMEN DEL ENTRENO (antes
     juzgaban la coherencia dieta↔entreno a ciegas).
   - **`POST /api/plans/{id}/generate-education`**: recuperar el educativo
     fallido sin regenerar (ni repagar) el plan entero.
   - **SENCILLEZ (lo que pidió el dueño)**: "Generando…" sobrevive al cambio de
     pestaña (mapa de peticiones en vuelo → no se relanza ni se gasta el doble);
     toast honesto cuando el borrador queda retenido; en la banda de retención
     el botón destacado es «Ver este borrador» y «Activar de todas formas» pide
     confirmación; «Volver al plan activo»; «Regenerar con estas comidas» avisa
     del gasto y de que pisa ediciones; «Subir Word editado» sale a primera fila
     tras descargar el Word; la tarjeta «Adaptar» aparece también cuando la
     revisión automática decidió algo sin ajustes de texto; el editor explica en
     MÓVIL por qué «Guardar» está bloqueado; y el cliente SOLO-DIETA ve sus
     Novedades en "Mi día" (solo estaban en Entreno, que él nunca abre).
   - Tests: `tests/test_produccion_planes.py` (8) — solo-entreno sin dieta
     fantasma, diet break aplicado, calibración con registros reales, Novedades
     sin jerga, memoria de vetos, panel caído en ámbar, resumen de entreno para
     los revisores y no-aviso con feedback sin enviar.

0000000. ✅ **CIERRE: todo fusionado y a cero (agosto 2026).** El trabajo vivía
   en CINCO ramas de cinco sesiones distintas; esta rama iba 96 commits por
   detrás de `main` y dos sesiones habían hecho la MISMA tanda 7 en paralelo.
   Todo fusionado en `claude/stripe-integration-steps-somce4` (PR #112).
   - **Reconciliación de la tanda 7 duplicada**, quedándose con lo mejor de
     cada versión: el esquema `ExerciseListOut` (la exclusión forma parte del
     tipo) + su exclusión extra; el endpoint de RESUMEN de planes en vez del
     `?ligero=true`; las fotos del período con las DOS mitades (una petición
     compartida Y miniatura del backend); y los dos avisos del cliente que no
     se pesa combinados en uno. ⚠️ CORREGIDO DESPUÉS: los dejé anidados
     (`sin_pesajes` como `else` de `no_diet_logs`) y eso encerró el de pesajes
     dentro de la guarda de nutrición, perdiendo al DQR Train. Ahora el de
     dieta va bajo su guarda y el de pesajes vale para todos, sin duplicar.
   - **Daño de fusión, corregido**: siete ficheros se commitearon con las
     marcas de conflicto dentro; la racha del portal se quedó con media función
     de cada versión (ahora usa la ÚNICA definición de "día registrado" del
     sistema); y había un accesor `pesajes` duplicado del que Python se quedaba
     con el roto.
   - **Dos fallos que solo aparecieron al correr la suite en orden INVERSO**
     (para comprobar que nada dependía del orden): un cliente con el paquete
     antiguo (`pro`/`start`) tumbaba con un 500 la lista ENTERA de clientes,
     "Hoy" y su ficha —la tabla de equivalencias existía y no se aplicaba a la
     salida—; y el test de migraciones dejaba el engine atado a una base
     temporal que después borraba, envenenando todo lo que corriera detrás.
   - **Lo último que quedaba construido y sin conectar, conectado**: el panel
     §9 revisa la revisión quincenal (pagando solo si el Revisor 0 veta); el
     embudo self-serve de `/planes` con "Contratar ahora" directo a Stripe y el
     precio real a la vista; archivar/restaurar ejercicios; subir el logo de la
     marca; y descargar el informe de la revisión.
   - **NO fusionada a propósito**: `claude/dqr-white-label-4ojp01` es otro
     producto (white-label para otro gimnasio, con su kit de demo) y borra el
     material de marketing de DQ. Es una decisión del dueño.
   - Verificado con todo junto: suite completa **en los dos órdenes**, `tsc`,
     build, arranque desde base VACÍA a la última migración (0043), una sola
     cabeza de Alembic, la app levanta sus 165 rutas, y las cuatro guardas
     (`check:anclas`, `check:avisos`, `check:claves`, `check:portapapeles`).

000000. ✅ **TANDAS 7–8: el cierre del inventario (agosto 2026).** La 7
   (optimización) la llevó la sesión paralela. La **8**, la última, barrió lo
   que quedaba: créditos de IA, código construido y sin conectar, UX del panel
   e integraciones.
   - **Construido y sin puerta**: la PORTABILIDAD RGPD (ZIP con todo lo del
     cliente) existía y no tenía botón — ahora está en el perfil, encima del de
     borrar; el atajo para recuperar SOLO el contenido educativo que falló (sin
     repagar núcleo + comidas + panel) tampoco tenía botón; el diagnóstico del
     correo (`/api/email/status|test`) no tenía pantalla — está en Recursos, con
     el estado, lo que falta en el `.env`, envío de prueba y los últimos
     intentos; el "enlace de reservas" se guardaba y no lo leía nadie — ahora va
     en el WhatsApp de reprogramar la videollamada, que es lo que su propio
     campo promete; y `AUTO_PILOT_DEFAULT` prometía un modo que no existe (y que
     iría contra el criterio del sistema): fuera el ajuste y su superficie de
     API, la columna queda inerte y anotada.
   - **Dinero**: los CONTRACARGOS (`charge.dispute.*`) eran el único movimiento
     que el sistema no escuchaba —el banco retira el dinero y hay PLAZO para
     responder con pruebas—; la baja de la oferta cancelaba en Stripe y dejaba
     el `stripe_subscription_id` puesto, con lo que ese cliente no volvía a
     entrar NUNCA en la ventana de renovación; la repesca no miraba las facturas
     FALLIDAS (lo más caro de perder); y una referencia de checkout no numérica
     reventaba el `int()` del webhook con un 500 que Stripe reintenta durante
     días.
   - **Créditos**: una respuesta cortada por `max_tokens` se trataba como "JSON
     mal formado" y se reintentaba idéntica —dos llamadas caras para un fallo
     seguro—; los revisores del panel juzgaban el entreno por un RECUENTO
     ("6 ejercicios, 18 series") teniendo por rúbrica "selección y orden de
     ejercicios"; y la biblioteca de ejercicios viajaba en el user prompt, sin
     cachear, repagándose entera en cada reintento (ahora es un segundo bloque
     de system con `cache_control`).
   - **El cuadre del banco**: deshacía lo que el solver acababa de fijar
     (gramos fuera de las cotas del catálogo y caseras que mienten,
     «4 ud (165 g)» con la unidad a 55 g). Ahora intenta primero el solver, y la
     medida casera recalcula sus unidades — espejado en el editor TS y cubierto
     por el contrato de paridad. Un ingrediente que caía a 0 g tumbaba el
     `model_validate` y el `except` tiraba EN SILENCIO todas las reparaciones.
   - **La memoria de vetos (§13) dejó de aprender**: desde que se repara antes
     de juzgar, el alérgeno colado y el desvío de la toma emiten `seguridad:` y
     `cuadre:`, no `violation:`, y la memoria solo miraba el primer prefijo.
   - **Avisos sin salida**: la baja RGPD podía quedar bloqueada para siempre si
     Stripe fallaba con un error que el filtro no reconoce (ahora el coach puede
     declarar que la canceló él, y queda en la auditoría); "N sin ficha" no se
     podía apagar (mig. 0043, `payments.dismissed_at`); Historial y Aprendizaje
     se quedaban girando para siempre al fallar su carga.
   - **Guardas nuevas**: `npm run check:portapapeles` (una sola puerta al
     portapapeles: había ocho `writeText` a pelo, tres con un "Copiado ✓"
     incondicional detrás de un catch mudo) y `tests/test_ajustes_vivos.py`
     (toda clave de `.env.example` existe en Settings y la menciona alguien).
   - **Dos verificados y NO arreglados a propósito**, por ser decisión del
     dueño: enchufar el panel §9 a la revisión quincenal (pagar 8-10 roles cada
     quincena va contra el recorte de créditos que él pidió) y retirar el embudo
     self-serve de `/planes` (tres endpoints públicos sin consumidor que pueden
     estar enlazados desde fuera). Los dos quedan anotados en el código y en el
     inventario.

00000. ✅ **TANDAS 1–6 (agosto 2026): el inventario de hallazgos, arreglado por
   prioridad.** Tras la ronda 3 quedó `docs/HALLAZGOS_POR_VERIFICAR.md`: la
   salida en crudo de dos barridos automáticos cuya verificación adversarial
   murió contra el límite de sesión (**pistas con fichero y línea, NO hechos**).
   Se atacó en tandas, ordenadas de más grave a menos, por VARIAS sesiones en
   paralelo — el reparto vive en la cabecera de ese documento y hay que
   reclamar la tanda ANTES de tocar nada (tres sesiones hicieron la 3 a la vez
   y hubo que reconciliar a mano un aviso duplicado y un N+1 reintroducido).
   - **Tanda 1** (graves): progresión semanal o día de sesión malformados
     tumbaban "Hoy"/Entreno de TODOS los clientes; el plan declaraba macros que
     su propia lista de la compra no daba; la memoria de vetos se sanea también
     al LEERLA.
   - **Tanda 2** (pagos): devoluciones descontadas dos veces (la fila sintética
     de cuadre + el desglose `re_…`), la devolución posterior entraba "vista",
     y borrar un cobro a mano dejaba al cliente en "pago pendiente".
   - **Tanda 3** (el ciclo): cuatro de los cinco automatismos podían morir en
     silencio → `services/job_state.py` (los cinco vigilados, con escalado por
     horas sin éxito) enchufado al scheduler, a las alertas del panel y al push;
     el badge del coach se apagaba solo; el gasto de IA se anotaba por debajo
     del real; un correo que no llegó a salir consumía su intento.
   - **Tanda 4** (IA y planes): copiar un plan arrastraba el sello de adaptación
     de OTRO cliente; a un DQR Train regenerar no le apagaba el aviso "sin
     adaptar"; la gráfica de perímetros pintaba el "antes" en la columna del
     "ahora"; la caché del PDF no acertaba NUNCA (python-docx sella la hora en
     el zip) y cada descarga levantaba un LibreOffice.
   - **Tanda 5** (RGPD): la baja dejaba cabos sueltos y el nombre del borrado
     sobrevivía en las fichas de otros; Caddy cortaba a 30 MB los vídeos que el
     backend admite hasta 300.
   - **Tanda 6** (portal y anamnesis): en un móvil COMPARTIDO el borrador de un
     cliente acababa en la ficha de otro (claves de `sessionStorage` sin token →
     guarda nueva `npm run check:claves`, que encontró sola el mismo fallo en
     Entreno); un guardado viejo podía BORRAR las series recién registradas (el
     PUT del diario reemplaza la lista entera → número de envío monotónico
     compartido por los dos escritores, en Diario y en Entreno); las
     contradicciones y el retrato de la anamnesis se servían congelados del
     sidecar y dejaban de seguir a las correcciones del coach (son funciones
     DETERMINISTAS de la ficha: se recalculan en vivo); quien ya envió el
     formulario podía reescribir su ficha subiendo un PDF por detrás.
   - **Comprobación transversal de las seis**: todas las tandas fusionadas en
     una rama (la 2 y la 4 vivían solo en la otra), una sola cabeza de Alembic
     con el arranque desde cero probado, cero funciones huérfanas, cero TODO
     nuevos, suite + `tsc` + build + las tres guardas en verde — y, una a una,
     **cada regresión comprobada quitando su arreglo**: las 16 caen sin él (las
     otras tres son de front o de test, sin código que revertir).

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
