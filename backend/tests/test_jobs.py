"""Tests de integración de los jobs del scheduler (Fase 4).

Requieren PostgreSQL (se saltan si no hay). Verifican el ciclo completo con
efectos reales: el job calcula hechos desde la DB, transiciona estados,
registra en audit_log y dispara emails (transporte mockeado para no enviar de
verdad). Comprueban la IDEMPOTENCIA: ejecutar el job dos veces el mismo día no
duplica transiciones ni emails.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture()
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _no_real_email(monkeypatch):
    """Sustituye el transporte SMTP: ningún email sale de verdad."""
    from app.services.email_service import EmailService

    sent = []
    monkeypatch.setattr(EmailService, "_transport", lambda self, msg: sent.append(msg))
    monkeypatch.setenv("EMAILS_ENABLED", "true")
    # settings ya está cacheado; forzamos el flag directamente
    from app.config import settings

    monkeypatch.setattr(settings, "emails_enabled", True)
    monkeypatch.setattr(settings, "smtp_from", "coach@example.com")
    return sent


def _make_client(db, *, status, email):
    import uuid

    from app.models import Client
    from app.security import new_portal_token

    # email único por ejecución para que los tests sean reejecutables sobre la
    # misma base de datos sin colisionar con el constraint de unicidad.
    unique_email = f"{uuid.uuid4().hex[:8]}.{email}"
    c = Client(full_name="Test Cliente", email=unique_email, status=status,
               portal_token="tmp", emails_enabled=True)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _make_period(db, client, *, start, end, status="open"):
    from app.models import Period, Plan

    plan = Plan(client_id=client.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    p = Period(client_id=client.id, plan_id=plan.id, period_index=1,
               starts_on=start, ends_on=end, status=status)
    db.add(p)
    db.commit()
    return p


def _add_log(db, period, log_date):
    from app.models import DailyLog

    db.add(DailyLog(period_id=period.id, log_date=log_date, diet_adherence="yes"))
    db.commit()


def _count_emails(db, client_id, kind):
    from sqlalchemy import func, select

    from app.models import EmailLog

    return db.scalar(
        select(func.count()).select_from(EmailLog)
        .where(EmailLog.client_id == client_id, EmailLog.kind == kind)
    )


def _count_status_changes(db, client_id):
    from sqlalchemy import func, select

    from app.models import AuditLog

    return db.scalar(
        select(func.count()).select_from(AuditLog)
        .where(AuditLog.entity == "client", AuditLog.entity_id == client_id,
               AuditLog.event == "status_changed")
    )


def test_job_transitions_to_at_risk_and_alerts_coach(db, _no_real_email):
    from app.services.jobs import run_daily_maintenance

    today = date(2026, 6, 20)
    client = _make_client(db, status="active", email="atrisk@example.com")
    # período terminado hace 5 días, sin cerrar
    _make_period(db, client, start=date(2026, 5, 26), end=date(2026, 6, 15), status="open")

    summary = run_daily_maintenance(db, today)
    db.refresh(client)

    assert client.status == "at_risk"
    assert summary["transitions"] >= 1
    assert _count_status_changes(db, client.id) == 1
    assert _count_emails(db, client.id, "coach_at_risk") == 1


def test_job_is_idempotent(db, _no_real_email):
    from app.services.jobs import run_daily_maintenance

    today = date(2026, 6, 20)
    client = _make_client(db, status="active", email="idem@example.com")
    _make_period(db, client, start=date(2026, 5, 26), end=date(2026, 6, 15), status="open")

    run_daily_maintenance(db, today)
    run_daily_maintenance(db, today)  # segunda pasada mismo día
    run_daily_maintenance(db, today)  # tercera

    db.refresh(client)
    assert client.status == "at_risk"
    # una sola transición y un solo email pese a 3 ejecuciones
    assert _count_status_changes(db, client.id) == 1
    assert _count_emails(db, client.id, "coach_at_risk") == 1


def test_job_sends_reminder_day_12(db, _no_real_email):
    from app.services.jobs import run_daily_maintenance

    start = date(2026, 6, 1)
    today = start + timedelta(days=11)  # día 12
    client = _make_client(db, status="active", email="reminder@example.com")
    period = _make_period(db, client, start=start, end=start + timedelta(days=13), status="open")
    # 4 registros: no at_risk pero por debajo del umbral de recordatorio
    for i in range(4):
        _add_log(db, period, start + timedelta(days=i))

    run_daily_maintenance(db, today)
    db.refresh(client)

    assert client.status == "active"  # el recordatorio no cambia estado
    assert _count_emails(db, client.id, "reminder_no_logs") == 1

    # idempotencia del recordatorio
    run_daily_maintenance(db, today)
    assert _count_emails(db, client.id, "reminder_no_logs") == 1


def test_job_marks_inactive_after_30_days(db, _no_real_email):
    from app.services.jobs import run_daily_maintenance

    today = date(2026, 6, 20)
    client = _make_client(db, status="active", email="inactive@example.com")
    # último log hace 35 días
    period = _make_period(db, client, start=date(2026, 4, 1), end=date(2026, 4, 14), status="open")
    _add_log(db, period, date(2026, 5, 16))

    run_daily_maintenance(db, today)
    db.refresh(client)
    assert client.status == "inactive"


def test_job_respects_client_email_toggle(db, _no_real_email):
    from app.services.jobs import run_daily_maintenance

    today = date(2026, 6, 20)
    client = _make_client(db, status="active", email="notoggle@example.com")
    client.emails_enabled = False
    db.commit()
    _make_period(db, client, start=date(2026, 5, 26), end=date(2026, 6, 15), status="open")

    run_daily_maintenance(db, today)
    db.refresh(client)
    # transiciona igual, pero el email queda registrado como "disabled"
    assert client.status == "at_risk"
    from sqlalchemy import select

    from app.models import EmailLog

    log = db.scalar(select(EmailLog).where(
        EmailLog.client_id == client.id, EmailLog.kind == "coach_at_risk"))
    assert log is not None and log.status == "disabled"
