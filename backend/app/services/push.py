"""Web Push del portal — recordatorios de seguimiento (spec TRASPASO §8.1).

Flujo completo:
1. El portal registra un service worker y pide permiso de notificaciones.
2. El navegador crea una suscripción (endpoint + claves) que se guarda en
   `push_subscriptions` vía POST /api/p/{token}/push/subscribe.
3. Un job del scheduler (cada 3 h, ver scheduler.py) llama a
   `run_push_reminders`: para cada cliente suscrito calcula qué le FALTA hoy
   (diario / entreno / revisión quincenal) y, si hay pendientes, envía un push
   cifrado con pywebpush firmado con las claves VAPID del .env.
4. El service worker muestra la notificación y pone el número en el badge del
   icono (`navigator.setAppBadge`).

Decisiones:
- El nº de la notificación/badge = nº de cosas pendientes (1–3), como pide la
  spec ("el nº depende de lo que falte").
- Horario activo 08:00–22:00 (hora local settings.tz): el trigger corre cada
  3 h en punto (00/03/06/09/12/15/18/21) pero fuera de ese rango no se envía
  nada — nadie quiere un recordatorio de dieta de madrugada. Cambiar
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

# TTL del push = 3 h (si el móvil está apagado más tiempo, el siguiente ciclo
# ya traerá el recordatorio actualizado; no tiene sentido acumular antiguos).
PUSH_TTL_SECONDS = 3 * 3600

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
    elif sub.is_coach:
        # Dispositivo del COACH (endpoint único por navegador): que abra el
        # portal de un cliente para previsualizarlo NO lo convierte en el
        # dispositivo de ese cliente ni le quita el resumen — solo claves.
        sub.p256dh = p256dh
        sub.auth = auth
    else:
        sub.client_id = client.id  # por si el dispositivo cambió de token/cliente
        sub.p256dh = p256dh
        sub.auth = auth
    sub.user_agent = (user_agent or "")[:255] or None
    db.flush()  # SessionLocal usa autoflush=False: sin esto, dos llamadas en la
    # misma sesión no se verían y el upsert duplicaría el endpoint
    return sub


def save_coach_subscription(db: Session, endpoint: str, p256dh: str, auth: str,
                            user_agent: str | None = None) -> PushSubscription:
    """Dispositivo del COACH (web del coach): recibe el resumen de alertas."""
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if sub is None:
        sub = PushSubscription(client_id=None, is_coach=True, endpoint=endpoint,
                               p256dh=p256dh, auth=auth)
        db.add(sub)
    else:
        sub.client_id = None
        sub.is_coach = True
        sub.p256dh = p256dh
        sub.auth = auth
    sub.user_agent = (user_agent or "")[:255] or None
    db.flush()
    return sub


def remove_coach_subscription(db: Session, endpoint: str) -> bool:
    sub = db.scalar(select(PushSubscription).where(
        PushSubscription.endpoint == endpoint, PushSubscription.is_coach.is_(True)))
    if sub is None:
        return False
    db.delete(sub)
    return True


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


# -------------------------------------------------- push "plan publicado" ----

def build_plan_published_payload(brand_name: str, portal_url: str, *, republished: bool) -> dict:
    """Payload de la notificación al cliente cuando su plan queda publicado."""
    body = (
        "Tu planificación se ha actualizado tras tu revisión. Ábrela en tu portal."
        if republished
        else "Tu planificación ya está lista. Ábrela en tu portal para empezar."
    )
    return {
        "title": brand_name or "Tu planificación",
        "body": body,
        "count": 1,
        "url": portal_url,
        "tag": "dq-plan",  # tag propia: no pisa la de los recordatorios
    }


def notify_plan_published(db: Session, client: Client, *, republished: bool = False) -> int:
    """Avisa al cliente (push) de que su plan está publicado. No hace commit.
    Silencioso si el push no está configurado o el cliente no tiene dispositivos."""
    if not push_configured():
        return 0
    brand = portal_svc.brand_payload(db)
    base = settings.public_base_url.rstrip("/")
    payload = build_plan_published_payload(
        brand.get("name", ""), f"{base}/p/{client.portal_token}", republished=republished
    )
    return send_to_client(db, client, payload)


def notify_video_call_scheduled(db: Session, client: Client, when_label: str,
                                meet_url: str) -> int:
    """Avisa al cliente (push) de que su videollamada quedó agendada. No commit.
    Abre el enlace de Meet al tocar la notificación. Silencioso sin push/devices."""
    if not push_configured():
        return 0
    brand = portal_svc.brand_payload(db)
    payload = {
        "title": brand.get("name", "Tu asesoría"),
        "body": f"Videollamada de revisión agendada: {when_label}. ¡Te espero!",
        "count": 1,
        "url": meet_url,
        "tag": "dq-videollamada",
    }
    return send_to_client(db, client, payload)


# --------------------------------------------------------------- envío ----

def _send_to_subs(db: Session, subs: list[PushSubscription], payload: dict, who: str) -> int:
    """Envía el payload a una lista de dispositivos. Devuelve cuántos aceptaron.
    Borra suscripciones caducadas (404/410)."""
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
                logger.info("suscripción caducada (%s), se borra", who)
                db.delete(sub)
            else:
                logger.warning("push fallido (%s, HTTP %s): %s", who, status, exc)
        except Exception:  # nunca tumbar el ciclo por un dispositivo raro
            logger.exception("push fallido (%s)", who)
    return sent


def send_to_client(db: Session, client: Client, payload: dict) -> int:
    """Envía el payload a todos los dispositivos del cliente."""
    subs = list(
        db.scalars(select(PushSubscription).where(PushSubscription.client_id == client.id))
    )
    return _send_to_subs(db, subs, payload, f"cliente {client.id}")


def send_to_coach(db: Session, payload: dict) -> int:
    """Envía el payload a todos los dispositivos del COACH."""
    subs = list(
        db.scalars(select(PushSubscription).where(PushSubscription.is_coach.is_(True)))
    )
    return _send_to_subs(db, subs, payload, "coach")


def _within_active_hours(now_local: datetime) -> bool:
    return ACTIVE_FROM <= now_local.hour < ACTIVE_UNTIL


def run_push_reminders(db: Session, now: datetime | None = None) -> dict:
    """Job de recordatorios (cada 3 h). Idempotente a nivel de ciclo: cada
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

    client_ids = db.scalars(
        select(PushSubscription.client_id)
        .where(PushSubscription.client_id.is_not(None)).distinct()
    ).all()
    notified = 0
    devices = 0
    for cid in client_ids:
        client = db.get(Client, cid)
        # A un cliente INACTIVO no se le recuerda nada (su período abierto
        # residual mantendría "te falta la revisión" para siempre).
        if client is None or client.status == "inactive":
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

    # Recordatorio de VIDEOLLAMADA (Pro): si la tiene reservada para MAÑANA,
    # UN aviso al día. Se evalúa en TODAS las franjas (si el coach apunta la
    # fecha por la tarde, el aviso sale igualmente esa tarde); el duplicado se
    # evita con el registro de auditoría: ya avisado para esa fecha → no repite.
    from datetime import timedelta

    from app.models import AuditLog, VideoCall

    calls = db.scalars(select(VideoCall).where(
        VideoCall.status == "scheduled",
        VideoCall.scheduled_for == today + timedelta(days=1),
    )).all()
    for vc in calls:
        client = db.get(Client, vc.client_id)
        if client is None or client.status == "inactive":
            continue
        already = db.scalar(
            select(AuditLog.id).where(
                AuditLog.entity == "client",
                AuditLog.entity_id == client.id,
                AuditLog.event == "push_videocall_reminder",
                AuditLog.detail_json["date"].astext == vc.scheduled_for.isoformat(),
            ).limit(1)
        )
        if already:
            continue
        # Con hora concreta (agendado por Google Meet) el aviso la incluye y
        # enlaza directo a Meet; si no, al portal.
        hora = ""
        if vc.scheduled_at is not None:
            hora = " a las " + vc.scheduled_at.astimezone(ZoneInfo(settings.tz)).strftime("%H:%M")
        payload = {
            "title": brand.get("name", "Tu asesoría"),
            "body": f"Recordatorio: mañana{hora} tienes la videollamada con tu coach. ¡Te espero!",
            "count": 1,
            "url": vc.meet_url or f"{base}/p/{client.portal_token}",
            "tag": "dq-videollamada",
        }
        ok = send_to_client(db, client, payload)
        if ok:
            log_event(db, "client", client.id, "push_videocall_reminder",
                      {"date": vc.scheduled_for.isoformat(), "devices": ok})

    db.commit()
    summary = {"clients_notified": notified, "devices": devices,
               "subscribed_clients": len(client_ids)}
    logger.info("recordatorios push: %s", summary)
    return summary


def run_coach_digest(db: Session, now: datetime | None = None) -> dict:
    """Resumen push al MÓVIL DEL COACH (cada 3 h, 08–22): cuántos pendientes
    hay y los primeros, derivados del centro de alertas — siempre al día de
    sus clientes sin tener la web abierta."""
    if not push_configured():
        return {"skipped": "push sin configurar"}
    now_local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(settings.tz))
    if not _within_active_hours(now_local):
        return {"skipped": f"fuera de horario activo ({now_local:%H:%M})"}
    has_coach = db.scalar(select(PushSubscription.id).where(
        PushSubscription.is_coach.is_(True)).limit(1))
    if not has_coach:
        return {"skipped": "el coach no tiene dispositivos suscritos"}

    from app.routers.alerts import client_alerts

    alerts: list[dict] = []
    for client in db.scalars(select(Client).where(Client.status != "inactive")):
        try:
            alerts.extend(client_alerts(db, client, now_local.date()))
        except Exception:  # un cliente con datos raros no tumba el resumen entero
            logger.exception("alertas ilegibles del cliente %s en el digest", client.id)
    if not alerts:
        return {"alerts": 0, "devices": 0}

    # Las de severidad alta primero; 3 líneas máximo en el cuerpo. El nombre
    # puede venir vacío (dato legado): nunca reventar el resumen por eso.
    alerts.sort(key=lambda a: 0 if a.get("severity") == "alta" else 1)
    lines = [
        f"· {(a.get('client_name') or '').split()[0] if (a.get('client_name') or '').split() else 'Cliente'}: {a['action']}"
        for a in alerts[:3]
    ]
    if len(alerts) > 3:
        lines.append(f"…y {len(alerts) - 3} más")
    payload = {
        "title": f"{len(alerts)} pendiente{'s' if len(alerts) != 1 else ''} de tus clientes",
        "body": "\n".join(lines),
        "count": len(alerts),
        "url": f"{settings.public_base_url.rstrip('/')}/",
        "tag": "dq-coach",  # misma tag → el resumen nuevo sustituye al anterior
    }
    devices = send_to_coach(db, payload)
    db.commit()
    summary = {"alerts": len(alerts), "devices": devices}
    logger.info("resumen push del coach: %s", summary)
    return summary
