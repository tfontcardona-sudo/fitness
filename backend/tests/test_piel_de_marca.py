"""LA PIEL DE LA MARCA: que el switch cambie de verdad lo que se ve.

El dueño lo dijo así: «al hacer el switch a Professional es como si se cambiase
solo la imagen de fuera, y ni eso». Tenía razón, y esta es la lista de lo que
pasaba de verdad:

· la marca solo publicaba tres colores, así que el panel seguía siendo crema y
  el portal seguía siendo el azul noche de DQR con un brillo NARANJA abajo;
· el segundo color de Professional es un NEGRO (#161616) —en su identidad el
  negro es la estructura, no un acento— y ese color pintaba el anillo de
  progreso de la quincena: negro sobre negro, el cliente no veía los días que
  le quedaban para su revisión;
· `GET /api/public/landing` devolvía `logo_url=None` SIEMPRE, así que /dq,
  /planes y /oferta del centro imprimían el logo de DQ;
· las cinco tarifas del centro estaban guardadas en su perfil desde que se
  creó y no las enseñaba ninguna pantalla;
· y el informe de la revisión quincenal era el de DQR para las dos marcas.

Cada test de aquí FALLA con el código anterior.
"""
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


def _marcas(db):
    from sqlalchemy import select

    from app.models import BrandConfig

    return {b.slug: b for b in db.scalars(select(BrandConfig)).all()}


# ------------------------------------------------------------------ la piel --

def test_cada_marca_declara_su_piel_entera_no_tres_colores(db):
    """La piel es un DATO de la marca (mig. 0053), no un `if` por slug: una
    marca nueva elige la suya sin tocar código."""
    from app.services import branding

    ms = _marcas(db)
    assert branding.marca_por_id(ms["dqr"].id, db).skin == "dqr"
    assert branding.marca_por_id(ms["professional-fitness"].id, db).skin == "professional"


def test_la_piel_por_defecto_es_la_de_dqr(db):
    """Sin piel declarada (base antigua, perfil a medio hacer) se ve lo de
    siempre. Una pantalla sin estilo es peor que una con el estilo anterior."""
    from app.services.branding import DEFAULTS, marca_por_defecto

    assert DEFAULTS["skin"] == "dqr"
    assert marca_por_defecto().skin == "dqr"


def test_el_portal_del_cliente_lleva_la_piel_de_SU_marca(db):
    """No la del escaparate. Que el coach cambie el switch no puede cambiarle
    el portal a quien ya está pagando."""
    from app.models import Client
    from app.services.portal import brand_payload

    ms = _marcas(db)
    pf, dqr = ms["professional-fitness"], ms["dqr"]
    c = Client(brand_id=pf.id)
    assert brand_payload(db, c)["skin"] == "professional"
    c.brand_id = dqr.id
    assert brand_payload(db, c)["skin"] == "dqr"


def test_el_cuestionario_tambien_dice_su_piel(db):
    """El formulario de Professional es negro; sin la piel, el navegador
    enmarcaba esa pantalla en el fondo crema de DQR."""
    from app.models import BrandConfig
    from app.routers.portal_public import _variante_de_anamnesis

    pf = _marcas(db)["professional-fitness"]
    assert _variante_de_anamnesis(pf)["anamnesis_variant"] == "professional"
    assert (getattr(pf, "skin", None) or "dqr") == "professional"
    assert (getattr(BrandConfig(), "skin", None) or "dqr") == "dqr"


# ------------------------------------------------------------------- el logo --

def test_la_pagina_publica_sirve_el_logo_de_la_marca_y_no_el_de_dq(db, monkeypatch):
    """`logo_url` estaba clavado a None "porque /storage no pasa por Caddy", y
    por eso la página caía al logo empaquetado de DQ. Los logos viven bajo
    `media/` desde la ronda del 10-09 y Caddy SÍ los sirve."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import branding

    pf = _marcas(db)["professional-fitness"]
    previo, activa_previa = pf.logo_path, db.query(type(pf)).filter_by(activa=True).first()
    pf.logo_path = "media/logo-professional-fitness.png"
    if activa_previa is not None and activa_previa.id != pf.id:
        activa_previa.activa = False
        db.flush()
        pf.activa = True
    db.commit()
    branding.invalidar()
    try:
        with TestClient(app) as http:
            r = http.get("/api/public/landing")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["skin"] == "professional"
        assert cuerpo["logo_url"] == "/api/media/logo-professional-fitness.png"
    finally:
        pf.logo_path = previo
        if activa_previa is not None and activa_previa.id != pf.id:
            pf.activa = False
            db.flush()
            activa_previa.activa = True
        db.commit()
        branding.invalidar()


def test_un_logo_legado_no_se_promete_como_url(db):
    """Los logos viejos cuelgan de `brand/`, que Caddy NO sirve: prometerlos
    sería pintar un 404 en la cabecera de cada pantalla."""
    from app.services.storage import media_url

    assert media_url("brand/logo-dqr.png") is None
    assert media_url("media/logo-dqr.png") == "/api/media/logo-dqr.png"


# ----------------------------------------------------------- lo que se vende --

def test_el_catalogo_de_vender_lleva_las_tarifas_del_centro(db):
    """Las cinco tarifas del centro (gimnasio, entrenos, packs) viven en el
    perfil de la marca desde su migración y NINGUNA pantalla las enseñaba: el
    coach abría Vender y veía un solo producto, como si el resto de su negocio
    no existiera."""
    from app.services import branding, sales_catalog

    ms = _marcas(db)
    activa_previa = next((b for b in ms.values() if b.activa), None)
    pf = ms["professional-fitness"]
    if activa_previa is not None and activa_previa.id != pf.id:
        activa_previa.activa = False
        db.flush()
        pf.activa = True
        db.commit()
    branding.invalidar()
    try:
        cat = sales_catalog.sales_catalog(refresh=True)
        marca = cat["brand"]
        assert marca["slug"] == "professional-fitness"
        # La revisión de un centro es una VISITA: el argumentario de la
        # pantalla prometía "videollamada de revisión" a todo el mundo.
        assert marca["cita_modo"] == "presencial"
        assert len(marca["extra_services"]) == 5
        assert any("gimnasio" in e["title"].lower() for e in marca["extra_services"])
        # Y el servicio se llama como lo llama SU marca.
        assert [i["tier_label"] for i in cat["items"]] == ["Pack Premium"]
    finally:
        if activa_previa is not None and activa_previa.id != pf.id:
            pf.activa = False
            db.flush()
            activa_previa.activa = True
            db.commit()
        branding.invalidar()
        sales_catalog.sales_catalog(refresh=True)


# ------------------------------------------------------- el informe quincenal --

def _datos_de_informe() -> dict:
    return dict(
        client_name="Marta Vilanova", period_index=3,
        period_label="Del 1 al 14 de septiembre de 2026",
        goal_label="Objetivo: pérdida de grasa",
        metrics={"adherence": {"diet_yes": 9, "diet_partial": 3, "diet_no": 2,
                               "diet_adherence_ratio": 0.78, "days_logged": 13,
                               "period_days": 14, "log_ratio": 0.93},
                 "weight": {"delta_kg": -1.4}},
        weight_points=[("01/09", 68.5), ("14/09", 67.1)],
        goal_kg=63.0,
        e1rm_exercises=[{"name": "Sentadilla", "e1rm_kg": 78.0, "delta_kg": 4.0}],
        perimeters={"Cintura": [("Antes", 78.0), ("Ahora", 76.4)]},
        volume_by_group={"Pierna": 42.0},
        photo_pairs=None, ai_photo_analysis=None,
        natural_analysis="Quincena sólida: el peso baja a un ritmo sano.",
        changes_bullets=["Subimos 10 g de proteína al desayuno."],
        answers="Mueve la fruta a media tarde.",
        next_objectives=["Apuntar el peso 3 mañanas por semana."],
        closing_message="Vas bien, sigue así.",
        plan_adjustments=[{"area": "Dieta", "change": "+10 g proteína",
                           "reason": "Para sostener la fuerza en déficit."}],
        has_nutrition=True,
    )


def _texto(b: bytes) -> str:
    from io import BytesIO

    from docx import Document

    doc = Document(BytesIO(b))
    partes = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for fila in t.rows:
            partes += [c.text for c in fila.cells]
    return "\n".join(partes).upper()


def test_el_informe_de_professional_no_es_el_de_dqr():
    """El cliente del centro recibía su PLAN en negro y dorado y, quince días
    después, la revisión con la portada y el orden de DQR: dos marcas en el
    mismo buzón."""
    from app.services.docs.feedback_doc import generate_feedback_doc
    from app.services.docs.feedback_doc_pf import generate_feedback_doc_pf
    from app.services.docs.word_base import DocBrand

    pf = DocBrand(name="Professional", color_primary="#C9A227",
                  color_secondary="#161616", font_family="Inter",
                  contact_address="Carretera Pierre Vilar, 2 · 17002 Girona")
    dq = DocBrand(name="DQR Assessories", color_primary="#E8833A",
                  color_secondary="#2E5E8C", font_family="Inter")
    datos = _datos_de_informe()
    t_pf = _texto(generate_feedback_doc_pf(brand=pf, **datos))
    t_dqr = _texto(generate_feedback_doc(brand=dq, **datos))

    # Lo que solo tiene el del centro: su portada, sus fichas y SU CICLO — el
    # mismo bloque que ya trae su plan, con la cita presencial.
    for propio in ("TU QUINCENA EN UNA PÁGINA", "CÓMO SEGUIMOS", "SIGUES APUNTANDO",
                   "NOS VEMOS", "LA CUOTA SE RENUEVA CADA MES"):
        assert propio in t_pf, propio
        assert propio not in t_dqr, propio
    assert "GIRONA" in t_pf                      # un centro dice dónde está
    # Y la pieza de DQR que no le llega.
    assert "CUADRÍCULA DE CAMBIOS APLICADOS" in t_dqr
    assert "CUADRÍCULA DE CAMBIOS APLICADOS" not in t_pf


def test_la_cabecera_de_tabla_del_informe_del_centro_se_lee_en_papel():
    """El informe de DQR pinta la cabecera con el color primario y el texto en
    BLANCO. Dorado sobre blanco da 2,1:1: en papel no se lee. La del centro es
    negra con el texto en oro, como la de su plan."""
    from io import BytesIO

    from docx import Document
    from docx.oxml.ns import qn

    from app.services.docs.feedback_doc_pf import generate_feedback_doc_pf
    from app.services.docs.plan_doc_pf import NEGRO, ORO
    from app.services.docs.word_base import DocBrand

    marca = DocBrand(name="Professional", color_primary="#C9A227",
                     color_secondary="#161616", font_family="Inter")
    doc = Document(BytesIO(generate_feedback_doc_pf(brand=marca, **_datos_de_informe())))
    cabeceras = []
    for t in doc.tables:
        celda = t.rows[0].cells[0]
        shd = celda._tc.get_or_add_tcPr().find(qn("w:shd"))
        if shd is not None:
            cabeceras.append(shd.get(qn("w:fill")))
    assert NEGRO in cabeceras                   # la tabla de ajustes, en negro
    assert "C9A227" not in cabeceras            # nunca la cabecera en oro
    # Y el texto de esa cabecera, en oro.
    tabla = next(t for t in doc.tables
                 if t.rows[0].cells[0].text.strip().lower() == "área")
    colores = {str(r.font.color.rgb) for c in tabla.rows[0].cells
               for p in c.paragraphs for r in p.runs
               if r.font.color and r.font.color.rgb}
    assert ORO in colores


def test_las_cifras_del_informe_del_centro_son_las_mismas():
    """La piel cambia; la matemática NO. El informe solo IMPRIME lo que le dan
    calculado: si los números difirieran entre marcas, el negocio sería otro."""
    from app.services.docs.feedback_doc import generate_feedback_doc
    from app.services.docs.feedback_doc_pf import generate_feedback_doc_pf
    from app.services.docs.word_base import DocBrand

    pf = DocBrand(name="Professional", color_primary="#C9A227",
                  color_secondary="#161616", font_family="Inter")
    dq = DocBrand(name="DQR Assessories", color_primary="#E8833A",
                  color_secondary="#2E5E8C", font_family="Inter")
    datos = _datos_de_informe()
    t_pf = _texto(generate_feedback_doc_pf(brand=pf, **datos))
    t_dqr = _texto(generate_feedback_doc(brand=dq, **datos))
    for cifra in ("-1,4 KG", "13/14", "78 %"):
        assert cifra.replace(" ", "") in t_pf.replace(" ", ""), cifra
    for cifra in ("-1,4 KG", "13/14"):
        assert cifra.replace(" ", "") in t_dqr.replace(" ", ""), cifra


def test_el_informe_que_toca_lo_decide_la_marca_del_cliente(db):
    """La misma puerta que el documento del plan (`doc_variant`): un cliente
    sellado en Professional recibe el informe del centro."""
    from app.models import Client
    from app.services.plan_delivery import variante_de_documento

    ms = _marcas(db)
    assert variante_de_documento(db, Client(brand_id=ms["professional-fitness"].id)) \
        == "professional"
    assert variante_de_documento(db, Client(brand_id=ms["dqr"].id)) != "professional"
