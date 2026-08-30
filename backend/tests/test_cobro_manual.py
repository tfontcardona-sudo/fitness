"""Cobros FUERA de Stripe (efectivo, transferencia, Bizum).

El libro de caja tiene que contar TODO el dinero de la asesoría: si solo
contase la pasarela, el total del mes mentiría en cuanto un cliente paga por
otra vía. Requiere PostgreSQL (se salta sin él).
"""
import uuid
from datetime import date, datetime, timezone

import pytest


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seeds.run import main as seed_main

    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


def _nuevo_cliente(client, auth) -> int:
    r = client.post("/api/clients", headers=auth, json={
        "full_name": "Cobro Manual", "email": f"cobro-{uuid.uuid4().hex[:8]}@example.com",
        "billing_period": "3m",
    })
    assert r.status_code == 201, r.text
    return r.json()["client"]["id"]


def test_cobro_manual_suma_en_el_total_del_mes(client, auth):
    antes = client.get("/api/payments/summary", headers=auth).json()["month_total_cents"]
    cid = _nuevo_cliente(client, auth)

    r = client.post("/api/payments/manual", headers=auth, json={
        "client_id": cid, "amount_eur": 129.5, "method": "transferencia",
    })
    assert r.status_code == 201, r.text
    assert r.json()["amount_cents"] == 12950      # euros → céntimos, sin perder el decimal

    despues = client.get("/api/payments/summary", headers=auth).json()["month_total_cents"]
    assert despues - antes == 12950

    # Sale en el feed como un movimiento más, con su método a la vista.
    feed = client.get("/api/payments?limit=50", headers=auth).json()["items"]
    mio = next(p for p in feed if p["client_id"] == cid)
    assert mio["status"] == "paid" and "Transferencia" in (mio["description"] or "")

    # …y la ficha queda pagada, que es lo que apaga la alerta de "falta pago".
    ficha = client.get(f"/api/clients/{cid}", headers=auth).json()
    assert ficha["payment_status"] == "paid" and ficha["paid_at"]


def test_cobro_manual_usa_la_fecha_del_cobro_no_la_de_registro(client, auth):
    """Un cobro apuntado con retraso cuenta en el mes en que se cobró."""
    from app.db import SessionLocal
    from app.models import Payment
    from sqlalchemy import select

    cid = _nuevo_cliente(client, auth)
    ayer = date(2026, 7, 3)
    r = client.post("/api/payments/manual", headers=auth, json={
        "client_id": cid, "amount_eur": 60, "method": "efectivo",
        "paid_on": ayer.isoformat(),
    })
    assert r.status_code == 201, r.text
    with SessionLocal() as db:
        fila = db.scalar(select(Payment).where(Payment.client_id == cid))
        assert fila.paid_at.date() == ayer
        assert fila.kind == "manual" and fila.livemode is True
        # Lo apunta el coach: no puede aparecerle como "sin leer".
        assert fila.seen_at is not None


def test_cobro_manual_rechaza_importes_invalidos(client, auth):
    cid = _nuevo_cliente(client, auth)
    for importe in (0, -10):
        r = client.post("/api/payments/manual", headers=auth,
                        json={"client_id": cid, "amount_eur": importe})
        assert r.status_code == 422
    # Cliente inexistente: 404, no un 500 ni una fila huérfana.
    r = client.post("/api/payments/manual", headers=auth,
                    json={"client_id": 99999999, "amount_eur": 50})
    assert r.status_code == 404


def test_renovacion_avisa_con_cinco_dias(client, auth):
    """El dueño avisa 5 días antes de que venza el ciclo pagado."""
    from types import SimpleNamespace

    from app.services import renewals

    assert renewals.RENEWAL_WARN_DAYS == 5
    hoy = date(2026, 8, 21)
    # Mensual pagado hace 26 días → vence en 4: entra en la ventana.
    c = SimpleNamespace(payment_status="paid", stripe_subscription_id=None,
                        paid_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
                        billing_period="1m")
    assert renewals.is_due(c, hoy) is True
    # Hace 20 días → quedan 10: todavía no molesta al cliente.
    c.paid_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert renewals.is_due(c, hoy) is False


def test_el_doble_clic_no_duplica_el_cobro(client, auth):
    """El id llevaba el segundo actual, así que solo protegía si los dos envíos
    caían dentro del MISMO segundo — justo lo que no pasa con un doble clic."""
    cid = _nuevo_cliente(client, auth)
    cuerpo = {"client_id": cid, "amount_eur": 129.0, "method": "bizum"}
    r1 = client.post("/api/payments/manual", json=cuerpo, headers=auth)
    assert r1.status_code == 201, r1.text
    r2 = client.post("/api/payments/manual", json=cuerpo, headers=auth)
    assert r2.status_code == 409, "el segundo envío duplicó el ingreso"
    assert "nota" in r2.json()["detail"].lower(), "el 409 no dice cómo distinguirlos"

    # Con una nota distinta SÍ son dos cobros (pueden serlo de verdad).
    r3 = client.post("/api/payments/manual",
                     json={**cuerpo, "note": "segunda mensualidad"}, headers=auth)
    assert r3.status_code == 201, r3.text


def test_no_se_puede_anotar_un_cobro_del_futuro(client, auth):
    """Con una fecha futura el cobro desaparecía del mes y congelaba el ciclo
    de renovación."""
    from datetime import date, timedelta

    cid = _nuevo_cliente(client, auth)
    manana = (date.today() + timedelta(days=2)).isoformat()
    r = client.post("/api/payments/manual",
                    json={"client_id": cid, "amount_eur": 50.0, "method": "efectivo",
                          "paid_on": manana},
                    headers=auth)
    assert r.status_code == 400, r.text


def test_la_renovacion_pagada_en_mano_tambien_se_puede_anotar(client, auth):
    """El formulario solo salía si el cliente estaba «pendiente», que es justo
    lo que un cliente ya pagado NO es: no había forma de anotar su renovación."""
    cid = _nuevo_cliente(client, auth)
    r1 = client.post("/api/payments/manual",
                     json={"client_id": cid, "amount_eur": 129.0, "method": "efectivo"},
                     headers=auth)
    assert r1.status_code == 201
    # Ya está "paid"; el segundo cobro (otro importe) debe entrar igual.
    r2 = client.post("/api/payments/manual",
                     json={"client_id": cid, "amount_eur": 99.0, "method": "efectivo"},
                     headers=auth)
    assert r2.status_code == 201, r2.text


def test_un_cobro_a_mano_mal_tecleado_se_puede_borrar(client, auth):
    """1290 € en vez de 129 entraba en el total del mes, en la gráfica, en el
    CSV de la gestoría y movía la ventana de renovación… y no había NINGÚN
    camino en la web para arreglarlo. Los de Stripe, en cambio, son el extracto
    real de la pasarela: esos no se tocan."""
    from datetime import datetime, timezone

    from app.db import SessionLocal
    from app.models import Client, Payment
    from app.services import payments as pay_svc

    cid = _nuevo_cliente(client, auth)
    r = client.post("/api/payments/manual", headers=auth, json={
        "client_id": cid, "amount_eur": 1290.0, "method": "transferencia",
    })
    assert r.status_code == 201, r.text
    pago_id = r.json()["id"]

    with SessionLocal() as db:
        cliente = db.get(Client, cid)
        assert cliente.payment_status == "paid"
        de_stripe = pay_svc.record_payment(
            db, object_id=f"ch_no_borrar_{uuid.uuid4().hex[:8]}", kind="charge",
            status="paid", amount_cents=12900, livemode=False, client=cliente,
            paid_at=datetime.now(timezone.utc))
        db.commit()
        stripe_id = de_stripe.id

    # Uno de Stripe NO se puede borrar.
    assert client.delete(f"/api/payments/{stripe_id}", headers=auth).status_code == 409
    # El de a mano sí.
    assert client.delete(f"/api/payments/{pago_id}", headers=auth).status_code == 204

    with SessionLocal() as db:
        assert db.get(Payment, pago_id) is None
        ficha = db.get(Client, cid)
        # La ficha vuelve a apuntar al cobro que QUEDA, no a una fecha fantasma.
        assert ficha.payment_status == "paid" and ficha.paid_at is not None
