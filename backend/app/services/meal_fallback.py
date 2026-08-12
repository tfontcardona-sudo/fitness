"""Opciones de comida por defecto (deterministas) para tomas sin banco.

El método del coach da SIEMPRE al cliente 2-3 opciones cerradas por toma —
nunca una "toma libre" que le complique la vida. Cuando una toma se queda sin
contenido de banco (el coach añade comidas en el editor, la IA omitió un slot,
o el filtrado de alérgenos vació las opciones), estas plantillas se escalan a
los macros objetivo de la toma y se filtran por alergias/aversiones.

Es la red de seguridad determinista: instantánea (sin llamada a IA), segura
(nunca incluye un alérgeno declarado) y coherente (macros del plato ≈ objetivo
del slot). La IA sigue siendo la fuente principal de platos personalizados.
"""

from __future__ import annotations

import unicodedata

from app.services import guardrails as gr

# (alimento, gramos base, macros por 100 g: proteína, hidratos, grasa)
_ING = tuple[str, float, tuple[float, float, float]]

# Plantillas por tipo de toma, calibradas a unas kcal base razonables; después
# se escalan linealmente al objetivo del slot. Varias candidatas por tipo para
# poder descartar las que contengan alérgenos/aversiones y aun así dar 3.
_DESAYUNO: list[tuple[str, list[_ING]]] = [
    ("Yogur griego con avena y fruta",
     [("Yogur griego natural", 200, (9, 4, 10)), ("Copos de avena", 50, (13, 60, 7)),
      ("Plátano", 100, (1, 21, 0.3)), ("Nueces", 10, (15, 7, 65))]),
    ("Tostadas integrales con huevo y pavo",
     [("Pan integral", 80, (9, 43, 3.5)), ("Huevo entero", 110, (12.5, 0.7, 10)),
      ("Pavo en lonchas", 40, (22, 1, 2)), ("Tomate", 100, (1, 3.5, 0.2))]),
    ("Porridge de avena con proteína",
     [("Copos de avena", 60, (13, 60, 7)), ("Leche desnatada", 250, (3.4, 4.8, 0.3)),
      ("Proteína whey", 25, (80, 8, 7)), ("Frutos rojos", 100, (1, 8, 0.3))]),
    ("Revuelto de claras con pan y aguacate",
     [("Claras de huevo", 200, (11, 0.7, 0.2)), ("Huevo entero", 55, (12.5, 0.7, 10)),
      ("Pan integral", 70, (9, 43, 3.5)), ("Aguacate", 50, (2, 2, 15))]),
    ("Batido completo de plátano y cacahuete",
     [("Leche desnatada", 300, (3.4, 4.8, 0.3)), ("Proteína whey", 30, (80, 8, 7)),
      ("Plátano", 120, (1, 21, 0.3)), ("Crema de cacahuete 100%", 15, (25, 12, 50))]),
    ("Tortitas de avena con queso fresco y fruta",
     [("Copos de avena", 60, (13, 60, 7)), ("Claras de huevo", 150, (11, 0.7, 0.2)),
      ("Queso fresco batido 0%", 150, (8, 4, 0.2)), ("Frutos rojos", 100, (1, 8, 0.3))]),
    # Comodines SIN gluten/lactosa/huevo/frutos secos/marisco/soja: garantizan
    # opciones seguras también para el cliente multialérgico (auditoría de perfiles).
    ("Bol salado de arroz con pollo",
     [("Arroz (en crudo)", 60, (7, 78, 0.6)), ("Pechuga de pollo", 120, (22, 0, 2)),
      ("Tomate", 100, (1, 3.5, 0.2)), ("Aceite de oliva virgen extra", 8, (0, 0, 100))]),
    ("Tortitas de arroz con pavo y aguacate",
     [("Tortitas de arroz", 40, (8, 80, 3)), ("Pavo en lonchas", 80, (22, 1, 2)),
      ("Aguacate", 70, (2, 2, 15)), ("Tomate", 80, (1, 3.5, 0.2))]),
    # VEGANAS (patrón dietético): sin producto animal.
    ("Avena con plátano y crema de cacahuete",
     [("Copos de avena", 70, (13, 60, 7)), ("Plátano", 120, (1, 21, 0.3)),
      ("Crema de cacahuete 100%", 20, (25, 12, 50))]),
    ("Tostadas integrales con aguacate y tomate",
     [("Pan integral", 90, (9, 43, 3.5)), ("Aguacate", 80, (2, 2, 15)),
      ("Tomate", 100, (1, 3.5, 0.2)), ("Aceite de oliva virgen extra", 5, (0, 0, 100))]),
]

_SNACK: list[tuple[str, list[_ING]]] = [
    ("Yogur proteico con fruta y nueces",
     [("Yogur proteico natural", 200, (10, 4, 0.2)), ("Manzana", 150, (0.3, 12, 0.2)),
      ("Nueces", 15, (15, 7, 65))]),
    ("Requesón con pan integral y tomate",
     [("Requesón", 120, (12, 4, 4)), ("Pan integral", 50, (9, 43, 3.5)),
      ("Tomate", 90, (1, 3.5, 0.2))]),
    ("Batido de proteína con plátano",
     [("Proteína whey", 30, (80, 8, 7)), ("Leche desnatada", 250, (3.4, 4.8, 0.3)),
      ("Plátano", 100, (1, 21, 0.3))]),
    ("Tortitas de arroz con crema de cacahuete",
     [("Tortitas de arroz", 30, (8, 80, 3)), ("Crema de cacahuete 100%", 20, (25, 12, 50)),
      ("Plátano", 100, (1, 21, 0.3))]),
    ("Queso fresco batido con frutos rojos",
     [("Queso fresco batido 0%", 250, (8, 4, 0.2)), ("Frutos rojos", 120, (1, 8, 0.3)),
      ("Nueces", 10, (15, 7, 65))]),
    ("Pan integral con pavo y queso fresco",
     [("Pan integral", 60, (9, 43, 3.5)), ("Pavo en lonchas", 60, (22, 1, 2)),
      ("Queso fresco batido 0%", 100, (8, 4, 0.2)), ("Tomate", 80, (1, 3.5, 0.2))]),
    # Comodines SIN gluten/lactosa/huevo/frutos secos/marisco/soja (multialérgicos).
    ("Fruta con jamón de pavo",
     [("Manzana", 150, (0.3, 12, 0.2)), ("Plátano", 100, (1, 21, 0.3)),
      ("Pavo en lonchas", 80, (22, 1, 2))]),
    ("Tortitas de arroz con aguacate y tomate",
     [("Tortitas de arroz", 40, (8, 80, 3)), ("Aguacate", 80, (2, 2, 15)),
      ("Tomate", 100, (1, 3.5, 0.2))]),
    # VEGANA (patrón dietético): sin producto animal.
    ("Hummus con tortitas de arroz",
     [("Hummus", 120, (8, 15, 10)), ("Tortitas de arroz", 35, (8, 80, 3)),
      ("Manzana", 120, (0.3, 12, 0.2))]),
]

_PRINCIPAL: list[tuple[str, list[_ING]]] = [
    ("Pollo con arroz y verduras",
     [("Pechuga de pollo", 180, (22, 0, 2)), ("Arroz (en crudo)", 80, (7, 78, 0.6)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Merluza con patata y verduras",
     [("Merluza", 220, (16, 0, 1.8)), ("Patata (en crudo)", 350, (2, 17, 0.1)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 12, (0, 0, 100))]),
    ("Ternera magra con pasta y verduras",
     [("Ternera magra", 170, (21, 0, 5)), ("Pasta (en crudo)", 80, (12, 71, 1.5)),
      ("Verduras variadas", 180, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Salmón con quinoa y verduras",
     [("Salmón", 160, (20, 0, 12)), ("Quinoa (en crudo)", 70, (14, 64, 6)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 5, (0, 0, 100))]),
    ("Huevos con pan integral y aguacate",
     [("Huevo entero", 165, (12.5, 0.7, 10)), ("Claras de huevo", 100, (11, 0.7, 0.2)),
      ("Pan integral", 90, (9, 43, 3.5)), ("Aguacate", 70, (2, 2, 15)),
      ("Tomate", 100, (1, 3.5, 0.2))]),
    ("Pavo salteado con cuscús y verduras",
     [("Pechuga de pavo", 180, (22, 0, 1.5)), ("Cuscús (en crudo)", 75, (13, 72, 1)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Atún con boniato y verduras",
     [("Atún fresco", 170, (23, 0, 5)), ("Boniato (en crudo)", 300, (1.5, 21, 0.2)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 8, (0, 0, 100))]),
    # Comodines SIN pescado/marisco/gluten/lactosa/huevo/frutos secos/soja:
    # garantizan ≥3 opciones seguras también con aversión a pescado o multialergia
    # (hallazgo de la auditoría de perfiles: quien odiaba el pescado recibía
    # merluza/salmón en B/C y el Revisor 0 vetaba el plan entero).
    ("Pollo con patata y verduras",
     [("Pechuga de pollo", 180, (22, 0, 2)), ("Patata (en crudo)", 320, (2, 17, 0.1)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Ternera magra con arroz y verduras",
     [("Ternera magra", 170, (21, 0, 5)), ("Arroz (en crudo)", 75, (7, 78, 0.6)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 8, (0, 0, 100))]),
    ("Pavo con boniato y verduras",
     [("Pechuga de pavo", 180, (22, 0, 1.5)), ("Boniato (en crudo)", 280, (1.5, 21, 0.2)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    # VEGANAS (patrón dietético): legumbre + tubérculo/cereal, sin producto animal.
    ("Garbanzos salteados con arroz y verduras",
     [("Garbanzos cocidos", 250, (8, 19, 2.5)), ("Arroz (en crudo)", 60, (7, 78, 0.6)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Lentejas estofadas con patata y verduras",
     [("Lentejas cocidas", 280, (9, 16, 0.5)), ("Patata (en crudo)", 250, (2, 17, 0.1)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
    ("Tofu salteado con arroz y verduras",
     [("Tofu firme", 200, (13, 2, 8)), ("Arroz (en crudo)", 70, (7, 78, 0.6)),
      ("Verduras variadas", 200, (2, 5, 0.3)), ("Aceite de oliva virgen extra", 10, (0, 0, 100))]),
]


def _meal_kind(name: str | None) -> list[tuple[str, list[_ING]]]:
    n = (name or "").lower()
    n = "".join(c for c in unicodedata.normalize("NFD", n) if not unicodedata.combining(c))
    if "desayun" in n:
        return _DESAYUNO
    # "Recena" (toma pequeña antes de dormir) ANTES que "cena": contiene la
    # subcadena y se clasificaba como principal — sus opciones salían 600-900
    # kcal para una toma del 10 % del día (hallazgo de la revisión).
    if "recena" in n:
        return _SNACK
    if "comida" in n or "cena" in n or "almuerzo" in n:
        return _PRINCIPAL
    return _SNACK


def _ing_cap_g(food: str) -> float:
    """Tope de ración por ingrediente, espejo del guardarraíl de porciones
    (PORTION_SOLID_ABSURD_G / huevos): el banco jamás debe fabricar una opción
    que el Revisor 0 vete por 'porción irreal'."""
    from app.services.guardrails import (
        PORTION_EGG_ABSURD, PORTION_SOLID_ABSURD_G, _LIQUID_HINTS, _norm_food,
    )
    n = _norm_food(food)
    if "huevo" in n:
        return (PORTION_EGG_ABSURD * 55) - 5  # margen bajo el umbral
    if any(h in n for h in _LIQUID_HINTS):
        return 1000.0
    return PORTION_SOLID_ABSURD_G - 50  # margen para el redondeo a 5 g


def _scaled_option(key: str, title: str, ings: list[_ING], target_kcal: float) -> dict:
    base_kcal = sum(g * (4 * p + 4 * c + 9 * f) / 100 for _, g, (p, c, f) in ings)
    ratio = target_kcal / base_kcal if base_kcal > 0 and target_kcal > 0 else 1.0
    ratio = max(0.4, min(3.0, ratio))
    from app.services.nutrition_scale import _rhu  # half-up: convenio del sistema

    # Escalado con TOPE por ingrediente: lo que no cabe en uno (p. ej. >650 g de
    # patata) se redistribuye en kcal entre los que aún tienen margen, para que
    # la opción siga acercándose al objetivo sin porciones absurdas.
    dens = [(4 * p + 4 * c + 9 * f) / 100 for _, _, (p, c, f) in ings]  # kcal/g
    caps = [_ing_cap_g(food) for food, _, _ in ings]
    grams = [g * ratio for _, g, _ in ings]
    lost_kcal = 0.0
    for k in range(len(grams)):
        if grams[k] > caps[k]:
            lost_kcal += (grams[k] - caps[k]) * dens[k]
            grams[k] = caps[k]
    if lost_kcal > 1:
        room = [max(0.0, caps[k] - grams[k]) * dens[k] for k in range(len(grams))]
        total_room = sum(room)
        if total_room > 0:
            take = min(lost_kcal, total_room)
            for k in range(len(grams)):
                if room[k] > 0 and dens[k] > 0:
                    grams[k] += (take * room[k] / total_room) / dens[k]

    out_ings, tp, tc, tf = [], 0.0, 0.0, 0.0
    for (food, _g, (p, c, f)), g_final in zip(ings, grams):
        g_r = max(5, _rhu(g_final / 5) * 5)
        out_ings.append({"food": food, "grams": g_r, "household": ""})
        tp += g_r * p / 100
        tc += g_r * c / 100
        tf += g_r * f / 100
    # UNA SOLA VERDAD: las kcal declaradas son EXACTAMENTE 4/4/9 de los macros
    # declarados (ya redondeados). Antes se redondeaban por separado y la opción
    # nacía con un descuadre Atwater de ±7 kcal que vetaba el Revisor 0.
    p_r, c_r, f_r = _rhu(tp), _rhu(tc), _rhu(tf)
    return {
        "key": key, "title": title, "prep": "", "prep_minutes": 10,
        "ingredients": out_ings,
        "macros": {"kcal": 4 * p_r + 4 * c_r + 9 * f_r,
                   "protein_g": p_r, "carbs_g": c_r, "fat_g": f_r},
        "tags": [],
    }


def _violates_pattern(opt: dict, diet_pattern: str | None) -> bool:
    if not diet_pattern:
        return False
    forbidden = gr._DIET_PATTERN_FORBIDDEN.get(
        gr._norm_food(diet_pattern).replace(" ", "_"))
    if not forbidden:
        return False
    return gr._match_term(forbidden, gr._all_option_texts(opt)) is not None


def build_fallback_options(meal: dict, allergies: list[str] | None = None,
                           dislikes: list[str] | None = None,
                           diet_pattern: str | None = None) -> list[dict]:
    """Hasta 3 opciones cerradas (clave A/B/C) escaladas al objetivo de la toma.

    Alergias Y aversiones EXCLUYEN candidatas siempre: el Revisor 0
    (`validate_plan_deterministic`) veta ambas, así que colar una aversión "para
    llegar a 3" bloqueaba el plan entero (hallazgo de la auditoría de perfiles).
    Mejor 1-2 opciones seguras que 3 con una vetada. Si ninguna candidata es
    segura (caso extremo), devuelve lista vacía y el caller avisa al coach.
    """
    target = meal.get("target") or {}
    kcal = float(target.get("kcal") or 0) or (
        4 * float(target.get("protein_g") or 0) + 4 * float(target.get("carbs_g") or 0)
        + 9 * float(target.get("fat_g") or 0)
    )
    candidates = _meal_kind(meal.get("name"))
    scaled = [_scaled_option("?", t, ings, kcal) for t, ings in candidates]
    safe = [o for o in scaled
            if gr.option_allergen(o, allergies) is None
            and gr.option_allergen(o, dislikes) is None
            and not _violates_pattern(o, diet_pattern)]
    chosen = safe[:3]
    for i, o in enumerate(chosen):
        o["key"] = chr(ord("A") + i)
    return chosen


def _slot_is_empty(entry: dict | None) -> bool:
    if not isinstance(entry, dict):
        return True
    if entry.get("options"):
        return False
    eq = entry.get("equivalences") or {}
    return not (isinstance(eq, dict) and eq.get("groups"))


def ensure_bank_slots(nut: dict, allergies: list[str] | None = None,
                      dislikes: list[str] | None = None,
                      diet_pattern: str | None = None) -> int:
    """Garantiza que TODAS las tomas del plan flexible tengan contenido de banco.

    Para cada comida sin entrada (o con entrada vacía) inyecta 3 opciones por
    defecto escaladas a sus macros. No toca el modo estricto (menú cerrado) ni
    las tomas que ya tienen opciones/equivalencias. Devuelve cuántas rellenó.
    """
    if not isinstance(nut, dict):
        return 0
    meals = [m for m in (nut.get("meals") or []) if isinstance(m, dict)]
    if not meals:
        return 0
    bank = nut.get("meal_bank")
    if isinstance(bank, dict) and bank.get("mode") == "strict":
        return 0
    if not isinstance(bank, dict):
        bank = {"mode": "flexible_7", "slots": []}
        nut["meal_bank"] = bank
    slots = bank.setdefault("slots", [])
    by_slot = {s.get("slot"): s for s in slots if isinstance(s, dict)}
    filled = 0
    for m in meals:
        slot_no = m.get("slot")
        entry = by_slot.get(slot_no)
        if not _slot_is_empty(entry):
            continue
        options = build_fallback_options(m, allergies=allergies, dislikes=dislikes,
                                          diet_pattern=diet_pattern)
        if not options:
            continue
        titles = [o["title"] for o in options]
        new_entry = {
            "slot": slot_no, "fmt": "options", "options": options,
            "weekly_examples": [titles[i % len(titles)] for i in range(7)],
        }
        if entry is None:
            slots.append(new_entry)
            slots.sort(key=lambda s: (s.get("slot") is None, s.get("slot")))
        else:
            entry.update(new_entry)
        filled += 1
    return filled
