"""Biblioteca de planificaciones: copiar entre clientes, modelos y seguridad.

Lo importante que NO puede romperse:
- Los NÚMEROS nunca viajan: al pegar en otro cliente, kcal y macros son las
  del DESTINO (metrics), no las del origen. 0 créditos en todo el flujo.
- La copia AVISA de los choques con la ficha del destino (alérgenos, patrón).
- El paquete del destino manda (a un Start no se le pega entreno).
- La copia queda en borrador y editarla NO la activa a medias.

Requiere PostgreSQL.
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

        eng = create_engine(settings.database_url)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
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
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


FICHA = {
    "sex": "male", "birth_date": "1990-05-01", "height_cm": 178,
    "start_weight_kg": 82, "goal_type": "fat_loss", "level": "intermediate",
    "training_days": 4, "session_max_min": 60, "training_place": "gym",
    "diet_mode": "flexible_7",
}


def _cliente(client, auth, **extra) -> int:
    r = client.post("/api/clients", headers=auth, json={
        "full_name": extra.pop("full_name", "Cliente Biblioteca"),
        "email": f"lib-{uuid.uuid4().hex[:8]}@example.com",
        **extra,
    })
    assert r.status_code == 201, r.text
    cid = r.json()["client"]["id"]
    r = client.patch(f"/api/clients/{cid}", headers=auth, json=FICHA | extra)
    assert r.status_code == 200, r.text
    return cid


def _plan_base(client, auth, cid: int) -> dict:
    """La base sin IA es el origen perfecto para estas pruebas: estructura
    completa (comidas + banco + sesiones) y 0 créditos."""
    r = client.post(f"/api/clients/{cid}/scaffold-plan", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def test_copiar_recalcula_los_numeros_para_el_destino(client, auth):
    origen = _cliente(client, auth, full_name="Origen Fuerte")
    plan_origen = _plan_base(client, auth, origen)

    # Destino MUY distinto (mujer, 55 kg, ganancia muscular): si las kcal del
    # origen viajaran tal cual, sería un plan peligroso.
    destino = _cliente(client, auth, full_name="Destino Ligera", sex="female",
                       start_weight_kg=55, goal_type="muscle_gain")

    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    assert r.status_code == 200, r.text
    copia = r.json()

    reco = client.get(f"/api/clients/{destino}/macro-recommendation",
                      headers=auth).json()
    assert reco.get("available"), reco
    assert copia["nutrition"]["target_kcal"] == pytest.approx(
        reco["kcal"], abs=1), "las kcal no son las del destino"
    # Las comidas SUMAN el total nuevo (rescale + reconcile, como el editor).
    suma = sum(m["target"]["kcal"] for m in copia["nutrition"]["meals"])
    assert suma == pytest.approx(copia["nutrition"]["target_kcal"], abs=2)
    # Y nada del ciclo del origen viaja.
    assert "applied_adjustments" not in copia["nutrition"]
    assert copia["status"] == "draft"
    assert any("copiado de" in f for f in copia["guardrail_flags"])


def test_copiar_avisa_del_alergeno_del_destino(client, auth):
    origen = _cliente(client, auth, full_name="Origen Omnívoro")
    plan_origen = _plan_base(client, auth, origen)
    tiene_pollo = any(
        "pollo" in str(plan_origen.get("nutrition") or {}).lower() for _ in [0])
    if not tiene_pollo:
        pytest.skip("la base generada no trae pollo; el aviso se prueba con otro dato")

    destino = _cliente(client, auth, full_name="Destino Alérgica",
                       food_allergies=["pollo"])
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    assert r.status_code == 200, r.text
    avisos = " ".join(r.json()["warnings"])
    assert "ALÉRGENO" in avisos, f"no avisó del alérgeno: {avisos!r}"


def test_a_un_start_no_se_le_pega_el_entreno(client, auth):
    origen = _cliente(client, auth, full_name="Origen Full")
    plan_origen = _plan_base(client, auth, origen)
    destino = _cliente(client, auth, full_name="Destino Start",
                       package_tier="nutri")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["training"] is None
    assert any("no tiene entrenamiento contratado" in w for w in r.json()["warnings"])


def test_modelo_guardar_aplicar_renombrar_borrar(client, auth):
    origen = _cliente(client, auth, full_name="Origen Modelo")
    plan_origen = _plan_base(client, auth, origen)

    r = client.post("/api/plan-library/templates", headers=auth,
                    json={"plan_id": plan_origen["id"], "title": "Planificación base"})
    assert r.status_code == 201, r.text
    tpl = r.json()
    assert tpl["summary"], "el modelo debe llevar su resumen de una línea"

    lib = client.get("/api/plan-library", headers=auth).json()
    assert any(t["id"] == tpl["id"] for t in lib["templates"])
    # El pool de clientes también está, con resumen.
    assert any(p["client_id"] == origen and p["summary"] for p in lib["client_plans"])

    destino = _cliente(client, auth, full_name="Destino Modelo")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "template_id": tpl["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["nutrition"]["target_kcal"] > 0

    r = client.patch(f"/api/plan-library/templates/{tpl['id']}", headers=auth,
                     json={"title": "Base 2.0"})
    assert r.status_code == 200 and r.json()["title"] == "Base 2.0"

    assert client.delete(f"/api/plan-library/templates/{tpl['id']}",
                         headers=auth).status_code == 204
    lib = client.get("/api/plan-library", headers=auth).json()
    assert not any(t["id"] == tpl["id"] for t in lib["templates"])


def test_editar_la_copia_no_la_activa_a_medias(client, auth):
    origen = _cliente(client, auth, full_name="Origen Editable")
    plan_origen = _plan_base(client, auth, origen)
    destino = _cliente(client, auth, full_name="Destino Editable")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    copia = r.json()

    # Un retoque cualquiera (quitar un día del entreno) NO puede activarla:
    # el coach la está adaptando y el cliente no puede ver un plan a medias.
    tr = copia["training"]
    assert len(tr["sessions"]) >= 2
    tr["sessions"] = tr["sessions"][:-1]
    r = client.patch(f"/api/plans/{copia['id']}", headers=auth,
                     json={"training_json": tr})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft", "editar la copia la activó a medias"


def test_la_base_sin_ia_esta_disponible_para_todos_los_niveles(client, auth):
    """El botón "Crear a mano · 0 créditos" es ahora para TODOS, no solo para
    el avanzado: el backend nunca lo restringió y la web sí lo hacía."""
    cid = _cliente(client, auth, full_name="Principiante Manual", level="beginner")
    r = client.post(f"/api/clients/{cid}/scaffold-plan", headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"


def test_aplicar_exige_exactamente_un_origen(client, auth):
    destino = _cliente(client, auth, full_name="Destino Ambiguo")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino})
    assert r.status_code == 400
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": 1, "template_id": 1})
    assert r.status_code == 400
