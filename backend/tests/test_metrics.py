"""Tests unitarios del servicio de métricas (Fase 3).

No requieren base de datos: aritmética pura. Verifican fórmulas contra valores
calculados a mano y comportamiento robusto ante datos incompletos.
"""

from __future__ import annotations

from datetime import date

from app.services import metrics as m


# ----------------------------------------------------------------- energía ----

def test_mifflin_st_jeor_male():
    # 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    assert m.mifflin_st_jeor("male", 80, 180, 30) == 1780.0


def test_mifflin_st_jeor_female():
    # 10*60 + 6.25*165 - 5*30 - 161 = 1320.25 → redondeado a 1 decimal
    assert m.mifflin_st_jeor("female", 60, 165, 30) == 1320.2


def test_katch_mcardle():
    # masa magra = 80*(1-0.15)=68 ; 370 + 21.6*68 = 370 + 1468.8 = 1838.8
    assert m.katch_mcardle(80, 15) == 1838.8


def test_bmr_uses_katch_when_bodyfat_present():
    assert m.bmr("male", 80, 180, 30, body_fat_pct=15) == m.katch_mcardle(80, 15)


def test_bmr_falls_back_to_mifflin_without_bodyfat():
    assert m.bmr("male", 80, 180, 30) == m.mifflin_st_jeor("male", 80, 180, 30)


def test_activity_factor_mapping():
    assert m.activity_factor_for_days(1) == 1.2
    assert m.activity_factor_for_days(2) == 1.375
    assert m.activity_factor_for_days(4) == 1.55
    assert m.activity_factor_for_days(5) == 1.725
    assert m.activity_factor_for_days(6) == 1.9


def test_energy_targets_fat_loss_is_deficit():
    et = m.energy_targets("male", 80, 180, 30, "fat_loss", training_days=4)
    assert et.adjustment_pct < 0
    assert et.target_kcal < et.tdee
    assert et.method == "mifflin"


def test_energy_targets_muscle_gain_is_surplus():
    et = m.energy_targets("male", 70, 175, 25, "muscle_gain", training_days=5)
    assert et.adjustment_pct > 0
    assert et.target_kcal > et.tdee


def test_energy_targets_recomp_near_maintenance():
    # Hardening §3: recomposición = rango −5%..0% (no mantenimiento exacto). Con
    # el punto medio son −2,5% sobre el TDEE, salvo que choque con el suelo.
    et = m.energy_targets("female", 60, 165, 28, "recomp", training_days=3)
    assert -0.05 <= et.adjustment_pct <= 0.0
    assert et.target_kcal <= et.tdee
    assert et.bracket == "recomp/any"


def test_age_from_birth():
    assert m.age_from_birth(date(1990, 6, 15), today=date(2026, 6, 14)) == 35
    assert m.age_from_birth(date(1990, 6, 15), today=date(2026, 6, 15)) == 36


# ------------------------------------------------------------------- e1RM ----

def test_epley_single_rep_is_weight():
    assert m.epley_1rm(100, 1) == 100.0


def test_epley_formula():
    # 100 * (1 + 8/30) = 100 * 1.2666... = 126.67
    assert m.epley_1rm(100, 8) == 126.67


def test_epley_zero_reps():
    assert m.epley_1rm(100, 0) == 0.0


# ------------------------------------------------- tendencia de peso ----

def test_weight_trend_basic():
    pts = [
        (date(2026, 1, 1), 82.0),
        (date(2026, 1, 8), 81.4),
        (date(2026, 1, 15), 80.8),
    ]
    t = m.weight_trend(pts)
    assert t.start_kg == 82.0 and t.end_kg == 80.8
    assert t.delta_kg == -1.2
    assert t.n_measurements == 3
    # ~0.6 kg/semana de bajada
    assert t.weekly_rate_kg is not None and t.weekly_rate_kg < 0


def test_weight_trend_single_point():
    t = m.weight_trend([(date(2026, 1, 1), 80.0)])
    assert t.weekly_rate_kg == 0.0 and t.n_measurements == 1


def test_weight_trend_empty():
    t = m.weight_trend([])
    assert t.n_measurements == 0 and t.start_kg is None


# --------------------------------------------------------- adherencia ----

def test_adherence_summary_full():
    logs = [
        {"diet_adherence": "yes", "sleep_hours": 8, "energy_1_5": 4, "mood_1_5": 4, "fatigue_1_5": 2},
        {"diet_adherence": "partial", "sleep_hours": 7, "energy_1_5": 3, "mood_1_5": 3, "fatigue_1_5": 3},
        {"diet_adherence": "yes", "sleep_hours": 7.5, "energy_1_5": 5, "mood_1_5": 4, "fatigue_1_5": 2},
    ]
    s = m.adherence_summary(logs, period_days=14)
    assert s.days_logged == 3 and s.period_days == 14
    assert s.log_ratio == round(3 / 14, 3)
    assert s.diet_yes == 2 and s.diet_partial == 1 and s.diet_no == 0
    # (2 + 0.5*1) / 3 = 0.833
    assert s.diet_adherence_ratio == 0.833
    assert s.mean_sleep_h == round((8 + 7 + 7.5) / 3, 2)


def test_adherence_tolerates_missing_fields():
    s = m.adherence_summary([{"diet_adherence": "no"}, {}], period_days=10)
    assert s.diet_no == 1 and s.mean_sleep_h is None and s.mean_energy is None


# ----------------------------------------------- progreso por ejercicio ----

def test_exercise_e1rm_progress_picks_best():
    sets = [
        {"exercise_id": 12, "weight_kg": 60, "reps": 8, "daily_log_id": 1},
        {"exercise_id": 12, "weight_kg": 65, "reps": 6, "daily_log_id": 2},  # mejor e1RM
        {"exercise_id": 30, "weight_kg": 40, "reps": 10, "daily_log_id": 1},
    ]
    prog = m.exercise_e1rm_progress(sets)
    by_id = {p.exercise_id: p for p in prog}
    assert by_id[12].best_set == (65, 6)
    assert by_id[12].best_e1rm_kg == m.epley_1rm(65, 6)
    assert by_id[12].sessions == 2


def test_exercise_progress_ignores_incomplete_sets():
    sets = [{"exercise_id": 1, "weight_kg": None, "reps": 5},
            {"exercise_id": 1, "weight_kg": 50, "reps": None}]
    assert m.exercise_e1rm_progress(sets) == []


# ------------------------------------------- estadísticas de opciones ----

def test_option_choice_stats():
    chosen = [
        {"1": "A", "2": "C"},
        {"1": "A", "2": "B"},
        {"1": "B", "2": "C"},
    ]
    stats = m.option_choice_stats(chosen)
    assert stats[1]["A"] == 2 and stats[1]["B"] == 1
    assert stats[2]["C"] == 2 and stats[2]["B"] == 1


def test_option_choice_stats_tolerates_empty():
    assert m.option_choice_stats([None, {}]) == {}


# ------------------------------------------------- ensamblado JSON ----

def test_period_metrics_to_json_roundtrip():
    pm = m.PeriodMetrics(
        weight=m.weight_trend([(date(2026, 1, 1), 80.0), (date(2026, 1, 14), 79.0)]),
        adherence=m.adherence_summary([{"diet_adherence": "yes"}], period_days=14),
        exercise_progress=m.exercise_e1rm_progress(
            [{"exercise_id": 1, "weight_kg": 100, "reps": 5, "daily_log_id": 1}]
        ),
        option_stats=m.option_choice_stats([{"1": "A"}]),
    )
    js = pm.to_json()
    assert js["weight"]["delta_kg"] == -1.0
    assert js["adherence"]["diet_yes"] == 1
    assert js["exercise_progress"][0]["best_e1rm_kg"] == m.epley_1rm(100, 5)
    assert js["option_stats"]["1"]["A"] == 1
