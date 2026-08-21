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
  POST /api/payments/manual     cobro FUERA de Stripe (efectivo, transferencia,
                                Bizum): suma en el total del mes igual que uno
                                de la pasarela

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
    ManualPaymentIn,
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
        fee_cents=pago.fee_cents,
    )


@router.get("", response_model=PaymentsListOut)
def list_payments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None),
    orphan: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> PaymentsListOut:
    filas, total = pay_svc.list_payments(
        db, limit=limit, offset=offset, status=status_filter, client_id=client_id,
        orphan=orphan)
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


@router.get("/monthly")
def payments_monthly(months: int = Query(default=6, ge=2, le=24),
                     db: Session = Depends(get_db)) -> dict:
    """Ingresos netos por mes (gráfica de barras de la pantalla de Pagos)."""
    return {"months": pay_svc.monthly_series(db, months=months)}


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db)):
    """Libro de caja completo en CSV para la gestoría. Separador ';' y BOM
    UTF-8 para que Excel en español lo abra bien a doble clic. Se descarga
    desde el panel con el JWT en la cabecera (fetch → blob), como los Word."""
    import csv
    import io
    from zoneinfo import ZoneInfo

    from fastapi.responses import Response

    from app.config import settings as cfg
    from app.models import Payment

    filas = db.execute(
        select(Payment, Client.full_name)
        .outerjoin(Client, Client.id == Payment.client_id)
        .order_by(Payment.paid_at.desc())
    ).all()
    tz = ZoneInfo(cfg.tz)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Hora", "Cliente", "Email", "Concepto", "Tipo", "Estado",
                "Importe (€)", "Comisión Stripe (€)", "Neto (€)", "Moneda",
                "Modo", "ID de Stripe"])
    estados = {"paid": "Cobrado", "failed": "Fallido", "refunded": "Devolución",
               "canceled": "Baja"}
    tipos = {"checkout": "Pago único", "invoice": "Suscripción",
             "refund": "Devolución", "subscription": "Suscripción"}
    for pago, nombre in filas:
        local = pago.paid_at.astimezone(tz) if pago.paid_at else None
        importe = pago.amount_cents / 100
        if pago.status == "refunded":
            importe = -importe
        fee = (pago.fee_cents / 100) if pago.fee_cents is not None else None
        neto = (importe - fee) if (fee is not None and importe > 0) else None
        # Formato numérico español: coma decimal (Excel es-ES).
        def _num(v):
            return (f"{v:.2f}".replace(".", ",")) if v is not None else ""
        w.writerow([
            local.strftime("%d/%m/%Y") if local else "",
            local.strftime("%H:%M") if local else "",
            nombre or pago.customer_name or "",
            pago.customer_email or "",
            pago.description or "",
            tipos.get(pago.kind, pago.kind),
            estados.get(pago.status, pago.status),
            _num(importe), _num(fee), _num(neto),
            (pago.currency or "eur").upper(),
            "Real" if pago.livemode else "Prueba",
            pago.stripe_object_id,
        ])
    contenido = "﻿" + buf.getvalue()  # BOM: Excel detecta UTF-8
    return Response(
        content=contenido, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pagos_dqr.csv"'},
    )


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


@router.post("/manual", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def manual_payment(body: ManualPaymentIn, db: Session = Depends(get_db)) -> PaymentOut:
    """Anota un cobro que NO pasó por Stripe y actualiza la ficha del cliente.

    Sin esto el libro de caja solo contaba la pasarela y el total del mes mentía
    en cuanto el cliente pagaba en efectivo o por transferencia.
    """
    client = db.get(Client, body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    pago = pay_svc.record_manual_payment(
        db, client=client,
        amount_cents=int(round(body.amount_eur * 100)),
        method=body.method, paid_on=body.paid_on, note=body.note,
    )
    if pago is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese cobro ya estaba anotado")

    # La ficha queda al día: el ciclo de renovación cuenta desde ESTE cobro.
    client.payment_status = "paid"
    if client.paid_at is None or pago.paid_at > client.paid_at:
        client.paid_at = pago.paid_at
    # Un cobro nuevo reabre la ventana del recordatorio de renovación.
    if hasattr(client, "renewal_reminder_sent_at"):
        client.renewal_reminder_sent_at = None
    db.commit()
    db.refresh(pago)
    return _to_out(pago, {client.id: client.full_name})
