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
# La caché lleva la MARCA: al cambiar el switch, el catálogo de la otra
# marca no puede servirse por estar aún caliente.
_CACHE: dict = {"data": None, "at": 0.0, "marca": None}
_TTL_S = 120.0

# Los nombres salen de la MARCA activa (el escaparate del panel), no de una
# constante: con dos negocios en el mismo sistema, "DQR Full" solo vale para uno.
from app.services import packages as _pkgs


def _tier_label(tier: str) -> str:
    return _pkgs.label(tier)
PERIOD_LABEL = {"1m": "Mensual", "3m": "Trimestral", "6m": "Semestral"}


def _eur(cents: int) -> float:
    return round(cents / 100.0, 2)


def _txt(cents: int) -> str:
    """Importe como lo lee una persona en España: "1 €", "120,50 €"."""
    v = cents / 100.0
    return (f"{int(v)}" if float(v).is_integer() else f"{v:.2f}".replace(".", ",")) + " €"


def _todos_los_precios() -> dict:
    """{lookup_key: precio} de TODO el catálogo en una sola consulta (troceada
    en tandas de 10 como exige Stripe). Antes se pedía precio a precio: doce
    viajes a Stripe cada vez que el coach abría la pantalla."""
    if not settings.stripe_enabled:
        return {}
    from app.services.branding import marca_activa

    marca = marca_activa()
    keys = [marca.lookup_key(t, p) for t, p in marca.vende()]
    if marca.vende_oferta():
        keys += [marca.lookup_key(ss.OFFER_TIER, ss.OFFER_PERIOD),
                 marca.lookup_key(ss.OFFER_TIER, ss.OFFER2_PERIOD)]
    try:
        return ss._prices_by_lookup(ss._stripe(), keys)
    except Exception as exc:  # noqa: BLE001 — Stripe caído no rompe el panel
        _log.warning("catálogo: no se pudieron leer los precios: %s", exc)
        return {}


def _precio_de_stripe(precios: dict, tier: str, period: str) -> tuple[int | None, str | None]:
    """(importe en céntimos, problema) de un plan × duración."""
    if not settings.stripe_enabled:
        return None, "Stripe no está configurado en el servidor."
    pr = precios.get(ss._lookup_key(tier, period))
    if pr is None:
        # Reserva: un id puesto a mano en el .env sigue siendo válido para cobrar.
        if settings.stripe_price_for(tier, period) or settings.stripe_price_legacy(tier, period):
            return None, None
        return None, ("Falta el precio en Stripe (se crea solo al primer cobro "
                      "o con el script de precios).")
    if not pr.get("active", True):
        return None, "El precio existe en Stripe pero está archivado."
    return int(pr.get("unit_amount") or 0), None


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
          schedule: list[dict] | None = None, per_month_cents: int | None = None,
          tier_label: str = "", period_label: str = "",
          highlight: bool = False) -> dict:
    return {
        # Etiquetas ya montadas: el panel no tiene que trocear títulos.
        "tier_label": tier_label,
        "period_label": period_label,
        "per_month_eur": _eur(per_month_cents) if per_month_cents else None,
        # CALENDARIO de cobros (cuándo y cuánto). Lo calcula el backend con los
        # céntimos reales: el panel lo pintaba restando (total − primero) / 2,
        # que se rompe en cuanto cambie un importe.
        "schedule": schedule or [{"when": "Hoy", "eur": _eur(first_cents)}],
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
    """Todo lo vendible con su enlace y su estado. Cacheado 2 minutos.

    QUÉ se vende lo decide la MARCA activa, no una tabla fija en el código:
    DQR ofrece 3 planes × 3 duraciones + las dos formas de su oferta;
    Professional, un solo plan mensual (Génesis.99) y sus servicios de centro,
    que se cobran allí y no por la web. Lo que la marca no vende no aparece —
    antes salían once productos vacíos con su enlace roto."""
    from app.services.branding import marca_activa

    marca = marca_activa()
    if (not refresh and _CACHE["data"] is not None
            and _CACHE.get("marca") == marca.slug
            and time.time() - _CACHE["at"] < _TTL_S):
        return _CACHE["data"]

    base = settings.public_base_url.rstrip("/")
    items: list[dict] = []
    precios = _todos_los_precios()

    # --- Las DOS formas de pagar la MISMA oferta (programa cerrado de 3 meses).
    # Solo si la marca TIENE oferta de captación: un centro puede no tenerla.
    if marca.vende_oferta():
        cupon = _cupon_de_la_oferta()
        of_cents, of_issue = _precio_de_stripe(precios, ss.OFFER_TIER, ss.OFFER_PERIOD)
        oferta = marca.oferta()
        primer = int(oferta.get("first_month_cents") or ss.OFFER_FIRST_MONTH_CENTS)
        cobros = int(oferta.get("charges") or ss.OFFER_CHARGES)
        mensual = of_cents if of_cents is not None else int(
            oferta.get("monthly_cents") or ss.OFFER_MONTHLY_CENTS)
        total3 = primer + mensual * (cobros - 1)
        items.append(_item(
            key="oferta", kind="oferta", tier=ss.OFFER_TIER, period=ss.OFFER_PERIOD,
            title="Oferta · en 3 pagos", tier_label=_tier_label(ss.OFFER_TIER),
            period_label="En 3 pagos",
            subtitle=(f"{_txt(primer)} hoy, luego {_txt(mensual)} y {_txt(mensual)}"),
            charges=cobros, total_cents=total3,
            first_cents=primer, auto_stop=True, base=base,
            schedule=[{"when": "Hoy", "eur": _eur(primer)},
                      {"when": "Al mes", "eur": _eur(mensual)},
                      {"when": "A los 2 meses", "eur": _eur(mensual)}],
            issue=of_issue or cupon, highlight=True,
        ))

        of2_cents, of2_issue = _precio_de_stripe(precios, ss.OFFER_TIER, ss.OFFER2_PERIOD)
        of2 = marca.oferta("oferta2")
        cobros2 = int(of2.get("charges") or ss.OFFER2_CHARGES)
        cada = of2_cents if of2_cents is not None else int(
            of2.get("monthly_cents") or ss.OFFER2_MONTHLY_CENTS)
        items.append(_item(
            key="oferta2", kind="oferta", tier=ss.OFFER_TIER, period=ss.OFFER2_PERIOD,
            title="Oferta · en 2 pagos", tier_label=_tier_label(ss.OFFER_TIER),
            period_label="En 2 pagos",
            subtitle=f"{_txt(cada)} hoy y {_txt(cada)} en un mes",
            charges=cobros2, total_cents=cada * cobros2,
            first_cents=cada, auto_stop=True, base=base,
            schedule=[{"when": "Hoy", "eur": _eur(cada)},
                      {"when": "Al mes", "eur": _eur(cada)}],
            issue=of2_issue, highlight=True,
        ))

    # --- Planes normales (pago único por la duración contratada).
    meses = {"1m": 1, "3m": 3, "6m": 6}
    for tier, period in marca.vende():
        cents, issue = _precio_de_stripe(precios, tier, period)
        importe = cents if cents is not None else marca.importe(tier, period)
        n = meses[period]
        al_mes = f" · {_txt(round(importe / n))}/mes" if n > 1 else ""
        items.append(_item(
            key=f"{tier}-{period}", kind="plan", tier=tier, period=period,
            title=f"{_tier_label(tier)} · {PERIOD_LABEL[period]}",
            tier_label=_tier_label(tier), period_label=PERIOD_LABEL[period],
            per_month_cents=(round(importe / n) if n > 1 else None),
            subtitle=f"{_txt(importe)} en un pago{al_mes} · no se renueva solo",
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
        # La MARCA a la que pertenece este catálogo: la pantalla de Vender lo
        # dice, para que el coach no mande el enlace del otro negocio.
        "brand": {"slug": marca.slug, "name": marca.name,
                  "color_primary": marca.color_primary,
                  "contact_phone": marca.contact_phone,
                  "contact_address": marca.contact_address},
        # Lo que la marca vende pero NO cobra por la web (entreno personal,
        # packs de sesiones): se enseña para poder decírselo al cliente.
        "extra_services": list(marca.extra_services or []),
    }
    _CACHE["data"] = data
    _CACHE["at"] = time.time()
    _CACHE["marca"] = marca.slug
    return data
