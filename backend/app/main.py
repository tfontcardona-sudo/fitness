"""Punto de entrada de la API.

Health check + CORS + registro de routers. Migraciones y seeds se ejecutan
en entrypoint.sh antes de arrancar; el scheduler se añade en la Fase 4.
"""

from contextlib import asynccontextmanager
import logging
import re

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text

from app.config import settings
from app.ratelimit import client_key
from app.db import engine
from app.routers import (
    ai_credit, alerts, auth, brand, clients, coach_push, email, exercises,
    google_oauth, learning, payments, plan_library,
    plans, portal_public, public_site,
    resources, sales, stripe_router, whatsapp,
)

APP_VERSION = "0.2.0"

# ---------------------------------------------------------------- logs ----
# El token del portal es una credencial PERMANENTE al historial clínico
# completo del cliente (anamnesis, medicación, lesiones, peso, fotos) y viaja
# en la RUTA, así que el access log de uvicorn lo escribía EN CLARO en cada
# línea: `GET /api/p/<TOKEN>/state 200`. Cualquiera con acceso a los logs del
# contenedor —o una copia de seguridad de ellos— entraba al portal de todos.
_RE_TOKEN_PORTAL = re.compile(r"(/api/p/)[^/\s\"']+")


def enmascara_tokens(texto: str) -> str:
    """Sustituye el token del portal por *** en cualquier texto de log."""
    return _RE_TOKEN_PORTAL.sub(r"\1***", texto)


class _FiltroTokens(logging.Filter):
    """Filtro para `uvicorn.access` (y cualquier logger): enmascara el token."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            if record.args:
                record.args = tuple(
                    enmascara_tokens(a) if isinstance(a, str) else a
                    for a in record.args
                )
            if isinstance(record.msg, str):
                record.msg = enmascara_tokens(record.msg)
        except Exception:  # noqa: BLE001 — un log jamás puede tumbar la app
            pass
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lo primero de lo primero: que ningún token de portal acabe en los logs.
    for _nombre in ("uvicorn.access", "uvicorn.error", "app.errors"):
        _lg = logging.getLogger(_nombre)
        if not any(isinstance(f, _FiltroTokens) for f in _lg.filters):
            _lg.addFilter(_FiltroTokens())

    # SEGURIDAD (lo primero): los secretos de firma NO pueden ser los de ejemplo
    # del repositorio público ni ser cortos. En producción se REHÚSA arrancar
    # con secretos forjables (mejor una caída visible que sesiones falsificables);
    # en dev/tests solo se avisa.
    _secret_problems = settings.insecure_secrets()
    if _secret_problems:
        _seclog = logging.getLogger("app.security")
        detalle = "; ".join(_secret_problems)
        # Solo se REHÚSA arrancar por lo catastrófico (secreto de ejemplo del
        # repo público). Un secreto corto pero propio se avisa fuerte pero no
        # tumba una producción en marcha (evita una caída por un aviso de higiene).
        _blocking = settings.blocking_secret_problems()
        if settings.is_production and _blocking:
            _seclog.critical(
                "ARRANQUE BLOQUEADO por seguridad: %s. Genera secretos largos y "
                "aleatorios (p. ej. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`), "
                "ponlos en el .env del servidor (JWT_SECRET / PORTAL_TOKEN_SECRET) y reinicia.",
                "; ".join(_blocking),
            )
            raise RuntimeError(f"Secretos inseguros en producción: {'; '.join(_blocking)}")
        _seclog.warning("Revisa los secretos de firma: %s", detalle)

    # Aviso claro en los logs si el email está activado pero sin configurar: es
    # la causa nº1 de "no llegan los correos" (típicamente SMTP_PASS vacío).
    from app.services.email_service import email_config_status

    _cfg = email_config_status()
    if settings.emails_enabled and not _cfg["ready"]:
        logging.getLogger("app.email").warning(
            "EMAIL SIN CONFIGURAR: no saldrán correos. Falta: %s. "
            "Rellena el .env del servidor y reinicia.", ", ".join(_cfg["missing"]),
        )

    # Aviso si Stripe está a medias (clave puesta pero faltan precios/webhook).
    if settings.stripe_enabled:
        _missing = ["STRIPE_WEBHOOK_SECRET"] if not settings.stripe_webhook_secret else []
        _missing += [
            f"STRIPE_PRICE_{t.upper()}_{p.upper()}"
            for t in ("nutri", "train", "full") for p in ("1m", "3m", "6m")
            if not settings.stripe_price_for(t, p)
        ]
        if _missing:
            logging.getLogger("app.stripe").warning(
                "Stripe sin IDs en el .env (%s): se resolverán por lookup_key. "
                "Si aún no existen, ejecuta scripts/setup_stripe_prices.py.",
                ", ".join(_missing))

    # El scheduler se desactiva en tests/CI con SCHEDULER_ENABLED=false.
    # Vive en Settings como el resto de la config (una sola fuente de verdad).
    scheduler_on = settings.scheduler_enabled
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler, start_scheduler

        start_scheduler()
    yield
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler

        shutdown_scheduler()
    engine.dispose()


# En producción se OCULTAN la documentación interactiva y el esquema OpenAPI:
# exponerlos da a un desconocido el mapa completo de la API (facilita copiarla y
# buscar puntos débiles). En dev siguen disponibles en /api/docs.
_docs_url = None if settings.is_production else "/api/docs"
_openapi_url = None if settings.is_production else "/api/openapi.json"

app = FastAPI(
    title="Sistema de Asesorías Fitness",
    version=APP_VERSION,
    docs_url=_docs_url,
    redoc_url=None,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)

# Rate limiting compartido (los routers definen sus límites con su propio
# Limiter; este objeto en app.state habilita el manejador global de errores).
app.state.limiter = Limiter(key_func=client_key)

# Archivos PÚBLICOS (foto de la landing, portada y vídeos de ejercicios).
# Bajo /api/* para que Caddy los proxyee; StaticFiles soporta Range (el vídeo
# se puede adelantar/atrasar sin descargarlo entero).
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.services.storage import media_dir  # noqa: E402

app.mount("/api/media", StaticFiles(directory=media_dir()), name="media")


@app.exception_handler(StarletteHTTPException)
def _http_error_handler(request: Request, exc: StarletteHTTPException):
    """Los ENLACES DE PAGO los abre una persona: un 404 en JSON crudo
    ({"detail":"No encontrado"}) es lo que veía un cliente cuyo enlace había
    caducado porque se le regeneró el acceso al portal. Se le da una página que
    explica qué hacer; el resto de la API sigue devolviendo JSON."""
    if request.url.path.startswith("/api/pay/") and exc.status_code in (403, 404):
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Enlace caducado</title></head>"
            "<body style=\"font-family:system-ui,sans-serif;max-width:32rem;"
            "margin:3rem auto;padding:0 1.25rem;text-align:center\">"
            "<h1 style='font-size:1.2rem'>Este enlace de pago ya no vale</h1>"
            "<p>Se ha renovado por seguridad. Escríbeme y te paso uno nuevo al "
            "momento: no pierdes nada.</p></body></html>",
            status_code=exc.status_code,
        )
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail})


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Los ENLACES DE PAGO los abre una persona en su navegador: un JSON crudo
    # ("detail: Demasiadas peticiones") parecía la web rota y era justo el
    # momento de cobrar. Se le da una página legible que puede reintentar.
    if request.url.path.startswith("/api/pay/"):
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Un momento…</title></head>"
            "<body style=\"font-family:system-ui,sans-serif;max-width:32rem;"
            "margin:3rem auto;padding:0 1.25rem;text-align:center\">"
            "<h1 style='font-size:1.2rem'>Un momento, por favor</h1>"
            "<p>Se han abierto muchos pagos seguidos desde esta conexión. "
            "Espera unos segundos y vuelve a intentarlo.</p>"
            "<p><a href='' style=\"display:inline-block;background:#E8833A;"
            "color:#fff;text-decoration:none;font-weight:700;padding:0.9rem 1.5rem;"
            "border-radius:0.75rem\">Reintentar</a></p></body></html>",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Demasiadas peticiones, inténtalo en un momento"},
    )


# Los errores NO controlados dejaban un 500 opaco ("Internal Server Error") que
# no decía nada al coach ni facilitaba el diagnóstico. Ahora: traza completa en
# los logs + causa legible en la respuesta SOLO para el coach autenticado.
_errlog = logging.getLogger("app.errors")


def _peticion_de_coach(request: Request) -> bool:
    """¿La petición trae un JWT de coach válido? Solo entonces se expone el
    detalle del error. Antes se decidía por PREFIJO de ruta, pero rutas
    PRE-login como /api/auth/login (accesibles por cualquier anónimo) no
    estaban en la lista y filtraban el tipo/mensaje de la excepción (posibles
    fragmentos de SQL, rutas internas…). Atarlo a la autenticación cierra ese
    hueco para todas las rutas presentes y futuras."""
    from app.security import decode_access_token

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return False
    return decode_access_token(auth[7:].strip()) is not None


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _errlog.exception("Error no controlado en %s %s", request.method,
                      enmascara_tokens(request.url.path))
    # A un desconocido NUNCA se le da el detalle interno del error (va al log).
    # Al coach autenticado sí, para que la web muestre la causa sin ir al servidor.
    detail = (f"Error interno ({type(exc).__name__}): {exc}"
              if _peticion_de_coach(request)
              else "Error interno, inténtalo de nuevo en un momento")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": {"message": detail}},
    )


# CORS: en producción el ÚNICO origen legítimo es el dominio público. Los
# localhost solo se permiten en desarrollo — dejarlos en producción daba a
# cualquier página del localhost de la víctima (un dev-server, una app local)
# un origen de confianza para pedir a la API con credenciales. Métodos y
# cabeceras se enumeran (antes '*') para no exponer más de lo que se usa.
_cors_origins = [settings.public_base_url]
if not settings.is_production:
    _cors_origins += ["http://localhost", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class SecurityHeadersMiddleware:
    """Cabeceras de seguridad a nivel de aplicación (defensa en profundidad
    además de las de Caddy; también protegen si se accede a la API directamente).

    Es ASGI puro (no BaseHTTPMiddleware): solo AÑADE cabeceras en la respuesta,
    sin leer/buffer el cuerpo — así NO rompe el streaming ni las peticiones Range
    de los vídeos de ejercicios (/api/media).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")

        async def _send(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                # El navegador no adivina el tipo (bloquea trucos de sniffing).
                headers.append((b"x-content-type-options", b"nosniff"))
                # El PORTAL sirve datos de salud por token en la URL: ni se
                # cachea (historial/proxies) ni se filtra el token por Referer.
                if path.startswith("/api/p/"):
                    headers.append((b"cache-control", b"no-store"))
                    headers.append((b"referrer-policy", b"no-referrer"))
            await send(message)

        await self.app(scope, receive, _send)


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(exercises.router)
app.include_router(brand.router)
app.include_router(resources.router)
app.include_router(plans.router)
app.include_router(plan_library.router)
app.include_router(alerts.router)
app.include_router(ai_credit.router)
app.include_router(payments.router)
app.include_router(sales.router)
app.include_router(learning.router)
app.include_router(email.router)
app.include_router(stripe_router.router)
app.include_router(coach_push.router)
app.include_router(google_oauth.router)
app.include_router(public_site.router)
app.include_router(whatsapp.router)
app.include_router(portal_public.router)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Health check para monitoring (VPS) y para el healthcheck de Docker."""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": APP_VERSION,
        "database": "up" if db_ok else "down",
    }
