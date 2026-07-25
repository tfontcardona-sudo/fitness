"""Tests del gate de seguridad — lista roja y semáforo (hardening §12)."""
from __future__ import annotations

from app.services.safety_gate import bmi, red_flags, traffic_light


def _codes(flags):
    return {f.code for f in flags}


def test_cliente_sano_sin_banderas():
    prof = {"sex": "male", "age": 30, "height_cm": 178, "weight_kg": 80,
            "medical_notes": "Ninguna", "medication_notes": ""}
    assert red_flags(prof) == []


def test_menor_y_mayor_de_edad():
    assert "menor" in _codes(red_flags({"age": 16, "height_cm": 170, "weight_kg": 60}))
    assert "mayor_65" in _codes(red_flags({"age": 70, "height_cm": 170, "weight_kg": 70}))


def test_bajo_peso_imc():
    # 45 kg / 1,70 m → IMC 15,6 < 18,5
    flags = red_flags({"age": 25, "height_cm": 170, "weight_kg": 45})
    assert "bajo_peso" in _codes(flags)
    assert bmi(45, 170) == 15.6


def test_embarazo_lactancia():
    assert "embarazo" in _codes(red_flags({"age": 30, "lifestyle_notes": "Estoy embarazada de 4 meses"}))
    assert "embarazo" in _codes(red_flags({"age": 32, "medical_notes": "En lactancia"}))


def test_tca_por_texto_libre():
    prof = {"age": 22, "lifestyle_notes": "A veces me provoco el vómito y uso laxante para adelgazar"}
    assert "tca" in _codes(red_flags(prof))


def test_patologias_y_medicacion_acento_insensible():
    prof = {"age": 40, "medical_notes": "Diabético tipo 2 e hipotiroidismo",
            "medication_notes": "Levotiroxina y Sintrom"}
    codes = _codes(red_flags(prof))
    assert {"diabetes", "tiroides", "med_levotiroxina", "med_anticoagulante"} <= codes


def test_glp1_y_bariatrica():
    prof = {"age": 45, "medication_notes": "Ozempic semanal",
            "medical_notes": "Bypass gástrico hace 2 años"}
    codes = _codes(red_flags(prof))
    assert "med_glp1" in codes and "bariatrica" in codes


def test_contradicciones_sin_resolver():
    flags = red_flags({"age": 30}, unresolved_contradictions=["quiere perder grasa y ganar 5 kg"])
    assert "contradiccion" in _codes(flags)


# ---- Semáforo ----

def test_rojo_manda_sobre_todo():
    from app.services.safety_gate import RedFlag
    color = traffic_light(has_deterministic_violation=False,
                          red=[RedFlag("diabetes", "Diabetes", "diabetico")],
                          icp=95, minor_findings=0)
    assert color == "rojo"


def test_verde_exige_limpieza_e_icp_alto():
    assert traffic_light(has_deterministic_violation=False, red=[], icp=88, minor_findings=0) == "verde"
    # ICP intermedio → ámbar
    assert traffic_light(has_deterministic_violation=False, red=[], icp=70, minor_findings=0) == "ambar"
    # hallazgos menores → ámbar aunque el ICP sea alto
    assert traffic_light(has_deterministic_violation=False, red=[], icp=90, minor_findings=2) == "ambar"


def test_violacion_determinista_es_rojo():
    assert traffic_light(has_deterministic_violation=True, red=[], icp=99, minor_findings=0) == "rojo"
