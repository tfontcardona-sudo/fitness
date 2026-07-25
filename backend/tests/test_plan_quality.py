"""Tests de los mecanismos de calidad del plan (hardening §10)."""
from __future__ import annotations

import pytest

from app.services.plan_quality import (
    Candidate,
    adherence_stress_test,
    common_sense_checklist,
    is_canary,
    pick_best_of_n,
    simulate_trajectory,
)


def test_simulacion_deficit_baja_peso():
    r = simulate_trajectory(weight_kg=90, tdee=2700, target_kcal=2160, weeks=12)  # -20%
    assert r.final_weight_kg < 90
    assert len(r.points) == 12
    assert r.total_change_kg < 0


def test_simulacion_alcanza_objetivo_en_plazo():
    # -540 kcal/día ≈ -0,49 kg/sem ≈ -5,9 kg en 12 sem. Objetivo -6 kg → ok.
    r = simulate_trajectory(weight_kg=90, tdee=2700, target_kcal=2160, weeks=12,
                            goal_weight_kg=84)
    assert r.verdict == "ok" and r.reaches_goal


def test_simulacion_demasiado_lenta_no_alcanza():
    r = simulate_trajectory(weight_kg=90, tdee=2700, target_kcal=2600, weeks=12,
                            goal_weight_kg=80)  # déficit pequeño para -10 kg
    assert r.verdict == "lento" and not r.reaches_goal


def test_simulacion_demasiado_rapida():
    r = simulate_trajectory(weight_kg=90, tdee=2700, target_kcal=1800, weeks=12,
                            goal_weight_kg=88)  # déficit grande para solo -2 kg
    assert r.verdict == "rapido" and not r.reaches_goal


def test_estres_de_adherencia():
    res = adherence_stress_test(weight_kg=90, tdee=2700, target_kcal=2160, goal_type="fat_loss")
    names = {r.scenario for r in res}
    assert "descontrol_finde" in names
    # con adherencia perfecta progresa; con descontrol puede no progresar
    perfect = next(r for r in res if r.scenario == "adherencia_perfecta")
    assert perfect.still_progresses


def test_best_of_n_penaliza_fragilidad():
    a = Candidate("robusto", icp=82, fragility=0.0)
    b = Candidate("brillante_pero_fragil", icp=90, fragility=0.6)
    best, why = pick_best_of_n([a, b])
    assert best.label == "robusto"   # 82 vs 90-15=75
    assert "robustez" in why


def test_best_of_n_sin_candidatos():
    with pytest.raises(ValueError):
        pick_best_of_n([])


def test_checklist_caza_comida_gigante_y_sesion_larga():
    nut = {"meals": [{"slot": 1, "target": {"kcal": 1600}}]}
    tr = {"sessions": [{"name": "Full", "exercises": [{"sets": 40}]}]}
    issues = common_sense_checklist(nut, tr, session_max_min=60)
    assert any("demasiado grande" in i for i in issues)
    assert any("no cabe" in i for i in issues)


def test_checklist_plan_sano_sin_issues():
    nut = {"meals": [{"slot": 1, "target": {"kcal": 600}}, {"slot": 2, "target": {"kcal": 700}}]}
    tr = {"sessions": [{"name": "Upper", "exercises": [{"sets": 16}]}]}
    assert common_sense_checklist(nut, tr, session_max_min=75) == []


def test_canario():
    assert is_canary(0) and is_canary(4)
    assert not is_canary(5) and not is_canary(20)
