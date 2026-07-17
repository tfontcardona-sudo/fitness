"""Integración con Stripe: sesiones de pago (Checkout) y webhook de cobro.

Dos formas de registrarse:
- Registro PERSONAL (self-serve): el cliente elige plan en la página pública de
  planes, paga, y el webhook crea su perfil (con su plan) marcado como pagado y
  le envía el acceso al portal para rellenar la anamnesis.
- Alta MANUAL: el coach crea el cliente; el enlace de pago lleva su client_id y,
  al pagar, el webhook marca a ESE cliente como pagado.

El estado de pago es SOLO informativo: no bloquea el trabajo del coach.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Client
from app.security import new_portal_token
from app.services.audit import log_event

_log = logging.getLogger("app.stripe")

_TIERS = {"start", "full", "pro"}
# Duraciones contratables de cada plan: mensual, trimestral, semestral.
_PERIODS = {"1m", "3m", "6m"}


class StripeError(RuntimeError):
    """Error recuperable de Stripe (config ausente, plan inválido, firma mala)."""


def _stripe():
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


def create_checkout_url(db: Session, tier: str, period: str = "1m", *,
                        client: Client | None = None) -> str:
    """Crea una Checkout Session de Stripe para `tier` × `period` (duración
    mensual/trimestral/semestral) y devuelve su URL de pago.

    Si `client` viene dado (alta manual), el pago queda asociado a ese cliente
    (client_id en metadata). Si no (registro personal), Stripe recoge email,
    nombre y teléfono y el webhook creará el perfil."""
    if not settings.stripe_enabled:
        raise StripeError("Stripe no está configurado (falta STRIPE_SECRET_KEY en el .env).")
    if tier not in _TIERS:
        raise StripeError(f"Plan desconocido: {tier}")
    if period not in _PERIODS:
        raise StripeError(f"Duración desconocida: {period}")
    price = settings.stripe_price_for(tier, period)
    if not price:
        raise StripeError(
            f"Falta el precio de Stripe del plan {tier} {period} "
            f"(STRIPE_PRICE_{tier.upper()}_{period.upper()} en el .env).")

    stripe = _stripe()
    base = settings.public_base_url
    metadata = {"tier": tier, "billing_period": period}
    extra: dict = {}
    if client is not None:
        metadata["client_id"] = str(client.id)
        if client.email:
            extra["customer_email"] = client.email
    else:
        # Registro personal: pedimos teléfono para poder contactar al cliente.
        extra["phone_number_collection"] = {"enabled": True}

    session = stripe.checkout.Session.create(
        mode=settings.stripe_mode,
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{base}/pago-ok",
        cancel_url=f"{base}/planes",
        metadata=metadata,
        client_reference_id=(str(client.id) if client else None),
        **extra,
    )
    return session.url


# --------------------------------------------------------------- webhook ----

def _mark_paid(db: Session, client: Client, period: str | None = None) -> None:
    # La duración que el cliente pagó de verdad manda sobre la de la ficha.
    if period in _PERIODS and client.billing_period != period:
        client.billing_period = period
    if client.payment_status != "paid":
        client.payment_status = "paid"
        client.paid_at = datetime.now(timezone.utc)
        log_event(db, "client", client.id, "payment_received",
                  {"tier": client.package_tier, "billing_period": client.billing_period})


def _create_selfserve_client(db: Session, *, name: str, email: str,
                             phone: str | None, tier: str, period: str | None) -> Client:
    """Crea el perfil de un cliente que se ha registrado y pagado por su cuenta."""
    client = Client(
        full_name=(name or email.split("@")[0]).strip(),
        email=email,
        phone=phone,
        package_tier=tier if tier in _TIERS else "full",
        billing_period=period if period in _PERIODS else "1m",
        status="onboarding",
        auto_pilot=settings.auto_pilot_default,
        portal_token="pendiente",
        payment_status="paid",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(client)
    db.flush()
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "client_created",
              {"by": "stripe", "tier": client.package_tier,
               "billing_period": client.billing_period})
    log_event(db, "client", client.id, "payment_received",
              {"tier": client.package_tier, "billing_period": client.billing_period})
    db.commit()
    db.refresh(client)

    # Le enviamos el acceso al portal para que rellene su anamnesis (arranca el
    # workflow normal). El envío nunca bloquea la creación.
    try:
        from app.services.portal_access import send_portal_access

        send_portal_access(db, client)
        db.commit()
    except Exception:
        db.rollback()
    return client


def handle_webhook(db: Session, payload: bytes, sig_header: str | None) -> dict:
    """Verifica el aviso de Stripe y actúa sobre `checkout.session.completed`:
    marca el pago del cliente (alta manual) o crea el perfil (registro personal)."""
    if not settings.stripe_webhook_secret:
        raise StripeError("Falta STRIPE_WEBHOOK_SECRET en el .env.")
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header or "", settings.stripe_webhook_secret)
    except Exception as exc:  # firma inválida o payload corrupto
        raise StripeError(f"Firma del webhook inválida: {exc}") from exc

    if event["type"] != "checkout.session.completed":
        return {"ignored": event["type"]}

    session = event["data"]["object"]
    # En modo pago único exigimos que el cobro esté completado.
    if session.get("payment_status") == "unpaid":
        return {"ignored": "unpaid"}

    meta = session.get("metadata") or {}
    tier = meta.get("tier")
    period = meta.get("billing_period")
    client_id = meta.get("client_id") or session.get("client_reference_id")

    # Alta manual: marcar ese cliente como pagado.
    if client_id:
        client = db.get(Client, int(client_id))
        if not client:
            _log.warning("Webhook Stripe: cliente %s no encontrado", client_id)
            return {"error": "client_not_found", "client_id": client_id}
        _mark_paid(db, client, period)
        db.commit()
        return {"marked_paid": client.id}

    # Registro personal: crear el perfil desde los datos de Stripe.
    details = session.get("customer_details") or {}
    email = (details.get("email") or "").strip().lower()
    if not email:
        _log.warning("Webhook Stripe: checkout sin email; no se puede crear cliente")
        return {"error": "no_email"}
    existing = db.scalar(select(Client).where(func.lower(Client.email) == email))
    if existing:  # ya existía (o webhook reenviado): idempotente
        _mark_paid(db, existing, period)
        db.commit()
        return {"marked_paid": existing.id, "existing": True}

    client = _create_selfserve_client(
        db, name=details.get("name") or "", email=email,
        phone=details.get("phone"), tier=tier or "full", period=period)
    return {"created": client.id}
