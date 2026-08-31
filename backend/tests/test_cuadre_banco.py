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


# ---------------------------------------------------------------------------
# El cuadre respeta el catálogo (lo que arreglaba el solver, no lo deshace)
# ---------------------------------------------------------------------------

def _catalogo():
    return {
        1: {"id": 1, "canonical_name": "Huevo entero", "protein_g": 12.6,
            "carbs_g": 0.7, "fat_g": 9.5, "unit_grams": 55,
            "min_grams": 55, "max_grams": 220},
        2: {"id": 2, "canonical_name": "Pan integral", "protein_g": 8.5,
            "carbs_g": 41.0, "fat_g": 3.3, "unit_grams": 40,
            "min_grams": 40, "max_grams": 150},
    }


def test_el_cuadre_no_se_salta_las_cotas_del_catalogo():
    """`_scale_dish` mueve TODOS los gramos por un factor y no conoce el
    catálogo: se saltaba `min_grams`/`max_grams` justo después de que el solver
    los hubiera respetado. Con catálogo disponible, el cuadre pasa por el
    solver, que sí los respeta."""
    from app.services.ai.generator import _repara_desvios_del_banco

    catalogo = _catalogo()
    banco = {"mode": "flexible_7", "slots": [{"slot": 1, "options": [{
        "title": "Huevos con pan",
        # La MITAD del objetivo en todos los ejes: desvío de ESCALA puro (el de
        # composición se deja a propósito sin tocar), así que el cuadre actúa.
        "macros": {"kcal": 350, "protein_g": 20, "carbs_g": 30, "fat_g": 14},
        "ingredients": [
            {"food_id": 1, "name": "Huevo entero", "grams": 110, "household": "2 ud (110 g)"},
            {"food_id": 2, "name": "Pan integral", "grams": 80, "household": "2 ud (80 g)"},
        ],
    }]}]}
    objetivos = {1: {"kcal": 700, "protein_g": 40, "carbs_g": 60, "fat_g": 28}}

    assert _repara_desvios_del_banco(banco, objetivos, catalogo) == 1
    ings = banco["slots"][0]["options"][0]["ingredients"]
    for ing in ings:
        f = catalogo[ing["food_id"]]
        assert ing["grams"] <= f["max_grams"], f"{f['canonical_name']} pasa del tope"
        assert ing["grams"] >= f["min_grams"], f"{f['canonical_name']} baja del suelo"
        # Y la medida casera CUADRA con los gramos (no "4 ud (165 g)" a 55 g/ud).
        casera = str(ing.get("household") or "")
        if " ud (" in casera:
            uds = int(casera.split(" ud")[0])
            assert abs(uds * f["unit_grams"] - ing["grams"]) < 1e-6, casera


def test_sin_catalogo_el_cuadre_sigue_funcionando_como_antes():
    """Un plato con ingredientes libres (sin `food_id`) no puede pasar por el
    solver: se conserva el escalado de siempre."""
    from app.services.ai.generator import _repara_desvios_del_banco

    banco = {"mode": "flexible_7", "slots": [{"slot": 1, "options": [{
        "title": "Plato libre",
        "macros": {"kcal": 300, "protein_g": 20, "carbs_g": 30, "fat_g": 10},
        "ingredients": [{"name": "Algo", "grams": 100}],
    }]}]}
    objetivos = {1: {"kcal": 600, "protein_g": 40, "carbs_g": 60, "fat_g": 20}}

    assert _repara_desvios_del_banco(banco, objetivos, _catalogo()) == 1
    assert banco["slots"][0]["options"][0]["ingredients"][0]["grams"] > 100


def test_un_ingrediente_diminuto_no_se_esfuma_a_cero():
    """El esquema exige `grams > 0`. Con el redondeo a múltiplos de 5 y un
    factor a la baja, un ingrediente de 2 g caía a 0 y el `model_validate` de
    vuelta reventaba: el `except` tiraba EN SILENCIO todas las reparaciones y
    el plan salía retenido por desvíos ya corregidos."""
    from app.services.nutrition_scale import _scale_g

    assert _scale_g(2, 0.4) == 5
    assert _scale_g(1, 0.1) == 5
    assert _scale_g(0, 1.5) == 0        # lo que no pesaba, sigue sin pesar


# ---------------------------------------------------------------------------
# La memoria de vetos (§13) y lo que de verdad aprende
# ---------------------------------------------------------------------------

def test_la_memoria_aprende_lo_que_el_backend_tuvo_que_reparar(tmp_path, monkeypatch):
    """Desde que se REPARA antes de juzgar, los dos tropiezos más repetidos de
    la IA —colar un alérgeno en el banco y no dar en el objetivo de la toma— ya
    no llegan a `check_meal_options`, así que dejaron de emitir `violation:`.
    La memoria solo miraba ese prefijo: dejó de aprenderlos, el prompt no
    advertía, el modelo los repetía y el backend seguía pagando por
    arreglarlos."""
    from app.config import settings
    from app.services.coach_lessons import record_ai_vetos, vetos_reference

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    for _ in range(2):   # se inyecta lo REPETIDO
        record_ai_vetos([
            "seguridad: retiradas 3 opción(es)/alimento(s) con alérgenos del banco",
            "cuadre: 4 plato(s) ajustados al objetivo de su toma (corregido automáticamente)",
        ])
    bloque = vetos_reference()
    assert "alérgeno" in bloque.lower()
    assert "objetivo de su toma" in bloque or "cuadre" in bloque.lower()
    # Y sigue SIN cifras del cliente.
    import re
    assert not re.search(r"\d+\s*(kcal|g\b)", bloque), bloque


def test_el_veto_de_patron_dietetico_no_llega_mutilado_al_prompt(tmp_path, monkeypatch):
    """El texto real del guardrail es «restricción 'vegano' violada: …» y no
    lleva la palabra "patrón": la rama que lo resumía no se activaba nunca y la
    frase caía al limpiador genérico, que se lleva los nombres entrecomillados
    y las cifras y deja un muñón inyectado en la generación de TODOS los
    clientes."""
    from app.services.coach_lessons import _sin_cifras

    real = "violation: restricción 'vegano' violada: slot 2 'tortilla' contiene 'huevo'"
    assert _sin_cifras(real) == "violation: se coló un alimento fuera del patrón dietético"
