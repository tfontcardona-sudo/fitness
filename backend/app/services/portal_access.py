"""Acceso del cliente al portal: genera credenciales y las envía por email.

El cliente entra al portal con su email (usuario) y una contraseña que se le
envía por correo la primera vez que el coach registra su anamnesis (y que el
coach puede reenviar/regenerar cuando quiera). El enlace por token sigue
funcionando en paralelo (retrocompatibilidad).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client
from app.security import hash_password
from app.services import email_templates as tpl
from app.services.email_service import EmailService, brand_from_config
from app.services.audit import log_event

# Alfabeto sin caracteres ambiguos (nada de l, I, 1, O, 0) para que la clave del
# email se lea y se teclee sin confusión.
_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def generate_portal_password(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def send_portal_access(db: Session, client: Client) -> dict:
    """Genera una contraseña nueva para el cliente, la guarda (hash) y le envía
    por email su acceso (usuario = email + contraseña + enlace de login).

    Siempre genera una contraseña nueva cuando se llama (primera vez o reenvío):
    así hay texto plano que enviar y el reenvío invalida la clave anterior. NO
    hace commit: lo controla el caller (el envío y el hash se guardan juntos).

    Devuelve {"status": sent|disabled|failed, "password": str|None}.
    """
    if not client.email:
        return {"status": "no_email", "password": None}

    password = generate_portal_password()
    client.portal_password_hash = hash_password(password)

    brand = brand_from_config(db)
    login_url = f"{settings.public_base_url}/portal"
    first = (client.full_name or client.email).split()[0]
    subject, html = tpl.portal_access(brand, first, login_url, client.email, password)
    status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="portal_access", client=client,
    )

    # Solo se sella como "enviado" si el email SALIÓ de verdad. Si estaba
    # desactivado o falló, se deja sin sellar para que el auto-envío reintente en
    # la siguiente subida de anamnesis (y el coach pueda reenviarlo a mano).
    if status == "sent":
        client.portal_access_sent_at = datetime.now(timezone.utc)
    log_event(db, "client", client.id, "portal_access_sent", {"status": status})
    # La contraseña en claro solo se devuelve para que el coach pueda verla en la
    # respuesta si el email está desactivado; nunca se persiste ni se loguea.
    return {"status": status, "password": password}
