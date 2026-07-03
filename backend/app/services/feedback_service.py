"""Orquestación del FEEDBACK quincenal del coach (cierre → informe).

A partir de un período CERRADO por el cliente:
1. reúne los registros diarios + datos de cierre + período anterior,
2. calcula TODAS las métricas con services/metrics (la IA nunca calcula),
3. pide a la IA SOLO la parte cualitativa (análisis y recomendaciones),
4. genera el documento Word con gráficas y lo persiste como FeedbackDoc,
5. marca el período como `analyzed` y guarda métricas/análisis.

Devuelve el FeedbackDoc creado. Reutilizable con un AIClient inyectado (tests).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, FeedbackDoc, Period, WorkoutLog
from app.services import metrics as M
from app.services.audit import log_event
from app.services.docs.feedback_doc import generate_feedback_doc
from app.services.docs.word_base import DocBrand
from app.services.storage import abs_path, client_dir, storage_root


class FeedbackError(RuntimeError):
    """No se pudo generar el feedback (datos insuficientes o fallo de IA)."""


def _doc_brand(db: Session) -> DocBrand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


def _prev_period(db: Session, period: Period) -> Period | None:
    return db.scalar(
        select(Period).where(
            Period.client_id == period.client_id,
            Period.period_index < period.period_index,
        ).order_by(Period.period_index.desc()).limit(1)
    )


def _perimeters(prev: Period | None, cur: Period) -> dict[str, list[tuple[str, float]]] | None:
    """Series de perímetros: período anterior (si hay) → actual."""
    fields = [("Cintura", "closing_waist_cm"), ("Cadera", "closing_hip_cm"),
              ("Brazo", "closing_arm_cm"), ("Muslo", "closing_thigh_cm")]
    out: dict[str, list[tuple[str, float]]] = {}
    for label, attr in fields:
        cur_v = getattr(cur, attr, None)
        if cur_v is None:
            continue
        series: list[tuple[str, float]] = []
        prev_v = getattr(prev, attr, None) if prev else None
        if prev_v is not None:
            series.append(("Anterior", prev_v))
        series.append(("Actual", cur_v))
        out[label] = series
    return out or None


def _photo_pairs(db: Session, prev: Period | None, cur: Period) -> list[tuple[str, str]] | None:
    """Empareja fotos por ángulo: período anterior vs actual."""
    from app.models import ProgressPhoto

    if not prev:
        return None
    def by_kind(pid: int) -> dict[str, str]:
        rows = db.scalars(select(ProgressPhoto).where(ProgressPhoto.period_id == pid))
        d: dict[str, str] = {}
        for ph in rows:
            try:
                p = abs_path(ph.file_path)
                if p.exists():
                    d[ph.kind] = str(p)
            except Exception:
                pass
        return d
    before, after = by_kind(prev.id), by_kind(cur.id)
    pairs = [(before[k], after[k]) for k in after if k in before]
    return pairs or None


def _workout_sets_for_logs(db: Session, log_ids: list[int]) -> list[dict]:
    if not log_ids:
        return []
    return [
        {"exercise_id": wl.exercise_id, "weight_kg": wl.weight_kg, "reps": wl.reps, "daily_log_id": wl.daily_log_id}
        for wl in db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(log_ids)))
    ]


def compute_period_summary(db: Session, period_id: int) -> dict:
    """Resumen de métricas del período SIN IA, a partir de lo que el cliente
    registró: cambio de peso corporal, adherencia, fuerza ganada (e1RM vs período
    anterior) y distancia al objetivo. Para el botón de feedback rápido del coach."""
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    client = db.get(Client, period.client_id)

    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period_id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    wt = M.weight_trend(raw_points)

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)

    # Fuerza: mejor e1RM por ejercicio este período vs el período anterior
    sets = _workout_sets_for_logs(db, [dl.id for dl in logs])
    progress = M.exercise_e1rm_progress(sets)[:6]
    prev = _prev_period(db, period)
    prev_best: dict[int, float] = {}
    if prev:
        prev_logs = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id == prev.id)))
        for p in M.exercise_e1rm_progress(_workout_sets_for_logs(db, list(prev_logs))):
            prev_best[p.exercise_id] = p.best_e1rm_kg
    ex_ids = {p.exercise_id for p in progress}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    strength = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
        "delta_kg": round(p.best_e1rm_kg - prev_best[p.exercise_id], 1) if p.exercise_id in prev_best else None,
    } for p in progress]

    current = period.closing_weight_kg if period.closing_weight_kg is not None else (
        wt.end_kg if wt.end_kg is not None else client.start_weight_kg
    )
    goal = client.goal_weight_kg
    distance = round(current - goal, 1) if (current is not None and goal is not None) else None

    return {
        "period_index": period.period_index,
        "status": period.status,
        "weight": {
            "start_kg": wt.start_kg, "end_kg": wt.end_kg,
            "delta_kg": wt.delta_kg, "weekly_rate_kg": wt.weekly_rate_kg,
        },
        "body_weight_now_kg": current,
        "goal_weight_kg": goal,
        "distance_to_goal_kg": distance,
        "adherence": {
            "diet_pct": round(adh.diet_adherence_ratio * 100),
            "log_pct": round(min(1.0, adh.log_ratio) * 100),
            "days_logged": adh.days_logged, "period_days": adh.period_days,
        },
        "strength": strength,
    }


def _gather_doc_inputs(db: Session, period: Period, client: Client) -> dict:
    """Reúne TODO lo calculado que necesita el documento de feedback (sin IA).
    Reutilizado por la generación y por la edición/regeneración."""
    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    period_days = (period.ends_on - period.starts_on).days + 1

    raw_points = [(dl.log_date, dl.weight_kg) for dl in logs if dl.weight_kg is not None]
    if period.closing_weight_kg is not None:
        raw_points.append((period.ends_on, period.closing_weight_kg))
    weight_points = [(f"{d.day}/{d.month}", w) for d, w in sorted(raw_points)]
    wt = M.weight_trend(raw_points)

    adh = M.adherence_summary([{
        "diet_adherence": dl.diet_adherence, "sleep_hours": dl.sleep_hours,
        "energy_1_5": dl.energy_1_5, "mood_1_5": dl.mood_1_5, "fatigue_1_5": dl.fatigue_1_5,
    } for dl in logs], period_days)

    sets = _workout_sets_for_logs(db, [dl.id for dl in logs])
    progress = M.exercise_e1rm_progress(sets)[:5]
    ex_ids = {p.exercise_id for p in progress} | {s["exercise_id"] for s in sets}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    e1rm_exercises = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
    } for p in progress]

    weeks = max(1.0, period_days / 7)
    vol_counts: dict[str, float] = {}
    for s in sets:
        info = ex_info.get(s["exercise_id"])
        group = info.muscle_primary if info else "otros"
        vol_counts[group] = vol_counts.get(group, 0) + 1
    volume_by_group = {g: round(c / weeks, 1) for g, c in vol_counts.items()} or None

    prev = _prev_period(db, period)
    pm = M.PeriodMetrics(weight=wt, adherence=adh, exercise_progress=progress)
    return {
        "weight_points": weight_points, "e1rm_exercises": e1rm_exercises,
        "perimeters": _perimeters(prev, period),
        "volume_by_group": volume_by_group,
        "photo_pairs": _photo_pairs(db, prev, period),
        "metrics_json": pm.to_json(),
    }


def _write_feedback_doc(db: Session, client: Client, period: Period, inputs: dict, ai_out) -> str:
    """Genera el .docx con las gráficas + el texto (de la IA o editado) y lo guarda."""
    docx = generate_feedback_doc(
        brand=_doc_brand(db), client_name=client.full_name, period_index=period.period_index,
        metrics=inputs["metrics_json"], weight_points=inputs["weight_points"],
        goal_kg=client.goal_weight_kg, e1rm_exercises=inputs["e1rm_exercises"],
        perimeters=inputs["perimeters"], volume_by_group=inputs["volume_by_group"],
        photo_pairs=inputs["photo_pairs"],
        ai_photo_analysis=ai_out.ai_photo_analysis if inputs["photo_pairs"] else None,
        natural_analysis=ai_out.natural_analysis, changes_bullets=ai_out.changes_bullets,
        answers=ai_out.answers, next_objectives=ai_out.next_objectives,
        closing_message=ai_out.closing_message,
        plan_adjustments=[
            {"area": a.area, "change": a.change, "reason": a.reason}
            for a in getattr(ai_out, "plan_adjustments", []) or []
        ],
    )
    folder = client_dir(client.id, "feedback")
    fname = f"feedback_p{period.period_index}.docx"
    (folder / fname).write_bytes(docx)
    return str((folder / fname).relative_to(storage_root()))


def build_period_feedback(db: Session, period_id: int, ai=None) -> FeedbackDoc:
    """Genera y persiste el feedback (borrador) de un período cerrado."""
    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.feedback import generate_feedback_analysis

    ai = ai or AIClient()
    period = db.get(Period, period_id)
    if not period:
        raise FeedbackError("Período no encontrado")
    if period.status == "open":
        raise FeedbackError("El período aún no está cerrado por el cliente")
    client = db.get(Client, period.client_id)

    inputs = _gather_doc_inputs(db, period, client)
    logs_q = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    payload = {
        "objetivo": client.goal_type, "peso_objetivo_kg": client.goal_weight_kg,
        "periodo_index": period.period_index, "metricas": inputs["metrics_json"],
        # Registro DIARIO crudo del cliente (para que la IA lo interprete)
        "registro_diario": [{
            "fecha": dl.log_date.isoformat(), "peso": dl.weight_kg, "sueno_h": dl.sleep_hours,
            "pasos": dl.steps, "saciedad_1_10": dl.satiety_1_10, "agua_l": dl.water_liters,
            "adherencia_dieta": dl.diet_adherence, "notas": dl.free_notes,
        } for dl in logs_q],
        # REVISIÓN QUINCENAL completa
        "revision_quincenal": {
            "peso_kg": period.closing_weight_kg,
            "medidas_cm": {"cintura": period.closing_waist_cm, "cadera": period.closing_hip_cm,
                           "brazo": period.closing_arm_cm, "muslo": period.closing_thigh_cm},
            "sensaciones_1_5": period.closing_feelings_json,
            "adherencia_dieta_0_10": period.adherence_diet_0_10,
            "adherencia_entreno_0_10": period.adherence_training_0_10,
            "comidas_libres": period.free_meals_count,
            "cambios_importantes": period.closing_changes,
            "lo_mas_dificil": period.closing_hardest,
            "objetivo_proximo": period.closing_next_goal,
            "dudas": period.closing_questions,
            "valoracion_1_5": period.closing_rating,
        },
        "hay_fotos": bool(inputs["photo_pairs"]),
    }
    try:
        ai_out = generate_feedback_analysis(payload, ai)
    except AIGenerationError as exc:
        raise FeedbackError(f"La IA no devolvió un feedback válido: {exc}") from exc

    docx_rel = _write_feedback_doc(db, client, period, inputs, ai_out)
    fb = FeedbackDoc(period_id=period.id, kind="biweekly",
                     content_json={**ai_out.model_dump(), "metrics": inputs["metrics_json"],
                                   "weight_points": inputs["weight_points"],
                                   "goal_weight_kg": client.goal_weight_kg},
                     docx_path=docx_rel)
    db.add(fb)
    period.status = "analyzed"
    period.metrics_json = inputs["metrics_json"]
    period.ai_analysis_json = ai_out.model_dump()
    period.ai_photo_analysis = ai_out.ai_photo_analysis
    db.flush()
    log_event(db, "period", period.id, "feedback_generated", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb


_TEXT_FIELDS = ("natural_analysis", "changes_bullets", "plan_adjustments", "answers",
                "next_objectives", "closing_message", "ai_photo_analysis")


def update_feedback_text(db: Session, feedback_id: int, text: dict) -> FeedbackDoc:
    """Edición MANUAL del feedback por el coach: actualiza el texto, **regenera el
    Word** y refresca lo que verá el cliente. No recalcula métricas ni llama a la IA."""
    from app.services.ai.feedback import FeedbackAIOutput

    fb = db.get(FeedbackDoc, feedback_id)
    if not fb:
        raise FeedbackError("Feedback no encontrado")
    period = db.get(Period, fb.period_id)
    client = db.get(Client, period.client_id)

    current = dict(fb.content_json or {})
    metrics = current.get("metrics")
    merged = {k: current.get(k) for k in _TEXT_FIELDS}
    for k, v in (text or {}).items():
        if k in merged:
            merged[k] = v
    ai_out = FeedbackAIOutput.model_validate(merged)

    inputs = _gather_doc_inputs(db, period, client)
    fb.docx_path = _write_feedback_doc(db, client, period, inputs, ai_out)
    fb.content_json = {**ai_out.model_dump(), "metrics": metrics or inputs["metrics_json"],
                       "weight_points": inputs["weight_points"],
                       "goal_weight_kg": client.goal_weight_kg}
    period.ai_analysis_json = ai_out.model_dump()
    db.flush()
    log_event(db, "period", period.id, "feedback_edited", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb
