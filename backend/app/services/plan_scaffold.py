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
from app.services import training_cycle as tc
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
                      + ", ".join(sin_opciones) + " — revisa alergias/patrón, o "
                      "edítalo descargando el Word y subiéndolo"]

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
             "personalízalo descargando el Word, editándolo y subiéndolo"])


# ----------------------------------------------------------- entrenamiento ----

# Reparto semanal estándar según el nº de sesiones (mismas etiquetas, con
# acentos, que usan la IA y el portal: "Lunes"…"Domingo").
_REPARTO_SEMANAL = {
    1: ("Lunes",),
    2: ("Lunes", "Jueves"),
    3: ("Lunes", "Miércoles", "Viernes"),
    4: ("Lunes", "Martes", "Jueves", "Viernes"),
    5: ("Lunes", "Martes", "Miércoles", "Viernes", "Sábado"),
    6: ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"),
    7: ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"),
}

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


def _reparto_del_ciclo(sesiones: int, ciclo: int) -> list[int]:
    """En qué días del ciclo caen las sesiones (1…ciclo).

    Con la SEMANA se respeta el reparto de siempre (`_REPARTO_SEMANAL`): ese
    cliente que entrena lunes, miércoles y viernes lo sigue haciendo. Con un
    ciclo más largo se reparten de forma pareja para que el descanso quede
    repartido y no todo al final — y el coach lo mueve en el editor."""
    if ciclo == tc.SEMANA:
        etiquetas = _REPARTO_SEMANAL.get(sesiones, _REPARTO_SEMANAL[3])
        return [tc.DAY_LABELS.index(e) + 1 for e in etiquetas[:sesiones]]
    sesiones = max(1, min(sesiones, ciclo))
    return [round(i * ciclo / sesiones) + 1 for i in range(sesiones)]


def _progresion_del_mesociclo(bloques: int) -> list[dict]:
    """La progresión, con tantas entradas como bloques tenga el mesociclo.

    Estaba clavada a cuatro semanas (Base · Progresión · Pico · Deload). Un
    mesociclo de 2 bloques no da para una descarga —descargar la mitad del
    tiempo no es periodizar— y uno de 6 necesita más escalones de subida."""
    bloques = max(tc.MIN_BLOQUES, min(tc.MAX_BLOQUES, int(bloques or tc.BLOQUES_POR_DEFECTO)))
    con_descarga = bloques >= 3           # con 2 o menos no hay margen
    con_pico = bloques >= 4
    subidas = bloques - 1 - int(con_descarga) - int(con_pico)
    salida = [{"week": 1, "intent": "Base", "load_pct": 100.0, "rir_target": "2",
               "volume_note": "Asienta técnica y cargas de referencia."}]
    for k in range(subidas):
        salida.append({
            "week": len(salida) + 1, "intent": "Progresión",
            "load_pct": round(100.0 + 2.5 * (k + 1), 1), "rir_target": "1-2",
            "volume_note": "Sube peso o repeticiones donde el RIR lo permita."})
    if con_pico:
        salida.append({
            "week": len(salida) + 1, "intent": "Pico",
            "load_pct": round(100.0 + 2.5 * (subidas + 1), 1), "rir_target": "1",
            "volume_note": "El bloque más exigente del mesociclo."})
    if con_descarga:
        salida.append({
            "week": len(salida) + 1, "intent": "Deload", "load_pct": 60.0,
            "rir_target": "3-4",
            "volume_note": "Mitad de series: recuperar para el siguiente ciclo."})
    return salida[:bloques]


def _texto_de_descarga(progresion: list[dict], ciclo: int) -> str:
    """La descarga, dicha sobre el bloque que de verdad la lleva.

    El texto estaba clavado en "Semana 4" y después en "Bloque {bloques}": con
    un mesociclo de 2 bloques no hay descarga (`_progresion_del_mesociclo` no
    la pone) y el plan prometía una que no existe. Se lee de la progresión."""
    etiqueta = tc.etiqueta_de_bloque(ciclo)
    for p in progresion:
        if str(p.get("intent") or "").strip().lower() == "deload":
            return (f"{etiqueta} {p['week']}: reduce las series a la mitad y la "
                    "carga al 60 %. Llega fresco al siguiente ciclo; el deload "
                    "es parte del plan, no un extra.")
    return (f"Este mesociclo es corto ({len(progresion)} "
            f"{etiqueta.lower()}{'s' if len(progresion) != 1 else ''}) y no lleva "
            "descarga programada: si llegas muy fatigado, baja las series a la "
            "mitad durante una vuelta al ciclo antes de seguir.")


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
    # El CICLO manda sobre los días de la semana: con 7 sale exactamente lo de
    # siempre; con 10, las sesiones que esa persona entrena en 10 días.
    ciclo = int(getattr(client, "cycle_days", None) or tc.SEMANA)
    bloques = int(getattr(client, "mesocycle_blocks", None) or tc.BLOQUES_POR_DEFECTO)
    sesiones = tc.sesiones_objetivo(client.training_days or 3, ciclo)
    days = min(6, max(2, int(client.training_days or 3)))
    split_name, day_defs = _SPLITS[days]
    # Un ciclo largo repite el patrón del split hasta llenar sus sesiones: seis
    # sesiones en 10 días son ese Torso/Pierna dando dos vueltas y media, no un
    # split nuevo que haya que inventarse.
    if sesiones > len(day_defs):
        day_defs = [day_defs[i % len(day_defs)] for i in range(sesiones)]
    elif sesiones < len(day_defs):
        day_defs = day_defs[:sesiones]
    dias_del_ciclo = _reparto_del_ciclo(len(day_defs), ciclo)
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
                # Día REAL de la semana, no "Día {i}": el portal detecta la
                # sesión de HOY comparando con "lunes…domingo", así que un plan
                # base nunca marcaba sesión del día ni la preseleccionaba en
                # Entreno (auditoría 27-08). El coach lo reparte a su gusto en
                # el editor; este es el reparto estándar de partida.
                "day": tc.etiqueta_de_dia(dias_del_ciclo[i - 1], ciclo),
                "day_index": dias_del_ciclo[i - 1],
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

    progresion = _progresion_del_mesociclo(bloques)
    training = {
        "split_name": split_name,
        # También lo lee el CLIENTE en su PDF: se le explica su rutina, no el
        # proceso interno de preparación.
        "split_rationale": (
            f"Rutina de {len(sessions)} "
            + ("sesión repartida" if len(sessions) == 1 else "sesiones repartidas")
            + (" en la semana" if tc.es_semanal(ciclo) else f" en un ciclo de {ciclo} días")
            + " para que cada grupo muscular trabaje con la frecuencia adecuada "
            "y descanse lo suficiente, ajustada al tiempo que tienes por sesión "
            "y a tu material."
        ),
        "weekly_progression": progresion,
        "cycle_days": ciclo,
        "sessions": sessions,
        "cardio": {"daily_steps": pasos, "sessions": []},
        "deload_instructions": _texto_de_descarga(progresion, ciclo),
    }
    return TrainingCore.model_validate(training).model_dump()
