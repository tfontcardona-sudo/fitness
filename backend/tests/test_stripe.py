"""Tests del webhook de Stripe (con Stripe simulado).

Verifica las dos rutas de `checkout.session.completed`:
- alta manual (metadata.client_id) → marca a ese cliente como pagado;
- registro personal (sin client_id) → crea el perfil con su plan, pagado.

Requiere PostgreSQL. No llama a Stripe de verdad: se simula construct_event.
"""
from __future__ import annotations

import uuid
import warnings

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


def _fake_stripe(event: dict):
    """Devuelve un módulo stripe simulado cuyo Webhook.construct_event → event."""
    class _Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return event

    class _Stripe:
        Webhook = _Webhook

    return lambda: _Stripe


def _completed(session_obj: dict) -> dict:
    return {"type": "checkout.session.completed", "data": {"object": session_obj}}


def _prep(monkeypatch):
    from app.config import settings
    from app.services import stripe_service

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "emails_enabled", False)  # nada de SMTP en tests
    return stripe_service


def test_webhook_marks_manual_client_paid(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    db = SessionLocal()
    try:
        c = Client(full_name="Manual Pay", email=f"m-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", status="onboarding", portal_token="p",
                   payment_status="pending")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        event = _completed({"metadata": {"client_id": str(cid), "tier": "full",
                                         "billing_period": "6m"},
                            "payment_status": "paid"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res.get("marked_paid") == cid

        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "paid" and c.paid_at is not None
        # La duración que se pagó de verdad queda reflejada en la ficha.
        assert c.billing_period == "6m"
    finally:
        db.close()


def test_webhook_selfserve_creates_paid_client(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from sqlalchemy import func, select

    email = f"self-{uuid.uuid4().hex[:8]}@x.com"
    event = _completed({
        "metadata": {"tier": "nutri", "billing_period": "3m"},
        "payment_status": "paid",
        "customer_details": {"email": email, "name": "Nuevo Cliente", "phone": "600111222"},
    })
    monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))

    db = SessionLocal()
    try:
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert "created" in res
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        assert c is not None
        assert c.package_tier == "nutri"
        assert c.billing_period == "3m"
        assert c.payment_status == "paid"
        assert c.status == "onboarding"
        assert c.portal_token and c.portal_token != "pendiente"
    finally:
        db.close()


def test_webhook_selfserve_existing_email_is_idempotent(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    email = f"dup-{uuid.uuid4().hex[:8]}@x.com"
    db = SessionLocal()
    try:
        c = Client(full_name="Ya existe", email=email, package_tier="full",
                   status="onboarding", portal_token="p", payment_status="pending")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        event = _completed({"metadata": {"tier": "full"}, "payment_status": "paid",
                            "customer_details": {"email": email, "name": "Ya existe"}})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res.get("marked_paid") == cid and res.get("existing") is True
    finally:
        db.close()


# ---- resolución de precios: .env nuevo → lookup_key → .env antiguo ----

def test_resolucion_precio_prioriza_lookup(monkeypatch):
    # El lookup de Stripe manda: el .env del servidor arrastra IDs del plan Full
    # ANTIGUO (otro importe) y no debe pisar los precios nuevos del script.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_price_nutri_1m", "price_env")
    monkeypatch.setattr(settings, "stripe_price_start_1m", "price_viejo")
    monkeypatch.setattr(ss, "_price_by_lookup", lambda t, p: "price_lookup")
    assert ss._resolve_price_id("nutri", "1m") == "price_lookup"

    # Sin lookup (Stripe caído o script no ejecutado), el .env nuevo es la reserva.
    monkeypatch.setattr(ss, "_price_by_lookup", lambda t, p: "")
    assert ss._resolve_price_id("nutri", "1m") == "price_env"


def test_resolucion_precio_lookup_gana_al_env_antiguo(monkeypatch):
    # Con el script ejecutado (lookup_key en Stripe), los IDs viejos del .env
    # (START/PRO, con los importes antiguos) NO deben pisar los precios nuevos.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_price_nutri_1m", "")
    monkeypatch.setattr(settings, "stripe_price_start_1m", "price_viejo")
    monkeypatch.setattr(ss, "_price_by_lookup", lambda t, p: "price_lookup")
    assert ss._resolve_price_id("nutri", "1m") == "price_lookup"


def test_resolucion_precio_cae_al_env_antiguo_sin_lookup(monkeypatch):
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_price_full_1m", "")
    monkeypatch.setattr(settings, "stripe_price_pro_1m", "price_pro_viejo")
    monkeypatch.setattr(ss, "_price_by_lookup", lambda t, p: "")
    assert ss._resolve_price_id("full", "1m") == "price_pro_viejo"


class FakeStripe:
    """Stripe mínimo en memoria: productos y precios con lookup_keys, para
    probar el auto-alta sin red. Imita los métodos que usa el servicio."""

    def __init__(self):
        self.products: list[dict] = []
        self.prices: list[dict] = []
        fake = self

        class Product:
            @staticmethod
            def list(**kw):
                return {"data": list(fake.products)}

            @staticmethod
            def create(**kw):
                prod = {"id": f"prod_{len(fake.products) + 1}", **kw}
                fake.products.append(prod)
                return prod

        class Price:
            @staticmethod
            def list(lookup_keys=None, **kw):
                data = [p for p in fake.prices if p.get("active", True)
                        and (not lookup_keys or p.get("lookup_key") in lookup_keys)]
                return {"data": data}

            @staticmethod
            def create(**kw):
                pr = {"id": f"price_{len(fake.prices) + 1}", "active": True, **kw}
                fake.prices.append(pr)
                return pr

            @staticmethod
            def modify(price_id, **kw):
                for p in fake.prices:
                    if p["id"] == price_id:
                        p.update(kw)

        self.Product = Product
        self.Price = Price


def _reset_stripe_caches(monkeypatch, ss):
    monkeypatch.setattr(ss, "_lookup_cache", {"at": 0.0, "ids": {}})
    monkeypatch.setattr(ss, "_ensure_state", {"at": 0.0})
    monkeypatch.setattr(ss, "_prices_cache", {"at": 0.0, "data": None})


def test_auto_alta_crea_los_9_precios_que_faltan(monkeypatch):
    # Sin script ejecutado (Stripe vacío), resolver un precio los CREA todos:
    # la primera visita a /planes o el primer checkout dejan Stripe configurado.
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    pid = ss._price_by_lookup("train", "1m")
    assert pid
    assert len(fake.products) == 3 and len(fake.prices) == 9
    creado = next(p for p in fake.prices if p["lookup_key"] == "dqr_train_1m")
    assert creado["unit_amount"] == 6900 and creado["currency"] == "eur"
    assert pid == creado["id"]

    # Idempotente: resolver otra combinación después no crea nada más.
    _reset_stripe_caches(monkeypatch, ss)
    assert ss._price_by_lookup("nutri", "3m")
    assert len(fake.prices) == 9


def test_auto_alta_transfiere_lookup_si_cambia_el_importe(monkeypatch):
    # Un precio existente con OTRO importe no se pisa: precio nuevo con el mismo
    # lookup_key (transferido) y el antiguo desactivado.
    from app.services import stripe_service as ss

    fake = FakeStripe()
    fake.products.append({"id": "prod_x", "metadata": {"dqr_tier": "train"}})
    fake.prices.append({"id": "price_old", "active": True, "product": "prod_x",
                        "lookup_key": "dqr_train_1m", "unit_amount": 4900,
                        "currency": "eur"})
    ss.ensure_canonical_prices(fake, log=lambda m: None)

    old = next(p for p in fake.prices if p["id"] == "price_old")
    assert old["active"] is False
    nuevo = next(p for p in fake.prices
                 if p.get("lookup_key") == "dqr_train_1m" and p["active"])
    assert nuevo["unit_amount"] == 6900
    assert nuevo.get("transfer_lookup_key") is True


def test_planes_muestra_precios_de_reserva_sin_stripe(monkeypatch):
    # Sin STRIPE_SECRET_KEY (dev) la página de planes enseña igualmente los
    # importes canónicos de las 9 combinaciones — nunca tarjetas sin precio.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", "")
    _reset_stripe_caches(monkeypatch, ss)

    data = ss.get_plan_prices()
    t = data["tiers"]
    assert t["train"]["1m"]["total"] == 69.0
    assert t["train"]["3m"] == {"total": 195.0, "months": 3, "per_month": 65.0}
    assert t["nutri"]["1m"]["total"] == 79.0
    assert t["nutri"]["6m"]["per_month"] == 72.0
    assert t["full"]["1m"]["total"] == 129.0
    assert t["full"]["6m"] == {"total": 708.0, "months": 6, "per_month": 118.0}


def test_planes_reserva_con_stripe_caido_no_se_cachea(monkeypatch):
    # Con Stripe configurado pero sin responder, se enseña la reserva canónica
    # pero NO se cachea: la siguiente visita reintenta leer los precios reales.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(ss, "_resolve_price_id", lambda t, p: "")
    _reset_stripe_caches(monkeypatch, ss)

    data = ss.get_plan_prices()
    assert data["tiers"]["train"]["1m"]["total"] == 69.0
    assert ss._prices_cache["data"] is None  # sin cachear → reintenta


def test_importes_del_script_cumplen_lo_pedido():
    # Nutri > Train en cada duración; Full < Train+Nutri en cada duración.
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "setup_prices", pathlib.Path(__file__).parents[1] / "scripts" / "setup_stripe_prices.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    A = mod.AMOUNTS
    for p in ("1m", "3m", "6m"):
        assert A["nutri"][p] > A["train"][p]
        assert A["full"][p] < A["train"][p] + A["nutri"][p]
    assert A["train"]["1m"] == 6900 and A["nutri"]["1m"] == 7900 and A["full"]["1m"] == 12900


def test_webhook_metadata_antigua_crea_el_plan_correcto(monkeypatch):
    # Una Checkout Session creada ANTES del deploy lleva metadata tier="start"
    # (el plan solo-dieta viejo): el webhook debe dar de alta NUTRI, no Full
    # (que incluiría entreno y videollamada que el cliente NO pagó).
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from sqlalchemy import func, select

    email = f"legacy-{uuid.uuid4().hex[:8]}@x.com"
    event = _completed({
        "metadata": {"tier": "start", "billing_period": "1m"},
        "payment_status": "paid",
        "customer_details": {"email": email, "name": "Legacy Buyer", "phone": "600000111"},
    })
    monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))

    db = SessionLocal()
    try:
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert "created" in res
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        assert c is not None and c.package_tier == "nutri"
        # Limpieza: el conftest borra los clientes @x.com (con dependientes) al
        # final de la suite, como en el resto de tests del webhook.
    finally:
        db.close()
