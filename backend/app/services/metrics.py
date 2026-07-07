"""Servicio de métricas — TODA la aritmética del sistema vive aquí.

Principio rector (PARTE D.2): **la IA nunca calcula**. El backend computa
energía, medias, tendencias, adherencias y e1RM, y se los entrega ya hechos.
Esto garantiza reproducibilidad, testabilidad y que los guardrails operen
sobre números fiables, no sobre lo que la IA "creía" haber calculado.

Unidades: kg, cm, kcal, gramos. Pesos de comida siempre en crudo (E.3).
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

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
    """Mapea días de entrenamiento/semana a factor de actividad (E.1)."""
    if training_days <= 1:
        return ACTIVITY_FACTORS["sedentary"]
    if training_days <= 2:
        return ACTIVITY_FACTORS["light"]
    if training_days <= 4:
        return ACTIVITY_FACTORS["moderate"]
    if training_days <= 5:
        return ACTIVITY_FACTORS["active"]
    return ACTIVITY_FACTORS["very_active"]


def tdee(bmr_value: float, training_days: int) -> float:
    return round(bmr_value * activity_factor_for_days(training_days), 1)


def age_from_birth(birth: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


@dataclass
class EnergyTargets:
    bmr: float
    tdee: float
    target_kcal: float
    method: str           # "mifflin" | "katch"
    adjustment_pct: float  # negativo = déficit, positivo = superávit


def energy_targets(
    sex: str, weight_kg: float, height_cm: float, age: int, goal_type: str,
    training_days: int, body_fat_pct: float | None = None,
) -> EnergyTargets:
    """Objetivo calórico de referencia que el backend entrega a la IA.

    La IA puede afinar dentro de los guardrails, pero parte de esta base
    objetiva en lugar de inventarla.
    """
    use_katch = body_fat_pct is not None and 3 <= body_fat_pct <= 60
    b = bmr(sex, weight_kg, height_cm, age, body_fat_pct)
    t = tdee(b, training_days)
    lo, hi = GOAL_ADJUSTMENT.get(goal_type, (0.0, 0.05))
    mid = (lo + hi) / 2
    if goal_type == "fat_loss":
        target = t * (1 - mid)
        adj = -mid
    elif goal_type == "muscle_gain":
        target = t * (1 + mid)
        adj = mid
    elif goal_type == "injury_recovery":
        # Lesión: mantenimiento a déficit muy ligero — nunca superávit ni
        # déficit fuerte (la reparación de tejidos necesita energía y proteína).
        target = t * (1 - mid)
        adj = -mid
    else:  # recomp / maintenance → mantenimiento
        target = t
        adj = 0.0
    return EnergyTargets(
        bmr=b, tdee=t, target_kcal=round(target, 1),
        method="katch" if use_katch else "mifflin",
        adjustment_pct=round(adj, 4),
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
