"""Tests de la integración con Google Calendar / Meet (servicio, sin BD).

Cubren la parte con riesgo real (construcción de la petición a la API de Google y
extracción del enlace de Meet) sin tocar la red: se mockea `httpx` y el token de
acceso. El flujo OAuth (state firmado) se prueba de punta a punta con itsdangerous.
"""

from __future__ import annotations

import warnings
from datetime import datetime

import pytest

warnings.filterwarnings("ignore")

from app.config import settings  # noqa: E402
from app.services import google_calendar as gcal  # noqa: E402


@pytest.fixture(autouse=True)
def _google_configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    monkeypatch.setattr(settings, "google_calendar_id", "primary")
    monkeypatch.setattr(settings, "tz", "Europe/Madrid")


class _Resp:
    """Respuesta httpx falsa."""

    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._json


# --------------------------------------------------------------- OAuth ----

def test_authorize_url_and_state_roundtrip():
    url = gcal.build_authorize_url("coach1")
    assert url.startswith(gcal._AUTH_URL)
    for frag in ("client_id=cid", "access_type=offline", "prompt=consent",
                 "response_type=code", "state="):
        assert frag in url
    # El state firmado se puede verificar y devuelve el usuario del coach.
    import re
    from urllib.parse import unquote

    state = unquote(re.search(r"state=([^&]+)", url).group(1))
    assert gcal.verify_state(state) == "coach1"


def test_verify_state_rejects_tampering():
    with pytest.raises(gcal.GoogleCalendarError):
        gcal.verify_state("no-es-un-state-valido")


def test_build_authorize_url_requires_config(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    with pytest.raises(gcal.GoogleCalendarError):
        gcal.build_authorize_url("coach1")


# ------------------------------------------------------- meet url helper ----

def test_extract_meet_url():
    assert gcal._extract_meet_url({"hangoutLink": "https://meet.google.com/abc"}) == "https://meet.google.com/abc"
    assert gcal._extract_meet_url(
        {"conferenceData": {"entryPoints": [
            {"entryPointType": "more", "uri": "https://x"},
            {"entryPointType": "video", "uri": "https://meet.google.com/xyz"},
        ]}}
    ) == "https://meet.google.com/xyz"
    assert gcal._extract_meet_url({}) is None


def test_event_times_uses_business_tz():
    start, end = gcal._event_times(datetime(2026, 7, 21, 17, 0), 45)
    assert start["timeZone"] == "Europe/Madrid"
    assert start["dateTime"].startswith("2026-07-21T17:00")
    assert end["dateTime"].startswith("2026-07-21T17:45")


# ------------------------------------------------------- crear evento ----

def test_create_meet_event_builds_request(monkeypatch):
    monkeypatch.setattr(gcal, "_valid_access_token", lambda db: "tok-123")
    captured = {}

    def fake_post(url, params=None, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["json"] = json
        return _Resp({"id": "ev1", "hangoutLink": "https://meet.google.com/join",
                      "htmlLink": "https://calendar.google.com/ev1"})

    monkeypatch.setattr(gcal.httpx, "post", fake_post)

    out = gcal.create_meet_event(
        db=None, summary="Videollamada · Ana", description="revisión",
        start_at=datetime(2026, 7, 21, 17, 0), duration_min=30,
        attendee_email="ana@test.local")

    assert out == {"event_id": "ev1", "meet_url": "https://meet.google.com/join",
                   "html_link": "https://calendar.google.com/ev1"}
    # Meet: conferenceDataVersion=1 + sendUpdates=all + invitación al cliente
    assert captured["params"]["conferenceDataVersion"] == 1
    assert captured["params"]["sendUpdates"] == "all"
    assert captured["headers"]["Authorization"] == "Bearer tok-123"
    body = captured["json"]
    assert body["attendees"] == [{"email": "ana@test.local"}]
    assert body["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"] == "hangoutsMeet"
    # Recordatorios nativos configurados (no useDefault)
    assert body["reminders"]["useDefault"] is False
    methods = {(r["method"], r["minutes"]) for r in body["reminders"]["overrides"]}
    assert ("email", 1440) in methods and ("popup", 10) in methods


def test_create_meet_event_no_attendee(monkeypatch):
    monkeypatch.setattr(gcal, "_valid_access_token", lambda db: "tok")
    monkeypatch.setattr(gcal.httpx, "post",
                        lambda *a, **k: _Resp({"id": "ev", "hangoutLink": "https://meet.google.com/z"}))
    out = gcal.create_meet_event(
        db=None, summary="s", description="d",
        start_at=datetime(2026, 7, 21, 17, 0), duration_min=30, attendee_email=None)
    assert out["meet_url"] == "https://meet.google.com/z"


def test_create_meet_event_api_error_translated(monkeypatch):
    import httpx

    monkeypatch.setattr(gcal, "_valid_access_token", lambda db: "tok")

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(gcal.httpx, "post", boom)
    with pytest.raises(gcal.GoogleCalendarError):
        gcal.create_meet_event(db=None, summary="s", description="d",
                               start_at=datetime(2026, 7, 21, 17, 0), duration_min=30,
                               attendee_email=None)


def test_cancel_meet_event_ignores_404(monkeypatch):
    monkeypatch.setattr(gcal, "_valid_access_token", lambda db: "tok")
    monkeypatch.setattr(gcal.httpx, "delete", lambda *a, **k: _Resp(status_code=404))
    # 404/410 = el evento ya no existe: no debe lanzar (el objetivo ya se cumple)
    gcal.cancel_meet_event(db=None, event_id="nope")
