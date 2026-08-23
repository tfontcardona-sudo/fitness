"""Punto de entrada de la API.

Health check + CORS + registro de routers. Migraciones y seeds se ejecutan
en entrypoint.sh antes de arrancar; el scheduler se añade en la Fase 4.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.ratelimit import client_key
from app.db import engine
from app.routers import (
    ai_credit, alerts, auth, brand, clients, coach_push, email, exercises,
    google_oauth, learning, payments, plan_library,
    plans, portal_public, public_site,
    resources, stripe_router, whatsapp,
)

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
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
    _errlog.exception("Error no controlado en %s %s", request.method, request.url.path)
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
