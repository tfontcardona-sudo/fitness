"""Activación de planes SIN botón "Publicar".

La planificación queda ACTIVA en el momento de generarla o adaptarla (el envío
al cliente va por WhatsApp, no hay paso de publicación): se supersede la
versión anterior del mes, se abre el período de seguimiento si no lo hay, se
fija la etapa del objetivo y se avisa al cliente por email (opcional).
El endpoint POST /plans/{id}/publish sigue existiendo para activar borradores
antiguos (legado), usando esta misma función.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Plan
from app.services.audit import log_event


def activate_plan(db: Session, plan: Plan, *, notify: bool = True) -> None:
    """Deja `plan` como la versión ACTIVA del mes. No hace commit."""
    client = db.get(Client, plan.client_id)

    for older in db.scalars(
        select(Plan).where(
            Plan.client_id == plan.client_id,
            Plan.month_index == plan.month_index,
            Plan.status == "published",
        )
    ):
        if older.id != plan.id:
            older.status = "superseded"

    plan.status = "published"
    plan.published_at = datetime.now(timezone.utc)
    if plan.goal_type is None and client is not None:
        plan.goal_type = client.goal_type
    if client is not None:
        if client.status == "onboarding":
            client.status = "active"
        # Arranque de la etapa del objetivo (alerta de los 45 días)
        if client.goal_started_on is None:
            client.goal_started_on = date.today()

    log_event(db, "plan", plan.id, "plan_published", {"month_index": plan.month_index})

    # Seguimiento AUTÓNOMO: el período de 14 días se abre si no hay ninguno
    from app.services.periods import ensure_open_period

    ensure_open_period(db, plan.client_id)

    if notify and client is not None:
        try:
            from app.config import settings
            from app.services import email_templates as tpl
            from app.services.email_service import EmailService, brand_from_config

            brand = brand_from_config(db)
            portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
            subject, html = tpl.plan_published(
                brand, client.full_name.split()[0], portal_url, plan.month_index > 1
            )
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind="plan_published", client=client)
        except Exception:
            # El email nunca bloquea la activación del plan
            pass
