"""Plan BASE determinista para clientes avanzados (0 llamadas a la IA).

El coach de un avanzado monta el plan a mano pero no desde cero: el sistema
prepara borrador completo (números de metrics, comidas con target por toma,
banco determinista y sesiones desde la biblioteca filtrada) sin gastar créditos,
y NO se activa hasta que el coach pulse Activar (editar no lo activa).
"""
from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.services import plan_scaffold


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


def _cliente(**kw) -> SimpleNamespace:
    base = dict(meal_schedule=None, meals_per_day=4, training_days=4,
                session_max_min=60, daily_activity_level="light")
    base.update(kw)
    return SimpleNamespace(**base)


def _energy() -> SimpleNamespace:
    return SimpleNamespace(tdee=2600.0, method="mifflin", adjustment_pct=0.10)


def _macros() -> SimpleNamespace:
    return SimpleNamespace(kcal=2860, protein_g=160, carbs_g=380, fat_g=80)


# ---- nutrición determinista ----

def test_nutricion_base_reparte_exacto_por_tomas():
    """La suma de las tomas ES el total del día, gramo a gramo (criterio del
    Revisor 0): el residuo del redondeo cae en la última comida."""
    nut = plan_scaffold.build_nutrition(_cliente(), _energy(), _macros())
    assert nut["target_kcal"] == 2860
    assert [m["slot"] for m in nut["meals"]] == [1, 2, 3, 4]
    for eje in ("protein_g", "carbs_g", "fat_g"):
        assert sum(m["target"][eje] for m in nut["meals"]) == nut["macros"][eje]
    for m in nut["meals"]:
        t = m["target"]
        # kcal por toma = Atwater exacto de sus macros (como el banco fallback).
        assert t["kcal"] == 4 * t["protein_g"] + 4 * t["carbs_g"] + 9 * t["fat_g"]


def test_nutricion_base_usa_el_horario_declarado():
    sched = [{"slot": 1, "name": "Desayuno", "time": "07:30"},
             {"slot": 2, "name": "Almuerzo", "time": "13:00"},
             {"slot": 3, "name": "Cena", "time": "21:30"}]
    nut = plan_scaffold.build_nutrition(_cliente(meal_schedule=sched), _energy(), _macros())
    assert [(m["name"], m["time"]) for m in nut["meals"]] == [
        ("Desayuno", "07:30"), ("Almuerzo", "13:00"), ("Cena", "21:30")]


# ---- entrenamiento determinista ----

def _biblioteca() -> list[dict]:
    pats = ["horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull",
            "squat", "hip_hinge", "lunge", "knee_flexion", "plantar_flexion",
            "shoulder_abduction", "elbow_extension", "elbow_flexion",
            "core_anti_extension", "core_anti_rotation", "knee_extension",
            "scapular_elevation"]
    lib = []
    for i, p in enumerate(pats):
        for lvl in (1, 3):
            lib.append({"id": len(lib) + 1, "canonical_name": f"{p}-{lvl}",
                        "movement_pattern": p, "muscle_primary": "x",
                        "level_min": lvl, "technique_notes": f"técnica {p}",
                        "biomechanics_notes": None})
    return lib


def test_entrenamiento_base_por_dias_y_duracion():
    tr = plan_scaffold.build_training(_cliente(training_days=4, session_max_min=75),
                                      _biblioteca())
    assert tr["split_name"].startswith("Torso")
    assert len(tr["sessions"]) == 4
    assert all(len(s["exercises"]) >= 4 for s in tr["sessions"])
    assert [w["week"] for w in tr["weekly_progression"]] == [1, 2, 3, 4]
    # Sesiones cortas → menos huecos.
    tr45 = plan_scaffold.build_training(_cliente(training_days=3, session_max_min=40),
                                        _biblioteca())
    assert all(len(s["exercises"]) <= 4 for s in tr45["sessions"])


def test_entrenamiento_base_prefiere_nivel_alto_y_no_repite_en_sesion():
    tr = plan_scaffold.build_training(_cliente(training_days=3, session_max_min=90),
                                      _biblioteca())
    ids_por_sesion = [[e["exercise_id"] for e in s["exercises"]] for s in tr["sessions"]]
    for ids in ids_por_sesion:
        assert len(ids) == len(set(ids))  # sin repetir dentro de la sesión
    # Con nivel 3 disponible en cada patrón, el hueco elige el nivel alto.
    lib = {e["id"]: e for e in _biblioteca()}
    primeros = [ids[0] for ids in ids_por_sesion]
    assert all(lib[i]["level_min"] == 3 for i in primeros)


# ---- endpoint + excepción de activación ----

@needs_db
def test_scaffold_endpoint_borrador_sin_ia_y_activacion_manual(monkeypatch):
    """El scaffold crea un borrador válido SIN tocar la IA; editar (PATCH) no lo
    activa (excepción al auto-activar) y el botón Activar sí."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import SessionLocal
    from app.main import app
    from app.models import Client, User
    from app.security import create_access_token, hash_password, new_portal_token
    from sqlalchemy import select as _select

    monkeypatch.setattr(settings, "emails_enabled", False)
    # Si algo intentara instanciar la IA, el test debe reventar: 0 créditos.
    from app.services.ai import client as ai_client_mod

    def _boom(*a, **k):
        raise AssertionError("el scaffold no puede tocar la IA")
    monkeypatch.setattr(ai_client_mod.AIClient, "__init__", _boom)

    with SessionLocal() as db:
        if not db.scalar(_select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
        c = Client(full_name="Avanzado Scaffold", email=f"sc-{uuid.uuid4().hex[:8]}@x.com",
                   portal_token="p", status="active", package_tier="full",
                   level="advanced", sex="male", birth_date=date(1990, 3, 2),
                   height_cm=180, start_weight_kg=85, goal_type="fat_loss",
                   training_days=3, session_max_min=60, training_place="gym",
                   diet_mode="flexible_7", meals_per_day=4)
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id
    auth = {"Authorization": f"Bearer {create_access_token('coach1')}"}

    with TestClient(app) as http:
        r = http.post(f"/api/clients/{cid}/scaffold-plan", headers=auth)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "draft" and d["review"] is None
        assert any(f.startswith("base sin IA") for f in d["guardrail_flags"])
        nut, tr = d["nutrition"], d["training"]
        assert nut["meals"] and (nut.get("meal_bank") or {}).get("slots")
        assert nut["gen_inputs"]["level"] == "advanced"
        assert tr["sessions"] and all(s["exercises"] for s in tr["sessions"])

        # Editar el borrador base NO lo activa…
        r2 = http.patch(f"/api/plans/{d['id']}", headers=auth,
                        json={"training_json": tr,
                              "base_rev": nut.get("rev") or 0})
        assert r2.status_code == 200 and r2.json()["status"] == "draft"
        # …y el botón Activar sí.
        r3 = http.post(f"/api/plans/{d['id']}/publish", headers=auth)
        assert r3.status_code == 200

    # Limpieza: el conftest borra los @x.com al final de la suite.


@needs_db
def test_alta_manual_guarda_el_nivel(monkeypatch):
    """La ventana del alta elige el nivel: el backend lo persiste."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.db import SessionLocal
    from app.main import app
    from app.models import User
    from app.security import create_access_token, hash_password
    from sqlalchemy import select as _select

    monkeypatch.setattr(settings, "emails_enabled", False)
    with SessionLocal() as db:
        if not db.scalar(_select(User).where(User.username == "coach1")):
            db.add(User(username="coach1", password_hash=hash_password("test")))
            db.commit()
    auth = {"Authorization": f"Bearer {create_access_token('coach1')}"}

    with TestClient(app) as http:
        r = http.post("/api/clients", headers=auth, json={
            "full_name": "Nivel Alta", "email": f"na-{uuid.uuid4().hex[:8]}@x.com",
            "level": "advanced"})
        assert r.status_code == 201
        assert r.json()["client"]["level"] == "advanced"
