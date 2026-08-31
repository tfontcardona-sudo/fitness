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
    # Se garantiza el usuario: los seeds solo crean admin si hay ADMIN_1_USER/PASS,
    # así que en una BD recién migrada coach1 podría no existir → 401.
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
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


# ---- consumo EN VIVO (eventos de uso) ----

@needs_db
def test_eventos_de_uso_alimentan_el_consumo_en_vivo(client, auth):
    from app.db import SessionLocal
    from app.models import AiUsageEvent
    from app.services.ai_credit import record_usage

    with SessionLocal() as db:
        db.query(AiUsageEvent).delete()
        db.commit()

    # Dos llamadas reales → el gasto de hoy y de la ventana se ven sin apuntar saldo.
    record_usage("claude-haiku-4-5", 1_000_000, 0)      # $1
    record_usage("claude-opus-4-8", 0, 200_000)          # $5

    data = client.get("/api/ai-credit", headers=auth).json()
    assert data["spent_today_usd"] == pytest.approx(6.0)
    assert data["spent_window_usd"] == pytest.approx(6.0)
    assert data["calls_window"] == 2
    assert data["last_call_at"] is not None


@needs_db
def test_planes_restantes_desde_el_coste_medio():
    from app.services.ai_credit import plans_left

    # $90 restantes a $6 el plan → 15 planes.
    assert plans_left(90.0, 6.0) == 15
    # Sin saldo apuntado o sin histórico no se inventa un número.
    assert plans_left(None, 6.0) is None
    assert plans_left(90.0, None) is None
    assert plans_left(90.0, 0.0) is None
    # Nunca negativo.
    assert plans_left(0.0, 6.0) == 0


@needs_db
def test_resumen_de_uso_nunca_revienta():
    # usage_summary es best-effort: con la BD viva siempre devuelve las claves.
    from app.db import SessionLocal
    from app.services.ai_credit import usage_summary

    with SessionLocal() as db:
        s = usage_summary(db)
    assert set(s) >= {"spent_today_usd", "spent_window_usd", "calls_window",
                      "last_call_at", "avg_cost_per_plan_usd", "window_days"}


def test_el_gasto_de_varios_revisores_en_paralelo_no_se_pisa():
    """Los 8-10 revisores del panel corren EN PARALELO, cada uno con su sesión.
    Con el patrón leer-modificar-escribir todos leían el mismo saldo y el
    último en escribir se llevaba por delante lo que habían sumado los otros:
    el gasto anotado salía por debajo del real y el coach veía un saldo
    optimista justo en la operación que más créditos consume."""
    import threading

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import AiCreditState, AiUsageEvent
    from app.services import ai_credit

    db = SessionLocal()
    try:
        estado = ai_credit.get_state(db)
        antes = float(estado.spent_usd or 0.0)
        db.expire_all()
    finally:
        db.close()

    coste = ai_credit.estimate_cost_usd("claude-opus-4-8", 10_000, 2_000)
    assert coste > 0, "el modelo de prueba tiene que costar algo"

    hilos = [threading.Thread(target=ai_credit.record_usage,
                              args=("claude-opus-4-8", 10_000, 2_000))
             for _ in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    db = SessionLocal()
    try:
        estado = db.scalar(select(AiCreditState).limit(1))
        db.refresh(estado)
        sumado = float(estado.spent_usd or 0.0) - antes
        esperado = coste * 8
        assert abs(sumado - esperado) < esperado * 0.01, (
            f"se anotaron {sumado:.6f} $ de {esperado:.6f} $: se pisaron entre ellos")
    finally:
        # Limpieza: se deja el saldo como estaba y fuera los eventos de prueba.
        estado.spent_usd = antes
        db.query(AiUsageEvent).filter(
            AiUsageEvent.model == "claude-opus-4-8",
            AiUsageEvent.input_tokens == 10_000,
            AiUsageEvent.output_tokens == 2_000).delete()
        db.commit()
        db.close()
