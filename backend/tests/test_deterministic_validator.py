"""Tests del Validador Determinista (hardening §9.0) — el "Revisor 0" del panel
con veto absoluto: coherencia Atwater, suma de comidas, tolerancias del contrato,
alérgenos en subingredientes, patrón dietético, nº de comidas y porciones."""
from __future__ import annotations

from app.services.guardrails import validate_plan_deterministic


def _coherent_plan() -> dict:
    """Plan mínimo COHERENTE: kcal = 4/4/9, Σ comidas = día, opciones cuadran."""
    return {
        "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 44},  # 600+800+396... ajustar
        "meals": [
            {"slot": 1, "target": {"kcal": 800, "protein_g": 60, "carbs_g": 80, "fat_g": 18}},
            {"slot": 2, "target": {"kcal": 1196, "protein_g": 90, "carbs_g": 120, "fat_g": 26}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": [
            {"slot": 1, "options": [
                {"key": "A", "title": "Avena con pollo", "prep": "hervir",
                 "ingredients": [{"food": "Copos de avena", "grams": 80, "household": ""},
                                  {"food": "Pechuga de pollo", "grams": 150, "household": ""}],
                 # kcal = 60·4 + 80·4 + 18·9 = 722 (Atwater coherente consigo misma)
                 "macros": {"kcal": 722, "protein_g": 60, "carbs_g": 80, "fat_g": 18}},
            ]},
        ]},
    }


def _fix_totals(plan: dict) -> dict:
    """Cuadra macros y Σ comidas para partir de un plan sin violaciones."""
    m = plan["macros"]
    m_kcal = m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    plan["target_kcal"] = m_kcal
    # dos comidas: reparte exacto
    p, c, f = m["protein_g"], m["carbs_g"], m["fat_g"]
    plan["meals"] = [
        {"slot": 1, "target": {"kcal": (p//2)*4 + (c//2)*4 + (f//2)*9,
                                "protein_g": p//2, "carbs_g": c//2, "fat_g": f//2}},
        {"slot": 2, "target": {"kcal": (p-p//2)*4 + (c-c//2)*4 + (f-f//2)*9,
                                "protein_g": p-p//2, "carbs_g": c-c//2, "fat_g": f-f//2}},
    ]
    return plan


def test_plan_coherente_pasa():
    plan = _fix_totals(_coherent_plan())
    r = validate_plan_deterministic(plan)
    assert r.ok, r.violations


def test_atwater_incoherente_bloquea():
    plan = _fix_totals(_coherent_plan())
    plan["target_kcal"] = plan["target_kcal"] + 200  # declara 200 kcal de más
    r = validate_plan_deterministic(plan)
    assert not r.ok
    assert any("Atwater" in v for v in r.violations)


def test_suma_de_comidas_distinta_del_dia_bloquea():
    plan = _fix_totals(_coherent_plan())
    plan["meals"][0]["target"]["protein_g"] += 30  # rompe Σ = día
    r = validate_plan_deterministic(plan)
    assert not r.ok
    assert any("Σ comidas" in v for v in r.violations)


def test_tolerancias_del_contrato():
    plan = _fix_totals(_coherent_plan())
    obj = {"kcal": plan["target_kcal"], "protein_g": plan["macros"]["protein_g"] + 20,
           "carbs_g": plan["macros"]["carbs_g"], "fat_g": plan["macros"]["fat_g"]}
    r = validate_plan_deterministic(plan, objective_macros=obj)
    assert not r.ok  # proteína 20 g por debajo del contrato (> ±5 g)
    assert any("proteína" in v for v in r.violations)


def test_alergeno_en_subingrediente_del_titulo():
    plan = _fix_totals(_coherent_plan())
    # 'pesto' en el título → frutos secos, aunque no esté en ingredients.
    plan["meal_bank"]["slots"][0]["options"][0]["title"] = "Pasta al pesto"
    r = validate_plan_deterministic(plan, allergies=["frutos secos"])
    assert not r.ok
    assert any("ALÉRGENO" in v for v in r.violations)


def test_alimento_odiado_es_veto_no_aviso():
    plan = _fix_totals(_coherent_plan())
    r = validate_plan_deterministic(plan, dislikes=["pollo"])
    assert not r.ok
    assert any("odiado" in v for v in r.violations)


def test_patron_vegano_bloquea_alimentos_animales():
    plan = _fix_totals(_coherent_plan())  # lleva pollo
    r = validate_plan_deterministic(plan, diet_pattern="vegano")
    assert not r.ok
    assert any("vegano" in v for v in r.violations)


def test_numero_de_comidas():
    plan = _fix_totals(_coherent_plan())  # 2 comidas
    r = validate_plan_deterministic(plan, meals_expected=3)
    assert not r.ok
    assert any("nº de comidas" in v for v in r.violations)


def test_porcion_irreal_bloquea():
    plan = _fix_totals(_coherent_plan())
    plan["meal_bank"]["slots"][0]["options"][0]["ingredients"][1]["grams"] = 900  # 900 g pollo
    r = validate_plan_deterministic(plan)
    assert not r.ok
    assert any("porción irreal" in v for v in r.violations)


def test_huevos_irreales_bloquea():
    plan = _fix_totals(_coherent_plan())
    plan["meal_bank"]["slots"][0]["options"][0]["ingredients"] = [
        {"food": "Huevo entero", "grams": 550, "household": "10 huevos"}
    ]
    r = validate_plan_deterministic(plan)
    assert not r.ok
    assert any("huevos" in v for v in r.violations)


def test_liquido_grande_no_es_porcion_irreal():
    plan = _fix_totals(_coherent_plan())
    plan["meal_bank"]["slots"][0]["options"][0]["ingredients"] = [
        {"food": "Leche desnatada", "grams": 750, "household": "3 vasos"}
    ]
    r = validate_plan_deterministic(plan)
    # 750 g de leche es una ración grande pero no absurda: no bloquea por porción.
    assert not any("porción irreal" in v for v in r.violations)
