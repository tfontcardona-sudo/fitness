"""EDITAR EL EMAIL DEL CLIENTE DESDE LA FICHA.

`ClientUpdate` no aceptaba `email`: Pydantic lo descartaba en silencio
(gotcha §5.8) y el coach no tenía dónde corregir una errata del alta. El
email es además su credencial de entrada al portal, así que un duplicado no
puede colarse — revienta el UNIQUE de la tabla con un 500 sin explicación si
no se comprueba antes.

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


def _cliente(db, **kw):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name=kw.pop("nombre", "Cliente"),
               email=kw.pop("email", f"ce-{uuid.uuid4().hex[:8]}@example.com"),
               portal_token="tmp", status="active", package_tier="full")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


def test_el_patch_acepta_el_email(db):
    from app.routers.clients import update_client
    from app.schemas.entities import ClientUpdate

    c = _cliente(db)
    nuevo = f"nuevo-{uuid.uuid4().hex[:8]}@example.com"
    out = update_client(c.id, ClientUpdate(email=nuevo), db)
    assert out.email == nuevo
    db.refresh(c)
    assert c.email == nuevo


def test_no_se_puede_repetir_el_email_de_otro_cliente(db):
    from fastapi import HTTPException

    from app.routers.clients import update_client
    from app.schemas.entities import ClientUpdate

    otro = _cliente(db, nombre="Ya Existe")
    c = _cliente(db)
    with pytest.raises(HTTPException) as exc:
        update_client(c.id, ClientUpdate(email=otro.email), db)
    assert exc.value.status_code == 422
    assert "Ya Existe" in exc.value.detail
    db.refresh(c)
    assert c.email != otro.email


def test_guardar_el_mismo_email_no_falla(db):
    """No es un cambio: no debe chocar consigo mismo."""
    from app.routers.clients import update_client
    from app.schemas.entities import ClientUpdate

    c = _cliente(db)
    out = update_client(c.id, ClientUpdate(email=c.email), db)
    assert out.email == c.email
