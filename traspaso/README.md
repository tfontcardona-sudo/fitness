# Sistema de Asesorías Fitness Automatizadas

Plataforma **single-tenant** para gestionar asesorías premium de nutrición y
entrenamiento: generación de planes con IA bajo guardrails de seguridad, portal
del cliente sin login, recalibración quincenal automática, feedbacks con
gráficas y documentos Word con marca.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy/Alembic · APScheduler · React+TS+Vite+Tailwind · Caddy · Docker · Anthropic API

---

## Arranque rápido (desarrollo)

```bash
cp .env.example .env        # rellena ANTHROPIC_API_KEY como mínimo
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Servicio | URL |
|---|---|
| Frontend (Vite + HMR) | http://localhost:5173 |
| API + docs (Swagger) | http://localhost:8000/api/docs |
| Health check | http://localhost:8000/api/health |
| Portal del cliente | http://localhost:5173/p/{token} |
| Mailpit (emails de prueba) | http://localhost:8025 |
| PostgreSQL | localhost:5432 |

En desarrollo los emails se envían a **Mailpit** (no hace falta SMTP real). El
`entrypoint.sh` aplica migraciones y el seed (150 ejercicios + marca + 2 admins)
automáticamente en cada arranque.

**Acceso del coach:** usuario/contraseña de `ADMIN_1_USER`/`ADMIN_1_PASS` del `.env`.

## Despliegue en VPS (Hetzner u otro)

1. Instala Docker + Docker Compose en el VPS.
2. Clona el repo y `cp .env.example .env`. Rellena **todas** las variables:
   - `ANTHROPIC_API_KEY` y, si quieres, `MODEL_HEAVY`/`MODEL_LIGHT`.
   - Secretos largos y aleatorios para `JWT_SECRET` y `PORTAL_TOKEN_SECRET`
     (genera con `openssl rand -hex 32`).
   - Credenciales de los 2 admins (`ADMIN_1_*`, `ADMIN_2_*`).
   - SMTP real (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`).
3. Apunta un registro DNS `A` de tu dominio (p. ej. `app.tudominio.com`) a la IP.
4. En `.env`: `DOMAIN=app.tudominio.com` → Caddy obtiene el certificado HTTPS solo.
5. `docker compose up -d --build`
6. Verifica: `https://app.tudominio.com/api/health`

Sin dominio todavía: deja `DOMAIN=` vacío y el sistema sirve por HTTP en el :80.

**Copias de seguridad:** el volumen `db_data` contiene la base de datos y
`./storage` los archivos de clientes (fotos, documentos). Respáldalos juntos.

## Arquitectura

```
backend/
  app/
    main.py            FastAPI: health, CORS, routers, scheduler en lifespan
    config.py          settings (pydantic-settings, lee .env)
    db.py              engine + SessionLocal + Base
    models.py          14 tablas SQLAlchemy 2.0 (PARTE C.1 + users)
    security.py        JWT (coaches) + tokens de portal firmados (itsdangerous)
    deps.py            dependencias de auth (get_current_user, get_client_by_token)
    routers/           auth · clients · exercises · brand · plans · portal_public
    schemas/           ai.py (contratos IA) · entities.py (API)
    seeds/             150 ejercicios + marca + admins (idempotente)
    services/
      metrics.py       BMR/TDEE/e1RM/tendencias/adherencia (toda la aritmetica)
      guardrails.py    limites de seguridad E.4 (nutricion) y F.4 (entrenamiento)
      state_machine.py maquina de estados del cliente (G.2, funcion pura)
      jobs.py          mantenimiento diario (transiciones + emails)
      scheduler.py     APScheduler (job diario)
      email_service.py + email_templates.py   SMTP con marca + log
      portal.py        logica de la vista HOY
      swap.py          swap de ejercicios (F.5)
      ai/              client.py (retry+validacion) · generator.py (3 llamadas) · prompts.py
      docs/            plan_doc · feedback_doc · charts (matplotlib) · shopping_list · word_base
    consent_pdf.py     PDF de consentimiento RGPD
  tests/               9 archivos de test (unitarios + integracion)
frontend/
  src/
    pages/             LoginPage · DashboardPage · ClientsPage · ClientProfilePage · BrandPage
    components/        AppShell · ui · ClientSummaryTab · ClientAnamnesisTab
    portal/            PortalApp + 5 vistas (HOY · plan · diario · cierre · feedback)
    hooks/             useAuth · useBrand
    lib/               api.ts · format.ts
storage/               fotos, documentos y uploads de clientes (fuera del repo — RGPD)
```

### Principios de diseño

- **La IA decide, el backend calcula y valida.** La IA nunca hace aritmetica:
  el backend le entrega BMR/TDEE/kcal y revalida cada salida con guardrails. Una
  violacion se recorta, se registra y fuerza `review_pending` aunque auto-pilot
  este ON.
- **Generacion en 3 llamadas orquestadas:** nucleo del plan → banco de comidas
  segun `diet_mode` → contenido educativo. Cada salida se valida contra su
  contrato Pydantic con retry y el error inyectado.
- **Portal sin login:** token firmado (`itsdangerous`) en la URL, revocable
  regenerandolo. Las fotos se sirven solo bajo token correcto y se les elimina
  el EXIF.
- **Todo lo de cara al cliente en castellano** (planes, portal, documentos, emails).

## Tests

Los tests unitarios (metricas, guardrails, IA, maquina de estados, documentos)
no necesitan base de datos. Los de integracion requieren PostgreSQL.

```bash
# Dentro del contenedor de la API (con la DB levantada):
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api pytest

# Solo unitarios (sin DB):
pytest tests/test_metrics.py tests/test_guardrails.py tests/test_ai_service.py \
       tests/test_state_machine.py tests/test_documents.py
```

**Cobertura:** 99 tests. El archivo `tests/test_integration_a3.py` cierra el
checklist de autoverificacion A.3 del documento de especificacion.

## Variables de entorno (.env)

| Variable | Descripcion |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic |
| `MODEL_HEAVY` / `MODEL_LIGHT` | Modelos para generacion / parseo |
| `DATABASE_URL` | Cadena de conexion PostgreSQL |
| `JWT_SECRET` | Secreto para los JWT de coaches |
| `PORTAL_TOKEN_SECRET` | Secreto para firmar tokens de portal |
| `ADMIN_1_*` / `ADMIN_2_*` | Credenciales de los 2 coaches (seed) |
| `DOMAIN` | Dominio para HTTPS automatico (vacio = HTTP :80) |
| `SMTP_*` / `EMAILS_ENABLED` | Configuracion de email |
| `AUTO_PILOT_DEFAULT` | Auto-pilot por defecto en nuevos clientes |
| `TZ` | Zona horaria (Europe/Madrid) |

## Estado del proyecto

- [x] **Fase 0** — Esqueleto: Docker, API con health check, frontend shell
- [x] **Fase 1** — Modelos (14 tablas) + migracion + seed 150 ejercicios + schemas + types.ts
- [x] **Fase 2** — Auth JWT + CRUD (clients/brand/exercises) + tokens de portal + wizard de anamnesis + RGPD
- [x] **Fase 3** — Metricas (BMR/TDEE/e1RM) + guardrails (E.4/F.4) + servicio de IA (3 llamadas orquestadas)
- [x] **Fase 4** — Scheduler (APScheduler) + maquina de estados (G.2) + servicio de email SMTP con plantillas
- [x] **Fase 5** — Frontend de coaches: login JWT + dashboard + clientes + perfil (resumen/anamnesis) + marca
- [x] **Fase 6** — Portal del cliente mobile-first: HOY + plan + diario + cierre + feedback + solicitar ajuste
- [x] **Fase 7** — Documentos Word con marca (plan + feedback) + graficas matplotlib + lista de la compra
- [x] **Fase 8** — Swap de ejercicios + tests de integracion (checklist A.3) + README final

**Proyecto completo y desplegable.**
