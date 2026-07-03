"""Registro de auditoría (audit_log) — toda acción relevante deja traza."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    entity: str,
    entity_id: int | None,
    event: str,
    detail: dict | None = None,
) -> None:
    """Añade la entrada al UoW actual; el commit lo hace el caller."""
    db.add(AuditLog(entity=entity, entity_id=entity_id, event=event, detail_json=detail))
