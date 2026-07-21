"""Punto de entrada de la API.

Health check + CORS + registro de routers. Migraciones y seeds se ejecutan
en entrypoint.sh antes de arrancar; el scheduler se añade en la Fase 4.
"""

from contextlib import asynccontextmanager
import logging
import os

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
    alerts, auth, brand, clients, coach_push, email, exercises, plans,
    portal_public, public_site, resources, stripe_router,
)

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            for t in ("start", "full", "pro") for p in ("1m", "3m", "6m")
            if not settings.stripe_price_for(t, p)
        ]
        if _missing:
            logging.getLogger("app.stripe").warning(
                "STRIPE INCOMPLETO: los pagos pueden fallar. Falta: %s.", ", ".join(_missing))

    # El scheduler se desactiva en tests/CI con SCHEDULER_ENABLED=false.
    scheduler_on = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler, start_scheduler

        start_scheduler()
    yield
    if scheduler_on:
        from app.services.scheduler import shutdown_scheduler

        shutdown_scheduler()
    engine.dispose()


app = FastAPI(
    title="Sistema de Asesorías Fitness",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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
# los logs + causa legible en la respuesta (la web la muestra en el aviso).
# App single-tenant tras login: exponer el tipo/mensaje del error es aceptable
# y ahorra un viaje a los logs del servidor.
_errlog = logging.getLogger("app.errors")


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _errlog.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": {"message": f"Error interno ({type(exc).__name__}): {exc}"}},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.public_base_url,
        "http://localhost",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(exercises.router)
app.include_router(brand.router)
app.include_router(resources.router)
app.include_router(plans.router)
app.include_router(alerts.router)
app.include_router(email.router)
app.include_router(stripe_router.router)
app.include_router(coach_push.router)
app.include_router(public_site.router)
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
