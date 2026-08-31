"""Regresiones de la tanda 2 de la auditoría: pagos, libro de caja y altas.

Cada test fija un fallo REAL verificado sobre el código: si vuelve, lo caza.
"""
import uuid
import warnings
from datetime import datetime, timedelta, timezone

import pytest

warnings.filterwarnings("ignore")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


def _cargo(cargo_id: str, *, total: int, pi: str, refunds: list[dict] | None = None) -> dict:
    """Payload de un cargo de Stripe con (o sin) el desglose de devoluciones."""
    creado = int((datetime.now(timezone.utc) - timedelta(days=120)).timestamp())
    d = {
        "id": cargo_id, "amount_refunded": total, "currency": "eur",
        "livemode": True, "created": creado, "payment_intent": pi,
        "billing_details": {"email": None, "name": "Quien Sea"},
    }
    if refunds is not None:
        d["refunds"] = {"data": refunds}
    return d


def test_el_desglose_no_duplica_la_fila_de_diferencia():
    """El mismo dinero se restaba DOS veces: una carga sin desglose anotaba la
    fila sintética "…_difN" y, cuando después llegaba el desglose real, los
    re_… se insertaban encima (el guard solo miraba la fila con el id del
    cargo). 150 € devueltos pasaban a restar 250 € del mes y del CSV."""
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Payment
    from app.services import payments as pay

    uid = uuid.uuid4().hex[:8]
    ch, pi = f"ch_dup_{uid}", f"pi_dup_{uid}"
    re1, re2 = f"re_a_{uid}", f"re_b_{uid}"
    with SessionLocal() as db:
        # 1) Webhook CON desglose: una devolución parcial de 100 €.
        pay.record_refunds_of_charge(
            db, _cargo(ch, total=10000, pi=pi,
                       refunds=[{"id": re1, "amount": 10000, "created": None}]))
        db.commit()
        # 2) Sincronización SIN desglose con 150 € acumulados → fila diferencia.
        pay.record_refunds_of_charge(db, _cargo(ch, total=15000, pi=pi), seen_by_age=True)
        db.commit()
        devuelto = lambda: int(db.scalar(  # noqa: E731
            select(func.coalesce(func.sum(Payment.amount_cents), 0))
            .where(Payment.payment_intent == pi, Payment.status == "refunded")) or 0)
        assert devuelto() == 15000, "la diferencia debe cuadrar el acumulado"

        # 3) Ahora llega el desglose ENTERO: sustituye a la fila sintética.
        pay.record_refunds_of_charge(
            db, _cargo(ch, total=15000, pi=pi, refunds=[
                {"id": re1, "amount": 10000, "created": None},
                {"id": re2, "amount": 5000, "created": None}]))
        db.commit()
        assert devuelto() == 15000, "el desglose no puede volver a restar lo mismo"

        for p in db.scalars(select(Payment).where(Payment.payment_intent == pi)):
            db.delete(p)
        db.commit()


def test_una_devolucion_nueva_no_entra_ya_leida():
    """Una devolución de ayer sobre un cobro de hace meses entraba "vista" (se
    juzgaba por la fecha del CARGO) y el badge no avisaba: dinero que se va sin
    que nadie se entere."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Payment
    from app.services import payments as pay

    uid = uuid.uuid4().hex[:8]
    ch, pi = f"ch_seen_{uid}", f"pi_seen_{uid}"
    with SessionLocal() as db:
        pay.record_refunds_of_charge(
            db, _cargo(ch, total=5000, pi=pi,
                       refunds=[{"id": f"re_s_{uid}", "amount": 5000, "created": None}]),
            seen=True, seen_by_age=True)
        db.commit()
        # Devuelven MÁS después, y la carga ya no trae desglose.
        pay.record_refunds_of_charge(db, _cargo(ch, total=9000, pi=pi),
                                     seen=True, seen_by_age=True)
        db.commit()
        nuevas = list(db.scalars(select(Payment).where(
            Payment.payment_intent == pi, Payment.status == "refunded",
            Payment.seen_at.is_(None))))
        assert nuevas, "la devolución posterior tiene que quedar SIN LEER"
        for p in db.scalars(select(Payment).where(Payment.payment_intent == pi)):
            db.delete(p)
        db.commit()


def test_borrar_un_cobro_a_mano_no_marca_impagado_a_quien_pago():
    """El recálculo solo miraba las filas con `client_id`: los cobros de Stripe
    se enlazan por EMAIL, así que borrar un apunte a mano dejaba en "pago
    pendiente" a un cliente que sí había pagado por la pasarela."""
    from app.db import SessionLocal
    from app.models import Client, Payment
    from app.security import new_portal_token
    from app.services import payments as pay

    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        c = Client(full_name=f"Pagador {uid}", email=f"pagador-{uid}@test.local",
                   portal_token="p", status="active", payment_status="paid",
                   paid_at=datetime.now(timezone.utc))
        db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
        # Cobro de Stripe SIN ficha enlazada (llegó con otro correo de facturación).
        stripe_pago = pay.record_payment(
            db, object_id=f"ch_mail_{uid}", kind="charge", status="paid",
            amount_cents=12900, livemode=True, client=None,
            customer_email=c.email, paid_at=datetime.now(timezone.utc) - timedelta(days=2))
        manual = pay.record_payment(
            db, object_id=f"man_{uid}", kind="manual", status="paid",
            amount_cents=1000, livemode=True, client=c,
            paid_at=datetime.now(timezone.utc))
        db.commit()
        cid, mid, sid = c.id, manual.id, stripe_pago.id

    from fastapi.testclient import TestClient

    from app.main import app
    from app.security import create_access_token
    import os

    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    with TestClient(app) as http:
        assert http.delete(f"/api/payments/{mid}", headers=auth).status_code == 204

    with SessionLocal() as db:
        ficha = db.get(Client, cid)
        assert ficha.payment_status == "paid", "pagó por Stripe: no puede quedar impagado"
        assert ficha.paid_at is not None
        for p in (db.get(Payment, sid),):
            if p is not None:
                db.delete(p)
        db.delete(ficha)
        db.commit()


def test_el_total_del_cliente_no_sale_de_la_pagina_ni_cuenta_pruebas():
    """La ficha sumaba los 20 movimientos que pintaba (y el dinero de prueba):
    a partir del movimiento 21 el total era falso."""
    from app.db import SessionLocal
    from app.models import Client, Payment
    from app.security import new_portal_token
    from app.services import payments as pay

    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        c = Client(full_name=f"Muchos {uid}", email=f"muchos-{uid}@test.local",
                   portal_token="p", status="active")
        db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
        for i in range(25):
            pay.record_payment(db, object_id=f"ch_{uid}_{i}", kind="charge",
                               status="paid", amount_cents=1000, livemode=True,
                               client=c, paid_at=datetime.now(timezone.utc))
        # Dinero de PRUEBA: se ve en el feed, pero no es un ingreso.
        pay.record_payment(db, object_id=f"test_{uid}", kind="charge", status="paid",
                           amount_cents=99900, livemode=False, client=c,
                           paid_at=datetime.now(timezone.utc))
        # Una devolución resta.
        pay.record_payment(db, object_id=f"re_{uid}", kind="refund", status="refunded",
                           amount_cents=1000, livemode=True, client=c,
                           paid_at=datetime.now(timezone.utc))
        db.commit()
        cid = c.id
        assert pay.neto_de_cliente(db, cid) == 24000  # 25×10 € − 10 €, sin pruebas

        for p in db.scalars(
            __import__("sqlalchemy").select(Payment).where(Payment.client_id == cid)
        ):
            db.delete(p)
        db.delete(db.get(Client, cid))
        db.commit()
