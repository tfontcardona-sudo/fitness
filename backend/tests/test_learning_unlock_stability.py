"""Tests de §11 (estabilidad), §12 (desbloqueo progresivo), §13 (aprendizaje),
§14 (telemetría/versionado)."""
from __future__ import annotations

import pytest

from app.services.plan_stability import PROMPT_VERSION, PlanTelemetry, stability_score


# ---- §11 estabilidad + §14 telemetría (puro) ----

def test_estabilidad_planes_identicos_es_1():
    a = {"target_kcal": 2000, "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}}
    assert stability_score(a, a) == 1.0


def test_estabilidad_baja_con_divergencia():
    a = {"target_kcal": 2000, "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}}
    b = {"target_kcal": 2400, "macros": {"protein_g": 120, "carbs_g": 300, "fat_g": 40}}
    s = stability_score(a, b)
    assert 0.0 <= s < 0.9


def test_telemetria_serializa():
    t = PlanTelemetry(model="claude-x", generation_ms=1200, cost_usd=0.03,
                      repair_iterations=1, panel_color="ambar", icp=78.5, stability=0.9)
    j = t.to_json()
    assert j["prompt_version"] == PROMPT_VERSION
    assert j["panel_color"] == "ambar" and j["icp"] == 78.5


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


# ---- §13 aprendizaje continuo ----

@needs_db
def test_clasificador_de_ediciones():
    from app.services.continuous_learning import classify_edit
    assert classify_edit("meals.0.target.protein_g") == "calculo"
    assert classify_edit("meal_bank.slots.0.options.0.ingredients.1.food") == "seleccion_alimentos"
    assert classify_edit("training.sessions.0.exercises.2.sets") == "volumen"
    assert classify_edit("nutrition.rationale") == "redaccion"


@needs_db
def test_propuesta_de_mejoras_tras_repeticion():
    from app.db import SessionLocal
    from app.models import Client, Plan, PlanEdit
    from app.services.continuous_learning import propose_improvements, record_edit
    import uuid

    with SessionLocal() as db:
        db.query(PlanEdit).delete()
        db.commit()
        # crear un plan real para la FK
        c = Client(full_name="Edit", email=f"edit-{uuid.uuid4().hex[:8]}@x.com",
                   portal_token=uuid.uuid4().hex)
        db.add(c)
        db.commit()
        p = Plan(client_id=c.id, month_index=1, version=1, status="draft",
                 nutrition_json={}, training_json={}, education_json={})
        db.add(p)
        db.commit()
        for _ in range(3):
            record_edit(db, plan_id=p.id, category="calculo", field_path="macros.protein_g")
        md = propose_improvements(db)
        assert "calculo" in md and "requiere tu aprobación" in md.lower()


# ---- §12 desbloqueo progresivo ----

@needs_db
def test_segmentacion_cliente():
    from app.services.progressive_unlock import client_segment
    assert client_segment({"age": 30, "food_allergies": []}) == "adulto_sano_estandar"
    assert client_segment({"age": 30, "medical_notes": "Diabético"}) == "clinico"
    # un menor lo captura primero la lista roja (nunca auto-verde): "clinico"
    assert client_segment({"age": 16}) == "clinico"
    # edad ausente/ inválida (no numérica) → segmento "edad_fuera"
    assert client_segment({}) == "edad_fuera"
    assert client_segment({"age": 30, "diet_pattern": "vegano"}) == "dieta_compleja"


@needs_db
def test_desbloqueo_y_reversion():
    from app.db import SessionLocal
    from app.models import SegmentUnlock
    from app.services.progressive_unlock import (
        UNLOCK_STREAK, register_plan_outcome, segment_allows_green,
    )

    seg = "test_segment_x"
    with SessionLocal() as db:
        db.query(SegmentUnlock).filter(SegmentUnlock.segment == seg).delete()
        db.commit()
        for _ in range(UNLOCK_STREAK):
            row = register_plan_outcome(db, seg, clean=True)
        assert row.unlocked is True
        # una edición material revierte a ámbar
        row = register_plan_outcome(db, seg, clean=False)
        assert row.unlocked is False and row.clean_streak == 0


@needs_db
def test_segmento_clinico_nunca_verde():
    from app.db import SessionLocal
    from app.services.progressive_unlock import segment_allows_green
    with SessionLocal() as db:
        assert segment_allows_green(db, {"age": 40, "medical_notes": "Diabético"}) is False
