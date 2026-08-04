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
  Train  69 €/mes · 177 € trimestre (59/mes) · 324 € semestre (54/mes)
  Nutri  79 €/mes · 201 € trimestre (67/mes) · 372 € semestre (62/mes)
  Full  129 €/mes · 330 € trimestre (110/mes) · 600 € semestre (100/mes)
(Ancla fijada por el dueño: Full trimestral 330 €. Descuento por compromiso
~15 % al mes en trimestral y ~22 % en semestral; Full siempre por debajo de
la suma de Train+Nutri.)

La tabla de importes y la lógica de alta viven en
app.services.stripe_service (CANONICAL_AMOUNTS + ensure_canonical_prices):
este script solo las invoca desde la terminal. Además, la propia api hace
AUTO-ALTA de los precios que falten al resolverlos — este script queda como
vía manual/explícita.
"""
from __future__ import annotations

import pathlib
import sys

# GOTCHA: lanzado como `python scripts/setup_stripe_prices.py`, sys.path[0] es
# scripts/ (no el WORKDIR del contenedor), y `app` no se puede importar. Sin
# esta línea el script moría con ModuleNotFoundError y el deploy lo silenciaba.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services.stripe_service import (  # noqa: E402
    CANONICAL_AMOUNTS,
    ensure_canonical_prices,
)

# Alias para quien importe la tabla desde el script (tests, otros scripts).
AMOUNTS = CANONICAL_AMOUNTS


def main() -> int:
    from app.config import settings

    if not settings.stripe_enabled:
        print("ERROR: falta STRIPE_SECRET_KEY en el .env del servidor.")
        return 1
    import stripe

    stripe.api_key = settings.stripe_secret_key
    live = settings.stripe_secret_key.startswith("sk_live")
    print(f"Stripe en modo {'LIVE (cobros reales)' if live else 'TEST'}.\n")

    ensure_canonical_prices(stripe, log=print)

    print("\nListo. El backend resuelve estos precios por lookup_key: no hay que "
          "copiar IDs al .env. La página /planes los mostrará en ~10 min como "
          "máximo (caché) o al reiniciar la api.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
