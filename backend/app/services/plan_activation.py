"""Activación de planes SIN botón "Publicar".

La planificación queda ACTIVA en el momento de generarla, adaptarla o editarla
(el envío al cliente va por WhatsApp, no hay paso de publicación): se supersede
cualquier plan publicado anterior, se abre el período de seguimiento si no lo
hay, se fija la etapa del objetivo y se avisa al cliente por email (opcional).
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
    """Deja `plan` como el ÚNICO plan activo del cliente. No hace commit.

    Supersede CUALQUIER otro plan publicado — también los de meses anteriores:
    si no, al cambiar de objetivo y generar el mes siguiente con el período aún
    abierto, el portal y el PDF del cliente seguirían sirviendo el plan viejo
    anclado a ese período hasta el siguiente feedback."""
    client = db.get(Client, plan.client_id)

    same_month_replaced = False
    for older in db.scalars(
        select(Plan).where(
            Plan.client_id == plan.client_id,
            Plan.status == "published",
        )
    ):
        if older.id != plan.id:
            older.status = "superseded"
            if older.month_index == plan.month_index:
                same_month_replaced = True

    plan.status = "published"
    plan.published_at = datetime.now(timezone.utc)
    if plan.goal_type is None and client is not None:
        plan.goal_type = client.goal_type
    if client is not None:
        if client.status == "onboarding":
            client.status = "active"
        # Arranque de la etapa del objetivo (alerta de los 45 días). Fecha local.
        if client.goal_started_on is None:
            from app.services.portal import today_local
            client.goal_started_on = today_local()

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
            first = client.full_name.split()[0]
            if same_month_replaced:
                # ADAPTACIÓN/actualización del mes en curso: email de "plan
                # actualizado", no otro "¡Bienvenido!" ni "nuevo mes".
                resumen = ("Hemos ajustado tu dieta y entrenamiento a tu última "
                           "revisión. Todo está ya aplicado en tu portal y en tu PDF.")
                subject, html = tpl.plan_republished(brand, first, portal_url, resumen)
                kind = "plan_republished"
            else:
                subject, html = tpl.plan_published(
                    brand, first, portal_url, plan.month_index > 1
                )
                kind = "plan_published"
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind=kind, client=client)
        except Exception:
            # El email nunca bloquea la activación del plan
            pass
