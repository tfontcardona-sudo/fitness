"""Tests de la maquinaria del gimnasio, la creación de ejercicios a mano y la
descarga del plan en Word editable.

Requiere PostgreSQL (mismos fixtures que la suite A3).
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


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seeds.run import main as seed_main

    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    # Token directo (sin pasar por /api/auth/login): el login real está capado a
    # 5/min contra fuerza bruta y la suite completa ya consume ese cupo.
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


def test_maquinaria_sembrada_y_repetir_no_duplica(client, auth):
    """Las máquinas del coach están en la biblioteca (marca en el nombre, nombre
    a secas como alias) y volver a sembrar no crea duplicados."""
    from app.db import SessionLocal
    from app.seeds.machines_data import MACHINE_EXERCISES
    from app.seeds.run import seed_machines

    r = client.get("/api/exercises?include_archived=true", headers=auth)
    assert r.status_code == 200
    names = {e["canonical_name"] for e in r.json()}
    for expected in ("Hip Thrust (Panatta)", "Pec Deck (Nautilus)", "Hack Squat (Etenon)",
                     "V-Squat (Prime)", "Belt Squat", "Cinta de correr", "Empuje de trineo"):
        assert expected in names, f"falta {expected}"
    # todas las máquinas del listado presentes
    assert {d["canonical_name"] for d in MACHINE_EXERCISES} <= names

    db = SessionLocal()
    try:
        assert seed_machines(db) == 0  # idempotente por nombre
    finally:
        db.close()


def test_cardio_como_grupo_propio(client, auth):
    r = client.get("/api/exercises?muscle=cardio", headers=auth)
    assert r.status_code == 200
    cardio = r.json()
    assert len(cardio) >= 7
    assert all(e["movement_pattern"] == "cardio" for e in cardio)


def test_crear_ejercicio_a_mano_y_usarlo(client, auth):
    """El flujo del buscador del editor: POST crea el ejercicio y aparece en la
    lista; un nombre repetido devuelve 409 (no duplica)."""
    import uuid

    name = f"Press especial del coach {uuid.uuid4().hex[:6]}"
    r = client.post("/api/exercises", headers=auth, json={
        "canonical_name": name,
        "muscle_primary": "pecho",
        "movement_pattern": "horizontal_push",
        "equipment": ["maquina"],
        "level_min": 1,
    })
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["canonical_name"] == name and created["id"] > 0

    r2 = client.get("/api/exercises?include_archived=true", headers=auth)
    assert any(e["id"] == created["id"] for e in r2.json())

    dup = client.post("/api/exercises", headers=auth, json={
        "canonical_name": name,
        "muscle_primary": "pecho",
        "movement_pattern": "horizontal_push",
        "level_min": 1,
    })
    assert dup.status_code == 409


def test_documento_word_editable(client, auth):
    """format=docx devuelve el Word original (zip 'PK'), con filename .docx;
    el formato por defecto sigue siendo el PDF de entrega."""
    import uuid

    r = client.post("/api/clients", headers=auth, json={
        "full_name": "Cliente Word", "email": f"word-{uuid.uuid4().hex[:8]}@example.com",
    })
    assert r.status_code in (200, 201), r.text
    cid = r.json()["client"]["id"]
    r = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1,
        "nutrition_json": {
            "target_kcal": 2000,
            "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
            "meals": [
                {"slot": 1, "name": "Desayuno", "time": "08:00",
                 "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 30}},
                {"slot": 2, "name": "Cena", "time": "21:00",
                 "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 30}},
            ],
        },
        "training_json": {"sessions": []},
        "education_json": {},
    })
    assert r.status_code in (200, 201), r.text
    plan_id = r.json()["id"]

    w = client.get(f"/api/plans/{plan_id}/document?format=docx", headers=auth)
    assert w.status_code == 200
    assert w.content[:2] == b"PK"  # .docx = zip
    assert ".docx" in w.headers.get("content-disposition", "")
    assert "wordprocessingml" in w.headers.get("content-type", "")

    bad = client.get(f"/api/plans/{plan_id}/document?format=exe", headers=auth)
    assert bad.status_code == 422  # formato no permitido
