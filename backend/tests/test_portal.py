"""Test de integración del portal del cliente (Fase 6).

Recorre el ciclo completo desde el lado del coach y del cliente:
alta → anamnesis → plan generado (IA mock) → publicar → abrir período →
vista HOY → registro de diario → cierre. Requiere PostgreSQL.

El plan se genera con el servicio de IA real pero con un cliente SCRIPTED
(sin API), reutilizando las fixtures de test_ai_service para producir un plan
válido que pasa los guardrails.
"""

from __future__ import annotations

import io
import json
import uuid
import warnings
from datetime import date, timedelta

import pytest
from PIL import Image

warnings.filterwarnings("ignore")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")

ADMIN_USER = "coach1"
ADMIN_PASS = "passw0rd"


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
                    json={"username": ADMIN_USER, "password": os.environ.get("ADMIN_1_PASS", ADMIN_PASS)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _generate_plan_content():
    """Genera contenido de plan válido con el pipeline de IA y cliente mock."""
    from app.services.ai.generator import ClientContext, generate_monthly_plan
    from tests.test_ai_service import (
        ScriptedClient,
        _education_json,
        _flexible_meals_json,
        _valid_core_json,
    )

    ctx = ClientContext(
        sex="male", age=30, height_cm=180, weight_kg=82, goal_type="fat_loss",
        level="intermediate", training_days=4, session_max_min=75,
        training_place="gym", diet_mode="flexible_7", meals_per_day=4,
        meal_schedule=[{"slot": i, "name": n, "time": t} for i, n, t in
                       [(1, "Desayuno", "08:00"), (2, "Comida", "14:00"),
                        (3, "Merienda", "18:00"), (4, "Cena", "21:30")]],
        food_allergies=[], food_dislikes=[], food_likes=["pollo"],
        contraindications=set(), body_fat_pct=None,
        bmr=1780, tdee=2759, target_kcal=2200, energy_method="mifflin",
        exercise_library=[
            {"id": 12, "canonical_name": "Press banca", "movement_pattern": "horizontal_push",
             "muscle_primary": "pecho", "contraindications": [], "equipment": ["barra"],
             "level_min": 2, "archived": False},
        ],
    )
    sc = ScriptedClient([_valid_core_json(), _flexible_meals_json(), _education_json()])
    plan = generate_monthly_plan(ctx, sc)
    nutrition, training, education, flags = plan.to_persistable()
    return nutrition, training, education, flags


def test_full_portal_cycle(client, auth):
    # 1) Alta + anamnesis (flexible)
    body = client.post("/api/clients", headers=auth,
                       json={"full_name": "Portal Tester", "email": f"portal-{uuid.uuid4().hex[:8]}@example.com"}).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]

    anam = {
        "sex": "male", "birth_date": "1994-03-10", "height_cm": 180, "start_weight_kg": 82,
        "goal_type": "fat_loss", "goal_weight_kg": 76, "level": "intermediate",
        "training_days": 4, "session_max_min": 75, "training_place": "gym",
        "equipment": ["barra"], "excluded_exercise_ids": [], "meals_per_day": 4,
        "meal_schedule": [{"slot": i, "name": n, "time": t} for i, n, t in
                          [(1, "Desayuno", "08:00"), (2, "Comida", "14:00"),
                           (3, "Merienda", "18:00"), (4, "Cena", "21:30")]],
        "food_allergies": [], "food_dislikes": [], "food_likes": ["pollo"],
        "diet_mode": "flexible_7", "consent_accepted": True,
    }
    assert client.post(f"/api/p/{token}/anamnesis", json=anam).status_code == 200

    # 2) Estado antes del plan: sin plan, sin período
    state = client.get(f"/api/p/{token}/state").json()
    assert state["has_plan"] is False and state["period"] is None
    assert state["status"] == "onboarding"
    assert state["brand"]["name"]

    # 3) Coach genera y crea el plan
    nutrition, training, education, flags = _generate_plan_content()
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags, "generated_by": "test",
    }).json()
    assert plan["status"] == "draft"

    # 4) Publicar → cliente active
    pub = client.post(f"/api/plans/{plan['id']}/publish", headers=auth).json()
    assert pub["status"] == "published"
    assert client.get(f"/api/clients/{cid}", headers=auth).json()["status"] == "active"

    # 5) Abrir período (empieza hoy, 14 días)
    today = date.today()
    per = client.post(f"/api/clients/{cid}/periods", headers=auth, json={
        "plan_id": plan["id"], "starts_on": today.isoformat(), "days": 14,
    }).json()
    assert per["period_index"] == 1

    # 6) Estado tras el plan: con plan y período
    state = client.get(f"/api/p/{token}/state").json()
    assert state["has_plan"] is True
    assert state["period"]["days_left"] >= 0
    assert state["period"]["can_close"] is False  # día 1, aún no

    # 7) Vista HOY: comidas con opciones; sesión según el weekday
    todayv = client.get(f"/api/p/{token}/today").json()
    assert todayv["day_label"]
    assert len(todayv["meals"]) == 4
    assert all(len(m["options"]) == 7 for m in todayv["meals"])  # flexible: 7 opciones
    assert todayv["already_logged"] is False

    # 8) Plan completo navegable
    full = client.get(f"/api/p/{token}/plan").json()
    assert full["nutrition"] and full["training"] and full["education"]
    assert full["diet_mode"] == "flexible_7"

    # 9) Registro de diario (autosave) con elección de opciones y un set
    diary = {
        "log_date": today.isoformat(), "weight_kg": 81.5, "sleep_hours": 7.5,
        "diet_adherence": "yes", "energy_1_5": 4, "mood_1_5": 4, "fatigue_1_5": 2,
        "chosen_options_json": {"1": "A", "2": "C"},
        "workout_sets": [
            {"exercise_id": 12, "set_number": 1, "reps": 8, "weight_kg": 60, "rpe": 8},
            {"exercise_id": 12, "set_number": 2, "reps": 7, "weight_kg": 60, "rpe": 9},
        ],
    }
    assert client.put(f"/api/p/{token}/diary", json=diary).json()["saved"] is True

    # 10) Releer el diario: persistió todo
    got = client.get(f"/api/p/{token}/diary/{today.isoformat()}").json()
    assert got["exists"] and got["weight_kg"] == 81.5
    assert len(got["workout_sets"]) == 2

    # HOY ahora marca already_logged y la opción elegida
    todayv2 = client.get(f"/api/p/{token}/today").json()
    assert todayv2["already_logged"] is True
    slot1 = next(m for m in todayv2["meals"] if m["slot"] == 1)
    assert slot1["chosen_key"] == "A"

    # 11) Autosave idempotente: re-guardar no duplica sets
    client.put(f"/api/p/{token}/diary", json=diary)
    got2 = client.get(f"/api/p/{token}/diary/{today.isoformat()}").json()
    assert len(got2["workout_sets"]) == 2

    # 12) Cierre antes de día 14 → 403
    close_body = {"closing_weight_kg": 80.5, "closing_rating": 4}
    assert client.post(f"/api/p/{token}/close", json=close_body).status_code == 403


def test_close_period_when_due(client, auth):
    """Período que empezó hace 14 días: el cierre debe estar disponible."""
    body = client.post("/api/clients", headers=auth,
                       json={"full_name": "Cierre Listo", "email": f"cierre-{uuid.uuid4().hex[:8]}@example.com"}).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]

    nutrition, training, education, flags = _generate_plan_content()
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education,
    }).json()
    client.post(f"/api/plans/{plan['id']}/publish", headers=auth)

    start = date.today() - timedelta(days=14)
    client.post(f"/api/clients/{cid}/periods", headers=auth,
                json={"plan_id": plan["id"], "starts_on": start.isoformat(), "days": 14})

    state = client.get(f"/api/p/{token}/state").json()
    assert state["period"]["can_close"] is True

    # Cierre con foto
    img = Image.new("RGB", (40, 40), (90, 80, 70))
    b = io.BytesIO(); img.save(b, format="JPEG"); b.seek(0)
    photos = client.post(f"/api/p/{token}/close/photos",
                         files=[("files", ("c.jpg", b, "image/jpeg"))])
    assert photos.status_code == 200

    res = client.post(f"/api/p/{token}/close", json={
        "closing_weight_kg": 80.2, "closing_rating": 4,
        "closing_hardest": "Las cenas el finde", "closing_waist_cm": 84,
    })
    assert res.status_code == 200 and res.json()["closed"] is True
    # cliente pasa a review_pending
    assert client.get(f"/api/clients/{cid}", headers=auth).json()["status"] == "review_pending"


def test_change_request_creates_and_alerts(client, auth):
    body = client.post("/api/clients", headers=auth,
                       json={"full_name": "Pide Ajuste", "email": f"ajuste-{uuid.uuid4().hex[:8]}@example.com"}).json()
    cid = body["client"]["id"]
    token = body["links"]["portal_token"]

    cr = client.post(f"/api/p/{token}/change-request",
                     json={"message": "No puedo hacer sentadilla, me molesta la rodilla"})
    assert cr.status_code == 200 and cr.json()["status"] == "open"

    # el coach la ve en su cola
    crs = client.get(f"/api/clients/{cid}/change-requests", headers=auth).json()
    assert len(crs) == 1
    # y puede resolverla
    rid = crs[0]["id"]
    assert client.post(f"/api/change-requests/{rid}/resolve", headers=auth).json()["status"] == "resolved"
