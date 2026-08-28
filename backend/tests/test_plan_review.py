"""§9 (enganche): panel de supervisión + reparación determinista en la generación.

Con IA simulada (no gasta API): se comprueba que el panel anota color/ICP, que un
veto clínico escala a rojo y que la envoltura best-effort nunca rompe la generación.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from app.services.ai.generator import ClientContext


def _ctx(**over) -> ClientContext:
    base = dict(
        sex="male", age=30, height_cm=180, weight_kg=82, goal_type="fat_loss",
        level="intermediate", training_days=4, session_max_min=75,
        training_place="gym", diet_mode="flexible_7", meals_per_day=2,
        meal_schedule=[{"slot": 1, "name": "Desayuno", "time": "08:00"},
                       {"slot": 2, "name": "Cena", "time": "21:00"}],
        food_allergies=[], food_dislikes=[], food_likes=["pollo"],
        contraindications=set(), body_fat_pct=None,
        bmr=1780, tdee=2500, target_kcal=2000, energy_method="mifflin",
        exercise_library=[],
    )
    base.update(over)
    return ClientContext(**base)


def _client(**over):
    base = dict(
        birth_date=None, sex="male", height_cm=180, current_weight_kg=82,
        start_weight_kg=82, medical_notes=None, medication_notes=None,
        injuries_notes=None, lifestyle_notes=None, current_supplements=None,
        food_allergies=[], food_dislikes=[], meals_per_day=2, goal_type="fat_loss",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _nutrition() -> dict:
    # Coherente: target_kcal ≡ 4·P + 4·C + 9·G ≡ suma de comidas. Proteína 170 g
    # (2,07 g/kg para 82 kg) dentro del rango de fat_loss.
    return {
        "tdee_kcal": 2500, "target_kcal": 2000,
        "macros": {"protein_g": 170, "carbs_g": 150, "fat_g": 80},
        "rationale": "Déficit moderado para fat_loss.",
        "meals": [
            {"slot": 1, "name": "Desayuno", "time": "08:00",
             "target": {"kcal": 800, "protein_g": 68, "carbs_g": 60, "fat_g": 32}},
            {"slot": 2, "name": "Cena", "time": "21:00",
             "target": {"kcal": 1200, "protein_g": 102, "carbs_g": 90, "fat_g": 48}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    }


class _FakeAI:
    """generate_json devuelve SIEMPRE el mismo veredicto de revisor."""

    def __init__(self, veredicto="aprobado", puntuacion=88, hallazgos=None):
        self._v, self._p, self._h = veredicto, puntuacion, hallazgos or []

    def generate_json(self, *, model, system, user, schema, temperature=None, **_kw):
        return schema(veredicto=self._v, puntuacion_rubrica=self._p, hallazgos=self._h)


def test_panel_anota_color_e_icp_sin_ia():
    # Sin IA: corre solo el revisor 0 (determinista). Un plan válido no escala.
    from app.services.plan_review import review_generated_plan

    nut, review = review_generated_plan(_nutrition(), client=_client(), ctx=_ctx(), ai=None)
    assert review is not None
    assert review["color"] in ("verde", "ambar", "rojo")
    assert 0.0 <= review["icp"] <= 100.0
    assert nut["target_kcal"] == 2000  # plan intacto


def test_panel_con_revisores_ia_aprueba():
    from app.services.plan_review import review_and_repair

    nut, review = review_and_repair(
        _nutrition(), client=_client(), ctx=_ctx(), ai=_FakeAI("aprobado", 90))
    assert review["escalated"] is False
    assert review["color"] in ("verde", "ambar")
    assert review["iterations"] >= 1


def test_veto_clinico_escala_a_rojo():
    # La lista roja del perfil (medicación anticoagulante) fuerza veto → rojo.
    from app.services.plan_review import review_and_repair

    cl = _client(medication_notes="Toma Sintrom (anticoagulante)")
    _, review = review_and_repair(_nutrition(), client=cl, ctx=_ctx(), ai=_FakeAI())
    assert review["color"] == "rojo"
    assert review["vetoed"] is True
    assert review["red_flags"]


def test_best_effort_nunca_rompe():
    # Ante cualquier fallo del panel (aquí, nutrición None que rompe el
    # validador), la envoltura devuelve el plan tal cual — pero "no revisado"
    # NO puede parecer "aprobado": el resumen queda en ÁMBAR degradado con el
    # hallazgo "Revisión no ejecutada" para que el coach lo revise a mano.
    from app.services.plan_review import review_generated_plan

    nut, review = review_generated_plan(None, client=_client(), ctx=_ctx(), ai=None)
    assert nut is None
    assert review is not None
    assert review["color"] == "ambar"
    assert review["degraded_reviewers"] == ["panel"]
    assert any("Revisión no ejecutada" in f["title"] for f in review["findings"])
