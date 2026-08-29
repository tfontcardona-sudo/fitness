"""Catálogo de VENTA del panel: qué puede vender el coach y con qué enlace.

Una sola verdad para la pantalla "Vender" del panel: cada cosa vendible (las
dos formas de pagar la OFERTA y los 9 planes × duración) con su importe real,
sus condiciones en cristiano, su ENLACE de pago definitivo y —lo importante—
si ese enlace va a funcionar de verdad.

Por qué existe: el enlace de pago se construía en el navegador
(`window.location.origin`) y no se comprobaba nada. Si a Stripe le faltaba el
precio o el cupón, el cliente que abría el enlace acababa en la página de
planes (o en un error) y el coach no se enteraba. Aquí el enlace lo da el
BACKEND (dominio público oficial) y viene con `ready`/`issue`: el panel puede
avisar ANTES de mandárselo a nadie.
"""

from __future__ import annotations

import logging
import time

from app.config import settings
from app.services import stripe_service as ss

_log = logging.getLogger("app.sales")

# El catálogo consulta Stripe (precios + cupón): se cachea igual que los precios
# públicos para no pedirlo en cada pintado del panel.
_CACHE: dict = {"data": None, "at": 0.0}
_TTL_S = 120.0

TIER_LABEL = {"train": "DQR Train", "nutri": "DQR Nutri", "full": "DQR Full"}
PERIOD_LABEL = {"1m": "Mensual", "3m": "Trimestral", "6m": "Semestral"}


def _eur(cents: int) -> float:
    return round(cents / 100.0, 2)


def _txt(cents: int) -> str:
    """Importe como lo lee una persona en España: "1 €", "120,50 €"."""
    v = cents / 100.0
    return (f"{int(v)}" if float(v).is_integer() else f"{v:.2f}".replace(".", ",")) + " €"


def _precio_de_stripe(tier: str, period: str) -> tuple[int | None, str | None]:
    """(importe en céntimos, problema). El importe sale de Stripe; si no se
    puede leer, se devuelve None y el motivo (el caller cae al canónico)."""
    if not settings.stripe_enabled:
        return None, "Stripe no está configurado en el servidor."
    try:
        price_id = ss._resolve_price_id(tier, period)
    except Exception as exc:  # noqa: BLE001 — Stripe caído no rompe el panel
        _log.warning("catálogo: no se pudo resolver el precio %s %s: %s", tier, period, exc)
        return None, "No se ha podido consultar Stripe ahora mismo."
    if not price_id:
        return None, "Falta el precio en Stripe (se crea solo al primer cobro o con el script de precios)."
    try:
        pr = ss._stripe().Price.retrieve(price_id)
        if not pr.get("active", True):
            return None, "El precio existe en Stripe pero está archivado."
        return int(pr.get("unit_amount") or 0), None
    except Exception as exc:  # noqa: BLE001
        _log.warning("catálogo: precio %s ilegible: %s", price_id, exc)
        return None, "El precio existe pero Stripe no ha respondido."


def _cupon_de_la_oferta() -> str | None:
    """Problema con el cupón del primer mes a 1 €, o None si está bien.
    Sin cupón, el checkout de la oferta en 3 pagos falla al crearse y el cliente
    acaba en /planes sin saber por qué."""
    if not settings.stripe_enabled:
        return "Stripe no está configurado en el servidor."
    try:
        cup = ss._stripe().Coupon.retrieve(ss.OFFER_COUPON_ID)
        if cup.get("valid") is False:
            return "El cupón del primer mes a 1 € ya no es válido en Stripe."
        return None
    except Exception as exc:  # noqa: BLE001
        _log.warning("catálogo: cupón %s ilegible: %s", ss.OFFER_COUPON_ID, exc)
        return "Falta el cupón del primer mes a 1 € en Stripe."


def _item(*, key: str, kind: str, tier: str, period: str, title: str,
          subtitle: str, charges: int, total_cents: int, first_cents: int,
          auto_stop: bool, base: str, issue: str | None,
          highlight: bool = False) -> dict:
    return {
        "key": key,
        "kind": kind,                  # "oferta" | "plan"
        "tier": tier,
        "period": period,
        "title": title,
        "subtitle": subtitle,
        "charges": charges,            # nº de cobros que hará Stripe
        "total_eur": _eur(total_cents),
        "first_eur": _eur(first_cents),  # lo que paga HOY
        "auto_stop": auto_stop,        # ¿el cobro se detiene solo al final?
        "url": f"{base}/api/pay/plan/{tier}/{period}",
        "ready": issue is None,
        "issue": issue,
        "highlight": highlight,
    }


def sales_catalog(*, refresh: bool = False) -> dict:
    """Todo lo vendible con su enlace y su estado. Cacheado 2 minutos."""
    if not refresh and _CACHE["data"] is not None and time.time() - _CACHE["at"] < _TTL_S:
        return _CACHE["data"]

    base = settings.public_base_url.rstrip("/")
    items: list[dict] = []

    # --- Las DOS formas de pagar la MISMA oferta (programa cerrado de 3 meses).
    cupon = _cupon_de_la_oferta()
    of_cents, of_issue = _precio_de_stripe(ss.OFFER_TIER, ss.OFFER_PERIOD)
    mensual = of_cents if of_cents is not None else ss.OFFER_MONTHLY_CENTS
    total3 = ss.OFFER_FIRST_MONTH_CENTS + mensual * (ss.OFFER_CHARGES - 1)
    items.append(_item(
        key="oferta", kind="oferta", tier=ss.OFFER_TIER, period=ss.OFFER_PERIOD,
        title="Oferta · en 3 pagos",
        subtitle=(f"{_txt(ss.OFFER_FIRST_MONTH_CENTS)} hoy, luego "
                  f"{_txt(mensual)} y {_txt(mensual)}"),
        charges=ss.OFFER_CHARGES, total_cents=total3,
        first_cents=ss.OFFER_FIRST_MONTH_CENTS, auto_stop=True, base=base,
        issue=of_issue or cupon, highlight=True,
    ))

    of2_cents, of2_issue = _precio_de_stripe(ss.OFFER_TIER, ss.OFFER2_PERIOD)
    cada = of2_cents if of2_cents is not None else ss.OFFER2_MONTHLY_CENTS
    items.append(_item(
        key="oferta2", kind="oferta", tier=ss.OFFER_TIER, period=ss.OFFER2_PERIOD,
        title="Oferta · en 2 pagos",
        subtitle=f"{_txt(cada)} hoy y {_txt(cada)} en un mes",
        charges=ss.OFFER2_CHARGES, total_cents=cada * ss.OFFER2_CHARGES,
        first_cents=cada, auto_stop=True, base=base,
        issue=of2_issue, highlight=True,
    ))

    # --- Planes normales (pago único por la duración contratada).
    meses = {"1m": 1, "3m": 3, "6m": 6}
    for tier in ss.TIER_ORDER:
        for period in ss.PERIOD_ORDER:
            cents, issue = _precio_de_stripe(tier, period)
            importe = cents if cents is not None else ss.CANONICAL_AMOUNTS[tier][period]
            n = meses[period]
            al_mes = f" · {_txt(round(importe / n))}/mes" if n > 1 else ""
            items.append(_item(
                key=f"{tier}-{period}", kind="plan", tier=tier, period=period,
                title=f"{TIER_LABEL[tier]} · {PERIOD_LABEL[period]}",
                subtitle=f"{_txt(importe)} en un pago{al_mes}",
                charges=1, total_cents=importe, first_cents=importe,
                auto_stop=False, base=base, issue=issue,
            ))

    data = {
        "base_url": base,
        "stripe_enabled": bool(settings.stripe_enabled),
        # Modo de PRUEBA de Stripe: un enlace de test NO cobra de verdad — el
        # coach tiene que saberlo antes de mandárselo a un cliente.
        "test_mode": bool(settings.stripe_secret_key.startswith("sk_test")),
        "items": items,
    }
    _CACHE["data"] = data
    _CACHE["at"] = time.time()
    return data
