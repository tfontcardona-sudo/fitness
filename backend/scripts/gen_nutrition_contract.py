"""Genera shared/nutrition_contract.json — vectores dorados del contrato
compartido backend↔frontend de objetivos calóricos.

Autoridad: el BACKEND (app/services/nutrition_scale.py). Los valores esperados
se calculan desde el backend; el test de paridad (tests/test_nutrition_parity.py)
verifica que la implementación TS (frontend/src/lib/nutritionTargets.ts) produce
EXACTAMENTE lo mismo. Reejecutar tras cualquier cambio en la lógica de objetivos:

    python -m scripts.gen_nutrition_contract   (desde backend/)
"""
from __future__ import annotations

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
)

GOALS = ["fat_loss", "muscle_gain", "recomp", "maintenance", "injury_recovery"]

# NOTA sobre clampTargets: NO entra en los vectores cruzados. El backend reparte
# "acotar" (clamp_targets) y "cuadrar carbohidratos 4/4/9" (reconcile_nutrition)
# en DOS pasos; el frontend (clampTargets) lo hace en UNO. Son descomposiciones
# distintas por diseño (el backend reconcilia el plan entero; el editor previsualiza
# a nivel de macros), así que compararlas 1:1 daría falsa deriva. Lo que SÍ se
# fija son los primitivos puros idénticos + los PARÁMETROS del clamp como
# constantes (topes de kcal y bounds por kg), abajo.


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
