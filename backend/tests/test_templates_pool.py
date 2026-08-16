"""Tests del POOL DE RUTINAS (plan_templates + /api/templates).

- Las plantillas SEMBRADAS resuelven el 100 % de sus ejercicios contra la
  biblioteca y quedan en el shape de plans.training_json.
- CRUD del pool + documento con la marca + "usar con un cliente" (nuevo crea el
  perfil con plan BORRADOR; existente añade el plan).

Requiere PostgreSQL (como test_portal).
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


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seeds.run import main as seed_main

    seed_main()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth(client):
    # Se firma el token directamente (sin /auth/login, que tiene rate limit) y
    # se garantiza que el usuario EXISTE (get_current_user lo busca en BD).
    from app.db import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    s = SessionLocal()
    try:
        if not s.query(User).filter_by(username=ADMIN_USER).first():
            s.add(User(username=ADMIN_USER, password_hash=hash_password("test-only")))
            s.commit()
    finally:
        s.close()
    return {"Authorization": f"Bearer {create_access_token(ADMIN_USER)}"}


@pytest.fixture()
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


def _routine_body(db, category="mantenimiento", title=None):
    """Rutina mínima válida con ids REALES de la biblioteca."""
    from sqlalchemy import select

    from app.models import Exercise

    ids = list(db.scalars(select(Exercise.id).order_by(Exercise.id).limit(3)))
    assert len(ids) == 3, "la biblioteca de ejercicios debe estar sembrada"
    return {
        "category": category,
        "title": title or f"Rutina test {uuid.uuid4().hex[:6]}",
        "case_note": "Caso de prueba",
        "level": "beginner",
        "training_place": "gym",
        "training_json": {
            "split_name": "Full body test",
            "sessions": [{
                "day": "Lunes", "name": "Sesión A", "warmup": "", "cooldown": "",
                "exercises": [
                    {"exercise_id": i, "sets": 3, "rep_range": "8-10",
                     "rir": "2", "rest_sec": 120, "technique_cue": ""}
                    for i in ids
                ],
            }],
        },
    }


# ------------------------------------------------------------ seeds del pool --
def test_seeds_del_pool_resuelven_al_cien_por_cien(db):
    """Cada plantilla de fábrica: ejercicios resueltos, 4 semanas de progresión,
    sesiones = days_per_week y rir como cadena (contrato del portal)."""
    try:
        from app.seeds.templates_data import TEMPLATES
    except Exception:
        pytest.skip("templates_data aún no generado")

    from app.services.templates import CATEGORY_KEYS, resolve_training

    assert len(TEMPLATES) >= 150
    per_cat: dict[str, int] = {}
    for entry in TEMPLATES:
        assert entry["category"] in CATEGORY_KEYS
        per_cat[entry["category"]] = per_cat.get(entry["category"], 0) + 1
        training = resolve_training(db, entry)  # TemplateError si algo no resuelve
        assert len(training["sessions"]) == entry["days_per_week"]
        assert [w["week"] for w in training["weekly_progression"]] == [1, 2, 3, 4]
        for s in training["sessions"]:
            for e in s["exercises"]:
                assert isinstance(e["rir"], str) and e["exercise_id"] >= 1
        # Eje DIETA del caso: sin él la plantilla no serviría al servicio de dieta
        assert 3 <= (entry.get("meals_per_day") or 0) <= 5
    # Los TRES grupos del negocio, con al menos 50 casos cada uno.
    assert set(per_cat) == CATEGORY_KEYS, per_cat
    assert all(n >= 50 for n in per_cat.values()), per_cat


def test_seed_plan_templates_idempotente(db):
    try:
        from app.seeds.templates_data import TEMPLATES  # noqa: F401
    except Exception:
        pytest.skip("templates_data aún no generado")

    from app.services.templates import seed_plan_templates

    seed_plan_templates(db)          # puede insertar (primera vez)
    assert seed_plan_templates(db) == 0  # re-ejecutar no duplica


# ------------------------------------------------------------------- API ----
def test_categorias_y_crud(client, auth, db):
    cats = client.get("/api/templates/categories", headers=auth).json()
    assert {c["key"] for c in cats} == {"masa", "definicion", "mantenimiento"}

    body = _routine_body(db)
    r = client.post("/api/templates", headers=auth, json=body)
    assert r.status_code == 201, r.text
    tpl = r.json()
    assert tpl["source"] == "manual" and tpl["days_per_week"] == 1
    # El backend normaliza el shape completo (progresión/cardio/deload de serie)
    assert [w["week"] for w in tpl["training_json"]["weekly_progression"]] == [1, 2, 3, 4]

    listado = client.get("/api/templates?category=mantenimiento", headers=auth).json()
    assert any(t["id"] == tpl["id"] for t in listado)

    r = client.patch(f"/api/templates/{tpl['id']}", headers=auth,
                     json={"title": "Renombrada", "level": "advanced"})
    assert r.status_code == 200 and r.json()["title"] == "Renombrada"

    # Documento con la marca (Word: no exige LibreOffice en el runner)
    r = client.get(f"/api/templates/{tpl['id']}/document?format=docx", headers=auth)
    assert r.status_code == 200 and len(r.content) > 10_000

    r = client.delete(f"/api/templates/{tpl['id']}", headers=auth)
    assert r.status_code == 204
    assert client.get(f"/api/templates/{tpl['id']}", headers=auth).status_code == 404


def test_editar_con_ejercicio_inexistente_da_422(client, auth, db):
    body = _routine_body(db)
    body["training_json"]["sessions"][0]["exercises"][0] = {
        "name": "Ejercicio inventado que no existe", "sets": 3,
        "rep_range": "8-10", "rir": "2", "rest_sec": 120, "technique_cue": "",
    }
    r = client.post("/api/templates", headers=auth, json=body)
    assert r.status_code == 422
    assert "fuera de la biblioteca" in r.json()["detail"]


def test_usar_con_cliente_nuevo_crea_perfil_y_borrador(client, auth, db):
    from sqlalchemy import select

    from app.models import Client, Plan

    body = _routine_body(db, category="mantenimiento")
    tpl = client.post("/api/templates", headers=auth, json=body).json()

    email = f"pool-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(f"/api/templates/{tpl['id']}/use", headers=auth, json={
        "new_client": {"full_name": "Cliente Del Pool", "email": email,
                       "package_tier": "train"},
    })
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["created_client"] is True

    nuevo = db.get(Client, out["client_id"])
    assert nuevo is not None and nuevo.status == "onboarding"
    # Ficha pre-rellenada con lo que la rutina sabe del caso
    assert nuevo.level == "beginner" and nuevo.training_days == 1
    plan = db.get(Plan, out["plan_id"])
    assert plan.status == "draft" and plan.generated_by == "template"
    assert plan.training_json["sessions"], "el plan copia la rutina"

    # Repetir el email → 409 (no crea duplicados)
    r = client.post(f"/api/templates/{tpl['id']}/use", headers=auth, json={
        "new_client": {"full_name": "Otro", "email": email},
    })
    assert r.status_code == 409

    # Cliente EXISTENTE → segundo plan borrador (month_index avanza)
    r = client.post(f"/api/templates/{tpl['id']}/use", headers=auth,
                    json={"client_id": out["client_id"]})
    assert r.status_code == 200
    plan2 = db.get(Plan, r.json()["plan_id"])
    assert plan2.month_index == plan.month_index + 1

    client.delete(f"/api/templates/{tpl['id']}", headers=auth)


# ------------------------------------------- eje dieta / servicios / sugerencias --
def test_filtro_por_servicio_y_documento_de_solo_dieta(client, auth, db):
    """El pool sirve a los TRES servicios: la misma plantilla entrega solo la
    dieta, solo el entreno o el pack, y el filtro `service` respeta eso."""
    from app.services.templates import seed_plan_templates

    seed_plan_templates(db)

    solo_dieta = client.get("/api/templates?service=nutri", headers=auth).json()
    assert solo_dieta, "las plantillas sembradas traen su dieta de referencia"
    tpl = next(t for t in solo_dieta if t["diet_focus"])
    assert 3 <= tpl["meals_per_day"] <= 5

    # Solo entreno: la rutina creada a mano no tiene dieta, así que NO sale
    body = _routine_body(db)
    manual = client.post("/api/templates", headers=auth, json=body).json()
    ids_nutri = {t["id"] for t in client.get("/api/templates?service=nutri", headers=auth).json()}
    ids_train = {t["id"] for t in client.get("/api/templates?service=train", headers=auth).json()}
    assert manual["id"] in ids_train and manual["id"] not in ids_nutri

    r = client.get(f"/api/templates/{tpl['id']}/document?format=docx&service=nutri", headers=auth)
    assert r.status_code == 200 and len(r.content) > 10_000
    client.delete(f"/api/templates/{manual['id']}", headers=auth)


def test_editar_las_comidas_rehace_la_dieta(client, auth, db):
    """Cambiar tomas o patrón desde el editor RECONSTRUYE la dieta de la
    plantilla (no deja el reparto viejo con la etiqueta nueva)."""
    from app.services.templates import seed_plan_templates

    seed_plan_templates(db)
    pool = client.get("/api/templates?service=nutri", headers=auth).json()
    tid = next(t["id"] for t in pool if (t["meals_per_day"] or 0) == 4)

    r = client.patch(f"/api/templates/{tid}", headers=auth,
                     json={"meals_per_day": 5, "diet_pattern": "vegetariano"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["meals_per_day"] == 5 and out["diet_pattern"] == "vegetariano"
    assert len(out["nutrition_json"]["meals"]) == 5
    # Y vuelve a dejarla como estaba (la suite no ensucia el pool sembrado)
    client.patch(f"/api/templates/{tid}", headers=auth,
                 json={"meals_per_day": 4, "diet_pattern": ""})


def test_recomendaciones_para_un_cliente(client, auth, db):
    """5 sugerencias del pool con su porqué: el camino rápido del coach."""
    from app.models import Client
    from app.security import new_portal_token
    from app.services.templates import seed_plan_templates

    seed_plan_templates(db)
    c = Client(full_name="Sugerencias Test", email=f"sug-{uuid.uuid4().hex[:8]}@example.com",
               package_tier="full", billing_period="unico", status="onboarding",
               portal_token="pendiente", goal_type="fat_loss", level="beginner",
               training_days=3, training_place="gym", sex="female", height_cm=165,
               start_weight_kg=78, meals_per_day=4, diet_pattern="vegetariano")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()

    r = client.get(f"/api/templates/recommend/{c.id}", headers=auth)
    assert r.status_code == 200, r.text
    sug = r.json()
    assert 1 <= len(sug) <= 5
    # Todas del grupo del objetivo, con motivo y resumen legibles
    assert sug[0]["category"] == "definicion"
    assert sug[0]["why"].startswith("Encaja por")
    assert "·" in sug[0]["summary"]
    # El patrón dietético del cliente pesa: alguna vegetariana entre las 5
    assert any(s["diet_pattern"] == "vegetariano" for s in sug)

    db.delete(c)
    db.commit()
