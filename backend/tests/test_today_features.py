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
