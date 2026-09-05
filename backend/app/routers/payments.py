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

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
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
from app.services.audit import log_event

router = APIRouter(prefix="/api/payments", tags=["payments"],
                   dependencies=[Depends(get_current_user)])


def _slug_marca(db: Session) -> str:
    """Identificador corto de la marca activa, para el nombre del CSV: con dos
    negocios, dos archivos "pagos_dqr.csv" en la carpeta de descargas son el
    mismo libro para el que los abre."""
    from app.services.branding import marca_activa

    return (marca_activa(db).slug or "dqr")


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
        # Neto REAL del cliente (cobros − devoluciones, sin dinero de prueba):
        # la ficha lo sumaba de la página que pintaba y mentía a partir del
        # movimiento 21. Solo se calcula cuando se filtra por cliente.
        client_total_cents=pay_svc.neto_de_cliente(db, client_id) if client_id else None,
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

    # El CSV de la gestoría es el de la marca ACTIVA: cada negocio lleva su
    # libro. Con un solo perfil de marca el filtro no existe y sale todo.
    _marca = pay_svc.filtro_de_marca(db)
    _q = (select(Payment, Client.full_name)
          .outerjoin(Client, Client.id == Payment.client_id)
          .order_by(Payment.paid_at.desc()))
    if _marca is not None:
        _q = _q.where(_marca)
    filas = db.execute(_q).all()
    tz = ZoneInfo(cfg.tz)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Fecha", "Hora", "Cliente", "Email", "Concepto", "Tipo", "Estado",
                "Importe (€)", "Comisión Stripe (€)", "Neto (€)", "Moneda",
                "Modo", "ID de Stripe"])
    estados = {"paid": "Cobrado", "failed": "Fallido", "refunded": "Devolución",
               "canceled": "Baja"}
    tipos = {"checkout": "Pago único", "invoice": "Suscripción",
             "refund": "Devolución", "subscription": "Suscripción",
             "manual": "Cobro a mano", "dispute": "Contracargo"}
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
        headers={"Content-Disposition":
                 f'attachment; filename="pagos_{_slug_marca(db)}.csv"'},
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


class HuerfanoIn(BaseModel):
    """`client_id` a quién pertenece el cobro; sin él, se declara ajeno."""

    client_id: int | None = None


@router.post("/{payment_id}/resolver", response_model=PaymentOut)
def resolver_huerfano(payment_id: int, body: HuerfanoIn | None = None,
                      db: Session = Depends(get_db)) -> PaymentOut:
    """Le da salida a un cobro SIN FICHA: se asigna a un cliente, o se declara
    ajeno a la asesoría y deja de contar en el aviso "N sin ficha".

    Ese aviso no tenía forma de apagarse: `adopt_orphans` solo reasocia por
    email y dentro de 30 días, así que un cobro de otro producto de la cuenta
    —o uno con el email mal escrito en el checkout— contaba para siempre. Un
    aviso que no se puede resolver se acaba ignorando, y con él los que sí."""
    try:
        pago = pay_svc.resolver_huerfano(
            db, payment_id, client_id=(body.client_id if body else None))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    log_event(db, "payment", pago.id, "orphan_resolved",
              {"client_id": pago.client_id})
    db.commit()
    nombres = {}
    if pago.client_id:
        cliente = db.get(Client, pago.client_id)
        if cliente is not None:
            nombres[cliente.id] = cliente.full_name
    return _to_out(pago, nombres)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_cobro_manual(payment_id: int, db: Session = Depends(get_db)) -> Response:
    """Borra un cobro anotado A MANO (solo esos: lo de Stripe es el extracto).

    Un 1290 tecleado en vez de 129 entraba en el total del mes, en la gráfica,
    en el CSV de la gestoría y reescribía la ventana de renovación… y no había
    NINGÚN camino en la web para arreglarlo. Al borrarlo, la ficha vuelve a
    apuntar al cobro anterior del cliente.
    """
    from app.models import Payment

    pago = db.get(Payment, payment_id)
    if pago is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cobro no encontrado")
    if pago.kind != "manual":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Solo se pueden borrar los cobros anotados a mano: los de Stripe "
            "son el extracto real de la pasarela.")
    client_id = pago.client_id
    db.delete(pago)
    db.flush()
    # La ficha se recalcula con lo que QUEDA: si se borra el último cobro, el
    # cliente no puede quedarse con esa fecha de pago fantasma.
    if client_id:
        cliente = db.get(Client, client_id)
        if cliente is not None:
            # Los cobros de Stripe se enlazan por EMAIL, y si el cliente pagó
            # con otro correo su fila queda sin ficha: mirando solo client_id,
            # borrar un cobro a mano marcaba como IMPAGADO a alguien que sí
            # había pagado (y le reabría el aviso de pago y el banner del
            # portal). Se mira también por su email, igual que la pasarela.
            email = (cliente.email or "").strip().lower()
            suyos = [Payment.client_id == client_id]
            if email:
                suyos.append(func.lower(Payment.customer_email) == email)
            ultimo = db.scalar(
                select(Payment).where(Payment.status == "paid", or_(*suyos))
                .order_by(Payment.paid_at.desc().nullslast()).limit(1))
            cliente.paid_at = ultimo.paid_at if ultimo else None
            # Una suscripción viva de Stripe manda sobre la ausencia de filas:
            # el cobro está domiciliado aunque el libro aún no lo tenga.
            if ultimo is None and not cliente.stripe_subscription_id:
                cliente.payment_status = "pending"
    log_event(db, "client", client_id or 0, "manual_payment_deleted",
              {"payment_id": payment_id, "amount_cents": pago.amount_cents})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/manual", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def manual_payment(body: ManualPaymentIn, db: Session = Depends(get_db)) -> PaymentOut:
    """Anota un cobro que NO pasó por Stripe y actualiza la ficha del cliente.

    Sin esto el libro de caja solo contaba la pasarela y el total del mes mentía
    en cuanto el cliente pagaba en efectivo o por transferencia.
    """
    client = db.get(Client, body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # Fecha futura: el cobro desaparecería del mes y congelaría la renovación.
    hoy = pay_svc.hoy_local()
    if body.paid_on and body.paid_on > hoy:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Esa fecha aún no ha llegado: anota el cobro el día que lo recibas.")

    importe = int(round(body.amount_eur * 100))
    ya_estaba = pay_svc.existe_cobro_manual(
        db, client_id=client.id, paid_on=body.paid_on or hoy,
        amount_cents=importe, method=body.method, note=body.note)
    if ya_estaba:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya hay un cobro igual de este cliente ese día (mismo importe y "
            "método). Si de verdad son dos, añádele una nota que los distinga.")

    pago = pay_svc.record_manual_payment(
        db, client=client, amount_cents=importe,
        method=body.method, paid_on=body.paid_on, note=body.note,
    )
    if pago is None:
        # Aquí ya NO puede ser un duplicado (se comprobó arriba): es un fallo
        # real de la base de datos y decir "ya estaba anotado" haría que el
        # coach diera por bueno un cobro que no se guardó.
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "No se pudo anotar el cobro. Vuelve a intentarlo.")

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
