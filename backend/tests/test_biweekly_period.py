"""§8 (hardening): decisión quincenal determinista desde el cierre de período.

Verifica el PUENTE DB→motor (`decision_for_period`) sin tocar la IA: se crean
períodos con registros diarios y datos de cierre, y se comprueba que la regla que
dispara la decisión es la esperada. Es la parte del §8 que la CI puede ejercitar.
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
        full_name="BW Client", email=f"bw-{uuid.uuid4().hex[:8]}@x.com",
        portal_token=f"tok-{uuid.uuid4().hex}",
        sex="male", birth_date=date(1990, 1, 1),
        height_cm=178, current_weight_kg=82.0, body_fat_pct=18.0,
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
               waist=None, feelings=None):
    from app.models import Period
    p = Period(
        client_id=client_id, plan_id=_mk_plan(db, client_id).id, period_index=idx,
        starts_on=starts, ends_on=starts + timedelta(days=13),
        status="closed", closing_weight_kg=closing_weight,
        adherence_diet_0_10=adherence_0_10, closing_waist_cm=waist,
        closing_feelings_json=feelings,
    )
    db.add(p)
    db.flush()
    return p


def _add_weighins(db, period, series):
    """series: lista de (offset_dias, peso_kg) → DailyLog con peso."""
    from app.models import DailyLog
    for off, w in series:
        db.add(DailyLog(
            period_id=period.id,
            log_date=period.starts_on + timedelta(days=off), weight_kg=w,
            diet_adherence="yes",
        ))
    db.flush()


def test_request_data_con_un_solo_pesaje():
    from app.db import SessionLocal
    from app.services.biweekly_period import decision_for_period
    with SessionLocal() as db:
        c = _mk_client(db)
        p = _mk_period(db, c.id, 1, date(2026, 1, 1), closing_weight=82.0)
        # Ningún registro diario con peso → solo el de cierre = 1 punto.
        dec = decision_for_period(db, p, c)
        assert dec.action == "request_data"
        assert dec.rule == "dato_insuficiente"
        db.rollback()


def test_adherencia_baja_bloquea_kcal():
    from app.db import SessionLocal
    from app.services.biweekly_period import decision_for_period
    with SessionLocal() as db:
        c = _mk_client(db)
        p = _mk_period(db, c.id, 1, date(2026, 2, 1), closing_weight=81.0, adherence_0_10=5)
        _add_weighins(db, p, [(0, 82.0), (4, 81.7), (8, 81.4), (12, 81.1)])
        dec = decision_for_period(db, p, c)
        assert dec.action == "work_adherence"
        assert dec.rule == "adherencia_baja"
        assert dec.kcal_delta_pct == 0.0
        db.rollback()


def test_fuera_de_ritmo_ajusta_kcal_sin_tocar_proteina():
    from app.db import SessionLocal
    from app.services.biweekly_period import decision_for_period
    with SessionLocal() as db:
        c = _mk_client(db, goal_type="fat_loss", body_fat_pct=18.0)
        # Buena adherencia pero peso prácticamente plano en 2 semanas (pérdida
        # demasiado lenta para fat_loss) → ajuste de kcal, proteína bloqueada.
        p = _mk_period(db, c.id, 1, date(2026, 3, 1), closing_weight=81.95, adherence_0_10=10)
        _add_weighins(db, p, [(0, 82.0), (3, 82.0), (6, 81.98), (9, 81.97), (12, 81.96)])
        dec = decision_for_period(db, p, c)
        assert dec.action == "adjust_kcal"
        assert dec.rule == "fuera_del_ritmo"
        assert dec.protein_locked is True          # la proteína NUNCA se toca
        assert dec.kcal_delta_pct < 0.0            # pérdida demasiado lenta → más déficit
        db.rollback()


def test_serializable_y_con_snapshot():
    from app.db import SessionLocal
    from app.services.biweekly_period import decision_for_period, decision_to_json
    with SessionLocal() as db:
        c = _mk_client(db)
        p = _mk_period(db, c.id, 1, date(2026, 4, 1), closing_weight=81.0, adherence_0_10=9)
        _add_weighins(db, p, [(0, 82.0), (6, 81.5), (12, 81.0)])
        js = decision_to_json(decision_for_period(db, p, c))
        assert set(js) >= {"action", "rule", "rationale", "inputs_snapshot", "protein_locked"}
        assert js["inputs_snapshot"]["n_weigh_ins"] >= 3
        db.rollback()


def test_cerrar_por_el_coach_no_inventa_un_segundo_pesaje():
    """Un cliente que solo se pesó UNA vez y no envió la revisión: el coach la
    cierra y el peso de cierre se COPIA de ese mismo pesaje.

    Contarlo como medición nueva anulaba el guardarraíl de "un solo pesaje" y
    la regresión salía a 0,00 %/semana → el motor recortaba un −6 % de calorías
    de verdad sobre un dato que se había inventado el propio sistema.
    """
    from app.db import SessionLocal
    from app.services.biweekly_period import checkin_inputs_from_period, decision_for_period

    with SessionLocal() as db:
        c = _mk_client(db)
        p = _mk_period(db, c.id, 1, date(2026, 3, 1), closing_weight=82.0)
        _add_weighins(db, p, [(3, 82.0)])

        inputs = checkin_inputs_from_period(db, p, c)
        assert len(inputs.weight_points) == 1
        assert inputs.single_measurement is True
        dec = decision_for_period(db, p, c)
        assert dec.action == "request_data" and dec.kcal_delta_pct == 0.0

        # Con un peso de cierre DISTINTO sí hay dos mediciones de verdad.
        p.closing_weight_kg = 81.2
        db.flush()
        inputs = checkin_inputs_from_period(db, p, c)
        assert len(inputs.weight_points) == 2 and inputs.single_measurement is False
        db.rollback()
