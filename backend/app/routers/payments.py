"""Feed de pagos del panel del coach — "quién pagó, cuánto y cuándo".

Lee el LIBRO DE CAJA (`payments`, alimentado por el webhook de Stripe y por la
sincronización) y lo sirve como un feed tipo app de banco: movimientos del más
reciente al más antiguo, con lo NO LEÍDO marcado (`seen_at IS NULL`) y una
cabecera con los ingresos del mes.

  GET  /api/payments            feed paginado (limit/offset, filtro por estado)
  GET  /api/payments/summary    cabecera: mes, mes anterior, sin leer, avisos
  POST /api/payments/seen       sella lo leído (todos o los indicados)
  POST /api/payments/sync       repesca de Stripe lo que falte (histórico y
                                cobros cuyo webhook se perdió)

GOTCHA: sin `from __future__ import annotations` (gotcha §5.1 — rompe la
resolución de tipos de FastAPI/Pydantic en los routers).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client
from app.schemas.entities import (
    PaymentOut,
    PaymentsListOut,
    PaymentsSeenIn,
    PaymentsSummaryOut,
)
from app.services import payments as pay_svc

router = APIRouter(prefix="/api/payments", tags=["payments"],
                   dependencies=[Depends(get_current_user)])


def _to_out(pago, nombres: dict) -> PaymentOut:
    """Fila del libro → item del feed. El nombre a mostrar es el de la ficha si
    aún existe (puede haberse corregido tras el cobro) y, si no, el que dio
    Stripe: un pago huérfano también tiene que decir de quién es."""
    nombre = nombres.get(pago.client_id) or pago.customer_name or pago.customer_email
    return PaymentOut(
        id=pago.id,
        kind=pago.kind,
        status=pago.status,
        amount_cents=pago.amount_cents,
        currency=pago.currency,
        livemode=pago.livemode,
        client_id=pago.client_id,
        display_name=nombre or "Sin identificar",
        customer_email=pago.customer_email,
        tier=pago.tier,
        billing_period=pago.billing_period,
        description=pago.description,
        paid_at=pago.paid_at,
        seen_at=pago.seen_at,
        stripe_object_id=pago.stripe_object_id,
    )


@router.get("", response_model=PaymentsListOut)
def list_payments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PaymentsListOut:
    filas, total = pay_svc.list_payments(
        db, limit=limit, offset=offset, status=status_filter, client_id=client_id)
    # Nombres en UNA consulta (nada de N+1 recorriendo el feed cliente a cliente).
    ids = {p.client_id for p in filas if p.client_id}
    nombres = dict(db.execute(
        select(Client.id, Client.full_name).where(Client.id.in_(ids))
    ).all()) if ids else {}
    return PaymentsListOut(
        items=[_to_out(p, nombres) for p in filas],
        count=total,
        unseen=pay_svc.unseen_count(db),
    )


@router.get("/summary", response_model=PaymentsSummaryOut)
def payments_summary(db: Session = Depends(get_db)) -> PaymentsSummaryOut:
    return PaymentsSummaryOut(**pay_svc.summary(db))


@router.post("/seen")
def mark_seen(body: PaymentsSeenIn | None = None,
              db: Session = Depends(get_db)) -> dict:
    """Marca lo leído (como abrir la app del banco). Sin cuerpo, marca todo."""
    marcados = pay_svc.mark_seen(db, (body.ids if body else None))
    return {"marked": marcados, "unseen": pay_svc.unseen_count(db)}


@router.post("/sync")
def sync_payments(days: int = Query(default=pay_svc.SYNC_DEFAULT_DAYS, ge=1, le=1095),
                  db: Session = Depends(get_db)) -> dict:
    """Trae de Stripe los movimientos que falten (histórico previo a esta tabla
    y cobros cuyo webhook se perdió). Idempotente: lo ya anotado se ignora."""
    from app.services.stripe_service import StripeError

    try:
        return pay_svc.sync_from_stripe(db, days=days)
    except StripeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
