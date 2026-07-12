"""Jobs del scheduler (G.1/G.2/G.5) — la capa con efectos.

`run_daily_maintenance(db, today)` es el job diario idempotente:
- Para cada cliente con período activo, calcula los hechos desde la DB.
- Llama a la máquina de estados (función pura) para decidir transiciones.
- Persiste cambios de estado, registra en audit_log y dispara los emails que
  correspondan (recordatorio al cliente, alerta at_risk al coach).

Idempotencia: un email de un `kind` concreto no se reenvía si ya se registró
para ese cliente hoy (se consulta email_log por kind + fecha). Así, ejecutar el
job dos veces el mismo día no duplica nada.

Se ejecuta vía APScheduler (scheduler.py) una vez al día, y también puede
invocarse manualmente para pruebas o backfill.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, DailyLog, EmailLog, Period
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config
from app.services.state_machine import (
    ClientFacts,
    can_transition,
    evaluate_transition,
)


def _first_name(client: Client) -> str:
    """Primer nombre para el saludo, robusto ante nombre en blanco: sin esto un
    `full_name` vacío/espacios reventaba el job diario con IndexError y abortaba
    TODAS las transiciones y recordatorios de esa ejecución."""
    parts = (client.full_name or "").split()
    return parts[0] if parts else (client.email or "").split("@")[0] or "hola"


def _already_sent_today(db: Session, client_id: int, kind: str, today: date) -> bool:
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    n = db.scalar(
        select(func.count())
        .select_from(EmailLog)
        .where(
            EmailLog.client_id == client_id,
            EmailLog.kind == kind,
            EmailLog.sent_at >= start,
        )
    )
    return bool(n)


def _active_period(db: Session, client_id: int) -> Period | None:
    """Período más reciente del cliente que no esté analizado."""
    return db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status != "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )


def _facts_for(db: Session, client: Client) -> ClientFacts:
    period = _active_period(db, client.id)
    if period is None:
        return ClientFacts(status=client.status)

    days_logged = db.scalar(
        select(func.count())
        .select_from(DailyLog)
        .where(DailyLog.period_id == period.id)
    ) or 0

    last_log_date = db.scalar(
        select(func.max(DailyLog.log_date)).where(DailyLog.period_id == period.id)
    )
    last_activity = last_log_date or period.starts_on

    return ClientFacts(
        status=client.status,
        has_active_period=True,
        period_start=period.starts_on,
        period_end=period.ends_on,
        period_closed=period.status in ("closed", "analyzed"),
        days_logged_in_period=int(days_logged),
        last_activity_date=last_activity,
    )


def run_daily_maintenance(db: Session, today: date | None = None) -> dict:
    """Job diario. Devuelve un resumen de lo actuado (útil para logs/tests)."""
    today = today or date.today()
    summary = {"evaluated": 0, "transitions": 0, "reminders": 0, "at_risk_alerts": 0,
               "periods_opened": 0}

    clients = db.scalars(
        select(Client).where(Client.status.notin_(["inactive"]))
    ).all()
    if not clients:
        return summary

    # Seguimiento autónomo (red de seguridad diaria): reabrir el ciclo de 14
    # días a quien tenga plan publicado y ningún período abierto.
    from app.services.periods import ensure_open_period

    for c in clients:
        if ensure_open_period(db, c.id) is not None:
            summary["periods_opened"] += 1

    emailer = EmailService(db)
    brand = brand_from_config(db)
    base = settings.public_base_url

    for client in clients:
        summary["evaluated"] += 1
        facts = _facts_for(db, client)
        decision = evaluate_transition(facts, today)

        # 1) Recordatorio día 12 (no cambia estado)
        if decision.send_reminder and not _already_sent_today(db, client.id, "reminder_no_logs", today):
            period = _active_period(db, client.id)
            days_left = max(0, (period.ends_on - today).days) if period else 0
            subject, html = tpl.reminder_no_logs(
                brand, _first_name(client),
                f"{base}/p/{client.portal_token}", days_left,
                has_training=getattr(client, "package_tier", None) != "start",
            )
            emailer.send(to=client.email, subject=subject, html=html,
                         kind="reminder_no_logs", client=client)
            summary["reminders"] += 1

        # 1b) Día 14+: recordatorio de CERRAR la revisión quincenal (uno al
        # día mientras el período siga abierto y vencido).
        closing_period = _active_period(db, client.id)
        if (closing_period is not None and closing_period.status == "open"
                and today >= closing_period.ends_on
                and not _already_sent_today(db, client.id, "closing_due", today)):
            subject, html = tpl.closing_due(
                brand, _first_name(client),
                f"{base}/p/{client.portal_token}", closing_period.period_index,
            )
            emailer.send(to=client.email, subject=subject, html=html,
                         kind="closing_due", client=client)
            summary["reminders"] += 1

        # 2) Cambio de estado
        if decision.new_status and decision.new_status != client.status:
            if can_transition(client.status, decision.new_status):
                old = client.status
                client.status = decision.new_status
                log_event(db, "client", client.id, "status_changed",
                          {"from": old, "to": decision.new_status, "reason": decision.reason})
                summary["transitions"] += 1

                # 3) Alerta al coach si pasa a at_risk
                if decision.notify_coach_at_risk and not _already_sent_today(
                    db, client.id, "coach_at_risk", today
                ):
                    coach_to = settings.smtp_from or settings.smtp_user
                    if coach_to:
                        subject, html = tpl.coach_at_risk(
                            brand, client.full_name, decision.reason, f"{base}/clientes/{client.id}",
                        )
                        emailer.send(to=coach_to, subject=subject, html=html,
                                     kind="coach_at_risk", client=client)
                        summary["at_risk_alerts"] += 1

    db.commit()
    return summary
