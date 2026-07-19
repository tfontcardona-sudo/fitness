"""Tests del banco de opciones por defecto (tomas sin banco → 3 opciones).

Regla de producto: al cliente SIEMPRE se le dan opciones concretas — ninguna
toma puede quedar como "toma libre". Estas opciones deben cuadrar con los
macros de la toma y respetar alergias/aversiones.
"""

from app.services.meal_fallback import build_fallback_options, ensure_bank_slots


def _meal(name="Media mañana", kcal=400, p=30, c=45, f=10, slot=2):
    return {"slot": slot, "name": name, "time": "11:00",
            "target": {"kcal": kcal, "protein_g": p, "carbs_g": c, "fat_g": f}}


def test_da_tres_opciones_escaladas_a_las_kcal_objetivo():
    opts = build_fallback_options(_meal(kcal=400))
    assert len(opts) == 3
    assert [o["key"] for o in opts] == ["A", "B", "C"]
    for o in opts:
        # coherencia interna: kcal ≡ 4/4/9 de sus propios macros (±1 por redondeo)
        m = o["macros"]
        assert abs(m["kcal"] - (4 * m["protein_g"] + 4 * m["carbs_g"] + 9 * m["fat_g"])) <= 2
        # y cerca del objetivo de la toma (el escalado es lineal y con redondeo a 5 g)
        assert 400 * 0.8 <= m["kcal"] <= 400 * 1.2
        assert o["ingredients"] and all(i["grams"] >= 5 for i in o["ingredients"])


def test_tipo_de_toma_por_nombre():
    des = build_fallback_options(_meal(name="Desayuno", kcal=500))
    cena = build_fallback_options(_meal(name="Cena", kcal=650))
    titles_des = " ".join(o["title"].lower() for o in des)
    titles_cena = " ".join(o["title"].lower() for o in cena)
    assert "avena" in titles_des or "tostadas" in titles_des or "porridge" in titles_des
    assert "pollo" in titles_cena or "merluza" in titles_cena or "ternera" in titles_cena


def test_alergias_excluyen_siempre():
    opts = build_fallback_options(_meal(name="Cena", kcal=600), allergies=["pescado"])
    text = " ".join(i["food"].lower() for o in opts for i in o["ingredients"])
    assert "merluza" not in text and "salmón" not in text
    assert len(opts) == 3  # quedan suficientes candidatas seguras


def test_aversiones_se_evitan_si_es_posible():
    opts = build_fallback_options(_meal(name="Cena", kcal=600), dislikes=["pasta"])
    text = " ".join(i["food"].lower() for o in opts for i in o["ingredients"])
    assert "pasta" not in text


def test_ensure_rellena_solo_los_slots_vacios():
    nut = {
        "meals": [_meal(name="Desayuno", slot=1), _meal(name="Media mañana", slot=2),
                  _meal(name="Cena", slot=3)],
        "meal_bank": {"mode": "flexible_7", "slots": [
            {"slot": 1, "fmt": "options",
             "options": [{"key": "A", "title": "Del coach", "ingredients": [],
                          "macros": {"kcal": 500, "protein_g": 40, "carbs_g": 50, "fat_g": 12}}],
             "weekly_examples": []},
        ]},
    }
    filled = ensure_bank_slots(nut)
    assert filled == 2
    slots = {s["slot"]: s for s in nut["meal_bank"]["slots"]}
    assert slots[1]["options"][0]["title"] == "Del coach"  # lo existente no se toca
    assert len(slots[2]["options"]) == 3 and len(slots[3]["options"]) == 3
    assert len(slots[2]["weekly_examples"]) == 7
    # idempotente: una segunda pasada no cambia nada
    assert ensure_bank_slots(nut) == 0


def test_ensure_crea_el_banco_si_no_existe_y_respeta_strict():
    nut = {"meals": [_meal(slot=1)]}
    assert ensure_bank_slots(nut) == 1
    assert nut["meal_bank"]["mode"] == "flexible_7"

    strict = {"meals": [_meal(slot=1)], "meal_bank": {"mode": "strict", "days": []}}
    assert ensure_bank_slots(strict) == 0
    assert "slots" not in strict["meal_bank"]
