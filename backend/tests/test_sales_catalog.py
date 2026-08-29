"""Catálogo de VENTA del panel (pantalla "Vender").

Lo que se prueba aquí es lo que el coach ve ANTES de mandar un enlace: importes
reales, condiciones de cada oferta y —sobre todo— si ese enlace va a poder
cobrar. Un enlace que no abre Stripe tiene que salir marcado, no enviarse.
"""
import warnings

warnings.filterwarnings("ignore")


class _PreciosFalsos:
    """Stripe mínimo: devuelve precios por lookup_key e impone su límite real."""

    def __init__(self, *, faltan=(), moneda="eur", cupon=True):
        self.faltan = set(faltan)
        self.moneda = moneda
        self.cupon = cupon
        self.tandas: list[list[str]] = []
        fake = self

        class Price:
            @staticmethod
            def list(lookup_keys=None, **kw):
                # Stripe rechaza más de 10 lookup_keys por llamada.
                assert lookup_keys is not None and len(lookup_keys) <= 10
                fake.tandas.append(list(lookup_keys))
                datos = []
                for k in lookup_keys:
                    if k in fake.faltan:
                        continue
                    cents = (12000 if k == "dqr_full_oferta"
                             else 12050 if k == "dqr_full_oferta2" else 6900)
                    datos.append({"id": f"pr_{k}", "lookup_key": k, "active": True,
                                  "unit_amount": cents, "currency": fake.moneda})
                return {"data": datos}

        class Coupon:
            @staticmethod
            def retrieve(cid):
                if not fake.cupon:
                    raise KeyError(cid)
                return {"id": cid, "valid": True}

        self.Price = Price
        self.Coupon = Coupon


def _catalogo(monkeypatch, fake, **over):
    from app.config import settings
    from app.services import sales_catalog as sc
    from app.services import stripe_service as ss

    monkeypatch.setattr(settings, "stripe_secret_key", over.get("key", "sk_live_x"))
    monkeypatch.setattr(ss, "_stripe", lambda: fake)
    monkeypatch.setattr(sc, "_CACHE", {"data": None, "at": 0.0})
    return sc.sales_catalog(refresh=True)


def test_el_catalogo_trae_las_dos_ofertas_con_sus_condiciones(monkeypatch):
    fake = _PreciosFalsos()
    cat = _catalogo(monkeypatch, fake)

    ofertas = {i["key"]: i for i in cat["items"] if i["kind"] == "oferta"}
    assert set(ofertas) == {"oferta", "oferta2"}

    tres = ofertas["oferta"]
    assert tres["charges"] == 3 and tres["total_eur"] == 241.0
    # El CALENDARIO lo calcula el backend (el panel no hace cuentas).
    assert [(c["when"], c["eur"]) for c in tres["schedule"]] == [
        ("Hoy", 1.0), ("Al mes", 120.0), ("A los 2 meses", 120.0)]
    assert tres["first_eur"] == 1.0 and tres["auto_stop"] is True
    assert tres["url"].endswith("/api/pay/plan/full/oferta")
    assert tres["ready"] is True

    dos = ofertas["oferta2"]
    assert dos["charges"] == 2 and dos["total_eur"] == 241.0
    assert dos["first_eur"] == 120.5
    assert "120,50 €" in dos["subtitle"]          # en español, con coma
    assert [(c["when"], c["eur"]) for c in dos["schedule"]] == [
        ("Hoy", 120.5), ("Al mes", 120.5)]
    assert dos["url"].endswith("/api/pay/plan/full/oferta2")

    # Y los 9 planes sueltos, cada uno con su enlace.
    planes = [i for i in cat["items"] if i["kind"] == "plan"]
    assert len(planes) == 9 and all(p["charges"] == 1 for p in planes)
    # Un plan es UN pago y no se renueva solo: es lo que pregunta el cliente.
    assert all(p["auto_stop"] is False and len(p["schedule"]) == 1 for p in planes)
    assert all("no se renueva solo" in p["subtitle"] for p in planes)


def test_nunca_se_piden_mas_de_diez_lookup_keys(monkeypatch):
    """El fallo que dejó los enlaces de la oferta sin abrir Stripe: once claves
    en una sola llamada. El catálogo las pide troceadas."""
    fake = _PreciosFalsos()
    _catalogo(monkeypatch, fake)
    assert fake.tandas and all(len(t) <= 10 for t in fake.tandas)
    pedidas = {k for t in fake.tandas for k in t}
    assert {"dqr_full_oferta", "dqr_full_oferta2"} <= pedidas


def test_un_precio_que_falta_en_stripe_sale_marcado(monkeypatch):
    """El coach tiene que saber ANTES de enviarlo que ese enlace no cobra."""
    fake = _PreciosFalsos(faltan={"dqr_full_oferta2"})
    cat = _catalogo(monkeypatch, fake)
    dos = next(i for i in cat["items"] if i["key"] == "oferta2")
    assert dos["ready"] is False
    assert "Falta el precio" in (dos["issue"] or "")
    # Aun así se muestra el importe (el canónico) para no dejar la tarjeta muda.
    assert dos["total_eur"] == 241.0


def test_sin_cupon_la_oferta_de_tres_pagos_no_se_puede_enviar(monkeypatch):
    """Sin el cupón del primer mes a 1 €, el checkout falla al crearse y el
    cliente acababa en /planes. La tarjeta lo dice de antemano."""
    fake = _PreciosFalsos(cupon=False)
    cat = _catalogo(monkeypatch, fake)
    tres = next(i for i in cat["items"] if i["key"] == "oferta")
    assert tres["ready"] is False and "cupón" in (tres["issue"] or "")
    # La de 2 pagos NO usa cupón: esa sigue disponible.
    dos = next(i for i in cat["items"] if i["key"] == "oferta2")
    assert dos["ready"] is True


def test_modo_prueba_se_avisa(monkeypatch):
    """Con claves de test los enlaces no cobran dinero real: el panel avisa."""
    cat = _catalogo(monkeypatch, _PreciosFalsos(), key="sk_test_x")
    assert cat["test_mode"] is True


def test_sin_stripe_configurado_nada_es_enviable(monkeypatch):
    cat = _catalogo(monkeypatch, _PreciosFalsos(), key="")
    assert cat["stripe_enabled"] is False
    assert all(i["ready"] is False for i in cat["items"])
    assert all("no está configurado" in (i["issue"] or "") for i in cat["items"])


# --- El enlace de UN cliente: el coach tiene que saber qué hará al abrirlo ---

def _cliente(db, **over):
    from app.models import Client
    from app.security import new_portal_token
    import uuid

    campos = dict(full_name="Enlace Cliente", email=f"lnk-{uuid.uuid4().hex[:8]}@test.local",
                  package_tier="full", billing_period="1m", status="active",
                  portal_token="p", payment_status="pending")
    campos.update(over)
    c = Client(**campos)
    db.add(c); db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def test_el_enlace_de_un_cliente_dice_si_va_a_cobrar():
    """Antes el coach lo mandaba a ciegas: si el cliente ya había pagado, el
    enlace le llevaba a "¡Pago recibido!" y parecía roto."""
    import os

    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.security import create_access_token

    db = SessionLocal()
    pendiente = _cliente(db)
    pagado = _cliente(db, payment_status="paid")
    db.close()

    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    with TestClient(app) as http:
        r1 = http.get(f"/api/sales/client-link/{pendiente.id}", headers=auth).json()
        assert r1["state"] == "cobra" and r1["url"].endswith(f"/api/pay/{pendiente.portal_token}")
        assert "abre el pago" in r1["note"]

        r2 = http.get(f"/api/sales/client-link/{pagado.id}", headers=auth).json()
        assert r2["state"] == "pagado" and "NO le cobra" in r2["note"]

