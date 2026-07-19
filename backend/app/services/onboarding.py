"""Email de arranque del cliente: pago del plan + anamnesis (PDF editable).

Compartido por el alta MANUAL (botón "Enviar por email" del coach) y el registro
PERSONAL de la página pública de planes (se envía solo al dejar los datos).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config

TIER_LABEL = {"start": "DQR Start", "full": "DQR Full", "pro": "DQR Pro"}


def send_onboarding_email(db: Session, client: Client) -> str:
    """Envía el mensaje de arranque (pago + anamnesis) y registra el evento.
    Devuelve el status del email (sent | disabled | failed…). NO hace commit."""
    base = settings.public_base_url
    pay_url = f"{base}/api/pay/{client.portal_token}"
    anamnesis_url = f"{base}/anamnesis/{client.portal_token}"
    first = ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]
    label = TIER_LABEL.get(client.package_tier, "tu plan")
    brand = brand_from_config(db)
    subject, html = tpl.onboarding_pay_anamnesis(brand, first, label, pay_url, anamnesis_url)
    status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="onboarding", client=client)
    log_event(db, "client", client.id, "onboarding_sent", {"status": status})
    return status
