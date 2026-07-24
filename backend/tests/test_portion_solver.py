"""Tests del solver de porciones y el filtro de alimentos (hardening §2)."""
from __future__ import annotations

from app.services.portion_solver import (
    equivalent_portion,
    filter_foods,
    solve_portions,
)

# Alimentos de prueba (macros por 100 g, cotas y unidad práctica).
POLLO = {"id": 1, "canonical_name": "Pechuga de pollo", "group": "proteina",
         "kcal": 120, "protein_g": 22.5, "carbs_g": 0, "fat_g": 2.6, "fiber_g": 0,
         "allergens": [], "tags": ["sin_gluten"], "unit_grams": None, "min_grams": 80, "max_grams": 300}
ARROZ = {"id": 2, "canonical_name": "Arroz blanco", "group": "carbohidrato",
         "kcal": 354, "protein_g": 7, "carbs_g": 78, "fat_g": 1, "fiber_g": 1.3,
         "allergens": [], "tags": ["vegano"], "unit_grams": None, "min_grams": 40, "max_grams": 150}
ACEITE = {"id": 3, "canonical_name": "Aceite de oliva virgen extra", "group": "grasa",
          "kcal": 884, "protein_g": 0, "carbs_g": 0, "fat_g": 100, "fiber_g": 0,
          "allergens": [], "tags": ["vegano"], "unit_grams": 10, "min_grams": 5, "max_grams": 40}
HUEVO = {"id": 4, "canonical_name": "Huevo entero", "group": "proteina",
         "kcal": 143, "protein_g": 12.6, "carbs_g": 0.7, "fat_g": 9.9, "fiber_g": 0,
         "allergens": ["huevo"], "tags": ["vegetariano"], "unit_grams": 55, "min_grams": 55, "max_grams": 220}
GAMBAS = {"id": 5, "canonical_name": "Gambas", "group": "proteina",
          "kcal": 85, "protein_g": 18, "carbs_g": 0.9, "fat_g": 1, "fiber_g": 0,
          "allergens": ["marisco"], "tags": [], "unit_grams": None, "min_grams": 80, "max_grams": 250}
ALMENDRAS = {"id": 6, "canonical_name": "Almendras", "group": "grasa",
             "kcal": 579, "protein_g": 21, "carbs_g": 22, "fat_g": 50, "fiber_g": 12.5,
             "allergens": ["frutos secos"], "tags": ["vegano"], "unit_grams": None, "min_grams": 15, "max_grams": 60}


# ----------------------------------------------------------------- filtro ----

def test_filtro_quita_alergeno_por_campo():
    foods = [POLLO, GAMBAS, HUEVO]
    out = filter_foods(foods, allergies=["marisco"])
    names = {f["canonical_name"] for f in out}
    assert "Gambas" not in names
    assert "Pechuga de pollo" in names


def test_filtro_quita_alergeno_por_nombre_sinonimo():
    # 'frutos secos' declarado → 'Almendras' fuera aunque no repita el término.
    out = filter_foods([POLLO, ALMENDRAS], allergies=["frutos secos"])
    assert all(f["canonical_name"] != "Almendras" for f in out)


def test_filtro_patron_vegano_quita_animales():
    out = filter_foods([POLLO, ARROZ, HUEVO, ALMENDRAS], diet_pattern="vegano")
    names = {f["canonical_name"] for f in out}
    assert names == {"Arroz blanco", "Almendras"}  # pollo y huevo fuera


def test_filtro_alimento_odiado():
    out = filter_foods([POLLO, ARROZ], dislikes=["pollo"])
    assert all(f["canonical_name"] != "Pechuga de pollo" for f in out)


def test_alergeno_no_entra_nunca_ni_por_accidente():
    # Ni el filtro por campo ni por nombre dejan pasar el alérgeno.
    out = filter_foods([POLLO, GAMBAS, HUEVO, ALMENDRAS],
                       allergies=["marisco", "huevo", "frutos secos"])
    assert {f["canonical_name"] for f in out} == {"Pechuga de pollo"}


# ----------------------------------------------------------------- solver ----

def test_solver_acerca_los_macros_al_objetivo():
    target = {"protein_g": 45, "carbs_g": 60, "fat_g": 15}
    sol = solve_portions([POLLO, ARROZ, ACEITE], target)
    dev = sol.deviation_pct(target)
    # Con 3 alimentos bien elegidos, cada eje debe quedar cerca (±15%).
    assert abs(dev["protein_g"]) <= 15, dev
    assert abs(dev["carbs_g"]) <= 15, dev
    assert abs(dev["fat_g"]) <= 20, dev
    # Y devuelve gramos positivos y realistas dentro de cotas.
    for it in sol.items:
        f = next(x for x in [POLLO, ARROZ, ACEITE] if x["id"] == it.food_id)
        assert f["min_grams"] - 5 <= it.grams <= f["max_grams"] + 5


def test_solver_redondea_a_unidades_practicas():
    # El huevo (unit_grams=55) debe salir en múltiplos de 55 g.
    sol = solve_portions([HUEVO], {"protein_g": 25, "carbs_g": 1, "fat_g": 20})
    if sol.items:
        g = sol.items[0].grams
        assert g % 55 == 0, g


def test_solver_sin_alimentos_no_rompe():
    sol = solve_portions([], {"protein_g": 40, "carbs_g": 50, "fat_g": 10})
    assert sol.items == []
    assert sol.totals["kcal"] == 0


def test_solver_totales_coinciden_con_la_suma_de_items():
    sol = solve_portions([POLLO, ARROZ, ACEITE], {"protein_g": 40, "carbs_g": 55, "fat_g": 12})
    p = round(sum(i.macros["protein_g"] for i in sol.items), 1)
    assert sol.totals["protein_g"] == p


# ------------------------------------------------------------ equivalencias ----

def test_equivalencia_por_macro_neta():
    # 60 g de arroz (crudo) aportan 46,8 g HC; ¿cuánta patata iguala esos HC?
    PATATA = {"canonical_name": "Patata", "kcal": 77, "protein_g": 2, "carbs_g": 17,
              "fat_g": 0.1, "unit_grams": None}
    grams = equivalent_portion(ARROZ, 60, PATATA, axis="carbs_g")
    # 46,8 g HC / (17/100) = 275 g de patata (redondeado a 5)
    assert 270 <= grams <= 280
