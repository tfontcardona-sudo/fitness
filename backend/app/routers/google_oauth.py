"""Conexión de la cuenta de Google del coach (OAuth) para Calendar + Meet.

Flujo (pocos clics):
1. El coach pulsa "Conectar con Google" en Ajustes → GET /api/google/oauth/start
   devuelve la URL de consentimiento y la web redirige allí.
2. El coach acepta en Google → Google redirige a /api/google/oauth/callback
   (PÚBLICO: Google no manda nuestro JWT) con ?code&state.
3. El callback canjea el code, guarda el refresh_token y redirige de vuelta a
   /recursos?google=connected. A partir de ahí, agendar crea el evento + Meet.

`GET /status` alimenta el estado (enabled/connected/email). `POST /disconnect`
borra la credencial. Todos menos el callback requieren el JWT del coach.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.services import google_calendar as gcal
from app.services.audit import log_event

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/status")
def status(db: Session = Depends(get_db),
           user: User = Depends(get_current_user)) -> dict:
    """Estado de la integración para la web del coach."""
    return gcal.connection_status(db)


@router.get("/oauth/start")
def oauth_start(db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> dict:
    """Devuelve la URL de consentimiento de Google (la web redirige a ella)."""
    return {"authorize_url": gcal.build_authorize_url(user.username)}


@router.get("/oauth/callback")
def oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Callback público de Google. Canjea el code y vuelve a Ajustes."""
    base = settings.public_base_url.rstrip("/")
    dest_ok = f"{base}/recursos?google=connected"
    dest_err = f"{base}/recursos?google=error"

    if error or not code or not state:
        return RedirectResponse(dest_err, status_code=302)
    try:
        gcal.verify_state(state)
        cred = gcal.exchange_code(db, code)
        log_event(db, "brand", 1, "google_connected", {"email": cred.google_email})
        db.commit()
    except gcal.GoogleCalendarError:
        db.rollback()
        return RedirectResponse(dest_err, status_code=302)
    return RedirectResponse(dest_ok, status_code=302)


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db),
               user: User = Depends(get_current_user)) -> dict:
    """Desconecta la cuenta de Google (borra la credencial)."""
    removed = gcal.disconnect(db)
    log_event(db, "brand", 1, "google_disconnected", None)
    db.commit()
    return {"disconnected": removed}
