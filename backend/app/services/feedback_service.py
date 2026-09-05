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
from app.services import packages as pkgs


class FeedbackError(RuntimeError):
    """No se pudo generar el feedback (datos insuficientes o fallo de IA)."""


from app.services.branding import fila_de_marca


def _doc_brand(db: Session, client=None) -> DocBrand:
    """Delega en la ÚNICA función de marca de documentos (`plan_delivery`):
    tres copias del mismo código eran tres sitios donde arreglar el logo."""
    from app.services.plan_delivery import doc_brand

    return doc_brand(db, client)

def _prev_period(db: Session, period: Period) -> Period | None:
    return db.scalar(
        select(Period).where(
            Period.client_id == period.client_id,
            Period.period_index < period.period_index,
        ).order_by(Period.period_index.desc()).limit(1)
    )


def _perimeters(prev: Period | None, cur: Period,
                client=None) -> dict[str, list[tuple[str, float]]] | None:
    """Series de perímetros: período anterior (si hay) → actual. En la PRIMERA
    revisión el "antes" son los perímetros INICIALES de la anamnesis (mig.
    0041): sin ellos el primer informe no podía enseñar el delta de medidas —
    justo la prueba de progreso cuando la báscula no se mueve (recomp)."""
    fields = [("Cintura", "closing_waist_cm"), ("Cadera", "closing_hip_cm"),
              ("Brazo", "closing_arm_cm"), ("Muslo", "closing_thigh_cm")]
    out: dict[str, list[tuple[str, float]]] = {}
    fuentes: set[str] = set()
    crudo: dict[str, tuple[float | None, float]] = {}
    for label, attr in fields:
        cur_v = getattr(cur, attr, None)
        if cur_v is None:
            continue
        prev_v = getattr(prev, attr, None) if prev else None
        if prev_v is not None:
            fuentes.add("Anterior")
        elif client is not None:
            prev_v = getattr(client, attr.replace("closing_", "initial_"), None)
            if prev_v is not None:
                fuentes.add("Inicio")
        crudo[label] = (prev_v, cur_v)
    # UNA sola etiqueta para la columna del "antes". Si unas medidas vienen del
    # cierre anterior y otras de la anamnesis, dos etiquetas distintas parten
    # la rejilla en tres columnas y descolocan las series (la gráfica acababa
    # pintando el antes de una medida sobre el ahora de otra).
    etiqueta_prev = ("Antes" if len(fuentes) > 1
                     else (fuentes.pop() if fuentes else "Anterior"))
    for label, (prev_v, cur_v) in crudo.items():
        series: list[tuple[str, float]] = []
        if prev_v is not None:
            series.append((etiqueta_prev, prev_v))
        series.append(("Actual", cur_v))
        out[label] = series
    return out or None


def _photo_pairs(db: Session, prev: Period | None, cur: Period) -> list[tuple[str, str]] | None:
    """Empareja fotos por ángulo: el "antes" contra las de este período.

    En la PRIMERA revisión el "antes" son las fotos INICIALES de la anamnesis
    (las que el cliente sube al terminar el cuestionario, guardadas sin
    período): mismo criterio que los perímetros iniciales. Antes se devolvía
    None y el primer informe —el que más necesita enseñar el cambio— salía sin
    comparativa aunque las fotos existieran.
    """
    from app.models import ProgressPhoto

    def _por_angulo(consulta) -> dict[str, str]:
        d: dict[str, str] = {}
        for ph in db.scalars(consulta):
            try:
                p = abs_path(ph.file_path)
                if p.exists():
                    d[ph.kind] = str(p)
            except Exception:  # noqa: BLE001
                pass
        return d

    after = _por_angulo(select(ProgressPhoto).where(ProgressPhoto.period_id == cur.id))
    if not after:
        return None
    if prev is not None:
        before = _por_angulo(
            select(ProgressPhoto).where(ProgressPhoto.period_id == prev.id))
    else:
        before = _por_angulo(
            select(ProgressPhoto).where(ProgressPhoto.client_id == cur.client_id,
                                        ProgressPhoto.period_id.is_(None)))
    pairs = [(before[k], after[k]) for k in after if k in before]
    return pairs or None


def _workout_sets_for_logs(db: Session, log_ids: list[int]) -> list[dict]:
    if not log_ids:
        return []
    return [
        {"exercise_id": wl.exercise_id, "weight_kg": wl.weight_kg, "reps": wl.reps, "daily_log_id": wl.daily_log_id}
        for wl in db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id.in_(log_ids)))
    ]


def sets_por_periodo(db: Session, period_ids: list[int]) -> dict[int, list[dict]]:
    """Series de entreno de VARIOS períodos en UNA consulta, agrupadas por período.

    La usa quien va a resumir varios períodos seguidos (la pestaña Historial):
    `compute_period_summary` compara cada período con TODOS los anteriores, así
    que llamarlo en bucle releía las mismas series una y otra vez —coste
    cuadrático— aunque cada llamada suelta esté bien optimizada.
    """
    if not period_ids:
        return {}
    filas = db.execute(
        select(DailyLog.period_id, WorkoutLog.exercise_id, WorkoutLog.weight_kg,
               WorkoutLog.reps, WorkoutLog.daily_log_id)
        .join(WorkoutLog, WorkoutLog.daily_log_id == DailyLog.id)
        .where(DailyLog.period_id.in_(period_ids))
    ).all()
    out: dict[int, list[dict]] = {pid: [] for pid in period_ids}
    for pid, ex_id, w, reps, dlid in filas:
        out.setdefault(pid, []).append(
            {"exercise_id": ex_id, "weight_kg": w, "reps": reps, "daily_log_id": dlid})
    return out


def compute_period_summary(db: Session, period_id: int, *,
                           cache_sets: dict[int, list[dict]] | None = None) -> dict:
    """Resumen de métricas del período SIN IA, a partir de lo que el cliente
    registró: cambio de peso corporal, adherencia, fuerza ganada (e1RM vs período
    anterior) y distancia al objetivo. Para el botón de feedback rápido del coach.

    `cache_sets` (opcional): series YA cargadas por período (ver
    `sets_por_periodo`). Quien resume varios períodos seguidos las trae de una
    vez y evita releerlas en cada iteración; el resultado es idéntico."""
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

    # Fuerza POR GRUPO MUSCULAR: el ejercicio más relevante de cada grupo (mayor
    # e1RM), con kg medios levantados y repes medias, comparado con la última
    # revisión ANTERIOR que tenga datos de ese ejercicio (no solo la inmediata):
    # kg subidos/bajados reales, Δe1RM y % de ganancia o pérdida de fuerza.
    sets = (cache_sets.get(period_id, []) if cache_sets is not None
            else _workout_sets_for_logs(db, [dl.id for dl in logs]))
    progress_all = M.exercise_e1rm_progress(sets)

    def _avg_by_ex(ss: list[dict]) -> dict[int, tuple[float, float]]:
        by: dict[int, list[dict]] = {}
        for s in ss:
            if s.get("weight_kg") and s.get("reps"):
                by.setdefault(s["exercise_id"], []).append(s)
        return {k: (sum(x["weight_kg"] for x in v) / len(v),
                    sum(x["reps"] for x in v) / len(v)) for k, v in by.items()}

    avg_now = _avg_by_ex(sets)
    # Períodos anteriores, del más reciente al más antiguo: el primer dato que
    # exista por ejercicio es la referencia de comparación. UNA sola consulta
    # (join) para todos los períodos: sin N consultas por período.
    prev_best: dict[int, float] = {}
    prev_avg: dict[int, tuple[float, float]] = {}
    earlier_ids = list(db.scalars(
        select(Period.id).where(Period.client_id == period.client_id,
                                Period.period_index < period.period_index)
        .order_by(Period.period_index.desc())
    ))
    if earlier_ids:
        if cache_sets is not None:
            sets_by_period = {pid: cache_sets.get(pid, []) for pid in earlier_ids}
        else:
            rows = db.execute(
                select(DailyLog.period_id, WorkoutLog.exercise_id,
                       WorkoutLog.weight_kg, WorkoutLog.reps, WorkoutLog.daily_log_id)
                .join(WorkoutLog, WorkoutLog.daily_log_id == DailyLog.id)
                .where(DailyLog.period_id.in_(earlier_ids))
            ).all()
            sets_by_period = {}
            for pid, ex_id, w, reps, dlid in rows:
                sets_by_period.setdefault(pid, []).append(
                    {"exercise_id": ex_id, "weight_kg": w, "reps": reps, "daily_log_id": dlid}
                )
        for prev_id in earlier_ids:  # ya en orden descendente
            prev_sets = sets_by_period.get(prev_id) or []
            for p in M.exercise_e1rm_progress(prev_sets):
                prev_best.setdefault(p.exercise_id, p.best_e1rm_kg)
            for ex_id, avg in _avg_by_ex(prev_sets).items():
                prev_avg.setdefault(ex_id, avg)

    ex_ids = {p.exercise_id for p in progress_all}
    ex_info = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}

    # El más relevante de cada grupo muscular primero; luego completa hasta 8.
    picked: list = []
    seen_groups: set[str] = set()
    for p in progress_all:  # ya viene ordenado por e1RM desc
        g = ex_info[p.exercise_id].muscle_primary if p.exercise_id in ex_info else "otros"
        if g not in seen_groups:
            seen_groups.add(g)
            picked.append(p)
    for p in progress_all:
        if len(picked) >= 8:
            break
        if p not in picked:
            picked.append(p)
    picked = picked[:8]

    def _row(p) -> dict:
        prev_rm = prev_best.get(p.exercise_id)
        delta = round(p.best_e1rm_kg - prev_rm, 1) if prev_rm is not None else None
        aw, ar = avg_now.get(p.exercise_id, (None, None))
        paw = prev_avg.get(p.exercise_id, (None, None))[0]
        return {
            "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
            "muscle": ex_info[p.exercise_id].muscle_primary if p.exercise_id in ex_info else None,
            "e1rm_kg": p.best_e1rm_kg,
            "delta_kg": delta,
            "pct": round(delta / prev_rm * 100, 1) if (delta is not None and prev_rm) else None,
            "avg_weight_kg": round(aw, 1) if aw is not None else None,
            "avg_reps": round(ar, 1) if ar is not None else None,
            "avg_weight_delta_kg": round(aw - paw, 1) if (aw is not None and paw is not None) else None,
        }

    strength = [_row(p) for p in picked]

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
            # None = SIN registros de dieta (no es un 0 % de incumplimiento):
            # la pantalla lo dice con "Sin datos" en vez de acusar al cliente.
            "diet_pct": (round(adh.diet_adherence_ratio * 100)
                         if (adh.diet_yes + adh.diet_partial + adh.diet_no) > 0
                         else None),
            "log_pct": round(min(1.0, adh.log_ratio) * 100),
            "days_logged": adh.days_logged, "period_days": adh.period_days,
            # Días que SIGUIÓ el plan (dieta): completos y a medias, para poder
            # decir "12 de 15 días" además del porcentaje.
            "diet_days_yes": adh.diet_yes, "diet_days_partial": adh.diet_partial,
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

    # DELTA vs el período anterior: la sección se llama "Progresión de fuerza"
    # y solo enseñaba valores absolutos — el "+2,5 kg" que el cliente quiere
    # ver ya lo sabe pintar la gráfica (charts.e1rm_chart, delta_kg).
    prev_for_delta = _prev_period(db, period)
    prev_best: dict[int, float] = {}
    if prev_for_delta is not None:
        prev_logs = db.scalars(
            select(DailyLog.id).where(DailyLog.period_id == prev_for_delta.id)
        ).all()
        if prev_logs:
            prev_sets = _workout_sets_for_logs(db, list(prev_logs))
            for pp in M.exercise_e1rm_progress(prev_sets):
                prev_best[pp.exercise_id] = pp.best_e1rm_kg
    e1rm_exercises = [{
        "name": ex_info[p.exercise_id].canonical_name if p.exercise_id in ex_info else f"#{p.exercise_id}",
        "e1rm_kg": p.best_e1rm_kg,
        **({"delta_kg": round(p.best_e1rm_kg - prev_best[p.exercise_id], 1)}
           if p.exercise_id in prev_best else {}),
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
        "perimeters": _perimeters(prev, period, client),
        "volume_by_group": volume_by_group,
        "photo_pairs": _photo_pairs(db, prev, period),
        "metrics_json": pm.to_json(),
    }


_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _period_label(period: Period) -> str | None:
    """"Del 1 al 14 de agosto de 2026" — el rango real del período, que es lo
    que el cliente busca al comparar informes ("Período 7" no le dice nada)."""
    a, b = period.starts_on, period.ends_on
    if not a or not b:
        return None
    if a.month == b.month:
        return f"Del {a.day} al {b.day} de {_MESES_ES[b.month - 1]} de {b.year}"
    return (f"Del {a.day} de {_MESES_ES[a.month - 1]} al {b.day} de "
            f"{_MESES_ES[b.month - 1]} de {b.year}")


def _goal_label_es(goal: str | None) -> str | None:
    return {"fat_loss": "Objetivo: pérdida de grasa",
            "muscle_gain": "Objetivo: ganancia muscular",
            "recomp": "Objetivo: recomposición corporal",
            "maintenance": "Objetivo: mantenimiento",
            "injury_recovery": "Objetivo: recuperación de lesión"}.get(goal or "")


def _write_feedback_doc(db: Session, client: Client, period: Period, inputs: dict, ai_out) -> str:
    """Genera el .docx con las gráficas + el texto (de la IA o editado) y lo guarda."""
    docx = generate_feedback_doc(
        brand=_doc_brand(db, client), client_name=client.full_name, period_index=period.period_index,
        period_label=_period_label(period), goal_label=_goal_label_es(client.goal_type),
        # Lo contratado manda también en el DOCUMENTO (ya mandaba en el prompt
        # de la IA): a un cliente de solo entrenamiento no se le puede reprochar
        # por escrito una "adherencia dieta 0 %".
        has_nutrition=pkgs.has_nutrition(client.package_tier),
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
    # Paquete solo-nutrición (Nutri): el feedback no habla de entreno.
    nutrition_only = not pkgs.has_training(getattr(client, "package_tier", None))
    # Y el simétrico (Train): no habla de dieta. Sin esto, el informe le
    # hablaba de calorías y adherencia a la dieta a quien no la ha contratado.
    training_only = not pkgs.has_nutrition(getattr(client, "package_tier", None))

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
            # En solo-entreno no hay dieta que reportar (ni el cliente ve
            # esos campos en su portal: irían siempre a null).
            **({} if training_only else {
                "adherencia_dieta_0_10": period.adherence_diet_0_10}),
            # En solo-nutrición no hay adherencia de entreno que reportar.
            **({} if nutrition_only else {"adherencia_entreno_0_10": period.adherence_training_0_10}),
            **({} if training_only else {"comidas_libres": period.free_meals_count}),
            "cambios_importantes": period.closing_changes,
            "lo_mas_dificil": period.closing_hardest,
            "objetivo_proximo": period.closing_next_goal,
            "dudas": period.closing_questions,
            "valoracion_1_5": period.closing_rating,
        },
        "hay_fotos": bool(inputs["photo_pairs"]),
    }
    # §8 (hardening): raíl de decisión DETERMINISTA. Se calcula sin IA a partir
    # del cierre, ANTES de la llamada — y viaja en el payload como CONTRATO: la
    # IA redacta sus ajustes ALINEADOS con esta decisión, no la contradice.
    from app.services.biweekly_period import decision_for_period, decision_to_json

    biweekly = decision_to_json(decision_for_period(db, period, client))
    payload["decision_determinista"] = {
        **biweekly,
        "instruccion": (
            "Esta decisión la calculó el sistema con reglas fijas y ES LA QUE MANDA "
            "sobre las calorías. Redacta tus 'plan_adjustments' alineados con ella: "
            "si action != 'adjust_kcal', NO propongas subir ni bajar calorías; si es "
            "'adjust_kcal', usa exactamente su kcal_delta_pct."
        ),
    }
    try:
        ai_out = generate_feedback_analysis(payload, ai, nutrition_only=nutrition_only,
                                            training_only=training_only)
    except AIGenerationError as exc:
        raise FeedbackError(f"La IA no devolvió un feedback válido: {exc}") from exc

    docx_rel = _write_feedback_doc(db, client, period, inputs, ai_out)
    content = {**ai_out.model_dump(), "metrics": inputs["metrics_json"],
               "weight_points": inputs["weight_points"],
               "biweekly_decision": biweekly,
               "goal_weight_kg": client.goal_weight_kg}
    # Regenerar NO duplica: si el período ya tiene feedback, se reemplaza su
    # contenido (mismo doc, mismo id) en vez de apilar un segundo documento.
    fb = db.scalar(select(FeedbackDoc).where(FeedbackDoc.period_id == period.id)
                   .order_by(FeedbackDoc.id.desc()).limit(1))
    if fb is not None:
        fb.content_json = content
        fb.docx_path = docx_rel
        # NO se fuerza a borrador: si el cliente YA había recibido este feedback,
        # se conserva enviado (con el texto actualizado) para no ocultárselo al
        # regenerar. Si seguía en borrador (sent_at None), continúa en borrador.
    else:
        fb = FeedbackDoc(period_id=period.id, kind="biweekly",
                         content_json=content, docx_path=docx_rel)
        db.add(fb)
    period.status = "analyzed"
    period.metrics_json = inputs["metrics_json"]
    period.ai_analysis_json = {**ai_out.model_dump(), "biweekly_decision": biweekly}
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
    # Se PRESERVAN las claves no textuales ya persistidas (biweekly_decision y
    # cualquier otra futura): editar una frase no puede borrar el raíl auditable.
    fb.content_json = {**current, **ai_out.model_dump(),
                       "metrics": metrics or inputs["metrics_json"],
                       "weight_points": inputs["weight_points"],
                       "goal_weight_kg": client.goal_weight_kg}
    period.ai_analysis_json = {**(period.ai_analysis_json or {}), **ai_out.model_dump()}
    db.flush()
    log_event(db, "period", period.id, "feedback_edited", {"feedback_id": fb.id})
    db.commit()
    db.refresh(fb)
    return fb
