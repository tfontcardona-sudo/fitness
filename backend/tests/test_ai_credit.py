"""Créditos IA (Anthropic): contabilidad local + endpoints del botón del sidebar."""

import pytest

from app.services.ai_credit import estimate_cost_usd


def test_coste_por_familia_de_modelo():
    # Opus: $5/M entrada, $25/M salida.
    assert estimate_cost_usd("claude-opus-4-8", 1_000_000, 0) == 5.00
    assert estimate_cost_usd("claude-opus-4-8", 0, 1_000_000) == 25.00
    # Haiku: $1/M, $5/M — el modelo LIGHT del portal.
    assert estimate_cost_usd("claude-haiku-4-5-20251001", 2_000_000, 1_000_000) == 7.00
    # Familia desconocida → tarifa conservadora (la de opus), nunca 0.
    assert estimate_cost_usd("modelo-raro", 1_000_000, 0) == 5.00
    assert estimate_cost_usd("", 0, 0) == 0.0


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

    # Como en el resto de módulos: los seeds crean el admin/brand si faltan.
    # Sin esto, este archivo corre PRIMERO (orden alfabético) y en una BD
    # recién migrada el coach no existe → 401 y fallos que no son del código.
    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth():
    # Token directo: /api/auth/login está capado a 5/min contra fuerza bruta.
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


@needs_db
def test_requiere_autenticacion(client):
    assert client.get("/api/ai-credit").status_code in (401, 403)


@needs_db
def test_fijar_saldo_y_descontar_uso(client, auth):
    # El coach apunta el saldo tras recargar → gasto a cero, restante = saldo.
    r = client.put("/api/ai-credit", headers=auth, json={"balance_usd": 100})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["balance_usd"] == 100 and data["spent_usd"] == 0
    assert data["remaining_usd"] == 100
    assert "console.anthropic.com" in data["recharge_url"]

    # Una llamada a la IA descuenta su coste real (misma vía que AIClient).
    from app.services.ai_credit import record_usage

    record_usage("claude-opus-4-8", 1_000_000, 200_000)  # 5 + 5 = $10
    data = client.get("/api/ai-credit", headers=auth).json()
    assert data["spent_usd"] == pytest.approx(10.0)
    assert data["remaining_usd"] == pytest.approx(90.0)

    # Nueva recarga apuntada → el contador de gasto se reinicia.
    data = client.put("/api/ai-credit", headers=auth, json={"balance_usd": 40}).json()
    assert data["remaining_usd"] == 40 and data["spent_usd"] == 0


@needs_db
def test_saldo_sin_configurar_no_inventa_numeros(client, auth):
    # Antes de configurar nada, remaining es None (el botón pide apuntarlo).
    from app.db import SessionLocal
    from app.models import AiCreditState

    with SessionLocal() as db:
        db.query(AiCreditState).delete()
        db.commit()

    data = client.get("/api/ai-credit", headers=auth).json()
    assert data["balance_usd"] is None and data["remaining_usd"] is None


def test_record_usage_jamas_revienta_sin_bd(monkeypatch):
    # La contabilidad es best-effort: sin BD no puede romper una generación.
    import app.services.ai_credit as mod

    def boom():
        raise RuntimeError("BD caída")

    monkeypatch.setattr("app.db.SessionLocal", boom)
    mod.record_usage("claude-opus-4-8", 1000, 1000)  # no debe lanzar
