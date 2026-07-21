"""Tests del ciclo de videollamadas quincenales (Pro) y del push del coach.

- Alertas del ciclo: agendar → pendiente de fecha → reservada (mañana/confirmar)
  → realizada o reagendada (el ciclo vuelve a empezar).
- Suscripciones del COACH (upsert por endpoint) y condiciones de salto del
  resumen push `run_coach_digest` (horario activo, sin dispositivos).
"""

from __future__ import annotations

import uuid
import warnings
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

warnings.filterwarnings("ignore")

from app.services import push as push_svc  # noqa: E402


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture()
def db():
    from app.db import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def pro_client_reviewed(db):
    """Cliente PRO con plan publicado y período 1 CERRADO: toca la videollamada."""
    from app.models import Client, Period, Plan

    today = date.today()
    uid = uuid.uuid4().hex[:10]
    client = Client(
        full_name=f"VC Test {uid}",
        email=f"vc-{uid}@test.local",
        portal_token=f"tok-vc-{uid}-{uuid.uuid4().hex}",
        status="active",
        package_tier="pro",
    )
    db.add(client)
    db.flush()
    plan = Plan(
        client_id=client.id, month_index=1, version=1, status="published",
        training_json={}, nutrition_json={},
    )
    db.add(plan)
    db.flush()
    period = Period(
        client_id=client.id, plan_id=plan.id, period_index=1,
        starts_on=today - timedelta(days=16), ends_on=today - timedelta(days=2),
        status="closed",
    )
    db.add(period)
    db.flush()
    yield client, plan, period
    from app.models import AuditLog, VideoCall

    db.query(VideoCall).filter_by(client_id=client.id).delete()
    db.query(AuditLog).filter_by(entity="client", entity_id=client.id).delete()
    db.flush()
    # TODOS los períodos (los tests pueden abrir el siguiente): hijos primero.
    db.query(Period).filter_by(client_id=client.id).delete()
    db.flush()
    db.delete(plan)
    db.flush()
    db.delete(client)
    db.commit()


def _vc_alerts(db, client) -> list[dict]:
    from app.routers.alerts import client_alerts

    return [a for a in client_alerts(db, client, date.today())
            if a["kind"].startswith("video_call")]


@needs_db
def test_video_call_alert_cycle(db, pro_client_reviewed) -> None:
    from app.models import VideoCall

    client, _plan, _period = pro_client_reviewed
    today = date.today()
    now = datetime.now(ZoneInfo("Europe/Madrid"))

    # Revisión cerrada sin videollamada → esperando que el cliente proponga
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_wait"]

    # El cliente PROPONE día/hora → el coach debe aceptar o modificar
    vc = VideoCall(client_id=client.id, period_index=1, status="proposed",
                   scheduled_at=now + timedelta(days=3),
                   scheduled_for=today + timedelta(days=3))
    db.add(vc)
    db.flush()
    alerts = _vc_alerts(db, client)
    assert [a["kind"] for a in alerts] == ["video_call_proposed"]
    assert alerts[0]["severity"] == "alta"

    # El coach MODIFICA → pendiente de agendar a mano (acordar por WhatsApp)
    vc.status = "pending_manual"
    db.flush()
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_manual"]

    # Agendada para pasado mañana → sin alertas (aún no toca recordar)
    vc.status = "scheduled"
    vc.scheduled_for = today + timedelta(days=2)
    db.flush()
    assert _vc_alerts(db, client) == []

    # REGRESIÓN: se abre el período siguiente — la agendada NO puede desaparecer.
    from app.models import Period

    p2 = Period(client_id=client.id, plan_id=_plan.id, period_index=2,
                starts_on=today, ends_on=today + timedelta(days=13), status="open")
    db.add(p2)
    db.flush()

    # Mañana → recordatorio de severidad alta (AUNQUE haya un período abierto)
    vc.scheduled_for = today + timedelta(days=1)
    db.flush()
    alerts = _vc_alerts(db, client)
    assert [a["kind"] for a in alerts] == ["video_call_tomorrow"]
    assert alerts[0]["severity"] == "alta"

    # Fecha ya pasada → confirmar realizada o reagendar
    vc.scheduled_for = today - timedelta(days=1)
    db.flush()
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_confirm"]

    # Realizada → ciclo cerrado, sin alertas
    vc.status = "done"
    db.flush()
    assert _vc_alerts(db, client) == []


@needs_db
def test_no_video_call_alert_outside_pro(db, pro_client_reviewed) -> None:
    client, _plan, _period = pro_client_reviewed
    client.package_tier = "full"
    db.flush()
    assert _vc_alerts(db, client) == []


@needs_db
def test_schedule_meet_creates_event_and_persists(db, pro_client_reviewed, monkeypatch) -> None:
    """POST schedule-meet: crea el evento (gcal mockeado), guarda hora + Meet +
    id de evento y deja la videollamada en 'scheduled'. Reagendar cancela el
    evento en Google y limpia los campos."""
    import os

    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import VideoCall
    from app.security import create_access_token
    from app.services import google_calendar as gcal
    from app.services.email_service import EmailService

    client, _plan, _period = pro_client_reviewed
    db.commit()  # el endpoint usa su propia sesión: la fila debe estar confirmada

    # gcal mockeado (sin red): conectado + creación de evento con enlace de Meet.
    monkeypatch.setattr(gcal, "is_connected", lambda _db: True)
    created = {}
    def fake_create(_db, **kw):
        created.update(kw)
        return {"event_id": "ev-123", "meet_url": "https://meet.google.com/abc",
                "html_link": "https://calendar.google.com/ev-123"}
    monkeypatch.setattr(gcal, "create_meet_event", fake_create)
    # El email no debe dejar EmailLog (rompería el FK del teardown) ni enviar.
    monkeypatch.setattr(EmailService, "send", lambda self, **kw: "sent")

    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    http = TestClient(app)
    start = f"{(date.today() + timedelta(days=3)).isoformat()}T17:00"
    r = http.post(f"/api/clients/{client.id}/video-calls/schedule-meet", headers=auth,
                  json={"period_index": 1, "start_at": start, "duration_min": 45})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["meet_url"] == "https://meet.google.com/abc"
    assert body["duration_min"] == 45
    assert body["scheduled_at"] is not None
    # Se invitó al cliente por email en el evento.
    assert created["attendee_email"] == client.email

    db.expire_all()
    vc = db.scalar(select(VideoCall).where(VideoCall.client_id == client.id, VideoCall.period_index == 1))
    assert vc.google_event_id == "ev-123"
    assert vc.scheduled_for == date.today() + timedelta(days=3)

    # Reagendar: cancela el evento en Google y vuelve a 'pending' sin datos.
    cancelled = {}
    monkeypatch.setattr(gcal, "cancel_meet_event",
                        lambda _db, event_id: cancelled.update(event_id=event_id))
    r2 = http.post(f"/api/clients/{client.id}/video-calls/{vc.id}/reschedule", headers=auth)
    assert r2.status_code == 200, r2.text
    assert cancelled.get("event_id") == "ev-123"
    b2 = r2.json()
    assert b2["status"] == "pending_manual"
    assert b2["meet_url"] is None and b2["scheduled_at"] is None


@needs_db
def test_schedule_meet_requires_google_connected(db, pro_client_reviewed, monkeypatch) -> None:
    """Sin Google conectado, el endpoint responde 409 (no crea nada)."""
    import os

    from fastapi.testclient import TestClient

    from app.main import app
    from app.security import create_access_token
    from app.services import google_calendar as gcal

    client, _plan, _period = pro_client_reviewed
    db.commit()  # el endpoint usa su propia sesión: la fila debe estar confirmada
    monkeypatch.setattr(gcal, "is_connected", lambda _db: False)
    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    http = TestClient(app)
    start = f"{(date.today() + timedelta(days=3)).isoformat()}T17:00"
    r = http.post(f"/api/clients/{client.id}/video-calls/schedule-meet", headers=auth,
                  json={"period_index": 1, "start_at": start, "duration_min": 30})
    assert r.status_code == 409


@needs_db
def test_client_proposes_then_coach_accepts(db, pro_client_reviewed, monkeypatch) -> None:
    """El cliente propone día/hora desde su portal → el coach acepta → se crea el
    evento (gcal mockeado) y el portal pasa a 'scheduled' (tarjeta Unirme)."""
    import os

    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import VideoCall
    from app.security import create_access_token, new_portal_token
    from app.services import google_calendar as gcal
    from app.services.email_service import EmailService

    client, _plan, _period = pro_client_reviewed
    client.portal_token = new_portal_token(client.id)  # token firmado válido
    db.commit()
    http = TestClient(app)

    # 1) El cliente PROPONE (endpoint público del portal, token en la URL).
    start = f"{(date.today() + timedelta(days=4)).isoformat()}T18:00"
    rp = http.post(f"/api/p/{client.portal_token}/video-call", json={"start_at": start})
    assert rp.status_code == 200, rp.text
    assert rp.json()["state"] == "proposed"
    assert http.get(f"/api/p/{client.portal_token}/video-call").json()["state"] == "proposed"

    db.expire_all()
    vc = db.scalar(select(VideoCall).where(
        VideoCall.client_id == client.id, VideoCall.period_index == 1))
    assert vc.status == "proposed" and vc.scheduled_at is not None

    # 2) El coach ACEPTA → crea el evento y queda 'scheduled'.
    monkeypatch.setattr(gcal, "is_connected", lambda _db: True)
    monkeypatch.setattr(gcal, "create_meet_event", lambda _db, **kw: {
        "event_id": "evP", "meet_url": "https://meet.google.com/p", "html_link": "h"})
    monkeypatch.setattr(EmailService, "send", lambda self, **kw: "sent")
    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    ra = http.post(f"/api/clients/{client.id}/video-calls/{vc.id}/accept",
                   headers=auth, json={"duration_min": 30})
    assert ra.status_code == 200, ra.text
    b = ra.json()
    assert b["status"] == "scheduled" and b["meet_url"] == "https://meet.google.com/p"
    assert http.get(f"/api/p/{client.portal_token}/video-call").json()["state"] == "scheduled"


@needs_db
def test_coach_modify_sets_pending_manual(db, pro_client_reviewed) -> None:
    """Modificar deja la videollamada 'pendiente de agendar a mano' y el portal
    del cliente informa de que el coach le escribirá."""
    import os

    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import VideoCall
    from app.security import create_access_token, new_portal_token

    client, _plan, _period = pro_client_reviewed
    client.portal_token = new_portal_token(client.id)  # token firmado válido
    db.commit()
    http = TestClient(app)

    start = f"{(date.today() + timedelta(days=4)).isoformat()}T18:00"
    rp = http.post(f"/api/p/{client.portal_token}/video-call", json={"start_at": start})
    assert rp.status_code == 200, rp.text
    db.expire_all()
    vc = db.scalar(select(VideoCall).where(
        VideoCall.client_id == client.id, VideoCall.period_index == 1))

    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    rm = http.post(f"/api/clients/{client.id}/video-calls/{vc.id}/modify", headers=auth)
    assert rm.status_code == 200, rm.text
    assert rm.json()["status"] == "pending_manual"
    assert http.get(f"/api/p/{client.portal_token}/video-call").json()["state"] == "pending_manual"


@needs_db
def test_coach_subscription_upsert_and_digest_skips(db, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "push_enabled", True)
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")

    ep = f"https://push.example/coach-{uuid.uuid4().hex}"
    s1 = push_svc.save_coach_subscription(db, ep, "k1", "a1")
    s2 = push_svc.save_coach_subscription(db, ep, "k2", "a2")  # upsert, mismo endpoint
    assert s1.id == s2.id
    assert s2.is_coach is True and s2.client_id is None and s2.p256dh == "k2"

    # De madrugada no se molesta a nadie
    night = datetime(2026, 7, 20, 2, 0, tzinfo=ZoneInfo(settings.tz))
    assert "skipped" in push_svc.run_coach_digest(db, night.astimezone(timezone.utc))

    # Sin dispositivos del coach, el job se salta el resumen
    assert push_svc.remove_coach_subscription(db, ep) is True
    db.flush()
    day = datetime(2026, 7, 20, 12, 0, tzinfo=ZoneInfo(settings.tz))
    out = push_svc.run_coach_digest(db, day.astimezone(timezone.utc))
    assert out.get("skipped") == "el coach no tiene dispositivos suscritos"
