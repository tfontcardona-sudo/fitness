"""Coherencia y reescalado de la nutrición del plan (espejo del frontend
`lib/nutritionTargets.ts` — cambiar ambos a la vez).

Cuando un ajuste toca calorías o macros, TODO el plan debe moverse en bloque:
- calorías ⇄ macros coherentes (4/4/9; proteína y grasa por kg según el
  objetivo con la evidencia de services/metrics.py),
- objetivos de cada comida reescalados eje a eje,
- banco de comidas: macros de cada opción + GRAMOS de cada ingrediente
  (múltiplos de 5 g para que las raciones sean cocinables).

Lo usa la ADAPTACIÓN quincenal: antes solo cambiaba los totales y el PDF se
quedaba con los gramos antiguos.
"""

from __future__ import annotations

import copy
import re

from app.services.metrics import PROTEIN_RANGE

# Grasa por kg por objetivo (mismo criterio que el frontend); suelo 0,6 g/kg.
FAT_PER_KG = {
    "fat_loss": 0.8, "muscle_gain": 0.9, "recomp": 0.9,
    "maintenance": 1.0, "injury_recovery": 1.0,
}

# Topes de ajuste calórico respecto al TDEE (ESPEJO de lib/nutritionTargets.ts).
MAX_DEFICIT_PCT = 30
MAX_SURPLUS_PCT = 15


def kcal_of(p: float, c: float, f: float) -> int:
    return round(p * 4 + c * 4 + f * 9)


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def clamp_targets(nut: dict, weight_kg: float | None = None) -> None:
    """Topes FISIOLÓGICOS de los objetivos (defensa ante ediciones absurdas):
    un dedo de más en el editor (CH 800 g, grasa 0 g, +77% de superávit) no
    puede convertirse en un plan real. Se aplican ANTES de reconciliar, así
    cualquier camino (editor, adaptación, generación) queda protegido:
      - proteína entre 1,2 y 3,0 g/kg (sin peso: 60–280 g),
      - grasa entre 0,6 y 2,0 g/kg con suelo absoluto 20 g (sin peso: 20–160 g),
      - calorías dentro de [TDEE−30%, TDEE+15%] si hay TDEE (los mismos topes
        que ofrece el selector del editor); siempre dentro de 1100–4500 kcal.
    Muta `nut`. Idempotente sobre valores ya sanos."""
    if not isinstance(nut, dict):
        return
    m = nut.get("macros")
    if not isinstance(m, dict):
        return
    w = float(weight_kg) if isinstance(weight_kg, (int, float)) and weight_kg else 0.0
    p_lo, p_hi = (round(w * 1.2), round(w * 3.0)) if w else (60, 280)
    f_lo, f_hi = (max(20, round(w * 0.6)), round(w * 2.0)) if w else (20, 160)

    if isinstance(m.get("protein_g"), (int, float)):
        m["protein_g"] = round(_clamp(float(m["protein_g"]), p_lo, p_hi))
    if isinstance(m.get("fat_g"), (int, float)):
        m["fat_g"] = round(_clamp(float(m["fat_g"]), f_lo, f_hi))
    if isinstance(m.get("carbs_g"), (int, float)) and m["carbs_g"] < 0:
        m["carbs_g"] = 0

    tdee = nut.get("tdee_kcal")
    if isinstance(tdee, (int, float)) and tdee > 0:
        k_lo = max(1100.0, tdee * (1 - MAX_DEFICIT_PCT / 100))
        k_hi = min(4500.0, tdee * (1 + MAX_SURPLUS_PCT / 100))
    else:
        k_lo, k_hi = 1100.0, 4500.0
    if k_lo > k_hi:  # TDEE extremo/corrupto: manda el rango absoluto
        k_lo, k_hi = 1100.0, 4500.0
    target = nut.get("target_kcal")
    if isinstance(target, (int, float)) and target > 0:
        nut["target_kcal"] = round(_clamp(float(target), k_lo, k_hi))
    else:
        # Sin objetivo declarado: el implícito (suma de macros) también se acota.
        implicit = kcal_of(float(m.get("protein_g") or 0), float(m.get("carbs_g") or 0),
                           float(m.get("fat_g") or 0))
        if implicit > 0:
            nut["target_kcal"] = round(_clamp(float(implicit), k_lo, k_hi))


def reconcile_nutrition(nut: dict, weight_kg: float | None = None, *,
                        clamp: bool = True) -> dict:
    """Deja la nutrición internamente COHERENTE — una sola verdad numérica que
    todos los apartados (resumen energético, macros, estructura diaria, PDF y
    portal) comparten. Es la pieza que evita "aquí pone X kcal y allí otro número":

      1) target_kcal ≡ suma de macros (4/4/9): se conserva la proteína y la grasa
         (ancladas al objetivo por la IA/coach) y los carbohidratos hacen de
         colchón; si no caben, cede la grasa hasta su suelo (0,6 g/kg) y luego la
         proteína (1,6 g/kg). Después target_kcal se fija EXACTA a esa suma.
      2) Σ(objetivo de cada comida) ≡ totales, eje por eje: los objetivos por
         comida se reparten en proporción al plan y el redondeo restante va a la
         comida mayor; las kcal de cada comida se recalculan de sus macros, así
         cada comida cuadra sola y la suma cuadra con el total.

    Además: 0) aplica TOPES fisiológicos a los objetivos (clamp_targets) y
    3) reescala el BANCO de comidas por los mismos ratios que las comidas —
    así CUALQUIER camino de edición deja también el recetario/equivalencias
    en armonía con los totales (no solo los caminos que ya reescalaban).

    Idempotente: sobre datos ya coherentes no cambia nada. Muta y devuelve `nut`.
    """
    if not isinstance(nut, dict):
        return nut
    # `clamp=False` SOLO en la generación IA antes de los guardrails: ellos son
    # la autoridad que BLOQUEA una salida peligrosa (corregirla en silencio la
    # ocultaría). Las ediciones del coach y la adaptación sí se acotan.
    if clamp:
        clamp_targets(nut, weight_kg)
    macros = nut.get("macros")
    meals = [m for m in (nut.get("meals") or []) if isinstance(m, dict)]

    # --- 1) target_kcal ⇄ macros ------------------------------------------------
    target = nut.get("target_kcal")
    target = float(target) if isinstance(target, (int, float)) and target > 0 else 0.0

    if not isinstance(macros, dict) or not macros:
        # Sin macros: dedúcelos de la suma de las comidas (plan antiguo/parcial).
        if meals:
            p = sum(float((m.get("target") or {}).get("protein_g") or 0) for m in meals)
            c = sum(float((m.get("target") or {}).get("carbs_g") or 0) for m in meals)
            f = sum(float((m.get("target") or {}).get("fat_g") or 0) for m in meals)
            macros = {"protein_g": round(p), "carbs_g": round(c), "fat_g": round(f)}
            nut["macros"] = macros
        else:
            return nut  # nada que cuadrar

    p = float(macros.get("protein_g") or 0)
    f = float(macros.get("fat_g") or 0)
    c = float(macros.get("carbs_g") or 0)

    if target <= 0:
        # Sin objetivo declarado: el objetivo ES la suma de los macros que hay.
        target = float(kcal_of(p, c, f))

    # Carbohidratos = colchón para que P·4 + C·4 + G·9 == target.
    c = round((target - p * 4 - f * 9) / 4)
    if c < 0:
        # 1º baja la grasa hasta su suelo saludable
        fat_min = round((weight_kg or 0) * 0.6)
        f = max(fat_min, round((target - p * 4) / 9))
        c = round((target - p * 4 - f * 9) / 4)
    if c < 0:
        # 2º recorta la proteína hasta su suelo de preservación de masa
        protein_min = round((weight_kg or 0) * 1.6)
        p = max(protein_min, round((target - f * 9) / 4))
        c = max(0, round((target - p * 4 - f * 9) / 4))

    p, c, f = round(p), round(c), round(f)
    nut["macros"] = {**macros, "protein_g": p, "carbs_g": c, "fat_g": f}
    # Una sola verdad: el objetivo declarado ES exactamente la suma de sus macros.
    nut["target_kcal"] = kcal_of(p, c, f)

    # --- 2) objetivos por comida ⇄ totales -------------------------------------
    if not meals:
        return nut
    with_target = [m for m in meals if isinstance(m.get("target"), dict)]
    if not with_target:
        return nut

    # Sumas ANTES de repartir: son la base sobre la que está construido el banco
    # de comidas. Los ratios (totales nuevos / base) reescalan el banco después.
    def _pre_sum(axis: str) -> float:
        return sum(float(m["target"].get(axis) or 0) for m in with_target)

    pre_k, pre_p, pre_c, pre_f = (_pre_sum("kcal"), _pre_sum("protein_g"),
                                  _pre_sum("carbs_g"), _pre_sum("fat_g"))

    def _distribute(axis: str, total: int) -> None:
        vals = [float(m["target"].get(axis) or 0) for m in with_target]
        cur = sum(vals)
        if cur > 0:
            r = total / cur
            for m in with_target:
                m["target"][axis] = max(0, round(float(m["target"].get(axis) or 0) * r))
        elif total > 0:
            # La IA no repartió este eje: dáselo entero a la primera comida.
            for i, m in enumerate(with_target):
                m["target"][axis] = total if i == 0 else 0
        # Ajuste del redondeo a la comida mayor de este eje (suma EXACTA).
        diff = total - sum(int(m["target"].get(axis) or 0) for m in with_target)
        if diff:
            biggest = max(with_target, key=lambda m: m["target"].get(axis) or 0)
            biggest["target"][axis] = max(0, int(biggest["target"].get(axis) or 0) + diff)

    _distribute("protein_g", p)
    _distribute("carbs_g", c)
    _distribute("fat_g", f)
    # Las kcal de cada comida salen de SUS macros → cada comida cuadra sola y,
    # como kcal_of es lineal, la suma cuadra con target_kcal sin más ajustes.
    for m in with_target:
        t = m["target"]
        t["kcal"] = kcal_of(
            float(t.get("protein_g") or 0), float(t.get("carbs_g") or 0), float(t.get("fat_g") or 0)
        )

    # --- 3) banco de comidas ⇄ totales ------------------------------------------
    # Si las comidas se han movido (los totales nuevos difieren de la base sobre
    # la que estaba construido el banco), el recetario y las equivalencias se
    # reescalan por los MISMOS ratios — el PDF y el portal nunca quedan con
    # cantidades de otra versión. Con datos coherentes, ratios ≈ 1 → no-op.
    bank = nut.get("meal_bank")
    if isinstance(bank, dict):
        target_k = float(nut.get("target_kcal") or 0)
        r_k = (target_k / pre_k) if pre_k > 0 else 1.0
        r_p = (p / pre_p) if pre_p > 0 else 1.0
        r_c = (c / pre_c) if pre_c > 0 else 1.0
        r_f = (f / pre_f) if pre_f > 0 else 1.0
        if any(abs(r - 1.0) > 0.01 for r in (r_k, r_p, r_c, r_f)):
            scale_bank(bank, r_k, r_p, r_c, r_f)
    return nut


def macros_for_kcal(goal: str | None, weight_kg: float, kcal: float) -> dict:
    """Macros óptimos para unas kcal: proteína (punto medio del rango por
    evidencia) y grasa por kg; carbohidratos = el resto (grasa cede hasta su
    suelo de 0,6 g/kg si no caben)."""
    lo, hi = PROTEIN_RANGE.get(goal or "", (1.8, 2.2))
    protein = round(weight_kg * (lo + hi) / 2)
    fat = round(weight_kg * FAT_PER_KG.get(goal or "", 0.9))
    fat_min = round(weight_kg * 0.6)
    protein_min = round(weight_kg * 1.6)
    carbs = round((kcal - protein * 4 - fat * 9) / 4)
    if carbs < 0:
        fat = max(fat_min, round((kcal - protein * 4) / 9))
        carbs = round((kcal - protein * 4 - fat * 9) / 4)
    if carbs < 0:
        # proteína+grasa mínimas superan las kcal: recorta la proteína a su suelo
        # para que los macros no declaren unas kcal que no cumplen.
        protein = max(protein_min, round((kcal - fat * 9) / 4))
        carbs = max(0, round((kcal - protein * 4 - fat * 9) / 4))
    return {"kcal": round(kcal), "protein_g": protein, "carbs_g": carbs, "fat_g": fat}


def macros_scaled_to_kcal(base_nut: dict, kcal: float) -> dict:
    """Al cambiar SOLO las calorías, los TRES macros suben/bajan EN PROPORCIÓN
    al mix del plan (la dieta ya está adaptada al cliente; no se re-ancla por
    kg): P y G escalan por el ratio y los carbohidratos cuadran el 4/4/9.
    Espejo de `macrosScaledToKcal` en frontend lib/nutritionTargets.ts."""
    m = (base_nut or {}).get("macros") or {}
    p0 = m.get("protein_g") or 0
    c0 = m.get("carbs_g") or 0
    f0 = m.get("fat_g") or 0
    old = kcal_of(p0, c0, f0) or (base_nut or {}).get("target_kcal") or kcal
    r = (kcal / old) if old else 1.0
    protein = round(p0 * r)
    fat = round(f0 * r)
    carbs = max(0, round((kcal - protein * 4 - fat * 9) / 4))
    return {"kcal": round(kcal), "protein_g": protein, "carbs_g": carbs, "fat_g": fat}


def _scale(v, f: float):
    return round(v * f) if isinstance(v, (int, float)) else v


def _scale_g(v, f: float):
    """Gramos de ingrediente: reescala y redondea a múltiplos de 5."""
    return max(0, round(v * f / 5) * 5) if isinstance(v, (int, float)) else v


def _scale_amount_text(text, f: float):
    """Reescala las cantidades DENTRO de un texto de equivalencias
    ("140 g crudo = 380 g cocido" → ambos números). Solo toca números con
    unidad de peso/volumen (g/gr/ml); '2 huevos' o '1 taza' se quedan igual.
    Redondea a múltiplos de 5 a partir de 25 (raciones cocinables)."""
    if not isinstance(text, str) or f == 1.0:
        return text

    def repl(m):
        val = float(m.group(1).replace(",", "."))
        scaled = val * f
        scaled = round(scaled / 5) * 5 if scaled >= 25 else max(1, round(scaled))
        return f"{int(scaled)} {m.group(2)}"

    return re.sub(r"(\d+(?:[.,]\d+)?)\s*(g|gr|ml)\b", repl, text)


def _equiv_ratio(group_name, r_k: float, r_p: float, r_c: float, r_f: float) -> float:
    """Ratio del eje que corresponde a un grupo de equivalencias por su nombre."""
    n = (group_name or "").lower()
    if "prote" in n:
        return r_p
    if "gras" in n:
        return r_f
    if any(k in n for k in ("hidrat", "carb", "cereal", "almid", "frut")):
        return r_c
    return r_k


def _scale_dish(o: dict, r_k: float, r_p: float, r_c: float, r_f: float) -> None:
    if not o:
        return
    mm = o.get("macros")
    if mm:
        o["macros"] = {**mm, "kcal": _scale(mm.get("kcal"), r_k),
                       "protein_g": _scale(mm.get("protein_g"), r_p),
                       "carbs_g": _scale(mm.get("carbs_g"), r_c),
                       "fat_g": _scale(mm.get("fat_g"), r_f)}
    for ing in o.get("ingredients") or []:
        ing["grams"] = _scale_g(ing.get("grams"), r_k)
        # La medida casera ("1 taza ≈ 80 g") también lleva gramos dentro
        ing["household"] = _scale_amount_text(ing.get("household"), r_k)


def _scale_equivalences(eq: dict, r_k: float, r_p: float, r_c: float, r_f: float) -> None:
    """Sistema de equivalencias (comida/cena): las cantidades van en TEXTO
    ("140 g crudo = 380 g cocido") — cada grupo escala por SU eje (proteína,
    hidratos, grasas…) para que el PDF salga en armonía con los macros."""
    if not eq:
        return
    eq["intro"] = _scale_amount_text(eq.get("intro"), r_c)
    for g in eq.get("groups") or []:
        r = _equiv_ratio(g.get("name"), r_k, r_p, r_c, r_f)
        g["note"] = _scale_amount_text(g.get("note"), r)
        for it in g.get("items") or []:
            it["amount"] = _scale_amount_text(it.get("amount"), r)


def scale_bank(bank: dict, r_k: float, r_p: float, r_c: float, r_f: float) -> None:
    """Reescala el banco de comidas entero (opciones, gramos y equivalencias)
    por los ratios de cada eje. Muta `bank`."""
    if not bank:
        return
    if bank.get("mode") == "flexible_7":
        for slot in bank.get("slots") or []:
            for o in slot.get("options") or []:
                _scale_dish(o, r_k, r_p, r_c, r_f)
            _scale_equivalences(slot.get("equivalences") or {}, r_k, r_p, r_c, r_f)
    elif bank.get("mode") == "strict":
        for d in bank.get("days") or []:
            for m in d.get("meals") or []:
                _scale_dish(m.get("dish") or {}, r_k, r_p, r_c, r_f)


def rescale_nutrition(nut: dict, base: dict, kcal: float, protein_g: float,
                      carbs_g: float, fat_g: float) -> None:
    """Fija los totales nuevos en `nut` y reescala comidas y banco tomando como
    referencia los totales de `base` (la nutrición ORIGINAL, no la mutada)."""
    b_k = (base.get("target_kcal") or 0)
    b_m = base.get("macros") or {}
    ratio = lambda a, b: (a / b) if b else 1.0
    r_k = ratio(kcal, b_k)
    r_p = ratio(protein_g, b_m.get("protein_g") or 0)
    r_c = ratio(carbs_g, b_m.get("carbs_g") or 0)
    r_f = ratio(fat_g, b_m.get("fat_g") or 0)

    nut["target_kcal"] = round(kcal)
    nut["macros"] = {**(nut.get("macros") or {}),
                     "protein_g": round(protein_g), "carbs_g": round(carbs_g),
                     "fat_g": round(fat_g)}

    # Objetivos por comida: cada eje por su ratio (los totales cuadran)
    base_meals = base.get("meals") or []
    meals = copy.deepcopy(base_meals)
    for m in meals:
        t = m.get("target")
        if not t:
            continue
        m["target"] = {**t, "kcal": _scale(t.get("kcal"), r_k),
                       "protein_g": _scale(t.get("protein_g"), r_p),
                       "carbs_g": _scale(t.get("carbs_g"), r_c),
                       "fat_g": _scale(t.get("fat_g"), r_f)}
    # Resto de redondeo a la comida mayor de cada eje: la suma de las comidas
    # CUADRA EXACTA con los totales (sin deriva al encadenar adaptaciones).
    for key, total in (("kcal", kcal), ("protein_g", protein_g),
                       ("carbs_g", carbs_g), ("fat_g", fat_g)):
        with_t = [m["target"] for m in meals
                  if m.get("target") and isinstance(m["target"].get(key), (int, float))]
        if with_t:
            diff = round(total) - sum(t[key] for t in with_t)
            if diff:
                biggest = max(with_t, key=lambda t: t[key])
                biggest[key] = max(0, biggest[key] + diff)
    if meals:
        nut["meals"] = meals

    bank = copy.deepcopy(base.get("meal_bank") or None)
    if bank:
        scale_bank(bank, r_k, r_p, r_c, r_f)
        nut["meal_bank"] = bank
