"""Genera shared/nutrition_contract.json — vectores dorados del contrato
compartido backend↔frontend de objetivos calóricos.

Autoridad: el BACKEND (app/services/nutrition_scale.py). Los valores esperados
se calculan desde el backend; el test de paridad (tests/test_nutrition_parity.py)
verifica que la implementación TS (frontend/src/lib/nutritionTargets.ts) produce
EXACTAMENTE lo mismo. Reejecutar tras cualquier cambio en la lógica de objetivos:

    python -m scripts.gen_nutrition_contract   (desde backend/)
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from app.services.metrics import PROTEIN_RANGE
from app.services.nutrition_scale import (
    FAT_PER_KG,
    MAX_DEFICIT_PCT,
    MAX_SURPLUS_PCT,
    kcal_of,
    macros_for_kcal,
    macros_scaled_to_kcal,
    reconcile_nutrition,
    rescale_nutrition,
)

GOALS = ["fat_loss", "muscle_gain", "recomp", "maintenance", "injury_recovery"]

# NOTA sobre clampTargets: NO entra en los vectores cruzados. El backend reparte
# "acotar" (clamp_targets) y "cuadrar carbohidratos 4/4/9" (reconcile_nutrition)
# en DOS pasos; el frontend (clampTargets) lo hace en UNO. Son descomposiciones
# distintas por diseño (el backend reconcilia el plan entero; el editor previsualiza
# a nivel de macros), así que compararlas 1:1 daría falsa deriva. Lo que SÍ se
# fija son los primitivos puros idénticos + los PARÁMETROS del clamp como
# constantes (topes de kcal y bounds por kg), abajo.
#
# Vectores de PLAN COMPLETO (`rescaledPlan`): con objetivos 4/4/9-consistentes,
# el pipeline del backend (rescale_nutrition + reconcile_nutrition clamp=False)
# y el del editor (rescaledFrom clamp=false) SÍ deben producir el MISMO plan
# byte a byte — comidas, banco (flexible y strict), gramos, medidas caseras y
# equivalencias. Es la garantía de que lo que el coach previsualiza al editar
# es EXACTAMENTE lo que el backend persiste (sin "saltos" al guardar).

# Plan base con banco flexible: comidas + opciones con ingredientes/medida
# casera + equivalencias con grupos por eje. Cubre todos los caminos de escala.
_PLAN_FLEX = {
    "target_kcal": 2000, "tdee_kcal": 2400,
    "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
    "meals": [
        {"slot": 1, "name": "Desayuno", "target": {"kcal": 500, "protein_g": 35, "carbs_g": 55, "fat_g": 15}},
        {"slot": 2, "name": "Comida", "target": {"kcal": 700, "protein_g": 55, "carbs_g": 70, "fat_g": 20}},
        {"slot": 3, "name": "Merienda", "target": {"kcal": 300, "protein_g": 20, "carbs_g": 30, "fat_g": 10}},
        {"slot": 4, "name": "Cena", "target": {"kcal": 500, "protein_g": 40, "carbs_g": 45, "fat_g": 15}},
    ],
    "meal_bank": {
        "mode": "flexible_7",
        "slots": [
            {"slot": 1, "options": [
                {"name": "Avena con fruta",
                 "macros": {"kcal": 500, "protein_g": 35, "carbs_g": 55, "fat_g": 15},
                 "ingredients": [
                     {"name": "Avena", "grams": 80, "household": "8 cucharadas ≈ 80 g"},
                     {"name": "Plátano", "grams": 120}]},
                {"name": "Tostadas con pavo",
                 "macros": {"kcal": 495, "protein_g": 36, "carbs_g": 52, "fat_g": 16},
                 "ingredients": [{"name": "Pan integral", "grams": 100}]},
            ], "equivalences": {"intro": "Cambia 60 g de avena por:", "groups": [
                {"name": "Hidratos", "note": "80 g de pan",
                 "items": [{"food": "Arroz", "amount": "70 g"}]},
                {"name": "Proteínas", "note": None,
                 "items": [{"food": "Pollo", "amount": "120 g"}]},
            ]}},
            {"slot": 2, "options": [
                {"name": "Arroz con pollo",
                 "macros": {"kcal": 700, "protein_g": 55, "carbs_g": 70, "fat_g": 20},
                 "ingredients": [{"name": "Arroz", "grams": 90}, {"name": "Pollo", "grams": 180}]},
            ]},
        ],
    },
}

# Plan base con banco strict (menú semanal fijo): plato por día/slot.
_PLAN_STRICT = {
    "target_kcal": 1800,
    "macros": {"protein_g": 140, "carbs_g": 170, "fat_g": 60},
    "meals": [
        {"slot": 1, "target": {"kcal": 600, "protein_g": 45, "carbs_g": 60, "fat_g": 20}},
        {"slot": 2, "target": {"kcal": 1200, "protein_g": 95, "carbs_g": 110, "fat_g": 40}},
    ],
    "meal_bank": {"mode": "strict", "days": [
        {"day": "lunes", "meals": [
            {"slot": 1, "dish": {"name": "Yogur con nueces",
             "macros": {"kcal": 600, "protein_g": 45, "carbs_g": 60, "fat_g": 20},
             "ingredients": [{"name": "Yogur", "grams": 250}]}},
            {"slot": 2, "dish": {"name": "Pasta con atún",
             "macros": {"kcal": 1200, "protein_g": 95, "carbs_g": 110, "fat_g": 40},
             "ingredients": [{"name": "Pasta", "grams": 110}, {"name": "Atún", "grams": 160}]}},
        ]},
    ]},
}


def _rescaled_plan(base: dict, protein_g: int, carbs_g: int, fat_g: int) -> dict:
    """Expected del vector: pipeline REAL del backend sobre una copia del base."""
    kcal = kcal_of(protein_g, carbs_g, fat_g)
    n = copy.deepcopy(base)
    rescale_nutrition(n, base, kcal, protein_g, carbs_g, fat_g)
    reconcile_nutrition(n, None, clamp=False)
    return n


def build() -> dict:
    cases = []
    for p, c, f in [(150, 200, 60), (0, 0, 0), (200, 0, 50), (120, 350, 80)]:
        cases.append({"fn": "kcalOf", "args": [p, c, f], "expected": kcal_of(p, c, f)})
    for g in GOALS:
        for w, k in [(80, 2200), (60, 1500), (95, 3000), (55, 1200)]:
            cases.append({"fn": "macrosForKcal", "args": [g, w, k],
                          "expected": macros_for_kcal(g, w, k)})
    cases.append({"fn": "macrosForKcal", "args": ["recomp", 100, 900],
                  "expected": macros_for_kcal("recomp", 100, 900)})
    for base, k in [
        ({"macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}, "target_kcal": 2000}, 2500),
        ({"macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}, "target_kcal": 2000}, 1600),
        ({"macros": {"protein_g": 0, "carbs_g": 0, "fat_g": 0}, "target_kcal": 0}, 2000),
    ]:
        cases.append({"fn": "macrosScaledToKcal", "args": [base, k],
                      "expected": macros_scaled_to_kcal(base, k)})
    # Plan completo (backend rescale+reconcile ⇄ editor rescaledFrom): subida,
    # bajada y banco strict. Los objetivos son 4/4/9-consistentes por construcción
    # (kcal = kcal_of(p,c,f)), la única zona donde ambos pipelines son 1:1.
    for plan, (p, c, f) in [
        (_PLAN_FLEX, (170, 230, 70)),
        (_PLAN_FLEX, (130, 150, 50)),
        (_PLAN_STRICT, (150, 190, 65)),
    ]:
        cases.append({
            "fn": "rescaledPlan",
            "args": [plan, {"kcal": kcal_of(p, c, f), "protein_g": p,
                            "carbs_g": c, "fat_g": f}],
            "expected": _rescaled_plan(plan, p, c, f),
        })
    return {
        "_comment": (
            "Contrato compartido backend↔frontend de objetivos calóricos. "
            "Autoridad: backend (app/services/nutrition_scale.py). NO editar a "
            "mano: regenerar con scripts/gen_nutrition_contract.py. El test "
            "tests/test_nutrition_parity.py verifica que el frontend "
            "(lib/nutritionTargets.ts) produce lo mismo."
        ),
        "constants": {
            "MAX_DEFICIT_PCT": MAX_DEFICIT_PCT, "MAX_SURPLUS_PCT": MAX_SURPLUS_PCT,
            "FAT_PER_KG": FAT_PER_KG,
            "PROTEIN_MID_PER_KG": {g: round(sum(PROTEIN_RANGE[g]) / 2, 4) for g in GOALS},
            # Parámetros del clamp (deben coincidir en clamp_targets ↔ clampTargets):
            "CLAMP_BOUNDS": {
                "protein_per_kg": [1.2, 3.0], "fat_per_kg": [0.6, 2.0],
                "fat_floor_g": 20, "kcal_abs": [1100, 4500],
                "protein_no_weight": [60, 280], "fat_no_weight": [20, 160],
            },
        },
        "cases": cases,
    }


def main() -> None:
    out = Path(__file__).resolve().parents[2] / "shared" / "nutrition_contract.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n")
    print(f"escrito {out} ({len(build()['cases'])} casos)")


if __name__ == "__main__":
    main()
