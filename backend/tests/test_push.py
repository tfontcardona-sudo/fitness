"""Tests de Web Push (TRASPASO §8.1).

Dos bloques:
- Puros (sin BD): detección de sesión del día, diario rellenado, ventana
  horaria y construcción del payload.
- Integración (requieren PostgreSQL, como test_portal): pendientes reales de
  un cliente, upsert de suscripciones y el job `run_push_reminders` con el
  envío monkeypatcheado (nunca se llama a servicios de push reales).
"""

from __future__ import annotations

import json
import uuid
import warnings
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

warnings.filterwarnings("ignore")

from app.services import push as push_svc  # noqa: E402
from app.services.portal import DAY_LABELS  # noqa: E402


# ------------------------------------------------------------- puros ----

def test_has_session_on() -> None:
    monday = date(2026, 6, 29)  # lunes
    training = {"sessions": [{"day": "Lunes"}, {"day": " jueves "}]}
    assert push_svc.has_session_on(training, monday) is True
    assert push_svc.has_session_on(training, monday + timedelta(days=1)) is False  # martes
    assert push_svc.has_session_on(training, monday + timedelta(days=3)) is True   # jueves
    assert push_svc.has_session_on(None, monday) is False
    assert push_svc.has_session_on({}, monday) is False


def _fake_log(**kw) -> SimpleNamespace:
    base = {f: None for f in push_svc._DIARY_FIELDS}
    base.update(kw)
    return SimpleNamespace(**base)


def test_diary_is_filled() -> None:
    assert push_svc.diary_is_filled(None) is False
    assert push_svc.diary_is_filled(_fake_log()) is False               # fila vacía (autosave)
    assert push_svc.diary_is_filled(_fake_log(free_notes="")) is False  # "" no cuenta
    assert push_svc.diary_is_filled(_fake_log(weight_kg=71.2)) is True
    assert push_svc.diary_is_filled(_fake_log(diet_adherence="yes")) is True


def test_within_active_hours() -> None:
    tz = ZoneInfo("Europe/Madrid")
    mk = lambda h: datetime(2026, 7, 3, h, 0, tzinfo=tz)  # noqa: E731
    assert push_svc._within_active_hours(mk(7)) is False
    assert push_svc._within_active_hours(mk(8)) is True
    assert push_svc._within_active_hours(mk(21)) is True
    assert push_svc._within_active_hours(mk(22)) is False


def test_build_reminder_payload() -> None:
    one = push_svc.build_reminder_payload(
        {"diary": True, "workout": False, "quincenal": False, "count": 1},
        "DQ", "https://x/p/abc",
    )
    assert one["title"] == "DQ"
    assert one["count"] == 1
    assert one["url"] == "https://x/p/abc"
    assert "el diario de hoy" in one["body"]

    three = push_svc.build_reminder_payload(
        {"diary": True, "workout": True, "quincenal": True, "count": 3}, "DQ", "u"
    )
    assert three["count"] == 3
    assert "entreno" in three["body"] and "diario" in three["body"]
    assert "y la revisión quincenal" in three["body"]


def test_push_configured(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "push_enabled", True)
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")
    assert push_svc.push_configured() is True
    monkeypatch.setattr(settings, "vapid_private_key", "")
    assert push_svc.push_configured() is False
    monkeypatch.setattr(settings, "vapid_private_key", "priv")
    monkeypatch.setattr(settings, "push_enabled", False)
    assert push_svc.push_configured() is False


# -------------------------------------------------- integración (PG) ----

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
def client_with_plan(db):
    """Cliente + plan publicado (sesión HOY) + período abierto empezado hace 2 días."""
    from app.models import Client, Period, Plan

    today = date.today()
    uid = uuid.uuid4().hex[:10]
    client = Client(
        full_name=f"Push Test {uid}",
        email=f"push-{uid}@test.local",
        portal_token=f"tok-push-{uid}-{uuid.uuid4().hex}",
        status="active",
    )
    db.add(client)
    db.flush()
    plan = Plan(
        client_id=client.id, month_index=1, version=1, status="published",
        training_json={"sessions": [{"day": DAY_LABELS[today.weekday()], "exercises": []}]},
        nutrition_json={},
    )
    db.add(plan)
    db.flush()
    period = Period(
        client_id=client.id, plan_id=plan.id, period_index=1,
        starts_on=today - timedelta(days=2), ends_on=today + timedelta(days=11),
        status="open",
    )
    db.add(period)
    db.flush()
    yield client, plan, period
    # Limpieza (FKs sin cascade: hijos primero)
    from app.models import AuditLog, DailyLog, PushSubscription, WorkoutLog

    for log in db.query(DailyLog).filter_by(period_id=period.id):
        db.query(WorkoutLog).filter_by(daily_log_id=log.id).delete()
        db.delete(log)
    db.query(PushSubscription).filter_by(client_id=client.id).delete()
    db.query(AuditLog).filter_by(entity="client", entity_id=client.id).delete()
    db.flush()
    # Sin relación ORM Plan↔Period, el orden de DELETE hay que forzarlo a mano
    db.delete(period)
    db.flush()
    db.delete(plan)
    db.flush()
    db.delete(client)
    db.commit()


@needs_db
def test_pending_for_client(db, client_with_plan) -> None:
    from app.models import DailyLog, WorkoutLog

    client, plan, period = client_with_plan
    today = date.today()

    # Día 3, nada registrado → falta diario + entreno (hoy hay sesión), no quincenal
    p = push_svc.pending_for_client(db, client, today)
    assert p == {"diary": True, "workout": True, "quincenal": False, "count": 2}

    # Fila de diario vacía (autosave) → sigue faltando el diario
    log = DailyLog(period_id=period.id, log_date=today)
    db.add(log)
    db.flush()
    assert push_svc.pending_for_client(db, client, today)["diary"] is True

    # Peso apuntado → diario hecho; entreno aún no
    log.weight_kg = 70.5
    db.flush()
    p = push_svc.pending_for_client(db, client, today)
    assert p["diary"] is False and p["workout"] is True and p["count"] == 1

    # Una serie registrada → todo al día
    db.add(WorkoutLog(daily_log_id=log.id, exercise_id=1, set_number=1, reps=8, weight_kg=40))
    db.flush()
    assert push_svc.pending_for_client(db, client, today)["count"] == 0

    # Día ≥14 → toca la revisión quincenal
    period.starts_on = today - timedelta(days=14)
    db.flush()
    p = push_svc.pending_for_client(db, client, today)
    assert p["quincenal"] is True and p["count"] == 1

    # Período cerrado → nada pendiente para el cliente
    period.status = "closed"
    db.flush()
    assert push_svc.pending_for_client(db, client, today)["count"] == 0


@needs_db
def test_save_subscription_upsert(db, client_with_plan) -> None:
    from sqlalchemy import select

    from app.models import PushSubscription

    client, _, _ = client_with_plan
    ep = f"https://push.example/{uuid.uuid4().hex}"
    push_svc.save_subscription(db, client, ep, "k1", "a1", "UA/1")
    push_svc.save_subscription(db, client, ep, "k2", "a2", "UA/2")  # mismo endpoint
    db.flush()
    subs = db.scalars(select(PushSubscription).where(PushSubscription.endpoint == ep)).all()
    assert len(subs) == 1
    assert subs[0].p256dh == "k2" and subs[0].auth == "a2"

    assert push_svc.remove_subscription(db, client, ep) is True
    assert push_svc.remove_subscription(db, client, ep) is False


@needs_db
def test_run_push_reminders_sends_and_respects_hours(db, client_with_plan, monkeypatch) -> None:
    from app.config import settings

    client, _, _ = client_with_plan
    monkeypatch.setattr(settings, "push_enabled", True)
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")
    monkeypatch.setattr(settings, "vapid_subject", "mailto:t@t.t")

    push_svc.save_subscription(db, client, f"https://push.example/{uuid.uuid4().hex}", "k", "a")
    db.commit()

    calls: list[dict] = []
    monkeypatch.setattr(
        push_svc, "webpush",
        lambda **kw: calls.append(kw),
    )

    tz = ZoneInfo(settings.tz)
    # La fixture se construye relativa a date.today() (período abierto y sesión
    # en el día de hoy), así que el "ahora" del job debe partir de hoy, no de una
    # fecha fija que solo era válida el día en que se escribió el test.
    today = date.today()
    noon = datetime(today.year, today.month, today.day, 12, 0, tzinfo=tz)

    summary = push_svc.run_push_reminders(db, now=noon)
    assert summary["clients_notified"] >= 1
    ours = [c for c in calls if client.portal_token in json.loads(c["data"])["url"]]
    assert len(ours) == 1
    payload = json.loads(ours[0]["data"])
    assert payload["count"] == 2  # diario + entreno de la fixture
    assert ours[0]["ttl"] == push_svc.PUSH_TTL_SECONDS

    # Fuera de horario (23:00) → no envía nada
    calls.clear()
    late = datetime(today.year, today.month, today.day, 23, 0, tzinfo=tz)
    summary = push_svc.run_push_reminders(db, now=late)
    assert "skipped" in summary and not calls


@needs_db
def test_expired_subscription_is_deleted(db, client_with_plan, monkeypatch) -> None:
    from sqlalchemy import select

    from app.config import settings
    from app.models import PushSubscription
    from app.services.push import WebPushException

    client, _, _ = client_with_plan
    monkeypatch.setattr(settings, "push_enabled", True)
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")

    ep = f"https://push.example/{uuid.uuid4().hex}"
    push_svc.save_subscription(db, client, ep, "k", "a")
    db.flush()

    def gone(**_kw):
        raise WebPushException("Gone", response=SimpleNamespace(status_code=410))

    monkeypatch.setattr(push_svc, "webpush", gone)
    sent = push_svc.send_to_client(db, client, {"title": "x", "body": "y", "count": 1})
    db.flush()
    assert sent == 0
    assert db.scalar(select(PushSubscription).where(PushSubscription.endpoint == ep)) is None
