"""Máquina de estados del cliente (G.2).

    onboarding → active → awaiting_feedback
              → (at_risk si +4 días sin cerrar tras fin de período
                 o <30% de registros a día 10)
              → review_pending → active …
    inactive (manual o >30 días sin actividad)

Diseño en dos capas:

1. `evaluate_transition(...)` — FUNCIÓN PURA: dado el estado actual y unos
   hechos (fechas, conteo de registros, si el período está cerrado…), decide
   el nuevo estado y el motivo. Sin DB, sin emails: 100% testable.

2. `apply_daily_transitions(db, ...)` — capa con efectos: lee los clientes,
   calcula los hechos desde la DB, llama a la función pura y, si hay cambio,
   persiste el estado, registra en audit_log y dispara el email/alerta que
   corresponda. Idempotente: ejecutarla dos veces el mismo día no duplica
   transiciones ni emails (los emails de aviso se controlan por kind+día).

Las transiciones que dependen de eventos (publicar plan → active; enviar
feedback → review_pending→active) las disparan los endpoints/pipeline, no el
scheduler; aquí vive solo lo que depende del paso del tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Umbrales de G.2
AT_RISK_DAYS_AFTER_PERIOD_END = 4   # +4 días sin cerrar tras fin de período
LOG_RATIO_CHECK_DAY = 10            # a día 10 del período
LOG_RATIO_MIN = 0.30               # <30% de registros → at_risk
INACTIVE_DAYS = 30                 # >30 días sin actividad → inactive
REMINDER_DAY = 12                  # recordatorio si no registra (día 12)


@dataclass
class ClientFacts:
    """Hechos observables de un cliente, calculados desde la DB."""

    status: str
    has_active_period: bool = False
    period_start: date | None = None
    period_end: date | None = None
    period_closed: bool = False
    days_logged_in_period: int = 0
    last_activity_date: date | None = None  # último log o cierre


@dataclass
class TransitionDecision:
    new_status: str | None      # None = sin cambio
    reason: str = ""
    # Señales para la capa de efectos (no cambian estado pero disparan email):
    send_reminder: bool = False
    notify_coach_at_risk: bool = False


def _period_day(today: date, start: date) -> int:
    """Día del período (1-indexado). Día de inicio = día 1."""
    return (today - start).days + 1


def evaluate_transition(facts: ClientFacts, today: date) -> TransitionDecision:
    """Decide la transición por paso del tiempo. Función pura.

    Orden de prioridad: inactividad > at_risk > recordatorio. Estados terminales
    o gestionados por eventos (onboarding, review_pending) no transicionan aquí.
    """
    status = facts.status

    # inactive: cualquier estado activo con >30 días sin actividad
    if status in ("active", "awaiting_feedback", "at_risk"):
        if facts.last_activity_date is not None:
            idle = (today - facts.last_activity_date).days
            if idle > INACTIVE_DAYS:
                return TransitionDecision("inactive", f"{idle} días sin actividad")

    # onboarding no transiciona por tiempo (espera a publicar plan → evento)
    if status == "onboarding":
        return TransitionDecision(None)

    if status in ("active", "awaiting_feedback"):
        # ¿Período terminado y sin cerrar +4 días? → at_risk
        if facts.period_end is not None and not facts.period_closed:
            days_past_end = (today - facts.period_end).days
            if days_past_end >= AT_RISK_DAYS_AFTER_PERIOD_END:
                return TransitionDecision(
                    "at_risk",
                    f"{days_past_end} días sin cerrar el período",
                    notify_coach_at_risk=True,
                )

        # ¿Baja adherencia a día 10? → at_risk
        if facts.period_start is not None and not facts.period_closed:
            day = _period_day(today, facts.period_start)
            if day >= LOG_RATIO_CHECK_DAY:
                expected = day
                ratio = facts.days_logged_in_period / expected if expected else 0
                if ratio < LOG_RATIO_MIN:
                    return TransitionDecision(
                        "at_risk",
                        f"adherencia {ratio * 100:.0f}% (<{LOG_RATIO_MIN * 100:.0f}%) a día {day}",
                        notify_coach_at_risk=True,
                    )

        # Recordatorio día 12 si aún no ha registrado nada hoy/poco (no cambia estado)
        if (
            status == "active"
            and facts.period_start is not None
            and not facts.period_closed
            and _period_day(today, facts.period_start) == REMINDER_DAY
            and facts.days_logged_in_period < REMINDER_DAY // 2
        ):
            return TransitionDecision(None, "recordatorio día 12", send_reminder=True)

    return TransitionDecision(None)


# valid transitions for event-driven changes (validación defensiva)
VALID_TRANSITIONS = {
    "onboarding": {"active", "inactive"},
    "active": {"awaiting_feedback", "at_risk", "inactive"},
    "awaiting_feedback": {"review_pending", "at_risk", "active", "inactive"},
    "at_risk": {"review_pending", "active", "inactive"},
    "review_pending": {"active", "inactive"},
    "inactive": {"active"},  # reactivación manual
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())
