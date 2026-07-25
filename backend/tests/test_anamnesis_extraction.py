"""Tests de extracción y control de calidad de la anamnesis (hardening §5)."""
from __future__ import annotations

from datetime import date, timedelta

from app.services.anamnesis_extraction import (
    COVERAGE_MATRIX,
    client_portrait,
    coverage_gaps,
    detect_contradictions,
    dual_pass_extract,
)


def _codes(cs):
    return {c.code for c in cs}


def test_contradiccion_perder_y_ganar():
    prof = {"goal_type": "fat_loss", "lifestyle_notes": "Quiero ganar masa muscular y estar fuerte"}
    assert "perder_y_ganar" in _codes(detect_contradictions(prof))


def test_contradiccion_dieta_vs_alimentos():
    prof = {"diet_pattern": "vegano", "food_likes": ["pollo", "arroz"]}
    cs = detect_contradictions(prof)
    assert "dieta_vs_alimentos" in _codes(cs)


def test_contradiccion_plazo_imposible():
    prof = {"start_weight_kg": 90, "goal_weight_kg": 75,
            "goal_deadline": (date.today() + timedelta(days=30)).isoformat()}
    assert "plazo_imposible" in _codes(detect_contradictions(prof))


def test_plazo_razonable_no_contradice():
    prof = {"start_weight_kg": 90, "goal_weight_kg": 85,
            "goal_deadline": (date.today() + timedelta(days=70)).isoformat()}
    assert "plazo_imposible" not in _codes(detect_contradictions(prof))


def test_cliente_sano_sin_contradicciones():
    prof = {"goal_type": "fat_loss", "lifestyle_notes": "Quiero perder grasa y verme mejor"}
    assert detect_contradictions(prof) == []


def test_matriz_de_cobertura_sin_huecos():
    # Cada campo del formulario influye en algo y tiene un test que lo demuestra.
    assert coverage_gaps() == []
    for k, v in COVERAGE_MATRIX.items():
        assert v["influye"] and v["test"], k


def test_retrato_del_cliente_conciso():
    prof = {"sex": "male", "goal_type": "fat_loss", "level": "beginner", "training_days": 3,
            "lifestyle_notes": "Trabajo a turnos y como fuera a menudo",
            "food_allergies": ["lactosa"], "session_max_min": 60}
    p = client_portrait(prof)
    assert "perder grasa" in p
    assert "turnos" in p
    assert len(p.splitlines()) <= 10


def test_doble_pase_coincidente_alta_confianza():
    a = lambda: {"sex": "male", "start_weight_kg": 80, "goal_type": "fat_loss"}
    r = dual_pass_extract(a, a)
    assert not r.needs_review
    assert all(c >= 0.85 for c in r.confidence.values())


def test_doble_pase_discrepancia_en_critico_pide_revision():
    a = lambda: {"sex": "male", "start_weight_kg": 80}
    b = lambda: {"sex": "female", "start_weight_kg": 80}   # discrepa en 'sex' (crítico)
    r = dual_pass_extract(a, b)
    assert r.needs_review
    assert any("sex" in d for d in r.discrepancies)


def test_doble_pase_baja_confianza_en_critico():
    a = lambda: ({"goal_type": "fat_loss"}, {"goal_type": 0.6})   # confianza baja
    b = lambda: ({"goal_type": "fat_loss"}, {"goal_type": 0.6})
    r = dual_pass_extract(a, b)
    assert r.needs_review  # coinciden pero confianza <0,85 en campo crítico
