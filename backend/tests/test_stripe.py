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


def test_auto_reprecio_detecta_importes_desviados(monkeypatch):
    """REGRESIÓN (revisión adversarial): con los 9 lookup_keys YA en Stripe pero
    con importes VIEJOS (p. ej. tras un reprecio en el código, desplegado por el
    cron de auto-deploy que NO ejecuta el script), la resolución debe detectar
    la deriva y alinear los precios sola — antes solo actuaba si FALTABAN keys
    y el reprecio no llegaba nunca a Stripe."""
    from app.services import stripe_service as ss

    fake = FakeStripe()
    viejos = {"train": {"1m": 6900, "3m": 19500, "6m": 37200},
              "nutri": {"1m": 7900, "3m": 22500, "6m": 43200},
              "full": {"1m": 12900, "3m": 36900, "6m": 70800}}
    for i, t in enumerate(("train", "nutri", "full")):
        fake.products.append({"id": f"prod_{t}", "metadata": {"dqr_tier": t}})
        for p in ("1m", "3m", "6m"):
            fake.prices.append({"id": f"price_old_{t}_{p}", "active": True,
                                "product": f"prod_{t}", "lookup_key": f"dqr_{t}_{p}",
                                "unit_amount": viejos[t][p], "currency": "eur"})
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    pid = ss._price_by_lookup("full", "3m")
    nuevo = next(p for p in fake.prices
                 if p.get("lookup_key") == "dqr_full_3m" and p["active"])
    assert pid == nuevo["id"] and nuevo["unit_amount"] == 33000  # ancla: 330 €
    viejo = next(p for p in fake.prices if p["id"] == "price_old_full_3m")
    assert viejo["active"] is False  # el precio antiguo queda archivado
    # Todas las combinaciones quedaron alineadas con la tabla canónica.
    for t in ("train", "nutri", "full"):
        for p in ("1m", "3m", "6m"):
            activo = next(x for x in fake.prices
                          if x.get("lookup_key") == f"dqr_{t}_{p}" and x["active"])
            assert activo["unit_amount"] == ss.CANONICAL_AMOUNTS[t][p]
    # La caché del catálogo se invalidó: la próxima lectura trae los nuevos.
    assert ss._prices_cache["data"] is None


def test_error_del_sdk_de_stripe_no_revienta_el_enlace_de_pago(monkeypatch):
    """REGRESIÓN (revisión adversarial): un error de la LIBRERÍA de Stripe
    (precio recién archivado, timeout, rate limit) no hereda de nuestra
    StripeError; antes se propagaba como 500 al navegador del interesado. Debe
    traducirse a StripeError → 302 a /planes, y vaciar la caché de precios
    para que el siguiente clic se auto-repare."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app
    from app.services import stripe_service as ss

    class _SdkBoom:
        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    raise ValueError("The price specified is archived")

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(ss, "_resolve_price_id", lambda t, p: "price_x")
    monkeypatch.setattr(ss, "_stripe", lambda: _SdkBoom())
    _reset_stripe_caches(monkeypatch, ss)
    ss._lookup_cache["ids"]["dqr_full_3m"] = "price_x"  # caché "envenenada"

    with TestClient(app) as http:
        r = http.get("/api/pay/plan/full/3m", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/planes")
    assert ss._lookup_cache["ids"] == {}  # el siguiente clic re-resuelve


def test_head_del_enlace_de_pago_no_crea_sesion(monkeypatch):
    """El prefetch HEAD (escáneres de enlaces) no debe crear sesiones de pago."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import stripe_router as sr

    llamadas = []
    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda *a, **k: llamadas.append(1) or "https://stripe.test/x")
    with TestClient(app) as http:
        r = http.head("/api/pay/plan/full/3m", follow_redirects=False)
        # En esta versión de FastAPI el HEAD ni llega al handler (405); si una
        # futura versión lo auto-registra, el handler lo trata como bot (200).
        assert r.status_code in (200, 405)
    assert llamadas == []


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
    assert t["train"]["3m"] == {"total": 177.0, "months": 3, "per_month": 59.0}
    assert t["nutri"]["1m"]["total"] == 79.0
    assert t["nutri"]["6m"]["per_month"] == 62.0
    assert t["full"]["1m"]["total"] == 129.0
    assert t["full"]["3m"] == {"total": 330.0, "months": 3, "per_month": 110.0}
    assert t["full"]["6m"] == {"total": 600.0, "months": 6, "per_month": 100.0}


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


def test_enlace_de_pago_directo_por_plan(monkeypatch):
    """GET /api/pay/plan/{tier}/{period}: el enlace del kit de ventas redirige a
    Stripe con el plan correcto; los nombres antiguos se traducen; un enlace mal
    escrito NUNCA cobra el plan por defecto (→ /planes); los bots de vista
    previa de WhatsApp no crean sesiones de pago."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import stripe_router as sr

    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: f"https://stripe.test/{t}/{p}")
    with TestClient(app) as http:
        r = http.get("/api/pay/plan/full/3m", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "https://stripe.test/full/3m"

        # Nombres antiguos: pro → full (mismo circuito que el webhook).
        r = http.get("/api/pay/plan/pro/1m", follow_redirects=False)
        assert r.headers["location"] == "https://stripe.test/full/1m"

        # Tier o duración desconocidos → /planes, jamás un cobro "por defecto".
        for path in ("/api/pay/plan/fulll/3m", "/api/pay/plan/full/9m"):
            r = http.get(path, follow_redirects=False)
            assert r.status_code == 302 and r.headers["location"].endswith("/planes")

        # Bot de vista previa (WhatsApp renderizando el enlace): mini-página OG,
        # sin crear una sesión de Stripe por cada previsualización.
        r = http.get("/api/pay/plan/full/3m",
                     headers={"User-Agent": "WhatsApp/2.24.1"},
                     follow_redirects=False)
        assert r.status_code == 200 and "DQR Full" in r.text

        # Stripe caído/no configurado → /planes (nunca un 500 al interesado).
        def _boom(db, t, p, **kw):
            raise sr.StripeError("sin clave")
        monkeypatch.setattr(sr, "create_checkout_url", _boom)
        r = http.get("/api/pay/plan/full/3m", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/planes")


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
    # Ancla del dueño (agosto 2026): Full trimestral 330 €; el resto adaptado.
    assert A["full"]["3m"] == 33000 and A["full"]["6m"] == 60000
    assert A["train"]["3m"] == 17700 and A["train"]["6m"] == 32400
    assert A["nutri"]["3m"] == 20100 and A["nutri"]["6m"] == 37200
    # El descuento por compromiso crece con la duración (precio/mes decreciente).
    for t in ("train", "nutri", "full"):
        assert A[t]["3m"] / 3 < A[t]["1m"]
        assert A[t]["6m"] / 6 < A[t]["3m"] / 3


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
