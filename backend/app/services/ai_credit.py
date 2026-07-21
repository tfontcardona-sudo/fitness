"""Créditos de la API de Anthropic — contabilidad local (fila única).

Anthropic NO expone el saldo de créditos por API, así que el portal lo lleva
en local: el coach apunta el saldo cuando recarga y cada llamada a la IA
descuenta su coste estimado (tokens reales de la respuesta × precio oficial
del modelo). El botón del sidebar muestra `balance - gastado` y enlaza a la
página de recarga de la consola de Anthropic.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AiCreditState

RECHARGE_URL = "https://console.anthropic.com/settings/billing"

# Precio oficial (USD por millón de tokens: entrada, salida) por familia.
_PRICES: tuple[tuple[str, tuple[float, float]], ...] = (
    ("haiku", (1.00, 5.00)),
    ("sonnet", (3.00, 15.00)),
    ("opus", (5.00, 25.00)),
)
_DEFAULT = (5.00, 25.00)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Coste de una llamada según la familia del modelo (entrada + salida)."""
    model_l = (model or "").lower()
    price_in, price_out = _DEFAULT
    for family, prices in _PRICES:
        if family in model_l:
            price_in, price_out = prices
            break
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def get_state(db: Session) -> AiCreditState:
    """Fila única get-or-create (mismo patrón que BrandConfig)."""
    state = db.scalar(select(AiCreditState).limit(1))
    if not state:
        state = AiCreditState(spent_usd=0.0)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def remaining_usd(state: AiCreditState) -> float | None:
    """Saldo restante estimado; None mientras el coach no configure el saldo."""
    if state.balance_usd is None:
        return None
    return round(state.balance_usd - (state.spent_usd or 0.0), 2)


def record_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    """Acumula el coste de una llamada. Sesión propia y a prueba de fallos:
    la contabilidad JAMÁS puede romper una generación de plan."""
    try:
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        if cost <= 0:
            return
        from app.db import SessionLocal

        with SessionLocal() as db:
            state = get_state(db)
            state.spent_usd = (state.spent_usd or 0.0) + cost
            db.commit()
    except Exception:  # noqa: BLE001 — contabilidad best-effort
        pass
