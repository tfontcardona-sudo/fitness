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

_TIERS = {"nutri", "train", "full"}
# Duraciones contratables de cada plan: mensual, trimestral, semestral.
_PERIODS = {"1m", "3m", "6m"}


class StripeError(RuntimeError):
    """Error recuperable de Stripe (config ausente, plan inválido, firma mala)."""


def _stripe():
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


# --------------------------------------------------- resolución de precios ----

# lookup_key canónico de cada precio en Stripe: dqr_{tier}_{period}. Los crea
# scripts/setup_stripe_prices.py; con ellos NO hace falta copiar IDs al .env.
_LOOKUP_TTL_S = 600
_lookup_cache: dict = {"at": 0.0, "ids": {}}


def _lookup_key(tier: str, period: str) -> str:
    return f"dqr_{tier}_{period}"


def _price_by_lookup(tier: str, period: str) -> str:
    """ID del precio ACTIVO con lookup_key dqr_{tier}_{period}, con caché.
    Best-effort: ante cualquier fallo devuelve "" (el caller decide qué hacer)."""
    import time

    now = time.time()
    if now - _lookup_cache["at"] > _LOOKUP_TTL_S:
        _lookup_cache["ids"] = {}
        _lookup_cache["at"] = now
    key = _lookup_key(tier, period)
    if key in _lookup_cache["ids"]:
        return _lookup_cache["ids"][key]
    try:
        stripe = _stripe()
        keys = [_lookup_key(t, p) for t in _TIERS for p in _PERIODS]
        found = {pr["lookup_key"]: pr["id"]
                 for pr in stripe.Price.list(lookup_keys=keys, active=True, limit=100)["data"]
                 if pr.get("lookup_key")}
        for k in keys:
            _lookup_cache["ids"][k] = found.get(k, "")
    except Exception as exc:  # noqa: BLE001 — sin red/clave: se cae a los .env
        _log.warning("No se pudieron resolver precios por lookup_key: %s", exc)
        return ""
    return _lookup_cache["ids"].get(key, "")


def _resolve_price_id(tier: str, period: str) -> str:
    """Precio a cobrar para tier×period, por orden de prioridad:
    1) .env con nombre nuevo (mando explícito del coach),
    2) lookup_key en Stripe (precios creados por el script — el camino normal),
    3) .env con nombre antiguo (START/PRO), para no romper una config previa.
    """
    direct = settings.stripe_price_for(tier, period)
    if direct:
        return direct
    by_lookup = _price_by_lookup(tier, period)
    if by_lookup:
        return by_lookup
    return settings.stripe_price_legacy(tier, period)


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
    price = _resolve_price_id(tier, period)
    if not price:
        raise StripeError(
            f"Falta el precio de Stripe del plan {tier} {period}: ejecuta "
            "scripts/setup_stripe_prices.py (o pon "
            f"STRIPE_PRICE_{tier.upper()}_{period.upper()} en el .env).")

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


# ---------------------------------------------------------------- precios ----

_PERIOD_MONTHS = {"1m": 1, "3m": 3, "6m": 6}
_prices_cache: dict = {"at": 0.0, "data": None}
_PRICES_TTL_S = 600  # los precios cambian poco; 10 min de caché evita latencia


def get_plan_prices() -> dict:
    """Importes REALES de los 9 precios (plan × duración) leídos de Stripe, para
    mostrarlos en la página de planes (total + equivalente al mes). Con caché.

    Devuelve {"currency": "eur", "tiers": {tier: {period: {"total": €, "months": n,
    "per_month": €}}}}; una combinación sin precio configurado o con error → None.
    """
    import time

    if _prices_cache["data"] is not None and time.time() - _prices_cache["at"] < _PRICES_TTL_S:
        return _prices_cache["data"]

    tiers: dict = {t: {p: None for p in _PERIOD_MONTHS} for t in _TIERS}
    currency = "eur"
    if settings.stripe_enabled:
        stripe = _stripe()
        for tier in _TIERS:
            for period, months in _PERIOD_MONTHS.items():
                price_id = _resolve_price_id(tier, period)
                if not price_id:
                    continue
                try:
                    pr = stripe.Price.retrieve(price_id)
                    amount = (pr.get("unit_amount") or 0) / 100.0
                    currency = pr.get("currency") or currency
                    tiers[tier][period] = {
                        "total": amount,
                        "months": months,
                        "per_month": round(amount / months, 2),
                    }
                except Exception as exc:  # precio borrado/ID malo: no rompe la página
                    _log.warning("Precio %s (%s %s) ilegible: %s", price_id, tier, period, exc)

    data = {"currency": currency, "tiers": tiers}
    # Un fallo TRANSITORIO de Stripe no puede dejar /planes sin precios 10 min:
    # el resultado totalmente vacío (con Stripe configurado) no se cachea — la
    # siguiente visita reintenta.
    all_empty = all(v is None for t in tiers.values() for v in t.values())
    if not (settings.stripe_enabled and all_empty):
        _prices_cache.update(at=time.time(), data=data)
    return data


# --------------------------------------------------------------- webhook ----

def _notify_coach_payment(db: Session, client: Client, *, new_client: bool) -> None:
    """Push inmediato al COACH: entró un pago (o un alta nueva con pago). Un
    ingreso no puede esperar al resumen de cada 3 h. Nunca rompe el webhook."""
    try:
        from app.services import push as push_svc

        first = ((client.full_name or "").split() or ["Un cliente"])[0]
        base = settings.public_base_url.rstrip("/")
        push_svc.send_to_coach(db, {
            "title": "Nuevo cliente pagado 🎉" if new_client else "Pago recibido",
            "body": (f"{first} se ha registrado y pagado el plan {client.package_tier}."
                     if new_client else
                     f"{first} ha completado el pago de su plan {client.package_tier}."),
            "count": 1,
            "url": f"{base}/clientes/{client.id}",
            "tag": "dq-pago",
        })
    except Exception:  # noqa: BLE001
        pass


def _mark_paid(db: Session, client: Client, period: str | None = None) -> None:
    # La duración que el cliente pagó de verdad manda sobre la de la ficha.
    if period in _PERIODS and client.billing_period != period:
        client.billing_period = period
    if client.payment_status != "paid":
        client.payment_status = "paid"
        client.paid_at = datetime.now(timezone.utc)
        log_event(db, "client", client.id, "payment_received",
                  {"tier": client.package_tier, "billing_period": client.billing_period})
        _notify_coach_payment(db, client, new_client=False)


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
    _notify_coach_payment(db, client, new_client=True)
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
    # También el ARRANQUE (enlace de la anamnesis): sin él, el cliente que
    # pagó por el checkout público directo se quedaba solo con el acceso al
    # portal y nunca recibía su cuestionario inicial.
    try:
        from app.services.onboarding import send_onboarding_email

        send_onboarding_email(db, client)
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
            _notify_orphan_payment(db, session)
            return {"error": "client_not_found", "client_id": client_id}
        _mark_paid(db, client, period)
        db.commit()
        return {"marked_paid": client.id}

    # Registro personal: crear el perfil desde los datos de Stripe.
    details = session.get("customer_details") or {}
    email = (details.get("email") or "").strip().lower()
    if not email:
        _log.warning("Webhook Stripe: checkout sin email; no se puede crear cliente")
        _notify_orphan_payment(db, session)
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
