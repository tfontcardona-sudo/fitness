"""Tests del servicio de IA (Fase 3) con un cliente MOCK.

No gastan API real: se sustituye `_raw_call` por respuestas controladas. Se
verifica el parseo robusto, el retry con error inyectado, y el pipeline
completo de generación con guardrails (núcleo → comidas → educativo).
"""

from __future__ import annotations

import json

import pytest

from app.schemas.ai import PlanCoreOutput
from app.services.ai.client import AIClient, AIGenerationError
from app.services.ai.generator import (
    ClientContext,
    PlanGenerationError,
    generate_monthly_plan,
)


# ----------------------------------------------------- parseo y retry ----

class ScriptedClient(AIClient):
    """AIClient cuyo _raw_call devuelve respuestas de una lista, en orden."""

    def __init__(self, responses: list[str]):
        super().__init__(api_key="test")
        self._responses = list(responses)
        self.calls: list[dict] = []

    def _raw_call(self, *, model, system, user):
        self.calls.append({"model": model, "system": system, "user": user})
        return self._responses.pop(0)


def test_extract_json_from_markdown_fence():
    from app.services.ai.client import _extract_json

    raw = 'Claro, aquí tienes:\n```json\n{"a": 1}\n```\nEspero que sirva.'
    assert json.loads(_extract_json(raw)) == {"a": 1}


def test_extract_json_from_braces():
    from app.services.ai.client import _extract_json

    raw = 'preámbulo {"a": 1, "b": 2} epílogo'
    assert json.loads(_extract_json(raw)) == {"a": 1, "b": 2}


def _valid_core_json() -> str:
    return json.dumps({
        "nutrition": {
            "tdee_kcal": 2759, "target_kcal": 2200,
            "rationale": "Déficit 20% sobre TDEE para fat_loss",
            "macros": {"protein_g": 175, "carbs_g": 210, "fat_g": 65},
            "meals": [
                {"slot": 1, "name": "Desayuno", "time": "08:00",
                 "target": {"kcal": 550, "protein_g": 44, "carbs_g": 52, "fat_g": 16}},
                {"slot": 2, "name": "Comida", "time": "14:00",
                 "target": {"kcal": 750, "protein_g": 60, "carbs_g": 72, "fat_g": 22}},
                {"slot": 3, "name": "Merienda", "time": "18:00",
                 "target": {"kcal": 350, "protein_g": 30, "carbs_g": 28, "fat_g": 11}},
                {"slot": 4, "name": "Cena", "time": "21:30",
                 "target": {"kcal": 550, "protein_g": 41, "carbs_g": 58, "fat_g": 16}},
            ],
            "supplements": [{"name": "Creatina", "dose": "5 g", "timing": "diario",
                             "evidence_note": "Evidencia sólida"}],
            "flexibility_rules": ["Si fallas una comida, retoma en la siguiente"],
            "refeed_or_break": None,
        },
        "training": {
            "split_name": "Upper/Lower 4 días", "split_rationale": "4 días, intermedio",
            "weekly_progression": [
                {"week": 1, "intent": "Base", "load_pct": 100, "rir_target": "2-3", "volume_note": "ref"},
                {"week": 2, "intent": "Prog", "load_pct": 102.5, "rir_target": "2", "volume_note": "+1"},
                {"week": 3, "intent": "Pico", "load_pct": 105, "rir_target": "1-2", "volume_note": "ok"},
                {"week": 4, "intent": "Deload", "load_pct": 90, "rir_target": "3-4", "volume_note": "-45%"},
            ],
            "sessions": [
                {"day": "Lunes", "name": "Upper A", "warmup": "5' movilidad",
                 "exercises": [
                     {"exercise_id": 12, "sets": 4, "rep_range": "6-8", "rir": "2",
                      "tempo": "2-0-1", "rest_sec": 150, "start_weight_hint_kg": 60,
                      "progression_rule": "doble progresión", "technique_cue": "Escápulas",
                      "biomech_cue": "Antebrazo vertical"}],
                 "cooldown": "Estiramiento"},
            ],
            "cardio": {"daily_steps": 9000,
                       "sessions": [{"type": "liss", "minutes": 30, "times_per_week": 2, "notes": "Z2"}]},
            "deload_instructions": "Semana 4: mitad de series",
        },
    })


def test_generate_json_retries_with_injected_error():
    # Primera respuesta inválida (falta training), segunda válida.
    bad = json.dumps({"nutrition": {"tdee_kcal": 2000}})
    client = ScriptedClient([bad, _valid_core_json()])
    result = client.generate_json(
        model="m", system="s", user="genera el plan", schema=PlanCoreOutput
    )
    assert isinstance(result, PlanCoreOutput)
    assert len(client.calls) == 2
    # El segundo prompt incluye la corrección inyectada
    assert "CORRECCIÓN REQUERIDA" in client.calls[1]["user"]


def test_generate_json_raises_after_second_failure():
    client = ScriptedClient(['{"malo": 1}', '{"sigue": "mal"}'])
    with pytest.raises(AIGenerationError):
        client.generate_json(model="m", system="s", user="x", schema=PlanCoreOutput)


# ------------------------------------------------- pipeline completo ----

def _ctx() -> ClientContext:
    return ClientContext(
        sex="male", age=30, height_cm=180, weight_kg=82, goal_type="fat_loss",
        level="intermediate", training_days=4, session_max_min=75,
        training_place="gym", diet_mode="flexible_7", meals_per_day=4,
        meal_schedule=[{"slot": i, "name": n, "time": t} for i, n, t in
                       [(1, "Desayuno", "08:00"), (2, "Comida", "14:00"),
                        (3, "Merienda", "18:00"), (4, "Cena", "21:30")]],
        food_allergies=["lactosa"], food_dislikes=["brócoli"], food_likes=["pollo"],
        contraindications=set(), body_fat_pct=None,
        bmr=1780, tdee=2759, target_kcal=2200, energy_method="mifflin",
        exercise_library=[
            {"id": 12, "canonical_name": "Press banca", "movement_pattern": "horizontal_push",
             "muscle_primary": "pecho", "contraindications": [], "equipment": ["barra"],
             "level_min": 2, "archived": False},
        ],
    )


def _flexible_meals_json() -> str:
    targets = {
        1: (550, 44, 52, 16), 2: (750, 60, 72, 22),
        3: (350, 30, 28, 11), 4: (550, 41, 58, 16),
    }
    slots = []
    for slot, (kcal, p, c, f) in targets.items():
        options = []
        for key in "ABCDEFG":
            options.append({
                "key": key, "title": f"Opción {key} slot {slot}",
                "ingredients": [{"food": "Pollo", "grams": 150, "household": "1 pechuga"}],
                "prep": "Cocinar y servir", "prep_minutes": 8,
                "macros": {"kcal": kcal, "protein_g": p, "carbs_g": c, "fat_g": f},
                "tags": ["rápido"],
            })
        slots.append({"slot": slot, "options": options})
    return json.dumps({"mode": "flexible_7", "slots": slots})


def _education_json() -> str:
    return json.dumps({
        "pills": [
            {"topic": "Sobrecarga progresiva", "for_client": "Subir poco a poco."},
            {"topic": "RIR", "for_client": "Reps en reserva."},
            {"topic": "Proteína", "for_client": "Reparto diario."},
        ],
        "biomech_by_pattern": [
            {"pattern": "empuje_horizontal", "cues": ["escápulas", "muñeca neutra"],
             "why": "Estabilidad del hombro"},
        ],
        "faq": [{"q": "¿Si fallo una comida?", "a": "Retomar sin compensar."}],
    })


def test_full_pipeline_generates_plan():
    client = ScriptedClient([_valid_core_json(), _flexible_meals_json(), _education_json()])
    plan = generate_monthly_plan(_ctx(), client)
    assert len(client.calls) == 3
    nutrition_json, training_json, education_json, flags = plan.to_persistable()
    assert nutrition_json["target_kcal"] == 2200
    assert "meal_bank" in nutrition_json
    assert training_json["split_name"].startswith("Upper")
    assert len(education_json["pills"]) == 3
    # plan limpio: sin violaciones de guardrails
    assert not any(f.startswith("violation:") for f in flags)


def test_pipeline_blocks_core_violating_guardrails():
    # Núcleo con kcal por debajo del suelo → guardrail de nutrición bloquea
    bad_core = json.loads(_valid_core_json())
    bad_core["nutrition"]["target_kcal"] = 1200
    bad_core["nutrition"]["macros"] = {"protein_g": 175, "carbs_g": 60, "fat_g": 45}
    client = ScriptedClient([json.dumps(bad_core)])
    with pytest.raises(PlanGenerationError) as exc:
        generate_monthly_plan(_ctx(), client)
    assert "guardrails" in str(exc.value)


def test_pipeline_flags_out_of_tolerance_meal_options():
    # Una opción del slot 1 desviada >5% → warning recuperable (no bloquea)
    meals = json.loads(_flexible_meals_json())
    meals["slots"][0]["options"][0]["macros"]["kcal"] = 900  # muy alto
    client = ScriptedClient([_valid_core_json(), json.dumps(meals), _education_json()])
    plan = generate_monthly_plan(_ctx(), client)
    flags = plan.guardrail_flags
    assert any("slot 1" in f for f in flags)
