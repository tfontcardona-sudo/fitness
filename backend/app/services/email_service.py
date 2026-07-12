"""Servicio de envío de email (G.5).

- Envía vía SMTP usando smtplib (síncrono; el scheduler corre en su propio
  hilo y los endpoints que envían lo hacen de forma puntual).
- Respeta el toggle GLOBAL (settings.emails_enabled) y POR CLIENTE
  (client.emails_enabled): si cualquiera está desactivado, no envía pero
  registra el intento con status "disabled".
- Toda salida (enviada, fallida o desactivada) deja traza en email_log.
- En desarrollo, docker-compose.dev.yml apunta SMTP a Mailpit, así que los
  emails se ven en http://localhost:8025 sin configurar un SMTP real.

El servicio NO decide CUÁNDO enviar (eso es la máquina de estados / scheduler /
endpoints); solo CÓMO enviar y registrar.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import BrandConfig, Client, EmailLog
from app.services.email_templates import Brand

_log = logging.getLogger("app.email")


def email_config_status() -> dict:
    """Resumen (sin secretos) de la configuración SMTP: qué está puesto y qué
    falta. Sirve para diagnosticar por qué no salen los correos."""
    missing = []
    if not settings.emails_enabled:
        missing.append("EMAILS_ENABLED (debe ser true)")
    if not settings.smtp_host:
        missing.append("SMTP_HOST")
    if not settings.smtp_user:
        missing.append("SMTP_USER")
    if not settings.smtp_pass:
        missing.append("SMTP_PASS (contraseña de aplicación de Gmail)")
    return {
        "emails_enabled": settings.emails_enabled,
        "smtp_host": settings.smtp_host or None,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user or None,
        "smtp_from": settings.smtp_from or None,
        "smtp_pass_set": bool(settings.smtp_pass),
        "ready": not missing,
        "missing": missing,
    }


def brand_from_config(db: Session) -> Brand:
    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return Brand(name="Tu asesoría", color_primary="#6EE7B7", color_bg="#0A0A0F")
    logo_url = None
    if cfg.logo_path:
        logo_url = f"{settings.public_base_url}/storage/{cfg.logo_path}"
    return Brand(
        name=cfg.name,
        color_primary=cfg.color_primary,
        color_bg=cfg.color_bg,
        contact_email=cfg.contact_email or None,
        logo_url=logo_url,
    )


class EmailService:
    """Envío + registro. Inyectable: en tests se sustituye `_transport`."""

    def __init__(self, db: Session):
        self.db = db
        # Último error de envío (tipo + mensaje), para que el caller lo pueda
        # mostrar/devolver sin tener que mirar los logs del contenedor.
        self.last_error: str | None = None

    # -- transporte (sobrescribible en tests) --
    def _transport(self, msg: EmailMessage) -> None:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                self._auth_and_send(s, msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                try:
                    s.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass  # Mailpit y algunos relays no usan TLS
                self._auth_and_send(s, msg)

    def _auth_and_send(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)

    def _log(self, client_id: int | None, kind: str, subject: str, status: str,
             error: str | None = None) -> None:
        self.db.add(EmailLog(
            client_id=client_id, kind=kind, subject=subject, status=status,
            error=(error or None) and error[:500],
        ))

    def send(
        self, *, to: str, subject: str, html: str, kind: str,
        client: Client | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> str:
        """Envía un email y registra el resultado. Devuelve el status final.

        `attachments`: lista de (nombre_fichero, contenido, mime "tipo/subtipo"),
        p. ej. el PDF del plan para los paquetes de entrega por email.

        No hace commit: el caller controla la transacción (así el envío y los
        cambios de estado que lo motivan se confirman juntos o no).
        """
        client_id = client.id if client else None
        self.last_error = None

        # Toggle global o por cliente desactivado → no enviar, pero registrar.
        if not settings.emails_enabled or (client is not None and not client.emails_enabled):
            self._log(client_id, kind, subject, "disabled")
            return "disabled"

        # SMTP sin configurar: fallo claro (no un error de conexión críptico a
        # localhost). El caso típico de "no llegan los correos" es SMTP_PASS vacío.
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_pass:
            self.last_error = (
                "SMTP sin configurar: faltan " +
                ", ".join(email_config_status()["missing"]) +
                ". Rellénalos en el .env del servidor y reinicia."
            )
            _log.warning("Email '%s' no enviado a %s: %s", kind, to, self.last_error)
            self._log(client_id, kind, subject, "failed", self.last_error)
            return "failed"

        msg = EmailMessage()
        msg["From"] = settings.smtp_from or settings.smtp_user or "no-reply@fitness.local"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(
            "Este email requiere un cliente compatible con HTML. "
            "Abre tu portal para ver el contenido."
        )
        msg.add_alternative(html, subtype="html")

        for filename, content, mime in attachments or []:
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                content, maintype=maintype or "application",
                subtype=subtype or "octet-stream", filename=filename,
            )

        try:
            self._transport(msg)
            self._log(client_id, kind, subject, "sent")
            _log.info("Email '%s' enviado a %s", kind, to)
            return "sent"
        except Exception as exc:
            # Causa legible (SMTPAuthenticationError → app password mal; conexión
            # rechazada → host/puerto; etc.). Se registra y se guarda.
            self.last_error = f"{type(exc).__name__}: {exc}"
            _log.warning("Email '%s' NO enviado a %s: %s", kind, to, self.last_error)
            self._log(client_id, kind, subject, "failed", self.last_error)
            return "failed"
