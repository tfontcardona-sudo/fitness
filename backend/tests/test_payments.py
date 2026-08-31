"""Tests del LIBRO DE CAJA de Stripe (tabla `payments`) y su feed en el panel.

Cubren lo que el coach ve en /pagos: quién pagó, cuánto y cuándo, con lo no
leído marcado. Stripe está simulado (nunca se llama a la API real): se sustituye
`stripe_service._stripe` por un módulo falso, igual que en test_stripe.py.

Requiere PostgreSQL.
"""
from __future__ import annotations

import os
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


# ------------------------------------------------------------- utilidades ----

def _fake_stripe(event: dict):
    class _Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return event

    class _Stripe:
        Webhook = _Webhook

    return lambda: _Stripe


def _prep(monkeypatch):
    from app.config import settings
    from app.services import stripe_service

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "emails_enabled", False)
    return stripe_service


def _nuevo_cliente(db, *, pagado: bool = False, email: str | None = None):
    from app.models import Client
    from app.security import new_portal_token

    uid = uuid.uuid4().hex[:8]
    c = Client(
        full_name=f"Pago {uid}", email=email or f"pago-{uid}@x.com",
        package_tier="full", billing_period="1m", status="onboarding",
        portal_token="p", payment_status="paid" if pagado else "pending",
        paid_at=datetime.now(timezone.utc) - timedelta(days=40) if pagado else None,
    )
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _sesion(**extra) -> dict:
    """Checkout Session de Stripe con lo que trae de verdad un pago único."""
    base = {
        "id": f"cs_test_{uuid.uuid4().hex[:12]}",
        "mode": "payment",
        "payment_status": "paid",
        "amount_total": 12900,
        "currency": "eur",
        "livemode": True,
        "created": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "customer_details": {"email": "quien@x.com", "name": "Quien Paga"},
        "metadata": {"tier": "full", "billing_period": "1m"},
    }
    base.update(extra)
    return base


def _evento(tipo: str, obj: dict) -> dict:
    return {"id": f"evt_{uuid.uuid4().hex[:12]}", "type": tipo, "data": {"object": obj}}


def _pagos_de(db, object_id: str) -> list:
    from sqlalchemy import select

    from app.models import Payment

    return list(db.scalars(select(Payment).where(Payment.stripe_object_id == object_id)))


# --------------------------------------------------- anotación del webhook ----

def test_checkout_anota_el_movimiento_con_importe_y_fecha_de_stripe(monkeypatch):
    """El bug de origen: un cobro solo dejaba payment_status='paid' y una traza
    SIN importe. Ahora el libro guarda cuánto y cuándo, con el dato de Stripe."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        ses = _sesion(metadata={"client_id": str(c.id), "tier": "full",
                                "billing_period": "3m"}, amount_total=33000)
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"marked_paid": c.id}

        db.expire_all()
        pagos = _pagos_de(db, ses["id"])
        assert len(pagos) == 1
        p = pagos[0]
        assert p.amount_cents == 33000 and p.currency == "eur"
        assert p.status == "paid" and p.kind == "checkout"
        assert p.client_id == c.id
        assert p.billing_period == "3m"
        # Fecha REAL del cobro (la de Stripe), no la de recepción del webhook.
        assert abs((p.paid_at - datetime.fromtimestamp(ses["created"], tz=timezone.utc))
                   .total_seconds()) < 2
        # Sin leer: es lo que enciende el badge del panel.
        assert p.seen_at is None
    finally:
        db.close()


def test_reentrega_del_mismo_checkout_no_duplica_el_movimiento(monkeypatch):
    """REGRESIÓN: Stripe reenvía el mismo evento si tarda la respuesta. El
    ingreso no puede contarse dos veces en el libro."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        ses = _sesion(metadata={"client_id": str(c.id), "tier": "full",
                                "billing_period": "1m"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        stripe_service.handle_webhook(db, b"{}", "sig")
        stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        assert len(_pagos_de(db, ses["id"])) == 1
    finally:
        db.close()


def test_renovacion_de_pago_unico_deja_rastro(monkeypatch):
    """REGRESIÓN (auditoría del libro de caja): `_mark_paid` solo escribía si
    había transición pending→paid, así que la RENOVACIÓN de un cliente que ya
    constaba pagado no dejaba traza, ni aviso, ni refrescaba `paid_at` (la
    alerta de renovación seguía contando desde el primer pago para siempre)."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db, pagado=True)
        antiguo = c.paid_at
        avisos = []
        monkeypatch.setattr(stripe_service, "_notify_coach_payment",
                            lambda db_, cl, **kw: avisos.append(kw))

        ses = _sesion(metadata={"client_id": str(c.id), "tier": "full",
                                "billing_period": "1m"}, amount_total=12900)
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        assert len(_pagos_de(db, ses["id"])) == 1          # queda anotada
        assert len(avisos) == 1                            # y el coach se entera
        assert avisos[0]["amount_cents"] == 12900
        from app.models import Client

        assert db.get(Client, c.id).paid_at > antiguo      # contador reiniciado
    finally:
        db.close()


def test_pago_huerfano_se_anota_sin_cliente(monkeypatch):
    """El dinero entró aunque no haya ficha (borrada entre el alta y el cobro):
    antes solo salía un push efímero; ahora se VE en el feed."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        ses = _sesion(metadata={"client_id": "99999999", "tier": "full",
                                "billing_period": "1m"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res["error"] == "client_not_found"

        db.expire_all()
        pagos = _pagos_de(db, ses["id"])
        assert len(pagos) == 1
        assert pagos[0].client_id is None
        # El pagador queda identificado por lo que dio Stripe.
        assert pagos[0].customer_email == "quien@x.com"
    finally:
        db.close()


def test_checkout_de_suscripcion_no_duplica_el_ingreso(monkeypatch):
    """La oferta cobra por FACTURA (invoice.paid). Si además se anotara la
    sesión de checkout, el primer mes contaría dos veces en los ingresos."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        ses = _sesion(mode="subscription", amount_total=100,
                      metadata={"client_id": str(c.id), "tier": "full",
                                "billing_period": "oferta"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        assert _pagos_de(db, ses["id"]) == []
    finally:
        db.close()


def test_factura_fallida_y_pagada_conviven_como_dos_movimientos(monkeypatch):
    """Una factura puede fallar y cobrarse después: son DOS movimientos de la
    misma factura y el feed tiene que enseñar los dos (el UNIQUE es
    objeto+estado, no solo objeto)."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        c.billing_period = "oferta"
        db.commit()
        inv_id = f"in_test_{uuid.uuid4().hex[:10]}"
        factura = {
            "id": inv_id, "currency": "eur", "livemode": True,
            "amount_paid": 12000, "amount_due": 12000,
            "billing_reason": "subscription_cycle",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "customer_email": c.email,
            "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
            "subscription_details": {"metadata": {"client_id": str(c.id)}},
        }
        monkeypatch.setattr(stripe_service, "_notify_coach_payment_failed",
                            lambda *a, **k: None)
        monkeypatch.setattr(stripe_service, "_notify_coach_payment", lambda *a, **k: None)

        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("invoice.payment_failed", factura)))
        stripe_service.handle_webhook(db, b"{}", "sig")
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("invoice.paid", factura)))
        stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        estados = sorted(p.status for p in _pagos_de(db, inv_id))
        assert estados == ["failed", "paid"]
    finally:
        db.close()


def test_devolucion_se_anota_y_resta_de_los_ingresos(monkeypatch):
    """Sin `charge.refunded`, un reembolso dejaba el saldo del mes inflado: el
    feed enseñaba un ingreso que ya no existía."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        antes = pay_svc.summary(db)["month_total_cents"]
        ahora = int(datetime.now(timezone.utc).timestamp())
        cargo = {
            "id": f"ch_test_{uuid.uuid4().hex[:10]}", "currency": "eur",
            "livemode": True, "amount": 12900, "amount_refunded": 5000,
            "created": ahora, "billing_details": {"email": c.email, "name": c.full_name},
            "refunds": {"data": [{"created": ahora}]},
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.refunded", cargo)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res["refunded"] == 5000 and res["client_id"] == c.id

        db.expire_all()
        pagos = _pagos_de(db, cargo["id"])
        assert len(pagos) == 1 and pagos[0].status == "refunded"
        # La devolución RESTA en el total del mes.
        assert pay_svc.summary(db)["month_total_cents"] == antes - 5000
    finally:
        db.close()


def test_modo_prueba_no_suma_en_los_totales():
    """Un cobro de sk_test_ no es dinero real: se ve en el feed, pero el total
    del mes no puede contarlo."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        antes = pay_svc.summary(db)["month_total_cents"]
        pay_svc.record_payment(
            db, object_id=f"cs_prueba_{uuid.uuid4().hex[:10]}", kind="checkout",
            status="paid", amount_cents=9900, livemode=False,
            customer_email=f"prueba-{uuid.uuid4().hex[:8]}@x.com",
            paid_at=datetime.now(timezone.utc))
        db.commit()
        assert pay_svc.summary(db)["month_total_cents"] == antes
        assert pay_svc.summary(db)["test_count"] >= 1
    finally:
        db.close()


def test_borrado_rgpd_anonimiza_el_movimiento_sin_borrarlo():
    """El libro de caja no puede perder dinero porque alguien se dé de baja,
    pero tampoco puede conservar sus datos personales: la fila se queda sin
    ficha, sin nombre y sin email."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Payment
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        obj = f"cs_rgpd_{uuid.uuid4().hex[:10]}"
        pay_svc.record_payment(
            db, object_id=obj, kind="checkout", status="paid", amount_cents=7900,
            client=c, customer_name=c.full_name, customer_email=c.email,
            paid_at=datetime.now(timezone.utc))
        db.commit()

        pay_svc.anonymize_client(db, c.id)
        db.commit()
        db.expire_all()
        p = db.scalar(select(Payment).where(Payment.stripe_object_id == obj))
        assert p is not None and p.amount_cents == 7900   # el dinero sigue
        assert p.client_id is None and p.customer_name is None and p.customer_email is None
        # Esta fila se limpia AQUÍ: al anonimizarla se queda sin cliente y sin
        # email, así que la limpieza de conftest (que busca por esos dos campos)
        # ya no puede reconocerla como sintética.
        db.delete(p)
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------- feed (API) ----

@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


def test_feed_lista_marca_leido_y_apaga_el_badge(http):
    """El ciclo completo de la pantalla: llega un cobro sin leer, se lista, se
    sella al abrir y el badge se queda a cero (como la app del banco)."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        obj = f"cs_feed_{uuid.uuid4().hex[:10]}"
        pay_svc.record_payment(
            db, object_id=obj, kind="checkout", status="paid", amount_cents=12900,
            customer_name="Feed Cliente", customer_email="feed@x.com",
            description="DQR Full · 1 mes", paid_at=datetime.now(timezone.utc))
        db.commit()
    finally:
        db.close()

    auth = _auth()
    r = http.get("/api/payments?limit=100", headers=auth)
    assert r.status_code == 200, r.text
    datos = r.json()
    fila = next((i for i in datos["items"] if i["stripe_object_id"] == obj), None)
    assert fila is not None
    assert fila["amount_cents"] == 12900
    assert fila["display_name"] == "Feed Cliente"   # sin ficha, el nombre de Stripe
    assert datos["unseen"] >= 1

    assert http.post("/api/payments/seen", headers=auth).json()["unseen"] == 0
    assert http.get("/api/payments/summary", headers=auth).json()["unseen"] == 0


def test_feed_exige_sesion_de_coach(http):
    """Los cobros son datos sensibles: sin JWT, nada."""
    assert http.get("/api/payments").status_code in (401, 403)
    assert http.get("/api/payments/summary").status_code in (401, 403)


def test_filtro_por_estado_del_feed(http):
    """Los chips de la pantalla (Cobrados / Fallidos / Devoluciones) filtran de
    verdad en el servidor, no solo en pantalla."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        obj = f"in_fallo_{uuid.uuid4().hex[:10]}"
        pay_svc.record_payment(
            db, object_id=obj, kind="invoice", status="failed", amount_cents=12000,
            customer_name="Impago Test", customer_email=f"impago-{uuid.uuid4().hex[:8]}@x.com",
            paid_at=datetime.now(timezone.utc))
        db.commit()
    finally:
        db.close()

    r = http.get("/api/payments?status=failed&limit=100", headers=_auth())
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(i["status"] == "failed" for i in items)
    assert any(i["stripe_object_id"] == obj for i in items)


# ------------------- regresiones de la revisión adversarial ------------------

def test_devoluciones_parciales_sucesivas_se_suman(monkeypatch):
    """REGRESIÓN (revisión adversarial): `charge.amount_refunded` es ACUMULADO y
    Stripe avisa en CADA devolución. Con el id del CARGO como clave, la segunda
    parcial se descartaba entera por idempotencia y el libro se quedaba corto
    (30 € devueltos de 80 € reales). Ahora cada reembolso es su movimiento."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        antes = pay_svc.summary(db)["month_total_cents"]
        ahora = int(datetime.now(timezone.utc).timestamp())
        ch_id = f"ch_test_{uuid.uuid4().hex[:10]}"
        re1 = {"id": f"re_{uuid.uuid4().hex[:10]}", "amount": 3000, "created": ahora}
        re2 = {"id": f"re_{uuid.uuid4().hex[:10]}", "amount": 5000, "created": ahora + 60}

        def cargo(refunds, acumulado):
            return {"id": ch_id, "currency": "eur", "livemode": True, "amount": 12900,
                    "amount_refunded": acumulado, "created": ahora,
                    "billing_details": {"email": c.email, "name": c.full_name},
                    "refunds": {"data": refunds}}

        for payload in (cargo([re1], 3000), cargo([re1, re2], 8000)):
            monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
                _evento("charge.refunded", payload)))
            stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        assert pay_svc.summary(db)["month_total_cents"] == antes - 8000
    finally:
        db.close()


def test_una_devolucion_no_puede_restar_dos_veces(monkeypatch):
    """REGRESIÓN: el webhook anota los `re_…` y después la sincronización trae
    el mismo cargo SIN el desglose (con las versiones nuevas de la API,
    `charge.refunds` ya no viene por defecto).

    Sin el guard simétrico se insertaba además la fila agregada del cargo y los
    129 € devueltos restaban 258 € del mes, de la gráfica y del CSV.
    """
    _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        antes = pay_svc.summary(db)["month_total_cents"]
        ahora = int(datetime.now(timezone.utc).timestamp())
        ch_id = f"ch_test_{uuid.uuid4().hex[:10]}"
        pi_id = f"pi_test_{uuid.uuid4().hex[:10]}"
        base = {"id": ch_id, "currency": "eur", "livemode": True, "amount": 12900,
                "created": ahora, "payment_intent": pi_id,
                "billing_details": {"email": c.email, "name": c.full_name}}

        # 1) Webhook CON desglose → una fila re_…
        con_desglose = {**base, "amount_refunded": 12900, "refunds": {"data": [
            {"id": f"re_{uuid.uuid4().hex[:10]}", "amount": 12900, "created": ahora}]}}
        assert pay_svc.record_refunds_of_charge(db, con_desglose, client=c) == 1
        db.commit()

        # 2) Sincronización del MISMO cargo, ya sin `refunds`
        sin_desglose = {**base, "amount_refunded": 12900}
        assert pay_svc.record_refunds_of_charge(db, sin_desglose, client=c) == 0
        db.commit()

        db.expire_all()
        assert pay_svc.summary(db)["month_total_cents"] == antes - 12900

        # 3) Y si de verdad han devuelto MÁS, se anota solo la diferencia.
        mas = {**base, "amount_refunded": 15000}
        assert pay_svc.record_refunds_of_charge(db, mas, client=c) == 1
        db.commit()
        db.expire_all()
        assert pay_svc.summary(db)["month_total_cents"] == antes - 15000
    finally:
        db.close()


def test_devolucion_de_un_cobro_ajeno_no_resta(monkeypatch):
    """REGRESIÓN (revisión adversarial): una factura ajena de la misma cuenta de
    Stripe (un taller, otro producto) NO se anota como ingreso, así que su
    devolución tampoco puede restar — el libro enseñaría un −300 € de algo que
    nunca sumó."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        antes = pay_svc.summary(db)["month_total_cents"]
        cargo = {
            "id": f"ch_ajeno_{uuid.uuid4().hex[:10]}", "currency": "eur",
            "livemode": True, "amount": 30000, "amount_refunded": 30000,
            "created": int(datetime.now(timezone.utc).timestamp()),
            # Ni ficha (email desconocido) ni factura nuestra anotada.
            "billing_details": {"email": f"taller-{uuid.uuid4().hex[:6]}@otracosa.com"},
            "invoice": f"in_ajena_{uuid.uuid4().hex[:8]}",
            "refunds": {"data": []},
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.refunded", cargo)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"ignored": "cargo_ajeno"}

        db.expire_all()
        assert _pagos_de(db, cargo["id"]) == []
        assert pay_svc.summary(db)["month_total_cents"] == antes
    finally:
        db.close()


def test_factura_fallida_antigua_conserva_el_movimiento(monkeypatch):
    """REGRESIÓN (revisión adversarial): en la rama del impago REZAGADO se salía
    con `return` sin `db.commit()`, así que el movimiento anotado se perdía al
    cerrar la sesión (el intento fallido desaparecía del libro)."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db, pagado=True)
        c.paid_at = datetime.now(timezone.utc)     # cobro POSTERIOR al fallo
        c.billing_period = "oferta"
        db.commit()
        inv_id = f"in_rezag_{uuid.uuid4().hex[:10]}"
        factura = {
            "id": inv_id, "currency": "eur", "livemode": True, "amount_due": 12000,
            "amount_paid": 0, "billing_reason": "subscription_cycle",
            "created": int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp()),
            "customer_email": c.email,
            "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
            "subscription_details": {"metadata": {"client_id": str(c.id)}},
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("invoice.payment_failed", factura)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res["ignored"] == "invoice_fallida_antigua"

        db.close()
        db = SessionLocal()                        # sesión NUEVA: ¿persistió?
        assert len(_pagos_de(db, inv_id)) == 1
    finally:
        db.close()


def test_paid_at_se_refresca_aunque_el_movimiento_ya_estuviera_anotado(monkeypatch):
    """REGRESIÓN (revisión adversarial): si la sincronización anotaba el cobro
    primero, la reentrega del webhook llegaba con `movimiento_nuevo=False` y
    `paid_at` se quedaba en el pago ANTERIOR (alerta de renovación eterna).
    Ahora manda la FECHA del movimiento, no quién escribió la fila."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db, pagado=True)
        antiguo = c.paid_at
        ses = _sesion(metadata={"client_id": str(c.id), "tier": "full",
                                "billing_period": "1m"},
                      created=int(datetime.now(timezone.utc).timestamp()))
        # La sincronización se adelanta y anota el movimiento.
        pay_svc.record_payment(
            db, object_id=ses["id"], kind="checkout", status="paid",
            amount_cents=12900, client=c, customer_email=c.email,
            paid_at=datetime.fromtimestamp(ses["created"], tz=timezone.utc), seen=True)
        db.commit()

        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        stripe_service.handle_webhook(db, b"{}", "sig")

        db.expire_all()
        assert db.get(Client, c.id).paid_at > antiguo
    finally:
        db.close()


def test_sincronizacion_deja_sin_leer_lo_reciente_y_visto_lo_antiguo():
    """REGRESIÓN (revisión adversarial): la sincronización marcaba TODO como
    visto. Un cobro de hoy recuperado por sincronización significa que su
    webhook se perdió: el coach no se ha enterado y debe llegarle sin leer."""
    from app.services.payments import _visto_por_antiguedad

    ahora = datetime.now(timezone.utc)
    assert _visto_por_antiguedad(ahora) is False              # de hoy → sin leer
    assert _visto_por_antiguedad(ahora - timedelta(days=3)) is True   # histórico


def test_la_factura_huerfana_de_la_oferta_se_adopta_al_crear_la_ficha(monkeypatch):
    """REGRESIÓN (revisión adversarial): en el alta self-serve de la OFERTA,
    Stripe paga la primera factura ANTES de completar el checkout, así que el
    movimiento se anotaba sin ficha y nadie lo reasociaba: aviso "pago sin ficha
    asociada" eterno, el cobro no salía en la ficha del cliente y el borrado
    RGPD no llegaba a esa fila (dejaba su nombre y su email)."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client

    db = SessionLocal()
    try:
        email = f"oferta-{uuid.uuid4().hex[:8]}@x.com"
        inv_id = f"in_oferta_{uuid.uuid4().hex[:10]}"
        # 1) Llega la PRIMERA factura de la suscripción: aún no hay cliente.
        factura = {
            "id": inv_id, "currency": "eur", "livemode": True,
            "amount_paid": 100, "amount_due": 100,
            "billing_reason": "subscription_create",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "customer_email": email, "customer_name": "Nuevo Oferta",
            "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
            "subscription_details": {"metadata": {"billing_period": "oferta"}},
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("invoice.paid", factura)))
        assert stripe_service.handle_webhook(db, b"{}", "sig")["ignored"] == "invoice_sin_cliente"
        db.expire_all()
        assert _pagos_de(db, inv_id)[0].client_id is None       # huérfano de momento

        # 2) Llega el checkout y CREA la ficha: debe adoptar el movimiento.
        ses = _sesion(mode="subscription", amount_total=100, metadata={
            "tier": "full", "billing_period": "oferta"},
            customer_details={"email": email, "name": "Nuevo Oferta"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        cid = res.get("created") or res.get("marked_paid")
        assert cid, res

        db.expire_all()
        assert _pagos_de(db, inv_id)[0].client_id == cid
        db.query(Client).filter(Client.id == cid).count()       # la ficha existe
    finally:
        db.close()


def test_la_baja_de_suscripcion_se_ve_en_el_feed_sin_sumar(monkeypatch):
    """Petición del dueño: TODO lo que pase en Stripe debe verse en la web. La
    baja de la suscripción entra en el feed como movimiento informativo
    (importe 0, gris) sin tocar los ingresos del mes."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db, pagado=True)
        c.billing_period = "oferta"
        sub_id = f"sub_test_{uuid.uuid4().hex[:10]}"
        c.stripe_subscription_id = sub_id
        db.commit()
        antes = pay_svc.summary(db)["month_total_cents"]

        evento = {"id": f"evt_{uuid.uuid4().hex[:10]}",
                  "type": "customer.subscription.deleted",
                  "created": int(datetime.now(timezone.utc).timestamp()),
                  "data": {"object": {"id": sub_id, "livemode": True,
                                       "metadata": {"client_id": str(c.id)},
                                       "canceled_at": int(datetime.now(timezone.utc).timestamp())}}}
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(evento))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"subscription_cancelled": c.id}

        db.expire_all()
        filas = _pagos_de(db, sub_id)
        assert len(filas) == 1
        assert filas[0].status == "canceled" and filas[0].amount_cents == 0
        assert pay_svc.summary(db)["month_total_cents"] == antes  # no suma ni resta
    finally:
        db.close()


def test_serie_mensual_de_ingresos_neta_y_sin_huecos():
    """La gráfica de Pagos: cobrado − devuelto por mes natural, con CEROS en
    los meses sin movimiento (la tendencia no puede saltarse un mes malo) y
    sin contar pagos de prueba."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        ahora = datetime.now(timezone.utc)
        uid = uuid.uuid4().hex[:6]
        antes = pay_svc.monthly_series(db, months=6)
        pay_svc.record_payment(
            db, object_id=f"cs_serie_{uid}", kind="checkout", status="paid",
            amount_cents=10000, customer_email=f"serie-{uid}@x.com",
            paid_at=ahora, seen=True)
        pay_svc.record_payment(
            db, object_id=f"re_serie_{uid}", kind="refund", status="refunded",
            amount_cents=2500, customer_email=f"serie-{uid}@x.com",
            paid_at=ahora, seen=True)
        pay_svc.record_payment(  # prueba: no debe sumar
            db, object_id=f"cs_serie_test_{uid}", kind="checkout", status="paid",
            amount_cents=99999, livemode=False, customer_email=f"serie-{uid}@x.com",
            paid_at=ahora, seen=True)
        db.commit()

        serie = pay_svc.monthly_series(db, months=6)
        assert len(serie) == 6 and len(antes) == 6  # sin huecos
        assert serie[-1]["month"] == ahora.astimezone(pay_svc._tz()).strftime("%Y-%m")
        # Delta del mes actual: +100 € − 25 € = 75 €; el de PRUEBA no cuenta
        # (por delta: otros tests de la suite también anotan en este mes).
        assert serie[-1]["total_cents"] - antes[-1]["total_cents"] == 7500
    finally:
        db.close()


def test_sync_no_anota_devoluciones_de_cobros_ajenos(monkeypatch):
    """REGRESIÓN (auditoría crítica): el webhook ya filtraba las devoluciones de
    cobros AJENOS (_cargo_es_nuestro), pero la SINCRONIZACIÓN las anotaba igual
    — reintroducía el bug por la puerta de atrás y restaba dinero que nunca
    sumó."""
    from app.config import settings
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
        antes = pay_svc.summary(db)["month_total_cents"]
        ahora = int(datetime.now(timezone.utc).timestamp())
        cargo_ajeno = {
            "id": f"ch_sync_ajeno_{uuid.uuid4().hex[:8]}", "currency": "eur",
            "livemode": True, "amount": 30000, "amount_refunded": 30000,
            "created": ahora,
            "billing_details": {"email": f"ajeno-{uuid.uuid4().hex[:6]}@otro.com"},
            "invoice": None, "refunds": {"data": []},
        }

        class _Iter:
            def __init__(self, data): self._d = data
            def auto_paging_iter(self): return iter(self._d)

        class _Charge:
            @staticmethod
            def list(**kw): return _Iter([cargo_ajeno])

        class _Vacio:
            @staticmethod
            def list(**kw): return _Iter([])

        class _Checkout:
            Session = _Vacio

        class _FakeStripe:
            Charge = _Charge
            Invoice = _Vacio
            checkout = _Checkout

        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "_stripe", lambda: _FakeStripe)

        res = pay_svc.sync_from_stripe(db, days=30)
        assert res["errors"] == []
        db.expire_all()
        assert _pagos_de(db, cargo_ajeno["id"]) == []
        assert pay_svc.summary(db)["month_total_cents"] == antes
    finally:
        db.close()


def test_checkout_ajeno_no_crea_ficha(monkeypatch):
    """REGRESIÓN (auditoría crítica): un checkout de OTRO producto de la misma
    cuenta de Stripe (Payment Link de un ebook, un taller) no lleva nuestra
    metadata. Antes creaba una ficha «Full pagado» al comprador y le enviaba
    portal + anamnesis de una asesoría que no contrató. Ahora se anota como
    huérfano en el libro (el dinero se VE) sin fabricar clientes."""
    stripe_service = _prep(monkeypatch)
    from sqlalchemy import func as sqlfunc, select

    from app.db import SessionLocal
    from app.models import Client

    db = SessionLocal()
    try:
        email = f"ebook-{uuid.uuid4().hex[:8]}@x.com"
        ses = _sesion(metadata={},  # SIN tier ni client_id: sesión ajena
                      customer_details={"email": email, "name": "Comprador Ebook"},
                      amount_total=1500)
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", ses)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"ignored": "checkout_ajeno"}

        db.expire_all()
        assert db.scalar(select(sqlfunc.count(Client.id)).where(
            sqlfunc.lower(Client.email) == email)) == 0        # sin ficha
        pagos = _pagos_de(db, ses["id"])
        assert len(pagos) == 1 and pagos[0].client_id is None  # pero se VE
    finally:
        db.close()


def test_filtro_sin_ficha_lleva_a_los_cobros_huerfanos(http):
    """El resumen contaba los pagos sin ficha y no había forma de llegar a ellos
    desde la web: el chip ya aplica un filtro real contra el backend."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    obj = f"cs_huerfano_{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        pay_svc.record_payment(
            db, object_id=obj, kind="checkout", status="paid", amount_cents=9900,
            customer_name="Sin Ficha", customer_email="huerfano@x.com",
            paid_at=datetime.now(timezone.utc), livemode=True, client=None,
        )
        db.commit()
    finally:
        db.close()

    r = http.get("/api/payments?orphan=true&limit=50", headers=_auth())
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items, "el filtro no devolvió ningún huérfano"
    assert all(p["client_id"] is None for p in items)
    assert any(p["stripe_object_id"] == obj for p in items)

    # Sin el filtro, el mismo movimiento sigue en el feed general.
    r2 = http.get("/api/payments?limit=50", headers=_auth())
    assert any(p["stripe_object_id"] == obj for p in r2.json()["items"])


def test_un_tipo_de_movimiento_desconocido_no_tumba_el_libro(monkeypatch):
    """Una sola fila con un `kind` que el esquema no reconoce —una versión
    anterior, un arreglo a mano en la base, un tipo nuevo de Stripe— devolvía
    un 500 y se llevaba por delante el feed ENTERO de /pagos y el bloque de
    cobros de la ficha. El libro de caja tiene que enseñar lo que hay."""
    _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Payment
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        c = _nuevo_cliente(db)
        raro = Payment(
            stripe_object_id=f"ch_raro_{uuid.uuid4().hex[:8]}", kind="charge",
            status="paid", amount_cents=12900, currency="eur", livemode=False,
            client_id=c.id, description="Cobro de un tipo que no conocemos",
            paid_at=datetime.now(timezone.utc))
        db.add(raro)
        db.commit()

        filas, _total = pay_svc.list_payments(db, client_id=c.id, limit=10)
        assert any(p.kind == "charge" for p in filas)
        # Y el mapper del feed lo serializa sin reventar (era el 500).
        from app.routers.payments import _to_out

        salida = [_to_out(p, {c.id: c.full_name}) for p in filas]
        assert salida and any(x.kind == "charge" for x in salida)
    finally:
        db.close()


def test_una_referencia_no_numerica_no_tumba_el_webhook(monkeypatch):
    """`client_reference_id` lo pone quien crea la sesión, y en esta cuenta de
    Stripe hay más productos que los nuestros. Un Payment Link ajeno con una
    referencia de texto ("pedido-42") reventaba el `int()` del webhook con un
    500 — y Stripe reintenta un 500 durante días, así que ese webhook se
    atascaba y el cobro se quedaba sin anotar en el libro."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        sesion = {
            "id": f"cs_ref_texto_{uuid.uuid4().hex[:10]}", "currency": "eur",
            "livemode": True, "amount_total": 4900, "payment_status": "paid",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "client_reference_id": "pedido-42",     # ← ni numérico ni nuestro
            "metadata": {},
            "customer_details": {"email": f"taller-{uuid.uuid4().hex[:6]}@otracosa.com",
                                 "name": "Comprador Ajeno"},
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("checkout.session.completed", sesion)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")

        # Ni 500 ni ficha fabricada: se anota como huérfano y se ve el dinero.
        assert res == {"ignored": "checkout_ajeno"}, res
        db.expire_all()
        filas = _pagos_de(db, sesion["id"])
        assert len(filas) == 1 and filas[0].client_id is None
    finally:
        db.close()


def test_la_sincronizacion_repesca_los_cobros_que_FALLARON(monkeypatch):
    """La repesca solo miraba `status="paid"`. Un cobro que NO entró es lo más
    caro de perder —el cliente cree que ha pagado, sigue entrenando y el coach
    trabaja gratis— y dependía por completo de que llegase su webhook; la
    sincronización existe justo para cuando el webhook no llega.

    Y una factura recién emitida que aún no se ha intentado cobrar NO es un
    impago: esa no puede entrar."""
    from app.config import settings
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
        ahora = int(datetime.now(timezone.utc).timestamp())
        marca = uuid.uuid4().hex[:8]
        impagada = {
            "id": f"in_impago_{marca}", "currency": "eur", "livemode": True,
            "amount_due": 12000, "amount_paid": 0, "created": ahora,
            "attempted": True, "attempt_count": 2,
            "billing_reason": "subscription_cycle",
            "customer_email": f"impago-{marca}@x.com", "customer_name": "Impago Cliente",
            "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
        }
        sin_intentar = {
            "id": f"in_nueva_{marca}", "currency": "eur", "livemode": True,
            "amount_due": 12000, "amount_paid": 0, "created": ahora,
            "attempted": False, "attempt_count": 0,
            "billing_reason": "subscription_cycle",
            "customer_email": f"nueva-{marca}@x.com",
            "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
        }

        class _Iter:
            def __init__(self, data): self._d = data
            def auto_paging_iter(self): return iter(self._d)

        class _Invoice:
            @staticmethod
            def list(**kw):
                if kw.get("status") == "open":
                    return _Iter([impagada, sin_intentar])
                return _Iter([])

        class _Vacio:
            @staticmethod
            def list(**kw): return _Iter([])

        class _Checkout:
            Session = _Vacio

        class _FakeStripe:
            Charge = _Vacio
            Invoice = _Invoice
            checkout = _Checkout

        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "_stripe", lambda: _FakeStripe)

        res = pay_svc.sync_from_stripe(db, days=30)
        assert res["errors"] == [], res["errors"]
        db.expire_all()

        filas = _pagos_de(db, impagada["id"])
        assert len(filas) == 1, "el impago repescado no se anotó"
        assert filas[0].status == "failed"
        assert filas[0].amount_cents == 12000
        # SIN LEER: si aparece por repesca es que el coach no se enteró.
        assert filas[0].seen_at is None
        # La factura que aún no se ha intentado cobrar no es un impago.
        assert _pagos_de(db, sin_intentar["id"]) == []
    finally:
        db.close()


def _cobro_anotado(db, *, email: str, importe: int = 12900):
    """Un cobro nuestro ya en el libro, para poder disputarlo después."""
    from app.services import payments as pay_svc

    cid = f"ch_disp_{uuid.uuid4().hex[:10]}"
    pay_svc.record_payment(
        db, object_id=cid, kind="checkout", status="paid", amount_cents=importe,
        customer_name="Cliente Disputa", customer_email=email,
        payment_intent=f"pi_{uuid.uuid4().hex[:12]}",
        paid_at=datetime.now(timezone.utc))
    db.commit()
    from sqlalchemy import select

    from app.models import Payment
    return db.scalar(select(Payment).where(Payment.stripe_object_id == cid))


def test_un_contracargo_resta_y_avisa(monkeypatch):
    """CONTRACARGO: el cliente reclama el cobro a su banco. Es lo más caro que
    pasa en la pasarela y era EL ÚNICO movimiento de dinero que el sistema no
    miraba: Stripe retiene el importe, el libro seguía enseñando el ingreso y
    el coach no se enteraba — y una disputa tiene PLAZO para responder con
    pruebas, así que enterarse tarde es perderla."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, p: avisos.append(p))

    db = SessionLocal()
    try:
        cobro = _cobro_anotado(db, email=f"disputa-{uuid.uuid4().hex[:6]}@x.com")
        antes = pay_svc.summary(db)["month_total_cents"]

        disputa = {
            "id": f"dp_{uuid.uuid4().hex[:12]}", "amount": 12900, "currency": "eur",
            "livemode": True, "status": "needs_response",
            "charge": cobro.stripe_object_id,
            "payment_intent": cobro.payment_intent,
            "created": int(datetime.now(timezone.utc).timestamp()),
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.dispute.created", disputa)))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res["dispute"] == "needs_response", res

        db.expire_all()
        filas = _pagos_de(db, disputa["id"])
        assert len(filas) == 1 and filas[0].status == "refunded"
        assert filas[0].seen_at is None                      # nunca "visto"
        assert pay_svc.summary(db)["month_total_cents"] == antes - 12900
        assert avisos and "Contracargo" in avisos[-1]["title"]

        # Y una disputa de un cobro AJENO de la misma cuenta no resta.
        ajena = dict(disputa, id=f"dp_{uuid.uuid4().hex[:12]}",
                     charge=f"ch_ajeno_{uuid.uuid4().hex[:8]}", payment_intent=None)
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.dispute.created", ajena)))
        assert stripe_service.handle_webhook(db, b"{}", "sig") == {"ignored": "disputa_ajena"}
    finally:
        db.close()


def test_un_contracargo_ganado_devuelve_el_dinero_al_libro(monkeypatch):
    """Si el banco da la razón al coach, el dinero vuelve: la salida anotada al
    abrirse la disputa se anula, o el mes quedaría restado para siempre."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import payments as pay_svc
    from app.services import push as push_svc

    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, p: None)
    db = SessionLocal()
    try:
        cobro = _cobro_anotado(db, email=f"ganada-{uuid.uuid4().hex[:6]}@x.com")
        antes = pay_svc.summary(db)["month_total_cents"]
        disputa = {
            "id": f"dp_{uuid.uuid4().hex[:12]}", "amount": 12900, "currency": "eur",
            "livemode": True, "status": "needs_response",
            "charge": cobro.stripe_object_id, "payment_intent": cobro.payment_intent,
            "created": int(datetime.now(timezone.utc).timestamp()),
        }
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.dispute.created", disputa)))
        stripe_service.handle_webhook(db, b"{}", "sig")
        db.expire_all()
        assert pay_svc.summary(db)["month_total_cents"] == antes - 12900

        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(
            _evento("charge.dispute.closed", dict(disputa, status="won"))))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res["dispute"] == "won", res
        db.expire_all()
        assert pay_svc.summary(db)["month_total_cents"] == antes
    finally:
        db.close()


def test_un_cobro_sin_ficha_por_fin_tiene_salida(http, monkeypatch):
    """El resumen avisa de "N sin ficha" y el feed sabe filtrarlos, pero NADA
    apagaba el aviso: `adopt_orphans` solo reasocia por email y dentro de 30
    días, así que un cobro de otro producto de la cuenta —o uno con el email
    mal escrito en el checkout— contaba para siempre. Un aviso que no se puede
    resolver se acaba ignorando, y con él los que sí importan."""
    from app.db import SessionLocal
    from app.services import payments as pay_svc

    db = SessionLocal()
    try:
        marca = uuid.uuid4().hex[:8]
        pay_svc.record_payment(
            db, object_id=f"cs_huerfano_{marca}", kind="checkout", status="paid",
            amount_cents=4900, customer_name="Ajeno Total",
            customer_email=f"ajeno-{marca}@otracosa.com",
            paid_at=datetime.now(timezone.utc))
        db.commit()
        fila = _pagos_de(db, f"cs_huerfano_{marca}")[0]
        antes = pay_svc.summary(db)["orphan_count"]
        assert antes >= 1

        # Sale en el filtro de huérfanos…
        pagos, _ = pay_svc.list_payments(db, orphan=True, limit=100)
        assert fila.id in {p.id for p in pagos}

        # …y se puede declarar ajeno: deja de contar y sale del filtro.
        r = http.post(f"/api/payments/{fila.id}/resolver", headers=_auth(), json={})
        assert r.status_code == 200, r.text
        db.expire_all()
        assert pay_svc.summary(db)["orphan_count"] == antes - 1
        pagos, _ = pay_svc.list_payments(db, orphan=True, limit=100)
        assert fila.id not in {p.id for p in pagos}
        # Pero el DINERO sigue contando: no se ha borrado nada.
        assert _pagos_de(db, f"cs_huerfano_{marca}")[0].amount_cents == 4900
    finally:
        db.close()
