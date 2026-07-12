"""Diagnóstico y prueba del envío de email (SMTP).

Herramientas para el coach: ver si el SMTP está bien configurado, mandar un
correo de prueba y consultar los últimos intentos con su causa de fallo. Así,
si "no llega el correo", se ve exactamente por qué (SMTP_PASS vacío, contraseña
de aplicación rechazada, conexión, etc.).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import EmailLog
from app.services import email_templates as tpl
from app.services.email_service import (
    EmailService,
    brand_from_config,
    email_config_status,
)

router = APIRouter(prefix="/api/email", tags=["email"], dependencies=[Depends(get_current_user)])


def _recent_log(db: Session, limit: int = 10) -> list[dict]:
    rows = db.scalars(select(EmailLog).order_by(EmailLog.id.desc()).limit(limit)).all()
    return [{
        "kind": r.kind, "subject": r.subject, "status": r.status,
        "error": r.error, "sent_at": r.sent_at.isoformat() if r.sent_at else None,
    } for r in rows]


@router.get("/status")
def email_status(db: Session = Depends(get_db)) -> dict:
    """Estado de la configuración SMTP + últimos intentos de envío."""
    return {"config": email_config_status(), "recent": _recent_log(db)}


class EmailTestIn(BaseModel):
    to: str


@router.post("/test")
def email_test(body: EmailTestIn, db: Session = Depends(get_db)) -> dict:
    """Envía un correo de prueba a `to` y devuelve el resultado real (con la causa
    si falla). Úsalo tras rellenar el SMTP para confirmar que entrega."""
    brand = brand_from_config(db)
    subject, html = tpl.test_email(brand)
    svc = EmailService(db)
    status = svc.send(to=body.to, subject=subject, html=html, kind="test")
    db.commit()
    return {"status": status, "error": svc.last_error, "config": email_config_status()}
