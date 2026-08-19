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
from app.services import packages as pkgs
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

    # Solo cuentan los días con contenido REAL: el autosave del portal crea la
    # fila vacía con solo abrir la pantalla, y contarla inflaba la adherencia
    # (el disparador de "en riesgo" y el % que ve el coach mentían).
    from app.services.push import diary_is_filled

    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id)
    ))
    days_logged = sum(1 for lg in logs if diary_is_filled(lg))

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
    # Fecha LOCAL (Europe/Madrid), no la del servidor (UTC): entre las 00:00 y
    # las 02:00 locales date.today() aún sería "ayer" y descuadraría los días.
    from app.services.portal import today_local

    today = today or today_local()
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
    # Consolidar las aperturas ANTES del mantenimiento: sin este commit, el
    # primer fallo del bucle de abajo hacía rollback y se llevaba por delante
    # los períodos recién abiertos de TODOS los clientes de esta ejecución
    # (auditoría crítica) — el mantenimiento ya comitea cliente a cliente.
    db.commit()

    emailer = EmailService(db)
    brand = brand_from_config(db)
    base = settings.public_base_url

    for client in clients:
        summary["evaluated"] += 1
        # Cada cliente consolida SU trabajo con su propio commit: si un cliente
        # posterior falla, los EmailLog de correos YA ENTREGADOS por SMTP no se
        # pierden en el rollback (sin esto, la siguiente ejecución los
        # reenviaba duplicados al no constar en email_log).
        try:
            _maintain_client(db, client, today, emailer, brand, base, summary)
            db.commit()
        except Exception:
            import logging

            logging.getLogger("jobs").exception(
                "mantenimiento fallido del cliente %s; se continúa", client.id)
            db.rollback()

    return summary


def _maintain_client(db: Session, client: Client, today: date,
                     emailer: EmailService, brand, base: str, summary: dict) -> None:
    """Mantenimiento de UN cliente (recordatorios + transición de estado).
    El commit lo hace el caller, cliente a cliente."""
    facts = _facts_for(db, client)
    decision = evaluate_transition(facts, today)

    # 1) Recordatorio día 12 (no cambia estado)
    if decision.send_reminder and not _already_sent_today(db, client.id, "reminder_no_logs", today):
        period = _active_period(db, client.id)
        days_left = max(0, (period.ends_on - today).days) if period else 0
        subject, html = tpl.reminder_no_logs(
            brand, _first_name(client),
            f"{base}/p/{client.portal_token}", days_left,
            has_training=pkgs.has_training(getattr(client, "package_tier", None)),
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

    # 1c) Recordatorio (email) de la videollamada de MAÑANA (Pro con evento
    # agendado en Google Meet). Complementa la invitación nativa de Google y el
    # push del portal: capa extra "para que no pase por alto". Uno al día.
    if pkgs.has_video_call(getattr(client, "package_tier", None)):
        from datetime import timedelta

        from app.models import VideoCall
        from app.services.portal import format_when_es

        vc = db.scalar(
            select(VideoCall).where(
                VideoCall.client_id == client.id,
                VideoCall.status == "scheduled",
                VideoCall.scheduled_for == today + timedelta(days=1),
            )
        )
        if (vc is not None and vc.meet_url and vc.scheduled_at is not None
                and not _already_sent_today(db, client.id, "video_call_reminder", today)):
            subject, html = tpl.video_call_reminder(
                brand, _first_name(client), format_when_es(vc.scheduled_at), vc.meet_url)
            emailer.send(to=client.email, subject=subject, html=html,
                         kind="video_call_reminder", client=client)
            summary["reminders"] += 1

    # 1d) ONBOARDING fantasma (auditoría del ciclo): quien paga/registra y no
    # envía la anamnesis no recibía NINGÚN recordatorio nunca más. D+3 y D+7.
    if client.status == "onboarding" and getattr(client, "created_at", None):
        days_onb = (today - client.created_at.date()).days
        if days_onb in (3, 7):
            try:
                from app.services.storage import list_documents
                has_doc = bool(list_documents(client.id))
            except Exception:  # noqa: BLE001
                has_doc = True  # ante la duda, no molestar
            kind = f"onboarding_reminder_d{days_onb}"
            if not has_doc and not _already_sent_today(db, client.id, kind, today):
                anamnesis_url = f"{base}/anamnesis/{client.portal_token}"
                subject, html = tpl.onboarding_reminder(
                    brand, _first_name(client), anamnesis_url, days_onb)
                emailer.send(to=client.email, subject=subject, html=html,
                             kind=kind, client=client)
                summary["reminders"] += 1

    # 2) Cambio de estado
    if decision.new_status and decision.new_status != client.status:
        if can_transition(client.status, decision.new_status):
            old = client.status
            client.status = decision.new_status
            log_event(db, "client", client.id, "status_changed",
                      {"from": old, "to": decision.new_status, "reason": decision.reason})
            summary["transitions"] += 1

            # La caída a INACTIVO era silenciosa (auditoría del ciclo): push
            # inmediato al coach para decidir (reactivar/archivar/escribirle).
            if decision.new_status == "inactive":
                try:
                    from app.services import push as push_svc

                    push_svc.send_to_coach(db, {
                        "title": f"💤 {client.full_name} ha pasado a inactivo",
                        "body": decision.reason or "30 días sin actividad.",
                        "url": f"/clientes/{client.id}",
                        "tag": f"inactive-{client.id}",
                    })
                except Exception:  # noqa: BLE001 — el push nunca rompe el job
                    pass

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
