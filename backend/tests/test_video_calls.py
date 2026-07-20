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
    db.delete(period)
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

    # Revisión cerrada sin videollamada → toca agendarla
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_schedule"]

    # Propuesta enviada (pendiente de fecha) → sigue avisando (apuntar fecha)
    vc = VideoCall(client_id=client.id, period_index=1, status="pending")
    db.add(vc)
    db.flush()
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_schedule"]

    # Reservada para pasado mañana → sin alertas (aún no toca recordar)
    vc.status = "scheduled"
    vc.scheduled_for = today + timedelta(days=2)
    db.flush()
    assert _vc_alerts(db, client) == []

    # Mañana → recordatorio de severidad alta
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

    # NO se hizo (reagendar): vuelve a pendiente sin fecha → alerta de nuevo
    vc.status = "pending"
    vc.scheduled_for = None
    db.flush()
    assert [a["kind"] for a in _vc_alerts(db, client)] == ["video_call_schedule"]


@needs_db
def test_no_video_call_alert_outside_pro(db, pro_client_reviewed) -> None:
    client, _plan, _period = pro_client_reviewed
    client.package_tier = "full"
    db.flush()
    assert _vc_alerts(db, client) == []


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
