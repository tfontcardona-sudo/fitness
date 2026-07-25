"""Mecanismos adicionales de calidad del plan (hardening §10).

Comprobaciones de PROPÓSITO (no de números sueltos), que cazan errores de fondo
que ninguna validación puntual detecta:

- `simulate_trajectory`: proyecta N semanas con el modelo determinista (balance
  energético → trayectoria de peso). Si el plan no alcanza el objetivo en el
  plazo, o lo supera con demasiado margen, es incoherente aunque cada número
  esté bien.
- `adherence_stress_test`: simula incumplimientos realistas (saltarse comidas,
  comer fuera, perder una sesión, descontrol de finde). ¿Sigue aterrizando en
  un rango aceptable? Un plan que solo funciona con adherencia perfecta es frágil.
- `pick_best_of_n`: en perfiles complejos, elige entre 2-3 candidatos por ICP y
  penalización de fragilidad, justificando la elección.
- `common_sense_checklist`: pase corto final — ¿cantidades humanas? ¿la sesión
  cabe en el tiempo? ¿algo chirría?
- `is_canary`: los primeros N planes de una versión nueva van a ámbar sí o sí.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 1 kg de grasa corporal ≈ 7700 kcal. Cambio de peso ≈ balance acumulado / 7700.
KCAL_PER_KG = 7700.0


@dataclass
class TrajectoryPoint:
    week: int
    weight_kg: float


@dataclass
class TrajectoryResult:
    points: list[TrajectoryPoint]
    final_weight_kg: float
    total_change_kg: float
    reaches_goal: bool
    verdict: str  # ok | lento | rapido | sin_objetivo


def simulate_trajectory(
    *, weight_kg: float, tdee: float, target_kcal: float, weeks: int = 12,
    goal_weight_kg: float | None = None, adherence: float = 1.0,
) -> TrajectoryResult:
    """Proyecta la trayectoria de peso semana a semana por balance energético.
    `adherence` (0-1) atenúa el balance real (comer de más rebaja el déficit)."""
    daily_balance = (target_kcal - tdee)  # negativo = déficit
    # Adherencia imperfecta: al fallar, se tiende a MANTENIMIENTO (se pierde parte
    # del déficit o del superávit), no a invertirlo.
    effective_balance = daily_balance * max(0.0, min(1.0, adherence))
    weekly_kg = effective_balance * 7 / KCAL_PER_KG

    points, w = [], weight_kg
    for wk in range(1, weeks + 1):
        w = round(w + weekly_kg, 2)
        points.append(TrajectoryPoint(wk, w))
    total = round(w - weight_kg, 2)

    reaches, verdict = True, "sin_objetivo"
    if goal_weight_kg is not None:
        needed = goal_weight_kg - weight_kg
        if abs(needed) < 0.1:
            verdict = "ok"
        elif needed == 0:
            verdict = "ok"
        else:
            ratio = total / needed if needed else 0
            if ratio < 0.7:
                verdict, reaches = "lento", False
            elif ratio > 1.4:
                verdict, reaches = "rapido", False
            else:
                verdict = "ok"
    return TrajectoryResult(points, w, total, reaches, verdict)


@dataclass
class StressResult:
    scenario: str
    weekly_kg: float
    still_progresses: bool


def adherence_stress_test(
    *, weight_kg: float, tdee: float, target_kcal: float, goal_type: str,
) -> list[StressResult]:
    """Simula incumplimientos realistas y comprueba que el plan sigue aterrizando
    en la dirección correcta (no que sea perfecto)."""
    scenarios = {
        "adherencia_perfecta": 1.0,
        "salta_desayuno_3d": 0.9,
        "come_fuera_2x": 0.82,
        "pierde_1_sesion": 0.92,
        "descontrol_finde": 0.7,
    }
    out: list[StressResult] = []
    want_loss = goal_type == "fat_loss"
    want_gain = goal_type == "muscle_gain"
    for name, adh in scenarios.items():
        weekly = (target_kcal - tdee) * max(0.0, adh) * 7 / KCAL_PER_KG
        # "Progresa" = va en la dirección del objetivo (o mantiene si es el caso).
        if want_loss:
            ok = weekly < -0.05
        elif want_gain:
            ok = weekly > 0.02
        else:
            ok = abs(weekly) < 0.25
        out.append(StressResult(name, round(weekly, 3), ok))
    return out


@dataclass
class Candidate:
    label: str
    icp: float
    fragility: float = 0.0   # 0 robusto … 1 frágil (de la prueba de estrés)


def pick_best_of_n(candidates: list[Candidate]) -> tuple[Candidate, str]:
    """Elige el mejor candidato por ICP penalizado por fragilidad, con
    justificación. Empates → el de mayor ICP bruto."""
    if not candidates:
        raise ValueError("sin candidatos")
    scored = [(c.icp - 25 * c.fragility, c) for c in candidates]
    scored.sort(key=lambda x: (x[0], x[1].icp), reverse=True)
    best = scored[0][1]
    why = (f"Elegido '{best.label}' (ICP {best.icp:.0f}, fragilidad "
           f"{best.fragility:.2f}) sobre {len(candidates) - 1} alternativa(s): "
           "mejor confianza ajustada por robustez ante incumplimientos.")
    return best, why


def common_sense_checklist(nutrition: dict, training: dict | None,
                           *, session_max_min: int | None = None) -> list[str]:
    """Pase corto de sentido común. Devuelve la lista de cosas que 'chirrían'
    (vacía = todo humano). Complementa, no sustituye, a las validaciones finas."""
    issues: list[str] = []
    # ¿cantidades humanas? nº de comidas y kcal por comida sensatos
    meals = [m for m in (nutrition.get("meals") or []) if isinstance(m, dict)]
    for m in meals:
        k = float((m.get("target") or {}).get("kcal") or 0)
        if k > 1400:
            issues.append(f"una comida con {k:.0f} kcal es demasiado grande")
        if 0 < k < 100:
            issues.append(f"una comida con {k:.0f} kcal es demasiado pequeña")
    if training and session_max_min:
        for sess in training.get("sessions") or []:
            n = sum(int(e.get("sets") or 0) for e in sess.get("exercises") or [])
            est = n * 3 + 10
            if est > session_max_min * 1.3:
                issues.append(
                    f"la sesión '{sess.get('name', '?')}' (~{est} min) no cabe en "
                    f"{session_max_min} min")
    return issues


# --- Canario (§10 + §12): los primeros N planes de una versión → ámbar ---
CANARY_COUNT = 5


def is_canary(plans_with_version: int, threshold: int = CANARY_COUNT) -> bool:
    """True si aún estamos dentro de los primeros N planes de la versión actual:
    esos van a ÁMBAR sí o sí, independientemente de la puntuación."""
    return plans_with_version < threshold
