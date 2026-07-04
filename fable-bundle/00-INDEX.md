# Fable bundle — snapshot compacto de Fitness System (DQ)

Snapshot de **solo lectura** de todo el proyecto en **9 archivos** para dárselo a Fable como contexto,
sin arrastrar los ~300 archivos del repo. **El proyecto real (`../`) es la fuente de verdad**; esto es una foto.

Generado: 2026-07-02. Contiene **97 archivos fuente** concatenados (todo el `.py`, `.ts/.tsx`, `.css`, config e infra).

## Orden de lectura sugerido

1. **`01-TRASPASO.md`** ← EMPIEZA AQUÍ. Estado del proyecto, dónde nos quedamos, pendientes (Web Push), caveats (API sin crédito), cómo arrancar/probar, gotchas.
2. `08-docs-readme-claude.md` — README + CLAUDE.md originales (visión general + instrucciones del repo).
3. `03-backend-core.md` — `main.py`, `config.py`, `db.py`, `deps.py`, `security.py`, `models.py`, `schemas/*`, migraciones Alembic, y `seeds/` (biblioteca de ejercicios).
4. `04-backend-routers.md` — endpoints (auth, clients, plans, exercises, brand, portal_public).
5. `05-backend-services.md` — lógica: `adapt_plan.py`, `feedback_service.py`, `ai/*`, `docs/*` (Word/PDF), `metrics.py`, `guardrails.py`, `scheduler.py`, `storage.py`, etc.
6. `06-frontend-coach.md` — app del coach: `pages/*`, `components/*`, `lib/*`, `hooks/*`.
7. `07-frontend-portal-core.md` — portal del cliente (`portal/*`) + `types.ts` + `index.css` + `App.tsx` + `main.tsx`.
8. `02-infra-config.md` — docker-compose, Dockerfile, entrypoint, requirements, package.json, tsconfig/vite/tailwind, `.env.example`.

## Formato

Cada `.md` concatena varios archivos separados por marcadores:

```
===== FILE: ruta/relativa/al/repo.ext =====
<contenido íntegro del archivo>
```

Para editar de verdad, hazlo en el repo real (`../backend/...`, `../frontend/...`), no aquí.

## Qué NO está aquí (binarios excluidos a propósito)

Son assets binarios; siguen en el repo real:

- `backend/app/assets/plan/*.png` (7 imágenes del PDF del plan: cover, plate, food_round, header_*). ~2.9 MB.
- `backend/app/assets/anamnesis_template.pdf` (231 KB).
- Carpetas de datos/artefactos: `_render/` (QA de render docx→imagen), `storage/` (documentos generados de clientes), `node_modules/`, `.git/`.

Si Fable necesita tocar el PDF del plan, que mire esos assets + `05-backend-services.md` → `docs/plan_doc.py` (y las memorias `plan-doc-design` / `plan-example-fidelity`).

## Recordatorio de estado (resumen del TRASPASO)

- Última feature terminada y verificada: **portal de seguimiento** (entreno/diario/quincenal) + seguimiento en tiempo real del coach + **adaptación de plan** tras la revisión quincenal.
- **502 al adaptar plan: RESUELTO** (adaptación determinista sin IA, `services/adapt_plan.py`).
- **Bloqueante:** API de Anthropic **sin crédito** → generar plan/feedback IA falla (se simuló para el cliente Manuel id 34). Adaptar NO necesita IA y funciona.
- **Web Push: HECHO (2026-07-03)** — PWA por cliente + service worker + VAPID + `push_subscriptions` + job cada 4 h + badge. Detalle y activación en `01-TRASPASO.md` §8.1. OJO: los volcados de código de este bundle (02–07) son del snapshot 2026-07-02 y NO incluyen los archivos de Web Push; la fuente de verdad es el repo.
