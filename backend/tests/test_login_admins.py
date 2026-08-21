"""Las credenciales del panel salen del .env, y el .env MANDA.

Es un sistema de un solo coach: quien controla el .env controla la instalación.
Aun así, el seed solo creaba el usuario si no existía, así que cambiar
ADMIN_1_PASS no tenía ningún efecto — el hash viejo seguía en la base de datos
y el coach se quedaba fuera con un "credenciales incorrectas" imposible de
explicar (le pasó al dueño con su instalación real).
"""
from __future__ import annotations

import uuid

import pytest

from tests.test_portal import _db_available

pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture()
def sembrar(monkeypatch):
    """Ejecuta seed_admins como si el .env tuviera esas credenciales.

    Se toca el objeto `settings` con monkeypatch en vez de recargar módulos:
    recargar app.config deja al resto de la suite apuntando a un objeto de
    configuración distinto del que ya tienen importado los demás módulos, y
    rompe tests que no tienen nada que ver.
    """
    from app.config import settings
    from app.db import SessionLocal
    from app.seeds.run import seed_admins

    # El segundo admin no participa: si el .env del entorno lo trae, ensuciaría
    # la cuenta de usuarios creados/corregidos que comprueban los tests.
    monkeypatch.setattr(settings, "admin_2_user", "", raising=False)
    monkeypatch.setattr(settings, "admin_2_pass", "", raising=False)

    def _hacerlo(usuario: str, password: str) -> int:
        monkeypatch.setattr(settings, "admin_1_user", usuario, raising=False)
        monkeypatch.setattr(settings, "admin_1_pass", password, raising=False)
        with SessionLocal() as db:
            return seed_admins(db)

    return _hacerlo


def _login(usuario: str, password: str) -> int:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as http:
        return http.post("/api/auth/login",
                         json={"username": usuario, "password": password}).status_code


@pytest.fixture()
def usuario():
    nombre = f"admin_{uuid.uuid4().hex[:8]}"
    yield nombre
    from sqlalchemy import delete

    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        db.execute(delete(User).where(User.username == nombre))
        db.commit()


def test_cambiar_la_contrasena_en_el_env_deja_entrar(sembrar, usuario):
    """REGRESIÓN: el seed no actualizaba el hash y el login se quedaba en 401."""
    assert sembrar(usuario, "Primera-Clave-1") == 1, "debe crear el admin"
    assert _login(usuario, "Primera-Clave-1") == 200

    # El coach cambia la contraseña en el .env y vuelve a levantar el sistema.
    assert sembrar(usuario, "Segunda-Clave-2") == 1, "debe corregir el hash"
    assert _login(usuario, "Segunda-Clave-2") == 200, "la contraseña NUEVA entra"
    assert _login(usuario, "Primera-Clave-1") == 401, "la vieja ya no vale"


def test_el_seed_es_idempotente_si_nada_cambia(sembrar, usuario):
    """Arrancar dos veces con el mismo .env no toca nada (ni reescribe hashes)."""
    assert sembrar(usuario, "Clave-Estable-1") == 1
    assert sembrar(usuario, "Clave-Estable-1") == 0, "sin cambios, no toca nada"
    assert _login(usuario, "Clave-Estable-1") == 200
