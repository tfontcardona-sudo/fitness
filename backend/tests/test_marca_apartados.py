"""LO QUE USA CADA NEGOCIO: que el switch no enseñe pantallas de la otra marca.

El dueño, mirando dos capturas del panel del centro: «se ven diferentes
funciones o apartados, como el de recursos típicas de DQR, pero así no funciona
ni utiliza eso Professional Fitness… los elementos que no se utilicen de DQR
que estén en Professional, bórralos para el switch de Professional».

Lo que pasaba: el panel enseñaba exactamente lo mismo con una marca u otra —el
catálogo de PRODUCTOS de afiliación, la PÁGINA DE ENLACES del perfil de
Instagram, la conexión con Google, los tres planes de DQR en el alta y en la
ficha— aunque el negocio de delante no usara nada de eso.

La regla que se probó aquí, y que es la que evita que esto se vuelva un lío de
`if slug == …`: lo que YA lo dice otro dato se DEDUCE (las videollamadas las
dice `cita_modo`, la oferta sus `prices`, el educativo `doc_variant`, el
cuestionario en PDF `anamnesis_variant`) y solo lo que no está dicho en ningún
sitio se DECLARA (`features`, mig. 0054).

Cada test de aquí falla con el código anterior.
"""
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


def _marca(db, slug: str):
    from sqlalchemy import select

    from app.models import BrandConfig

    return db.scalar(select(BrandConfig).where(BrandConfig.slug == slug))


def _cliente(db, marca, **kw):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name=kw.pop("nombre", "Cliente"),
               email=f"ap-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active",
               package_tier=kw.pop("tier", "full"), brand_id=marca.id, **kw)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


# ------------------------------------------------------------ lo deducido --

def test_una_marca_que_revisa_en_el_centro_no_usa_videollamadas():
    """No hace falta declararlo: ya lo dice `cita_modo`. Si se declarara
    aparte, un día diría que sí hace videollamadas y sus citas serían visitas."""
    from app.services.branding import Marca

    centro = Marca(id=1, slug="c", name="C", cita_modo="presencial")
    online = Marca(id=2, slug="o", name="O", cita_modo="videollamada")
    assert centro.usa("videollamadas") is False
    assert online.usa("videollamadas") is True
    # Y una marca sin decir nada es de las de siempre: videollamada.
    assert Marca(id=3, slug="x", name="X").usa("videollamadas") is True


def test_lo_deducido_manda_sobre_lo_declarado():
    """Se puede APAGAR a mano algo que por defecto se tendría, pero no ENCENDER
    una videollamada en un negocio cuyas citas son visitas: eso no sería una
    opción, sería una mentira que el resto del ciclo desmiente."""
    from app.services.branding import Marca

    mentirosa = Marca(id=1, slug="c", name="C", cita_modo="presencial",
                      features={"videollamadas": True})
    assert mentirosa.usa("videollamadas") is False


def test_la_oferta_el_educativo_y_el_pdf_salen_de_sus_propios_datos():
    from app.services.branding import Marca

    sin_oferta = Marca(id=1, slug="c", name="C", prices={"full": {"1m": 12990}},
                       doc_variant="simple", anamnesis_variant="professional")
    assert sin_oferta.usa("oferta") is False
    assert sin_oferta.usa("educativo") is False
    assert sin_oferta.usa("anamnesis_pdf") is False

    con_todo = Marca(id=2, slug="d", name="D",
                     prices={"oferta": {"monthly_cents": 12000}},
                     doc_variant="completo", anamnesis_variant="dq")
    assert con_todo.usa("oferta") is True
    assert con_todo.usa("educativo") is True
    assert con_todo.usa("anamnesis_pdf") is True


def test_lo_no_declarado_se_usa():
    """Una marca nueva no se queda sin pantallas por no rellenar una lista, y
    añadir una función al sistema no obliga a repasar todas las marcas."""
    from app.services.branding import Marca

    assert Marca(id=1, slug="n", name="N").usa("productos") is True
    assert Marca(id=1, slug="n", name="N", features={"productos": False}).usa("productos") is False


# ---------------------------------------------------------- las dos marcas --

def test_el_centro_no_usa_afiliacion_ni_pagina_de_enlaces_y_dqr_si(db):
    from app.services import branding

    pf = branding.marca_por_id(_marca(db, "professional-fitness").id, db)
    dqr = branding.marca_por_id(_marca(db, "dqr").id, db)
    assert pf.lo_que_usa() == {"productos": False, "enlaces": False,
                               "videollamadas": False, "oferta": False,
                               "educativo": False, "anamnesis_pdf": False}
    assert all(dqr.lo_que_usa().values()), "DQR no pierde NADA con este cambio"


def test_el_contrato_de_marca_lleva_lo_que_usa(db):
    """El panel pregunta, no deduce: si dedujera por su cuenta, el día que
    cambie una regla diría una cosa el servidor y otra la pantalla."""
    from app.schemas.entities import BrandConfigOut, BrandProfileOut

    pf = _marca(db, "professional-fitness")
    assert BrandConfigOut.model_validate(pf).usa["enlaces"] is False
    assert BrandProfileOut.model_validate(pf).usa["productos"] is False


def test_la_pagina_publica_tambien_dice_lo_que_usa_la_marca(db):
    """`/dq` es una URL pública que puede estar enlazada desde fuera: con una
    marca que no la usa se lleva a lo que sí vende, no se rompe."""
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/api/public/landing")
    assert r.status_code == 200
    assert "usa" in r.json() and "enlaces" in r.json()["usa"]


# -------------------------------------------------- lo que ve cada pantalla --

def test_la_ficha_ofrece_solo_los_planes_que_vende_su_marca(db):
    """El selector ofrecía SIEMPRE los tres planes de DQR y sus tres
    duraciones: en un centro que solo vende una cuota mensual se le podía
    poner a un cliente un «DQR Train semestral» que nadie cobra."""
    from app.routers.clients import get_client

    pf = _marca(db, "professional-fitness")
    c = _cliente(db, pf, tier="full", billing_period="1m")
    out = get_client(c.id, db)
    assert out.plan_options == ["full"]
    assert out.billing_options == ["1m"]
    assert out.brand_usa["enlaces"] is False


def test_lo_que_el_cliente_tiene_contratado_nunca_desaparece_del_selector(db):
    """Quitarlo de la lista sería cambiárselo sin querer al primer guardado."""
    from app.routers.clients import get_client

    pf = _marca(db, "professional-fitness")
    c = _cliente(db, pf, tier="train", billing_period="6m")   # de antes
    out = get_client(c.id, db)
    assert "train" in out.plan_options and "6m" in out.billing_options


def test_el_cuestionario_en_pdf_es_el_de_dqr_y_no_se_le_da_a_otra_marca(db):
    """El fichero oficial lleva la marca de DQR dentro: servírselo al cliente
    del centro es mandarle el cuestionario de una asesoría con la que no ha
    contratado nada (y el suyo es una pantalla, no un papel)."""
    from fastapi.testclient import TestClient

    from app.main import app

    api = TestClient(app)
    del_centro = _cliente(db, _marca(db, "professional-fitness"))
    de_dqr = _cliente(db, _marca(db, "dqr"))
    assert api.get(f"/api/p/{del_centro.portal_token}/anamnesis-template").status_code == 404
    assert api.get(f"/api/p/{de_dqr.portal_token}/anamnesis-template").status_code in (200, 404)


def test_los_avisos_de_la_cita_hablan_de_visita_cuando_es_una_visita(db):
    """El panel decía «el cliente propuso videollamada» y «se crea el Meet con
    invitación» para una cita en la que no hay ni Meet ni enlace.

    Se prueba sobre la cartera de la marca ACTIVA de la suite (DQR) con una
    cita SELLADA como presencial: es el criterio del sistema —lo acordado en
    esa cita manda sobre lo que haga hoy el negocio— y así el test no depende
    de cuál sea la marca activa."""
    from datetime import date, datetime, timedelta, timezone

    from app.models import Period, Plan, VideoCall
    from app.routers.alerts import list_alerts

    c = _cliente(db, _marca(db, "dqr"), tier="full")
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=date.today() - timedelta(days=20),
               ends_on=date.today() - timedelta(days=6), status="closed")
    db.add(p)
    db.flush()
    db.add(VideoCall(client_id=c.id, period_index=1, status="proposed", modo="presencial",
                     scheduled_at=datetime.now(timezone.utc) + timedelta(days=2)))
    db.commit()
    try:
        avisos = list_alerts(db)["alerts"]
        textos = " ".join(str(a.get("message", "")) + " " + str(a.get("fix") or "")
                          for a in avisos if a.get("client_id") == c.id)
        assert "visita en el centro" in textos
        assert "videollamada" not in textos
    finally:
        db.query(VideoCall).filter(VideoCall.client_id == c.id).delete()
        db.query(Period).filter(Period.client_id == c.id).delete()
        db.query(Plan).filter(Plan.client_id == c.id).delete()
        db.commit()
