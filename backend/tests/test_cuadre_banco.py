"""Regresión del cuadre del banco: solo se arregla el desvío de ESCALA."""
import warnings
warnings.filterwarnings("ignore")


def _macros_reales(ingredientes, por_100g):
    """Los macros que dan DE VERDAD esos gramos, según la tabla del caso."""
    out = {"protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for ing in ingredientes:
        p100 = por_100g[ing["food"]]
        f = ing["grams"] / 100.0
        for k in out:
            out[k] += p100[k] * f
    return {k: round(v, 1) for k, v in out.items()}


def test_un_desvio_de_composicion_no_se_maquilla():
    """`_scale_dish` fija cada macro a su eje pero mueve los gramos por un
    ÚNICO factor. Con un plato que tiene el mix equivocado eso dejaba los
    macros clavados al objetivo y los ingredientes dando otra cosa: el plan
    IMPRIMÍA una proteína que su propia lista de la compra no da, el PDF
    imprimía esos gramos y nada lo cazaba después (el Revisor 0 compara los
    macros DECLARADOS, y los revisores IA solo ven nombres de alimentos)."""
    from app.services.ai.generator import _repara_desvios_del_banco

    POR_100G = {
        "Pollo":  {"protein_g": 23.0, "carbs_g": 0.0,  "fat_g": 2.0},
        "Arroz":  {"protein_g": 7.0,  "carbs_g": 78.0, "fat_g": 0.6},
        "Aceite": {"protein_g": 0.0,  "carbs_g": 0.0,  "fat_g": 100.0},
    }
    ingredientes = [{"food": "Pollo", "grams": 120}, {"food": "Arroz", "grams": 80},
                    {"food": "Aceite", "grams": 10}]
    # Macros COHERENTES con esos gramos (los que dan de verdad).
    reales = _macros_reales(ingredientes, POR_100G)
    mac = dict(reales)
    mac["kcal"] = round(mac["protein_g"] * 4 + mac["carbs_g"] * 4 + mac["fat_g"] * 9)

    plato = {"key": "A", "title": "Pollo con arroz",
             "ingredients": [dict(i) for i in ingredientes], "macros": dict(mac)}
    bank = {"mode": "flexible_7", "slots": [{"slot": 1, "options": [plato]}]}
    # Objetivo con OTRO reparto (más proteína, menos hidratos): composición.
    objetivo = {1: {"kcal": mac["kcal"], "protein_g": 45, "carbs_g": 45, "fat_g": 15}}

    cuadrados = _repara_desvios_del_banco(bank, objetivo)
    assert cuadrados == 0, "un desvío de composición no se puede arreglar con gramos"
    assert plato["macros"] == mac, "el plato no se ha tocado"
    # Y lo que importa: sus macros los siguen dando sus ingredientes.
    assert _macros_reales(plato["ingredients"], POR_100G) == reales


def test_un_desvio_de_escala_si_se_cuadra_y_los_gramos_lo_acompanan():
    """El caso que motivó el cuadre: el mix CORRECTO en la cantidad
    equivocada (un plato a 700 kcal contra un objetivo de 800). Ahí sí basta
    con mover los gramos, y el plato sigue siendo lo que sus ingredientes dan."""
    from app.services.ai.generator import _repara_desvios_del_banco

    POR_100G = {
        "Pollo":  {"protein_g": 23.0, "carbs_g": 0.0,  "fat_g": 2.0},
        "Arroz":  {"protein_g": 7.0,  "carbs_g": 78.0, "fat_g": 0.6},
        "Aceite": {"protein_g": 0.0,  "carbs_g": 0.0,  "fat_g": 100.0},
    }
    # Gramos elegidos para que ×1,2 caiga en múltiplos de 5 y el redondeo de
    # `_scale_g` (raciones cocinables) no ensucie la comprobación.
    ingredientes = [{"food": "Pollo", "grams": 150}, {"food": "Arroz", "grams": 100},
                    {"food": "Aceite", "grams": 25}]
    reales = _macros_reales(ingredientes, POR_100G)
    mac = dict(reales)
    mac["kcal"] = round(mac["protein_g"] * 4 + mac["carbs_g"] * 4 + mac["fat_g"] * 9)

    plato = {"key": "A", "title": "Pollo con arroz",
             "ingredients": [dict(i) for i in ingredientes], "macros": dict(mac)}
    bank = {"mode": "flexible_7", "slots": [{"slot": 1, "options": [plato]}]}
    # MISMO mix, un 20 % más de todo: puro desvío de escala.
    objetivo = {1: {k: round(v * 1.2, 1) for k, v in mac.items()}}

    cuadrados = _repara_desvios_del_banco(bank, objetivo)
    assert cuadrados == 1, "el desvío de escala sí se cuadra"
    assert [i["grams"] for i in plato["ingredients"]] == [180, 120, 30]

    # Los macros quedan en el objetivo…
    for eje in ("protein_g", "carbs_g", "fat_g"):
        assert abs(plato["macros"][eje] - objetivo[1][eje]) <= 1.0, eje
    # …y los INGREDIENTES los siguen dando (que es lo que se rompía).
    ahora = _macros_reales(plato["ingredients"], POR_100G)
    for eje in ("protein_g", "carbs_g", "fat_g"):
        declarado = float(plato["macros"][eje])
        assert abs(ahora[eje] - declarado) / max(declarado, 1) <= 0.05, (
            f"{eje}: declara {declarado} y sus gramos dan {ahora[eje]}")
