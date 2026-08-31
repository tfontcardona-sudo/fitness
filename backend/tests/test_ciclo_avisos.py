"""El ciclo: automatismos, avisos y recordatorios (tanda 3 de la auditoría).

Fija cuatro fallos verificados a mano sobre el código de `main`:

1. Un correo FALLIDO contaba como enviado → el recordatorio no se reintentaba
   nunca (y los que solo se disparan un día concreto se perdían para siempre).
2. El aviso de videollamada al coach usaba una tag compartida: la segunda
   videollamada del día sustituía a la primera y el coach solo veía una.
3. La petición que el cliente escribe desde su portal no generaba aviso si aún
   no tenía planificación publicada (justo cuando más preguntas hace).
4. El badge de la app se apagaba con cualquier aviso sin `count` (sw.js).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

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


def _cliente(db, *, status="active"):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name="Aviso Tester", email=f"aviso-{uuid.uuid4().hex[:8]}@example.com",
               status=status, portal_token="tmp", emails_enabled=True)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _email_log(db, client_id, kind, status, *, today=None):
    from app.models import EmailLog

    today = today or date.today()
    db.add(EmailLog(
        client_id=client_id, kind=kind, subject="asunto", status=status,
        sent_at=datetime(today.year, today.month, today.day, 10, 0, tzinfo=timezone.utc),
    ))
    db.commit()


# ------------------------------------------------ 1) correos fallidos ----
def test_un_correo_fallido_no_bloquea_el_reintento(db):
    """SMTP caído deja fila `failed`: NO debe contar como 'ya enviado hoy'."""
    from app.services.jobs import _already_sent_today

    hoy = date.today()
    c = _cliente(db)
    assert _already_sent_today(db, c.id, "reminder_no_logs", hoy) is False

    _email_log(db, c.id, "reminder_no_logs", "failed", today=hoy)
    assert _already_sent_today(db, c.id, "reminder_no_logs", hoy) is False, (
        "un envío fallido bloqueaba el recordatorio del día entero"
    )


def test_un_correo_enviado_si_bloquea_el_reintento(db):
    """Lo que SÍ salió no se repite (idempotencia del job diario)."""
    from app.services.jobs import _already_sent_today

    hoy = date.today()
    c = _cliente(db)
    _email_log(db, c.id, "closing_due", "sent", today=hoy)
    assert _already_sent_today(db, c.id, "closing_due", hoy) is True


def test_correos_desactivados_no_se_reintentan(db):
    """`disabled` no es un fallo: el cliente los tiene apagados a propósito."""
    from app.services.jobs import _already_sent_today

    hoy = date.today()
    c = _cliente(db)
    _email_log(db, c.id, "onboarding_reminder_d3", "disabled", today=hoy)
    assert _already_sent_today(db, c.id, "onboarding_reminder_d3", hoy) is True


def test_tras_un_fallo_el_recordatorio_sale_al_reintentar(db, monkeypatch):
    """Extremo a extremo con el aviso de CERRAR la quincena: con el fallo de hoy
    ya registrado, el mantenimiento vuelve a intentarlo y el correo llega."""
    from sqlalchemy import func, select

    from app.config import settings
    from app.models import EmailLog, Period, Plan
    from app.services.email_service import EmailService
    from app.services.jobs import run_daily_maintenance

    enviados = []
    monkeypatch.setattr(EmailService, "_transport", lambda self, msg: enviados.append(msg))
    monkeypatch.setattr(settings, "emails_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_user", "u")
    monkeypatch.setattr(settings, "smtp_pass", "p")
    monkeypatch.setattr(settings, "smtp_from", "coach@example.com")

    hoy = date.today()
    c = _cliente(db, status="active")
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    # Quincena vencida y sin cerrar: dispara el aviso "cierra tu revisión".
    db.add(Period(client_id=c.id, plan_id=plan.id, period_index=1,
                  starts_on=hoy - timedelta(days=13), ends_on=hoy, status="open"))
    db.commit()

    # El intento de hoy FALLÓ (SMTP caído): queda su fila `failed`.
    _email_log(db, c.id, "closing_due", "failed", today=hoy)

    run_daily_maintenance(db, today=hoy)

    ok = db.scalar(
        select(func.count()).select_from(EmailLog).where(
            EmailLog.client_id == c.id,
            EmailLog.kind == "closing_due",
            EmailLog.status == "sent",
        )
    )
    assert ok >= 1, "el aviso de cerrar la quincena no se reintentó tras el fallo"


def test_lo_ya_enviado_no_se_repite_en_la_misma_ejecucion(db, monkeypatch):
    """La otra cara: si HOY ya salió, el mantenimiento no lo manda otra vez."""
    from sqlalchemy import func, select

    from app.config import settings
    from app.models import EmailLog, Period, Plan
    from app.services.email_service import EmailService
    from app.services.jobs import run_daily_maintenance

    monkeypatch.setattr(EmailService, "_transport", lambda self, msg: None)
    monkeypatch.setattr(settings, "emails_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_user", "u")
    monkeypatch.setattr(settings, "smtp_pass", "p")

    hoy = date.today()
    c = _cliente(db, status="active")
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    db.add(Period(client_id=c.id, plan_id=plan.id, period_index=1,
                  starts_on=hoy - timedelta(days=13), ends_on=hoy, status="open"))
    db.commit()
    _email_log(db, c.id, "closing_due", "sent", today=hoy)

    run_daily_maintenance(db, today=hoy)

    total = db.scalar(
        select(func.count()).select_from(EmailLog).where(
            EmailLog.client_id == c.id, EmailLog.kind == "closing_due")
    )
    assert total == 1, "se duplicó un aviso que ya había salido hoy"


# --------------------------------------- 2) tag por videollamada ----
def test_dos_videollamadas_el_mismo_dia_son_dos_avisos(db, monkeypatch):
    """La tag del aviso al coach lleva el id: dos videollamadas no se pisan."""
    from types import SimpleNamespace

    from app.services import push as push_svc

    payloads = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda _db, payload: payloads.append(payload) or 1)
    monkeypatch.setattr(push_svc, "send_to_client", lambda _db, _c, _p: 1)

    c = _cliente(db)
    for vc_id in (101, 202):
        vc = SimpleNamespace(id=vc_id, meet_url=None)
        push_svc._send_videocall_reminder(
            db, c, vc, "DQR", client_body="cuerpo", coach_body="cuerpo")

    tags = [p["tag"] for p in payloads]
    assert len(tags) == 2
    assert len(set(tags)) == 2, f"las dos videollamadas comparten tag: {tags}"
    assert all(t.startswith("dq-vc-coach") for t in tags)


# ------------------------- 3) petición de cambio sin plan publicado ----
def test_peticion_del_cliente_sin_plan_llega_al_coach(db):
    """Escribir al coach genera aviso AUNQUE aún no tenga planificación."""
    from app.models import ChangeRequest
    from app.routers.alerts import client_alerts

    c = _cliente(db, status="onboarding")  # sin ningún plan
    db.add(ChangeRequest(client_id=c.id, message="¿Puedo cambiar el día de pierna?",
                         status="open"))
    db.commit()

    kinds = [a["kind"] for a in client_alerts(db, c, date.today())]
    assert "change_request" in kinds, (
        "la petición del cliente sin plan publicado no generaba ningún aviso"
    )


def test_peticion_del_cliente_con_plan_sigue_llegando(db):
    """No se pierde el caso que ya funcionaba (cliente con plan publicado)."""
    from app.models import ChangeRequest, Plan
    from app.routers.alerts import client_alerts

    c = _cliente(db, status="active")
    db.add(Plan(client_id=c.id, month_index=1, version=1, status="published"))
    db.add(ChangeRequest(client_id=c.id, message="Una duda de la dieta", status="open"))
    db.commit()

    kinds = [a["kind"] for a in client_alerts(db, c, date.today())]
    assert "change_request" in kinds


# ------------------------------------------------- 4) badge (sw.js) ----
def test_sw_no_apaga_el_badge_sin_count():
    """El service worker solo toca el badge si el aviso TRAE `count`."""
    from pathlib import Path

    sw = Path(__file__).resolve().parents[2] / "frontend" / "public" / "sw.js"
    src = sw.read_text(encoding="utf-8")
    assert "data.count !== undefined" in src and "data.count !== null" in src, (
        "sw.js vuelve a tratar la ausencia de `count` como cero y apaga el badge"
    )
