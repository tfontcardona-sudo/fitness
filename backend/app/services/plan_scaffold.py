"""Plan BASE determinista para clientes AVANZADOS — 0 llamadas a la IA.

Al cliente avanzado la planificación se la hace el COACH, pero no desde cero:
este módulo prepara un borrador COMPLETO y válido con todo lo que el sistema
sabe calcular sin IA:

  - Objetivos calóricos y reparto de macros (metrics.energy_targets +
    macro_targets — la única verdad numérica del sistema).
  - Comidas con su horario y su target por toma (reparto estándar que suma
    EXACTO el total del día, criterio del Revisor 0).
  - Banco de comidas determinista (meal_fallback + base de alimentos), con
    alérgenos/aversiones/patrón dietético respetados.
  - Sesiones de entrenamiento montadas desde la biblioteca FILTRADA
    (guardrails), con series/repes/RIR/descansos y progresión estándar.

El resultado pasa por los MISMOS contratos Pydantic que la salida de la IA
(NutritionCore/TrainingCore): el editor y el portal no distinguen su origen.
El coach lo repasa en el editor, cambia lo que quiera y lo activa.
"""

from app.schemas.ai import NutritionCore, TrainingCore
from app.services.metrics import _rhu

# ------------------------------------------------------------- nutrición ----

# Reparto estándar del día por número de comidas (suma 100), ALINEADO
# posición a posición con _MEAL_NAMES: la comida principal (14:00) es siempre
# la mayor y los tentempiés (media mañana/merienda/recena) los menores. El
# coach lo ajustará: es un punto de partida razonable, no un dogma.
_MEAL_WEIGHTS: dict[int, list[int]] = {
    2: [45, 55],
    3: [30, 40, 30],
    4: [25, 35, 15, 25],
    #   Desayuno, Media mañana, Comida, Merienda, Cena(, Recena)
    5: [20, 10, 35, 10, 25],
    6: [20, 10, 30, 10, 20, 10],
}

_MEAL_NAMES: dict[int, list[tuple[str, str]]] = {
    2: [("Comida", "14:00"), ("Cena", "21:00")],
    3: [("Desayuno", "08:00"), ("Comida", "14:00"), ("Cena", "21:00")],
    4: [("Desayuno", "08:00"), ("Comida", "14:00"), ("Merienda", "17:30"),
        ("Cena", "21:00")],
    5: [("Desayuno", "08:00"), ("Media mañana", "11:00"), ("Comida", "14:00"),
        ("Merienda", "17:30"), ("Cena", "21:00")],
    6: [("Desayuno", "08:00"), ("Media mañana", "11:00"), ("Comida", "14:00"),
        ("Merienda", "17:30"), ("Cena", "21:00"), ("Recena", "23:00")],
}


def _meal_slots(client) -> list[tuple[int, str, str]]:
    """(slot, nombre, hora) de cada comida: el horario declarado del cliente si
    existe; si no, un reparto estándar por su nº de comidas (por defecto 4).

    SANEO: la lectura IA de un PDF manuscrito puede dejar meal_schedule con
    slots duplicados, a 0 o negativos — se ordenan de forma estable por el slot
    declarado y se RENUMERAN 1..N (ninguna toma se pierde y el contrato
    NutritionCore, que exige slots únicos ascendentes, nunca revienta)."""
    schedule = client.meal_schedule or []
    declared: list[tuple[float, str, str]] = []
    for i, item in enumerate(schedule):
        if not isinstance(item, dict):
            continue
        raw = item.get("slot")
        orden = float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else float(i + 1)
        declared.append((orden, str(item.get("name") or f"Comida {i + 1}"),
                         str(item.get("time") or "12:00")))
    if declared:
        declared.sort(key=lambda s: s[0])
        return [(i + 1, name, time) for i, (_o, name, time) in enumerate(declared)]
    n = client.meals_per_day or 4
    n = min(6, max(2, int(n)))
    return [(i + 1, name, time) for i, (name, time) in enumerate(_MEAL_NAMES[n])]


def build_nutrition(client, energy, macros) -> dict:
    """NutritionCore determinista: targets del día repartidos por toma con SUMA
    EXACTA — el residuo del redondeo cae en la comida de MAYOR peso (la
    principal), que es la que mejor lo absorbe (criterio Σ comidas = día del
    Revisor 0). `energy` es EnergyTargets; `macros`, MacroPlan."""
    slots = _meal_slots(client)
    weights = _MEAL_WEIGHTS.get(len(slots)) or [round(100 / len(slots))] * len(slots)
    # Si el nº de comidas declarado no casa con la tabla, normaliza pesos.
    if len(weights) != len(slots):
        weights = [round(100 / len(slots))] * len(slots)

    total_p, total_c, total_f = macros.protein_g, macros.carbs_g, macros.fat_g
    grams = [[_rhu(total_p * w / 100), _rhu(total_c * w / 100),
              _rhu(total_f * w / 100)] for w in weights]
    # Residuo del redondeo → la toma de mayor peso (absorbe también residuos
    # negativos sin dejar ninguna toma a cero).
    principal = max(range(len(weights)), key=lambda i: weights[i])
    grams[principal][0] += total_p - sum(g[0] for g in grams)
    grams[principal][1] += total_c - sum(g[1] for g in grams)
    grams[principal][2] += total_f - sum(g[2] for g in grams)

    meals = []
    for (slot, name, time), (p, c, f) in zip(slots, grams):
        meals.append({
            "slot": slot, "name": name, "time": time,
            "target": {"kcal": 4 * p + 4 * c + 9 * f,
                       "protein_g": p, "carbs_g": c, "fat_g": f},
        })

    nut = {
        "tdee_kcal": round(energy.tdee, 1),
        "target_kcal": float(macros.kcal),
        # OJO: `rationale` lo LEE EL CLIENTE (sale en el PDF como nota del
        # ajuste). Nada de instrucciones para el coach aquí — las notas de
        # trabajo van en guardrail_flags, que solo ve el panel.
        "rationale": (
            f"Tus calorías salen de tu gasto estimado ({round(energy.tdee)} kcal) "
            f"con un ajuste del {energy.adjustment_pct:+.0%} para tu objetivo, y "
            "el reparto de proteína, grasa e hidratos está calculado sobre tu "
            "peso y tus días de entrenamiento."
        ),
        "macros": {"protein_g": total_p, "carbs_g": total_c, "fat_g": total_f},
        "meals": meals,
        "supplements": [],
        "flexibility_rules": [],
        "refeed_or_break": None,
    }
    return NutritionCore.model_validate(nut).model_dump()


_DAY_NAMES = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


def build_strict_menu(nut: dict, allergies: list[str] | None = None,
                      dislikes: list[str] | None = None,
                      diet_pattern: str | None = None) -> tuple[dict | None, list[str]]:
    """Menú CERRADO de 7 días (modo strict) montado con las opciones seguras del
    banco determinista, rotándolas por día. Devuelve (meal_bank, avisos); si
    alguna toma no tiene NINGUNA opción segura, no se puede cerrar el menú
    completo → (None, avisos) y el coach lo monta en el editor."""
    from app.services.meal_fallback import build_fallback_options

    por_toma: dict[int, list[dict]] = {}
    sin_opciones: list[str] = []
    for meal in nut.get("meals") or []:
        opts = build_fallback_options(meal, allergies=allergies, dislikes=dislikes,
                                      diet_pattern=diet_pattern)
        if not opts:
            sin_opciones.append(str(meal.get("name") or f"toma {meal.get('slot')}"))
        por_toma[int(meal["slot"])] = opts
    if sin_opciones:
        return None, ["menú cerrado sin opciones seguras en: "
                      + ", ".join(sin_opciones) + " — móntalo en el editor"]

    days = []
    for i, day in enumerate(_DAY_NAMES):
        meals = []
        for meal in nut.get("meals") or []:
            slot = int(meal["slot"])
            opts = por_toma[slot]
            dish = dict(opts[i % len(opts)])
            dish["key"] = None  # en menú cerrado no hay claves A-G
            meals.append({"slot": slot, "dish": dish})
        days.append({"day": day, "meals": meals})
    return ({"mode": "strict", "days": days, "free_meal_guidelines": None},
            ["menú cerrado generado con opciones deterministas rotadas: "
             "personalízalo en el editor"])


# ----------------------------------------------------------- entrenamiento ----

# Cada día es una lista de "huecos": patrones aceptables por orden de
# preferencia. Los dos primeros huecos son los básicos de la sesión.
_PUSH = ("Empuje", [
    ("horizontal_push",), ("vertical_push",), ("horizontal_push", "shoulder_flexion"),
    ("shoulder_abduction",), ("elbow_extension",), ("elbow_extension",),
])
_PULL = ("Tracción", [
    ("vertical_pull",), ("horizontal_pull",), ("horizontal_pull", "vertical_pull"),
    ("elbow_flexion",), ("scapular_elevation", "shoulder_external_rotation"),
    ("core_anti_rotation",),
])
_LEG = ("Pierna", [
    ("squat",), ("hip_hinge",), ("lunge", "knee_extension"),
    ("knee_flexion",), ("plantar_flexion",), ("core_anti_extension",),
])
_TORSO = ("Torso", [
    ("horizontal_push",), ("horizontal_pull",), ("vertical_push",),
    ("vertical_pull",), ("elbow_extension", "elbow_flexion"),
    ("core_anti_rotation",),
])
_FULL_A = ("Full body A", [
    ("squat",), ("horizontal_push",), ("horizontal_pull",),
    ("shoulder_abduction", "vertical_push"), ("core_anti_extension",),
    ("plantar_flexion", "elbow_flexion"),
])
_FULL_B = ("Full body B", [
    ("hip_hinge",), ("vertical_push",), ("vertical_pull",),
    ("lunge", "knee_extension"), ("core_anti_rotation",),
    ("elbow_extension", "elbow_flexion"),
])

_SPLITS: dict[int, tuple[str, list[tuple[str, list[tuple[str, ...]]]]]] = {
    2: ("Full body 2 días", [_FULL_A, _FULL_B]),
    3: ("Empuje / Tracción / Pierna", [_PUSH, _PULL, _LEG]),
    4: ("Torso / Pierna ×2", [_TORSO, _LEG, _TORSO, _LEG]),
    5: ("Empuje / Tracción / Pierna / Torso / Pierna",
        [_PUSH, _PULL, _LEG, _TORSO, _LEG]),
    6: ("Empuje / Tracción / Pierna ×2", [_PUSH, _PULL, _LEG, _PUSH, _PULL, _LEG]),
}


def _pick(pool: list[dict], prefs: tuple[str, ...], used_session: set[int],
          used_week: set[int]) -> dict | None:
    """Mejor candidato del hueco: patrón preferido, sin repetir en la sesión y
    evitando repetir en la semana si hay alternativa. Orden determinista:
    nivel más alto primero (cliente avanzado), luego alfabético."""
    for pattern in prefs:
        candidates = [e for e in pool
                      if e.get("movement_pattern") == pattern
                      and e["id"] not in used_session]
        if not candidates:
            continue
        frescos = [e for e in candidates if e["id"] not in used_week]
        elegibles = frescos or candidates
        elegibles.sort(key=lambda e: (-int(e.get("level_min") or 1),
                                      str(e.get("canonical_name") or "")))
        return elegibles[0]
    return None


def _cue(text: str | None, default: str) -> str:
    t = (text or "").strip()
    return (t[:140] if t else default)


def build_training(client, filtered: list[dict]) -> dict:
    """TrainingCore determinista desde la biblioteca YA filtrada por guardrails:
    split estándar según los días declarados, básicos primero, series/repes/RIR
    y progresión de referencia. El coach lo remata en el editor."""
    days = min(6, max(2, int(client.training_days or 3)))
    split_name, day_defs = _SPLITS[days]
    # Sesiones cortas → menos huecos por día.
    max_min = int(client.session_max_min or 60)
    huecos = 4 if max_min <= 45 else 5 if max_min <= 60 else 6

    used_week: set[int] = set()
    sessions = []
    for i, (nombre, plantilla) in enumerate(day_defs, start=1):
        used_session: set[int] = set()
        exercises = []
        for j, prefs in enumerate(plantilla[:huecos]):
            ex = _pick(filtered, prefs, used_session, used_week)
            if ex is None:
                continue
            used_session.add(ex["id"])
            used_week.add(ex["id"])
            basico = j < 2
            exercises.append({
                "exercise_id": ex["id"],
                "sets": 4 if basico else 3,
                "rep_range": "6-10" if basico else "8-12",
                "rir": "2",
                "tempo": None,
                "rest_sec": 150 if basico else 90,
                "start_weight_hint_kg": None,
                "progression_rule": (
                    "Doble progresión: cuando completes todas las series en el "
                    "tope del rango con RIR 2, sube el peso la siguiente sesión."
                ),
                "technique_cue": _cue(ex.get("technique_notes"),
                                      "Técnica controlada y rango completo."),
                "biomech_cue": _cue(ex.get("biomechanics_notes"),
                                    "Controla la fase excéntrica (2-3 s)."),
            })
        if exercises:
            sessions.append({
                "day": f"Día {i}",
                "name": nombre,
                "warmup": ("5-8 min de cardio suave + 2 series de aproximación "
                           "en los básicos del día."),
                "exercises": exercises,
                "cooldown": "3-5 min de vuelta a la calma y estiramientos suaves.",
            })

    if not sessions:
        # Biblioteca sin candidatos para NINGÚN patrón de las plantillas: mejor
        # un error accionable que un 500 de validación (TrainingCore exige ≥1).
        raise ValueError(
            "La biblioteca filtrada no cubre los patrones básicos: revisa las "
            "restricciones del cliente (lesiones, material, exclusiones).")

    pasos = {"sedentary": 7000, "light": 8000, "active": 9000,
             "very_active": 10000}.get(client.daily_activity_level or "", 8000)

    training = {
        "split_name": split_name,
        # También lo lee el CLIENTE en su PDF: se le explica su rutina, no el
        # proceso interno de preparación.
        "split_rationale": (
            f"Rutina de {days} días repartida para que cada grupo muscular "
            "trabaje con la frecuencia adecuada y descanse lo suficiente, "
            "ajustada al tiempo que tienes por sesión y a tu material."
        ),
        "weekly_progression": [
            {"week": 1, "intent": "Base", "load_pct": 100.0, "rir_target": "2",
             "volume_note": "Asienta técnica y cargas de referencia."},
            {"week": 2, "intent": "Progresión", "load_pct": 102.5, "rir_target": "1-2",
             "volume_note": "Sube peso o repeticiones donde el RIR lo permita."},
            {"week": 3, "intent": "Pico", "load_pct": 105.0, "rir_target": "1",
             "volume_note": "Semana más exigente del ciclo."},
            {"week": 4, "intent": "Deload", "load_pct": 60.0, "rir_target": "3-4",
             "volume_note": "Mitad de series: recuperar para el siguiente ciclo."},
        ],
        "sessions": sessions,
        "cardio": {"daily_steps": pasos, "sessions": []},
        "deload_instructions": (
            "Semana 4: reduce las series a la mitad y la carga al 60 %. Llega "
            "fresco al siguiente ciclo; el deload es parte del plan, no un extra."
        ),
    }
    return TrainingCore.model_validate(training).model_dump()
