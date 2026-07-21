"""Integración con Google Calendar + Meet (videollamadas Pro).

El coach conecta su cuenta de Google UNA vez (OAuth); se guarda el
`refresh_token` en `google_credentials` (fila única single-tenant). A partir de
ahí, al agendar una videollamada el sistema crea un evento en Google Calendar
con enlace de Meet e invita al cliente por email (Google le manda la invitación
con sus recordatorios nativos).

Se implementa con `httpx` (ya es dependencia) hablando directamente con las APIs
REST de Google, para no arrastrar las librerías pesadas `google-api-python-client`.
Todo está protegido por `settings.google_enabled`: sin las claves OAuth en el
.env, la integración queda desactivada y el sistema sigue con el flujo manual
(enlace de reservas por WhatsApp) sin romperse.

Endpoints REST usados:
- Autorización:  https://accounts.google.com/o/oauth2/v2/auth
- Token:         https://oauth2.googleapis.com/token
- Userinfo:      https://www.googleapis.com/oauth2/v2/userinfo
- Calendar:      https://www.googleapis.com/calendar/v3/calendars/{id}/events
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import GoogleCredential

logger = logging.getLogger("google")

# Permisos mínimos: crear/editar eventos de Calendar + saber el email conectado.
SCOPES = "openid email https://www.googleapis.com/auth/calendar.events"

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_CAL_BASE = "https://www.googleapis.com/calendar/v3/calendars"

# Margen para refrescar el token antes de que caduque del todo.
_EXPIRY_MARGIN = timedelta(seconds=90)
_STATE_SALT = "google-oauth"
_STATE_MAX_AGE = 600  # 10 min para completar el consentimiento


class GoogleCalendarError(Exception):
    """Error legible de la integración (config, conexión o API de Google)."""


# --------------------------------------------------------------- estado ----

def is_connected(db: Session) -> bool:
    if not settings.google_enabled:
        return False
    cred = db.scalar(select(GoogleCredential).limit(1))
    return bool(cred and cred.refresh_token)


def connection_status(db: Session) -> dict:
    """{enabled, connected, email} para la web del coach (Ajustes)."""
    cred = db.scalar(select(GoogleCredential).limit(1)) if settings.google_enabled else None
    return {
        "enabled": settings.google_enabled,
        "connected": bool(cred and cred.refresh_token),
        "email": (cred.google_email if cred else None),
    }


# ------------------------------------------------------- flujo OAuth ----

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.jwt_secret, salt=_STATE_SALT)


def build_authorize_url(coach: str) -> str:
    """URL de consentimiento de Google. `state` firmado (itsdangerous) para que
    el callback público solo acepte flujos iniciados por nosotros."""
    if not settings.google_enabled:
        raise GoogleCalendarError(
            "La integración con Google no está configurada (faltan GOOGLE_CLIENT_ID/SECRET en el .env).")
    state = _serializer().dumps({"u": coach})
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",   # imprescindible para recibir refresh_token
        "prompt": "consent",        # fuerza refresh_token nuevo en cada conexión
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{_AUTH_URL}?{httpx.QueryParams(params)}"


def verify_state(state: str) -> str:
    """Devuelve el usuario del coach codificado en `state` o lanza error."""
    try:
        data = _serializer().loads(state, max_age=_STATE_MAX_AGE)
    except SignatureExpired as exc:
        raise GoogleCalendarError("El enlace de conexión caducó, vuelve a intentarlo.") from exc
    except BadSignature as exc:
        raise GoogleCalendarError("Estado de OAuth no válido.") from exc
    return str(data.get("u") or "")


def exchange_code(db: Session, code: str) -> GoogleCredential:
    """Canjea el `code` del callback por tokens y persiste la credencial."""
    if not settings.google_enabled:
        raise GoogleCalendarError("La integración con Google no está configurada.")
    try:
        resp = httpx.post(_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=20)
        resp.raise_for_status()
        tok = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("fallo al canjear el code de Google: %s", exc)
        raise GoogleCalendarError("Google rechazó la conexión, inténtalo de nuevo.") from exc

    email = _fetch_email(tok.get("access_token"))
    cred = db.scalar(select(GoogleCredential).limit(1))
    if cred is None:
        cred = GoogleCredential()
        db.add(cred)
    cred.access_token = tok.get("access_token")
    # Google no siempre reenvía el refresh_token (solo la primera vez o con
    # prompt=consent): conservamos el anterior si no viene uno nuevo.
    if tok.get("refresh_token"):
        cred.refresh_token = tok["refresh_token"]
    cred.token_expiry = _expiry_from(tok.get("expires_in"))
    cred.scope = tok.get("scope")
    cred.google_email = email
    db.flush()
    return cred


def disconnect(db: Session) -> bool:
    cred = db.scalar(select(GoogleCredential).limit(1))
    if cred is None:
        return False
    # Best-effort: revocar el token en Google (si falla, igual borramos local).
    if cred.refresh_token or cred.access_token:
        try:
            httpx.post("https://oauth2.googleapis.com/revoke",
                       params={"token": cred.refresh_token or cred.access_token},
                       timeout=10)
        except httpx.HTTPError:
            pass
    db.delete(cred)
    db.flush()
    return True


def _expiry_from(expires_in) -> datetime:
    secs = int(expires_in or 3600)
    return datetime.now(timezone.utc) + timedelta(seconds=secs)


def _fetch_email(access_token: str | None) -> str | None:
    if not access_token:
        return None
    try:
        r = httpx.get(_USERINFO_URL,
                      headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        r.raise_for_status()
        return r.json().get("email")
    except httpx.HTTPError:
        return None


# --------------------------------------------------------- access token ----

def _valid_access_token(db: Session) -> str:
    """Devuelve un access_token válido, refrescándolo si hace falta."""
    cred = db.scalar(select(GoogleCredential).limit(1))
    if cred is None or not cred.refresh_token:
        raise GoogleCalendarError(
            "Google no está conectado. Conéctalo en Ajustes para agendar por Meet.")
    now = datetime.now(timezone.utc)
    if cred.access_token and cred.token_expiry and cred.token_expiry - _EXPIRY_MARGIN > now:
        return cred.access_token
    # Refrescar.
    try:
        resp = httpx.post(_TOKEN_URL, data={
            "refresh_token": cred.refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        }, timeout=20)
        resp.raise_for_status()
        tok = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("fallo al refrescar el token de Google: %s", exc)
        raise GoogleCalendarError(
            "Se perdió la conexión con Google (vuelve a conectarlo en Ajustes).") from exc
    cred.access_token = tok.get("access_token")
    cred.token_expiry = _expiry_from(tok.get("expires_in"))
    if tok.get("refresh_token"):
        cred.refresh_token = tok["refresh_token"]
    db.flush()
    return cred.access_token


# ------------------------------------------------------------- eventos ----

def _event_times(start_at: datetime, duration_min: int) -> tuple[dict, dict]:
    """Bloques start/end de Calendar en la zona horaria del coach."""
    tzname = settings.tz
    end_at = start_at + timedelta(minutes=duration_min)
    return (
        {"dateTime": start_at.isoformat(), "timeZone": tzname},
        {"dateTime": end_at.isoformat(), "timeZone": tzname},
    )


def create_meet_event(
    db: Session,
    *,
    summary: str,
    description: str,
    start_at: datetime,
    duration_min: int,
    attendee_email: str | None,
) -> dict:
    """Crea el evento con Google Meet e invita al cliente. Devuelve
    {event_id, meet_url, html_link}. Lanza GoogleCalendarError si algo falla."""
    token = _valid_access_token(db)
    start, end = _event_times(start_at, duration_min)
    body: dict = {
        "summary": summary,
        "description": description,
        "start": start,
        "end": end,
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        # Recordatorios NATIVOS de Google para ambos: email 1 día antes + aviso
        # emergente 1 h y 10 min antes. Es la primera capa "para que no pase por
        # alto" (además del push y el email de la propia app).
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 10},
            ],
        },
    }
    if attendee_email:
        body["attendees"] = [{"email": attendee_email}]

    url = f"{_CAL_BASE}/{settings.google_calendar_id}/events"
    try:
        resp = httpx.post(
            url,
            params={"conferenceDataVersion": 1, "sendUpdates": "all"},
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=25,
        )
        resp.raise_for_status()
        ev = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("fallo al crear el evento en Google Calendar: %s", exc)
        raise GoogleCalendarError(
            "No se pudo crear el evento en Google Calendar, inténtalo de nuevo.") from exc

    return {
        "event_id": ev.get("id"),
        "meet_url": _extract_meet_url(ev),
        "html_link": ev.get("htmlLink"),
    }


def update_meet_event(
    db: Session,
    *,
    event_id: str,
    start_at: datetime,
    duration_min: int,
) -> dict:
    """Reprograma (nueva fecha/hora) un evento existente y reavisa a los invitados."""
    token = _valid_access_token(db)
    start, end = _event_times(start_at, duration_min)
    url = f"{_CAL_BASE}/{settings.google_calendar_id}/events/{event_id}"
    try:
        resp = httpx.patch(
            url,
            params={"sendUpdates": "all"},
            headers={"Authorization": f"Bearer {token}"},
            json={"start": start, "end": end},
            timeout=25,
        )
        resp.raise_for_status()
        ev = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("fallo al reprogramar el evento de Google: %s", exc)
        raise GoogleCalendarError(
            "No se pudo reprogramar el evento en Google Calendar.") from exc
    return {"event_id": ev.get("id"), "meet_url": _extract_meet_url(ev),
            "html_link": ev.get("htmlLink")}


def cancel_meet_event(db: Session, *, event_id: str) -> None:
    """Cancela (borra) el evento y avisa a los invitados. Silencioso si ya no
    existe (404): el objetivo — que no quede el evento — ya se cumple."""
    token = _valid_access_token(db)
    url = f"{_CAL_BASE}/{settings.google_calendar_id}/events/{event_id}"
    try:
        resp = httpx.delete(
            url, params={"sendUpdates": "all"},
            headers={"Authorization": f"Bearer {token}"}, timeout=20)
        if resp.status_code not in (200, 204, 404, 410):
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("fallo al cancelar el evento de Google: %s", exc)
        raise GoogleCalendarError("No se pudo cancelar el evento en Google Calendar.") from exc


def _extract_meet_url(ev: dict) -> str | None:
    """El enlace de Meet: `hangoutLink` o el entryPoint de vídeo del conferenceData."""
    if ev.get("hangoutLink"):
        return ev["hangoutLink"]
    for ep in (ev.get("conferenceData", {}) or {}).get("entryPoints", []) or []:
        if ep.get("entryPointType") == "video" and ep.get("uri"):
            return ep["uri"]
    return None
