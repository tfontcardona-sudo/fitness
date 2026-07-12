"""Tests de los paquetes/planes DQR (Start / Full / Pro).

Verifica la adaptación de la app al paquete del cliente:
- El portal expone `package_tier` para ocultar el entreno en Start.
- Un plan solo-nutrición (Start) se persiste sin entrenamiento y el portal lo
  sirve sin romperse.
- La entrega por email de la planificación funciona (paquetes Start/Full).

Requiere PostgreSQL (igual que test_portal / test_integration_a3).
"""

from __future__ import annotations

import uuid
import warnings

import pytest

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
    # Firmamos el token directamente (no vía /auth/login) para no consumir el
    # límite de 5 logins/minuto por IP, que comparten todos los módulos de test.
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(ADMIN_USER)}"}


_ANAM = {
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


def _create(client, auth, tier: str) -> tuple[int, str]:
    body = client.post("/api/clients", headers=auth, json={
        "full_name": f"Tier {tier}", "email": f"tier-{uuid.uuid4().hex[:8]}@example.com",
        "package_tier": tier,
    }).json()
    return body["client"]["id"], body["links"]["portal_token"]


def _nutrition_only_plan_content():
    """Genera un plan SOLO-NUTRICIÓN con el pipeline y un cliente scripted."""
    from app.services.ai.generator import ClientContext, generate_monthly_plan
    from tests.test_ai_service import (
        ScriptedClient,
        _flexible_meals_json,
        _nutrition_only_core_json,
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
        exercise_library=[],
    )
    sc = ScriptedClient([_nutrition_only_core_json(), _flexible_meals_json()])
    plan = generate_monthly_plan(ctx, sc, include_training=False)
    return plan.to_persistable()


def test_portal_state_exposes_package_tier(client, auth):
    # Pro (por defecto) y Start deben verse tal cual en el estado del portal.
    _, token_pro = _create(client, auth, "pro")
    assert client.get(f"/api/p/{token_pro}/state").json()["package_tier"] == "pro"

    _, token_start = _create(client, auth, "start")
    assert client.get(f"/api/p/{token_start}/state").json()["package_tier"] == "start"


def test_start_plan_is_nutrition_only(client, auth):
    cid, token = _create(client, auth, "start")
    assert client.post(f"/api/p/{token}/anamnesis", json=_ANAM).status_code == 200

    nutrition, training, education, flags = _nutrition_only_plan_content()
    assert training is None and education is None  # solo-nutrición

    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags, "generated_by": "test",
    }).json()
    client.post(f"/api/plans/{plan['id']}/publish", headers=auth)

    # El portal sirve el plan sin entreno y no se rompe.
    state = client.get(f"/api/p/{token}/state").json()
    assert state["package_tier"] == "start" and state["has_plan"] is True
    full = client.get(f"/api/p/{token}/plan").json()
    assert full["nutrition"] and full["training"] is None
    # La pantalla de entreno responde vacía (sin sesiones), no un error.
    tr = client.get(f"/api/p/{token}/training").json()
    assert tr["sessions"] == []


def test_send_plan_by_email(client, auth, monkeypatch):
    from app.config import settings
    # Sin SMTP real: forzamos el toggle a off para un resultado determinista.
    monkeypatch.setattr(settings, "emails_enabled", False)

    cid, token = _create(client, auth, "full")
    client.post(f"/api/p/{token}/anamnesis", json=_ANAM)
    nutrition, training, education, flags = _nutrition_only_plan_content()
    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": nutrition, "training_json": training,
        "education_json": education, "guardrail_flags": flags, "generated_by": "test",
    }).json()
    client.post(f"/api/plans/{plan['id']}/publish", headers=auth)

    r = client.post(f"/api/plans/{plan['id']}/send-email", headers=auth)
    assert r.status_code == 200
    assert r.json()["email_status"] == "disabled"


def test_email_status_reports_missing_config(client, auth):
    # En el entorno de test no hay SMTP configurado: el diagnóstico lo dice.
    r = client.get("/api/email/status", headers=auth).json()
    assert r["config"]["ready"] is False
    assert any("SMTP_PASS" in m for m in r["config"]["missing"])


def test_email_test_endpoint_reports_failure_reason(client, auth):
    # Sin SMTP, el envío de prueba falla con una causa legible (no silencioso).
    r = client.post("/api/email/test", headers=auth, json={"to": "x@example.com"}).json()
    assert r["status"] == "failed"
    assert r["error"] and "SMTP" in r["error"]
    # El intento queda registrado con su motivo para diagnóstico posterior.
    recent = client.get("/api/email/status", headers=auth).json()["recent"]
    assert any(e["kind"] == "test" and e["error"] for e in recent)
