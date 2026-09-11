"""¿Va bien la planificación de este cliente? (services/goal_progress.py).

DETERMINISTA sobre la MISMA decisión del motor quincenal (`biweekly_engine`):
no es un segundo criterio inventado, es su traducción a lenguaje de coach.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest


def _db() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db(), reason="Requiere PostgreSQL")


def _mk_client(db, **over):
    from app.models import Client
    base = dict(
        full_name="GP Client", email=f"gp-{uuid.uuid4().hex[:8]}@x.com",
        portal_token=f"tok-{uuid.uuid4().hex}",
        sex="male", birth_date=date(1990, 1, 1),
        height_cm=178, current_weight_kg=84.0, body_fat_pct=None,
        goal_type="fat_loss", level="intermediate", training_days=4, status="active",
    )
    base.update(over)
    c = Client(**base)
    db.add(c)
    db.flush()
    return c


def _mk_plan(db, client_id):
    from app.models import Plan
    pl = Plan(client_id=client_id, month_index=1, status="published")
    db.add(pl)
    db.flush()
    return pl


def _mk_period(db, client_id, idx, starts, *, closing_weight=None, adherence_0_10=9,
               status="closed"):
    from app.models import Period
    p = Period(
        client_id=client_id, plan_id=_mk_plan(db, client_id).id, period_index=idx,
        starts_on=starts, ends_on=starts + timedelta(days=13),
        status=status, closing_weight_kg=closing_weight,
        adherence_diet_0_10=adherence_0_10,
    )
    db.add(p)
    db.flush()
    return p


def _add_weighins(db, period, series):
    from app.models import DailyLog
    for off, w in series:
        db.add(DailyLog(
            period_id=period.id,
            log_date=period.starts_on + timedelta(days=off), weight_kg=w,
            diet_adherence="yes",
        ))
    db.flush()


def test_sin_periodo_cerrado_no_hay_veredicto():
    from app.db import SessionLocal
    from app.services.goal_progress import evaluate_goal_progress
    with SessionLocal() as db:
        c = _mk_client(db)
        assert evaluate_goal_progress(db, c) is None
        db.rollback()


def test_va_bien_dentro_del_ritmo_de_perdida_de_grasa():
    from app.db import SessionLocal
    from app.services.goal_progress import evaluate_goal_progress
    with SessionLocal() as db:
        c = _mk_client(db, goal_type="fat_loss", body_fat_pct=None)
        p = _mk_period(db, c.id, 1, date(2026, 1, 1), closing_weight=83.0, adherence_0_10=9)
        # 84.0 -> 83.0 en 14 días (~0,6 %/semana): dentro de la diana "medium".
        _add_weighins(db, p, [(0, 84.0), (4, 83.7), (8, 83.3), (13, 83.0)])
        out = evaluate_goal_progress(db, c)
        assert out is not None
        assert out["status"] == "on_track"
        assert out["rule"] == "dentro_del_ritmo"
        assert out["evidence"] == []
        assert any("Adherencia" in s for s in out["strengths"])
        db.rollback()


def test_necesita_ajuste_por_adherencia_baja():
    from app.db import SessionLocal
    from app.services.goal_progress import evaluate_goal_progress
    with SessionLocal() as db:
        c = _mk_client(db, goal_type="fat_loss")
        p = _mk_period(db, c.id, 1, date(2026, 1, 1), closing_weight=83.5, adherence_0_10=3)
        _add_weighins(db, p, [(0, 84.0), (5, 83.8), (13, 83.5)])
        out = evaluate_goal_progress(db, c)
        assert out is not None
        assert out["status"] == "needs_attention"
        assert out["rule"] == "adherencia_baja"
        assert out["strengths"] == []
        assert any("30" in e or "adherencia" in e.lower() for e in out["evidence"])
        db.rollback()


def test_datos_insuficientes_con_un_solo_pesaje():
    from app.db import SessionLocal
    from app.services.goal_progress import evaluate_goal_progress
    with SessionLocal() as db:
        c = _mk_client(db)
        _mk_period(db, c.id, 1, date(2026, 1, 1), closing_weight=83.0)
        # Ningún registro diario: solo el peso de cierre = 1 punto.
        out = evaluate_goal_progress(db, c)
        assert out is not None
        assert out["status"] == "insufficient_data"
        db.rollback()


def test_solo_mira_periodos_cerrados_o_analizados():
    """Un período ABIERTO no cuenta: el veredicto es sobre la última revisión
    de verdad, no sobre una quincena a medias sin cerrar."""
    from app.db import SessionLocal
    from app.services.goal_progress import evaluate_goal_progress
    with SessionLocal() as db:
        c = _mk_client(db)
        _mk_period(db, c.id, 1, date(2026, 1, 1), status="open")
        assert evaluate_goal_progress(db, c) is None
        db.rollback()
