"""Servicio de métricas — TODA la aritmética del sistema vive aquí.

Principio rector (PARTE D.2): **la IA nunca calcula**. El backend computa
energía, medias, tendencias, adherencias y e1RM, y se los entrega ya hechos.
Esto garantiza reproducibilidad, testabilidad y que los guardrails operen
sobre números fiables, no sobre lo que la IA "creía" haber calculado.

Unidades: kg, cm, kcal, gramos. Pesos de comida siempre en crudo (E.3).
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date


def _rhu(x: float) -> int:
    """Redondeo half-up (0,5 → 1), coherente con `_rhu` de nutrition_scale y con
    Math.round del frontend: una sola convención de redondeo en todo el sistema."""
    return int(math.floor(x + 0.5))

# ----------------------------------------------------------------- energía ----

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Ajuste calórico por objetivo (fracción del TDEE). El signo lo aplica el caller.
# Ajuste calórico por objetivo (rango basado en evidencia; se aplica el punto
# medio). Referencias: déficit moderado 15-25% preserva masa magra y adherencia
# (Helms 2014); superávit 5-12% minimiza ganancia de grasa (Iraki 2019);
# recomposición ≈ mantenimiento con proteína alta (Barakat 2020); en lesión se
# evita el déficit agresivo para no frenar la reparación de tejidos y se
# trabaja entre mantenimiento y −5% (Tipton 2015).
GOAL_ADJUSTMENT = {
    "fat_loss": (0.15, 0.25),      # déficit 15–25%
    "muscle_gain": (0.05, 0.12),   # superávit 5–12%
    "recomp": (0.0, 0.05),         # mantenimiento ±5%
    "maintenance": (0.0, 0.0),     # mantenimiento estricto
    "injury_recovery": (0.0, 0.05),  # mantenimiento a −5%
}


def mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """BMR (kcal/día). Mifflin-St Jeor — el estándar cuando no hay % graso."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if sex == "male" else -161), 1)


def katch_mcardle(weight_kg: float, body_fat_pct: float) -> float:
    """BMR vía masa magra (kcal/día). Preferible si hay % graso fiable."""
    lean = weight_kg * (1 - body_fat_pct / 100)
    return round(370 + 21.6 * lean, 1)


def bmr(
    sex: str, weight_kg: float, height_cm: float, age: int,
    body_fat_pct: float | None = None,
) -> float:
    """BMR usando Katch-McArdle si hay % graso, Mifflin-St Jeor si no (E.1)."""
    if body_fat_pct is not None and 3 <= body_fat_pct <= 60:
        return katch_mcardle(weight_kg, body_fat_pct)
    return mifflin_st_jeor(sex, weight_kg, height_cm, age)


def activity_factor_for_days(training_days: int) -> float:
    """Mapea días de entrenamiento/semana a factor de actividad (E.1). Retrocompat:
    se usa cuando no se conoce la actividad DIARIA (NEAT) del cliente."""
    if training_days <= 1:
        return ACTIVITY_FACTORS["sedentary"]
    if training_days <= 2:
        return ACTIVITY_FACTORS["light"]
    if training_days <= 4:
        return ACTIVITY_FACTORS["moderate"]
    if training_days <= 5:
        return ACTIVITY_FACTORS["active"]
    return ACTIVITY_FACTORS["very_active"]


# Actividad DIARIA fuera del entreno (NEAT: trabajo, pasos, tareas). Separarla de
# los días de entreno evita el sesgo de contar solo el gimnasio: un oficinista
# que entrena 6 días NO gasta como un mensajero que entrena 2. El entreno suma
# aparte (~0,03 por sesión/semana). Referencia: NEAT domina la variabilidad del
# gasto (Levine 2002); factores de ocupación tipo Tinsley/Trexler.
NEAT_FACTORS = {
    "sedentary": 1.25,    # oficina / sentado casi todo el día
    "light": 1.40,        # de pie o caminando a ratos (comercio, docencia)
    "active": 1.55,       # trabajo físico moderado, muchos pasos
    "very_active": 1.70,  # trabajo físico intenso (obra, mensajería, campo)
}
_EXERCISE_PER_DAY = 0.03


def activity_factor(training_days: int, daily_activity: str | None = None) -> float:
    """Factor de actividad total = NEAT (ocupación diaria) + entreno. Si no se
    conoce la actividad diaria, cae al mapeo por días (retrocompatible)."""
    if not daily_activity:
        return activity_factor_for_days(training_days)
    base = NEAT_FACTORS.get(daily_activity, NEAT_FACTORS["light"])
    return round(min(1.95, base + _EXERCISE_PER_DAY * max(0, training_days or 0)), 3)


def tdee(bmr_value: float, training_days: int, daily_activity: str | None = None) -> float:
    return round(bmr_value * activity_factor(training_days, daily_activity), 1)


def age_from_birth(birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


# --- Ajuste energético INDIVIDUALIZADO (hardening §3) -------------------------
# El punto medio del rango del objetivo daba a un cliente al 12% de graso y a
# otro al 35% exactamente el mismo déficit. La evidencia recomienda déficits
# mayores cuanta más grasa hay (más margen, menos riesgo de perder masa magra) y
# superávits menores cuanta más experiencia (menos capacidad de ganar músculo sin
# grasa). Cada rango lleva su RITMO DIANA de cambio de peso (%/semana).
# Referencias: Helms 2014 (déficit por nivel de grasa), Iraki 2019 / Garthe 2013
# (superávit por experiencia), Barakat 2020 (recomposición).

# Umbrales de % graso por sexo para elegir el bracket de pérdida.
_FAT_HIGH = {"male": 25.0, "female": 32.0}   # ≥ → graso alto
_FAT_LOW = {"male": 15.0, "female": 23.0}    # < → graso bajo


def _fat_bracket(sex: str, body_fat_pct: float | None) -> str:
    """"high" | "medium" | "low" según % graso y sexo; "medium" si no hay dato."""
    if body_fat_pct is None:
        return "medium"
    if body_fat_pct >= _FAT_HIGH.get(sex, 25.0):
        return "high"
    if body_fat_pct < _FAT_LOW.get(sex, 15.0):
        return "low"
    return "medium"


@dataclass
class EnergyAdjustment:
    pct: float          # fracción con signo sobre el TDEE (−0,20 = déficit 20%)
    rate_lo: float      # ritmo diana mín. (%/semana de peso corporal, con signo)
    rate_hi: float      # ritmo diana máx.
    bracket: str        # descripción del tramo aplicado (para trazabilidad)


# (conservador, agresivo) en fracción con signo + (ritmo_lo, ritmo_hi) %/sem.
_ADJUSTMENT_TABLE = {
    ("fat_loss", "high"):   ((-0.20, -0.25), (-0.7, -1.0)),
    ("fat_loss", "medium"): ((-0.15, -0.20), (-0.5, -0.7)),
    ("fat_loss", "low"):    ((-0.10, -0.15), (-0.3, -0.5)),
    ("muscle_gain", "novice"): ((0.12, 0.15), (0.25, 0.5)),
    ("muscle_gain", "exp"):    ((0.05, 0.10), (0.1, 0.25)),
    ("recomp", "any"):      ((0.0, -0.05), (0.0, 0.0)),
    ("injury_recovery", "any"): ((0.0, -0.05), (0.0, 0.0)),
    ("maintenance", "any"): ((0.0, 0.0), (0.0, 0.0)),
}


def individualized_energy_adjustment(
    goal_type: str, sex: str, body_fat_pct: float | None,
    level: str | None = None, adherence_ratio: float | None = None,
) -> EnergyAdjustment:
    """Ajuste calórico y ritmo diana individualizados por objetivo, % graso y
    experiencia. La adherencia histórica (si se conoce) elige el punto dentro del
    rango: buena adherencia → extremo más agresivo (lo sostiene); mala → extremo
    conservador (un déficit fuerte que no se cumple no sirve). Sin historial →
    punto medio (arranque prudente, principio del canario del §12)."""
    if goal_type == "fat_loss":
        key = ("fat_loss", _fat_bracket(sex, body_fat_pct))
    elif goal_type == "muscle_gain":
        key = ("muscle_gain", "novice" if level == "beginner" else "exp")
    elif goal_type in ("recomp", "injury_recovery", "maintenance"):
        key = (goal_type, "any")
    else:
        key = ("maintenance", "any")
    (cons, aggr), (rate_lo, rate_hi) = _ADJUSTMENT_TABLE[key]

    if adherence_ratio is None:
        pct = (cons + aggr) / 2
    elif adherence_ratio >= 0.85:
        pct = aggr
    elif adherence_ratio < 0.60:
        pct = cons
    else:
        pct = (cons + aggr) / 2
    return EnergyAdjustment(
        pct=round(pct, 4), rate_lo=rate_lo, rate_hi=rate_hi,
        bracket=f"{key[0]}/{key[1]}",
    )


# --- TDEE por componentes (hardening §3) --------------------------------------
# NEAT por pasos reales + EAT del entrenamiento REALMENTE planificado + ETA, en
# vez de un único factor multiplicador. Se usa cuando hay datos (pasos); si no,
# cae al método clásico (factor de actividad). MET por defecto ~6 (entreno de
# fuerza moderado-vigoroso). Referencias: Levine 2002 (NEAT), compendio de MET.
_STEP_KCAL = 0.00045  # kcal por paso y por kg de peso
_TRAINING_MET = 6.0


@dataclass
class TdeeComponents:
    bmr: float
    neat: float
    eat: float
    eta: float
    total: float


def tdee_by_components(
    bmr_value: float, weight_kg: float, daily_steps: float,
    sessions_per_week: int, session_min: float, met: float = _TRAINING_MET,
) -> TdeeComponents:
    """TDEE = BMR + NEAT(pasos) + EAT(entreno planificado) + ETA(10% del resto)."""
    neat = daily_steps * weight_kg * _STEP_KCAL
    eat = sessions_per_week * session_min * met * weight_kg / 60 / 7
    eta = 0.10 * (bmr_value + neat + eat)
    total = bmr_value + neat + eat + eta
    return TdeeComponents(
        bmr=round(bmr_value, 1), neat=round(neat, 1), eat=round(eat, 1),
        eta=round(eta, 1), total=round(total, 1),
    )


# Pasos/día representativos por nivel de actividad declarado (para poder usar el
# método por componentes con la anamnesis actual, que aún no pide pasos exactos).
_STEPS_BY_ACTIVITY = {
    "sedentary": 4000, "light": 7000, "active": 10000, "very_active": 13000,
}


@dataclass
class EnergyTargets:
    bmr: float
    tdee: float
    target_kcal: float
    method: str            # "mifflin" | "katch"
    adjustment_pct: float  # negativo = déficit, positivo = superávit
    # Individualización (hardening §3): trazabilidad de POR QUÉ este ajuste.
    bracket: str = ""
    rate_target_pct: tuple[float, float] = (0.0, 0.0)  # ritmo diana %/semana
    tdee_components: float | None = None   # TDEE por NEAT+EAT+ETA (si hay datos)
    warnings: list[str] = field(default_factory=list)


def energy_targets(
    sex: str, weight_kg: float, height_cm: float, age: int, goal_type: str,
    training_days: int, body_fat_pct: float | None = None,
    daily_activity: str | None = None, level: str | None = None,
    adherence_ratio: float | None = None, session_min: float | None = None,
) -> EnergyTargets:
    """Objetivo calórico de referencia que el backend entrega a la IA.

    La IA NO calcula: parte de esta base objetiva. El ajuste sobre el TDEE se
    individualiza por % graso (pérdida) o experiencia (ganancia) y, si se conoce,
    por adherencia histórica. El TDEE se compara con el método por componentes
    (NEAT+EAT+ETA) y se avisa si divergen >15%.
    """
    use_katch = body_fat_pct is not None and 3 <= body_fat_pct <= 60
    b = bmr(sex, weight_kg, height_cm, age, body_fat_pct)
    t = tdee(b, training_days, daily_activity)
    warnings: list[str] = []

    # TDEE por componentes con los datos disponibles (pasos aproximados por el
    # nivel de actividad). Se compara con el clásico; divergencia >15% → aviso.
    comp_total: float | None = None
    steps = _STEPS_BY_ACTIVITY.get(daily_activity or "")
    if steps:
        comp = tdee_by_components(
            b, weight_kg, steps, training_days or 0, session_min or 60.0,
        )
        comp_total = comp.total
        if t > 0 and abs(comp_total - t) / t > 0.15:
            warnings.append(
                f"TDEE clásico ({t:.0f}) y por componentes ({comp_total:.0f}) "
                f"divergen >15%: revisa actividad/pasos declarados."
            )

    adj = individualized_energy_adjustment(
        goal_type, sex, body_fat_pct, level, adherence_ratio
    )
    target = t * (1 + adj.pct)

    # Suelo de seguridad: nunca por debajo del BMR ni de un mínimo por sexo (mismo
    # criterio que el guardrail de nutrición). Sin esto, un cliente sedentario o
    # ligero en pérdida de grasa recibía un target < BMR que el propio guardrail
    # rechazaba → no se podía generar el plan. Se recalcula el % real aplicado.
    floor = max(b, 1600.0 if sex == "male" else 1400.0)
    applied = adj.pct
    if target < floor:
        target = floor
        applied = round((target / t - 1), 4) if t else 0.0
        warnings.append(
            "El ajuste pedido caía por debajo del suelo calórico seguro: se "
            "recalcula al ritmo seguro (nunca se rompe un suelo por un plazo)."
        )
    return EnergyTargets(
        bmr=b, tdee=t, target_kcal=round(target, 1),
        method="katch" if use_katch else "mifflin",
        adjustment_pct=round(applied, 4),
        bracket=adj.bracket, rate_target_pct=(adj.rate_lo, adj.rate_hi),
        tdee_components=comp_total, warnings=warnings,
    )


# Proteína (g/kg/día) por objetivo. Referencias: 1,6-2,2 maximiza síntesis
# proteica (Morton 2018); en déficit conviene el rango alto 2,0-2,4 para
# preservar masa (Helms 2014); recomposición 2,2-2,6 — la proteína alta es el
# motor del proceso (Barakat 2020); en lesión 2,0-2,5 contra la atrofia por
# desuso (Tipton 2015).
PROTEIN_RANGE = {
    "fat_loss": (2.0, 2.4),
    "muscle_gain": (1.6, 2.2),
    "recomp": (2.2, 2.6),
    "maintenance": (1.6, 2.2),
    "injury_recovery": (2.0, 2.5),
}


def protein_target_g(weight_kg: float, goal_type: str) -> tuple[float, float]:
    """Rango de proteína recomendado (g/día) según objetivo (E.2)."""
    lo, hi = PROTEIN_RANGE.get(goal_type, (1.8, 2.2))
    return round(weight_kg * lo, 1), round(weight_kg * hi, 1)


@dataclass
class MacroPlan:
    """Reparto completo de macros calculado EN CÓDIGO (hardening §3). La IA no
    decide gramos de macros: recibe este contrato y construye el menú para
    cumplirlo. `kcal` puede subir respecto a la pedida si los suelos no cabían."""

    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    fiber_g_min: int
    water_ml: int
    notes: list[str] = field(default_factory=list)


def macro_targets(
    sex: str, weight_kg: float, goal_type: str, kcal: float, training_days: int,
) -> MacroPlan:
    """Reparto completo de macros: proteína (punto medio del rango por objetivo),
    grasa (≥0,6 g/kg — 0,7 en mujeres — Y dentro del 20–35% de las kcal),
    carbohidratos = el resto con SUELO de 2 g/kg si entrena ≥3 días y 3 g/kg si
    ≥5. Fibra 14 g/1.000 kcal (mín. 25). Agua 30–40 ml/kg (guía 35).

    Regla innegociable (§3): si los suelos no caben en las kcal objetivo, se SUBEN
    las kcal (se reduce el déficit); NUNCA se rompe un suelo para cumplir un plazo.
    """
    notes: list[str] = []
    p_lo, p_hi = PROTEIN_RANGE.get(goal_type, (1.8, 2.2))
    protein = _rhu(weight_kg * (p_lo + p_hi) / 2)

    # Grasa: suelo por kg y suelo del 20% de kcal; techo del 35% de kcal.
    fat_kg_floor = weight_kg * (0.7 if sex == "female" else 0.6)
    fat_20 = 0.20 * kcal / 9
    fat_35 = 0.35 * kcal / 9
    fat = _rhu(min(max(fat_kg_floor, fat_20), max(fat_35, fat_kg_floor)))

    carbs = _rhu((kcal - protein * 4 - fat * 9) / 4)

    # Suelo de carbohidratos según volumen de entreno.
    carb_floor_per_kg = 3.0 if (training_days or 0) >= 5 else 2.0 if (training_days or 0) >= 3 else 0.0
    carb_floor = _rhu(weight_kg * carb_floor_per_kg)
    if carbs < carb_floor:
        # Los suelos (P + G + suelo de HC) no caben: se suben las kcal para
        # respetarlos en vez de romper el suelo (nunca por un plazo del cliente).
        carbs = carb_floor
        notes.append(
            f"kcal ajustadas para respetar el suelo de {carb_floor} g de "
            f"carbohidratos ({carb_floor_per_kg:g} g/kg): no se rompe un suelo "
            f"por un objetivo de plazo."
        )
    elif carbs < 0:
        carbs = 0
        notes.append("kcal ajustadas: proteína y grasa mínimas ya cubren la energía.")

    # UNA SOLA VERDAD: las kcal declaradas SON exactamente la suma 4/4/9 de sus
    # macros (mismo criterio que reconcile_nutrition). Así nunca hay "aquí pone X
    # kcal y los macros suman otra cosa" — el descuadre más visible para el cliente.
    final_kcal = protein * 4 + carbs * 4 + fat * 9
    fiber = max(25, _rhu(14 * final_kcal / 1000))
    water = _rhu(weight_kg * 35)
    return MacroPlan(
        kcal=final_kcal, protein_g=protein, carbs_g=carbs, fat_g=fat,
        fiber_g_min=fiber, water_ml=water, notes=notes,
    )


# ------------------------------------------------------------------- e1RM ----

def epley_1rm(weight_kg: float, reps: int) -> float:
    """1RM estimado (Epley). reps=1 → el propio peso."""
    if reps <= 0:
        return 0.0
    if reps == 1:
        return round(weight_kg, 2)
    return round(weight_kg * (1 + reps / 30), 2)


# ------------------------------------------------- agregados de un período ----

@dataclass
class WeightTrend:
    start_kg: float | None = None
    end_kg: float | None = None
    delta_kg: float | None = None
    weekly_rate_kg: float | None = None  # ritmo semanal (negativo = bajada)
    mean_kg: float | None = None
    n_measurements: int = 0


def weight_trend(points: list[tuple[date, float]]) -> WeightTrend:
    """Tendencia de peso a partir de (fecha, kg). Robusta a huecos.

    El ritmo semanal usa una regresión lineal simple por mínimos cuadrados
    sobre los días transcurridos: más estable que (fin - inicio) ante ruido.
    """
    pts = sorted((d, w) for d, w in points if w is not None)
    if not pts:
        return WeightTrend()
    weights = [w for _, w in pts]
    if len(pts) == 1:
        return WeightTrend(
            start_kg=weights[0], end_kg=weights[0], delta_kg=0.0,
            weekly_rate_kg=0.0, mean_kg=round(weights[0], 2), n_measurements=1,
        )
    day0 = pts[0][0]
    xs = [(d - day0).days for d, _ in pts]
    slope = _least_squares_slope(xs, weights)  # kg/día
    return WeightTrend(
        start_kg=round(weights[0], 2),
        end_kg=round(weights[-1], 2),
        delta_kg=round(weights[-1] - weights[0], 2),
        weekly_rate_kg=round(slope * 7, 3) if slope is not None else None,
        mean_kg=round(statistics.fmean(weights), 2),
        n_measurements=len(pts),
    )


def _least_squares_slope(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


@dataclass
class AdherenceSummary:
    days_logged: int = 0
    period_days: int = 0
    log_ratio: float = 0.0          # días registrados / días del período
    diet_yes: int = 0
    diet_partial: int = 0
    diet_no: int = 0
    diet_adherence_ratio: float = 0.0  # (yes + 0.5·partial) / registros de dieta
    mean_sleep_h: float | None = None
    mean_energy: float | None = None
    mean_mood: float | None = None
    mean_fatigue: float | None = None


def adherence_summary(
    logs: list[dict], period_days: int,
) -> AdherenceSummary:
    """Resume la adherencia y el bienestar del período.

    `logs`: lista de dicts con claves opcionales diet_adherence, sleep_hours,
    energy_1_5, mood_1_5, fatigue_1_5. Tolera campos ausentes/None.
    """
    s = AdherenceSummary(days_logged=len(logs), period_days=period_days)
    if period_days > 0:
        s.log_ratio = round(len(logs) / period_days, 3)

    diet = [g.get("diet_adherence") for g in logs if g.get("diet_adherence")]
    s.diet_yes = diet.count("yes")
    s.diet_partial = diet.count("partial")
    s.diet_no = diet.count("no")
    if diet:
        s.diet_adherence_ratio = round((s.diet_yes + 0.5 * s.diet_partial) / len(diet), 3)

    s.mean_sleep_h = _mean_of(logs, "sleep_hours")
    s.mean_energy = _mean_of(logs, "energy_1_5")
    s.mean_mood = _mean_of(logs, "mood_1_5")
    s.mean_fatigue = _mean_of(logs, "fatigue_1_5")
    return s


def _mean_of(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(statistics.fmean(vals), 2) if vals else None


@dataclass
class ExerciseProgress:
    exercise_id: int
    best_e1rm_kg: float
    best_set: tuple[float, int]  # (peso, reps) que produjo el mejor e1RM
    sessions: int


def exercise_e1rm_progress(sets: list[dict]) -> list[ExerciseProgress]:
    """Mejor e1RM por ejercicio dentro del período.

    `sets`: dicts con exercise_id, weight_kg, reps. Ignora sets sin peso/reps.
    El feedback grafica 3–5 ejercicios; esto da el dato a graficar (H.4).
    """
    by_ex: dict[int, list[dict]] = {}
    for st in sets:
        if st.get("weight_kg") and st.get("reps"):
            by_ex.setdefault(st["exercise_id"], []).append(st)

    out: list[ExerciseProgress] = []
    for ex_id, ex_sets in by_ex.items():
        best = max(ex_sets, key=lambda s: epley_1rm(s["weight_kg"], s["reps"]))
        out.append(ExerciseProgress(
            exercise_id=ex_id,
            best_e1rm_kg=epley_1rm(best["weight_kg"], best["reps"]),
            best_set=(best["weight_kg"], best["reps"]),
            sessions=len({s.get("daily_log_id") for s in ex_sets}),
        ))
    out.sort(key=lambda p: p.best_e1rm_kg, reverse=True)
    return out


def option_choice_stats(chosen: list[dict]) -> dict[int, dict[str, int]]:
    """Frecuencia de elección de opciones por slot (para regeneración mensual).

    `chosen`: lista de chosen_options_json, p.ej. [{"1":"A","2":"C"}, ...].
    Devuelve {slot: {opcion: veces}} para conservar las 4–5 más usadas (C.3).
    """
    counters: dict[int, Counter] = {}
    for day in chosen:
        if not day:
            continue
        for slot_str, opt in day.items():
            try:
                slot = int(slot_str)
            except (ValueError, TypeError):
                continue
            counters.setdefault(slot, Counter())[opt] += 1
    return {slot: dict(c.most_common()) for slot, c in counters.items()}


# ------------------------------------------------- ensamblado para la IA ----

@dataclass
class PeriodMetrics:
    """Paquete completo que el backend persiste en periods.metrics_json y
    entrega a la IA en recalibración/análisis. La IA solo lee, nunca recalcula."""

    weight: WeightTrend
    adherence: AdherenceSummary
    exercise_progress: list[ExerciseProgress] = field(default_factory=list)
    option_stats: dict[int, dict[str, int]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "weight": {
                "start_kg": self.weight.start_kg, "end_kg": self.weight.end_kg,
                "delta_kg": self.weight.delta_kg,
                "weekly_rate_kg": self.weight.weekly_rate_kg,
                "mean_kg": self.weight.mean_kg,
                "n_measurements": self.weight.n_measurements,
            },
            "adherence": {
                "days_logged": self.adherence.days_logged,
                "period_days": self.adherence.period_days,
                "log_ratio": self.adherence.log_ratio,
                "diet_yes": self.adherence.diet_yes,
                "diet_partial": self.adherence.diet_partial,
                "diet_no": self.adherence.diet_no,
                "diet_adherence_ratio": self.adherence.diet_adherence_ratio,
                "mean_sleep_h": self.adherence.mean_sleep_h,
                "mean_energy": self.adherence.mean_energy,
                "mean_mood": self.adherence.mean_mood,
                "mean_fatigue": self.adherence.mean_fatigue,
            },
            "exercise_progress": [
                {
                    "exercise_id": p.exercise_id, "best_e1rm_kg": p.best_e1rm_kg,
                    "best_weight_kg": p.best_set[0], "best_reps": p.best_set[1],
                    "sessions": p.sessions,
                }
                for p in self.exercise_progress
            ],
            "option_stats": {str(k): v for k, v in self.option_stats.items()},
        }
