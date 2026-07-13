"""Coherencia numérica de la nutrición: target_kcal ≡ macros (4/4/9) ≡ suma de
los objetivos por comida. Es la invariante que evita "aquí pone X kcal y allí
otro número" tanto al generar con IA como al editar/adaptar."""
from app.services.nutrition_scale import kcal_of, reconcile_nutrition


def _assert_coherent(nut: dict, tol: int = 0) -> None:
    m = nut["macros"]
    p, c, f = m["protein_g"], m["carbs_g"], m["fat_g"]
    # 1) target_kcal ≡ suma de macros (exacto)
    assert abs(nut["target_kcal"] - kcal_of(p, c, f)) <= tol
    meals = [x for x in nut.get("meals", []) if x.get("target")]
    if not meals:
        return
    # 2) suma de comidas ≡ totales, eje por eje (exacto)
    for axis, total in (("protein_g", p), ("carbs_g", c), ("fat_g", f),
                        ("kcal", nut["target_kcal"])):
        assert sum(mm["target"][axis] for mm in meals) == total, axis
    # 3) cada comida cuadra sola: su kcal == kcal_of(sus macros)
    for mm in meals:
        t = mm["target"]
        assert t["kcal"] == kcal_of(t["protein_g"], t["carbs_g"], t["fat_g"])


def test_macros_no_cuadran_con_calorias_se_cuadran():
    # target dice 2000 pero los macros suman 2180 → tras reconcile, cuadran
    nut = {
        "target_kcal": 2000,
        "macros": {"protein_g": 180, "carbs_g": 230, "fat_g": 60},  # =2180
        "meals": [],
    }
    reconcile_nutrition(nut, weight_kg=80)
    _assert_coherent(nut)
    # proteína y grasa se conservan; carbohidratos hacen de colchón
    assert nut["macros"]["protein_g"] == 180
    assert nut["macros"]["fat_g"] == 60


def test_suma_de_comidas_se_ajusta_a_los_totales():
    # Las comidas suman distinto que el total declarado → se reparten y cuadran
    nut = {
        "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 56},  # =2000
        "meals": [
            {"slot": 1, "name": "Desayuno", "target": {"kcal": 500, "protein_g": 30, "carbs_g": 60, "fat_g": 15}},
            {"slot": 2, "name": "Comida", "target": {"kcal": 900, "protein_g": 70, "carbs_g": 90, "fat_g": 25}},
            {"slot": 3, "name": "Cena", "target": {"kcal": 700, "protein_g": 60, "carbs_g": 55, "fat_g": 20}},
        ],
    }
    reconcile_nutrition(nut, weight_kg=75)
    _assert_coherent(nut)


def test_idempotente_sobre_datos_ya_coherentes():
    nut = {
        "target_kcal": 2000,
        "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 56},
        "meals": [
            {"slot": 1, "name": "Comida", "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 28}},
            {"slot": 2, "name": "Cena", "target": {"kcal": 1000, "protein_g": 75, "carbs_g": 100, "fat_g": 28}},
        ],
    }
    reconcile_nutrition(nut, weight_kg=75)
    _assert_coherent(nut)
    snapshot = {k: (v.copy() if isinstance(v, dict) else v) for k, v in nut.items()}
    reconcile_nutrition(nut, weight_kg=75)  # segunda pasada
    assert nut["target_kcal"] == snapshot["target_kcal"]
    assert nut["macros"] == snapshot["macros"]


def test_low_carb_extremo_cede_grasa_y_no_declara_kcal_imposibles():
    # proteína + grasa muy altas para un target bajo → carbohidratos no caben:
    # la grasa cede a su suelo (0,6 g/kg) y nunca quedan macros negativos.
    nut = {
        "target_kcal": 1200,
        "macros": {"protein_g": 200, "carbs_g": 300, "fat_g": 90},  # =3010, absurdo
        "meals": [],
    }
    reconcile_nutrition(nut, weight_kg=70)
    _assert_coherent(nut)
    assert nut["macros"]["carbs_g"] >= 0
    assert nut["macros"]["fat_g"] >= 0
    assert nut["macros"]["protein_g"] >= 0


def test_sin_macros_los_deduce_de_las_comidas():
    nut = {
        "target_kcal": 0,
        "meals": [
            {"slot": 1, "name": "Comida", "target": {"kcal": 800, "protein_g": 50, "carbs_g": 80, "fat_g": 25}},
            {"slot": 2, "name": "Cena", "target": {"kcal": 700, "protein_g": 45, "carbs_g": 70, "fat_g": 20}},
        ],
    }
    reconcile_nutrition(nut, weight_kg=70)
    assert nut["macros"]["protein_g"] > 0
    _assert_coherent(nut)


def test_no_rompe_con_plan_vacio():
    nut: dict = {}
    reconcile_nutrition(nut, weight_kg=70)
    assert nut == {} or "macros" not in nut


# ---------------------------------------------------------------------------
# Integración: guardar (PATCH) un plan con nutrición descuadrada lo deja
# coherente en la BD (la red final del editor). Requiere PostgreSQL.
# ---------------------------------------------------------------------------
import uuid  # noqa: E402

import pytest  # noqa: E402


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
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
def auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token('coach1')}"}


def _incoherent_nutrition() -> dict:
    # target dice 2000; macros suman 2180; comidas suman 1700 → todo descuadrado.
    return {
        "tdee_kcal": 2500, "target_kcal": 2000, "rationale": "test",
        "macros": {"protein_g": 180, "carbs_g": 230, "fat_g": 60},
        "meals": [
            {"slot": 1, "name": "Desayuno", "time": "08:00",
             "target": {"kcal": 400, "protein_g": 30, "carbs_g": 40, "fat_g": 12}},
            {"slot": 2, "name": "Comida", "time": "14:00",
             "target": {"kcal": 800, "protein_g": 70, "carbs_g": 80, "fat_g": 22}},
            {"slot": 3, "name": "Cena", "time": "21:00",
             "target": {"kcal": 500, "protein_g": 50, "carbs_g": 50, "fat_g": 16}},
        ],
        "supplements": [], "flexibility_rules": [], "refeed_or_break": None,
    }


def test_patch_plan_reconcilia_la_nutricion(client, auth):
    body = client.post("/api/clients", headers=auth, json={
        "full_name": "Coherencia", "email": f"coh-{uuid.uuid4().hex[:8]}@example.com",
        "package_tier": "full",
    }).json()
    cid = body["client"]["id"]

    plan = client.post(f"/api/clients/{cid}/plans", headers=auth, json={
        "month_index": 1, "nutrition_json": _incoherent_nutrition(),
        "training_json": None, "education_json": None,
        "guardrail_flags": [], "generated_by": "test",
    }).json()

    # Guardar con el editor (PATCH) reconcilia antes de persistir.
    r = client.patch(f"/api/plans/{plan['id']}", headers=auth,
                     json={"nutrition_json": _incoherent_nutrition()})
    assert r.status_code == 200
    nut = r.json()["nutrition_json"]
    m = nut["macros"]
    assert nut["target_kcal"] == kcal_of(m["protein_g"], m["carbs_g"], m["fat_g"])
    meals = [x for x in nut["meals"] if x.get("target")]
    for axis, total in (("protein_g", m["protein_g"]), ("carbs_g", m["carbs_g"]),
                        ("fat_g", m["fat_g"]), ("kcal", nut["target_kcal"])):
        assert sum(mm["target"][axis] for mm in meals) == total, axis
