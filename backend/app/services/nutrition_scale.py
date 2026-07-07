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


def kcal_of(p: float, c: float, f: float) -> int:
    return round(p * 4 + c * 4 + f * 9)


def macros_for_kcal(goal: str | None, weight_kg: float, kcal: float) -> dict:
    """Macros óptimos para unas kcal: proteína (punto medio del rango por
    evidencia) y grasa por kg; carbohidratos = el resto (grasa cede hasta su
    suelo de 0,6 g/kg si no caben)."""
    lo, hi = PROTEIN_RANGE.get(goal or "", (1.8, 2.2))
    protein = round(weight_kg * (lo + hi) / 2)
    fat = round(weight_kg * FAT_PER_KG.get(goal or "", 0.9))
    fat_min = round(weight_kg * 0.6)
    carbs = round((kcal - protein * 4 - fat * 9) / 4)
    if carbs < 0:
        fat = max(fat_min, round((kcal - protein * 4) / 9))
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

    def scale_dish(o: dict) -> None:
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

    def scale_equivalences(eq: dict) -> None:
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

    bank = copy.deepcopy(base.get("meal_bank") or None)
    if bank:
        if bank.get("mode") == "flexible_7":
            for slot in bank.get("slots") or []:
                for o in slot.get("options") or []:
                    scale_dish(o)
                scale_equivalences(slot.get("equivalences") or {})
        elif bank.get("mode") == "strict":
            for d in bank.get("days") or []:
                for m in d.get("meals") or []:
                    scale_dish(m.get("dish") or {})
        nut["meal_bank"] = bank
