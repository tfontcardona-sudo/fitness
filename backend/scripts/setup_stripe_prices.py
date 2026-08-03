"""Crea (o actualiza) en Stripe los 9 precios de los planes DQR — sin tocar el .env.

Uso, EN EL SERVIDOR (usa la STRIPE_SECRET_KEY que ya está en el .env):

    docker compose exec api python scripts/setup_stripe_prices.py

Qué hace, de forma IDEMPOTENTE (se puede ejecutar mil veces):
  1. Asegura un Producto por plan (DQR Train / DQR Nutri / DQR Full).
  2. Asegura un Precio por plan × duración con lookup_key "dqr_{tier}_{period}".
     El backend resuelve los precios por ese lookup_key, así que NO hay que
     copiar ningún ID al .env.
  3. Si un precio existe con OTRO importe, crea el nuevo y le TRANSFIERE el
     lookup_key (el antiguo queda desactivado; los pagos pasados no se tocan).

Importes (EUR, pago único por período — STRIPE_MODE=payment):
  Train  69 €/mes · 195 € trimestre · 372 € semestre
  Nutri  79 €/mes · 225 € trimestre · 432 € semestre
  Full  129 €/mes · 369 € trimestre · 708 € semestre
(El trimestre/semestre llevan un descuento pequeño por compromiso; Full siempre
por debajo de la suma de Train+Nutri.)
"""
from __future__ import annotations

import sys

# Importes en CÉNTIMOS por plan × duración.
AMOUNTS: dict[str, dict[str, int]] = {
    "train": {"1m": 6900, "3m": 19500, "6m": 37200},
    "nutri": {"1m": 7900, "3m": 22500, "6m": 43200},
    "full": {"1m": 12900, "3m": 36900, "6m": 70800},
}
PRODUCT_NAMES = {"train": "DQR Train", "nutri": "DQR Nutri", "full": "DQR Full"}
PERIOD_LABEL = {"1m": "1 mes", "3m": "3 meses", "6m": "6 meses"}
CURRENCY = "eur"


def lookup_key(tier: str, period: str) -> str:
    return f"dqr_{tier}_{period}"


def ensure_product(stripe, tier: str) -> str:
    """Producto del plan (uno por tier, marcado con metadata dqr_tier)."""
    for prod in stripe.Product.list(active=True, limit=100)["data"]:
        if (prod.get("metadata") or {}).get("dqr_tier") == tier:
            return prod["id"]
    prod = stripe.Product.create(
        name=PRODUCT_NAMES[tier], metadata={"dqr_tier": tier},
        description=f"Asesoría {PRODUCT_NAMES[tier]} — pago por período",
    )
    print(f"  + producto creado: {PRODUCT_NAMES[tier]} ({prod['id']})")
    return prod["id"]


def ensure_price(stripe, tier: str, period: str, product_id: str) -> None:
    key = lookup_key(tier, period)
    amount = AMOUNTS[tier][period]
    existing = stripe.Price.list(lookup_keys=[key], active=True, limit=1)["data"]
    if existing:
        pr = existing[0]
        if pr["unit_amount"] == amount and pr["currency"] == CURRENCY:
            print(f"  = {key}: ya existe con {amount / 100:.2f} € (sin cambios)")
            return
        # Importe distinto: precio nuevo con el MISMO lookup_key (transferido).
        stripe.Price.create(
            product=pr["product"], currency=CURRENCY, unit_amount=amount,
            lookup_key=key, transfer_lookup_key=True,
            nickname=f"{PRODUCT_NAMES[tier]} · {PERIOD_LABEL[period]}",
        )
        stripe.Price.modify(pr["id"], active=False)
        print(f"  ~ {key}: {pr['unit_amount'] / 100:.2f} € → {amount / 100:.2f} € "
              "(precio nuevo, el antiguo desactivado)")
        return
    stripe.Price.create(
        product=product_id, currency=CURRENCY, unit_amount=amount,
        lookup_key=key,
        nickname=f"{PRODUCT_NAMES[tier]} · {PERIOD_LABEL[period]}",
    )
    print(f"  + {key}: creado con {amount / 100:.2f} €")


def main() -> int:
    from app.config import settings

    if not settings.stripe_enabled:
        print("ERROR: falta STRIPE_SECRET_KEY en el .env del servidor.")
        return 1
    import stripe

    stripe.api_key = settings.stripe_secret_key
    live = settings.stripe_secret_key.startswith("sk_live")
    print(f"Stripe en modo {'LIVE (cobros reales)' if live else 'TEST'}.\n")

    for tier in ("train", "nutri", "full"):
        print(f"{PRODUCT_NAMES[tier]}:")
        product_id = ensure_product(stripe, tier)
        for period in ("1m", "3m", "6m"):
            ensure_price(stripe, tier, period, product_id)
        print()

    print("Listo. El backend resuelve estos precios por lookup_key: no hay que "
          "copiar IDs al .env. La página /planes los mostrará en ~10 min como "
          "máximo (caché) o al reiniciar la api.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
