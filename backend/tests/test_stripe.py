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

from app import branding
from app.services import stripe_service as ss

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
    """Stripe mínimo en memoria: productos y precios (con lookup_keys), para
    probar el auto-alta sin red."""

    def __init__(self):
        self.products: list[dict] = []
        self.prices: list[dict] = []
        self.coupons: dict[str, dict] = {}
        self.sub_modifications: list[tuple[str, dict]] = []
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

        class Coupon:
            @staticmethod
            def retrieve(coupon_id):
                if coupon_id not in fake.coupons:
                    raise KeyError(coupon_id)  # como el InvalidRequestError real
                return fake.coupons[coupon_id]

            @staticmethod
            def create(**kw):
                cup = {"valid": True, **kw}
                fake.coupons[kw["id"]] = cup
                return cup

            @staticmethod
            def delete(coupon_id):
                fake.coupons.pop(coupon_id, None)

        class Subscription:
            @staticmethod
            def modify(sub_id, **kw):
                fake.sub_modifications.append((sub_id, kw))

            @staticmethod
            def retrieve(sub_id):
                raise KeyError(sub_id)

        self.Product = Product
        self.Price = Price
        self.Coupon = Coupon
        self.Subscription = Subscription


def _reset_stripe_caches(monkeypatch, ss):
    monkeypatch.setattr(ss, "_lookup_cache", {"at": 0.0, "ids": {}})
    monkeypatch.setattr(ss, "_ensure_state", {"at": 0.0})
    monkeypatch.setattr(ss, "_prices_cache", {"at": 0.0, "data": None})


def test_auto_alta_crea_los_precios_que_faltan(monkeypatch):
    # Sin script ejecutado (Stripe vacío), resolver un precio los CREA todos:
    # la primera visita a /planes o el primer checkout dejan Stripe configurado.
    # Catálogo de Professional: UN precio de pago único por servicio.
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    pid = ss._price_by_lookup("train", "unico")
    assert pid
    # Tres pagos únicos, ni recurrentes ni cupones: no hay suscripciones.
    assert len(fake.products) == 3 and len(fake.prices) == 3
    assert not fake.coupons
    creado = next(p for p in fake.prices if p["lookup_key"] == ss._lookup_key("train", "unico"))
    assert creado["unit_amount"] == 7000 and creado["currency"] == "eur"
    pack = next(p for p in fake.prices if p["lookup_key"] == ss._lookup_key("full", "unico"))
    assert pack["unit_amount"] == 13000  # pack completo: 130 € de pago único
    assert pid == creado["id"]

    # Idempotente: resolver otra combinación después no crea nada más.
    _reset_stripe_caches(monkeypatch, ss)
    assert ss._price_by_lookup("nutri", "unico")
    assert len(fake.prices) == 3 and not fake.coupons


def test_auto_reprecio_detecta_importes_desviados(monkeypatch):
    """REGRESIÓN (revisión adversarial): con los lookup_keys YA en Stripe pero
    con importes VIEJOS (p. ej. tras un reprecio en el código, desplegado por el
    cron de auto-deploy que NO ejecuta el script), la resolución debe detectar
    la deriva y alinear los precios sola — antes solo actuaba si FALTABAN keys
    y el reprecio no llegaba nunca a Stripe."""
    from app.services import stripe_service as ss

    fake = FakeStripe()
    viejos = {"train": {"unico": 6500},
              "nutri": {"unico": 6500},
              "full": {"unico": 11900}}
    for i, t in enumerate(("train", "nutri", "full")):
        fake.products.append({"id": f"prod_{t}", "metadata": {branding.STRIPE_TIER_METADATA_KEY: t}})
        for p in ("unico",):
            fake.prices.append({"id": f"price_old_{t}_{p}", "active": True,
                                "product": f"prod_{t}", "lookup_key": ss._lookup_key(t, p),
                                "unit_amount": viejos[t][p], "currency": "eur"})
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    pid = ss._price_by_lookup("full", "unico")
    nuevo = next(p for p in fake.prices
                 if p.get("lookup_key") == ss._lookup_key("full", "unico") and p["active"])
    assert pid == nuevo["id"] and nuevo["unit_amount"] == 13000  # pack: 130 € únicos
    viejo = next(p for p in fake.prices if p["id"] == "price_old_full_unico")
    assert viejo["active"] is False  # el precio antiguo queda archivado
    # Todas las combinaciones quedaron alineadas con la tabla canónica.
    for t in ("train", "nutri", "full"):
        for p in ("unico",):
            activo = next(x for x in fake.prices
                          if x.get("lookup_key") == ss._lookup_key(t, p) and x["active"])
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
    ss._lookup_cache["ids"][ss._lookup_key("full", "3m")] = "price_x"  # caché "envenenada"

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
    fake.products.append({"id": "prod_x", "metadata": {branding.STRIPE_TIER_METADATA_KEY: "train"}})
    fake.prices.append({"id": "price_old", "active": True, "product": "prod_x",
                        "lookup_key": ss._lookup_key("train", "unico"), "unit_amount": 4900,
                        "currency": "eur"})
    ss.ensure_canonical_prices(fake, log=lambda m: None)

    old = next(p for p in fake.prices if p["id"] == "price_old")
    assert old["active"] is False
    nuevo = next(p for p in fake.prices
                 if p.get("lookup_key") == ss._lookup_key("train", "unico") and p["active"])
    assert nuevo["unit_amount"] == 7000
    assert nuevo.get("transfer_lookup_key") is True


def test_planes_muestra_precios_de_reserva_sin_stripe(monkeypatch):
    # Sin STRIPE_SECRET_KEY (dev) la página de planes enseña igualmente los
    # importes canónicos del catálogo ONLINE — nunca tarjetas sin precio. Los
    # tiers sin venta online (Entreno Personal/nutri) NO se exponen en el
    # endpoint público: sus tarifas presenciales viven en el frontend.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", "")
    _reset_stripe_caches(monkeypatch, ss)

    data = ss.get_plan_prices()
    t = data["tiers"]
    # Los TRES servicios son públicos y de pago único (70 / 70 / 130 €).
    assert t["full"]["unico"] == {"total": 130.0, "months": 1, "per_month": 130.0}
    assert t["nutri"]["unico"]["total"] == 70.0
    assert t["train"]["unico"]["total"] == 70.0


def test_planes_reserva_con_stripe_caido_no_se_cachea(monkeypatch):
    # Con Stripe configurado pero sin responder, se enseña la reserva canónica
    # pero NO se cachea: la siguiente visita reintenta leer los precios reales.
    from app.config import settings
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(ss, "_resolve_price_id", lambda t, p: "")
    _reset_stripe_caches(monkeypatch, ss)

    data = ss.get_plan_prices()
    assert data["tiers"]["full"]["unico"]["total"] == 130.0
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
        # PAGO ÚNICO: es el enlace REAL del botón "Contratar" de /planes. Estuvo
        # rebotando a /planes sin cobrar porque la lista de duraciones válidas
        # se escribió a mano y se quedó con las mensuales del motor.
        for tier in ("nutri", "train", "full"):
            r = http.get(f"/api/pay/plan/{tier}/unico", follow_redirects=False)
            assert r.status_code == 302, tier
            assert r.headers["location"] == f"https://stripe.test/{tier}/unico", tier

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
        assert r.status_code == 200 and branding.TIER_LABELS["full"] in r.text

        # Stripe caído/no configurado → /planes (nunca un 500 al interesado).
        def _boom(db, t, p, **kw):
            raise sr.StripeError("sin clave")
        monkeypatch.setattr(sr, "create_checkout_url", _boom)
        r = http.get("/api/pay/plan/full/3m", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/planes")


def test_importes_del_script_cumplen_lo_pedido():
    # Catálogo REAL de la marca: pago ÚNICO — Dieta 70 €, Entrenamiento 70 € y
    # Pack completo 130 € (con la cuota del gimnasio incluida). El pack cuesta
    # menos que los dos sueltos: es lo que lo hace atractivo.
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "setup_prices", pathlib.Path(__file__).parents[1] / "scripts" / "setup_stripe_prices.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    A = mod.AMOUNTS
    assert set(A) == {"nutri", "train", "full"}
    assert all(set(v) == {"unico"} for v in A.values()), "solo hay pago único"
    assert A["nutri"]["unico"] == 7000 and A["train"]["unico"] == 7000
    assert A["full"]["unico"] == 13000
    assert A["full"]["unico"] < A["train"]["unico"] + A["nutri"]["unico"]


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


# ---- catálogo white-label: guardas de venta online (Professional Girona) ----

def test_checkout_de_plan_sin_venta_online_se_rechaza(monkeypatch):
    # Professional vende los TRES online, pero el veto del motor sigue vivo:
    # un tier fuera de PUBLIC_TIERS no puede cobrarse online ni con un enlace
    # escrito a mano (otra instancia puede cobrar algo en el local).
    from app.config import settings
    from app.db import SessionLocal
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(branding, "PUBLIC_TIERS", ("full",))
    db = SessionLocal()
    try:
        for tier in ("train", "nutri"):
            with pytest.raises(ss.StripeError, match="en el centro"):
                ss.create_checkout_url(db, tier, "unico")
    finally:
        db.close()


def test_auto_alta_no_entra_en_bucle_de_reparacion(monkeypatch):
    # Sin suscripciones ni cupones, la resolución de precios no puede entrar en
    # un ciclo de "reparación" eterno buscando algo que no existe.
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    assert ss._price_by_lookup("full", "unico")
    assert len(fake.prices) == 3 and not fake.coupons

    # Segunda resolución: nada nuevo que crear (sin bucle de reparación).
    _reset_stripe_caches(monkeypatch, ss)
    assert ss._price_by_lookup("train", "unico")
    assert len(fake.prices) == 3 and not fake.coupons
