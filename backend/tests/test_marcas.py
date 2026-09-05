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
    # El nombre comercial es el de VERDAD del centro (mig. 0045), no un
    # "Professional Full" calcado de DQR: cada marca nombra lo suyo.
    assert pkgs.label("full") == "Génesis.99"
    assert branding.marca_activa(db).page_title == "Professional · Centre Salut & Fitness"
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
    assert pf.label("full") == "Génesis.99"
    # Professional vende UNA sola cosa por la web (99 €/mes) y no tiene oferta
    # de captación: lo que no está en `prices` no se vende ni se le crea precio
    # en Stripe. Sus otros servicios se cobran en el centro.
    assert pf.importe("full", "1m") == 9900
    assert pf.importe("full", "3m") is None and pf.importe("train", "1m") is None
    assert pf.vende() == [("full", "1m")]
    assert not pf.vende_oferta()
    assert dqr.vende_oferta()
    assert len(pf.extra_services) == 4        # entreno personal y packs del centro
    assert "Girona" in (pf.contact_address or "")
    # Las tarifas son SUYAS: cambiarlas en una no toca a la otra.
    assert pf.prices is not dqr.prices


def test_el_selector_del_panel_lista_las_marcas(http, db):
    r = http.get("/api/brand/perfiles", headers=_auth())
    assert r.status_code == 200, r.text
    slugs = {m["slug"]: m for m in r.json()}
    assert {"dqr", "professional-fitness"} <= set(slugs)
    assert sum(1 for m in r.json() if m["activa"]) == 1
    assert slugs["professional-fitness"]["service_labels"]["full"] == "Génesis.99"


def test_lo_que_edita_el_coach_va_a_la_marca_activa(http, db, restaura_marca):
    """El switch te mete DENTRO del otro programa: lo que edites después es
    suyo. Antes, con dos filas, un `limit(1)` sin orden escribía en una
    cualquiera y el coach editaba a ciegas la marca equivocada."""
    from app.models import BrandConfig

    ms = _marcas(db)
    pf_id = ms["professional-fitness"].id
    pf_nombre, pf_dir = ms["professional-fitness"].name, ms["professional-fitness"].contact_address
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
    # Y lo que el formulario NO manda no se borra: la dirección del centro no
    # está en la pantalla de marca y guardar los colores la dejaba en blanco.
    assert db.get(BrandConfig, pf_id).contact_address == pf_dir
    db.get(BrandConfig, pf_id).name = pf_nombre
    db.commit()


# --------------------------------------------------------------------------
# CADA NEGOCIO, SU CARTERA. El switch no es solo un cambio de colores: con la
# marca de Professional puesta, el panel enseña la cartera, las alertas y el
# libro de caja de Professional. Los de DQR ni aparecen ni se tocan.
# --------------------------------------------------------------------------

def _cliente_de(db, marca, nombre):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name=nombre, email=f"cart-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active", package_tier="full",
               brand_id=marca.id)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def _activar(http, db, marca_id):
    r = http.post(f"/api/brand/{marca_id}/activar", headers=_auth())
    assert r.status_code == 200, r.text
    # El switch corre en la sesión del endpoint; esta se quedó con las filas
    # viejas en memoria hasta expirarlas. No es un fallo del switch: en
    # producción cada petición trae su propia sesión.
    db.expire_all()


def test_el_panel_solo_enseña_la_cartera_de_la_marca_activa(http, db, restaura_marca):
    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    uno = _cliente_de(db, dqr, "Cartera DQR")
    otro = _cliente_de(db, pf, "Cartera Professional")

    _activar(http, db, dqr.id)
    ids = {c["id"] for c in http.get("/api/clients", headers=_auth()).json()}
    assert uno.id in ids and otro.id not in ids

    _activar(http, db, pf.id)
    ids = {c["id"] for c in http.get("/api/clients", headers=_auth()).json()}
    assert otro.id in ids and uno.id not in ids


def test_la_campana_no_suena_por_clientes_de_la_otra_marca(http, db, restaura_marca):
    """Las alertas son del negocio que se está llevando; los avisos de SISTEMA
    (automatismos parados) no son de ningún negocio y salen siempre."""
    from app.routers import alerts as al

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    # Un cliente de DQR con motivo de alerta seguro: activo y sin plan.
    victima = _cliente_de(db, dqr, "Sin plan DQR")

    _activar(http, db, dqr.id)
    de_dqr = http.get("/api/alerts", headers=_auth()).json()["alerts"]
    assert any(a["client_id"] == victima.id for a in de_dqr)

    _activar(http, db, pf.id)
    de_pf = http.get("/api/alerts", headers=_auth()).json()["alerts"]
    assert not any(a["client_id"] == victima.id for a in de_pf)


def test_el_libro_de_caja_se_lleva_por_negocio_y_los_huerfanos_salen_en_los_dos(
        http, db, restaura_marca):
    from datetime import datetime, timezone

    from app.models import Payment
    from app.services import payments as pay

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    cli = _cliente_de(db, dqr, "Paga en DQR")
    marca_id = uuid.uuid4().hex[:8]
    ahora = datetime.now(timezone.utc)
    db.add(Payment(stripe_object_id=f"ch_dqr_{marca_id}", kind="checkout", status="paid",
                   amount_cents=12900, currency="eur", livemode=True,
                   client_id=cli.id, paid_at=ahora))
    db.add(Payment(stripe_object_id=f"ch_orf_{marca_id}", kind="checkout", status="paid",
                   amount_cents=5000, currency="eur", livemode=True,
                   client_id=None, paid_at=ahora))
    db.commit()

    _activar(http, db, dqr.id)
    filas, _ = pay.list_payments(db, limit=100)
    ids = {p.stripe_object_id for p in filas}
    assert f"ch_dqr_{marca_id}" in ids and f"ch_orf_{marca_id}" in ids

    _activar(http, db, pf.id)
    filas, _ = pay.list_payments(db, limit=100)
    ids = {p.stripe_object_id for p in filas}
    # El cobro de DQR desaparece del libro de Professional; el HUÉRFANO no:
    # es dinero que entró y que nadie ha sabido atribuir, y esconderlo en la
    # marca que no toca es la forma de perderlo de vista para siempre.
    assert f"ch_dqr_{marca_id}" not in ids
    assert f"ch_orf_{marca_id}" in ids


def test_los_ingresos_del_mes_no_mezclan_los_dos_negocios(http, db, restaura_marca):
    from datetime import datetime, timezone

    from app.models import Payment
    from app.services import payments as pay

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    cli = _cliente_de(db, dqr, "Ingreso DQR")
    db.add(Payment(stripe_object_id=f"ch_mes_{uuid.uuid4().hex[:8]}", kind="checkout",
                   status="paid", amount_cents=9900, currency="eur", livemode=True,
                   client_id=cli.id, paid_at=datetime.now(timezone.utc)))
    db.commit()

    _activar(http, db, dqr.id)
    con_dqr = pay.summary(db)["month_total_cents"]
    _activar(http, db, pf.id)
    con_pf = pay.summary(db)["month_total_cents"]
    assert con_dqr - con_pf >= 9900


def test_el_portal_no_enseña_los_productos_de_la_otra_marca(db, restaura_marca):
    """La fuga que más se vería: los enlaces de afiliado de un negocio en el
    portal de los clientes del otro."""
    from sqlalchemy import select

    from app.models import RecommendedProduct
    from app.services.branding import invalidar, productos_de_la_marca

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    sufijo = uuid.uuid4().hex[:8]
    solo_dqr = RecommendedProduct(brand_id=dqr.id, title=f"Proteína DQR {sufijo}",
                                  url="https://example.com/a", active=True)
    comun = RecommendedProduct(brand_id=None, title=f"Cinturón común {sufijo}",
                               url="https://example.com/b", active=True)
    db.add_all([solo_dqr, comun])
    db.commit()
    invalidar()

    cli_pf = _cliente_de(db, pf, "Cliente Professional")
    visibles = set(db.scalars(
        select(RecommendedProduct.title).where(productos_de_la_marca(db, cli_pf))))
    assert f"Proteína DQR {sufijo}" not in visibles
    assert f"Cinturón común {sufijo}" in visibles      # el genérico sí

    cli_dqr = _cliente_de(db, dqr, "Cliente DQR")
    visibles = set(db.scalars(
        select(RecommendedProduct.title).where(productos_de_la_marca(db, cli_dqr))))
    assert {f"Proteína DQR {sufijo}", f"Cinturón común {sufijo}"} <= visibles


def test_el_resumen_semanal_del_coach_lleva_a_todos_y_dice_de_que_marca(
        db, restaura_marca):
    """El correo del lunes NO se filtra a propósito: cambiar el switch un
    viernes no puede dejar a media cartera sin vigilar."""
    from app.services.weekly_digest import build_digest

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    a = _cliente_de(db, dqr, "Semanal DQR")
    b = _cliente_de(db, pf, "Semanal Professional")

    d = build_digest(db)
    por_id = {c.client_id: c for c in d.clients}
    assert a.id in por_id and b.id in por_id
    assert por_id[a.id].brand and por_id[b.id].brand
    assert por_id[a.id].brand != por_id[b.id].brand


# --------------------------------------------------------------------------
# LA IDENTIDAD VISIBLE. Lo que el cliente ve —su portal, su cuestionario, su
# documento— es de SU marca; el escaparate público, de la activa.
# --------------------------------------------------------------------------

def test_el_cuestionario_de_una_marca_simple_es_mas_corto_y_tiene_lo_suyo(db, restaura_marca):
    """La anamnesis cambia de PIEL y de extras, nunca de sustancia: las
    preguntas de las que salen los números son las mismas."""
    from app.services.anamnesis_variant import anexar_respuestas, definicion

    completa = definicion("dq")
    simple = definicion("simple")
    assert completa["optional_blocks"] and not simple["optional_blocks"]
    assert not completa["extra_questions"] and simple["extra_questions"]
    # Una variante desconocida NO adelgaza el formulario: ante la duda, se
    # pregunta de más.
    assert definicion("loquesea") == completa

    # Las respuestas propias van etiquetadas a las notas, y lo que la marca no
    # pregunta se descarta (el cuerpo llega del navegador del cliente).
    notas = anexar_respuestas("Duerme mal", "simple",
                              {"socio": "Sí", "inventado": "borra la ficha"})
    assert "Duerme mal" in notas and "¿Eres socio del centro?] Sí" in notas
    assert "borra la ficha" not in notas


def test_el_portal_y_el_cuestionario_llevan_la_marca_del_cliente(http, db, restaura_marca):
    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    cli = _cliente_de(db, pf, "Cliente del centro")
    cli.status = "onboarding"
    db.commit()

    # Con el escaparate en DQR, el cliente de Professional sigue viendo lo suyo.
    _activar(http, db, dqr.id)
    st = http.get(f"/api/p/{cli.portal_token}").json()
    assert st["brand_name"] == _marcas(db)["professional-fitness"].name
    assert st["anamnesis_variant"] == "simple"
    assert st["optional_blocks"] == []
    assert [q["key"] for q in st["extra_questions"]] == ["socio", "horario"]

    # Y el manifest de la app que instala en el móvil, también.
    mf = http.get(f"/api/p/{cli.portal_token}/manifest.webmanifest").json()
    assert "Professional" in mf["name"] and "Professional" in mf["short_name"]


def test_el_documento_del_cliente_lleva_el_logo_y_el_pie_de_su_marca(db, restaura_marca):
    from app.services.plan_delivery import doc_brand

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    cli = _cliente_de(db, pf, "Documento del centro")
    marca_doc = doc_brand(db, cli)
    assert marca_doc.name == pf.name
    # El pie de un centro lleva su teléfono y su dirección, no solo un email.
    assert marca_doc.contact_phone and marca_doc.contact_address
    assert doc_brand(db, _cliente_de(db, dqr, "Documento DQR")).name == dqr.name


def test_el_escaparate_publico_no_ofrece_una_oferta_que_la_marca_no_tiene(
        http, db, restaura_marca):
    """La tarjeta del primer mes a 1 € estaba clavada en la página de enlaces:
    en una marca sin oferta llevaba a un checkout que no existe."""
    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]

    _activar(http, db, dqr.id)
    assert http.get("/api/public/landing").json()["has_offer"] is True

    _activar(http, db, pf.id)
    landing = http.get("/api/public/landing").json()
    assert landing["has_offer"] is False
    assert "Girona" in (landing["contact_address"] or "")


def test_el_catalogo_de_venta_solo_enseña_lo_que_la_marca_vende(http, db, restaura_marca):
    from app.services.sales_catalog import sales_catalog

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]

    _activar(http, db, pf.id)
    cat = sales_catalog(refresh=True)
    assert [i["key"] for i in cat["items"]] == ["full-1m"]
    assert cat["items"][0]["total_eur"] == 99.0
    assert len(cat["extra_services"]) == 4      # lo que se cobra en el centro
    assert cat["brand"]["slug"] == "professional-fitness"

    _activar(http, db, dqr.id)
    cat = sales_catalog(refresh=True)
    assert "oferta" in [i["key"] for i in cat["items"]]
    assert len(cat["items"]) > 5


def test_el_switch_no_deja_caliente_la_tarifa_del_negocio_anterior(http, db, restaura_marca):
    """`/planes` cachea los precios 10 minutos: sin invalidar al cambiar, la
    página seguía enseñando las tarifas del otro negocio."""
    from app.services import sales_catalog as sc, stripe_service as ss

    ms = _marcas(db)
    dqr, pf = ms["dqr"], ms["professional-fitness"]
    _activar(http, db, dqr.id)
    sales = sc.sales_catalog(refresh=True)
    assert sales["brand"]["slug"] == "dqr"
    assert sc._CACHE["data"] is not None

    _activar(http, db, pf.id)
    # El switch tira las cachés que dependen de la marca.
    assert sc._CACHE["data"] is None
    assert ss._prices_cache["data"] is None
    assert sc.sales_catalog()["brand"]["slug"] == "professional-fitness"


def test_el_selector_dice_cuantos_clientes_lleva_cada_negocio(http, db, restaura_marca):
    ms = _marcas(db)
    pf = ms["professional-fitness"]
    antes = {m["slug"]: m["clients_count"]
             for m in http.get("/api/brand/perfiles", headers=_auth()).json()}
    _cliente_de(db, pf, "Cuenta para el selector")
    despues = {m["slug"]: m["clients_count"]
               for m in http.get("/api/brand/perfiles", headers=_auth()).json()}
    assert despues["professional-fitness"] == antes["professional-fitness"] + 1
    assert despues["dqr"] == antes["dqr"]
