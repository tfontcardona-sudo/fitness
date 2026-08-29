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

    def _raw_call(self, *, model, system, user, temperature=None, **_kw):
        self.calls.append({"model": model, "system": system, "user": user,
                           "temperature": temperature})
        return self._responses.pop(0)


def test_revisor_usa_temperatura_0():
    # §14: cada revisor del panel juzga de forma determinista (temperatura 0).
    from app.services.review_panel import REVIEWER_ROLES, make_ai_reviewer

    resp = json.dumps({"veredicto": "aprobado", "puntuacion_rubrica": 90, "hallazgos": []})
    sc = ScriptedClient([resp])
    reviewer = make_ai_reviewer(sc, plan_text="PLAN", anamnesis_text="ANAM")
    reviewer(REVIEWER_ROLES[0])
    assert sc.calls[0]["temperature"] == 0


def test_generacion_no_fija_temperatura():
    # La generación del plan conserva la temperatura por defecto del modelo
    # (variedad en las opciones de comida); solo extracción/revisión van a 0.
    sc = ScriptedClient([_valid_core_json(), _flexible_meals_json(), _education_json()])
    generate_monthly_plan(_ctx(), sc, include_training=True)
    assert all(c["temperature"] is None for c in sc.calls)


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
            # Núcleo COHERENTE (kcal ≡ macros 4/4/9 ≡ suma de comidas): así el
            # pipeline no tiene que recuadrar nada y el banco scripted encaja con
            # los objetivos por slot. La corrección de núcleos descuadrados se
            # prueba en test_nutrition_coherence.py.
            "tdee_kcal": 2759, "target_kcal": 2125,
            "rationale": "Déficit 20% sobre TDEE para fat_loss",
            "macros": {"protein_g": 175, "carbs_g": 210, "fat_g": 65},  # =2125
            "meals": [
                {"slot": 1, "name": "Desayuno", "time": "08:00",
                 "target": {"kcal": 528, "protein_g": 44, "carbs_g": 52, "fat_g": 16}},
                {"slot": 2, "name": "Comida", "time": "14:00",
                 "target": {"kcal": 726, "protein_g": 60, "carbs_g": 72, "fat_g": 22}},
                {"slot": 3, "name": "Merienda", "time": "18:00",
                 "target": {"kcal": 331, "protein_g": 30, "carbs_g": 28, "fat_g": 11}},
                {"slot": 4, "name": "Cena", "time": "21:30",
                 "target": {"kcal": 540, "protein_g": 41, "carbs_g": 58, "fat_g": 16}},
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
    # kcal = kcal_of(macros) de cada slot, iguales a los objetivos del núcleo
    # coherente de _valid_core_json (así el banco encaja dentro del ±5%).
    targets = {
        1: (528, 44, 52, 16), 2: (726, 60, 72, 22),
        3: (331, 30, 28, 11), 4: (540, 41, 58, 16),
    }
    slots = []
    for slot, (kcal, p, c, f) in targets.items():
        options = []
        for key in "ABC":  # el esquema exige 1-4 opciones por slot (objetivo 3)
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
    # Coherencia garantizada por reconcile_nutrition: target_kcal ≡ suma de macros
    # (4/4/9) ≡ suma de los objetivos por comida. Es la invariante que evita que un
    # apartado diga X kcal y otro diga otro número.
    m = nutrition_json["macros"]
    assert nutrition_json["target_kcal"] == round(m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9)
    meals = nutrition_json["meals"]
    assert sum(x["target"]["kcal"] for x in meals) == nutrition_json["target_kcal"]
    for axis in ("protein_g", "carbs_g", "fat_g"):
        assert sum(x["target"][axis] for x in meals) == m[axis]
    assert "meal_bank" in nutrition_json
    assert training_json["split_name"].startswith("Upper")
    assert len(education_json["pills"]) == 3
    # plan limpio: sin violaciones de guardrails
    assert not any(f.startswith("violation:") for f in flags)


def _nutrition_only_core_json() -> str:
    core = json.loads(_valid_core_json())
    return json.dumps({"nutrition": core["nutrition"]})


def _food_catalog() -> list[dict]:
    return [
        {"id": 1, "canonical_name": "Pechuga de pollo", "aliases": [], "kcal": 120,
         "protein_g": 22.5, "carbs_g": 0, "fat_g": 2.6, "allergens": [], "tags": [],
         "unit_grams": None, "min_grams": 80, "max_grams": 300},
        {"id": 2, "canonical_name": "Arroz blanco", "aliases": [], "kcal": 354,
         "protein_g": 7, "carbs_g": 78, "fat_g": 1, "allergens": [], "tags": [],
         "unit_grams": None, "min_grams": 40, "max_grams": 200},
    ]


def _flexible_meals_with_ids() -> str:
    # Cada slot: 1 opción con dos ingredientes del catálogo (food_id 1 y 2) y gramos
    # ABSURDOS (999) que el solver debe corregir.
    targets = {1: (528, 44, 52, 16), 2: (726, 60, 72, 22),
               3: (331, 30, 28, 11), 4: (540, 41, 58, 16)}
    slots = []
    for slot, (kcal, p, c, f) in targets.items():
        slots.append({"slot": slot, "options": [{
            "key": "A", "title": f"Pollo con arroz slot {slot}",
            "ingredients": [
                {"food": "Pollo", "grams": 999, "household": "x", "food_id": 1},
                {"food": "Arroz", "grams": 999, "household": "x", "food_id": 2},
            ],
            "prep": "Cocer", "prep_minutes": 10,
            "macros": {"kcal": kcal, "protein_g": p, "carbs_g": c, "fat_g": f},
            "tags": [],
        }]})
    return json.dumps({"mode": "flexible_7", "slots": slots})


def test_solver_fija_gramos_en_generacion_con_catalogo():
    # §2: con catálogo, el solver reemplaza los gramos absurdos (999) por realistas.
    client = ScriptedClient([_nutrition_only_core_json(), _flexible_meals_with_ids()])
    plan = generate_monthly_plan(_ctx(), client, include_training=False,
                                 food_catalog=_food_catalog())
    nutrition_json, _, _, flags = plan.to_persistable()
    assert any(fl.startswith("solver:") for fl in flags)
    for slot in nutrition_json["meal_bank"]["slots"]:
        for opt in slot["options"]:
            for ing in opt["ingredients"]:
                assert 0 < ing["grams"] < 500  # ya no hay 999
    # El catálogo aparece en el prompt de comidas (2ª llamada).
    assert "CATÁLOGO DE ALIMENTOS" in client.calls[1]["user"]


def test_sin_catalogo_no_snapea_backward_compat():
    # Sin catálogo, la generación conserva EXACTAMENTE el comportamiento previo.
    client = ScriptedClient([_nutrition_only_core_json(), _flexible_meals_json()])
    plan = generate_monthly_plan(_ctx(), client, include_training=False)
    _, _, _, flags = plan.to_persistable()
    assert not any(fl.startswith("solver:") for fl in flags)
    assert "CATÁLOGO DE ALIMENTOS" not in client.calls[1]["user"]


def test_nutrition_only_pipeline_skips_training():
    # Paquete Start: núcleo de nutrición + comidas, SIN entreno ni educativo.
    client = ScriptedClient([_nutrition_only_core_json(), _flexible_meals_json()])
    plan = generate_monthly_plan(_ctx(), client, include_training=False)
    assert len(client.calls) == 2  # 2 llamadas, no 3
    nutrition_json, training_json, education_json, flags = plan.to_persistable()
    # Coherencia garantizada: target_kcal ≡ suma de macros (4/4/9) ≡ suma de comidas.
    m = nutrition_json["macros"]
    assert nutrition_json["target_kcal"] == round(m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9)
    assert sum(x["target"]["kcal"] for x in nutrition_json["meals"]) == nutrition_json["target_kcal"]
    assert "meal_bank" in nutrition_json
    assert training_json is None
    assert education_json is None
    assert not any(f.startswith("violation:") for f in flags)


def test_feedback_nutrition_only_prompt_excludes_training():
    # Paquete Start: el system del feedback prohíbe mencionar entreno.
    from app.services.ai.feedback import generate_feedback_analysis

    resp = json.dumps({
        "natural_analysis": "Buen ritmo de bajada.", "changes_bullets": [],
        "plan_adjustments": [], "answers": None, "next_objectives": [],
        "closing_message": "Sigue así.",
    })
    client = ScriptedClient([resp])
    generate_feedback_analysis({"objetivo": "fat_loss"}, client, nutrition_only=True)
    system = client.calls[0]["system"]
    assert "SOLO NUTRICIÓN" in system
    assert "NO menciones entrenamiento" in system

    # Full/Pro: el system NO lleva ese añadido.
    client2 = ScriptedClient([resp])
    generate_feedback_analysis({"objetivo": "fat_loss"}, client2, nutrition_only=False)
    assert "SOLO NUTRICIÓN" not in client2.calls[0]["system"]


def test_pipeline_blocks_core_violating_guardrails():
    # Núcleo con kcal por debajo del suelo → guardrail de nutrición bloquea.
    # Se scriptea el núcleo malo DOS veces: el pipeline reintenta una vez con
    # los vetos inyectados y, si el reintento también viola, veta de verdad.
    bad_core = json.loads(_valid_core_json())
    bad_core["nutrition"]["target_kcal"] = 1200
    bad_core["nutrition"]["macros"] = {"protein_g": 175, "carbs_g": 60, "fat_g": 45}
    client = ScriptedClient([json.dumps(bad_core), json.dumps(bad_core)])
    with pytest.raises(PlanGenerationError) as exc:
        generate_monthly_plan(_ctx(), client)
    assert "guardrails" in str(exc.value)
    # El reintento existió y llevaba los vetos inyectados en el user prompt.
    assert len(client.calls) == 2
    assert "violó estas reglas" in client.calls[1]["user"]


def test_pipeline_reintenta_y_corrige_el_nucleo_vetado():
    # Primer núcleo vetado + segundo válido → el plan SALE (antes moría con
    # PlanGenerationError a la primera) y queda constancia en los flags.
    bad_core = json.loads(_valid_core_json())
    bad_core["nutrition"]["target_kcal"] = 1200
    bad_core["nutrition"]["macros"] = {"protein_g": 175, "carbs_g": 60, "fat_g": 45}
    client = ScriptedClient([
        json.dumps(bad_core), _valid_core_json(),
        _flexible_meals_json(), _education_json(),
    ])
    plan = generate_monthly_plan(_ctx(), client)
    assert plan.nutrition is not None
    assert any("reintentado tras violar guardrails" in f for f in plan.guardrail_flags)


def test_pipeline_flags_out_of_tolerance_meal_options():
    # Una opción del slot 1 desviada >5% → warning recuperable (no bloquea)
    meals = json.loads(_flexible_meals_json())
    meals["slots"][0]["options"][0]["macros"]["kcal"] = 900  # muy alto
    client = ScriptedClient([_valid_core_json(), json.dumps(meals), _education_json()])
    plan = generate_monthly_plan(_ctx(), client)
    flags = plan.guardrail_flags
    assert any("slot 1" in f for f in flags)


# --- Regresión gotcha §5.2: 'temperature' NUNCA llega al modelo pesado ---------
# claude-opus-4-8 rechaza `temperature` con un 400; el hardening §14 lo
# reintrodujo (extracción/feedback con temperature=0) y tumbaba ambos flujos
# en producción. El filtro vive en AIClient para que ningún llamador lo repita.

def test_temperature_filtrada_para_modelo_pesado():
    from app.config import settings
    from app.services.ai.client import AIClient

    assert AIClient._effective_temperature(settings.model_heavy, 0) is None
    assert AIClient._effective_temperature(settings.model_heavy, 0.7) is None
    assert AIClient._effective_temperature(settings.model_heavy, None) is None
    # El modelo ligero (revisores §14) la conserva.
    assert AIClient._effective_temperature(settings.model_light, 0) == 0


def test_create_message_reintenta_sin_temperature():
    # Red de seguridad: si un modelo rechaza 'temperature' (400), se reintenta
    # una vez sin él en vez de tumbar la llamada.
    from types import SimpleNamespace

    from app.services.ai.client import AIClient

    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(dict(kwargs))
            if "temperature" in kwargs:
                raise RuntimeError("`temperature` is deprecated for this model")
            return SimpleNamespace(content=[], usage=None)

    client = AIClient(api_key="test")
    client._client = SimpleNamespace(messages=FakeMessages())
    client._create_message({"model": "m", "temperature": 0, "messages": []})
    assert len(calls) == 2
    assert "temperature" in calls[0] and "temperature" not in calls[1]


def _training_only_core_json() -> str:
    core = json.loads(_valid_core_json())
    return json.dumps({"training": core["training"]})


def test_plan_solo_entrenamiento_sin_dieta():
    """Plan `train`: núcleo de entreno + educativo. NADA de dieta."""
    sc = ScriptedClient([_training_only_core_json(), _education_json()])
    plan = generate_monthly_plan(_ctx(), sc, include_training=True,
                                 include_nutrition=False)
    assert len(sc.calls) == 2  # núcleo de entreno + educativo (sin comidas)
    nutrition_json, training_json, education_json, _flags = plan.to_persistable()
    assert nutrition_json is None          # no se persiste dieta
    assert training_json is not None and training_json["sessions"]
    assert education_json is not None
    # El prompt prohíbe explícitamente generar dieta y no pide comidas.
    assert "SOLO ENTRENAMIENTO" in sc.calls[0]["user"]
    assert "NO generes dieta" in sc.calls[0]["user"]


def test_plan_sin_nutricion_ni_entreno_es_error():
    from app.services.ai.generator import PlanGenerationError

    with pytest.raises(PlanGenerationError):
        generate_monthly_plan(_ctx(), ScriptedClient([]), include_training=False,
                              include_nutrition=False)


def test_el_patron_dietetico_llega_al_prompt_que_elige_los_alimentos():
    """Un vegano no puede recibir propuestas con pollo.

    El patrón viajaba solo en el bloque del cliente del NÚCLEO y en el filtro
    del catálogo; la llamada de comidas (la que de verdad elige los platos) no
    lo sabía, así que el plan salía con carne y el Revisor 0 lo vetaba después
    (créditos gastados y borrador retenido).
    """
    import dataclasses

    from app.schemas.ai import PlanCoreOutput
    from app.services.ai.generator import _meals_user_prompt

    core = PlanCoreOutput.model_validate_json(_valid_core_json())

    sin_patron = _meals_user_prompt(_ctx(), core)
    assert "PATRÓN DIETÉTICO" not in sin_patron

    vegano = dataclasses.replace(_ctx(), diet_pattern="vegano")
    prompt = _meals_user_prompt(vegano, core)
    assert "PATRÓN DIETÉTICO OBLIGATORIO" in prompt and "VEGANO" in prompt
    # Los alimentos prohibidos salen de la misma tabla que usa el validador.
    assert "pollo" in prompt.lower()

    halal = dataclasses.replace(_ctx(), diet_pattern="Halal")   # con mayúscula
    assert "HALAL" in _meals_user_prompt(halal, core)
