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
    """Stripe mínimo en memoria: productos, precios (con lookup_keys), cupones
    y suscripciones, para probar el auto-alta y la oferta sin red."""

    def __init__(self):
        self.products: list[dict] = []
        self.prices: list[dict] = []
        self.coupons: dict[str, dict] = {}
        # Cada llamada a Price.list con lookup_keys (para comprobar el troceado).
        self.lookup_calls: list[list[str]] = []
        self.sub_modifications: list[tuple[str, dict]] = []
        self.sub_cancelaciones: list[str] = []
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
                # LÍMITE REAL de la API: Stripe rechaza más de 10 lookup_keys
                # por llamada. Sin esta comprobación el doble era más
                # permisivo que Stripe y la suite daba verde mientras los
                # enlaces de la oferta se rompían en producción (9 planes +
                # las 2 formas de pago de la oferta = 11 claves).
                if lookup_keys is not None and len(lookup_keys) > 10:
                    raise ValueError(
                        "You cannot specify more than 10 lookup_keys")
                fake.lookup_calls.append(list(lookup_keys or []))
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

            @staticmethod
            def cancel(sub_id, **kw):
                fake.sub_cancelaciones.append(sub_id)
                return {"id": sub_id, "status": "canceled"}

        self.Product = Product
        self.Price = Price
        self.Coupon = Coupon
        self.Subscription = Subscription


def _reset_stripe_caches(monkeypatch, ss):
    monkeypatch.setattr(ss, "_lookup_cache", {"at": 0.0, "ids": {}})
    monkeypatch.setattr(ss, "_ensure_state", {"at": 0.0})
    monkeypatch.setattr(ss, "_prices_cache", {"at": 0.0, "data": None})


def test_enlace_con_puntuacion_pegada_sigue_yendo_a_stripe(monkeypatch):
    """REGRESIÓN: un enlace pegado desde WhatsApp arrastra a veces el punto
    final de la frase ("…/full/oferta.") o llega en mayúsculas. Antes eso se
    tomaba por un enlace inventado y acababa en /planes sin cobrar."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import stripe_router as sr

    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: f"https://stripe.test/{t}/{p}")
    with TestClient(app) as http:
        for path in ("/api/pay/plan/full/oferta.", "/api/pay/plan/full/3M",
                     "/api/pay/plan/FULL/oferta2)", "/api/pay/plan/full/1m,"):
            r = http.get(path, follow_redirects=False)
            assert r.status_code == 302, path
            assert r.headers["location"].startswith("https://stripe.test/"), path


def test_un_fallo_puntual_no_deja_los_enlaces_muertos_diez_minutos(monkeypatch):
    """REGRESIÓN: el id VACÍO se cacheaba con el TTL de 10 minutos, así que un
    tropiezo de Stripe dejaba la oferta (que no tiene reserva en el .env) sin
    enlace hasta que caducara la caché. Ahora el vacío no se cachea."""
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)
    # Stripe "vacío" y sin auto-alta posible: la resolución no encuentra nada.
    monkeypatch.setattr(ss, "ensure_canonical_prices",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sin permisos")))
    assert ss._price_by_lookup("full", "oferta") == ""
    assert "dqr_full_oferta" not in ss._lookup_cache["ids"]  # NO se cachea el vacío

    # Stripe se recupera: el siguiente intento ya resuelve (sin esperar al TTL).
    fake.prices.append({"id": "price_of", "lookup_key": "dqr_full_oferta",
                        "active": True, "unit_amount": ss.OFFER_MONTHLY_CENTS,
                        "currency": "eur", "recurring": {"interval": "month"}})
    assert ss._price_by_lookup("full", "oferta") == "price_of"


def test_los_lookup_keys_se_piden_en_tandas_de_diez(monkeypatch):
    """REGRESIÓN (el enlace de la oferta acababa en /planes): son ONCE claves
    (9 planes + las 2 formas de pagar la oferta) y Stripe admite 10 por
    llamada. Se piden en tandas y NINGUNA supera el límite."""
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    # Resolver el precio de la OFERTA (la clave nº 11) tiene que funcionar.
    pid = ss._price_by_lookup("full", "oferta")
    assert pid, "el precio de la oferta no se resolvió: el enlace acabaría en /planes"

    assert fake.lookup_calls, "no se consultó ningún lookup_key"
    assert all(len(t) <= 10 for t in fake.lookup_calls), fake.lookup_calls
    # Y entre todas las tandas se piden las once, sin dejarse ninguna.
    pedidas = {k for tanda in fake.lookup_calls for k in tanda}
    assert {"dqr_full_oferta", "dqr_full_oferta2", "dqr_train_1m"} <= pedidas

    # La segunda forma de pago también resuelve (era la que rompía el límite).
    assert ss._price_by_lookup("full", "oferta2")


def test_auto_alta_crea_los_9_precios_que_faltan(monkeypatch):
    # Sin script ejecutado (Stripe vacío), resolver un precio los CREA todos:
    # la primera visita a /planes o el primer checkout dejan Stripe configurado.
    from app.services import stripe_service as ss

    fake = FakeStripe()
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)

    pid = ss._price_by_lookup("train", "1m")
    assert pid
    # 9 pagos únicos + 2 recurrentes de la oferta (1 €→120 €/mes y 2 pagos de
    # 120,50 €); cupón del primer mes creado.
    assert len(fake.products) == 3 and len(fake.prices) == 11
    creado = next(p for p in fake.prices if p["lookup_key"] == "dqr_train_1m")
    assert creado["unit_amount"] == 6900 and creado["currency"] == "eur"
    assert pid == creado["id"]
    oferta = next(p for p in fake.prices if p["lookup_key"] == "dqr_full_oferta")
    assert oferta["unit_amount"] == 12000
    assert oferta["recurring"] == {"interval": "month"}
    oferta2 = next(p for p in fake.prices if p["lookup_key"] == "dqr_full_oferta2")
    assert oferta2["unit_amount"] == 12050
    assert oferta2["recurring"] == {"interval": "month"}
    cupon = fake.coupons["dqr_oferta_primer_mes"]
    assert cupon["amount_off"] == 11900 and cupon["duration"] == "once"

    # Idempotente: resolver otra combinación después no crea nada más.
    _reset_stripe_caches(monkeypatch, ss)
    assert ss._price_by_lookup("nutri", "3m")
    assert len(fake.prices) == 11 and len(fake.coupons) == 1


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
        assert r.status_code == 302 and r.headers["location"].endswith("/planes?pago=error")
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
        assert r.status_code == 302 and r.headers["location"].endswith("/planes?pago=error")


# ---- OFERTA: 1 € el primer mes → 120 €/mes en suscripción ----

def test_oferta_checkout_es_suscripcion_con_cupon(monkeypatch):
    """El checkout de la oferta va en modo SUSCRIPCIÓN con el cupón del primer
    mes a 1 €, y la metadata viaja también en la suscripción (para mapear las
    renovaciones). La oferta es solo del plan Full."""
    from types import SimpleNamespace

    from app.config import settings
    from app.services import stripe_service as ss

    capturas = []

    class _FakeCheckout:
        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    capturas.append(kw)
                    return SimpleNamespace(url="https://stripe.test/oferta")

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(ss, "_resolve_price_id", lambda t, p: "price_oferta")
    monkeypatch.setattr(ss, "_stripe", lambda: _FakeCheckout())

    url = ss.create_checkout_url(None, "full", "oferta")
    assert url == "https://stripe.test/oferta"
    kw = capturas[0]
    assert kw["mode"] == "subscription"
    assert kw["discounts"] == [{"coupon": ss.OFFER_COUPON_ID}]
    assert kw["subscription_data"]["metadata"]["billing_period"] == "oferta"
    assert kw["subscription_data"]["metadata"]["tier"] == "full"
    assert kw["phone_number_collection"] == {"enabled": True}  # self-serve

    # Solo Full: train/nutri con oferta se rechazan.
    with pytest.raises(ss.StripeError):
        ss.create_checkout_url(None, "train", "oferta")


def test_enlace_de_pago_de_la_oferta(monkeypatch):
    """GET /api/pay/plan/full/oferta redirige al checkout; con otro plan, a
    /planes (la oferta no existe para train/nutri). El bot de vista previa ve
    el titular del euro sin crear sesión."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import stripe_router as sr

    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: f"https://stripe.test/{t}/{p}")
    with TestClient(app) as http:
        r = http.get("/api/pay/plan/full/oferta", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "https://stripe.test/full/oferta"

        r = http.get("/api/pay/plan/train/oferta", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/planes")

        r = http.get("/api/pay/plan/full/oferta",
                     headers={"User-Agent": "WhatsApp/2.24.1"}, follow_redirects=False)
        assert r.status_code == 200 and "primer mes 1 €" in r.text


def test_webhook_checkout_oferta_crea_cliente_y_etiqueta_suscripcion(monkeypatch):
    """El pago de la oferta (self-serve) crea el cliente con billing 'oferta' y
    graba su client_id en la metadata de la suscripción — así las facturas de
    renovación se mapean solas."""
    stripe_service = _prep(monkeypatch)
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Client

    email = f"oferta-{uuid.uuid4().hex[:8]}@x.com"
    event = _completed({
        "metadata": {"tier": "full", "billing_period": "oferta"},
        "payment_status": "paid",
        "subscription": "sub_test_1",
        "customer_details": {"email": email, "name": "Cliente Oferta", "phone": "600222333"},
    })

    fake = FakeStripe()

    class _Hooked:
        Webhook = type("W", (), {"construct_event": staticmethod(lambda *a, **k: event)})
        Subscription = fake.Subscription

    monkeypatch.setattr(stripe_service, "_stripe", lambda: _Hooked)

    db = SessionLocal()
    try:
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert "created" in res
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        assert c is not None
        assert c.package_tier == "full" and c.billing_period == "oferta"
        assert c.payment_status == "paid"
        sub_id, kw = fake.sub_modifications[0]
        assert sub_id == "sub_test_1"
        assert kw["metadata"]["client_id"] == str(c.id)
    finally:
        db.close()


def test_webhook_renovaciones_de_la_oferta(monkeypatch):
    """invoice.payment_failed pasa al cliente a 'pendiente' y avisa al coach;
    invoice.paid lo devuelve a 'pagado' y refresca paid_at — ningún impago de
    la renovación mensual pasa desapercibido."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    db = SessionLocal()
    try:
        c = Client(full_name="Renueva Oferta", email=f"ren-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", billing_period="oferta", status="active",
                   portal_token="p", payment_status="paid")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        def _invoice_event(kind, **inv):
            ev = {"type": kind, "data": {"object": {
                "subscription": "sub_x",
                "subscription_details": {"metadata": {"client_id": str(cid)}},
                "billing_reason": "subscription_cycle", **inv,
            }}}
            monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(ev))
            return stripe_service.handle_webhook(db, b"{}", "sig")

        res = _invoice_event("invoice.payment_failed", amount_due=12000)
        assert res == {"invoice": "failed", "client_id": cid}
        db.expire_all()
        assert db.get(Client, cid).payment_status == "pending"
        assert any("no se pudo cobrar" in a["body"] for a in avisos)

        res = _invoice_event("invoice.paid", amount_paid=12000)
        assert res == {"invoice": "paid", "client_id": cid}
        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "paid" and c.paid_at is not None
    finally:
        db.close()


def test_cupon_borrado_se_detecta_y_recrea(monkeypatch):
    """REGRESIÓN (revisión adversarial): con los precios alineados pero el
    CUPÓN del primer mes borrado a mano en el dashboard, la promo moría en
    silencio. El detector de deriva vigila también el cupón y lo recrea."""
    from app.services import stripe_service as ss

    fake = FakeStripe()
    for t in ("train", "nutri", "full"):
        fake.products.append({"id": f"prod_{t}", "metadata": {"dqr_tier": t}})
        for p in ("1m", "3m", "6m"):
            fake.prices.append({"id": f"price_{t}_{p}", "active": True,
                                "product": f"prod_{t}", "lookup_key": f"dqr_{t}_{p}",
                                "unit_amount": ss.CANONICAL_AMOUNTS[t][p],
                                "currency": "eur"})
    fake.prices.append({"id": "price_of", "active": True, "product": "prod_full",
                        "lookup_key": "dqr_full_oferta", "unit_amount": 12000,
                        "currency": "eur", "recurring": {"interval": "month"}})
    assert not fake.coupons  # todo alineado EXCEPTO el cupón (borrado)

    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    _reset_stripe_caches(monkeypatch, ss)
    ss._price_by_lookup("full", "oferta")
    cupon = fake.coupons.get("dqr_oferta_primer_mes")
    assert cupon and cupon["amount_off"] == 11900 and cupon["duration"] == "once"


def test_webhook_baja_de_la_suscripcion(monkeypatch):
    """customer.subscription.deleted: el cliente de la oferta que se da de baja
    pasa a 'pendiente' (deja de pagar), se despega su suscripción y el coach
    recibe push — antes la ficha quedaba 'pagado' para siempre."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    db = SessionLocal()
    try:
        c = Client(full_name="Baja Oferta", email=f"baja-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", billing_period="oferta", status="active",
                   portal_token="p", payment_status="paid",
                   stripe_subscription_id="sub_baja_1")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        event = {"type": "customer.subscription.deleted",
                 "data": {"object": {"id": "sub_baja_1",
                                     "metadata": {"client_id": str(cid)}}}}
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"subscription_cancelled": cid}
        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "pending"
        assert c.stripe_subscription_id is None
        assert any("Suscripción cancelada" in a["title"] for a in avisos)
    finally:
        db.close()


def test_factura_ajena_a_la_oferta_se_ignora(monkeypatch):
    """Una factura de OTRO producto de la misma cuenta de Stripe (sin metadata
    nuestra y sin el precio de la oferta) no debe tocar a ningún cliente por
    coincidencia de email ni disparar avisos de huérfano."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal

    event = {"type": "invoice.paid",
             "data": {"object": {"customer_email": "cualquiera@x.com",
                                 "amount_paid": 5000,
                                 "billing_reason": "subscription_cycle",
                                 "lines": {"data": [{"price": {"lookup_key": "otro_producto"}}]}}}}
    monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
    db = SessionLocal()
    try:
        assert stripe_service.handle_webhook(db, b"{}", "sig") == {"ignored": "invoice_ajena"}
    finally:
        db.close()


def test_reintento_de_factura_no_duplica_avisos(monkeypatch):
    """Los reintentos de entrega de Stripe (misma factura, dos entregas) no
    deben duplicar push ni auditoría: idempotencia por invoice_id."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    db = SessionLocal()
    try:
        c = Client(full_name="Dedupe Oferta", email=f"dd-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", billing_period="oferta", status="active",
                   portal_token="p", payment_status="paid")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()

        event = {"type": "invoice.paid",
                 "data": {"object": {
                     "id": "in_dedupe_1", "amount_paid": 12000,
                     "billing_reason": "subscription_cycle",
                     "subscription_details": {"metadata": {"client_id": str(c.id)}}}}}
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        r1 = stripe_service.handle_webhook(db, b"{}", "sig")
        r2 = stripe_service.handle_webhook(db, b"{}", "sig")  # reintento
        assert r1 == {"invoice": "paid", "client_id": c.id}
        assert r2 == {"ignored": "invoice_repetida", "client_id": c.id}
        assert len(avisos) == 1  # un solo push, no dos
    finally:
        db.close()


def test_registro_publico_rechaza_oferta_sin_full(monkeypatch):
    """REGRESIÓN: el 422 oferta⇒Full también en POST /api/public/register (se
    colaba un train+oferta cuyo enlace cobraría un plan inexistente)."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import public_site

    # El límite por IP (5/min) vive en el módulo y lo comparte toda la suite:
    # al correrla entera, este test tardío se comía un 429 ajeno.
    monkeypatch.setattr(public_site.limiter, "enabled", False)

    with TestClient(app) as http:
        r = http.post("/api/public/register", json={
            "full_name": "Oferta Publica", "email": f"op-{uuid.uuid4().hex[:8]}@x.com",
            "phone": "600000222", "tier": "train", "period": "oferta"})
        assert r.status_code == 422


def test_patch_valida_la_combinacion_oferta_full(monkeypatch):
    """REGRESIÓN: el PATCH del coach tampoco puede dejar train/nutri+oferta —
    ni poniendo la oferta a un train, ni cambiando de plan a uno que ya está
    en la oferta."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import SessionLocal
    from app.main import app
    from app.models import Client, User
    from app.security import create_access_token, hash_password, new_portal_token
    from sqlalchemy import select as _select

    monkeypatch.setattr(settings, "emails_enabled", False)
    with SessionLocal() as db:
        if not db.scalar(_select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
        c_train = Client(full_name="Patch Train", email=f"pt-{uuid.uuid4().hex[:8]}@x.com",
                         package_tier="train", billing_period="1m", status="active",
                         portal_token="p1")
        c_oferta = Client(full_name="Patch Oferta", email=f"po-{uuid.uuid4().hex[:8]}@x.com",
                          package_tier="full", billing_period="oferta", status="active",
                          portal_token="p2")
        db.add_all([c_train, c_oferta])
        db.flush()
        c_train.portal_token = new_portal_token(c_train.id)
        c_oferta.portal_token = new_portal_token(c_oferta.id)
        db.commit()
        id_train, id_oferta = c_train.id, c_oferta.id
    auth = {"Authorization": f"Bearer {create_access_token('coach1')}"}

    with TestClient(app) as http:
        r = http.patch(f"/api/clients/{id_train}", headers=auth,
                       json={"billing_period": "oferta"})
        assert r.status_code == 422
        r = http.patch(f"/api/clients/{id_oferta}", headers=auth,
                       json={"package_tier": "train"})
        assert r.status_code == 422
        # La combinación válida sí pasa: oferta con full explícito.
        r = http.patch(f"/api/clients/{id_train}", headers=auth,
                       json={"package_tier": "full", "billing_period": "oferta"})
        assert r.status_code == 200


def test_enlace_estable_con_suscripcion_no_crea_otra(monkeypatch):
    """REGRESIÓN: el enlace de pago estable de un cliente de la oferta con
    suscripción YA creada e impago no monta una SEGUNDA suscripción con otro
    1 €: redirige a la factura ABIERTA de la que ya tiene (o a /pago-ok si
    está al día)."""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.models import Client
    from app.security import new_portal_token
    from app.services import stripe_service as ss

    db = SessionLocal()
    try:
        c = Client(full_name="Impago Oferta", email=f"im-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", billing_period="oferta", status="active",
                   portal_token="p", payment_status="pending",
                   stripe_subscription_id="sub_impago_1")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        token = c.portal_token
    finally:
        db.close()

    llamadas = []
    monkeypatch.setattr(ss, "open_invoice_url",
                        lambda cl: llamadas.append(cl.id) or "https://invoice.stripe.test/abierta")
    crear = []
    from app.routers import stripe_router as sr
    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda *a, **k: crear.append(1) or "https://no-deberia-llamarse")

    with TestClient(app) as http:
        r = http.get(f"/api/pay/{token}", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "https://invoice.stripe.test/abierta"
    assert llamadas and not crear  # factura abierta sí; checkout nuevo JAMÁS


def test_alta_manual_con_oferta_valida_el_plan(monkeypatch):
    """El alta manual acepta billing 'oferta' SOLO con el plan Full (422 con
    train/nutri): no puede existir un cliente con una oferta que no existe."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import SessionLocal
    from app.main import app
    from app.models import User
    from app.security import create_access_token, hash_password
    from sqlalchemy import select as _select

    monkeypatch.setattr(settings, "emails_enabled", False)
    with SessionLocal() as db:
        if not db.scalar(_select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
    auth = {"Authorization": f"Bearer {create_access_token('coach1')}"}

    with TestClient(app) as http:
        r = http.post("/api/clients", headers=auth, json={
            "full_name": "Oferta Train", "email": f"ot-{uuid.uuid4().hex[:8]}@x.com",
            "package_tier": "train", "billing_period": "oferta"})
        assert r.status_code == 422

        r = http.post("/api/clients", headers=auth, json={
            "full_name": "Oferta Full", "email": f"of-{uuid.uuid4().hex[:8]}@x.com",
            "package_tier": "full", "billing_period": "oferta"})
        assert r.status_code == 201
        assert r.json()["client"]["billing_period"] == "oferta"


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


# ---- OFERTA EN 2 PAGOS: 120,50 € hoy y 120,50 € al mes; se detiene sola ----

def test_oferta2_checkout_es_suscripcion_sin_cupon(monkeypatch):
    """La oferta en 2 pagos va en modo SUSCRIPCIÓN (120,50 €/mes) pero SIN el
    cupón del euro: dos cobros iguales. Solo del plan Full."""
    from types import SimpleNamespace

    from app.config import settings
    from app.services import stripe_service as ss

    capturas = []

    class _FakeCheckout:
        class checkout:
            class Session:
                @staticmethod
                def create(**kw):
                    capturas.append(kw)
                    return SimpleNamespace(url="https://stripe.test/oferta2")

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(ss, "_resolve_price_id", lambda t, p: "price_oferta2")
    monkeypatch.setattr(ss, "_stripe", lambda: _FakeCheckout())

    url = ss.create_checkout_url(None, "full", "oferta2")
    assert url == "https://stripe.test/oferta2"
    kw = capturas[0]
    assert kw["mode"] == "subscription"
    assert "discounts" not in kw  # sin cupón: los dos pagos son de 120,50 €
    assert kw["subscription_data"]["metadata"]["billing_period"] == "oferta2"
    assert kw["subscription_data"]["metadata"]["tier"] == "full"

    with pytest.raises(ss.StripeError):
        ss.create_checkout_url(None, "nutri", "oferta2")


def test_enlace_de_pago_de_la_oferta2(monkeypatch):
    """GET /api/pay/plan/full/oferta2 redirige al checkout; con otro plan, a
    /planes. El bot de vista previa ve los 2 pagos sin crear sesión."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import stripe_router as sr

    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: f"https://stripe.test/{t}/{p}")
    with TestClient(app) as http:
        r = http.get("/api/pay/plan/full/oferta2", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "https://stripe.test/full/oferta2"

        r = http.get("/api/pay/plan/nutri/oferta2", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"].endswith("/planes")

        r = http.get("/api/pay/plan/full/oferta2",
                     headers={"User-Agent": "WhatsApp/2.24.1"}, follow_redirects=False)
        assert r.status_code == 200 and "2 pagos de 120,50" in r.text


def _cliente_oferta2(db, *, sub_id="sub_2p"):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name="Dos Pagos", email=f"o2-{uuid.uuid4().hex[:8]}@x.com",
               package_tier="full", billing_period="oferta2", status="active",
               portal_token="p", payment_status="paid",
               stripe_subscription_id=sub_id)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _evento_factura_oferta2(cid: int, invoice_id: str, razon: str) -> dict:
    return {"type": "invoice.paid", "data": {"object": {
        "id": invoice_id, "subscription": "sub_2p",
        "subscription_details": {"metadata": {"client_id": str(cid),
                                              "billing_period": "oferta2"}},
        "billing_reason": razon, "amount_paid": 12050,
        "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta2"}}]},
    }}}


def test_webhook_segundo_pago_detiene_la_suscripcion(monkeypatch):
    """Al cobrarse la SEGUNDA factura de la oferta en 2 pagos, el webhook
    cancela la suscripción en Stripe (no puede haber un tercer cargo), y la
    baja que llega después NO marca al cliente como pendiente: el programa
    está pagado entero."""
    stripe_service = _prep(monkeypatch)
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Client, Payment
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    fake = FakeStripe()

    db = SessionLocal()
    try:
        c = _cliente_oferta2(db)
        cid = c.id

        def _mandar(evento):
            class _Hooked:
                Webhook = type("W", (), {
                    "construct_event": staticmethod(lambda *a, **k: evento)})
                Subscription = fake.Subscription

            monkeypatch.setattr(stripe_service, "_stripe", lambda: _Hooked)
            return stripe_service.handle_webhook(db, b"{}", "sig")

        # Primer pago (subscription_create): se anota, no se cancela nada.
        res = _mandar(_evento_factura_oferta2(cid, "in_2p_1", "subscription_create"))
        assert res == {"invoice": "paid", "client_id": cid}
        assert fake.sub_cancelaciones == []

        # Segundo pago (subscription_cycle): la suscripción se CANCELA.
        res = _mandar(_evento_factura_oferta2(cid, "in_2p_2", "subscription_cycle"))
        assert res == {"invoice": "paid", "client_id": cid}
        assert fake.sub_cancelaciones == ["sub_2p"]

        # La baja que Stripe emite tras la cancelación es un FIN natural: el
        # cliente sigue "pagado" y el feed lo cuenta como completada.
        res = _mandar({"type": "customer.subscription.deleted",
                       "data": {"object": {"id": "sub_2p",
                                           "metadata": {"client_id": str(cid)}}}})
        assert res == {"subscription_completed": cid}
        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "paid"
        assert c.stripe_subscription_id is None
        assert not any("Suscripción cancelada" in a.get("title", "") for a in avisos)
        fila = db.scalar(select(Payment).where(Payment.stripe_object_id == "sub_2p",
                                               Payment.status == "canceled"))
        assert fila is not None and "completada" in (fila.description or "")
    finally:
        db.close()


def test_webhook_baja_temprana_de_la_oferta2_es_impago(monkeypatch):
    """Si la suscripción de 2 pagos muere ANTES del segundo cobro (impagos
    agotados, baja manual), sí es una baja de verdad: pendiente + push."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    db = SessionLocal()
    try:
        c = _cliente_oferta2(db, sub_id="sub_2p_corta")
        cid = c.id
        # Solo consta UN pago en el libro.
        from app.services.payments import record_payment

        record_payment(db, object_id=f"in_2p_solo_{cid}", kind="invoice",
                       status="paid", amount_cents=12050, client=c,
                       billing_period="oferta2", description="pago 1 de 2")
        db.commit()

        event = {"type": "customer.subscription.deleted",
                 "data": {"object": {"id": "sub_2p_corta",
                                     "metadata": {"client_id": str(cid)}}}}
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"subscription_cancelled": cid}
        db.expire_all()
        assert db.get(Client, cid).payment_status == "pending"
        assert any("Suscripción cancelada" in a.get("title", "") for a in avisos)
    finally:
        db.close()


def test_oferta2_solo_full(monkeypatch):
    """El registro público rechaza train/nutri con la oferta en 2 pagos."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.routers import public_site

    # El limitador del MÓDULO (5/min por IP) se apaga solo aquí: la suite
    # entera comparte la IP del TestClient y este test corre tarde — sin esto
    # respondía 429 por cuota agotada, no lo que se prueba (el 422).
    monkeypatch.setattr(public_site.limiter, "enabled", False)
    with TestClient(app) as http:
        r = http.post("/api/public/register", json={
            "full_name": "No Puede", "email": f"no2-{uuid.uuid4().hex[:6]}@x.com",
            "phone": "600000001", "tier": "train", "period": "oferta2",
        })
        assert r.status_code == 422


def test_renovacion_de_la_oferta2_tras_completarse():
    """Completados los 2 pagos (suscripción ya cancelada y despegada), el
    programa de 3 meses acaba ~60 días después del segundo cobro: la ventana
    de renovación cuenta desde paid_at + 60."""
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from app.services.renewals import renewal_window

    hoy = datetime.now(timezone.utc)
    c = SimpleNamespace(payment_status="paid", stripe_subscription_id=None,
                        paid_at=hoy - timedelta(days=55), billing_period="oferta2")
    w = renewal_window(c, hoy.date())
    assert w is not None
    ends_on, dias = w
    assert dias == 5  # 60 − 55

    # Mientras la suscripción sigue viva, se cobra sola: sin ventana.
    c.stripe_subscription_id = "sub_2p"
    assert renewal_window(c, hoy.date()) is None


# ---- La OFERTA en 3 pagos también es un programa CERRADO: 1 € + 120 + 120 ----

def _cliente_oferta3(db, *, sub_id="sub_o3"):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name="Tres Pagos", email=f"o3-{uuid.uuid4().hex[:8]}@x.com",
               package_tier="full", billing_period="oferta", status="active",
               portal_token="p", payment_status="paid",
               stripe_subscription_id=sub_id)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _evento_factura_oferta3(cid: int, invoice_id: str, razon: str,
                            centimos: int) -> dict:
    return {"type": "invoice.paid", "data": {"object": {
        "id": invoice_id, "subscription": "sub_o3",
        "subscription_details": {"metadata": {"client_id": str(cid),
                                              "billing_period": "oferta"}},
        "billing_reason": razon, "amount_paid": centimos,
        "lines": {"data": [{"price": {"lookup_key": "dqr_full_oferta"}}]},
    }}}


def test_webhook_tercer_pago_detiene_la_oferta(monkeypatch):
    """La oferta del 1 € es el MISMO programa de 3 meses que la de 2 pagos:
    al cobrarse la TERCERA factura (1 € + 120 + 120) el webhook cancela la
    suscripción en Stripe — no hay cuarto cobro — y la baja posterior no
    marca al cliente como pendiente: el programa está pagado entero."""
    stripe_service = _prep(monkeypatch)
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Client, Payment
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    fake = FakeStripe()

    db = SessionLocal()
    try:
        c = _cliente_oferta3(db)
        cid = c.id

        def _mandar(evento):
            class _Hooked:
                Webhook = type("W", (), {
                    "construct_event": staticmethod(lambda *a, **k: evento)})
                Subscription = fake.Subscription

            monkeypatch.setattr(stripe_service, "_stripe", lambda: _Hooked)
            return stripe_service.handle_webhook(db, b"{}", "sig")

        # Pago 1 (1 €, subscription_create) y pago 2 (120 €): sin cancelar.
        res = _mandar(_evento_factura_oferta3(cid, "in_o3_1", "subscription_create", 100))
        assert res == {"invoice": "paid", "client_id": cid}
        res = _mandar(_evento_factura_oferta3(cid, "in_o3_2", "subscription_cycle", 12000))
        assert res == {"invoice": "paid", "client_id": cid}
        assert fake.sub_cancelaciones == []

        # Pago 3 (120 €): la suscripción se CANCELA — programa completo.
        res = _mandar(_evento_factura_oferta3(cid, "in_o3_3", "subscription_cycle", 12000))
        assert res == {"invoice": "paid", "client_id": cid}
        assert fake.sub_cancelaciones == ["sub_o3"]

        # La baja que emite Stripe tras la cancelación es un FIN natural.
        res = _mandar({"type": "customer.subscription.deleted",
                       "data": {"object": {"id": "sub_o3",
                                           "metadata": {"client_id": str(cid)}}}})
        assert res == {"subscription_completed": cid}
        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "paid"
        assert c.stripe_subscription_id is None
        assert not any("Suscripción cancelada" in a.get("title", "") for a in avisos)
        fila = db.scalar(select(Payment).where(Payment.stripe_object_id == "sub_o3",
                                               Payment.status == "canceled"))
        assert fila is not None and "1 € + 120 € + 120 €" in (fila.description or "")
    finally:
        db.close()


def test_una_segunda_contratacion_de_la_oferta_no_se_cancela_con_el_primer_euro(monkeypatch):
    """Un cliente que vuelve y contrata la oferta OTRA VEZ empieza de cero.

    El recuento miraba TODAS las facturas del cliente, de siempre: con las tres
    del programa anterior en el libro, su primera factura de 1 € ya sumaba
    cuatro, el sistema daba el programa por cobrado entero y cancelaba la
    suscripción. Tres meses de asesoría por un euro."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.services import push as push_svc
    from app.services.payments import record_payment

    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: None)
    fake = FakeStripe()

    db = SessionLocal()
    try:
        c = _cliente_oferta3(db, sub_id="sub_nueva")
        cid = c.id
        # El programa ANTERIOR, ya cobrado entero y con su suscripción muerta.
        for i, cents in enumerate((100, 12000, 12000)):
            record_payment(db, object_id=f"in_vieja_{cid}_{i}", kind="invoice",
                           status="paid", amount_cents=cents, client=c,
                           billing_period="oferta", description=f"pago {i + 1} de 3",
                           subscription_id="sub_vieja")
        db.commit()

        def _mandar(evento):
            class _Hooked:
                Webhook = type("W", (), {
                    "construct_event": staticmethod(lambda *a, **k: evento)})
                Subscription = fake.Subscription

            monkeypatch.setattr(stripe_service, "_stripe", lambda: _Hooked)
            return stripe_service.handle_webhook(db, b"{}", "sig")

        def _factura(invoice_id, razon, centimos):
            ev = _evento_factura_oferta3(cid, invoice_id, razon, centimos)
            ev["data"]["object"]["subscription"] = "sub_nueva"
            return ev

        # Primera factura de la contratación NUEVA: 1 €. No puede cancelar.
        assert _mandar(_factura("in_nueva_1", "subscription_create", 100)) == \
            {"invoice": "paid", "client_id": cid}
        assert fake.sub_cancelaciones == [], "canceló el programa nuevo cobrando 1 €"

        # Y cuando SÍ se completa el programa nuevo, se cancela como debe.
        _mandar(_factura("in_nueva_2", "subscription_cycle", 12000))
        assert fake.sub_cancelaciones == []
        _mandar(_factura("in_nueva_3", "subscription_cycle", 12000))
        assert fake.sub_cancelaciones == ["sub_nueva"]
    finally:
        db.close()


def test_webhook_baja_temprana_de_la_oferta3_es_impago(monkeypatch):
    """Si la suscripción de la oferta muere ANTES del tercer cobro (impagos
    agotados, baja manual), sí es una baja de verdad: pendiente + push."""
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.services import push as push_svc

    avisos = []
    monkeypatch.setattr(push_svc, "send_to_coach", lambda db, payload: avisos.append(payload))

    db = SessionLocal()
    try:
        c = _cliente_oferta3(db, sub_id="sub_o3_corta")
        cid = c.id
        # Solo constan DOS pagos en el libro (1 € + 120 €): falta el tercero.
        from app.services.payments import record_payment

        record_payment(db, object_id=f"in_o3a_{cid}", kind="invoice",
                       status="paid", amount_cents=100, client=c,
                       billing_period="oferta", description="pago 1 de 3")
        record_payment(db, object_id=f"in_o3b_{cid}", kind="invoice",
                       status="paid", amount_cents=12000, client=c,
                       billing_period="oferta", description="pago 2 de 3")
        db.commit()

        event = {"type": "customer.subscription.deleted",
                 "data": {"object": {"id": "sub_o3_corta",
                                     "metadata": {"client_id": str(cid)}}}}
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res == {"subscription_cancelled": cid}
        db.expire_all()
        assert db.get(Client, cid).payment_status == "pending"
        assert any("Suscripción cancelada" in a.get("title", "") for a in avisos)
    finally:
        db.close()


def test_renovacion_de_la_oferta3_tras_completarse():
    """Completados los 3 pagos (suscripción cancelada y despegada), el
    programa acaba ~30 días después del TERCER cobro: la ventana de renovación
    cuenta desde paid_at + 30. Con la suscripción viva, nunca avisa."""
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from app.services.renewals import renewal_window

    hoy = datetime.now(timezone.utc)
    c = SimpleNamespace(payment_status="paid", stripe_subscription_id=None,
                        paid_at=hoy - timedelta(days=25), billing_period="oferta")
    w = renewal_window(c, hoy.date())
    assert w is not None and w[1] == 5  # 30 − 25
    viva = SimpleNamespace(payment_status="paid", stripe_subscription_id="sub_x",
                           paid_at=hoy - timedelta(days=200), billing_period="oferta")
    assert renewal_window(viva, hoy.date()) is None


def test_describe_de_la_oferta3():
    from app.services.payments import describe

    assert describe("full", "oferta", kind="invoice",
                    billing_reason="subscription_create") == \
        "DQR Full · oferta (pago 1 de 3 · 1 €)"
    assert describe("full", "oferta", kind="invoice",
                    billing_reason="subscription_cycle") == \
        "DQR Full · oferta (pago 2 o 3 de 3)"


def test_describe_oferta2():
    """El feed de pagos dice cuál de los dos pagos es cada movimiento."""
    from app.services.payments import describe

    assert describe("full", "oferta2", kind="invoice",
                    billing_reason="subscription_create").endswith("pago 1 de 2)")
    assert describe("full", "oferta2", kind="invoice",
                    billing_reason="subscription_cycle").endswith("pago 2 de 2)")


# --- Enlace ESTABLE del cliente: que lleve a Stripe y cobre lo que toca ------

def test_renovar_a_un_cliente_de_la_oferta_no_le_revende_la_oferta(monkeypatch):
    """REGRESIÓN (dinero): al renovar a alguien que entró por la oferta, el
    enlace le abría OTRO programa de 3 meses con el primer mes a 1 € — el coach
    creía estar cobrando la renovación. Debe cobrarle su plan MENSUAL."""
    from datetime import datetime, timedelta, timezone

    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.routers import stripe_router as sr

    db = SessionLocal()
    c = _cliente_oferta3(db, sub_id="")          # programa ya completado
    c.stripe_subscription_id = None
    # 32 días desde el último cobro: el programa (30 d) ya venció → toca renovar
    c.paid_at = datetime.now(timezone.utc) - timedelta(days=32)
    db.commit()
    token = c.portal_token
    db.close()

    pedidos = []
    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: (pedidos.append((t, p)) or f"https://stripe.test/{t}/{p}"))
    with TestClient(app) as http:
        r = http.get(f"/api/pay/{token}", follow_redirects=False)
    assert r.status_code == 302, r.text
    assert r.headers["location"].startswith("https://stripe.test/"), r.headers
    assert pedidos and pedidos[-1] == ("full", "1m"), pedidos


def test_enlace_de_pago_caducado_no_enseña_json_crudo():
    """REGRESIÓN: si al cliente se le regenera el acceso al portal, su enlace de
    pago viejo devolvía {"detail":"No encontrado"} en crudo. Ahora es una página
    que le dice qué hacer."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as http:
        r = http.get("/api/pay/token-que-ya-no-vale", follow_redirects=False)
    assert r.status_code in (403, 404)
    assert "text/html" in r.headers.get("content-type", "")
    assert "ya no vale" in r.text


def test_la_vista_previa_de_whatsapp_no_crea_sesiones_de_pago(monkeypatch):
    """REGRESIÓN: cada previsualización del mensaje del coach abría una sesión
    REAL en Stripe (y enseñaba a dónde llevaba el enlace). Ahora se le da una
    mini-página; una persona sale de ella con el botón."""
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.routers import stripe_router as sr

    db = SessionLocal()
    c = _cliente_oferta3(db, sub_id="")
    c.stripe_subscription_id = None
    c.payment_status = "pending"
    db.commit()
    token = c.portal_token
    db.close()

    creadas = []
    monkeypatch.setattr(sr, "create_checkout_url",
                        lambda db, t, p, **kw: (creadas.append((t, p)) or "https://stripe.test/x"))
    cabecera = {"user-agent": "WhatsApp/2.23"}
    with TestClient(app) as http:
        r = http.get(f"/api/pay/{token}", headers=cabecera, follow_redirects=False)
        assert r.status_code == 200 and "text/html" in r.headers.get("content-type", "")
        assert not creadas, "la vista previa creó una sesión de pago"
        # La persona que caiga ahí sale con el botón (?ir=1).
        r2 = http.get(f"/api/pay/{token}?ir=1", headers=cabecera, follow_redirects=False)
        assert r2.status_code == 302 and creadas



def test_al_completar_la_oferta_la_ficha_suelta_la_suscripcion(monkeypatch):
    """DINERO SILENCIOSO. `renewals.renewal_window` devuelve None mientras la
    ficha lleve una suscripción ("se cobra sola, no hay nada que avisar"). El
    corte de la oferta la cancelaba EN STRIPE y dejaba el id puesto, así que
    ese cliente no volvía a entrar NUNCA en la ventana de renovación: ni email
    al cliente, ni alerta `renewal_due` al coach, ni reapertura del enlace de
    pago. El programa terminaba y no se enteraba nadie.

    Solo lo limpiaba el webhook `customer.subscription.deleted`; si se perdía
    —o el corte venía del backstop diario— no lo limpiaba nadie."""
    from datetime import date, datetime, timedelta, timezone

    from app.db import SessionLocal
    from app.models import Client
    from app.services import stripe_service
    from app.services.renewals import is_due, renewal_window

    class _Sub:
        @staticmethod
        def cancel(sub_id):
            return {"id": sub_id, "status": "canceled"}

    monkeypatch.setattr(stripe_service, "_stripe",
                        lambda: type("S", (), {"Subscription": _Sub})())

    db = SessionLocal()
    c = _cliente_oferta3(db, sub_id="sub_suelta")
    # Programa terminado hace 31 días: toca renovar.
    c.paid_at = datetime.now(timezone.utc) - timedelta(days=31)
    db.commit()
    cid = c.id
    try:
        # Con la suscripción en la ficha, la renovación NO existe.
        assert renewal_window(c, date.today()) is None

        assert stripe_service.detener_suscripcion_oferta(
            db, c, c.stripe_subscription_id, motivo="test", periodo="oferta") is True
        db.commit()
        db.refresh(c)

        assert c.stripe_subscription_id is None
        assert renewal_window(c, date.today()) is not None
        assert is_due(c, date.today()) is True
    finally:
        from sqlalchemy import delete

        from app.models import Payment

        db.execute(delete(Payment).where(Payment.client_id == cid))
        db.execute(delete(Client).where(Client.id == cid))
        db.commit()
        db.close()
