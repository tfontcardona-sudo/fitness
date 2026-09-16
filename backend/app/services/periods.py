"""Períodos de seguimiento AUTÓNOMOS.

El coach ya no pulsa "Iniciar seguimiento": el ciclo de 14 días se abre y se
renueva solo. `ensure_open_period` es idempotente y se invoca desde:
- la publicación de un plan (original o adaptado),
- el estado del portal del cliente (si entra y no hay período abierto),
- la pestaña Seguimiento del coach,
- el mantenimiento diario del scheduler (red de seguridad).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Client, Period, Plan
from app.services.audit import log_event

# La revisión dura DOS SEMANAS por defecto: es el ritmo con el que se pensó
# todo el ciclo (recordatorios, motor quincenal, documentos). Desde la ronda
# del ciclo variable el coach puede ponerle otra a un cliente concreto
# (`clients.review_days`), porque un principiante que necesita más margen y un
# avanzado en una fase de fuerza no se revisan al mismo ritmo.
PERIOD_DAYS = 14
MIN_REVIEW_DAYS = 7
MAX_REVIEW_DAYS = 31


def review_days(client: Client | None) -> int:
    """Cuántos días dura una revisión de ESTE cliente. Sin dato, la quincena.

    Una sola puerta: lo consultan la apertura del período, los recordatorios,
    el portal y el documento. Con dos reglas distintas, el portal le diría al
    cliente una fecha y el recordatorio le llegaría otro día."""
    crudo = getattr(client, "review_days", None)
    try:
        n = int(crudo)
    except (TypeError, ValueError):
        return PERIOD_DAYS
    return max(MIN_REVIEW_DAYS, min(MAX_REVIEW_DAYS, n))


def ensure_open_period(db: Session, client_id: int, *, commit: bool = False) -> Period | None:
    """Abre el siguiente período si el cliente tiene plan publicado y ningún
    período abierto. Devuelve el período creado, o None si no tocaba."""
    # La sesión va con autoflush=False: si el caller acaba de publicar un plan
    # en esta misma transacción, hay que volcarlo antes de consultar (si no,
    # el SELECT no ve el plan publicado y el período no se abriría hasta el
    # día siguiente por el job nocturno).
    db.flush()
    client = db.get(Client, client_id)
    if client is None or client.status in ("onboarding", "inactive"):
        return None
    # Con la revisión entregada y el feedback PENDIENTE no arranca ciclo nuevo:
    # el siguiente período empieza cuando el coach responde (feedback enviado).
    if client.status == "review_pending":
        return None

    plan = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1)
    )
    if plan is None:
        return None

    last = db.scalar(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    # "open" → ya hay ciclo en marcha. "closed" → el cliente entregó la revisión
    # y el coach aún no ha generado el feedback: tampoco toca abrir el siguiente
    # (se abriría con fecha del día del cierre y quemaría días de ciclo en vano).
    if last is not None and last.status in ("open", "closed"):
        return None

    # Fecha de NEGOCIO (Europe/Madrid), no UTC: cerca de medianoche evita abrir
    # el período con "ayer" y quemar un día del ciclo.
    from app.services.portal import today_local
    today = today_local()
    period = Period(
        client_id=client_id, plan_id=plan.id,
        period_index=(last.period_index + 1) if last else 1,
        starts_on=today, ends_on=today + timedelta(days=review_days(client) - 1),
        status="open",
    )
    # Índice único parcial (un solo período abierto por cliente): si dos
    # peticiones concurrentes intentan abrirlo a la vez, una gana y la otra
    # reutiliza el que ya existe (savepoint → no deshace el trabajo del caller).
    try:
        with db.begin_nested():
            db.add(period)
            db.flush()
    except IntegrityError:
        return db.scalar(
            select(Period).where(Period.client_id == client_id, Period.status == "open")
            .order_by(Period.period_index.desc()).limit(1)
        )
    log_event(db, "period", period.id, "period_opened",
              {"index": period.period_index, "auto": True})
    if commit:
        db.commit()
    return period


def current_month_index(db: Session, client_id: int) -> int:
    """MES de asesoría en curso (1, 2, 3…): dos revisiones quincenales = un mes.

    El mes se quedaba clavado en 1 para siempre —el frontend reenviaba el del
    plan anterior—, así que un cliente de medio año seguía recibiendo un PDF
    que decía "Mes 1 de asesoría" (auditoría de calidad). Se deriva del ciclo
    real: revisiones ya analizadas // 2 + 1.
    """
    from sqlalchemy import func

    analyzed = db.scalar(
        select(func.count()).select_from(Period)
        .where(Period.client_id == client_id, Period.status == "analyzed")
    ) or 0
    # Cuántas revisiones caben en un mes depende de lo que DURE la revisión de
    # este cliente: con la quincena de siempre son dos (el "//2" histórico),
    # con revisiones mensuales es una y con semanales, cuatro. Clavarlo en dos
    # le decía "Mes 1" durante dos meses a quien se revisa cada semana.
    por_mes = max(1, round(30 / review_days(db.get(Client, client_id))))
    return 1 + int(analyzed) // por_mes


def reference_weight_kg(db: Session, client: Client) -> float | None:
    """UNA SOLA VERDAD del peso de referencia (auditoría de ediciones): antes el
    editor usaba cierre>inicio, el PATCH current>inicio y la generación
    log>cierre>current>inicio — tres respuestas distintas para la misma
    pregunta. Prioridad: último registro del portal > cierre quincenal >
    current_weight_kg (anamnesis) > start_weight_kg."""
    from app.models import DailyLog

    latest_log_w = db.scalar(
        select(DailyLog.weight_kg)
        .join(Period, DailyLog.period_id == Period.id)
        .where(Period.client_id == client.id, DailyLog.weight_kg.is_not(None))
        .order_by(DailyLog.log_date.desc()).limit(1)
    )
    latest_close_w = db.scalar(
        select(Period.closing_weight_kg)
        .where(Period.client_id == client.id, Period.closing_weight_kg.is_not(None))
        .order_by(Period.period_index.desc()).limit(1)
    )
    return latest_log_w or latest_close_w or client.current_weight_kg or client.start_weight_kg
