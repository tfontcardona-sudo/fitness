"""Tests de coherencia dieta↔entreno (hardening §6)."""
from __future__ import annotations

from app.services.diet_training_coherence import check_diet_training_coherence


def _nut(target=2000, carbs=200, times=("08:00", "14:00", "21:00")):
    return {
        "target_kcal": target,
        "macros": {"protein_g": 150, "carbs_g": carbs, "fat_g": 60},
        "meals": [{"slot": i + 1, "time": t, "target": {}} for i, t in enumerate(times)],
    }


def _training(sets_pecho=20, sessions=4):
    return {"sessions": [
        {"exercises": [{"exercise_id": 1, "muscle_primary": "pecho", "sets": sets_pecho // sessions}]}
        for _ in range(sessions)
    ]}


def test_sobrecarga_con_deficit_profundo_avisa():
    r = check_diet_training_coherence(
        _nut(target=1900), _training(sets_pecho=24), tdee=2700)  # déficit ~30%
    assert any("sobrecarga" in w or "MANTENER" in w for w in r.warnings)


def test_deficit_suave_con_sobrecarga_no_avisa_por_ese_motivo():
    r = check_diet_training_coherence(
        _nut(target=2600), _training(sets_pecho=24), tdee=2700)  # déficit ~4%
    assert not any("sobrecarga" in w for w in r.warnings)


def test_sin_comida_peri_entreno_avisa():
    r = check_diet_training_coherence(
        _nut(times=("08:00", "13:00", "21:00")), _training(),
        tdee=2500, training_time="17:30")
    assert any("hora de entreno" in w for w in r.warnings)


def test_comida_cerca_del_entreno_no_avisa():
    r = check_diet_training_coherence(
        _nut(times=("08:00", "16:30", "21:00")), _training(),
        tdee=2500, training_time="17:30")
    assert not any("hora de entreno" in w for w in r.warnings)


def test_hidratos_bajos_con_muchos_dias_sugiere_ciclado():
    r = check_diet_training_coherence(
        _nut(target=2400, carbs=180), _training(sessions=5), tdee=2500)  # 180*4/2400=30%
    assert any("ciclado" in w for w in r.warnings)


def test_ultima_comida_muy_tardia_avisa():
    r = check_diet_training_coherence(
        _nut(times=("09:00", "15:00", "23:45")), None, sleep_hours=7)
    assert any("tardía" in w or "descanso" in w for w in r.warnings)


def test_lookup_por_exercise_id():
    training = {"sessions": [{"exercises": [{"exercise_id": 12, "sets": 24}]}]}
    lookup = {12: {"muscle_primary": "espalda"}}
    r = check_diet_training_coherence(
        _nut(target=1900), training, tdee=2700, exercise_lookup=lookup)
    assert any("espalda" in w for w in r.warnings)
