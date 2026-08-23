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


def test_copiar_solo_entreno_completa_la_dieta_con_la_base(client, auth):
    """Guardar un "sistema de entrenamiento" y aplicarlo a un cliente con
    dieta contratada no puede dejarle la dieta vacía: la mitad que falta se
    completa con la base determinista del sistema (0 créditos)."""
    origen = _cliente(client, auth, full_name="Origen Sistema Entreno")
    plan_origen = _plan_base(client, auth, origen)

    r = client.post("/api/plan-library/templates", headers=auth,
                    json={"plan_id": plan_origen["id"], "title": "Sistema torso-pierna"})
    tpl_id = r.json()["id"]
    # El modelo se queda SIN nutrición (simula un sistema de solo entreno).
    from app.db import SessionLocal
    from app.models import PlanTemplate

    db = SessionLocal()
    try:
        tpl = db.get(PlanTemplate, tpl_id)
        tpl.nutrition_json = None
        db.commit()
    finally:
        db.close()

    destino = _cliente(client, auth, full_name="Destino Full Sistema")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "template_id": tpl_id})
    assert r.status_code == 200, r.text
    copia = r.json()
    assert copia["training"] is not None
    assert copia["nutrition"] is not None, "la dieta debía completarse con la base"
    assert copia["nutrition"]["target_kcal"] > 0
    assert any("no traía dieta" in w for w in copia["warnings"])
    client.delete(f"/api/plan-library/templates/{tpl_id}", headers=auth)


def test_el_tope_calorico_de_la_copia_usa_el_tdee_del_destino(client, auth):
    """CRÍTICO de la revisión: reconcile corría con el tdee_kcal del ORIGEN
    todavía en el JSON, y clamp_targets acotaba las kcal del destino contra
    ese TDEE ajeno — a una clienta ligera la copia le dejaba MÁS kcal de las
    suyas (el suelo TDEE−30% del origen quedaba por encima de su objetivo)."""
    origen = _cliente(client, auth, full_name="Origen Pesado",
                      start_weight_kg=105, height_cm=190)
    plan_origen = _plan_base(client, auth, origen)
    tdee_origen = plan_origen["nutrition"]["tdee_kcal"]

    destino = _cliente(client, auth, full_name="Destino Muy Ligera", sex="female",
                       start_weight_kg=50, height_cm=158, goal_type="fat_loss")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    assert r.status_code == 200, r.text
    nut = r.json()["nutrition"]
    reco = client.get(f"/api/clients/{destino}/macro-recommendation",
                      headers=auth).json()
    assert nut["tdee_kcal"] == pytest.approx(reco["tdee"], abs=1)
    assert nut["target_kcal"] == pytest.approx(reco["kcal"], abs=1)
    # Y desde luego NO el suelo del TDEE del origen.
    assert nut["target_kcal"] < tdee_origen * 0.7 + 50


def test_descartar_un_borrador_copia(client, auth):
    origen = _cliente(client, auth, full_name="Origen Descartable")
    plan_origen = _plan_base(client, auth, origen)
    destino = _cliente(client, auth, full_name="Destino Descartable")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    copia = r.json()

    r = client.post(f"/api/plans/{copia['id']}/discard", headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "superseded"
    # Un plan publicado NO se descarta.
    r = client.post(f"/api/plans/{plan_origen['id']}/publish", headers=auth)
    assert r.status_code == 200
    r = client.post(f"/api/plans/{plan_origen['id']}/discard", headers=auth)
    assert r.status_code == 409


def test_activar_retira_los_avisos_de_copia(client, auth):
    """Los avisos de copia eran notas del borrador: al activar, los chequeos
    vivos toman el relevo — congelados aquí duplicaban avisos para siempre."""
    origen = _cliente(client, auth, full_name="Origen Flags")
    plan_origen = _plan_base(client, auth, origen)
    destino = _cliente(client, auth, full_name="Destino Flags")
    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    copia = r.json()
    assert any(f.startswith("copiado de") for f in copia["guardrail_flags"])

    r = client.post(f"/api/plans/{copia['id']}/publish", headers=auth)
    assert r.status_code == 200, r.text
    flags = r.json()["guardrail_flags"] or []
    assert not any(f.startswith("copiado de") or f.startswith("copia: ")
                   for f in flags), flags


def test_el_aviso_de_alergeno_mira_titulo_y_preparacion(client, auth):
    """Regresión de la revisión adversarial: el aviso de la copia usaba solo
    los INGREDIENTES (más laxo que el Revisor 0). Un subingrediente escondido
    en la preparación («salsa pesto» → frutos secos) debe avisar igual."""
    from app.db import SessionLocal
    from app.models import Client as ClientModel
    from app.services.plan_library import _avisos_de_seguridad

    cid = _cliente(client, auth, full_name="Alérgica Ligera",
                   food_allergies=["frutos secos"])
    nutrition = {
        "meal_bank": {"mode": "flexible_7", "slots": [{
            "slot": 1,
            "options": [{
                "key": "pollo_pesto", "title": "Pollo con arroz",
                "prep": "Saltea el pollo y termina con una cucharada de salsa pesto.",
                # Ingredientes LIMPIOS: el criterio de solo-ingredientes no lo veía.
                "ingredients": [{"food": "Pollo"}, {"food": "Arroz"}],
            }],
        }]},
    }
    with SessionLocal() as db:
        destino = db.get(ClientModel, cid)
        avisos = _avisos_de_seguridad(nutrition, None, destino, db)
    assert any("ALÉRGENO" in a for a in avisos), avisos


def test_copiar_entreno_a_cliente_solo_entreno_no_exige_dieta(client, auth):
    """Regresión: a un cliente SOLO-ENTRENO (sin modo de dieta en la ficha) se
    le puede copiar una rutina — el contrato calórico no pinta nada ahí y
    antes la copia moría con 422 «falta Modo de dieta»."""
    origen = _cliente(client, auth, full_name="Origen Full B")
    plan_origen = _plan_base(client, auth, origen)

    r = client.post("/api/clients", headers=auth, json={
        "full_name": "Destino Solo Entreno",
        "email": f"lib-{uuid.uuid4().hex[:8]}@example.com",
    })
    assert r.status_code == 201, r.text
    destino = r.json()["client"]["id"]
    ficha = {k: v for k, v in FICHA.items() if k != "diet_mode"}
    r = client.patch(f"/api/clients/{destino}", headers=auth,
                     json=ficha | {"package_tier": "train"})
    assert r.status_code == 200, r.text

    r = client.post("/api/plan-library/apply", headers=auth,
                    json={"client_id": destino, "plan_id": plan_origen["id"]})
    assert r.status_code == 200, r.text
    copia = r.json()
    assert copia["training"], "el entreno tiene que llegar igual"
    assert copia["nutrition"] is None
    assert any("no tiene nutrición contratada" in w for w in copia["warnings"])
