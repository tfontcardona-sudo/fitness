"""Motor de decisión de la revisión quincenal (hardening §8).

Decisión DETERMINISTA (no criterio del modelo): cada 15 días entra el seguimiento
del cliente y se decide QUÉ hacer con reglas fijas y auditables. Es el punto donde
estos sistemas se degradan, porque se trata como "un retoque". Reglas clave:

- Control de calidad del dato ANTES de decidir: un solo pesaje, o retención por
  ciclo menstrual, hacen que la decisión correcta sea NO tocar y pedir mejor
  registro — no inventar un ajuste sobre ruido.
- Media móvil / medias entre ventanas, nunca dato puntual contra dato puntual.
- Dentro del ritmo diana → NO tocar (la inercia es una decisión válida).
- Fuera de rango → ajustar kcal ±5-8% moviendo hidratos y grasa; la PROTEÍNA NO se
  toca.
- Adherencia <80% → PROHIBIDO tocar kcal (el problema es la ejecución).
- Peso estancado pero perímetros bajando y fuerza subiendo → recomposición en
  marcha: no tocar.
- Fatiga en rojo dos revisiones seguidas → diet break 7-10 días a mantenimiento.
- Refeed/diet break tras 8-12 semanas de déficit.

Cada decisión guarda la REGLA que la disparó y los datos de entrada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.services.metrics import weight_trend

# Umbrales (una sola fuente).
ADHERENCE_LOCK = 0.80          # < → no se tocan kcal, se trabaja adherencia
FATIGUE_RED = 4.0             # ≥ (sobre 5) = fatiga en rojo
KCAL_STEP_PCT = 0.06         # ±6% (dentro del 5-8% recomendado)
DEFICIT_WEEKS_FOR_BREAK = 8  # semanas de déficit → considerar refeed/diet break
RATE_TOLERANCE = 0.1         # holgura del ritmo (%/sem) antes de considerarlo fuera


@dataclass
class CheckinInputs:
    goal_type: str
    weight_kg: float
    target_rate_pct_week: tuple[float, float]     # ritmo diana con signo (%/sem)
    weight_points: list[tuple[date, float]]       # pesajes de la ventana
    prev_window_mean_kg: float | None = None      # media de la ventana anterior
    adherence_diet_ratio: float = 1.0             # 0..1
    perimeters_trend: str | None = None           # "down"|"up"|"flat"
    strength_trend: str | None = None             # "up"|"down"|"flat"
    fatigue_now: float | None = None              # media 1..5 (5 = peor)
    fatigue_prev: float | None = None             # fatiga de la revisión anterior
    weeks_in_deficit: int = 0
    single_measurement: bool = False              # un solo pesaje en la ventana
    menstrual_confound: bool = False              # posible retención por ciclo


@dataclass
class Decision:
    action: str          # hold | adjust_kcal | diet_break | work_adherence | request_data
    kcal_delta_pct: float = 0.0   # con signo; 0 si no se tocan las kcal
    protein_locked: bool = True   # la proteína NUNCA se mueve en un ajuste de kcal
    rule: str = ""
    rationale: str = ""
    notes: list[str] = field(default_factory=list)
    inputs_snapshot: dict = field(default_factory=dict)


def _actual_rate_pct_week(inp: CheckinInputs) -> float | None:
    """Ritmo real %/semana de peso corporal, por regresión de los pesajes
    (media móvil implícita). None si no hay datos suficientes."""
    if not inp.weight_points or inp.weight_kg <= 0:
        return None
    wt = weight_trend(inp.weight_points)
    if wt.weekly_rate_kg is None:
        return None
    return round(wt.weekly_rate_kg / inp.weight_kg * 100, 3)


def decide_biweekly(inp: CheckinInputs) -> Decision:
    """Aplica las reglas deterministas en orden de prioridad y devuelve la
    decisión con la regla disparada y los datos de entrada."""
    snap = {
        "goal_type": inp.goal_type, "adherence": inp.adherence_diet_ratio,
        "weeks_in_deficit": inp.weeks_in_deficit,
        "target_rate_pct_week": list(inp.target_rate_pct_week),
        "n_weigh_ins": len(inp.weight_points),
    }
    rate = _actual_rate_pct_week(inp)
    snap["actual_rate_pct_week"] = rate

    def d(action, **kw):
        kw.setdefault("inputs_snapshot", snap)
        return Decision(action=action, **kw)

    # 1) Calidad del dato: sin dato fiable, NO se decide sobre ruido.
    if inp.single_measurement or rate is None:
        return d("request_data", kcal_delta_pct=0.0, rule="dato_insuficiente",
                 rationale="Un solo pesaje (o ninguno) en la ventana: no se ajusta "
                 "sobre ruido. Pide más registros en las mismas condiciones.")
    if inp.menstrual_confound and inp.goal_type == "fat_loss" and rate > -RATE_TOLERANCE:
        return d("request_data", kcal_delta_pct=0.0, rule="posible_ciclo_menstrual",
                 rationale="Posible retención de líquidos por ciclo menstrual (mueve "
                 "1-2 kg de agua): no se toca; se confirma en la próxima ventana.")

    # 2) Adherencia baja: el problema es la ejecución, no el plan.
    if inp.adherence_diet_ratio < ADHERENCE_LOCK:
        return d("work_adherence", kcal_delta_pct=0.0, rule="adherencia_baja",
                 rationale=f"Adherencia {inp.adherence_diet_ratio*100:.0f}% < "
                 f"{ADHERENCE_LOCK*100:.0f}%: NO se tocan kcal. Se simplifica el plan y "
                 "se trabaja la adherencia; ajustar sobre baja adherencia enmascara la causa.")

    # 3) Fatiga en rojo dos revisiones seguidas → diet break.
    if (inp.fatigue_now or 0) >= FATIGUE_RED and (inp.fatigue_prev or 0) >= FATIGUE_RED:
        return d("diet_break", kcal_delta_pct=0.0, rule="fatiga_roja_2_revisiones",
                 rationale="Fatiga en rojo dos revisiones seguidas: diet break de 7-10 "
                 "días a mantenimiento antes de seguir.")

    # 4) Recomposición en marcha: peso plano pero perímetros ↓ y fuerza ↑.
    within = _within_target(rate, inp.target_rate_pct_week)
    if (abs(rate) < 0.2 and inp.perimeters_trend == "down"
            and inp.strength_trend == "up"):
        return d("hold", kcal_delta_pct=0.0, rule="recomposicion_en_marcha",
                 rationale="Peso estable pero perímetros bajando y fuerza subiendo: "
                 "recomposición en marcha. No se toca y se explica al cliente.")

    # 5) Dentro del ritmo diana → inercia (decisión válida e infravalorada).
    if within:
        dec = d("hold", kcal_delta_pct=0.0, rule="dentro_del_ritmo",
                rationale="El ritmo real está dentro de la diana: no se toca. Cambiar "
                "el plan por costumbre destruye la adherencia e impide saber qué funciona.")
        if inp.goal_type == "fat_loss" and inp.weeks_in_deficit >= DEFICIT_WEEKS_FOR_BREAK:
            dec.notes.append(
                f"{inp.weeks_in_deficit} semanas de déficit: considera un refeed "
                "semanal o diet break de 7 días."
            )
        return dec

    # 6) Fuera de rango → ajuste de kcal ±6% moviendo hidratos/grasa (proteína fija).
    lo, hi = sorted(inp.target_rate_pct_week)
    too_fast = rate < lo - RATE_TOLERANCE   # baja/gana MÁS rápido de lo diana
    if inp.goal_type == "fat_loss":
        # perder demasiado lento (rate por encima del techo) → más déficit (−kcal)
        delta = -KCAL_STEP_PCT if rate > hi + RATE_TOLERANCE else +KCAL_STEP_PCT if too_fast else 0.0
    elif inp.goal_type == "muscle_gain":
        # ganar demasiado lento → +kcal; demasiado rápido (grasa) → −kcal
        delta = +KCAL_STEP_PCT if rate < lo - RATE_TOLERANCE else -KCAL_STEP_PCT if rate > hi + RATE_TOLERANCE else 0.0
    else:
        delta = 0.0
    if delta == 0.0:
        return d("hold", rule="sin_cambio_neto",
                 rationale="El desvío no justifica un ajuste con signo claro: se mantiene.")
    return d("adjust_kcal", kcal_delta_pct=delta, protein_locked=True,
             rule="fuera_del_ritmo",
             rationale=f"Ritmo real {rate:+.2f}%/sem fuera de la diana "
             f"{lo:+.2f}..{hi:+.2f}: ajuste de kcal {delta*100:+.0f}% moviendo "
             "hidratos y grasa. La proteína NO se toca.")


def _within_target(rate: float, target: tuple[float, float]) -> bool:
    lo, hi = sorted(target)
    return (lo - RATE_TOLERANCE) <= rate <= (hi + RATE_TOLERANCE)
