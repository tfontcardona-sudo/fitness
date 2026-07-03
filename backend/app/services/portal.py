"""Lógica de presentación del portal del cliente (G.4).

Resuelve "el plan y período vigentes" de un cliente y arma la vista HOY a
partir del plan publicado y los registros del día. Mantener esto fuera del
router permite testearlo y reutilizarlo (p. ej. el documento Word offline de
seguimiento de la Fase 7 parte de la misma estructura día a día).

La vista HOY mapea el día de la semana actual a la sesión de entrenamiento
correspondiente del plan y a las comidas del día (banco flexible: las 7
opciones por slot; estricto: el plato del día).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig, Client, DailyLog, Exercise, Period, Plan

DAY_LABELS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DAY_SLUGS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente no analizado (el que el cliente está viviendo)."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def published_plan_for_period(db: Session, period: Period) -> Plan | None:
    return db.get(Plan, period.plan_id)


def latest_published_plan(db: Session, client_id: int) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc())
        .limit(1)
    )


def period_info(period: Period | None, today: date) -> dict | None:
    if period is None:
        return None
    days_total = (period.ends_on - period.starts_on).days + 1
    days_elapsed = max(0, min(days_total, (today - period.starts_on).days + 1))
    days_left = max(0, (period.ends_on - today).days)
    # Cierre disponible desde el día 14 del período (G.4)
    can_close = days_elapsed >= 14 and period.status == "open"
    return {
        "period_id": period.id,
        "period_index": period.period_index,
        "starts_on": period.starts_on,
        "ends_on": period.ends_on,
        "days_total": days_total,
        "days_elapsed": days_elapsed,
        "days_left": days_left,
        "can_close": can_close,
        "status": period.status,
    }


def brand_payload(db: Session) -> dict:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return {
            "name": "Tu asesoría", "color_primary": "#6EE7B7",
            "color_secondary": "#8B9DF7", "color_bg": "#0A0A0F",
            "font_family": "Inter", "portal_theme": "dark", "logo_path": None,
        }
    return {
        "name": cfg.name, "color_primary": cfg.color_primary,
        "color_secondary": cfg.color_secondary, "color_bg": cfg.color_bg,
        "font_family": cfg.font_family, "portal_theme": cfg.portal_theme,
        "logo_path": cfg.logo_path,
    }


def _meals_for_today(plan: Plan, client: Client, chosen: dict | None) -> list[dict]:
    """Comidas del día desde el plan. Flexible: 7 opciones/slot. Estricto: plato del día."""
    nutrition = plan.nutrition_json or {}
    meal_defs = nutrition.get("meals", [])  # slots con name/time/target
    bank = nutrition.get("meal_bank") or {}
    mode = client.diet_mode
    chosen = chosen or {}

    slots_out: list[dict] = []
    for mdef in meal_defs:
        slot = mdef["slot"]
        entry = {
            "slot": slot,
            "name": mdef.get("name", f"Comida {slot}"),
            "time": mdef.get("time", ""),
            "target": mdef.get("target", {}),
            "options": [],
            "chosen_key": chosen.get(str(slot)),
        }
        if mode == "flexible_7":
            for s in bank.get("slots", []):
                if s["slot"] == slot:
                    entry["options"] = [
                        {"key": o.get("key"), "title": o["title"], "macros": o["macros"],
                         "prep_minutes": o.get("prep_minutes"), "tags": o.get("tags", [])}
                        for o in s.get("options", [])
                    ]
                    entry["equivalences"] = s.get("equivalences")
        elif mode == "strict":
            # plato del día = el del weekday actual en el menú cerrado
            today_idx = date.today().weekday()
            slug = DAY_SLUGS[today_idx]
            for d in bank.get("days", []):
                if d["day"] == slug:
                    for meal in d["meals"]:
                        if meal["slot"] == slot:
                            dish = meal["dish"]
                            entry["options"] = [{
                                "key": dish.get("key", "A"), "title": dish["title"],
                                "macros": dish["macros"], "prep_minutes": dish.get("prep_minutes"),
                                "tags": dish.get("tags", []),
                            }]
        slots_out.append(entry)
    return slots_out


def _resolve_session(db: Session, sess: dict) -> dict:
    """Convierte una sesión del plan (con exercise_id) en una sesión con nombres
    de ejercicio y vídeo resueltos desde la biblioteca."""
    ex_ids = [e["exercise_id"] for e in sess.get("exercises", [])]
    lib = {
        ex.id: ex
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids)))
    } if ex_ids else {}
    exercises = []
    for e in sess.get("exercises", []):
        ex = lib.get(e["exercise_id"])
        exercises.append({
            "exercise_id": e["exercise_id"],
            "name": ex.canonical_name if ex else f"Ejercicio {e['exercise_id']}",
            "sets": e["sets"], "rep_range": e["rep_range"], "rir": e.get("rir", ""),
            "rest_sec": e.get("rest_sec", 90),
            "start_weight_hint_kg": e.get("start_weight_hint_kg"),
            "technique_cue": e.get("technique_cue"),
            "video_url": ex.video_url if ex and ex.video_url else None,
        })
    return {
        "day": sess.get("day", ""), "name": sess.get("name", ""),
        "warmup": sess.get("warmup"), "exercises": exercises,
        "cooldown": sess.get("cooldown"),
    }


def _session_for_today(db: Session, plan: Plan, today: date) -> dict | None:
    """Sesión de entrenamiento que toca hoy según el día de la semana.

    Mapea el weekday actual al `day` de las sesiones del plan (que vienen como
    "Lunes", "Martes"…). Si hoy no hay sesión, es día de descanso → None.
    """
    training = plan.training_json or {}
    today_label = DAY_LABELS[today.weekday()].lower()
    for sess in training.get("sessions", []):
        if sess.get("day", "").strip().lower() == today_label:
            return _resolve_session(db, sess)
    return None


def build_training_sessions(db: Session, client: Client) -> list[dict]:
    """TODAS las sesiones del plan vigente, con nombres de ejercicio resueltos.

    Para el selector de sesión del portal (el cliente registra la que ha hecho,
    no solo la del día)."""
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)
    if plan is None:
        return []
    training = plan.training_json or {}
    return [_resolve_session(db, s) for s in training.get("sessions", [])]


def build_today_view(db: Session, client: Client, today: date) -> dict:
    period = active_period(db, client.id)
    plan = published_plan_for_period(db, period) if period else latest_published_plan(db, client.id)

    meals: list[dict] = []
    session = None
    already_logged = False

    if plan is not None:
        chosen = None
        if period is not None:
            log = db.scalar(
                select(DailyLog).where(
                    DailyLog.period_id == period.id, DailyLog.log_date == today
                )
            )
            if log is not None:
                already_logged = True
                chosen = log.chosen_options_json
        meals = _meals_for_today(plan, client, chosen)
        session = _session_for_today(db, plan, today)

    return {
        "date": today,
        "day_label": DAY_LABELS[today.weekday()],
        "period": period_info(period, today),
        "meals": meals,
        "session": session,
        "already_logged": already_logged,
    }
