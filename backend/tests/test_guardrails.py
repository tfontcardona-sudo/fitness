"""Tests unitarios de los guardrails (Fase 3) — E.4 nutrición y F.4 entrenamiento.

Aritmética pura, sin base de datos. Cada test fija un caso límite y comprueba
que el guardrail bloquea (violation) o avisa (warning) como debe.
"""

from __future__ import annotations

from app.services import guardrails as gr


# ===================================================== nutrición (E.4) ====

BASE_NUTRITION = {
    "target_kcal": 2200,
    "macros": {"protein_g": 175, "carbs_g": 210, "fat_g": 65},
    "meals": [
        {"slot": 1, "target": {"kcal": 550, "protein_g": 44, "carbs_g": 52, "fat_g": 16}},
        {"slot": 2, "target": {"kcal": 750, "protein_g": 60, "carbs_g": 72, "fat_g": 22}},
        {"slot": 3, "target": {"kcal": 350, "protein_g": 30, "carbs_g": 28, "fat_g": 11}},
        {"slot": 4, "target": {"kcal": 550, "protein_g": 41, "carbs_g": 58, "fat_g": 16}},
    ],
}


def test_nutrition_valid_plan_passes():
    r = gr.check_nutrition(
        BASE_NUTRITION, sex="male", weight_kg=82, bmr=1780, tdee=2759,
    )
    assert r.ok, r.violations


def test_nutrition_kcal_below_floor_blocks():
    bad = {**BASE_NUTRITION, "target_kcal": 1500}
    r = gr.check_nutrition(bad, sex="male", weight_kg=82, bmr=1780, tdee=2759)
    assert not r.ok
    assert any("mínimo" in v for v in r.violations)


def test_nutrition_excessive_deficit_blocks():
    # 30%+ por debajo del TDEE
    bad = {**BASE_NUTRITION, "target_kcal": 1800,
           "macros": {"protein_g": 175, "carbs_g": 120, "fat_g": 60}}
    r = gr.check_nutrition(bad, sex="male", weight_kg=82, bmr=1700, tdee=2800)
    assert any("déficit" in v for v in r.violations)


def test_nutrition_low_protein_blocks():
    bad = {**BASE_NUTRITION, "macros": {"protein_g": 90, "carbs_g": 250, "fat_g": 70}}
    r = gr.check_nutrition(bad, sex="male", weight_kg=82, bmr=1780, tdee=2759)
    assert any("proteína" in v for v in r.violations)


def test_nutrition_low_fat_blocks():
    bad = {**BASE_NUTRITION, "macros": {"protein_g": 175, "carbs_g": 300, "fat_g": 20}}
    r = gr.check_nutrition(bad, sex="male", weight_kg=82, bmr=1780, tdee=2759)
    assert any("grasa" in v for v in r.violations)


def test_nutrition_recalibration_excessive_change_blocks():
    r = gr.check_nutrition(
        BASE_NUTRITION, sex="male", weight_kg=82, bmr=1780, tdee=2759,
        is_recalibration=True, previous_target_kcal=1800,  # 2200 vs 1800 = +22%
    )
    assert any("recalibración" in v for v in r.violations)


def test_nutrition_surplus_within_limit_passes():
    plan = {
        "target_kcal": 3000,
        "macros": {"protein_g": 160, "carbs_g": 380, "fat_g": 80},
        "meals": [{"slot": 1, "target": {"kcal": 3000, "protein_g": 160, "carbs_g": 380, "fat_g": 80}}],
    }
    r = gr.check_nutrition(plan, sex="male", weight_kg=80, bmr=1800, tdee=2800)
    # +7% está dentro del 15% → sin violación de superávit
    assert not any("superávit" in v for v in r.violations)


# --------------------------------------------- opciones de comida ±5% ----

def _option(key, kcal, p, c, f):
    return {"key": key, "macros": {"kcal": kcal, "protein_g": p, "carbs_g": c, "fat_g": f}}


def test_meal_options_within_tolerance_pass():
    slots = [{"slot": 1, "options": [_option("A", 550, 44, 52, 16), _option("B", 565, 45, 53, 16)]}]
    targets = {1: {"kcal": 550, "protein_g": 44, "carbs_g": 52, "fat_g": 16}}
    r = gr.check_meal_options(slots, targets)
    assert r.ok, r.violations


def test_meal_option_out_of_tolerance_blocks():
    slots = [{"slot": 1, "options": [_option("A", 700, 44, 52, 16)]}]  # +27% kcal
    targets = {1: {"kcal": 550, "protein_g": 44, "carbs_g": 52, "fat_g": 16}}
    r = gr.check_meal_options(slots, targets)
    assert not r.ok
    assert any("slot 1" in v and "kcal" in v for v in r.violations)


def test_strict_day_meals_validates_each_dish():
    days = [{"day": "lunes", "meals": [{"slot": 1, "dish": _option("A", 900, 44, 52, 16)}]}]
    targets = {1: {"kcal": 550, "protein_g": 44, "carbs_g": 52, "fat_g": 16}}
    r = gr.check_strict_day_meals(days, targets)
    assert any("lunes" in v for v in r.violations)


# ==================================================== entrenamiento (F.4) ====

LIBRARY = {
    12: {"canonical_name": "Press banca", "muscle_primary": "pecho",
         "contraindications": ["hombro"]},
    30: {"canonical_name": "Sentadilla", "muscle_primary": "cuadriceps",
         "contraindications": ["rodilla"]},
    45: {"canonical_name": "Curl bíceps", "muscle_primary": "biceps",
         "contraindications": []},
}


def _session(name, exercises):
    return {"name": name, "exercises": exercises}


def _ex(ex_id, sets, weight=None):
    e = {"exercise_id": ex_id, "sets": sets}
    if weight is not None:
        e["start_weight_hint_kg"] = weight
    return e


def test_training_valid_passes():
    training = {"sessions": [
        _session("Día A", [_ex(12, 4), _ex(45, 3)]),
        _session("Día B", [_ex(30, 4), _ex(45, 3)]),
    ]}
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=75,
        client_contraindications=set(), exercise_lookup=LIBRARY,
    )
    assert r.ok, r.violations


def test_training_too_many_sessions_blocks():
    training = {"sessions": [_session(f"D{i}", [_ex(45, 3)]) for i in range(5)]}
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=75,
        client_contraindications=set(), exercise_lookup=LIBRARY,
    )
    assert any("sesiones" in v for v in r.violations)


def test_training_contraindicated_exercise_blocks():
    training = {"sessions": [_session("Día A", [_ex(12, 4)])]}  # press banca → hombro
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=75,
        client_contraindications={"hombro"}, exercise_lookup=LIBRARY,
    )
    assert any("contraindicado" in v for v in r.violations)


def test_training_unknown_exercise_blocks():
    training = {"sessions": [_session("Día A", [_ex(999, 4)])]}
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=75,
        client_contraindications=set(), exercise_lookup=LIBRARY,
    )
    assert any("no existe" in v for v in r.violations)


def test_training_excessive_weekly_volume_blocks():
    # 30 series de bíceps en una semana > 25
    training = {"sessions": [_session("Día A", [_ex(45, 30)])]}
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=200,
        client_contraindications=set(), exercise_lookup=LIBRARY,
    )
    assert any("series/semana" in v for v in r.violations)


def test_training_session_too_long_blocks():
    # 20 series * 3 + 10 = 70 min > 45
    training = {"sessions": [_session("Día A", [_ex(45, 20)])]}
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=45,
        client_contraindications=set(), exercise_lookup=LIBRARY,
    )
    assert any("supera el máximo" in v and "min" in v for v in r.violations)


def test_training_load_increment_capped_on_recalibration():
    training = {"sessions": [_session("Día A", [_ex(45, 3, weight=66)])]}  # +32% sobre 50
    r = gr.check_training(
        training, training_days_declared=4, session_max_min=75,
        client_contraindications=set(), exercise_lookup=LIBRARY,
        is_recalibration=True, previous_weights={45: 50},
    )
    assert any("supera el máximo" in v and "%" in v for v in r.violations)


# ---------------------------------------- filtro de biblioteca ----

def test_filter_excludes_contraindicated_and_archived():
    exercises = [
        {"id": 1, "level_min": 1, "contraindications": ["rodilla"], "equipment": ["barra"], "archived": False},
        {"id": 2, "level_min": 1, "contraindications": [], "equipment": ["mancuernas"], "archived": True},
        {"id": 3, "level_min": 1, "contraindications": [], "equipment": ["peso_corporal"], "archived": False},
    ]
    out = gr.filter_exercises_for_client(
        exercises, client_contraindications={"rodilla"}, excluded_ids=set(),
        equipment_available={"barra", "mancuernas"}, level_max=2, training_place="gym",
    )
    ids = {e["id"] for e in out}
    assert ids == {3}  # 1 contraindicado, 2 archivado, 3 peso corporal siempre vale


def test_filter_excludes_above_level_and_excluded_ids():
    exercises = [
        {"id": 1, "level_min": 3, "contraindications": [], "equipment": ["peso_corporal"], "archived": False},
        {"id": 2, "level_min": 1, "contraindications": [], "equipment": ["peso_corporal"], "archived": False},
    ]
    out = gr.filter_exercises_for_client(
        exercises, client_contraindications=set(), excluded_ids={2},
        equipment_available=set(), level_max=2, training_place="home",
    )
    assert out == []  # 1 supera nivel, 2 excluido


def test_filter_home_requires_owned_equipment():
    exercises = [
        {"id": 1, "level_min": 1, "contraindications": [], "equipment": ["maquina"], "archived": False},
        {"id": 2, "level_min": 1, "contraindications": [], "equipment": ["mancuernas"], "archived": False},
    ]
    out = gr.filter_exercises_for_client(
        exercises, client_contraindications=set(), excluded_ids=set(),
        equipment_available={"mancuernas"}, level_max=2, training_place="home",
    )
    assert {e["id"] for e in out} == {2}  # no tiene máquina en casa
