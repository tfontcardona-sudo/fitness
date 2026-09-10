"""EL LOGO QUE NO SE VEÍA, RESCATADO SOLO.

Las imágenes de marca se guardaban bajo `storage/brand/`. Caddy solo proxya
`/api/*`: esa carpeta no se puede servir, así que el logo estaba subido y no
aparecía en ninguna parte. Ahora lo público vive bajo `storage/media/`.

Que el dueño tenga que volver a subir cada imagen a mano no es un arreglo: es
pasarle el problema. Esto comprueba que el rescate lo hace el sistema al
arrancar, que es idempotente y que una ruta que apunta a un hueco se limpia.
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


def test_el_logo_viejo_se_mueve_solo_a_donde_si_se_puede_servir(db):
    from app.services.branding import marca_activa
    from app.services.media_legacy import migrar_imagenes_de_marca
    from app.services.storage import brand_dir, media_url, storage_root

    from app.models import BrandConfig

    marca = db.get(BrandConfig, marca_activa(db).id)
    original = marca.logo_path

    viejo = brand_dir() / "logo-prueba-rescate.png"
    viejo.write_bytes(b"no-es-una-imagen-de-verdad-pero-es-un-fichero")
    marca.logo_path = str(viejo.relative_to(storage_root()))
    db.commit()

    try:
        assert migrar_imagenes_de_marca(db) >= 1
        db.expire_all()
        marca = db.get(BrandConfig, marca.id)
        # Ahora cuelga de media/ y, por tanto, TIENE una URL servible.
        assert marca.logo_path.startswith("media/brand/")
        cola = marca.logo_path.split("media/", 1)[1]
        assert media_url(marca.logo_path) == f"/api/media/{cola}"
        assert (storage_root() / marca.logo_path).is_file()
        assert not viejo.exists()          # no se deja una copia huérfana

        # Y volver a arrancar no hace nada: es idempotente.
        assert migrar_imagenes_de_marca(db) == 0

        nuevo = storage_root() / marca.logo_path
        nuevo.unlink(missing_ok=True)
    finally:
        db.expire_all()
        marca = db.get(BrandConfig, marca.id)
        marca.logo_path = original
        db.commit()


def test_una_ruta_que_apunta_a_un_hueco_se_limpia(db):
    """Pedirle al navegador una imagen que no existe es un 404 por carga y un
    hueco en la pantalla: mejor decir que no hay logo."""
    from app.services.branding import marca_activa
    from app.services.media_legacy import migrar_imagenes_de_marca

    from app.models import BrandConfig

    marca = db.get(BrandConfig, marca_activa(db).id)
    original = marca.logo_path
    marca.logo_path = "brand/logo-que-ya-no-existe.png"
    db.commit()
    try:
        assert migrar_imagenes_de_marca(db) >= 1
        db.expire_all()
        assert db.get(BrandConfig, marca.id).logo_path is None
    finally:
        db.expire_all()
        marca = db.get(BrandConfig, marca.id)
        marca.logo_path = original
        db.commit()
