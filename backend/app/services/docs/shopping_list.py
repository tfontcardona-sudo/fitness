"""Lista de la compra semanal (modo strict).

Deriva por agregación aritmética la lista de la compra exacta a partir del
menú cerrado de 7 días: suma los gramos de cada ingrediente a lo largo de toda
la semana y los agrupa por categoría. Es aritmética pura (testable) y debe
cuadrar con el menú (test de agregación, PARTE B).

El agrupado por categoría usa un diccionario de palabras clave; lo desconocido
cae en "Otros" para no perder nada.
"""

from __future__ import annotations

from collections import defaultdict

# Categorización por palabras clave (es de cara al cliente, en castellano).
CATEGORIES: dict[str, list[str]] = {
    "Proteínas": [
        "pollo", "pavo", "ternera", "cerdo", "huevo", "atún", "salmón", "merluza",
        "pescado", "gambas", "lomo", "jamón", "queso", "yogur", "skyr", "requesón",
        "tofu", "seitán", "proteína", "clara",
    ],
    "Verduras y hortalizas": [
        "lechuga", "tomate", "cebolla", "pimiento", "calabacín", "berenjena",
        "brócoli", "espinaca", "zanahoria", "pepino", "champiñón", "ajo", "espárrago",
        "judía", "col", "coliflor", "canónigos", "rúcula", "verdura", "ensalada",
    ],
    "Frutas": [
        "manzana", "plátano", "fresa", "naranja", "kiwi", "arándano", "pera", "uva",
        "melón", "sandía", "mango", "piña", "frambuesa", "fruta", "aguacate", "limón",
    ],
    "Hidratos": [
        "arroz", "pasta", "pan", "patata", "avena", "quinoa", "couscous", "legumbre",
        "lenteja", "garbanzo", "tortita", "cereal", "boniato", "harina",
    ],
    "Grasas y otros": [
        "aceite", "oliva", "almendra", "nuez", "cacahuete", "semilla", "mantequilla",
        "chocolate", "coco", "tahini", "crema",
    ],
}


def _categorize(food: str) -> str:
    f = food.lower()
    for cat, keywords in CATEGORIES.items():
        if any(k in f for k in keywords):
            return cat
    return "Otros"


def build_shopping_list(strict_menu: dict) -> dict[str, list[dict]]:
    """Agrega ingredientes de un menú strict (MealsStrictOutput serializado).

    Devuelve {categoría: [{food, grams, mentions}]} ordenado, donde `grams` es
    la suma semanal y `mentions` cuántas veces aparece (para detectar staples).
    """
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    non_gram: dict[str, int] = defaultdict(int)  # ingredientes "al gusto" sin gramos

    for day in strict_menu.get("days", []):
        for meal in day.get("meals", []):
            dish = meal.get("dish", {})
            for ing in dish.get("ingredients", []):
                food = ing.get("food", "").strip()
                if not food:
                    continue
                grams = ing.get("grams")
                if grams:
                    totals[food] += float(grams)
                    counts[food] += 1
                else:
                    non_gram[food] += 1

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for food, grams in totals.items():
        by_cat[_categorize(food)].append({
            "food": food, "grams": round(grams), "mentions": counts[food],
        })
    for food, n in non_gram.items():
        if food not in totals:
            by_cat[_categorize(food)].append({
                "food": food, "grams": None, "mentions": n,
            })

    # Ordena categorías por el orden canónico y los ítems por gramos desc.
    order = list(CATEGORIES.keys()) + ["Otros"]
    out: dict[str, list[dict]] = {}
    for cat in order:
        if cat in by_cat:
            out[cat] = sorted(by_cat[cat], key=lambda x: (x["grams"] is None, -(x["grams"] or 0)))
    return out


def shopping_list_total_grams(shopping: dict[str, list[dict]]) -> float:
    """Suma total de gramos (para el test de agregación: debe cuadrar con el menú)."""
    return sum(
        item["grams"] for items in shopping.values() for item in items if item["grams"]
    )
