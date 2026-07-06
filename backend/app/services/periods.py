"""Períodos de seguimiento AUTÓNOMOS.

El coach ya no pulsa "Iniciar seguimiento": el ciclo de 14 días se abre y se
renueva solo. `ensure_open_period` es idempotente y se invoca desde:
- la publicación de un plan (original o adaptado),
- el estado del portal del cliente (si entra y no hay período abierto),
- la pestaña Seguimiento del coach,
- el mantenimiento diario del scheduler (red de seguridad).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Period, Plan
from app.services.audit import log_event

PERIOD_DAYS = 14


def ensure_open_period(db: Session, client_id: int, *, commit: bool = False) -> Period | None:
    """Abre el siguiente período si el cliente tiene plan publicado y ningún
    período abierto. Devuelve el período creado, o None si no tocaba."""
    client = db.get(Client, client_id)
    if client is None or client.status in ("onboarding", "inactive"):
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
    if last is not None and last.status == "open":
        return None

    today = date.today()
    period = Period(
        client_id=client_id, plan_id=plan.id,
        period_index=(last.period_index + 1) if last else 1,
        starts_on=today, ends_on=today + timedelta(days=PERIOD_DAYS - 1),
        status="open",
    )
    db.add(period)
    db.flush()
    log_event(db, "period", period.id, "period_opened",
              {"index": period.period_index, "auto": True})
    if commit:
        db.commit()
    return period
