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


def test_avisa_de_las_tomas_que_caen_dentro_de_la_jornada():
    """La comprobación de horarios estaba escrita a medias: el bucle recorría
    las tomas y no hacía NADA (solo un comentario), así que nunca avisó. Lo
    que importa es cuántas comidas tiene que llevarse preparadas al trabajo."""
    from app.services.diet_training_coherence import check_diet_training_coherence

    nut = {
        "target_kcal": 2200, "macros": {"protein_g": 165, "carbs_g": 210, "fat_g": 68},
        "meals": [
            {"slot": 1, "name": "Desayuno", "time": "07:00"},
            {"slot": 2, "name": "Media mañana", "time": "11:00"},
            {"slot": 3, "name": "Comida", "time": "14:30"},
            {"slot": 4, "name": "Cena", "time": "21:00"},
        ],
    }
    r = check_diet_training_coherence(nut, None, tdee=2600, workday=("09:00", "18:00"))
    avisos = " ".join(r.warnings)
    assert "dentro de su jornada" in avisos
    assert "Media mañana" in avisos and "Comida" in avisos

    # Turno de NOCHE (sale al día siguiente): también se detecta.
    r2 = check_diet_training_coherence(nut, None, tdee=2600, workday=("22:00", "06:00"))
    assert "dentro de su jornada" not in " ".join(r2.warnings)

    # Sin jornada declarada no se inventa nada.
    r3 = check_diet_training_coherence(nut, None, tdee=2600)
    assert "dentro de su jornada" not in " ".join(r3.warnings)


def test_los_horarios_se_leen_de_las_notas_de_la_anamnesis():
    """Las comprobaciones de jornada, hora de entreno y sueño existían con sus
    tests… y NADIE les pasaba los datos en producción: se quedaban muertas. La
    anamnesis los recoge en texto con su tema delante."""
    from app.services.diet_training_coherence import horarios_de_las_notas

    notas = (
        "- Motivo: quiere llegar bien al verano\n"
        "- Trabajo: oficina de 9:00 a 18:00, come fuera\n"
        "- Horario de entreno: sobre las 20:30, después del trabajo\n"
        "- Sueño: 6,5 h y se despierta cansado\n"
    )
    out = horarios_de_las_notas(notas)
    assert out["workday"] == ("09:00", "18:00")
    assert out["training_time"] == "20:30"
    assert out["sleep_hours"] == 6.5

    # Ante la duda, NADA (mejor sin aviso que con un aviso inventado).
    assert horarios_de_las_notas("- Trabajo: turnos rotativos") == {}
    assert horarios_de_las_notas(None) == {}
