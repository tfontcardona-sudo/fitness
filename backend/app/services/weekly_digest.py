"""Resumen SEMANAL del coach (lunes por la mañana): push 📊 + email.

Una foto de la semana sin abrir el panel: cuántos clientes van al día, quién
está en riesgo, qué revisiones esperan feedback, renovaciones al caer y pagos
pendientes. Todo determinista (sin IA) sobre datos que ya existen.

Idempotente por semana: si el email `coach_weekly_summary` ya salió en los
últimos 6 días, no se repite (protege contra reinicios del scheduler el lunes).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client, DailyLog, EmailLog, Period

_log = logging.getLogger("app.weekly_digest")

DIGEST_KIND = "coach_weekly_summary"


@dataclass
class ClientWeek:
    client_id: int
    name: str
    status: str
    days_logged: int          # días con contenido REAL en los últimos 7
    weight_delta_kg: float | None  # último pesaje − primero (ventana 14 días)
    flags: list[str] = field(default_factory=list)
    brand: str = ""           # marca del cliente; vacío si el sistema lleva una sola


@dataclass
class WeeklyDigest:
    week_label: str
    clients: list[ClientWeek]
    at_risk: list[str]
    review_pending: list[str]
    renewals: list[str]
    unpaid: list[str]

    @property
    def active_count(self) -> int:
        return len(self.clients)

    @property
    def on_track_count(self) -> int:
        return sum(1 for c in self.clients if c.days_logged >= 5 and c.status == "active")


def _week_of(client: Client, db: Session, hoy) -> ClientWeek:
    from app.services.push import dias_registrados

    # 7 días INCLUSIVOS (hoy-6 … hoy): con hoy-7 la ventana tenía 8 fechas y un
    # cliente constante salía como "8/7" en el email.
    desde7 = hoy - timedelta(days=6)
    desde14 = hoy - timedelta(days=14)
    logs = db.execute(
        select(DailyLog)
        .join(Period, Period.id == DailyLog.period_id)
        .where(Period.client_id == client.id,
               DailyLog.log_date >= desde14, DailyLog.log_date <= hoy)
        .order_by(DailyLog.log_date)
    ).scalars().all()
    # Cuenta TODO lo que registra el cliente (diario, series de entreno o
    # comidas elegidas): un DQR Train solo registra series y salía con 0/7.
    dias = dias_registrados(db, [lg for lg in logs if lg.log_date >= desde7])
    pesos = [(lg.log_date, lg.weight_kg) for lg in logs if lg.weight_kg]
    delta = None
    if len(pesos) >= 3:
        delta = round(pesos[-1][1] - pesos[0][1], 1)
    return ClientWeek(
        client_id=client.id, name=client.full_name or client.email,
        status=client.status, days_logged=len(dias), weight_delta_kg=delta,
        brand=_marca_de(client, db),
    )


def _marca_de(client: Client, db: Session) -> str:
    """Nombre de la marca del cliente, o "" si solo hay una.

    El resumen semanal NO se filtra por la marca activa a propósito: es el
    correo del lunes del coach y tiene que llevar a TODOS sus clientes —
    cambiar el switch un viernes no puede dejar a media cartera sin vigilar.
    Lo que sí hace falta es saber de qué negocio es cada fila."""
    from app.services.branding import hay_varias_marcas, marca_de_cliente

    if not hay_varias_marcas(db):
        return ""
    return marca_de_cliente(client, db).name


def build_digest(db: Session, hoy=None) -> WeeklyDigest:
    """Construye el resumen de la semana que termina HOY (fecha de negocio)."""
    from app.services.portal import today_local
    from app.services.renewals import is_due

    hoy = hoy or today_local()
    clientes = db.execute(
        select(Client).where(Client.status.in_(("active", "at_risk", "review_pending")))
        .order_by(Client.full_name)
    ).scalars().all()

    semanas: list[ClientWeek] = []
    at_risk: list[str] = []
    review_pending: list[str] = []
    renewals: list[str] = []
    unpaid: list[str] = []
    for c in clientes:
        w = _week_of(c, db, hoy)
        if c.status == "at_risk":
            w.flags.append("en riesgo")
            at_risk.append(w.name)
        if c.status == "review_pending":
            w.flags.append("revisión por enviar")
            review_pending.append(w.name)
        if is_due(c, hoy):
            w.flags.append("renovación al caer")
            renewals.append(w.name)
        if getattr(c, "payment_status", None) == "pending":
            w.flags.append("pago pendiente")
            unpaid.append(w.name)
        semanas.append(w)

    ini = hoy - timedelta(days=6)
    label = f"{ini.strftime('%d/%m')} – {hoy.strftime('%d/%m')}"
    return WeeklyDigest(week_label=label, clients=semanas, at_risk=at_risk,
                        review_pending=review_pending, renewals=renewals,
                        unpaid=unpaid)


def _sent_this_week(db: Session) -> bool:
    desde = datetime.now(timezone.utc) - timedelta(days=6)
    n = db.scalar(
        select(func.count()).select_from(EmailLog).where(
            EmailLog.kind == DIGEST_KIND, EmailLog.sent_at >= desde,
            EmailLog.status == "sent")
    )
    return bool(n)


def run_weekly_digest(db: Session, hoy=None) -> dict:
    """Job del lunes: arma el resumen y lo envía (push + email al coach).
    Nunca lanza; devuelve un pequeño informe para el log."""
    resumen = {"clients": 0, "push": False, "email": False, "skipped": None}
    try:
        digest = build_digest(db, hoy)
        resumen["clients"] = digest.active_count
        if digest.active_count == 0:
            resumen["skipped"] = "sin clientes activos"
            return resumen

        # ---- push (best-effort) ----
        try:
            from app.services import push as push_svc

            if push_svc.push_configured():
                partes = [f"{digest.on_track_count}/{digest.active_count} al día"]
                if digest.at_risk:
                    partes.append(f"{len(digest.at_risk)} en riesgo")
                if digest.review_pending:
                    partes.append(f"{len(digest.review_pending)} revisiones por enviar")
                if digest.renewals:
                    partes.append(f"{len(digest.renewals)} renovaciones al caer")
                payload = {
                    "title": f"📊 Resumen semanal · {digest.week_label}",
                    "body": " · ".join(partes),
                    # Sin count, el service worker apagaba el badge del coach:
                    # el resumen del lunes le borraba los "N pagos sin leer".
                    "count": len(digest.at_risk) + len(digest.review_pending)
                             + len(digest.renewals),
                    "url": "/",
                    "tag": "dq-weekly",
                }
                push_svc.send_to_coach(db, payload)
                resumen["push"] = True
        except Exception as exc:  # noqa: BLE001
            _log.warning("Push del resumen semanal no enviado: %s", exc)

        # ---- email (idempotente por semana) ----
        if _sent_this_week(db):
            resumen["skipped"] = "email ya enviado esta semana"
            return resumen
        from app.services import email_templates as tpl
        from app.services.email_service import EmailService, brand_from_config

        emailer = EmailService(db)
        destinatario = settings.smtp_from or settings.smtp_user
        if not destinatario:
            resumen["skipped"] = "sin email del coach configurado"
            return resumen
        brand = brand_from_config(db)
        subject, html = tpl.coach_weekly_summary(brand, digest)
        estado = emailer.send(to=destinatario, subject=subject, html=html,
                              kind=DIGEST_KIND)
        resumen["email"] = estado == "sent"
        db.commit()
    except Exception as exc:  # noqa: BLE001 — un fallo no tumba el scheduler
        _log.warning("Resumen semanal fallido: %s", exc)
        db.rollback()
    return resumen
