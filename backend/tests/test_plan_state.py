"""Tests del PlanState — modelo único, versionado y propagación (hardening §4)."""
from __future__ import annotations

from app.services.plan_state import PlanState


def _nut():
    return {
        "tdee_kcal": 2500, "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
        "meals": [
            {"slot": 1, "name": "Desayuno", "target": {"kcal": 600, "protein_g": 45, "carbs_g": 60, "fat_g": 18}},
            {"slot": 2, "name": "Comida", "target": {"kcal": 1400, "protein_g": 105, "carbs_g": 140, "fat_g": 42}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": [
            {"slot": 1, "options": [
                {"key": "A", "title": "Avena con pollo",
                 "ingredients": [{"food": "Copos de avena", "grams": 80},
                                  {"food": "Pechuga de pollo", "grams": 150}],
                 "macros": {"kcal": 600, "protein_g": 45, "carbs_g": 60, "fat_g": 18}}]},
        ]},
    }


def test_estado_inicial_coherente_v1():
    ps = PlanState.new(_nut(), weight_kg=80)
    assert ps.current.version == 1
    nut = ps.current.nutrition
    m = nut["macros"]
    # kcal ≡ 4/4/9 tras reconciliar
    assert nut["target_kcal"] == m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9


def test_top_down_propaga_y_versiona():
    ps = PlanState.new(_nut(), weight_kg=80)
    ps.apply_targets(target_kcal=2500, weight_kg=80)
    assert ps.current.version == 2
    nut = ps.current.nutrition
    m = nut["macros"]
    assert nut["target_kcal"] == m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    # Σ comidas ≡ total, eje a eje
    for axis, total in (("protein_g", m["protein_g"]), ("carbs_g", m["carbs_g"]), ("fat_g", m["fat_g"])):
        assert sum(mm["target"][axis] for mm in nut["meals"]) == total


def test_bottom_up_recalcula_opcion_y_avisa():
    ps = PlanState.new(_nut(), weight_kg=80)
    food_lookup = {
        "Copos de avena": {"kcal": 375, "protein_g": 13.5, "carbs_g": 60, "fat_g": 7},
        "Pechuga de pollo": {"kcal": 120, "protein_g": 22.5, "carbs_g": 0, "fat_g": 2.6},
    }
    # subir mucho la avena descuadra la opción respecto al objetivo de la comida
    ps2, warnings = ps.edit_ingredient_grams(
        slot=1, option_key="A", food="Copos de avena", grams=250, food_lookup=food_lookup)
    assert ps2.current.version == 2
    opt = ps2.current.nutrition["meal_bank"]["slots"][0]["options"][0]
    # macros recalculados desde composición real (250 g avena + 150 g pollo)
    assert opt["macros"]["carbs_g"] == 150.0   # 250*0.60
    assert warnings  # se desvía del objetivo → avisa


def test_revert_restaura_version():
    ps = PlanState.new(_nut(), weight_kg=80)
    kcal_v1 = ps.current.nutrition["target_kcal"]
    ps.apply_targets(target_kcal=3000, weight_kg=80)
    assert ps.current.nutrition["target_kcal"] != kcal_v1
    ps.revert(1)
    assert ps.current.nutrition["target_kcal"] == kcal_v1
    assert len(ps.history) == 3   # v1, v2 (ajuste), v3 (revert)


def test_editar_ingrediente_inexistente_no_rompe():
    ps = PlanState.new(_nut(), weight_kg=80)
    _, warnings = ps.edit_ingredient_grams(slot=9, option_key="Z", food="X", grams=10)
    assert warnings and "no existe" in warnings[0]
