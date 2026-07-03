"""Tests de integración de la Fase 2 (auth, CRUD, portal público, RGPD).

Requieren una base de datos PostgreSQL real (usa ARRAY/JSONB). Se saltan
automáticamente si no hay DB disponible. En el contenedor de desarrollo:

    docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api pytest

Variables esperadas (las inyecta docker-compose.dev.yml):
    DATABASE_URL, JWT_SECRET, PORTAL_TOKEN_SECRET, ADMIN_1_USER/PASS, STORAGE_PATH
"""

from __future__ import annotations

import io
import os
import warnings
import zipfile

import pytest
from PIL import Image

warnings.filterwarnings("ignore")

ADMIN_USER = os.environ.get("ADMIN_1_USER", "coach1")
ADMIN_PASS = os.environ.get("ADMIN_1_PASS", "")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available() or not ADMIN_PASS,
    reason="Requiere PostgreSQL y ADMIN_1_PASS (entorno de docker-compose)",
)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seeds.run import main as seed_main

    seed_main()  # idempotente
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    r = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _jpg() -> io.BytesIO:
    im = Image.new("RGB", (50, 60), (100, 90, 80))
    b = io.BytesIO()
    im.save(b, format="JPEG")
    b.seek(0)
    return b


ANAMNESIS = {
    "sex": "male", "birth_date": "1990-05-10", "height_cm": 178, "start_weight_kg": 82,
    "goal_type": "fat_loss", "goal_weight_kg": 75, "level": "intermediate",
    "training_days": 4, "session_max_min": 75, "training_place": "gym",
    "equipment": ["barra", "mancuernas", "maquina"], "excluded_exercise_ids": [],
    "meals_per_day": 4,
    "meal_schedule": [
        {"slot": 1, "name": "Desayuno", "time": "08:00"},
        {"slot": 2, "name": "Comida", "time": "14:00"},
        {"slot": 3, "name": "Merienda", "time": "18:00"},
        {"slot": 4, "name": "Cena", "time": "21:30"},
    ],
    "food_allergies": ["lactosa"], "food_dislikes": ["brócoli"],
    "food_likes": ["pollo", "arroz"], "diet_mode": "flexible_7",
    "priority_zones": "core y glúteos",
}


def test_login_rejects_bad_password(client):
    assert client.post("/api/auth/login", json={"username": ADMIN_USER, "password": "x"}).status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_exercises_seeded_and_filterable(client, auth):
    full = client.get("/api/exercises?include_archived=true", headers=auth)
    # Al menos los 150 del seed (pueden existir personalizados de otros tests)
    assert full.status_code == 200 and len(full.json()) >= 150
    hinge = client.get("/api/exercises?pattern=hip_hinge", headers=auth).json()
    assert hinge and all(e["movement_pattern"] == "hip_hinge" for e in hinge)


def test_exercise_archive_hides_from_default_list(client, auth):
    import uuid
    new = {
        "canonical_name": f"Test archivable {uuid.uuid4().hex[:8]}", "aliases": [],
        "muscle_primary": "core",
        "muscle_secondary": [], "movement_pattern": "core_flexion",
        "equipment": ["peso_corporal"], "level_min": 1, "video_url": "",
        "technique_notes": "Notas de técnica suficientemente largas para validar",
        "biomechanics_notes": "Notas de biomecánica suficientemente largas para validar",
        "contraindications": [],
    }
    ex_id = client.post("/api/exercises", json=new, headers=auth).json()["id"]
    assert client.post(f"/api/exercises/{ex_id}/archive", headers=auth).json()["archived"] is True
    ids = [e["id"] for e in client.get("/api/exercises", headers=auth).json()]
    assert ex_id not in ids
    ids_all = [e["id"] for e in client.get("/api/exercises?include_archived=true", headers=auth).json()]
    assert ex_id in ids_all


def test_export_with_accented_name(client, auth):
    """Regresión: nombres con tildes/ñ no deben romper el header
    Content-Disposition (que viaja en latin-1)."""
    import uuid

    body = client.post(
        "/api/clients",
        json={
            "full_name": "Begoña Martínez Ruiz",
            "email": f"begona-{uuid.uuid4().hex[:8]}@example.com",
        },
        headers=auth,
    ).json()
    cid = body["client"]["id"]
    r = client.get(f"/api/clients/{cid}/export", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    # nombre de archivo normalizado a ASCII
    assert "begona_martinez_ruiz" in r.headers["content-disposition"]


def test_full_client_lifecycle(client, auth):
    body = client.post(
        "/api/clients",
        json={"full_name": "Test Lifecycle", "email": "lifecycle@example.com"},
        headers=auth,
    ).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]
    assert body["client"]["status"] == "onboarding"

    # portal público
    assert client.get("/api/p/token-invalido").status_code == 404
    assert client.get(f"/api/p/{token}").json()["anamnesis_done"] is False

    # foto antes de consentir → 403
    assert client.post(
        f"/api/p/{token}/anamnesis/photos",
        files={"files": ("f.jpg", _jpg(), "image/jpeg")},
    ).status_code == 403

    # anamnesis sin consentimiento → 422
    assert client.post(f"/api/p/{token}/anamnesis", json=ANAMNESIS).status_code == 422
    # con consentimiento → 200
    assert client.post(f"/api/p/{token}/anamnesis", json={**ANAMNESIS, "consent_accepted": True}).status_code == 200
    # reenvío → 409
    assert client.post(f"/api/p/{token}/anamnesis", json={**ANAMNESIS, "consent_accepted": True}).status_code == 409

    # fotos tras consentir
    assert client.post(
        f"/api/p/{token}/anamnesis/photos",
        files=[("files", ("a.jpg", _jpg(), "image/jpeg"))],
    ).status_code == 200

    # regeneración de token revoca el anterior
    new_token = client.post(f"/api/clients/{cid}/portal-token/regenerate", headers=auth).json()["portal_token"]
    assert client.get(f"/api/p/{token}").status_code == 404
    assert client.get(f"/api/p/{new_token}").status_code == 200

    # export RGPD
    r = client.get(f"/api/clients/{cid}/export", headers=auth)
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert "datos.json" in zf.namelist()

    # supresión con doble confirmación
    assert client.request("DELETE", f"/api/clients/{cid}?confirm=Mal", headers=auth).status_code == 400
    assert client.request("DELETE", f"/api/clients/{cid}?confirm=Test Lifecycle", headers=auth).status_code == 204
    assert client.get(f"/api/clients/{cid}", headers=auth).status_code == 404
