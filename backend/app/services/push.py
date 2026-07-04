"""Web Push del portal — recordatorios de seguimiento (spec TRASPASO §8.1).

Flujo completo:
1. El portal registra un service worker y pide permiso de notificaciones.
2. El navegador crea una suscripción (endpoint + claves) que se guarda en
   `push_subscriptions` vía POST /api/p/{token}/push/subscribe.
3. Un job del scheduler (cada 4 h, ver scheduler.py) llama a
   `run_push_reminders`: para cada cliente suscrito calcula qué le FALTA hoy
   (diario / entreno / revisión quincenal) y, si hay pendientes, envía un push
   cifrado con pywebpush firmado con las claves VAPID del .env.
4. El service worker muestra la notificación y pone el número en el badge del
   icono (`navigator.setAppBadge`).

Decisiones:
- El nº de la notificación/badge = nº de cosas pendientes (1–3), como pide la
  spec ("el nº depende de lo que falte").
- Horario activo 08:00–22:00 (hora local settings.tz): el trigger corre cada
  4 h en punto (00/04/08/12/16/20) pero fuera de ese rango no se envía nada —
  nadie quiere un recordatorio de dieta a las 4 de la madrugada. Cambiar
  ACTIVE_FROM/ACTIVE_UNTIL si se quiere otro rango.
- Suscripciones caducadas (el servicio de push responde 404/410) se borran.
- Sin claves VAPID en el .env todo queda desactivado sin romper nada.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, DailyLog, PushSubscription, WorkoutLog
from app.services import portal as portal_svc
from app.services.audit import log_event

logger = logging.getLogger("push")

# Ventana horaria (hora local settings.tz) en la que SÍ se envían recordatorios.
ACTIVE_FROM = 8    # inclusive
ACTIVE_UNTIL = 22  # exclusivo

# TTL del push = 4 h (si el móvil está apagado más tiempo, el siguiente ciclo
# ya traerá el recordatorio actualizado; no tiene sentido acumular antiguos).
PUSH_TTL_SECONDS = 4 * 3600

# Campos del diario que cuentan como "he rellenado algo hoy".
_DIARY_FIELDS = (
    "weight_kg", "sleep_hours", "steps", "satiety_1_10", "water_liters",
    "diet_adherence", "energy_1_5", "mood_1_5", "fatigue_1_5", "free_notes",
)


def push_configured() -> bool:
    return bool(
        settings.push_enabled
        and settings.vapid_public_key
        and settings.vapid_private_key
    )


# ------------------------------------------------------- suscripciones ----

def save_subscription(
    db: Session,
    client: Client,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None = None,
) -> PushSubscription:
    """Upsert por endpoint (el navegador puede re-suscribir el mismo device)."""
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if sub is None:
        sub = PushSubscription(client_id=client.id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.add(sub)
    else:
        sub.client_id = client.id  # por si el dispositivo cambió de token/cliente
        sub.p256dh = p256dh
        sub.auth = auth
    sub.user_agent = (user_agent or "")[:255] or None
    db.flush()  # SessionLocal usa autoflush=False: sin esto, dos llamadas en la
    # misma sesión no se verían y el upsert duplicaría el endpoint
    return sub


def remove_subscription(db: Session, client: Client, endpoint: str) -> bool:
    sub = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.client_id == client.id,
        )
    )
    if sub is None:
        return False
    db.delete(sub)
    db.flush()
    return True


# ---------------------------------------------------------- pendientes ----

def has_session_on(training_json: dict | None, day: date) -> bool:
    """¿El plan tiene sesión de entreno para ese día de la semana? (puro)."""
    if not training_json:
        return False
    label = portal_svc.DAY_LABELS[day.weekday()].lower()
    return any(
        (s.get("day", "").strip().lower() == label)
        for s in training_json.get("sessions", [])
    )


def diary_is_filled(log: DailyLog | None) -> bool:
    """El autosave puede crear la fila vacía: cuenta como rellenado solo si
    algún campo real tiene valor (puro sobre el objeto)."""
    if log is None:
        return False
    return any(getattr(log, f, None) not in (None, "") for f in _DIARY_FIELDS)


def pending_for_client(db: Session, client: Client, today: date) -> dict:
    """Qué le falta hoy al cliente: diario, entreno y/o revisión quincenal.

    Devuelve {"diary": bool, "workout": bool, "quincenal": bool, "count": int}.
    Solo hay pendientes con un período `open`; diario/entreno solo dentro del
    rango de fechas del período; la quincenal cuando `can_close` (día ≥14).
    """
    out = {"diary": False, "workout": False, "quincenal": False, "count": 0}
    period = portal_svc.active_period(db, client.id)
    if period is None or period.status != "open":
        return out

    info = portal_svc.period_info(period, today) or {}
    out["quincenal"] = bool(info.get("can_close"))

    if period.starts_on <= today <= period.ends_on:
        log = db.scalar(
            select(DailyLog).where(
                DailyLog.period_id == period.id, DailyLog.log_date == today
            )
        )
        out["diary"] = not diary_is_filled(log)

        plan = portal_svc.published_plan_for_period(db, period)
        if plan is not None and has_session_on(plan.training_json, today):
            has_sets = False
            if log is not None:
                has_sets = bool(
                    db.scalar(
                        select(WorkoutLog.id)
                        .where(WorkoutLog.daily_log_id == log.id)
                        .limit(1)
                    )
                )
            out["workout"] = not has_sets

    out["count"] = int(out["diary"]) + int(out["workout"]) + int(out["quincenal"])
    return out


def build_reminder_payload(pending: dict, brand_name: str, portal_url: str) -> dict:
    """Payload JSON que consume el service worker (sw.js)."""
    parts: list[str] = []
    if pending.get("workout"):
        parts.append("registrar el entreno de hoy")
    if pending.get("diary"):
        parts.append("el diario de hoy")
    if pending.get("quincenal"):
        parts.append("la revisión quincenal")

    if len(parts) == 1:
        body = f"Te falta {parts[0]}. Un minuto y listo 💪"
    else:
        body = "Te falta: " + ", ".join(parts[:-1]) + " y " + parts[-1] + "."

    return {
        "title": brand_name or "Tu seguimiento",
        "body": body,
        "count": pending.get("count", 0),
        "url": portal_url,
        "tag": "dq-seguimiento",  # misma tag → la nueva sustituye a la anterior
    }


# --------------------------------------------------------------- envío ----

def send_to_client(db: Session, client: Client, payload: dict) -> int:
    """Envía el payload a todos los dispositivos del cliente. Devuelve cuántos
    aceptaron. Borra suscripciones caducadas (404/410)."""
    subs = list(
        db.scalars(select(PushSubscription).where(PushSubscription.client_id == client.id))
    )
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject or "mailto:coach@example.com"},
                ttl=PUSH_TTL_SECONDS,
            )
            sub.last_success_at = datetime.now(timezone.utc)
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                logger.info("suscripción caducada (cliente %s), se borra", client.id)
                db.delete(sub)
            else:
                logger.warning("push fallido (cliente %s, HTTP %s): %s", client.id, status, exc)
        except Exception:  # nunca tumbar el ciclo por un dispositivo raro
            logger.exception("push fallido (cliente %s)", client.id)
    return sent


def _within_active_hours(now_local: datetime) -> bool:
    return ACTIVE_FROM <= now_local.hour < ACTIVE_UNTIL


def run_push_reminders(db: Session, now: datetime | None = None) -> dict:
    """Job de recordatorios (cada 4 h). Idempotente a nivel de ciclo: cada
    ejecución refleja el estado ACTUAL de pendientes; si ya no falta nada, no
    envía. Devuelve un resumen para el log."""
    if not push_configured():
        return {"skipped": "push sin configurar (VAPID_* en .env)"}

    now_local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(settings.tz))
    if not _within_active_hours(now_local):
        return {"skipped": f"fuera de horario activo ({now_local:%H:%M})"}

    today = now_local.date()
    brand = portal_svc.brand_payload(db)
    base = settings.public_base_url.rstrip("/")

    client_ids = db.scalars(select(PushSubscription.client_id).distinct()).all()
    notified = 0
    devices = 0
    for cid in client_ids:
        client = db.get(Client, cid)
        if client is None:
            continue
        pending = pending_for_client(db, client, today)
        if pending["count"] == 0:
            continue
        payload = build_reminder_payload(
            pending, brand.get("name", ""), f"{base}/p/{client.portal_token}"
        )
        ok = send_to_client(db, client, payload)
        if ok:
            notified += 1
            devices += ok
            log_event(db, "client", client.id, "push_reminder_sent",
                      {"pending": pending, "devices": ok})
    db.commit()
    summary = {"clients_notified": notified, "devices": devices,
               "subscribed_clients": len(client_ids)}
    logger.info("recordatorios push: %s", summary)
    return summary
