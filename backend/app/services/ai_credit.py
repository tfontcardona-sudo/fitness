"""Créditos de la API de Anthropic — contabilidad local (fila única).

Anthropic NO expone el saldo de créditos por API, así que el portal lo lleva
en local: el coach apunta el saldo cuando recarga y cada llamada a la IA
descuenta su coste estimado (tokens reales de la respuesta × precio oficial
del modelo). El botón del sidebar muestra `balance - gastado` y enlaza a la
página de recarga de la consola de Anthropic.
"""

from __future__ import annotations

from sqlalchemy import func, select
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
    """Acumula el coste de una llamada y deja su rastro para el consumo en vivo.
    Sesión propia y a prueba de fallos: la contabilidad JAMÁS puede romper una
    generación de plan."""
    try:
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        if cost <= 0:
            return
        from app.db import SessionLocal
        from app.models import AiUsageEvent

        from sqlalchemy import update

        with SessionLocal() as db:
            state = get_state(db)   # get-or-create de la fila única
            # SUMA EN LA BASE, no leer-modificar-escribir. Los 8-10 revisores
            # del panel corren EN PARALELO, cada uno con su sesión: con el
            # patrón anterior todos leían el mismo saldo y el último en
            # escribir se llevaba por delante lo que habían sumado los otros.
            # El gasto anotado salía por debajo del real y el coach veía un
            # saldo optimista justo en la operación que más créditos consume.
            db.execute(
                update(AiCreditState)
                .where(AiCreditState.id == state.id)
                .values(spent_usd=func.coalesce(AiCreditState.spent_usd, 0.0) + cost)
            )
            db.add(AiUsageEvent(
                model=model or "?", input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0, cost_usd=cost,
            ))
            db.commit()
    except Exception:  # noqa: BLE001 — contabilidad best-effort
        pass


# ------------------------------------------------------- consumo en vivo ----

# Ventana para estimar el coste medio por plan (y con él, los planes restantes).
USAGE_WINDOW_DAYS = 30


def usage_summary(db: Session) -> dict:
    """Consumo REAL en vivo: gasto de hoy, de la ventana, nº de llamadas, última
    llamada y coste medio por plan (gasto de la ventana ÷ planes generados con IA
    en la ventana). Nunca lanza: ante cualquier fallo devuelve ceros."""
    from datetime import timedelta

    from sqlalchemy import func

    from app.models import AiUsageEvent, Plan
    from app.services.portal import today_local

    out = {
        "spent_today_usd": 0.0, "spent_window_usd": 0.0, "calls_window": 0,
        "last_call_at": None, "avg_cost_per_plan_usd": None,
        "window_days": USAGE_WINDOW_DAYS,
    }
    try:
        since = _utcnow() - timedelta(days=USAGE_WINDOW_DAYS)
        # Día de negocio (Europe/Madrid), igual que el resto del sistema.
        start_today = _start_of_local_day(today_local())

        row = db.execute(
            select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0.0),
                   func.count(AiUsageEvent.id),
                   func.max(AiUsageEvent.created_at))
            .where(AiUsageEvent.created_at >= since)
        ).one()
        out["spent_window_usd"] = round(float(row[0] or 0.0), 4)
        out["calls_window"] = int(row[1] or 0)
        out["last_call_at"] = row[2]

        out["spent_today_usd"] = round(float(db.scalar(
            select(func.coalesce(func.sum(AiUsageEvent.cost_usd), 0.0))
            .where(AiUsageEvent.created_at >= start_today)
        ) or 0.0), 4)

        # Planes generados con IA en la misma ventana → coste medio por plan.
        # "coach" (manual) y "scaffold" (base sin IA del avanzado) NO cuentan:
        # cuestan 0 y meterlos en el denominador falsearía el coste medio.
        plans = int(db.scalar(
            select(func.count(Plan.id))
            .where(Plan.created_at >= since, Plan.generated_by.isnot(None),
                   Plan.generated_by.notin_(("coach", "scaffold", "library")))
        ) or 0)
        if plans > 0 and out["spent_window_usd"] > 0:
            out["avg_cost_per_plan_usd"] = round(out["spent_window_usd"] / plans, 4)
    except Exception:  # noqa: BLE001 — el resumen nunca rompe el endpoint
        pass
    return out


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _start_of_local_day(local_date):
    """Medianoche de la fecha de negocio (Europe/Madrid), con huso."""
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    return datetime.combine(local_date, time.min, tzinfo=ZoneInfo("Europe/Madrid"))


def plans_left(remaining: float | None, avg_cost_per_plan: float | None) -> int | None:
    """Planes que aún se pueden generar con el saldo restante (estimación).
    None si falta el saldo o aún no hay histórico para estimar el coste medio."""
    if remaining is None or not avg_cost_per_plan or avg_cost_per_plan <= 0:
        return None
    return max(0, int(remaining // avg_cost_per_plan))
