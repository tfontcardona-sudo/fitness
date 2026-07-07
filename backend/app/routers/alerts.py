"""Centro de ALERTAS del coach — preventivo e inteligente.

Cada alerta se CALCULA del estado real del cliente (nada que marcar como
leído): en cuanto el coach hace la acción que pide, la alerta desaparece sola.
Cubre el ciclo completo de la asesoría para que sea imposible dejar pasos sin
atender:

  onboarding  → crear/publicar la planificación
  revisión    → generar el feedback → enviarlo por WhatsApp
  adaptación  → adaptar el plan a la última revisión → publicar el borrador
  seguimiento → cliente sin registros varios días
  objetivo    → 45 días en la misma etapa: valorar cambio (posponible)
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client, DailyLog, FeedbackDoc, Period, Plan

router = APIRouter(prefix="/api", tags=["alerts"], dependencies=[Depends(get_current_user)])

GOAL_REVIEW_DAYS = 45
NO_LOGS_DAYS = 4

_GOAL_LABEL = {
    "fat_loss": "pérdida de grasa", "muscle_gain": "ganancia muscular",
    "recomp": "recomposición", "maintenance": "mantenimiento",
    "injury_recovery": "recuperación de lesión",
}


def _alert(client: Client, kind: str, severity: str, message: str, tab: str,
           action: str) -> dict:
    return {
        "client_id": client.id, "client_name": client.full_name,
        "kind": kind, "severity": severity, "message": message,
        "tab": tab, "action": action,
    }


def client_alerts(db: Session, client: Client, today: date | None = None) -> list[dict]:
    """Alertas de UN cliente (reutilizado por el listado y el backtest)."""
    today = today or date.today()
    out: list[dict] = []
    if client.status == "inactive":
        return out

    plans = list(db.scalars(
        select(Plan).where(Plan.client_id == client.id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ))
    published = next((p for p in plans if p.status == "published"), None)
    latest = plans[0] if plans else None
    last_period = db.scalar(
        select(Period).where(Period.client_id == client.id)
        .order_by(Period.period_index.desc()).limit(1)
    )

    # --- Arranque: sin planificación aún -----------------------------------
    if published is None:
        if latest is not None:  # borrador ANTIGUO sin activar (legado)
            out.append(_alert(client, "publish_plan", "alta",
                              f"Borrador v{latest.version} sin activar: revísalo y actívalo.",
                              "planificacion", "Activar planificación"))
        else:
            out.append(_alert(client, "create_plan", "media",
                              "Sin planificación: completa la anamnesis y genera el plan.",
                              "anamnesis", "Crear planificación"))
        return out  # sin plan publicado, el resto del ciclo no aplica

    # --- Revisión quincenal recibida sin feedback ---------------------------
    if last_period is not None and last_period.status == "closed":
        out.append(_alert(client, "generate_feedback", "alta",
                          f"Revisión #{last_period.period_index} recibida: revisa los datos y genera el feedback.",
                          "seguimiento", "Generar feedback"))

    # --- Feedback generado pero sin enviar ----------------------------------
    if last_period is not None and last_period.status == "analyzed":
        fb = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == last_period.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
        if fb is not None and fb.sent_at is None:
            out.append(_alert(client, "send_feedback", "alta",
                              f"Feedback de la revisión #{last_period.period_index} sin enviar al cliente.",
                              "feedback", "Enviar por WhatsApp"))

        # --- Plan sin adaptar a la última revisión --------------------------
        def _adapted_idx(p: Plan | None) -> int | None:
            if p is None:
                return None
            return ((p.nutrition_json or {}).get("applied_adjustments") or {}).get("period_index")

        if _adapted_idx(latest) != last_period.period_index:
            out.append(_alert(client, "adapt_plan", "alta",
                              f"Planificación sin adaptar a la revisión #{last_period.period_index}.",
                              "planificacion", "Adaptar planificación"))
        elif latest is not None and latest.status == "draft":
            out.append(_alert(client, "publish_plan", "alta",
                              f"Borrador adaptado a la revisión #{last_period.period_index} sin activar.",
                              "planificacion", "Activar planificación"))
    elif latest is not None and latest.status == "draft":
        # Borrador antiguo suelto (legado): los planes nuevos se activan solos
        out.append(_alert(client, "publish_plan", "media",
                          f"Borrador v{latest.version} sin activar.",
                          "planificacion", "Activar planificación"))

    # --- Cliente sin registros varios días (período abierto) ----------------
    if last_period is not None and last_period.status == "open":
        last_log = db.scalar(
            select(func.max(DailyLog.log_date)).where(DailyLog.period_id == last_period.id)
        )
        since = last_log or (last_period.starts_on - date.resolution)
        gap = (today - since).days
        days_in = (today - last_period.starts_on).days
        if gap >= NO_LOGS_DAYS and days_in >= NO_LOGS_DAYS:
            out.append(_alert(client, "no_logs", "media",
                              f"Sin registros del cliente desde hace {gap} días.",
                              "seguimiento", "Ver seguimiento"))

    # --- 45 días en la misma etapa de objetivo ------------------------------
    if client.goal_started_on is not None:
        days_goal = (today - client.goal_started_on).days
        snoozed = (client.goal_review_snoozed_on is not None
                   and (today - client.goal_review_snoozed_on).days < GOAL_REVIEW_DAYS)
        if days_goal >= GOAL_REVIEW_DAYS and not snoozed:
            goal = _GOAL_LABEL.get(client.goal_type or "", client.goal_type or "—")
            out.append(_alert(client, "goal_review", "media",
                              f"Lleva {days_goal} días con el objetivo de {goal}: valora si toca cambiarlo.",
                              "planificacion", "Valorar objetivo"))

    return out


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)) -> dict:
    """Todas las alertas pendientes, más graves primero."""
    clients = db.scalars(select(Client).order_by(Client.full_name)).all()
    alerts: list[dict] = []
    for c in clients:
        alerts.extend(client_alerts(db, c))
    alerts.sort(key=lambda a: (0 if a["severity"] == "alta" else 1, a["client_name"]))
    return {"alerts": alerts, "count": len(alerts),
            "high": sum(1 for a in alerts if a["severity"] == "alta")}
