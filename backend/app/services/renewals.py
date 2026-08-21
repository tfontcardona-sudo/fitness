"""Renovación de los planes de pago único (1m/3m/6m).

Una sola verdad para "¿cuándo vence el ciclo pagado de este cliente?", usada por:
- la alerta `renewal_due` del panel (routers/alerts.py),
- el email de renovación AL CLIENTE (services/jobs.py),
- el enlace estable de pago (routers/stripe_router.py): con la renovación al
  caer, el enlace vuelve a abrir un checkout aunque la ficha diga "paid".

La oferta (suscripción de Stripe) queda fuera a propósito: se cobra sola.
"""
from datetime import date, timedelta

BILLING_DAYS = {"1m": 30, "3m": 90, "6m": 180}
RENEWAL_WARN_DAYS = 5  # el dueño avisa al cliente 5 días antes


def renewal_window(client, today: date) -> tuple[date, int] | None:
    """(fin del ciclo pagado, días restantes — negativo si ya venció) o None si
    la renovación no aplica: sin pagar, suscripción que se cobra sola, o sin
    duración conocida. Nunca lanza."""
    if getattr(client, "payment_status", None) != "paid":
        return None
    if getattr(client, "stripe_subscription_id", None):
        return None
    paid_at = getattr(client, "paid_at", None)
    days = BILLING_DAYS.get(getattr(client, "billing_period", "") or "")
    if paid_at is None or days is None:
        return None
    ends_on = paid_at.date() + timedelta(days=days)
    return ends_on, (ends_on - today).days


def is_due(client, today: date) -> bool:
    """True si el ciclo vence en ≤5 días o ya venció (toca renovar)."""
    w = renewal_window(client, today)
    return w is not None and w[1] <= RENEWAL_WARN_DAYS
