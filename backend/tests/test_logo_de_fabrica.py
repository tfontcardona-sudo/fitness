"""EL LOGO DE FÁBRICA: que una marca nueva no dependa de un clic del dueño.

El dueño mandó el archivo real del logo de Professional (laurel + «PROFESSIONAL»
en oro sobre negro) y pidió que se aplicara él solo al desplegar — «yo te pido y
tú lo fusionas y despliegas». El fichero se empaqueta en el código
(`assets/brand/`) y `aplicar_logos_de_fabrica` lo sella en la fila de la marca
al arrancar, con el MISMO criterio que `media_legacy.py`: idempotente, y nunca
pisa lo que el dueño ya haya subido a mano.

Cada test de aquí falla con el código anterior (la función no existía).
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


def _marca(db, slug: str):
    from sqlalchemy import select

    from app.models import BrandConfig

    return db.scalar(select(BrandConfig).where(BrandConfig.slug == slug))


def test_el_fichero_de_fabrica_existe_de_verdad():
    """Sin el propio archivo, todo lo demás es teatro: el seed no puede
    inventarse un logo que el dueño no ha mandado."""
    from app.services.default_brand_logos import _ASSETS, _LOGOS_DE_FABRICA

    for slug, fichero in _LOGOS_DE_FABRICA.items():
        assert (_ASSETS / fichero).is_file(), f"falta el logo de fábrica de {slug}"


def test_se_aplica_a_una_marca_sin_logo(db):
    from app.services.default_brand_logos import aplicar_logos_de_fabrica

    marca = _marca(db, "professional-fitness")
    logo_previo = marca.logo_path
    marca.logo_path = None
    db.commit()
    try:
        n = aplicar_logos_de_fabrica(db)
        assert n == 1
        db.refresh(marca)
        assert marca.logo_path and marca.logo_path.startswith("media/brand/logo-")
    finally:
        marca.logo_path = logo_previo
        db.commit()


def test_no_pisa_el_logo_que_el_dueno_ya_subio(db):
    """Es un ARRANQUE, no una plantilla que se reimponga: en cuanto el dueño
    sube el suyo, este módulo deja esa marca en paz para siempre."""
    from app.services.default_brand_logos import aplicar_logos_de_fabrica

    marca = _marca(db, "professional-fitness")
    logo_previo = marca.logo_path
    marca.logo_path = "media/brand/logo-subido-por-el-dueno.png"
    db.commit()
    try:
        n = aplicar_logos_de_fabrica(db)
        assert n == 0
        db.refresh(marca)
        assert marca.logo_path == "media/brand/logo-subido-por-el-dueno.png"
    finally:
        marca.logo_path = logo_previo
        db.commit()


def test_una_marca_sin_fichero_de_fabrica_no_hace_nada(db):
    """DQR no tiene logo de fábrica (el suyo es el hardcoded `/dq-logo.png` del
    frontend, no este mecanismo): no se le inventa uno."""
    from app.services.default_brand_logos import aplicar_logos_de_fabrica

    marca = _marca(db, "dqr")
    logo_previo = marca.logo_path
    assert logo_previo is None
    try:
        n = aplicar_logos_de_fabrica(db)
        db.refresh(marca)
        assert marca.logo_path is None
        assert n == 0
    finally:
        marca.logo_path = logo_previo
        db.commit()


def test_es_idempotente(db):
    from app.services.default_brand_logos import aplicar_logos_de_fabrica

    marca = _marca(db, "professional-fitness")
    logo_previo = marca.logo_path
    marca.logo_path = None
    db.commit()
    try:
        aplicar_logos_de_fabrica(db)
        n2 = aplicar_logos_de_fabrica(db)
        assert n2 == 0, "la segunda vuelta no debe volver a escribir nada"
    finally:
        marca.logo_path = logo_previo
        db.commit()
