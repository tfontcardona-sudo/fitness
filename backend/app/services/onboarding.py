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

# El nombre del plan sale de la marca DEL CLIENTE (el mensaje es suyo).
from app.services import packages as _pkgs
from app.services.branding import marca_de_cliente


def send_onboarding_email(db: Session, client: Client) -> str:
    """Envía el mensaje de arranque (pago + anamnesis) y registra el evento.
    Devuelve el status del email (sent | disabled | failed…). NO hace commit."""
    base = settings.public_base_url
    pay_url = f"{base}/api/pay/{client.portal_token}"
    anamnesis_url = f"{base}/anamnesis/{client.portal_token}"
    first = ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]
    label = _pkgs.label(client.package_tier, marca_de_cliente(client))
    brand = brand_from_config(db)
    # Quien YA ha pagado (checkout de Stripe) no puede recibir un correo cuyo
    # paso 1 sea "realiza el pago": genera desconfianza justo tras cobrar
    # (auditoría). Se le manda el mismo mensaje SIN el bloque de pago.
    subject, html = tpl.onboarding_pay_anamnesis(
        brand, first, label, pay_url, anamnesis_url,
        include_pay=client.payment_status != "paid")
    status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="onboarding", client=client)
    log_event(db, "client", client.id, "onboarding_sent", {"status": status})
    return status
