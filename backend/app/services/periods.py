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

PERIOD_DAYS = 14


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
        starts_on=today, ends_on=today + timedelta(days=PERIOD_DAYS - 1),
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
