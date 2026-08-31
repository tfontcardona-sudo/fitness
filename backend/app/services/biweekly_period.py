"""Puente entre el cierre de período y el motor de decisión quincenal (hardening §8).

Reúne desde la base de datos (Period + Client + DailyLog) las entradas que necesita
`decide_biweekly` y devuelve la decisión DETERMINISTA con la regla que la disparó.
Se calcula sin IA: es el "raíl" auditable que acompaña al análisis del modelo, no el
criterio del modelo. Testeable en CI de punta a punta (no toca la API de Anthropic).
"""
from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, DailyLog, Period, Plan
from app.services import metrics as M
from app.services.biweekly_engine import CheckinInputs, Decision, decide_biweekly


def _trend(prev: float | None, cur: float | None, *, eps: float = 0.3) -> str | None:
    """Clasifica una serie de dos puntos: 'down' | 'up' | 'flat'. `eps` evita que el
    ruido de la cinta métrica se lea como tendencia."""
    if prev is None or cur is None:
        return None
    if cur < prev - eps:
        return "down"
    if cur > prev + eps:
        return "up"
    return "flat"


def _strength_trend(db: Session, period: Period, prev: Period | None) -> str | None:
    """Fuerza subiendo/bajando comparando el mejor e1RM del período con el anterior.
    Sin dato del período anterior no se afirma tendencia (None)."""
    from app.services.feedback_service import _workout_sets_for_logs

    def best_e1rm(p: Period) -> float | None:
        log_ids = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id == p.id)))
        if not log_ids:
            return None
        prog = M.exercise_e1rm_progress(_workout_sets_for_logs(db, log_ids))
        return prog[0].best_e1rm_kg if prog else None

    cur = best_e1rm(period)
    if cur is None or prev is None:
        return None
    old = best_e1rm(prev)
    if old is None:
        return None
    if cur > old * 1.01:
        return "up"
    if cur < old * 0.99:
        return "down"
    return "flat"


def _adherence_ratio(period: Period, adh: M.AdherenceSummary) -> float:
    """Adherencia de dieta 0..1. Prioriza el 0-10 que reporta el cliente al cerrar;
    si falta, cae al ratio derivado del registro diario."""
    if period.adherence_diet_0_10 is not None:
        return max(0.0, min(1.0, period.adherence_diet_0_10 / 10.0))
    # 0.0 real (todo "no") es un DATO, no una ausencia: el `or 1.0` anterior
    # convertía al peor cliente en adherencia perfecta y el motor ajustaba kcal
    # en vez de bloquear (auditoría #6). Sin registros de dieta → 1.0 neutro.
    n_regs = adh.diet_yes + adh.diet_partial + adh.diet_no
    if n_regs <= 0:
        return 1.0
    return max(0.0, min(1.0, adh.diet_adherence_ratio))


def _weeks_in_deficit(db: Session, client: Client, period: Period) -> int:
    """Semanas acumuladas en déficit REAL (solo fat_loss): ~2 semanas por cada
    período hasta el actual cuyo plan tenía target_kcal < tdee_kcal. Antes se
    contaban TODOS los períodos, así que un mantenimiento o diet break intermedio
    seguía sumando y el aviso de refeed/diet break llegaba inflado."""
    if client.goal_type != "fat_loss":
        return 0
    rows = db.execute(
        select(Plan.nutrition_json)
        .join(Period, Period.plan_id == Plan.id)
        .where(
            Period.client_id == period.client_id,
            Period.period_index <= period.period_index,
        )
    ).all()
    n_deficit = 0
    for (nut,) in rows:
        nut = nut or {}
        tk, td = nut.get("target_kcal"), nut.get("tdee_kcal")
        if tk and td:
            if float(tk) < float(td):
                n_deficit += 1
        else:
            # Plan legado sin kcal/tdee: con objetivo fat_loss se asume déficit
            # (mejor avisar de más del diet break que de menos).
            n_deficit += 1
    return n_deficit * 2


def _menstrual_confound(client: Client, raw_points: list[tuple]) -> bool:
    """Posible retención por ciclo menstrual: mujer + repunte de peso concentrado
    en los últimos días de la ventana (≥0,5 kg sobre la media previa). Heurística
    conservadora: exige ≥5 pesajes para no confundir ruido con retención. El motor
    solo la usa en fat_loss con ritmo estancado (regla `posible_ciclo_menstrual`)."""
    if (client.sex or "").lower() != "female":
        return False
    if len(raw_points) < 5:
        return False
    tail = [w for _, w in raw_points[-3:]]
    head = [w for _, w in raw_points[:-3]]
    if not head:
        return False
    return (sum(tail) / len(tail)) - (sum(head) / len(head)) >= 0.5


def checkin_inputs_from_period(db: Session, period: Period, client: Client) -> CheckinInputs:
    """Construye las entradas deterministas del motor quincenal a partir del período
    cerrado. No llama a la IA."""
    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        ultimo = max(raw_points, key=lambda x: x[0]) if raw_points else None
        # El peso de cierre solo cuenta como MEDICIÓN NUEVA si de verdad lo es.
        # Cuando el coach cierra la quincena por el cliente, el peso de cierre
        # se COPIA de su último pesaje del diario: añadirlo como punto aparte
        # fabricaba una segunda medición inexistente, anulaba el guardarraíl de
        # "un solo pesaje → no se ajusta sobre ruido" y la regresión daba
        # 0,00 %/semana → el motor recortaba un −6 % de calorías REAL a partir
        # de un dato inventado por el propio sistema. Justo en los clientes
        # para los que ese guardarraíl se diseñó.
        if ultimo is None or abs(float(ultimo[1]) - float(period.closing_weight_kg)) > 1e-6:
            raw_points.append((period.ends_on, period.closing_weight_kg))
    raw_points.sort()

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)
    adherence_ratio = _adherence_ratio(period, adh)

    weight_kg = (period.closing_weight_kg
                 or (raw_points[-1][1] if raw_points else None)
                 or client.current_weight_kg or 0.0)

    age = M.age_from_birth(client.birth_date) if client.birth_date else 30
    adj = M.individualized_energy_adjustment(
        client.goal_type or "maintenance", client.sex or "male",
        client.body_fat_pct, client.level, adherence_ratio,
    )

    prev = db.scalar(
        select(Period).where(
            Period.client_id == period.client_id,
            Period.period_index < period.period_index,
        ).order_by(Period.period_index.desc()).limit(1)
    )
    prev_mean = None
    fatigue_prev = None
    if prev is not None:
        prev_logs = list(db.scalars(
            select(DailyLog).where(DailyLog.period_id == prev.id)
        ))
        prev_weights = [dl.weight_kg for dl in prev_logs if dl.weight_kg is not None]
        if prev.closing_weight_kg is not None:
            prev_weights.append(prev.closing_weight_kg)
        if prev_weights:
            prev_mean = round(sum(prev_weights) / len(prev_weights), 2)
        prev_adh = M.adherence_summary([{"fatigue_1_5": dl.fatigue_1_5} for dl in prev_logs], 1)
        fatigue_prev = prev_adh.mean_fatigue

    return CheckinInputs(
        goal_type=client.goal_type or "maintenance",
        weight_kg=weight_kg,
        target_rate_pct_week=(adj.rate_lo, adj.rate_hi),
        weight_points=raw_points,
        prev_window_mean_kg=prev_mean,
        adherence_diet_ratio=adherence_ratio,
        perimeters_trend=_trend(
            prev.closing_waist_cm if prev else None, period.closing_waist_cm),
        strength_trend=_strength_trend(db, period, prev),
        fatigue_now=adh.mean_fatigue,
        fatigue_prev=fatigue_prev,
        weeks_in_deficit=_weeks_in_deficit(db, client, period),
        single_measurement=len(raw_points) <= 1,
        menstrual_confound=_menstrual_confound(client, raw_points),
    )


def decision_for_period(db: Session, period: Period, client: Client) -> Decision:
    """Decisión quincenal determinista para un período cerrado (regla + snapshot)."""
    return decide_biweekly(checkin_inputs_from_period(db, period, client))


def decision_to_json(dec: Decision) -> dict:
    """Serializa la decisión para persistirla junto al análisis y mostrarla al coach."""
    return asdict(dec)
