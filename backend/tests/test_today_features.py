"""Tests unitarios de las piezas nuevas: emparejado producto⇄suplemento, URL de
compra con descuento (patrón Shopify) y diff determinista del plan editado.
"""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")


def test_product_match_basico_y_sinonimos():
    from app.services.product_match import match_products, product_covers

    assert product_covers("Creatina monohidrato", "ESN Ultrapure Creatine")
    assert product_covers("Proteína de suero", "Designer Whey Protein")
    assert product_covers("Omega 3", "Super Omega-3 caps")
    assert not product_covers("Creatina", "Shaker 700 ml")

    res = match_products(["Creatina", "Melatonina"], ["ESN Creatine", "Whey ESN"])
    assert res["covered_titles"] == {"ESN Creatine"}
    assert res["missing"] == ["Melatonina"]


def test_discount_buy_url_solo_en_dominio_del_partner():
    from app.services.portal import discount_buy_url

    store = "https://www.esn.com/collections/all"
    prod = "https://www.esn.com/products/creatine?variant=1"
    out = discount_buy_url(prod, "QUICE10", store)
    assert out is not None
    assert out.startswith("https://www.esn.com/discount/QUICE10?redirect=")
    assert "%2Fproducts%2Fcreatine" in out

    # Otro dominio (o sin código/tienda) → enlace normal, sin inventos.
    otro = "https://amazon.es/dp/X1"
    assert discount_buy_url(otro, "QUICE10", store) == otro
    assert discount_buy_url(prod, None, store) == prod
    assert discount_buy_url(prod, "QUICE10", None) == prod


def test_plan_diff_nutricion_y_suplementos():
    from app.services.plan_diff import manual_change_summary

    old_n = {"target_kcal": 2200, "macros": {"protein_g": 180, "carbs_g": 230, "fat_g": 70},
             "meals": [{"name": "Desayuno"}, {"name": "Comida"}, {"name": "Cena"}],
             "supplements": [{"name": "Creatina"}]}
    new_n = {"target_kcal": 2000, "macros": {"protein_g": 200, "carbs_g": 230, "fat_g": 70},
             "meals": [{"name": "Desayuno"}, {"name": "Comida"}, {"name": "Cena"}],
             "supplements": [{"name": "Creatina"}, {"name": "Melatonina"}]}
    items = manual_change_summary(None, old_nutrition=old_n, new_nutrition=new_n,
                                  old_training=None, new_training=None)
    assert "Calorías: 2200 → 2000 kcal" in items
    assert "Proteína: 180 → 200 g" in items
    assert "Suplemento añadido: Melatonina" in items
    assert not any("Carbohidratos" in i for i in items)  # sin cambio → no aparece

    # Sin cambios → lista vacía (no molesta al coach).
    assert manual_change_summary(None, old_nutrition=old_n, new_nutrition=dict(old_n),
                                 old_training=None, new_training=None) == []


def _meal(name, kcal, p, c, f):
    return {"name": name, "target": {"kcal": kcal, "protein_g": p, "carbs_g": c, "fat_g": f}}


def test_reconcile_edicion_extrema_queda_sana_y_coherente():
    """El caso real del PDF roto: CH 800 / grasa 0 / +77% de superávit tecleados
    en el editor. Tras reconciliar: topes fisiológicos aplicados y TODO cuadra
    (totales ≡ macros ≡ comidas ≡ banco/equivalencias)."""
    import copy

    from app.services.nutrition_scale import kcal_of, reconcile_nutrition

    nut = {
        "tdee_kcal": 2203,
        "target_kcal": 3904,
        "macros": {"protein_g": 176, "carbs_g": 800, "fat_g": 0},
        "meals": [_meal("Desayuno", 472, 41, 50, 12), _meal("Comida", 618, 51, 63, 18),
                  _meal("Merienda", 378, 35, 37, 10), _meal("Cena", 588, 49, 35, 28)],
        "meal_bank": {"mode": "flexible_7", "slots": [{
            "slot": 1,
            "options": [{"title": "Batido", "macros": {"kcal": 472, "protein_g": 41, "carbs_g": 50, "fat_g": 12},
                         "ingredients": [{"food": "Avena", "grams": 100, "household": "1 taza (100 g)"}]}],
            "equivalences": {"intro": "Para ~50 g de CH", "groups": [
                {"name": "Fruta de postre", "note": None,
                 "items": [{"name": "Plátano", "amount": "120 g (1 pequeño)"}]},
                {"name": "Grasas", "note": None,
                 "items": [{"name": "Aceite de oliva", "amount": "12 g (1 cucharada)"}]},
            ]},
        }]},
    }
    reconcile_nutrition(nut, weight_kg=75)

    m = nut["macros"]
    # Topes fisiológicos: grasa nunca 0 (suelo 0,6 g/kg), kcal ≤ TDEE +15 %.
    assert m["fat_g"] >= 45
    assert 1100 <= nut["target_kcal"] <= round(2203 * 1.15)
    # Una sola verdad: kcal ≡ macros 4/4/9.
    assert nut["target_kcal"] == kcal_of(m["protein_g"], m["carbs_g"], m["fat_g"])
    # Las comidas suman EXACTO los totales, eje a eje.
    for axis, total in (("protein_g", m["protein_g"]), ("carbs_g", m["carbs_g"]),
                        ("fat_g", m["fat_g"]), ("kcal", nut["target_kcal"])):
        assert sum(mm["target"][axis] for mm in nut["meals"]) == total, axis
    # El banco se reescala en armonía: nada de plátanos de 520 g ni aceite de 1 g.
    platano = nut["meal_bank"]["slots"][0]["equivalences"]["groups"][0]["items"][0]["amount"]
    aceite = nut["meal_bank"]["slots"][0]["equivalences"]["groups"][1]["items"][0]["amount"]
    avena = nut["meal_bank"]["slots"][0]["options"][0]["ingredients"][0]["grams"]
    assert int(platano.split(" ")[0]) <= 240  # el bug lo dejaba en 520 g
    assert int(aceite.split(" ")[0]) >= 5     # el bug lo dejaba en "1 g"
    assert 50 <= avena <= 200

    # Idempotencia: reconciliar lo ya coherente no cambia nada.
    again = copy.deepcopy(nut)
    reconcile_nutrition(again, weight_kg=75)
    assert again == nut


def test_reconcile_no_toca_un_plan_sano():
    """Plan coherente y dentro de topes → reconcile es un no-op (ni banco ni comidas)."""
    import copy

    from app.services.nutrition_scale import reconcile_nutrition

    nut = {
        "tdee_kcal": 2500,
        "target_kcal": 2056,
        "macros": {"protein_g": 176, "carbs_g": 185, "fat_g": 68},
        "meals": [_meal("Desayuno", 472, 41, 50, 12), _meal("Comida", 618, 51, 63, 18),
                  _meal("Merienda", 378, 35, 37, 10), _meal("Cena", 588, 49, 35, 28)],
        "meal_bank": {"mode": "flexible_7", "slots": [{
            "slot": 1, "options": [{"title": "Batido",
                                    "macros": {"kcal": 472, "protein_g": 41, "carbs_g": 50, "fat_g": 12},
                                    "ingredients": [{"food": "Avena", "grams": 100, "household": "1 taza"}]}],
        }]},
    }
    before = copy.deepcopy(nut)
    reconcile_nutrition(nut, weight_kg=75)
    assert nut == before
