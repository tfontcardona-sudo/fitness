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


# Tope de recordatorios de cierre por período (ver 1b).
MAX_AVISOS_DE_CIERRE = 3


# `EmailLog` anota los TRES desenlaces: `sent`, `failed` (SMTP caído, dirección
# rechazada…) y `disabled` (los correos están apagados, del cliente o del
# servidor). Los contadores de abajo descartan los FALLIDOS: contarlos hacía que
# un correo que ni salió consumiera su intento — un fallo puntual de SMTP dejaba
# el recordatorio sin reintentar JAMÁS, y tres días de SMTP caído agotaban el
# tope de avisos de cierre para toda la quincena (el cliente no recibía ninguno
# y nadie lo notaba, porque en el libro constaban tres).
#
# Los `disabled` SÍ cuentan, y a propósito: ahí no ha fallado nada, es que ese
# cliente —o el servidor entero, como en desarrollo— tiene los correos
# apagados. Reintentarlo cada día solo llenaría el registro de filas sin enviar
# un solo correo.
_NO_FALLIDO = EmailLog.status != "failed"


def _already_sent_today(db: Session, client_id: int, kind: str, today: date) -> bool:
    """¿Ya se le mandó HOY un correo de este tipo?

    Un envío FALLIDO (SMTP caído, contraseña caducada) deja igualmente su fila en
    el registro. Contarla como "ya enviado" convertía una caída pasajera del
    correo en un recordatorio perdido para SIEMPRE: el del día 12, el de cerrar
    la quincena y los de arranque (D+3/D+7) solo se disparan en SU día, así que
    no había segunda oportunidad. Ahora un fallo no bloquea: al día siguiente se
    reintenta (el mantenimiento corre una vez al día, no hay riesgo de repetir).

    Los `disabled` SÍ cuentan: no son un fallo, es que ese cliente tiene los
    correos apagados a propósito — reintentarlo cada día solo llenaría el
    registro sin enviar nada.
    """
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    n = db.scalar(
        select(func.count())
        .select_from(EmailLog)
        .where(
            EmailLog.client_id == client_id,
            EmailLog.kind == kind,
            EmailLog.sent_at >= start,
            _NO_FALLIDO,
        )
    )
    return bool(n)


def _enviados_desde(db: Session, client_id: int, kind: str, desde: date) -> int:
    """Cuántas veces se ha mandado ese aviso desde una fecha (inicio de período
    o alta del cliente). Un envío FALLIDO no gasta cupo."""
    inicio = datetime(desde.year, desde.month, desde.day, tzinfo=timezone.utc)
    return int(db.scalar(
        select(func.count()).select_from(EmailLog).where(
            EmailLog.client_id == client_id, EmailLog.kind == kind,
            EmailLog.sent_at >= inicio,
            _NO_FALLIDO,
        )
    ) or 0)


def _ya_enviado_desde(db: Session, client_id: int, kind: str, desde: date) -> bool:
    """¿Se envió ya ese aviso en ESTE ciclo (desde el alta o el inicio del
    período)? Con la dedup por DÍA, los avisos de día exacto no se podían
    relajar a ">=" sin repetirlos; con esta, se envían en cuanto el job vuelva
    a correr y solo una vez."""
    return _enviados_desde(db, client_id, kind, desde) > 0


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
    # (el disparador de "en riesgo" y el % que ve el coach mentían). Y cuenta
    # TODO lo que el cliente registra —diario, series de entreno o comidas
    # elegidas—, no solo el diario: un DQR Train registra sus series y nada
    # más, y salía con 0 días → "en riesgo" con adherencia 0 %.
    from app.services.push import dias_con_registro

    dias = dias_con_registro(db, period.id)
    days_logged = len(dias)
    last_activity = max(dias) if dias else period.starts_on

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
               "periods_opened": 0,
               # Clientes que reventaron: sin esto el trabajo se anotaba como
               # correcto y ese cliente se quedaba sin recordatorios, sin
               # cierre vencido y sin transición de estado — cada día, en
               # silencio. `automatismos_parados()` solo ve el job entero
               # caído, no un cliente caído.
               "failed": 0, "failed_ids": []}

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
            summary["failed"] += 1
            if len(summary["failed_ids"]) < 20:
                summary["failed_ids"].append(client.id)

    # Aprendizaje del coach (§13 en vivo): si hay suficientes ediciones nuevas
    # de planes, se re-destilan las lecciones (modelo ligero, best-effort).
    try:
        from app.services.coach_lessons import maybe_refresh

        refreshed = maybe_refresh(db)
        if refreshed is not None:
            summary["lessons_refreshed"] = len(refreshed.get("lessons") or [])
    except Exception:  # noqa: BLE001
        pass

    # BACKSTOP de la OFERTA (las dos formas de pago): si el webhook que
    # cancela la suscripción tras el último cobro (el 2º de 120,50 € o el 3º
    # de 1 € + 120 + 120) se perdió (o Stripe falló en ese momento), aquí se
    # reintenta a diario — sin esto, al mes siguiente entraría un cargo
    # indebido. Best-effort: nunca rompe el job.
    try:
        from app.services.stripe_service import (
            OFFER_CHARGES_BY_PERIOD, detener_suscripcion_oferta,
            pagos_oferta_cobrados,
        )

        pendientes = db.scalars(
            select(Client).where(
                Client.billing_period.in_(list(OFFER_CHARGES_BY_PERIOD)),
                Client.stripe_subscription_id.is_not(None))
        ).all()
        for c in pendientes:
            requeridos = OFFER_CHARGES_BY_PERIOD[c.billing_period]
            if pagos_oferta_cobrados(db, c, c.billing_period) >= requeridos:
                if detener_suscripcion_oferta(db, c, c.stripe_subscription_id,
                                              motivo="backstop_diario",
                                              periodo=c.billing_period):
                    summary["ofertas_detenidas"] = summary.get("ofertas_detenidas", 0) + 1
                db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    return summary


def _maintain_client(db: Session, client: Client, today: date,
                     emailer: EmailService, brand, base: str, summary: dict) -> None:
    """Mantenimiento de UN cliente (recordatorios + transición de estado).
    El commit lo hace el caller, cliente a cliente."""
    facts = _facts_for(db, client)
    decision = evaluate_transition(facts, today)

    # 1) Recordatorio día 12 (no cambia estado)
    # Dedup por PERÍODO (no por día): con el umbral del día 12, la dedup diaria
    # habría mandado el mismo aviso los días 12, 13, 14…
    _periodo = _active_period(db, client.id)
    _desde = _periodo.starts_on if _periodo is not None else today
    if decision.send_reminder and not _ya_enviado_desde(
            db, client.id, "reminder_no_logs", _desde):
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

    # 1b) Día 14+: recordatorio de CERRAR la revisión quincenal.
    # CON TOPE: era uno al día SIN LÍMITE mientras el período siguiera abierto,
    # y el freno solo llegaba al pasar a `inactive` (30 días sin registros). Un
    # cliente que abandona el día 14 recibía ~31 emails y ~150 push por UNA
    # quincena: la vía rápida a que marque el remitente como spam y desinstale
    # la app. Tres avisos por período es insistir; treinta es acoso.
    closing_period = _active_period(db, client.id)
    _avisos_cierre = (
        _enviados_desde(db, client.id, "closing_due", closing_period.starts_on)
        if closing_period is not None else 0)
    if (closing_period is not None and closing_period.status == "open"
            and today >= closing_period.ends_on
            and _avisos_cierre < MAX_AVISOS_DE_CIERRE
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
        # UMBRAL, no igualdad: era el ÚNICO empujón automático a quien pagó y
        # no manda su anamnesis, y se disparaba solo si el job corría ESE día
        # exacto. Un reinicio del contenedor antes de las 06:30 (o un fallo con
        # ese cliente) y el aviso se perdía para siempre. La dedup ya no es por
        # día sino desde el ALTA: se manda una sola vez, cuando toque.
        hito = 7 if days_onb >= 7 else (3 if days_onb >= 3 else 0)
        if hito:
            try:
                from app.services.storage import anamnesis_documents
                has_doc = bool(anamnesis_documents(client.id))
            except Exception:  # noqa: BLE001
                has_doc = True  # ante la duda, no molestar
            # El formulario digital del portal también cuenta como enviada.
            if getattr(client, "consent_signed_at", None) is not None:
                has_doc = True
            kind = f"onboarding_reminder_d{hito}"
            if not has_doc and not _ya_enviado_desde(
                    db, client.id, kind, client.created_at.date()):
                anamnesis_url = f"{base}/anamnesis/{client.portal_token}"
                subject, html = tpl.onboarding_reminder(
                    brand, _first_name(client), anamnesis_url, hito)
                emailer.send(to=client.email, subject=subject, html=html,
                             kind=kind, client=client)
                summary["reminders"] += 1

    # 1e) RENOVACIÓN al cliente: su plan de pago único vence en ≤5 días (o ya
    # venció). UNA vez por ciclo pagado: el sello renewal_reminder_sent_at se
    # compara contra paid_at — un pago nuevo re-arma el aviso del ciclo
    # siguiente. El CTA es su enlace estable de pago, que en ventana de
    # renovación vuelve a abrir un checkout (routers/stripe_router.pay_link).
    from app.services.renewals import renewal_window, RENEWAL_WARN_DAYS

    ventana = renewal_window(client, today)
    if ventana is not None and ventana[1] <= RENEWAL_WARN_DAYS:
        ya_avisado = (client.renewal_reminder_sent_at is not None
                      and client.paid_at is not None
                      and client.renewal_reminder_sent_at >= client.paid_at)
        if not ya_avisado:
            ends_on, left = ventana
            subject, html = tpl.renewal_reminder(
                brand, _first_name(client),
                f"{base}/api/pay/{client.portal_token}",
                ends_on.strftime("%d/%m/%Y"), expired=left < 0,
            )
            resultado = emailer.send(to=client.email, subject=subject, html=html,
                                     kind="renewal_reminder", client=client)
            if resultado == "sent":
                from datetime import datetime, timezone

                client.renewal_reminder_sent_at = datetime.now(timezone.utc)
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
                "count": 1,
                        "body": decision.reason or "30 días sin actividad.",
                        "count": 1,  # sin count, el sw apagaba el badge de otros avisos
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
