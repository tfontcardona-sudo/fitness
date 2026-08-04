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
from app.services import packages as pkgs
from app.services.audit import log_event

_log = logging.getLogger("app.stripe")

_TIERS = {"nutri", "train", "full"}
# Duraciones contratables de cada plan: mensual, trimestral, semestral.
_PERIODS = {"1m", "3m", "6m"}

# Orden estable para recorrer/crear (los sets de arriba validan pertenencia).
TIER_ORDER = ("train", "nutri", "full")
PERIOD_ORDER = ("1m", "3m", "6m")

# ------------------------------------------ precios canónicos (la verdad) ----

# Importes en CÉNTIMOS de cada plan × duración: 69/79/129 € al mes. El ancla
# la fijó el dueño: Full trimestral = 330 € (110 €/mes) y el resto se adapta
# con la misma escala de descuento — trimestral ≈ −15 % por mes y semestral
# ≈ −22 % por mes, siempre con Nutri > Train y Full < Train+Nutri por duración:
#   Train  69 · 177 (59/mes) · 324 (54/mes)
#   Nutri  79 · 201 (67/mes) · 372 (62/mes)
#   Full  129 · 330 (110/mes) · 600 (100/mes)
# De esta tabla beben el script scripts/setup_stripe_prices.py, el AUTO-ALTA
# (si a Stripe le faltan precios, la api los crea sola; si cambia el importe,
# precio nuevo con el lookup_key transferido) y la reserva visual del catálogo.
CANONICAL_AMOUNTS: dict[str, dict[str, int]] = {
    "train": {"1m": 6900, "3m": 17700, "6m": 32400},
    "nutri": {"1m": 7900, "3m": 20100, "6m": 37200},
    "full": {"1m": 12900, "3m": 33000, "6m": 60000},
}
PRODUCT_NAMES = {"train": "DQR Train", "nutri": "DQR Nutri", "full": "DQR Full"}
PERIOD_LABEL = {"1m": "1 mes", "3m": "3 meses", "6m": "6 meses"}
CURRENCY = "eur"


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


def ensure_canonical_prices(stripe, log=None) -> list[str]:
    """Asegura EN STRIPE los 9 precios canónicos, de forma IDEMPOTENTE:
    un Producto por plan (marcado con metadata dqr_tier) y un Precio por
    plan × duración con lookup_key dqr_{tier}_{period}. Si un precio existe
    con OTRO importe, crea el nuevo y le transfiere el lookup_key (el antiguo
    queda desactivado; los pagos pasados no se tocan).

    Lo usan el script scripts/setup_stripe_prices.py (log=print) y el
    auto-alta de _price_by_lookup (log al logger). Devuelve el resumen."""
    say = log or (lambda msg: _log.info("%s", msg))
    out: list[str] = []

    def note(msg: str) -> None:
        out.append(msg)
        say(msg)

    products = {(p.get("metadata") or {}).get("dqr_tier"): p["id"]
                for p in stripe.Product.list(active=True, limit=100)["data"]}
    keys = [_lookup_key(t, p) for t in TIER_ORDER for p in PERIOD_ORDER]
    existing = {pr["lookup_key"]: pr
                for pr in stripe.Price.list(lookup_keys=keys, active=True,
                                            limit=100)["data"]
                if pr.get("lookup_key")}

    for tier in TIER_ORDER:
        product_id = products.get(tier)
        if not product_id:
            prod = stripe.Product.create(
                name=PRODUCT_NAMES[tier], metadata={"dqr_tier": tier},
                description=f"Asesoría {PRODUCT_NAMES[tier]} — pago por período",
            )
            product_id = prod["id"]
            note(f"  + producto creado: {PRODUCT_NAMES[tier]} ({product_id})")
        for period in PERIOD_ORDER:
            key = _lookup_key(tier, period)
            amount = CANONICAL_AMOUNTS[tier][period]
            nickname = f"{PRODUCT_NAMES[tier]} · {PERIOD_LABEL[period]}"
            pr = existing.get(key)
            if pr and pr["unit_amount"] == amount and pr["currency"] == CURRENCY:
                note(f"  = {key}: ya existe con {amount / 100:.2f} € (sin cambios)")
                continue
            if pr:
                # Importe distinto: precio nuevo con el MISMO lookup_key.
                stripe.Price.create(
                    product=pr["product"], currency=CURRENCY, unit_amount=amount,
                    lookup_key=key, transfer_lookup_key=True, nickname=nickname,
                )
                stripe.Price.modify(pr["id"], active=False)
                note(f"  ~ {key}: {pr['unit_amount'] / 100:.2f} € → "
                     f"{amount / 100:.2f} € (precio nuevo, el antiguo desactivado)")
            else:
                stripe.Price.create(
                    product=product_id, currency=CURRENCY, unit_amount=amount,
                    lookup_key=key, nickname=nickname,
                )
                note(f"  + {key}: creado con {amount / 100:.2f} €")
    return out


# Freno del auto-alta: como mucho un intento cada 10 min por proceso (si Stripe
# rechaza la creación, no hay que insistir en cada visita a /planes).
_ensure_state: dict = {"at": 0.0}
_ENSURE_RETRY_S = 600


def _price_by_lookup(tier: str, period: str) -> str:
    """ID del precio ACTIVO con lookup_key dqr_{tier}_{period}, con caché.

    AUTO-ALTA Y AUTO-REPRECIO: si a Stripe le faltan precios canónicos O alguno
    tiene un importe/moneda DISTINTOS de CANONICAL_AMOUNTS (p. ej. tras un
    reprecio en el código — el cron de auto-deploy NO ejecuta el script), se
    alinean aquí mismo con ensure_canonical_prices. La primera resolución de
    precios tras el deploy deja Stripe cuadrado sin pasos manuales. ⚠️ La tabla
    canónica MANDA: un importe cambiado a mano en el dashboard de Stripe se
    revierte — los precios se cambian en el código, no en Stripe.
    Best-effort: ante cualquier fallo devuelve "" (el caller decide)."""
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
        keys = [_lookup_key(t, p) for t in TIER_ORDER for p in PERIOD_ORDER]

        def _list_prices() -> dict:
            return {pr["lookup_key"]: pr
                    for pr in stripe.Price.list(lookup_keys=keys, active=True,
                                                limit=100)["data"]
                    if pr.get("lookup_key")}

        found = _list_prices()

        def _desalineado() -> bool:
            for t in TIER_ORDER:
                for p in PERIOD_ORDER:
                    pr = found.get(_lookup_key(t, p))
                    if (pr is None or pr.get("unit_amount") != CANONICAL_AMOUNTS[t][p]
                            or pr.get("currency") != CURRENCY):
                        return True
            return False

        if _desalineado() and now - _ensure_state["at"] > _ENSURE_RETRY_S:
            _ensure_state["at"] = now
            try:
                ensure_canonical_prices(stripe)
                found = _list_prices()
                # El catálogo mostrado (get_plan_prices) puede llevar importes
                # recién sustituidos: se invalida para que la próxima lectura
                # traiga los nuevos en vez de servir la caché 10 minutos.
                _prices_cache.update(at=0.0, data=None)
                _log.info("Precios de Stripe alineados con la tabla canónica (auto-alta).")
            except Exception as exc:  # noqa: BLE001 — clave sin permisos, red…
                _log.warning("Auto-alta de precios en Stripe fallida: %s", exc)
        for k in keys:
            _lookup_cache["ids"][k] = (found.get(k) or {}).get("id", "")
    except Exception as exc:  # noqa: BLE001 — sin red/clave: se cae a los .env
        _log.warning("No se pudieron resolver precios por lookup_key: %s", exc)
        return ""
    return _lookup_cache["ids"].get(key, "")


def _resolve_price_id(tier: str, period: str) -> str:
    """Precio a cobrar para tier×period, por orden de prioridad:
    1) lookup_key en Stripe (precios creados por el script — la verdad vigente),
    2) .env con nombre nuevo (reserva si Stripe no responde o no hay lookup),
    3) .env con nombre antiguo (START/PRO), último recurso.
    El lookup va PRIMERO a propósito: el .env del servidor arrastra
    STRIPE_PRICE_FULL_* del plan Full antiguo (otro importe) y no debe pisar
    los precios nuevos."""
    by_lookup = _price_by_lookup(tier, period)
    if by_lookup:
        return by_lookup
    direct = settings.stripe_price_for(tier, period)
    if direct:
        return direct
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

    try:
        session = stripe.checkout.Session.create(
            mode=settings.stripe_mode,
            line_items=[{"price": price, "quantity": 1}],
            success_url=f"{base}/pago-ok",
            cancel_url=f"{base}/planes",
            metadata=metadata,
            client_reference_id=(str(client.id) if client else None),
            **extra,
        )
    except Exception as exc:  # noqa: BLE001 — errores del SDK de Stripe
        # Los errores de la librería (precio recién archivado por un reprecio,
        # red, rate limit…) NO heredan de nuestra StripeError: sin esto se
        # propagaban como 500 al navegador del interesado. Además, el precio
        # cacheado puede ser el recién desactivado: se vacía la caché para que
        # el SIGUIENTE clic re-resuelva y se auto-repare en segundos.
        _lookup_cache["ids"] = {}
        _log.warning("Stripe rechazó la Checkout Session (%s %s): %s", tier, period, exc)
        raise StripeError(
            "La pasarela de pago no ha respondido; prueba de nuevo en un momento."
        ) from exc
    return session.url


# ---------------------------------------------------------------- precios ----

_PERIOD_MONTHS = {"1m": 1, "3m": 3, "6m": 6}
_prices_cache: dict = {"at": 0.0, "data": None}
_PRICES_TTL_S = 600  # los precios cambian poco; 10 min de caché evita latencia


def get_plan_prices() -> dict:
    """Importes de los 9 precios (plan × duración) para la página de planes
    (total + equivalente al mes). Con caché. Primero los REALES de Stripe; una
    combinación ilegible (Stripe caído, clave ausente, precio borrado) se rellena
    con el importe CANÓNICO — /planes nunca se queda sin precios. El cobro real
    sigue siendo siempre el precio de Stripe (el auto-alta lo crea con estos
    mismos importes).

    Devuelve {"currency": "eur", "tiers": {tier: {period: {"total": €, "months": n,
    "per_month": €}}}}.
    """
    import time

    if _prices_cache["data"] is not None and time.time() - _prices_cache["at"] < _PRICES_TTL_S:
        return _prices_cache["data"]

    tiers: dict = {t: {p: None for p in _PERIOD_MONTHS} for t in _TIERS}
    currency = "eur"
    leidos_de_stripe = 0
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
                    leidos_de_stripe += 1
                except Exception as exc:  # precio borrado/ID malo: no rompe la página
                    _log.warning("Precio %s (%s %s) ilegible: %s", price_id, tier, period, exc)

    for tier in _TIERS:  # reserva canónica para lo que Stripe no haya dado
        for period, months in _PERIOD_MONTHS.items():
            if tiers[tier][period] is None:
                amount = CANONICAL_AMOUNTS[tier][period] / 100.0
                tiers[tier][period] = {
                    "total": amount,
                    "months": months,
                    "per_month": round(amount / months, 2),
                }

    data = {"currency": currency, "tiers": tiers}
    # Con Stripe configurado pero SIN un solo precio legible (fallo transitorio),
    # no se cachea: la siguiente visita reintenta leer los reales en vez de
    # servir la reserva 10 minutos.
    if not (settings.stripe_enabled and leidos_de_stripe == 0):
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


def _notify_orphan_payment(db: Session, session: dict) -> None:
    """Push al COACH: entró un pago que no se pudo asociar a ningún cliente
    (cliente borrado entre el alta y el pago, o checkout sin email). El dinero
    está cobrado: alguien tiene que enterarse y resolverlo a mano en Stripe.
    Nunca rompe el webhook."""
    try:
        from app.services import push as push_svc

        details = session.get("customer_details") or {}
        who = details.get("email") or details.get("name") or "desconocido"
        amount = (session.get("amount_total") or 0) / 100.0
        push_svc.send_to_coach(db, {
            "title": "Pago sin cliente asociado ⚠️",
            "body": (f"Stripe cobró {amount:.2f} € a {who} pero no hay ficha a la "
                     "que asociarlo. Revísalo en el panel de Stripe."),
            "count": 1,
            "url": "https://dashboard.stripe.com/payments",
            "tag": "dq-pago-huerfano",
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
        # pkgs.normalize traduce la metadata ANTIGUA ("start"→nutri, "pro"→full)
        # de Checkout Sessions creadas antes del renombrado y aún en vuelo.
        package_tier=pkgs.normalize(tier),
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
    tier = pkgs.normalize(meta.get("tier"))
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
        phone=details.get("phone"), tier=tier, period=period)
    return {"created": client.id}
