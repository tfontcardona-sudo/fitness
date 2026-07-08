"""Regresión de la auditoría profunda (bugs que aparecían "usando la web").

Cubre los fallos reales encontrados: crash de pasos con puntos de miles, borrado
RGPD con suscripción push, idempotencia/estado de create_period, retirada de
alérgenos del banco y parseo por-macro de la adaptación.
"""

from __future__ import annotations

import pytest


# ---- B2: parseo de "pasos" robusto (no revienta la vista de seguimiento) ----

def test_steps_num_never_raises_on_dotted_numbers():
    from app.routers.clients import _steps_num
    # Antes '1.234.567' / '12.05.2026' lanzaban ValueError → 500 en /tracking.
    assert _steps_num("1.234.567") == 1234567.0
    assert _steps_num("10.000") == 10000.0        # miles con punto
    assert _steps_num("cardio + 4500") == 4500.0
    assert _steps_num("1.2.3") == 123.0
    assert _steps_num("") is None
    assert _steps_num(None) is None


# ---- W1: los alérgenos se retiran del banco flexible ----

def test_strip_allergens_removes_option_with_allergen():
    from app.services.ai.generator import _strip_allergens_from_bank
    from app.schemas.ai import MealsFlexibleOutput

    meals = MealsFlexibleOutput.model_validate({
        "mode": "flexible_7",
        "slots": [{
            "slot": 1,
            "options": [
                {"key": "A", "title": "Tostada con crema de cacahuete",
                 "ingredients": [{"food": "crema de cacahuete", "grams": 20, "household": "1 cda"}],
                 "prep": "x", "prep_minutes": 3,
                 "macros": {"kcal": 300, "protein_g": 12, "carbs_g": 30, "fat_g": 14}, "tags": []},
                {"key": "B", "title": "Tostada con pavo",
                 "ingredients": [{"food": "pavo", "grams": 60, "household": "3 lonchas"}],
                 "prep": "x", "prep_minutes": 3,
                 "macros": {"kcal": 300, "protein_g": 20, "carbs_g": 30, "fat_g": 8}, "tags": []},
            ],
        }],
    })
    removed = _strip_allergens_from_bank(meals, ["frutos secos"])
    assert removed == 1
    keys = [o.key for o in meals.slots[0].options]
    assert keys == ["B"]  # la opción con cacahuete se fue; queda la segura


def test_strip_allergens_keeps_slot_if_no_safe_alternative():
    from app.services.ai.generator import _strip_allergens_from_bank
    from app.schemas.ai import MealsFlexibleOutput

    meals = MealsFlexibleOutput.model_validate({
        "mode": "flexible_7",
        "slots": [{
            "slot": 1,
            "options": [
                {"key": "A", "title": "Yogur", "ingredients": [{"food": "yogur", "grams": 125, "household": "1"}],
                 "prep": "x", "prep_minutes": 1,
                 "macros": {"kcal": 100, "protein_g": 10, "carbs_g": 8, "fat_g": 3}, "tags": []},
            ],
        }],
    })
    removed = _strip_allergens_from_bank(meals, ["lactosa"])
    # Sin alternativa segura NO se vacía el slot (el flag ⚠ ALÉRGENO avisará).
    assert removed == 0
    assert len(meals.slots[0].options) == 1


# ---- estos requieren BD ----

def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text
        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.seeds.run import main as seed_main
    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    import os
    r = client.post("/api/auth/login",
                    json={"username": "coach1", "password": os.environ.get("ADMIN_1_PASS", "passw0rd")})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _email():
    import uuid
    return f"audit_{uuid.uuid4().hex[:8]}@example.com"


@needs_db
def test_delete_client_with_push_subscription_does_not_500(client, auth):
    """B1: borrar un cliente con suscripción push no debe fallar (RGPD)."""
    from app.db import SessionLocal
    from app.models import PushSubscription

    body = client.post("/api/clients", headers=auth,
                       json={"full_name": "Push User", "email": _email()}).json()
    cid = body["client"]["id"]
    db = SessionLocal()
    try:
        db.add(PushSubscription(client_id=cid, endpoint=f"https://push.example/{cid}",
                                p256dh="k", auth="a"))
        db.commit()
    finally:
        db.close()
    r = client.delete(f"/api/clients/{cid}?confirm=Push User", headers=auth)
    assert r.status_code == 204


@needs_db
def test_create_period_rejects_when_closed_period_pending(client, auth):
    """B6: con una revisión cerrada pendiente de feedback no se abre otro período."""
    from app.db import SessionLocal
    from app.models import Period
    from sqlalchemy import select

    body = client.post("/api/clients", headers=auth,
                       json={"full_name": "Closed Period", "email": _email()}).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]
    client.post(f"/api/p/{token}/anamnesis", json={
        "sex": "male", "birth_date": "1994-03-10", "height_cm": 180, "start_weight_kg": 82,
        "goal_type": "fat_loss", "goal_weight_kg": 76, "level": "intermediate",
        "training_days": 4, "session_max_min": 75, "training_place": "gym",
        "equipment": ["barra"], "excluded_exercise_ids": [], "meals_per_day": 4,
        "meal_schedule": [{"slot": i, "name": n, "time": t} for i, n, t in
                          [(1, "D", "08:00"), (2, "C", "14:00"), (3, "M", "18:00"), (4, "Ce", "21:30")]],
        "food_allergies": [], "food_dislikes": [], "food_likes": [], "diet_mode": "flexible_7",
        "consent_accepted": True,
    })
    from tests.test_integration_a3 import _plan_content
    nutrition, training, education, flags = _plan_content()
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags}).json()
    client.post(f"/api/plans/{plan['id']}/publish", headers=auth)

    # Fuerza el período abierto a "closed" (revisión entregada, feedback pendiente).
    db = SessionLocal()
    try:
        p = db.scalar(select(Period).where(Period.client_id == cid, Period.status == "open"))
        p.status = "closed"
        db.commit()
    finally:
        db.close()

    from datetime import date
    r = client.post(f"/api/clients/{cid}/periods", headers=auth,
                    json={"plan_id": plan["id"], "starts_on": date.today().isoformat(), "days": 14})
    assert r.status_code == 409  # no abre un segundo período no analizado
