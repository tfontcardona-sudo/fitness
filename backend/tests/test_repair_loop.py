"""Tests del bucle de reparación del panel (hardening §9)."""
from __future__ import annotations

from app.services.review_panel import (
    ReviewFinding,
    ReviewerVerdict,
    run_panel_with_repair,
)


def _coherent_plan() -> dict:
    m = {"protein_g": 150, "carbs_g": 200, "fat_g": 60}
    kcal = m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    p, c, f = m["protein_g"], m["carbs_g"], m["fat_g"]
    return {
        "target_kcal": kcal, "macros": m,
        "meals": [
            {"slot": 1, "target": {"kcal": (p // 2) * 4 + (c // 2) * 4 + (f // 2) * 9,
                                    "protein_g": p // 2, "carbs_g": c // 2, "fat_g": f // 2}},
            {"slot": 2, "target": {"kcal": (p - p // 2) * 4 + (c - c // 2) * 4 + (f - f // 2) * 9,
                                    "protein_g": p - p // 2, "carbs_g": c - c // 2, "fat_g": f - f // 2}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    }


def _profile(**kw):
    base = {"sex": "male", "age": 30, "height_cm": 178, "weight_kg": 80,
            "food_allergies": [], "food_dislikes": [], "meals_per_day": 2}
    base.update(kw)
    return base


def _incoherent_plan():
    p = _coherent_plan()
    p["target_kcal"] += 300   # rompe Atwater → bloqueante del validador 0
    return p


def test_reparacion_corrige_y_aprueba():
    calls = {"n": 0}

    def repair(plan, findings):
        calls["n"] += 1
        return _coherent_plan()  # la reparación arregla la incoherencia

    out = run_panel_with_repair(_incoherent_plan(), _profile(), repair=repair)
    assert not out.escalated
    assert out.iterations == 2          # 1ª falla, se repara, 2ª aprueba
    assert calls["n"] == 1
    assert out.final.color in ("verde", "ambar")


def test_reparacion_persistente_escala_tras_3_iteraciones():
    def repair(plan, findings):
        return _incoherent_plan()       # la reparación NO arregla nada

    out = run_panel_with_repair(_incoherent_plan(), _profile(), repair=repair)
    assert out.escalated
    assert out.iterations == 3          # máximo de iteraciones
    assert out.final.blocking()


def test_plan_ya_valido_no_itera():
    def repair(plan, findings):
        raise AssertionError("no debería llamarse")

    out = run_panel_with_repair(_coherent_plan(), _profile(), repair=repair)
    assert not out.escalated and out.iterations == 1


def test_reparacion_que_lanza_escala():
    def repair(plan, findings):
        raise RuntimeError("el generador falló")

    out = run_panel_with_repair(_incoherent_plan(), _profile(), repair=repair)
    assert out.escalated


def test_make_ai_reviewer_usa_ia_mock():
    from app.services.review_panel import make_ai_reviewer, REVIEWER_ROLES
    from app.schemas.ai import ReviewerOutput

    class FakeAI:
        def generate_json(self, *, model, system, user, schema):
            return ReviewerOutput(veredicto="aprobado", puntuacion_rubrica=88, hallazgos=[])

    reviewer = make_ai_reviewer(FakeAI(), plan_text="PLAN", anamnesis_text="ANAM")
    v = reviewer(REVIEWER_ROLES[0])
    assert v.veredicto == "aprobado" and v.puntuacion_rubrica == 88
    assert v.reviewer == REVIEWER_ROLES[0]["key"]
