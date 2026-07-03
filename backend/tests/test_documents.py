"""Tests de generación de documentos (Fase 7).

- Lista de la compra: la agregación aritmética cuadra con el menú (PARTE B).
- Gráficas: devuelven PNG no vacíos.
- Documentos Word: se generan, son ZIP válidos (docx) y no están vacíos.

No requieren base de datos: trabajan sobre estructuras en memoria.
"""

from __future__ import annotations

import io
import json
import zipfile

from app.services.docs import charts
from app.services.docs.feedback_doc import generate_feedback_doc
from app.services.docs.plan_doc import generate_plan_doc
from app.services.docs.shopping_list import (
    build_shopping_list,
    shopping_list_total_grams,
)
from app.services.docs.word_base import DocBrand

BRAND = DocBrand(name="DQ Coaching", color_primary="#6EE7B7",
                 color_secondary="#8B9DF7", font_family="Inter")


def _strict_menu(grams_per_ing=(("Pollo", 150), ("Arroz", 80), ("Aceite de oliva", 10))):
    days = []
    for d in ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]:
        meals = []
        for s in (1, 2, 3, 4):
            meals.append({
                "slot": s,
                "dish": {
                    "key": "A", "title": f"Plato {s}",
                    "ingredients": [{"food": f, "grams": g, "household": "x"} for f, g in grams_per_ing],
                    "prep": "Cocinar", "prep_minutes": 15,
                    "macros": {"kcal": 500, "protein_g": 40, "carbs_g": 50, "fat_g": 15}, "tags": [],
                },
            })
        days.append({"day": d, "meals": meals})
    return {"mode": "strict", "days": days, "free_meal_guidelines": None}


# ----------------------------------------------- lista de la compra ----

def test_shopping_list_aggregates_correctly():
    menu = _strict_menu()
    shopping = build_shopping_list(menu)
    # Pollo: 150 g × 4 slots × 7 días = 4200 g
    pollo = next(i for cat in shopping.values() for i in cat if i["food"] == "Pollo")
    assert pollo["grams"] == 4200
    arroz = next(i for cat in shopping.values() for i in cat if i["food"] == "Arroz")
    assert arroz["grams"] == 2240  # 80 × 28
    aceite = next(i for cat in shopping.values() for i in cat if i["food"] == "Aceite de oliva")
    assert aceite["grams"] == 280  # 10 × 28


def test_shopping_list_total_matches_menu():
    """Test de agregación (PARTE B): la suma de la lista cuadra con el menú."""
    grams = (("Pollo", 150), ("Arroz", 80), ("Aceite de oliva", 10))
    menu = _strict_menu(grams)
    expected = sum(g for _, g in grams) * 4 * 7  # por slot y día
    assert shopping_list_total_grams(build_shopping_list(menu)) == expected


def test_shopping_list_categorizes():
    menu = _strict_menu((("Pollo", 100), ("Brócoli", 200), ("Manzana", 150), ("Pan", 80)))
    shopping = build_shopping_list(menu)
    assert "Proteínas" in shopping
    assert "Verduras y hortalizas" in shopping
    assert "Frutas" in shopping
    assert "Hidratos" in shopping


def test_shopping_list_tolerates_no_grams():
    menu = {"mode": "strict", "days": [{"day": "lunes", "meals": [
        {"slot": 1, "dish": {"title": "X", "ingredients": [
            {"food": "Sal", "grams": None}, {"food": "Pollo", "grams": 150},
        ], "macros": {}}}]}]}
    shopping = build_shopping_list(menu)
    sal = next(i for cat in shopping.values() for i in cat if i["food"] == "Sal")
    assert sal["grams"] is None


# --------------------------------------------------------- gráficas ----

def test_charts_return_png():
    accent = "#6EE7B7"
    pngs = [
        charts.weight_trend_chart([("D1", 82), ("D7", 81), ("D14", 80)], 76, accent),
        charts.adherence_chart(85, 92, accent),
        charts.e1rm_chart([{"name": "Press", "e1rm_kg": 92, "delta_kg": 5}], accent),
        charts.perimeters_chart({"Cintura": [("I", 88), ("F", 85)]}, accent),
        charts.volume_by_group_chart({"pecho": 14, "espalda": 18}, accent),
    ]
    for png in pngs:
        assert png[:8] == b"\x89PNG\r\n\x1a\n"  # firma PNG
        assert len(png) > 1000


# ----------------------------------------------------- documentos ----

def _is_valid_docx(data: bytes) -> bool:
    if data[:2] != b"PK":  # los docx son ZIP
        return False
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return "word/document.xml" in zf.namelist()


def _plan_inputs():
    from tests.test_ai_service import _education_json, _flexible_meals_json, _valid_core_json

    core = json.loads(_valid_core_json())
    meals = json.loads(_flexible_meals_json())
    edu = json.loads(_education_json())
    nutrition = core["nutrition"]
    nutrition["meal_bank"] = meals
    return nutrition, core["training"], edu


def test_generate_plan_doc_flexible():
    nutrition, training, education = _plan_inputs()
    data = generate_plan_doc(
        brand=BRAND, client_name="Marta López", month_index=1, goal_type="fat_loss",
        diet_mode="flexible_7", nutrition=nutrition, training=training, education=education,
    )
    assert _is_valid_docx(data) and len(data) > 10000


def test_generate_plan_doc_strict_with_shopping_list():
    nutrition, training, education = _plan_inputs()
    nutrition = dict(nutrition)
    nutrition["meal_bank"] = _strict_menu()
    data = generate_plan_doc(
        brand=BRAND, client_name="Carlos Ruiz", month_index=2, goal_type="muscle_gain",
        diet_mode="strict", nutrition=nutrition, training=training, education=education,
    )
    assert _is_valid_docx(data)


def test_generate_feedback_doc_with_charts():
    metrics = {
        "weight": {"delta_kg": -1.2, "start_kg": 82, "end_kg": 80.8},
        "adherence": {"diet_adherence_ratio": 0.85, "log_ratio": 0.92, "days_logged": 13, "period_days": 14},
    }
    data = generate_feedback_doc(
        brand=BRAND, client_name="Marta López", period_index=1, metrics=metrics,
        weight_points=[("D1", 82.0), ("D7", 81.2), ("D14", 80.8)], goal_kg=76,
        e1rm_exercises=[{"name": "Press banca", "e1rm_kg": 92, "delta_kg": 5}],
        perimeters={"Cintura": [("I", 88), ("F", 85.5)]},
        volume_by_group={"pecho": 14, "espalda": 18},
        photo_pairs=None, ai_photo_analysis=None,
        natural_analysis="Has perdido 1,2 kg con una adherencia del 85%.",
        changes_bullets=["Mantenemos calorías.", "Subimos press banca 2,5 kg."],
        answers="Sobre el descanso: 2-3 min en básicos.",
        next_objectives=["Llegar a 80 kg."],
        closing_message="¡Vas muy bien!",
    )
    assert _is_valid_docx(data)
    # El feedback incrusta imágenes (gráficas): debe pesar bastante más
    assert len(data) > 50000


def test_feedback_doc_limits_changes_to_5_bullets():
    """Solo deben aparecer los primeros 5 bullets de cambios (H.4)."""
    metrics = {"weight": {"delta_kg": 0}, "adherence": {}}
    many = [f"Cambio {i}" for i in range(8)]
    data = generate_feedback_doc(
        brand=BRAND, client_name="Test", period_index=1, metrics=metrics,
        weight_points=[], goal_kg=None, e1rm_exercises=[], perimeters=None,
        volume_by_group=None, photo_pairs=None, ai_photo_analysis=None,
        natural_analysis="x", changes_bullets=many, answers=None,
        next_objectives=[], closing_message="fin",
    )
    # Extrae texto del docx y comprueba que "Cambio 5/6/7" no aparecen
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    assert "Cambio 0" in xml and "Cambio 4" in xml
    assert "Cambio 5" not in xml and "Cambio 7" not in xml
