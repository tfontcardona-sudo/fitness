"""EL SWITCH DE MARCA: el mismo sistema llevando dos negocios.

La maquinaria es la misma para las dos (motor de cálculo, guardarraíles, ciclo
quincenal, portal). Lo que cambia es lo que se VE y lo que se VENDE: nombre,
colores, nombres de los servicios, tarifas y precios de Stripe.

Lo que estos tests blindan, que es donde estaría el desastre:
- pulsar el switch NO le cambia la marca a un cliente que ya está pagando;
- los precios de Stripe de las dos marcas NUNCA comparten `lookup_key` (si la
  compartieran, activar una marca reescribiría el precio de la otra y con él
  las suscripciones en marcha);
- solo puede haber UNA marca activa, y lo garantiza la base.
"""
import os
import uuid

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


@pytest.fixture()
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


@pytest.fixture()
def restaura_marca(db):
    """Deja la marca activa como estaba: la base de pruebas es compartida."""
    from sqlalchemy import select, update

    from app.models import BrandConfig
    from app.services.branding import invalidar

    antes = db.scalar(select(BrandConfig.id).where(BrandConfig.activa.is_(True)))
    yield
    if antes is not None:
        db.execute(update(BrandConfig).values(activa=False))
        db.flush()
        db.get(BrandConfig, antes).activa = True
        db.commit()
    invalidar()


def _marcas(db):
    from sqlalchemy import select

    from app.models import BrandConfig

    return {b.slug: b for b in db.scalars(select(BrandConfig)).all()}


def test_hay_dos_perfiles_y_solo_uno_activo(db):
    from app.services import branding

    ms = _marcas(db)
    assert "dqr" in ms and "professional-fitness" in ms
    assert sum(1 for b in ms.values() if b.activa) == 1


def test_la_base_impide_dos_marcas_activas_a_la_vez(db, restaura_marca):
    """No depende del cuidado de quien programe: es un índice único parcial."""
    from sqlalchemy.exc import IntegrityError

    ms = _marcas(db)
    otra = ms["professional-fitness"] if ms["dqr"].activa else ms["dqr"]
    otra.activa = True                      # ya hay una activa: choca
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_el_switch_cambia_el_escaparate_pero_no_a_quien_ya_paga(http, db, restaura_marca):
    from app.models import Client
    from app.security import new_portal_token
    from app.services import branding, packages as pkgs

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    # Un cliente que entra AHORA queda sellado con la marca del escaparate.
    c = Client(full_name="Cliente de DQR", email=f"marca-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active", package_tier="full", brand_id=dqr.id)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()

    branding.invalidar()
    assert branding.marca_activa(db).slug == "dqr"
    assert pkgs.label("full") == "DQR Full"

    r = http.post(f"/api/brand/{pf.id}/activar", headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "professional-fitness"
    # El endpoint corre en SU sesión: esta tiene las filas en memoria con el
    # valor viejo hasta que se expiran (no es un fallo del switch).
    db.expire_all()

    # El ESCAPARATE es otro…
    assert branding.marca_activa(db).slug == "professional-fitness"
    assert pkgs.label("full") == "Professional Full"
    assert branding.marca_activa(db).page_title == "Professional Fitness"
    # …pero el cliente que ya estaba sigue en la suya.
    db.expire_all()
    assert branding.marca_de_cliente(db.get(Client, c.id), db).slug == "dqr"
    assert pkgs.label("full", branding.marca_de_cliente(db.get(Client, c.id), db)) == "DQR Full"

    db.delete(db.get(Client, c.id))
    db.commit()


def test_los_precios_de_stripe_de_las_dos_marcas_nunca_se_pisan(db):
    """Si dos marcas compartieran `lookup_key`, activar una reescribiría el
    precio de la otra — y con él lo que se cobra a sus suscripciones vivas."""
    from app.services import branding

    ms = _marcas(db)
    a = branding.marca_por_id(ms["dqr"].id, db)
    b = branding.marca_por_id(ms["professional-fitness"].id, db)
    claves_a = {a.lookup_key(t, p) for t in ("train", "nutri", "full")
                for p in ("1m", "3m", "6m", "oferta", "oferta2")}
    claves_b = {b.lookup_key(t, p) for t in ("train", "nutri", "full")
                for p in ("1m", "3m", "6m", "oferta", "oferta2")}
    assert claves_a & claves_b == set()
    assert a.lookup_key("full", "1m") == "dqr_full_1m"
    assert b.lookup_key("full", "1m") == "pf_full_1m"


def test_cada_marca_tiene_sus_tarifas_y_sus_nombres(db):
    from app.services import branding

    ms = _marcas(db)
    dqr = branding.marca_por_id(ms["dqr"].id, db)
    assert dqr.importe("full", "1m") == 12900 and dqr.importe("train", "6m") == 32400
    assert dqr.oferta()["first_month_cents"] == 100
    assert dqr.label("full") == "DQR Full"
    pf = branding.marca_por_id(ms["professional-fitness"].id, db)
    assert pf.label("full") == "Professional Full"
    # Las tarifas son SUYAS: cambiarlas en una no toca a la otra.
    assert pf.prices is not dqr.prices


def test_el_selector_del_panel_lista_las_marcas(http, db):
    r = http.get("/api/brand/perfiles", headers=_auth())
    assert r.status_code == 200, r.text
    slugs = {m["slug"]: m for m in r.json()}
    assert {"dqr", "professional-fitness"} <= set(slugs)
    assert sum(1 for m in r.json() if m["activa"]) == 1
    assert slugs["professional-fitness"]["service_labels"]["full"] == "Professional Full"


def test_lo_que_edita_el_coach_va_a_la_marca_activa(http, db, restaura_marca):
    """El switch te mete DENTRO del otro programa: lo que edites después es
    suyo. Antes, con dos filas, un `limit(1)` sin orden escribía en una
    cualquiera y el coach editaba a ciegas la marca equivocada."""
    from app.models import BrandConfig

    ms = _marcas(db)
    pf_id = ms["professional-fitness"].id
    dqr_nombre = ms["dqr"].name
    assert http.post(f"/api/brand/{pf_id}/activar", headers=_auth()).status_code == 200

    actual = http.get("/api/brand", headers=_auth()).json()
    assert actual["slug"] == "professional-fitness"
    cuerpo = {k: actual[k] for k in (
        "name", "color_primary", "color_secondary", "color_bg", "font_family",
        "tagline", "contact_email", "contact_phone", "contact_web", "portal_theme",
        "partner_store_url", "partner_discount_code", "meet_url")}
    cuerpo["name"] = "Professional Fitness · editado"
    assert http.put("/api/brand", headers=_auth(), json=cuerpo).status_code == 200

    db.expire_all()
    assert db.get(BrandConfig, pf_id).name == "Professional Fitness · editado"
    assert _marcas(db)["dqr"].name == dqr_nombre        # DQR, intacta
    db.get(BrandConfig, pf_id).name = "Professional Fitness"
    db.commit()
