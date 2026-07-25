"""Test de captura de ediciones del coach vía PATCH /api/plans (hardening §13)."""
from __future__ import annotations

import uuid

import pytest


def _db() -> bool:
    try:
        from sqlalchemy import create_engine, text
        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db(), reason="Requiere PostgreSQL")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def auth():
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


def _nut():
    return {
        "tdee_kcal": 2500, "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60},
        "meals": [
            {"slot": 1, "name": "Desayuno", "time": "08:00",
             "target": {"kcal": 800, "protein_g": 60, "carbs_g": 80, "fat_g": 24}},
            {"slot": 2, "name": "Cena", "time": "21:00",
             "target": {"kcal": 1200, "protein_g": 90, "carbs_g": 120, "fat_g": 36}},
        ],
        "meal_bank": {"mode": "flexible_7", "slots": []},
    }


def test_editar_plan_captura_edicion_clasificada(client, auth):
    from app.db import SessionLocal
    from app.models import PlanEdit
    from sqlalchemy import select

    cid = client.post("/api/clients", headers=auth, json={
        "full_name": "Edit Cap", "email": f"editcap-{uuid.uuid4().hex[:8]}@x.com"}).json()["client"]["id"]
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": _nut(),
        "training_json": {"sessions": []}, "education_json": {}}).json()

    # El coach sube las kcal → debe capturarse una edición de categoría "calculo".
    edited = _nut()
    edited["target_kcal"] = 2300
    r = client.patch(f"/api/plans/{plan['id']}", headers=auth, json={"nutrition_json": edited})
    assert r.status_code == 200, r.text

    with SessionLocal() as db:
        edits = db.scalars(select(PlanEdit).where(PlanEdit.plan_id == plan["id"])).all()
        assert edits, "no se capturó ninguna edición"
        assert any(e.category == "calculo" for e in edits)
        assert all(e.note for e in edits)  # cada edición guarda su texto legible
