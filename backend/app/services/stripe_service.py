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

from sqlalchemy import func, or_, select
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

# --- OFERTA de captación (solo plan Full): 3 meses, 1 € + 120 € + 120 € ---
# Es una SUSCRIPCIÓN de Stripe, pero NO abierta: la oferta es un PROGRAMA
# CERRADO de 3 meses — 1 € el primer mes y 120 € el segundo y el tercero
# (total 241 €). Precio recurrente mensual de 120 € + cupón estable de un solo
# uso por suscripción que deja el primer mes en 1 €; en cuanto se cobra la
# TERCERA factura, el webhook CANCELA la suscripción (no hay cuarto cobro).
# 120 €/mes queda por debajo de Train+Nutri sueltos (69+79=148 €) — el gancho.
OFFER_PERIOD = "oferta"               # billing_period del cliente en la oferta
OFFER_TIER = "full"                   # la oferta es SOLO del plan completo
OFFER_MONTHLY_CENTS = 12000           # 120 €/mes el segundo y el tercer mes
OFFER_FIRST_MONTH_CENTS = 100         # 1 € el primer mes
OFFER_CHARGES = 3                     # nº de facturas (1 € + 120 + 120): a la 3ª, se cancela
OFFER_LOOKUP = "dqr_full_oferta"      # lookup_key del precio RECURRENTE
OFFER_COUPON_ID = "dqr_oferta_primer_mes"  # id estable del cupón (duration=once)

# --- OFERTA EN 2 PAGOS (la MISMA oferta de 3 meses, otra forma de pagarla):
# 120,50 € hoy y 120,50 € al mes — total 241 €, exactamente lo mismo que
# 1 + 120 + 120. Es una suscripción mensual de 120,50 € que el webhook CANCELA
# en Stripe en cuanto se cobra la SEGUNDA factura (no hay tercer cobro: el
# programa queda pagado). El job diario reintenta la cancelación por si el
# webhook se perdiera — mismo mecanismo que la forma en 3 pagos.
OFFER2_PERIOD = "oferta2"             # billing_period del cliente en 2 pagos
OFFER2_MONTHLY_CENTS = 12050          # 120,50 € cada uno de los dos pagos
OFFER2_CHARGES = 2                    # nº de cobros: al segundo, se cancela
OFFER2_LOOKUP = "dqr_full_oferta2"    # = _lookup_key("full", "oferta2")
# Las DOS formas de pagar la misma oferta (ambas solo del plan Full) y cuántas
# facturas completan el programa en cada una.
OFFER_PERIODS = (OFFER_PERIOD, OFFER2_PERIOD)
OFFER_CHARGES_BY_PERIOD = {OFFER_PERIOD: OFFER_CHARGES, OFFER2_PERIOD: OFFER2_CHARGES}


class StripeError(RuntimeError):
    """Error recuperable de Stripe (config ausente, plan inválido, firma mala)."""


# Stripe admite un MÁXIMO de 10 `lookup_keys` por llamada a Price.list. Con los
# 9 planes + las DOS formas de pagar la oferta son ONCE: la llamada entera
# fallaba ("You cannot specify more than 10 lookup_keys"), la resolución de
# precios por lookup se caía y los enlaces de la OFERTA acababan redirigiendo a
# /planes en vez de abrir Stripe. Se pide por tandas y se juntan los resultados.
_LOOKUP_BATCH = 10


def _prices_by_lookup(stripe, keys: list[str]) -> dict:
    """{lookup_key: precio} pidiéndolos en tandas de 10 como manda la API."""
    found: dict = {}
    for i in range(0, len(keys), _LOOKUP_BATCH):
        tanda = keys[i:i + _LOOKUP_BATCH]
        for pr in stripe.Price.list(lookup_keys=tanda, active=True,
                                    limit=100)["data"]:
            if pr.get("lookup_key"):
                found[pr["lookup_key"]] = pr
    return found


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
    keys = ([_lookup_key(t, p) for t in TIER_ORDER for p in PERIOD_ORDER]
            + [OFFER_LOOKUP, OFFER2_LOOKUP])
    existing = _prices_by_lookup(stripe, keys)

    for tier in TIER_ORDER:
        product_id = products.get(tier)
        if not product_id:
            prod = stripe.Product.create(
                name=PRODUCT_NAMES[tier], metadata={"dqr_tier": tier},
                description=f"Asesoría {PRODUCT_NAMES[tier]} — pago por período",
            )
            product_id = prod["id"]
            products[tier] = product_id  # la oferta (más abajo) reusa el de Full
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
                # transfer_lookup_key TAMBIÉN al crear: un precio ARCHIVADO a
                # mano conserva su lookup_key y sin transferencia Stripe
                # rechaza el alta ("lookup key already in use") en bucle.
                stripe.Price.create(
                    product=product_id, currency=CURRENCY, unit_amount=amount,
                    lookup_key=key, transfer_lookup_key=True, nickname=nickname,
                )
                note(f"  + {key}: creado con {amount / 100:.2f} €")

    # ---- OFERTA: precio RECURRENTE mensual (suscripción) + cupón 1er mes 1 € ----
    # La variante en 2 PAGOS es otro precio recurrente (120,50 €/mes) con su
    # propio lookup_key: mismo tratamiento idempotente.
    for lookup, cents, nick in (
        (OFFER_LOOKUP, OFFER_MONTHLY_CENTS, "DQR Full · oferta (120 €/mes)"),
        (OFFER2_LOOKUP, OFFER2_MONTHLY_CENTS, "DQR Full · oferta 2 pagos (120,50 € ×2)"),
    ):
        pr = existing.get(lookup)
        ok = (pr is not None and pr.get("unit_amount") == cents
              and pr.get("currency") == CURRENCY
              and (pr.get("recurring") or {}).get("interval") == "month")
        if not ok:
            if pr is not None:
                stripe.Price.create(
                    product=pr["product"], currency=CURRENCY,
                    unit_amount=cents,
                    recurring={"interval": "month"},
                    lookup_key=lookup, transfer_lookup_key=True,
                    nickname=nick,
                )
                stripe.Price.modify(pr["id"], active=False)
                note(f"  ~ {lookup}: reprecio a {cents / 100:.2f} €/mes "
                     "(precio nuevo, el antiguo desactivado)")
            else:
                stripe.Price.create(
                    product=products["full"], currency=CURRENCY,
                    unit_amount=cents,
                    recurring={"interval": "month"},
                    lookup_key=lookup, transfer_lookup_key=True,
                    nickname=nick,
                )
                note(f"  + {lookup}: creado (suscripción {cents / 100:.2f} €/mes)")
        else:
            note(f"  = {lookup}: ya existe ({cents / 100:.2f} €/mes, sin cambios)")

    # Cupón del primer mes a 1 €: id ESTABLE, un solo cobro con descuento
    # (duration=once). Un cupón no se puede editar: si existe con otro importe,
    # se borra y se recrea (los clientes que ya lo redimieron no se tocan).
    descuento = OFFER_MONTHLY_CENTS - OFFER_FIRST_MONTH_CENTS
    cupon = None
    try:
        cupon = stripe.Coupon.retrieve(OFFER_COUPON_ID)
    except Exception:  # noqa: BLE001 — no existe (o borrado): se crea abajo
        cupon = None
    cupon_ok = (cupon is not None and cupon.get("amount_off") == descuento
                and cupon.get("currency") == CURRENCY
                and cupon.get("duration") == "once" and cupon.get("valid", True))
    if not cupon_ok:
        if cupon is not None:
            try:
                stripe.Coupon.delete(OFFER_COUPON_ID)
            except Exception:  # noqa: BLE001
                pass
        stripe.Coupon.create(
            id=OFFER_COUPON_ID, amount_off=descuento, currency=CURRENCY,
            duration="once", name="Oferta: primer mes 1 €",
        )
        note(f"  + cupón {OFFER_COUPON_ID}: primer mes a "
             f"{OFFER_FIRST_MONTH_CENTS / 100:.2f} € (−{descuento / 100:.2f} €)")
    else:
        note(f"  = cupón {OFFER_COUPON_ID}: ya existe (sin cambios)")

    # ---- Webhook: los eventos de la suscripción deben estar SUSCRITOS ----
    # La guía original decía escuchar SOLO checkout.session.completed; sin
    # invoice.paid/payment_failed y customer.subscription.deleted, todo el
    # seguimiento de renovaciones sería código muerto. Se añaden por API al
    # endpoint del dashboard (best-effort: sin permisos, aviso y a mano).
    try:
        # `charge.refunded` entró con el LIBRO DE CAJA (tabla payments): sin él
        # una devolución no restaría de los ingresos y el feed de pagos del
        # panel enseñaría un saldo falso.
        # `checkout.session.async_payment_succeeded`: los métodos de pago
        # diferidos (SEPA, transferencia) llegan con `completed` en estado
        # "unpaid" (se ignora) y el OK real viene después en este evento —
        # sin escucharlo, ese cobro no marcaba nunca al cliente como pagado.
        necesarios = {"checkout.session.completed",
                      "checkout.session.async_payment_succeeded", "invoice.paid",
                      "invoice.payment_failed", "customer.subscription.deleted",
                      "charge.refunded",
                      # Contracargo: el dinero se va y hay PLAZO para responder.
                      "charge.dispute.created", "charge.dispute.closed"}
        for ep in stripe.WebhookEndpoint.list(limit=100)["data"]:
            if "/api/stripe/webhook" not in (ep.get("url") or ""):
                continue
            actuales = set(ep.get("enabled_events") or [])
            if "*" in actuales or necesarios <= actuales:
                note("  = webhook: ya escucha los eventos de la suscripción")
            else:
                stripe.WebhookEndpoint.modify(
                    ep["id"], enabled_events=sorted(actuales | necesarios))
                note("  ~ webhook: añadidos invoice.paid / invoice.payment_failed / "
                     "customer.subscription.deleted / charge.refunded / "
                     "charge.dispute.* / checkout.session.async_payment_succeeded")
    except Exception as exc:  # noqa: BLE001 — clave restringida, sin red…
        note(f"  ! webhook sin comprobar ({exc}): añade a mano invoice.paid, "
             "invoice.payment_failed, customer.subscription.deleted, "
             "charge.refunded, charge.dispute.created, charge.dispute.closed y "
             "checkout.session.async_payment_succeeded en el dashboard")
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
        keys = ([_lookup_key(t, p) for t in TIER_ORDER for p in PERIOD_ORDER]
                + [OFFER_LOOKUP, OFFER2_LOOKUP])

        def _list_prices() -> dict:
            return _prices_by_lookup(stripe, keys)

        found = _list_prices()

        def _desalineado() -> bool:
            for t in TIER_ORDER:
                for p in PERIOD_ORDER:
                    pr = found.get(_lookup_key(t, p))
                    if (pr is None or pr.get("unit_amount") != CANONICAL_AMOUNTS[t][p]
                            or pr.get("currency") != CURRENCY):
                        return True
            # Los precios recurrentes de la oferta (las dos formas de pago).
            for lk, cents in ((OFFER_LOOKUP, OFFER_MONTHLY_CENTS),
                              (OFFER2_LOOKUP, OFFER2_MONTHLY_CENTS)):
                of = found.get(lk)
                if (of is None or of.get("unit_amount") != cents
                        or of.get("currency") != CURRENCY
                        or (of.get("recurring") or {}).get("interval") != "month"):
                    return True
            # El CUPÓN del primer mes también es reparable: borrado a mano en el
            # dashboard dejaría la promo muerta en silencio (cada checkout
            # fallaría con "No such coupon") y los precios seguirían alineados.
            try:
                cup = stripe.Coupon.retrieve(OFFER_COUPON_ID)
                return not (cup.get("amount_off") == OFFER_MONTHLY_CENTS - OFFER_FIRST_MONTH_CENTS
                            and cup.get("currency") == CURRENCY
                            and cup.get("duration") == "once"
                            and cup.get("valid", True))
            except Exception:  # noqa: BLE001 — no existe: hay que recrearlo
                return True

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
        # Solo se cachea lo ENCONTRADO. Cachear el vacío dejaba todos los
        # enlaces muertos durante los 10 minutos del TTL por un fallo puntual
        # de Stripe (y la oferta no tiene reserva en el .env que la salve).
        for k in keys:
            pid = (found.get(k) or {}).get("id", "")
            if pid:
                _lookup_cache["ids"][k] = pid
            else:
                _lookup_cache["ids"].pop(k, None)
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


def _es_primera_compra(client: "Client | None") -> bool:
    """¿Este pago es el de ARRANQUE de la asesoría, o una renovación?

    La página de "¡Pago recibido!" prometía a todo el mundo el cuestionario
    inicial "ya en tu correo". A quien RENUEVA no se le manda ninguno —ya hizo
    su anamnesis hace meses—, así que se quedaba esperando (y revisando el spam)
    un email que no iba a llegar nunca. Sin ficha (registro personal) sí es un
    alta; con ficha, lo es solo mientras siga en onboarding."""
    return client is None or client.status == "onboarding"


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
    es_oferta = period in OFFER_PERIODS
    if es_oferta and tier != OFFER_TIER:
        raise StripeError("La oferta es solo del plan Full.")
    if not es_oferta and period not in _PERIODS:
        raise StripeError(f"Duración desconocida: {period}")
    price = _resolve_price_id(tier, period)
    if not price:
        raise StripeError(
            f"Falta el precio de Stripe del plan {tier} {period}: ejecuta "
            "scripts/setup_stripe_prices.py (o pon "
            f"STRIPE_PRICE_{tier.upper()}_{period.upper()} en el .env).")

    base = settings.public_base_url.rstrip("/")
    metadata = {"tier": tier, "billing_period": period}
    extra: dict = {}
    if client is not None:
        metadata["client_id"] = str(client.id)
        if client.email:
            extra["customer_email"] = client.email
    else:
        # Registro personal: pedimos teléfono para poder contactar al cliente.
        extra["phone_number_collection"] = {"enabled": True}

    if es_oferta:
        # SUSCRIPCIÓN mensual de un PROGRAMA CERRADO de 3 meses. En la forma
        # de 3 pagos, el primer cobro queda a 1 € (cupón de un solo uso por
        # suscripción) y el webhook cancela la suscripción a la TERCERA
        # factura (1 € + 120 + 120). En la forma EN 2 PAGOS no hay cupón: dos
        # cobros de 120,50 € y cancelación al segundo. invoice.paid/
        # payment_failed mantienen el estado del cliente al día; la metadata
        # viaja también en la suscripción para mapear las facturas al cliente.
        if period == OFFER_PERIOD:
            extra["discounts"] = [{"coupon": OFFER_COUPON_ID}]
        extra["subscription_data"] = {"metadata": dict(metadata)}
        # El checkout de Stripe enseña "120,00 € al mes" (es una suscripción):
        # sin este texto, el cliente no sabría que el cobro SE DETIENE SOLO.
        mensaje = ("Oferta de 3 meses: 1 € hoy y 120 € el 2º y el 3er mes "
                   "(total 241 €). Después no se te cobra nada más: la "
                   "suscripción se detiene sola."
                   if period == OFFER_PERIOD else
                   "Oferta de 3 meses en 2 pagos: 120,50 € hoy y 120,50 € en "
                   "un mes (total 241 €). Después no se te cobra nada más: la "
                   "suscripción se detiene sola.")
        extra["custom_text"] = {"submit": {"message": mensaje}}

    # El MODO se valida: un STRIPE_MODE mal escrito en el .env tumbaba TODOS
    # los enlaces de plan (Stripe rechaza la sesión) sin decir dónde estaba el
    # fallo. Ante un valor raro, el de siempre: pago único.
    modo = settings.stripe_mode if settings.stripe_mode in ("payment", "subscription") else "payment"
    try:
        # _stripe() dentro del try: un fallo aquí (clave ilegible, SDK) salía
        # como 500 al navegador del interesado en vez de traducirse.
        stripe = _stripe()
        session = stripe.checkout.Session.create(
            mode="subscription" if es_oferta else modo,
            line_items=[{"price": price, "quantity": 1}],
            success_url=f"{base}/pago-ok" + ("" if _es_primera_compra(client) else "?r=1"),
            cancel_url=f"{base}/planes",
            metadata=metadata,
            client_reference_id=(str(client.id) if client else None),
            **extra,
        )
    except Exception as exc:  # noqa: BLE001 — errores del SDK de Stripe
        # Los errores de la librería (precio archivado, cupón borrado a mano,
        # red, rate limit…) NO heredan de nuestra StripeError: sin esto se
        # propagaban como 500 al navegador del interesado. Se vacía la caché de
        # precios Y el freno del auto-alta para que el SIGUIENTE clic
        # re-resuelva y repare lo que falte (precio nuevo, cupón recreado…).
        _lookup_cache["ids"] = {}
        _ensure_state["at"] = 0.0
        _log.warning("Stripe rechazó la Checkout Session (%s %s): %s", tier, period, exc)
        raise StripeError(
            "La pasarela de pago no ha respondido; prueba de nuevo en un momento."
        ) from exc
    return session.url


def open_invoice_url(client: Client) -> str | None:
    """URL de la factura ABIERTA de la suscripción de la oferta del cliente
    (página alojada por Stripe: actualiza la tarjeta y paga lo pendiente), o
    None si no hay ninguna. La usa el enlace de pago estable para NO crear una
    SEGUNDA suscripción con otro primer mes a 1 € tras un impago. Best-effort."""
    if not (client.billing_period in OFFER_PERIODS and client.stripe_subscription_id
            and settings.stripe_enabled):
        return None
    try:
        stripe = _stripe()
        invs = stripe.Invoice.list(subscription=client.stripe_subscription_id,
                                   status="open", limit=1)["data"]
        return invs[0].get("hosted_invoice_url") if invs else None
    except Exception as exc:  # noqa: BLE001
        # OJO: "no se pudo consultar" NO es "no debe nada". Devolviendo None se
        # mandaba a la página de "¡Pago recibido!" a un cliente que quizá tiene
        # una factura pendiente. El caller decide qué enseñar.
        _log.warning("No se pudo consultar la factura del cliente %s: %s", client.id, exc)
        raise StripeError(
            "No se ha podido consultar el estado de tu suscripción.") from exc


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

def _euros(cents: int | None) -> str:
    """Céntimos de Stripe → "129,00 €" (formato español, para el push)."""
    return f"{(cents or 0) / 100:.2f}".replace(".", ",") + " €"


def _notify_coach_payment(db: Session, client: Client, *, new_client: bool,
                          amount_cents: int | None = None) -> None:
    """Push inmediato al COACH: entró un pago (o un alta nueva con pago). Un
    ingreso no puede esperar al resumen de cada 3 h. Nunca rompe el webhook.

    Lleva el IMPORTE en el título, como el aviso de un banco, y abre el feed de
    pagos (/pagos). La `tag` es única por pago: con una tag compartida, dos
    cobros seguidos se veían como UNA sola notificación en el móvil (el segundo
    sustituía al primero)."""
    try:
        from app.services import push as push_svc
        from app.services.payments import unseen_count

        first = ((client.full_name or "").split() or ["Un cliente"])[0]
        base = settings.public_base_url.rstrip("/")
        importe = f"+{_euros(amount_cents)} · " if amount_cents else ""
        push_svc.send_to_coach(db, {
            "title": f"💰 {importe}{'Nuevo cliente pagado 🎉' if new_client else 'Pago recibido'}",
            "body": (f"{first} se ha registrado y pagado el plan {client.package_tier}."
                     if new_client else
                     f"{first} ha completado el pago de su plan {client.package_tier}."),
            # El badge del icono cuenta los pagos SIN LEER: al abrir el feed se
            # queda a cero, como en la app del banco.
            "count": max(1, unseen_count(db)),
            "url": f"{base}/pagos",
            "tag": f"dq-pago-{client.id}-{int(datetime.now(timezone.utc).timestamp())}",
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
            "title": "💰⚠️ Pago sin cliente asociado",
            "body": (f"Stripe cobró {amount:.2f} € a {who} pero no hay ficha a la "
                     "que asociarlo. Revísalo en el panel de Stripe."),
            "count": 1,
            "url": "https://dashboard.stripe.com/payments",
            "tag": "dq-pago-huerfano",
        })
    except Exception:  # noqa: BLE001
        pass


def _mark_paid(db: Session, client: Client, period: str | None = None, *,
               movimiento_nuevo: bool = False, amount_cents: int | None = None,
               pagado_en: datetime | None = None, tier: str | None = None) -> None:
    """Marca el cobro en la ficha del cliente.

    `movimiento_nuevo` lo decide el LIBRO DE CAJA (services/payments): es True
    cuando este cobro concreto de Stripe no estaba anotado. Sin él, un cliente
    que YA estaba pagado y RENUEVA (segundo pago único) no dejaba ningún rastro
    —ni traza, ni aviso, ni `paid_at` fresco— y la alerta de renovación seguía
    contando desde el primer pago para siempre (auditoría del libro de caja).
    Con él, una reentrega del MISMO pago sigue sin duplicar avisos."""
    # La duración que el cliente pagó de verdad manda sobre la de la ficha.
    if (period in _PERIODS or period in OFFER_PERIODS) and client.billing_period != period:
        client.billing_period = period
    # Y el PLAN pagado también: un cliente existente que compra OTRA tarifa por
    # el enlace del kit de ventas quedaba con la tarifa antigua en la ficha (y
    # el siguiente cobro/documento salía del plan equivocado — auditoría).
    if tier and tier in pkgs.TIERS and client.package_tier != tier:
        log_event(db, "client", client.id, "tier_changed_by_payment",
                  {"antes": client.package_tier, "ahora": tier})
        client.package_tier = tier
    transicion = client.payment_status != "paid"
    client.payment_status = "paid"
    # Fecha del último cobro: la renovación reinicia el contador de la alerta.
    # Se compara con la que ya tiene la ficha en vez de fiarse de "¿he anotado
    # yo esta fila?": si la sincronización con Stripe anotó antes el movimiento,
    # la reentrega del webhook llegaba con `movimiento_nuevo=False` y `paid_at`
    # se quedaba en el pago ANTERIOR (alerta de renovación eterna).
    cobrado_en = pagado_en or datetime.now(timezone.utc)
    if client.paid_at is None or cobrado_en > client.paid_at:
        client.paid_at = cobrado_en
    if transicion or movimiento_nuevo:
        log_event(db, "client", client.id, "payment_received",
                  {"tier": client.package_tier, "billing_period": client.billing_period,
                   "renovacion": not transicion})
        _notify_coach_payment(db, client, new_client=False, amount_cents=amount_cents)


def _anotar_checkout(db: Session, session: dict, client: Client | None, *,
                     event_id: str | None = None) -> bool:
    """Anota en el LIBRO DE CAJA (tabla payments) el cobro de una Checkout
    Session, con el importe, la moneda y la fecha REALES de Stripe.

    Devuelve True si el movimiento es NUEVO: esa es la señal que distingue un
    pago de verdad de una reentrega del mismo webhook, y la que permite avisar
    de una RENOVACIÓN de un cliente que ya constaba como pagado.

    Las sesiones en modo SUSCRIPCIÓN (la oferta) NO se anotan aquí: ese dinero
    entra como factura (`invoice.paid`) y anotar las dos cosas duplicaría el
    ingreso del primer mes en los totales."""
    if session.get("mode") == "subscription":
        return False
    from app.services import payments as pay_svc

    meta = session.get("metadata") or {}
    detalles = session.get("customer_details") or {}
    tier = (pkgs.normalize(meta.get("tier")) if meta.get("tier")
            else (client.package_tier if client else None))
    period = meta.get("billing_period") or (client.billing_period if client else None)
    pago = pay_svc.record_payment(
        db, object_id=session.get("id") or "", kind="checkout", status="paid",
        amount_cents=session.get("amount_total") or 0,
        currency=session.get("currency") or "eur",
        livemode=bool(session.get("livemode", True)),
        client=client, customer_name=detalles.get("name"),
        customer_email=detalles.get("email"), tier=tier, billing_period=period,
        description=pay_svc.describe(tier, period),
        paid_at=pay_svc.ts_to_dt(session.get("created")), event_id=event_id,
        payment_intent=_pi_of(session),
    )
    # La comisión SOLO se consulta para movimientos nuevos (una reentrega del
    # webhook no vuelve a llamar a Stripe) y jamás bloquea el cobro.
    if pago is not None and pago.fee_cents is None:
        pago.fee_cents = _fee_de_cobro(payment_intent=pago.payment_intent)
    return pago is not None


def _pi_of(objeto: dict) -> str | None:
    """El pi_… de una Checkout Session o factura (string o dict según versión)."""
    v = (objeto or {}).get("payment_intent")
    if isinstance(v, dict):
        v = v.get("id")
    return v or None


def _fee_de_cobro(*, payment_intent: str | None = None,
                  charge_id: str | None = None) -> int | None:
    """Comisión (céntimos) que Stripe se quedó de un cobro. UNA llamada extra a
    la API por cobro NUEVO; best-effort: cualquier fallo → None. El fee es
    informativo (para el neto del panel) y nunca puede tumbar el webhook."""
    try:
        stripe = _stripe()
        ch = None
        if charge_id:
            ch = stripe.Charge.retrieve(charge_id, expand=["balance_transaction"])
        elif payment_intent:
            pi = stripe.PaymentIntent.retrieve(
                payment_intent, expand=["latest_charge.balance_transaction"])
            ch = pi.get("latest_charge")
        txn = (ch or {}).get("balance_transaction")
        if isinstance(txn, dict) and txn.get("fee") is not None:
            return int(txn["fee"])
    except Exception:  # noqa: BLE001 — informativo, jamás rompe el cobro
        pass
    return None


def _create_selfserve_client(db: Session, *, name: str, email: str,
                             phone: str | None, tier: str, period: str | None,
                             amount_cents: int | None = None) -> Client:
    """Crea el perfil de un cliente que se ha registrado y pagado por su cuenta."""
    client = Client(
        full_name=(name or email.split("@")[0]).strip(),
        email=email,
        phone=phone,
        # pkgs.normalize traduce la metadata ANTIGUA ("start"→nutri, "pro"→full)
        # de Checkout Sessions creadas antes del renombrado y aún en vuelo.
        package_tier=pkgs.normalize(tier),
        billing_period=period if (period in _PERIODS or period in OFFER_PERIODS) else "1m",
        status="onboarding",
        portal_token="pendiente",
        payment_status="paid",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(client)
    db.flush()
    client.portal_token = new_portal_token(client.id)
    # La primera factura de la oferta se paga ANTES de completarse el checkout,
    # así que su movimiento pudo anotarse sin ficha (aún no existía): ahora que
    # el cliente existe, se le adopta. Si no, quedaba un "pago sin ficha
    # asociada" eterno y el borrado RGPD no llegaba a esa fila.
    try:
        from app.services.payments import adopt_orphans

        adopt_orphans(db, client)
    except Exception:  # noqa: BLE001 — la contabilidad nunca rompe el alta
        pass
    log_event(db, "client", client.id, "client_created",
              {"by": "stripe", "tier": client.package_tier,
               "billing_period": client.billing_period})
    log_event(db, "client", client.id, "payment_received",
              {"tier": client.package_tier, "billing_period": client.billing_period})
    _notify_coach_payment(db, client, new_client=True, amount_cents=amount_cents)
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


def _tag_subscription(db: Session, session: dict, client: Client) -> None:
    """Ancla la SUSCRIPCIÓN de la oferta al cliente: graba el client_id en la
    metadata de la suscripción (las facturas de renovación llegan sin la
    metadata de la sesión) Y el sub_… en la ficha (para no crear una segunda
    suscripción al reabrir el enlace de pago y para mapear cancelaciones).
    Best-effort: nunca rompe el webhook."""
    sub_id = session.get("subscription")
    if not sub_id:
        return
    try:
        client.stripe_subscription_id = sub_id
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    try:
        stripe = _stripe()
        stripe.Subscription.modify(sub_id, metadata={
            "client_id": str(client.id),
            "tier": client.package_tier or "",
            "billing_period": client.billing_period or "",
        })
    except Exception as exc:  # noqa: BLE001
        _log.warning("No se pudo etiquetar la suscripción %s: %s", sub_id, exc)


def _notify_coach_payment_failed(db: Session, client: Client) -> None:
    """Push inmediato al COACH: la renovación mensual de un cliente NO se pudo
    cobrar. Stripe reintentará solo; mientras, el cliente queda 'pendiente'
    (badge rojo + filtro de pagos). Nunca rompe el webhook."""
    try:
        from app.services import push as push_svc

        first = ((client.full_name or "").split() or ["Un cliente"])[0]
        base = settings.public_base_url.rstrip("/")
        push_svc.send_to_coach(db, {
            "title": "💰⚠️ Cobro fallido",
            "body": (f"La renovación de {first} no se pudo cobrar. Stripe "
                     "reintentará; si no entra, escríbele o revisa Stripe."),
            "count": 1,
            "url": f"{base}/clientes/{client.id}",
            # Por cliente: dos impagos el mismo día no pueden verse como uno.
            "tag": f"dq-pago-fallido-{client.id}",
        })
    except Exception:  # noqa: BLE001
        pass


def _invoice_subscription_bits(invoice: dict) -> tuple[str | None, dict]:
    """(sub_id, metadata) de la factura, tolerante con las DOS formas del
    payload: la clásica (invoice.subscription / invoice.subscription_details) y
    la de las versiones de API 2025-03-31+ (invoice.parent.subscription_details)
    — la forma la decide la versión anclada al ENDPOINT del webhook, no el SDK."""
    parent_details = ((invoice.get("parent") or {}).get("subscription_details") or {})
    details = invoice.get("subscription_details") or parent_details
    meta = details.get("metadata") or {}
    sub = invoice.get("subscription") or parent_details.get("subscription")
    sub_id = sub.get("id") if isinstance(sub, dict) else sub
    return sub_id, meta


def _invoice_es_de_la_oferta(invoice: dict) -> bool:
    """¿La factura pertenece a NUESTRA oferta (en cualquiera de sus dos formas
    de pago)? Mira el lookup_key del precio de sus líneas (dqr_full_oferta /
    dqr_full_oferta2). Sin esto, una cuenta de Stripe con OTROS productos
    (facturas manuales, suscripciones antiguas…) contaminaría el estado de
    pago de clientes homónimos vía la reserva por email."""
    for line in ((invoice.get("lines") or {}).get("data") or []):
        price = line.get("price") or {}
        if price.get("lookup_key") in (OFFER_LOOKUP, OFFER2_LOOKUP):
            return True
        # Forma 2025-03-31+: la línea lleva pricing.price_details, sin
        # lookup_key. Reserva: metadata de la propia línea/suscripción.
        if (line.get("metadata") or {}).get("billing_period") in OFFER_PERIODS:
            return True
    _sub, meta = _invoice_subscription_bits(invoice)
    return meta.get("billing_period") in OFFER_PERIODS or bool(meta.get("client_id"))


def periodo_de_factura(invoice: dict, client: Client | None = None) -> str:
    """¿A qué FORMA de la oferta pertenece esta factura: "oferta" (1 € →
    120 €/mes) u "oferta2" (2 pagos de 120,50 €)? Lookup del precio primero,
    metadata después y, como reserva, la ficha del cliente."""
    for line in ((invoice.get("lines") or {}).get("data") or []):
        if (line.get("price") or {}).get("lookup_key") == OFFER2_LOOKUP:
            return OFFER2_PERIOD
        if (line.get("price") or {}).get("lookup_key") == OFFER_LOOKUP:
            return OFFER_PERIOD
        if (line.get("metadata") or {}).get("billing_period") in OFFER_PERIODS:
            return (line.get("metadata") or {})["billing_period"]
    _sub, meta = _invoice_subscription_bits(invoice)
    if meta.get("billing_period") in OFFER_PERIODS:
        return meta["billing_period"]
    if client is not None and client.billing_period in OFFER_PERIODS:
        return client.billing_period
    return OFFER_PERIOD


def _client_from_invoice(db: Session, invoice: dict) -> Client | None:
    """Cliente al que pertenece una factura de suscripción: metadata de la
    suscripción (en cualquiera de las dos formas del payload), metadata de las
    líneas, la API y, como último recurso, el email de la factura — este último
    SOLO si la factura es verificablemente de la oferta (el caller lo filtra)."""
    sub_id, meta = _invoice_subscription_bits(invoice)
    cid = meta.get("client_id")
    if not cid:
        for line in ((invoice.get("lines") or {}).get("data") or []):
            cid = (line.get("metadata") or {}).get("client_id")
            if cid:
                break
    if not cid and sub_id:
        try:
            stripe = _stripe()
            sub = stripe.Subscription.retrieve(sub_id)
            cid = (sub.get("metadata") or {}).get("client_id")
        except Exception:  # noqa: BLE001
            cid = None
    if cid:
        try:
            client = db.get(Client, int(cid))
            if client is not None:
                return client
        except (TypeError, ValueError):
            pass
    # Ancla inversa: la ficha guarda el sub_… al pagar (mig. 0036).
    if sub_id:
        client = db.scalar(select(Client).where(Client.stripe_subscription_id == sub_id))
        if client is not None:
            return client
    email = (invoice.get("customer_email") or "").strip().lower()
    if email:
        return db.scalar(select(Client).where(func.lower(Client.email) == email))
    return None


def _anotar_factura(db: Session, invoice: dict, client: Client | None, *,
                    pagada: bool, event_id: str | None = None) -> bool:
    """Anota en el libro de caja el movimiento de una FACTURA de la suscripción
    (renovación mensual de la oferta): cobrada o fallida. Devuelve True si es
    nuevo. La factura fallida y la cobrada son dos movimientos distintos de la
    misma factura, así que las dos caben (el UNIQUE es objeto+estado)."""
    from app.services import payments as pay_svc

    cuando = ((invoice.get("status_transitions") or {}).get("paid_at")
              if pagada else None) or invoice.get("created")
    razon = invoice.get("billing_reason")
    periodo = periodo_de_factura(invoice, client)
    pago = pay_svc.record_payment(
        db, object_id=invoice.get("id") or "", kind="invoice",
        status="paid" if pagada else "failed",
        amount_cents=(invoice.get("amount_paid") if pagada else invoice.get("amount_due")) or 0,
        currency=invoice.get("currency") or "eur",
        livemode=bool(invoice.get("livemode", True)), client=client,
        customer_name=invoice.get("customer_name"),
        customer_email=invoice.get("customer_email"),
        tier=(client.package_tier if client else OFFER_TIER),
        billing_period=periodo,
        description=pay_svc.describe(client.package_tier if client else OFFER_TIER,
                                     periodo, kind="invoice", billing_reason=razon),
        paid_at=pay_svc.ts_to_dt(cuando), event_id=event_id,
        payment_intent=_pi_of(invoice),
        # A QUÉ suscripción pertenece: sin esto, el recuento de facturas de la
        # oferta mezclaba las de una contratación anterior con las de la nueva.
        subscription_id=_invoice_subscription_bits(invoice)[0],
    )
    if pago is not None and pagada and pago.fee_cents is None:
        cargo = invoice.get("charge")
        cargo_id = cargo.get("id") if isinstance(cargo, dict) else cargo
        pago.fee_cents = _fee_de_cobro(charge_id=cargo_id,
                                       payment_intent=pago.payment_intent)
    return pago is not None


def _pay_svc_ts(valor) -> datetime | None:
    """Marca de tiempo de Stripe → datetime (atajo del servicio de pagos)."""
    from app.services.payments import ts_to_dt

    return ts_to_dt(valor)


def _cargo_es_nuestro(db: Session, charge: dict, client: Client | None) -> bool:
    """¿Este cobro de Stripe pertenece a la asesoría? La cuenta puede tener
    otros productos (facturas manuales, talleres) y sus movimientos no deben
    entrar en el libro de caja — igual que `_invoice_es_de_la_oferta` filtra las
    facturas ajenas en el ingreso.

    Es nuestro si el pagador tiene ficha, si su factura ya está anotada, o si
    su payment_intent ya consta en el libro (robusto al borrado RGPD de la
    ficha: la pertenencia deja de depender solo del email)."""
    if client is not None:
        return True
    from app.models import Payment

    inv = charge.get("invoice")
    inv_id = inv.get("id") if isinstance(inv, dict) else inv
    if inv_id and db.scalar(
        select(Payment.id).where(Payment.stripe_object_id == inv_id).limit(1)
    ) is not None:
        return True
    pi = charge.get("payment_intent")
    pi_id = pi.get("id") if isinstance(pi, dict) else pi
    if pi_id:
        return db.scalar(
            select(Payment.id).where(Payment.payment_intent == pi_id).limit(1)
        ) is not None
    return False


def _handle_charge_refunded(db: Session, event: dict) -> dict:
    """Devolución: Stripe ha reembolsado (total o parcialmente) un cobro.

    Sin esto, un cliente reembolsado se quedaba 'pagado' para siempre y los
    ingresos del mes mentían — un saldo falso en un feed que imita al banco. Se
    anota el movimiento en negativo (resta en los totales) y se avisa al coach.
    El estado de la ficha NO se toca automáticamente: una devolución parcial no
    es una baja, y quien decide qué pasa con la asesoría es el coach."""
    from app.services import payments as pay_svc

    charge = event["data"]["object"]
    devuelto = charge.get("amount_refunded") or 0
    if devuelto <= 0:
        return {"ignored": "charge_sin_devolucion"}
    facturado = charge.get("billing_details") or {}
    email = (facturado.get("email") or charge.get("receipt_email") or "").strip().lower()
    client = db.scalar(select(Client).where(func.lower(Client.email) == email)) if email else None
    if not _cargo_es_nuestro(db, charge, client):
        # SIMETRÍA con el ingreso: un cobro ajeno de la misma cuenta de Stripe
        # (una factura manual de un taller, otro producto) no se anota como
        # ingreso — `_invoice_es_de_la_oferta` lo descarta —, así que su
        # devolución tampoco puede RESTAR. Si no, el libro enseñaría un −300 €
        # de algo que nunca sumó.
        return {"ignored": "cargo_ajeno"}
    # Una fila por REEMBOLSO: `amount_refunded` es el acumulado y Stripe avisa en
    # cada devolución (ver record_refunds_of_charge).
    nuevo = pay_svc.record_refunds_of_charge(
        db, charge, client=client, event_id=event.get("id")) > 0
    if client is not None:
        log_event(db, "client", client.id, "payment_refunded",
                  {"charge_id": charge.get("id"), "amount_eur": devuelto / 100.0})
    db.commit()
    if nuevo:
        try:
            from app.services import push as push_svc

            quien = (client.full_name if client else None) or facturado.get("name") or email or "un cobro"
            base = settings.public_base_url.rstrip("/")
            push_svc.send_to_coach(db, {
                "title": f"💸 Devolución de {_euros(devuelto)}",
                "body": f"Stripe ha reembolsado {_euros(devuelto)} a {quien}. Revisa si sigue de alta.",
                "count": 1,
                "url": f"{base}/pagos",
                "tag": f"dq-devolucion-{charge.get('id')}",
            })
        except Exception:  # noqa: BLE001 — el push nunca rompe el webhook
            pass
    return {"refunded": devuelto, "client_id": client.id if client else None}


def _handle_charge_dispute(db: Session, event: dict) -> dict:
    """CONTRACARGO: el cliente ha reclamado el cobro a su banco.

    Es lo más caro que puede pasar en la pasarela y era EL ÚNICO movimiento de
    dinero que el sistema no miraba: Stripe retiene el importe al abrirse la
    disputa (más una comisión que no se devuelve), y el coach no se enteraba de
    nada — ni en el libro, ni en el móvil. Se seguía viendo el ingreso del mes
    como si el dinero estuviera ahí, y al cliente como pagado.

    Se anota como una salida (`status="refunded"`, que es lo que RESTA de los
    totales y sale en el filtro "Devoluciones") y se avisa al momento. Si la
    disputa se GANA, Stripe manda `charge.dispute.closed` con `status=won` y se
    anota la vuelta del dinero. Como en la devolución, el estado de la ficha no
    se toca solo: quién sigue de alta lo decide el coach."""
    from app.services import payments as pay_svc

    disputa = event["data"]["object"]
    importe = disputa.get("amount") or 0
    if importe <= 0:
        return {"ignored": "disputa_sin_importe"}
    cargo = disputa.get("charge")
    cargo_id = cargo.get("id") if isinstance(cargo, dict) else cargo
    pi = disputa.get("payment_intent")
    pi_id = pi.get("id") if isinstance(pi, dict) else pi

    # ¿Es NUESTRO el cobro disputado? Misma simetría que la devolución: una
    # disputa de otro producto de la cuenta no puede restar de estos ingresos.
    from app.models import Payment

    vinculos = []
    if cargo_id:
        vinculos.append(Payment.stripe_object_id == cargo_id)
    if pi_id:
        vinculos.append(Payment.payment_intent == pi_id)
    fila = db.scalar(
        select(Payment).where(Payment.status == "paid", or_(*vinculos)).limit(1)
    ) if vinculos else None
    if fila is None:
        return {"ignored": "disputa_ajena"}
    client = db.get(Client, fila.client_id) if fila.client_id else None

    ganada = (disputa.get("status") or "") in ("won", "warning_closed")
    if ganada:
        # El dinero vuelve: se anula la salida anotada al abrirse.
        anotada = db.scalar(
            select(Payment).where(Payment.stripe_object_id == (disputa.get("id") or ""),
                                  Payment.status == "refunded").limit(1))
        if anotada is None:
            return {"ignored": "disputa_ganada_sin_anotar"}
        db.delete(anotada)
        db.commit()
        _avisa_de_la_disputa(db, client, importe, disputa, ganada=True)
        return {"dispute": "won", "client_id": client.id if client else None}

    nuevo = pay_svc.record_payment(
        db, object_id=disputa.get("id") or f"dp_{cargo_id}", kind="dispute",
        status="refunded", amount_cents=importe,
        currency=disputa.get("currency") or fila.currency or "eur",
        livemode=bool(disputa.get("livemode", True)), client=client,
        customer_name=fila.customer_name, customer_email=fila.customer_email,
        description="Contracargo (reclamación al banco)",
        paid_at=pay_svc.ts_to_dt(disputa.get("created") or event.get("created")),
        event_id=event.get("id"), payment_intent=pi_id,
        seen=False,   # jamás "visto": es dinero saliendo por una reclamación
    ) is not None
    if client is not None:
        log_event(db, "client", client.id, "payment_disputed",
                  {"dispute_id": disputa.get("id"), "amount_eur": importe / 100.0})
    db.commit()
    if nuevo:
        _avisa_de_la_disputa(db, client, importe, disputa, ganada=False)
    return {"dispute": disputa.get("status"), "client_id": client.id if client else None}


def _avisa_de_la_disputa(db: Session, client: Client | None, importe: int,
                         disputa: dict, *, ganada: bool) -> None:
    """Push al coach. Una disputa tiene PLAZO para responder con pruebas: si se
    entera tarde, la pierde por incomparecencia."""
    try:
        from app.services import push as push_svc

        quien = (client.full_name if client else None) or "un cliente"
        base = settings.public_base_url.rstrip("/")
        if ganada:
            titulo = f"💰 Contracargo ganado: {_euros(importe)}"
            cuerpo = f"El banco te ha dado la razón con {quien}: el dinero vuelve."
        else:
            titulo = f"💸⚠️ Contracargo de {_euros(importe)}"
            cuerpo = (f"{quien} ha reclamado el cobro a su banco. Stripe retiene "
                      "el importe y hay PLAZO para responder con pruebas: "
                      "entra en Stripe cuanto antes.")
        push_svc.send_to_coach(db, {
            "title": titulo, "body": cuerpo, "count": 1,
            "url": f"{base}/pagos",
            "tag": f"dq-disputa-{disputa.get('id')}",
        })
    except Exception:  # noqa: BLE001 — el push nunca rompe el webhook
        pass


def pagos_oferta_cobrados(db: Session, client: Client, periodo: str,
                          sub_id: str | None = None) -> int:
    """Nº de FACTURAS COBRADAS de la oferta (en la forma de pago `periodo`)
    que constan en el libro de caja para ESTA contratación. Con ≥ las que marca
    OFFER_CHARGES_BY_PERIOD el programa está pagado entero: la suscripción
    debe cancelarse y su baja no es un impago. En la forma de 3 pagos la
    factura del 1 € también cuenta (es la primera de las tres).

    Acotado a la suscripción en curso. Contando TODAS las del cliente, uno que
    vuelve y contrata la oferta por segunda vez arrastraba las tres del
    programa anterior: al pagar su primera factura de 1 € la cuenta daba
    cuatro, el programa se daba por cobrado entero y la suscripción se
    cancelaba — tres meses de asesoría por un euro. Los movimientos anteriores
    a la mig. 0042 no llevan `subscription_id`: para ellos se mantiene el
    criterio de antes (son, justamente, los de la contratación vieja)."""
    from app.models import Payment

    sub_id = sub_id or client.stripe_subscription_id
    condiciones = [
        Payment.client_id == client.id, Payment.kind == "invoice",
        Payment.status == "paid", Payment.billing_period == periodo,
    ]
    if sub_id:
        # Sin suscripción en la ficha no hay nada que distinguir y vale el
        # recuento de siempre. La mig. 0042 rellenó el sello de las facturas
        # de las suscripciones EN CURSO, así que una contratación a medio
        # camino en el momento del despliegue sigue contando entera.
        condiciones.append(Payment.subscription_id == sub_id)
    return int(db.scalar(
        select(func.count(Payment.id)).where(*condiciones)
    ) or 0)


def cancelar_suscripcion(sub_id: str | None) -> tuple[bool, str]:
    """Cancela una suscripción EN STRIPE. Devuelve (cancelada, detalle).

    Pensada para la baja del cliente (RGPD): sin esto, Stripe le seguía
    cobrando todos los meses a alguien que ya no existe en el sistema, el
    cobro entraba como huérfano y el coach se enteraba por la reclamación.
    Una suscripción que ya estaba cancelada (o que no existe) cuenta como
    cancelada: si no, la baja quedaría bloqueada para siempre.
    """
    if not sub_id:
        return True, "sin suscripción"
    try:
        stripe = _stripe()
        cancel = getattr(stripe.Subscription, "cancel", None) or stripe.Subscription.delete
        cancel(sub_id)
        return True, "cancelada"
    except Exception as exc:  # noqa: BLE001 — se traduce a un mensaje para el coach
        texto = str(exc).lower()
        if ("no such subscription" in texto or "resource_missing" in texto
                or "already canceled" in texto or "already been canceled" in texto):
            return True, "ya estaba cancelada"
        return False, str(exc)[:200]


def _olvida_la_suscripcion(client: Client, sub_id: str) -> None:
    """Quita de la ficha la suscripción que acaba de cancelarse.

    `renewals.renewal_window` devuelve None mientras la ficha tenga una
    suscripción: "se cobra sola, no hay nada que avisar". El corte de la oferta
    la cancelaba EN STRIPE y dejaba el id puesto, así que ese cliente no volvía
    a entrar NUNCA en la ventana de renovación: ni email al cliente, ni alerta
    `renewal_due` al coach, ni reapertura del enlace de pago. El programa
    terminaba y nadie se enteraba — silencioso y en dinero.

    Hasta ahora solo lo limpiaba el webhook `customer.subscription.deleted`; si
    ese evento se perdía (o el corte venía del backstop diario), no lo limpiaba
    nadie."""
    if client.stripe_subscription_id == sub_id:
        client.stripe_subscription_id = None


def detener_suscripcion_oferta(db: Session, client: Client, sub_id: str | None,
                               *, motivo: str, periodo: str = OFFER2_PERIOD) -> bool:
    """Cancela EN STRIPE la suscripción de la oferta: el último cobro del
    programa ya entró (el 2º de 120,50 € o el 3º de la forma 1 € + 120 + 120)
    y no puede haber otro. Devuelve True si quedó cancelada. Si Stripe falla,
    avisa al COACH al momento (push): es dinero — un cargo indebido sería una
    devolución y un cliente enfadado. El mantenimiento diario reintenta solo
    (backstop del webhook perdido)."""
    sub_id = sub_id or client.stripe_subscription_id
    if not sub_id:
        return False
    try:
        stripe = _stripe()
        cancel = getattr(stripe.Subscription, "cancel", None) or stripe.Subscription.delete
        cancel(sub_id)
        _olvida_la_suscripcion(client, sub_id)
        log_event(db, "client", client.id, "subscription_completed",
                  {"subscription": sub_id, "motivo": motivo})
        if periodo == OFFER_PERIOD:
            # En la forma del 1 € el corte es NUEVO (antes era suscripción
            # abierta): el coach se entera de cada programa que termina — y de
            # que en ~1 mes le llegará a ese cliente el aviso de renovación.
            try:
                from app.services import push as push_svc

                first = ((client.full_name or "").split() or ["Un cliente"])[0]
                base = settings.public_base_url.rstrip("/")
                push_svc.send_to_coach(db, {
                    "title": "💰 Oferta completada: cobros detenidos",
                    "body": (f"{first} ya pagó los 3 cobros de la oferta "
                             "(1 € + 120 € + 120 €): la suscripción se ha "
                             "detenido sola. En un mes le llegará el aviso de "
                             "renovación."),
                    "count": 1,
                    "url": f"{base}/clientes/{client.id}",
                    "tag": f"dq-oferta-fin-{sub_id}",
                })
            except Exception:  # noqa: BLE001 — el push nunca rompe el corte
                pass
        return True
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "canceled" in msg or "cancelled" in msg or "no such subscription" in msg:
            # Ya estaba cancelada (reintento del webhook o baja manual): hecho.
            _olvida_la_suscripcion(client, sub_id)
            return True
        _log.warning("No se pudo cancelar la suscripción de la oferta %s: %s",
                     sub_id, exc)
        try:
            from app.services import push as push_svc

            first = ((client.full_name or "").split() or ["Un cliente"])[0]
            detalle = ("sus 2 cobros de 120,50 €" if periodo == OFFER2_PERIOD
                       else "sus 3 cobros de la oferta (1 € + 120 € + 120 €)")
            push_svc.send_to_coach(db, {
                "title": "💰⚠️ Cancela la suscripción de la oferta",
                "body": (f"{first} ya pagó {detalle} pero la suscripción no se "
                         "pudo cancelar sola: cancélala en Stripe o le llegará "
                         "otro cobro indebido."),
                "count": 1,
                "url": f"https://dashboard.stripe.com/subscriptions/{sub_id}",
                "tag": f"dq-oferta-cancelar-{sub_id}",
            })
        except Exception:  # noqa: BLE001
            pass
        return False


def _handle_invoice_event(db: Session, event: dict) -> dict:
    """Renovaciones de la suscripción de la oferta: cada mes Stripe cobra solo y
    avisa aquí. invoice.paid refresca el pago del cliente; invoice.payment_failed
    lo pasa a 'pendiente' y avisa al coach al momento — ningún impago se pierde.
    Idempotente por factura (los reintentos de Stripe no duplican avisos)."""
    invoice = event["data"]["object"]
    pagada = event["type"] == "invoice.paid"
    if not _invoice_es_de_la_oferta(invoice):
        # Factura de OTRO producto de la misma cuenta de Stripe: no es nuestra.
        return {"ignored": "invoice_ajena"}
    # La PRIMERA factura de la suscripción (billing_reason=subscription_create)
    # convive con checkout.session.completed y puede llegar ANTES o DESPUÉS.
    primera = invoice.get("billing_reason") == "subscription_create"
    client = _client_from_invoice(db, invoice)
    if client is None:
        # Es de la oferta pero no se pudo mapear: alguien tiene que enterarse
        # (también de los IMPAGOS — el caso más peligroso de perder). El
        # movimiento se anota igual, sin cliente: el feed de pagos lo enseña.
        _anotar_factura(db, invoice, None, pagada=pagada, event_id=event.get("id"))
        db.commit()
        if not primera:
            _notify_orphan_payment(db, {
                "customer_details": {"email": invoice.get("customer_email"),
                                     "name": invoice.get("customer_name")},
                "amount_total": (invoice.get("amount_paid") if pagada
                                 else invoice.get("amount_due")),
            })
        return {"ignored": "invoice_sin_cliente"}

    # Idempotencia: si esta factura ya se procesó (reintento de entrega de
    # Stripe), no se re-avisa ni se re-escribe nada.
    invoice_id = invoice.get("id")
    if invoice_id:
        from app.models import AuditLog

        ya = db.scalar(
            select(AuditLog.id).where(
                AuditLog.entity == "client", AuditLog.entity_id == client.id,
                AuditLog.event == ("payment_received" if pagada else "payment_failed"),
                AuditLog.detail_json["invoice_id"].astext == invoice_id,
            ).limit(1))
        if ya:
            return {"ignored": "invoice_repetida", "client_id": client.id}

    _anotar_factura(db, invoice, client, pagada=pagada, event_id=event.get("id"))
    if pagada:
        transicion = client.payment_status != "paid"
        client.payment_status = "paid"
        client.paid_at = datetime.now(timezone.utc)
        log_event(db, "client", client.id, "payment_received",
                  {"source": "invoice", "invoice_id": invoice_id,
                   "amount_eur": (invoice.get("amount_paid") or 0) / 100.0,
                   "billing_reason": invoice.get("billing_reason")})
        # Aviso por TRANSICIÓN o por renovación: si la primera factura llega
        # antes que el checkout, el push del alta no se pierde; si llega
        # después, no se duplica (el checkout ya avisó y esto no transiciona).
        if transicion or not primera:
            _notify_coach_payment(db, client, new_client=False,
                                  amount_cents=invoice.get("amount_paid"))
    else:
        # Un payment_failed REZAGADO (reintento de webhook posterior al cobro
        # que lo resolvió) no debe tapar un pago más nuevo.
        creado = invoice.get("created") or event.get("created")
        if (client.paid_at is not None and creado
                and client.paid_at.timestamp() > float(creado)):
            # El movimiento SÍ se guarda (es un hecho contable: hubo un intento
            # fallido), aunque el estado de la ficha no cambie. Sin este commit,
            # la fila anotada arriba se perdía al cerrar la sesión: el endpoint
            # devuelve el dict directamente y `get_db` solo hace close().
            db.commit()
            return {"ignored": "invoice_fallida_antigua", "client_id": client.id}
        client.payment_status = "pending"
        log_event(db, "client", client.id, "payment_failed",
                  {"source": "invoice", "invoice_id": invoice_id,
                   "amount_eur": (invoice.get("amount_due") or 0) / 100.0})
        _notify_coach_payment_failed(db, client)
    db.commit()
    # PROGRAMA DE LA OFERTA COMPLETADO: con el último cobro anotado (el 2º de
    # 120,50 € o el 3º de la forma 1 € + 120 + 120), la suscripción se CANCELA
    # en Stripe — el programa está pagado entero y no puede haber otro cargo.
    # Se cuenta sobre el LIBRO (no sobre billing_reason): así el reintento de
    # un webhook o una factura repescada por sync no lo rompen.
    periodo_f = periodo_de_factura(invoice, client)
    requeridos = OFFER_CHARGES_BY_PERIOD.get(periodo_f or "")
    # La suscripción DE ESTA FACTURA manda sobre la de la ficha, que puede
    # haberse quedado atrás: lo que se cuenta son las facturas de la
    # contratación en curso, no todas las que el cliente pagó alguna vez.
    sub_de_la_factura = _invoice_subscription_bits(invoice)[0]
    if (pagada and requeridos
            and pagos_oferta_cobrados(db, client, periodo_f,
                                      sub_de_la_factura) >= requeridos):
        detener_suscripcion_oferta(
            db, client,
            sub_de_la_factura or client.stripe_subscription_id,
            motivo="programa_cobrado_entero", periodo=periodo_f)
        db.commit()
    return {"invoice": "paid" if pagada else "failed", "client_id": client.id}


def _handle_subscription_deleted(db: Session, event: dict) -> dict:
    """La suscripción de la oferta se canceló (por el cliente, por impagos
    agotados o a mano en Stripe): el cliente deja de pagar → pasa a 'pendiente'
    (badge rojo + filtro de pagos) y el coach recibe push. Sin esto, la ficha
    quedaría 'pagado' para siempre tras la baja."""
    sub = event["data"]["object"]
    sub_id = sub.get("id")
    cid = (sub.get("metadata") or {}).get("client_id")
    client = None
    if cid:
        try:
            client = db.get(Client, int(cid))
        except (TypeError, ValueError):
            client = None
    if client is None and sub_id:
        client = db.scalar(select(Client).where(Client.stripe_subscription_id == sub_id))
    if client is None and sub_id:
        # ÚLTIMO RECURSO: por el LIBRO. En el alta self-serve la suscripción no
        # lleva `client_id` en su metadata (la ficha nace después, en el
        # checkout), así que el único vínculo era el campo de la ficha — y ese
        # campo se limpia en cuanto la oferta se completa. Sin esta red, el
        # `deleted` que llega DESPUÉS de la limpieza no encontraba a nadie y el
        # movimiento "Oferta completada" se perdía del feed.
        from app.models import Payment

        client = db.scalar(
            select(Client).join(Payment, Payment.client_id == Client.id)
            .where(Payment.subscription_id == sub_id).limit(1))
    if client is None:
        return {"ignored": "subscription_sin_cliente"}
    # PROGRAMA DE LA OFERTA COMPLETADO: la baja la provocamos NOSOTROS al
    # entrar el último cobro (o el coach al ver el aviso). No es un impago ni
    # un abandono: el programa está pagado entero, la ficha sigue "pagada" y
    # el contador de renovación corre desde el último cobro. Solo si la
    # suscripción muere ANTES de completar los cobros es una baja de verdad.
    requeridos = OFFER_CHARGES_BY_PERIOD.get(client.billing_period or "")
    completada = (requeridos is not None
                  and pagos_oferta_cobrados(db, client, client.billing_period)
                  >= requeridos)
    if completada:
        if client.stripe_subscription_id == sub_id:
            client.stripe_subscription_id = None
        log_event(db, "client", client.id, "subscription_completed",
                  {"subscription": sub_id, "motivo": "programa_cobrado_entero"})
        from app.services import payments as pay_svc

        descripcion = ("Oferta en 2 pagos completada (no habrá más cobros)"
                       if client.billing_period == OFFER2_PERIOD else
                       "Oferta (1 € + 120 € + 120 €) completada (no habrá más cobros)")
        pay_svc.record_payment(
            db, object_id=sub_id or f"sub_fin_{client.id}", kind="subscription",
            status="canceled", amount_cents=0,
            livemode=bool(sub.get("livemode", True)), client=client,
            billing_period=client.billing_period,
            description=descripcion,
            paid_at=pay_svc.ts_to_dt(sub.get("canceled_at") or sub.get("ended_at")
                                     or event.get("created")),
            event_id=event.get("id"),
        )
        db.commit()
        return {"subscription_completed": client.id}
    client.payment_status = "pending"
    if client.stripe_subscription_id == sub_id:
        client.stripe_subscription_id = None
    log_event(db, "client", client.id, "subscription_cancelled",
              {"subscription": sub_id})
    # La baja también SE VE en el feed de Pagos (importe 0, fuera de los
    # totales): un push se esfuma; el movimiento queda y explica por qué esa
    # suscripción dejó de generar cobros mensuales.
    from app.services import payments as pay_svc

    pay_svc.record_payment(
        db, object_id=sub_id or f"sub_baja_{client.id}", kind="subscription",
        status="canceled", amount_cents=0,
        livemode=bool(sub.get("livemode", True)), client=client,
        description="Baja de la suscripción (oferta)",
        paid_at=pay_svc.ts_to_dt(sub.get("canceled_at") or sub.get("ended_at")
                                 or event.get("created")),
        event_id=event.get("id"),
    )
    try:
        from app.services import push as push_svc

        first = ((client.full_name or "").split() or ["Un cliente"])[0]
        base = settings.public_base_url.rstrip("/")
        push_svc.send_to_coach(db, {
            "title": "💰 Suscripción cancelada",
            "body": (f"{first} ha dejado la suscripción de la oferta: no habrá "
                     "más cobros mensuales. Revisa su ficha."),
            "count": 1,
            "url": f"{base}/clientes/{client.id}",
            "tag": f"dq-sub-cancelada-{client.id}",
        })
    except Exception:  # noqa: BLE001
        pass
    db.commit()
    return {"subscription_cancelled": client.id}


def _notify_coach_offer_reused(db: Session, client: Client) -> None:
    """Push DISTINTIVO: un cliente que YA existía ha contratado la oferta de
    1 € por el enlace público. Puede ser legítimo (venía de un plan suelto) o
    un atajo para rebajarse el plan — el coach decide, pero se entera SIEMPRE."""
    try:
        from app.services import push as push_svc

        first = ((client.full_name or "").split() or ["Un cliente"])[0]
        base = settings.public_base_url.rstrip("/")
        push_svc.send_to_coach(db, {
            "title": "💰⚠️ Cliente EXISTENTE con la oferta",
            "body": (f"{first} ya estaba dado de alta y ha contratado la oferta "
                     "de 1 €. Revisa que te cuadre (puedes cancelar la "
                     "suscripción en Stripe si no)."),
            "count": 1,
            "url": f"{base}/clientes/{client.id}",
            "tag": "dq-oferta-existente",
        })
    except Exception:  # noqa: BLE001
        pass


def handle_webhook(db: Session, payload: bytes, sig_header: str | None) -> dict:
    """Verifica el aviso de Stripe y actúa: `checkout.session.completed` marca
    el pago del cliente (alta manual) o crea el perfil (registro personal);
    `invoice.paid`/`invoice.payment_failed` mantienen al día las RENOVACIONES
    de la suscripción de la oferta."""
    if not settings.stripe_webhook_secret:
        raise StripeError("Falta STRIPE_WEBHOOK_SECRET en el .env.")
    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header or "", settings.stripe_webhook_secret)
    except Exception as exc:  # firma inválida o payload corrupto
        raise StripeError(f"Firma del webhook inválida: {exc}") from exc

    if event["type"] in ("invoice.paid", "invoice.payment_failed"):
        return _handle_invoice_event(db, event)
    if event["type"] == "customer.subscription.deleted":
        return _handle_subscription_deleted(db, event)
    if event["type"] == "charge.refunded":
        return _handle_charge_refunded(db, event)
    if event["type"].startswith("charge.dispute."):
        return _handle_charge_dispute(db, event)
    if event["type"] not in ("checkout.session.completed",
                             "checkout.session.async_payment_succeeded"):
        return {"ignored": event["type"]}

    session = event["data"]["object"]
    # En modo pago único exigimos que el cobro esté completado.
    if session.get("payment_status") == "unpaid":
        return {"ignored": "unpaid"}

    evt_id = event.get("id")
    meta = session.get("metadata") or {}
    client_id = meta.get("client_id") or session.get("client_reference_id")
    # `client_reference_id` lo pone QUIEN crea la sesión, y en esta cuenta hay
    # más productos que los nuestros: un Payment Link ajeno con una referencia
    # no numérica ("pedido-42", un email) reventaba el `int()` de más abajo con
    # un 500. Stripe reintenta un 500 durante días, así que ese webhook se
    # atascaba y con él el cobro se quedaba sin anotar. Una referencia que no
    # es un id nuestro simplemente NO es nuestra.
    if client_id is not None and not str(client_id).strip().isdigit():
        client_id = None
    # SIMETRÍA con facturas (`invoice_ajena`) y cargos (`cargo_ajeno`): una
    # Checkout Session de OTRO producto de la misma cuenta (un Payment Link de
    # un ebook, un taller) no lleva NUESTRA metadata — las sesiones que crea
    # create_checkout_url siempre llevan `tier` (las legadas en vuelo pueden no
    # llevar billing_period) o `client_id`. Sin este filtro, ese pago ajeno
    # creaba una ficha «Full pagado» al comprador y le enviaba portal +
    # anamnesis de una asesoría que no contrató (auditoría crítica). Se anota
    # en el libro como huérfano (el dinero entró y se VE), pero no se fabrica
    # ningún cliente.
    if not client_id and not meta.get("tier"):
        _anotar_checkout(db, session, None, event_id=evt_id)
        db.commit()
        return {"ignored": "checkout_ajeno"}
    tier = pkgs.normalize(meta.get("tier"))
    period = meta.get("billing_period")
    importe = session.get("amount_total")

    # Alta manual: marcar ese cliente como pagado.
    if client_id:
        client = db.get(Client, int(client_id))
        if not client:
            _log.warning("Webhook Stripe: cliente %s no encontrado", client_id)
            # El dinero entró aunque no haya ficha: se anota igual (sin cliente)
            # para que el pago huérfano SE VEA en el feed, no solo en un push.
            _anotar_checkout(db, session, None, event_id=evt_id)
            db.commit()
            _notify_orphan_payment(db, session)
            return {"error": "client_not_found", "client_id": client_id}
        nuevo = _anotar_checkout(db, session, client, event_id=evt_id)
        _mark_paid(db, client, period, movimiento_nuevo=nuevo, amount_cents=importe,
                   pagado_en=_pay_svc_ts(session.get("created")), tier=tier)
        db.commit()
        _tag_subscription(db, session, client)
        return {"marked_paid": client.id}

    # Registro personal: crear el perfil desde los datos de Stripe.
    details = session.get("customer_details") or {}
    email = (details.get("email") or "").strip().lower()
    if not email:
        _log.warning("Webhook Stripe: checkout sin email; no se puede crear cliente")
        _anotar_checkout(db, session, None, event_id=evt_id)
        db.commit()
        _notify_orphan_payment(db, session)
        return {"error": "no_email"}
    existing = db.scalar(select(Client).where(func.lower(Client.email) == email))
    if existing:  # ya existía (o webhook reenviado): idempotente
        # Un cliente EXISTENTE redimiendo la oferta pública de 1 € no es un
        # alta normal: puede ser un atajo para rebajarse el plan. Se procesa
        # (el dinero entró y la suscripción existe) pero con push DISTINTIVO
        # para que el coach lo revise y decida (idempotente: solo si cambia).
        era_oferta = existing.billing_period in OFFER_PERIODS
        nuevo = _anotar_checkout(db, session, existing, event_id=evt_id)
        _mark_paid(db, existing, period, movimiento_nuevo=nuevo, amount_cents=importe,
                   pagado_en=_pay_svc_ts(session.get("created")), tier=tier)
        try:  # la factura de la oferta pudo llegar antes y quedar sin ficha
            from app.services.payments import adopt_orphans

            adopt_orphans(db, existing)
        except Exception:  # noqa: BLE001
            pass
        db.commit()
        _tag_subscription(db, session, existing)
        if period in OFFER_PERIODS and not era_oferta:
            _notify_coach_offer_reused(db, existing)
        return {"marked_paid": existing.id, "existing": True}

    client = _create_selfserve_client(
        db, name=details.get("name") or "", email=email,
        phone=details.get("phone"), tier=tier, period=period, amount_cents=importe)
    _anotar_checkout(db, session, client, event_id=evt_id)
    db.commit()
    _tag_subscription(db, session, client)
    return {"created": client.id}
