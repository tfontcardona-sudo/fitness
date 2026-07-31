"""Regresiones de la auditoría integral (conectividad + ediciones + matemática).

Cada test fija un bug REAL encontrado por el banco de 100 perfiles sintéticos o
por la auditoría de código: si vuelve, esto lo caza.
"""
import os
import uuid
import warnings
from datetime import date, timedelta

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


DB = _db_available()


# ----------------------------------------------------- motor quincenal (§8) ---

def _points(weight: float, rate_pct_week: float, days: int = 14):
    today = date(2026, 7, 28)
    return [
        (today - timedelta(days=days - 1 - d),
         round(weight * (1 + rate_pct_week / 100 * (d / 7.0)), 2))
        for d in range(days)
    ]


def test_kcal_delta_en_puntos_porcentuales():
    """El bug de unidades: el motor emitía la FRACCIÓN (0.06) y adapt dividía
    entre 100 → el ajuste determinista era ±0,06% (un no-op). El contrato queda
    fijado en PUNTOS porcentuales."""
    from app.services.biweekly_engine import KCAL_STEP_PCT, CheckinInputs, decide_biweekly

    assert KCAL_STEP_PCT == 6.0  # puntos %, no fracción

    d = decide_biweekly(CheckinInputs(
        goal_type="fat_loss", weight_kg=84, target_rate_pct_week=(-0.8, -0.4),
        weight_points=_points(84, 0.0), prev_window_mean_kg=84,
        adherence_diet_ratio=0.95,
    ))
    assert d.action == "adjust_kcal"
    assert d.kcal_delta_pct == -6.0
    # Aplicado como en adapt_plan (d_pct/100): −6% de verdad, no −0,06%.
    import math
    assert math.floor(2000 * (1 + d.kcal_delta_pct / 100) + 0.5) == 1880


def test_deriva_no_deseada_en_mantenimiento():
    """Mantenimiento/recomposición con el peso derivando >0,45%/sem: antes caía
    en 'sin_cambio_neto' para siempre."""
    from app.services.biweekly_engine import CheckinInputs, decide_biweekly

    d = decide_biweekly(CheckinInputs(
        goal_type="maintenance", weight_kg=80, target_rate_pct_week=(0.0, 0.0),
        weight_points=_points(80, +0.8), prev_window_mean_kg=80,
        adherence_diet_ratio=0.95,
    ))
    assert d.action == "adjust_kcal" and d.kcal_delta_pct == -6.0
    assert d.rule == "deriva_no_deseada"


def test_adherencia_cero_no_es_perfecta():
    """Todo 'no' (ratio 0.0) se leía como 1.0 por el `or 1.0` y el motor
    ajustaba kcal en vez de bloquear."""
    from app.services.biweekly_period import _adherence_ratio
    from app.services.metrics import AdherenceSummary

    class P:  # período sin 0-10 del cierre
        adherence_diet_0_10 = None

    todo_no = AdherenceSummary(diet_yes=0, diet_partial=0, diet_no=10,
                               diet_adherence_ratio=0.0)
    assert _adherence_ratio(P(), todo_no) == 0.0
    sin_datos = AdherenceSummary()
    assert _adherence_ratio(P(), sin_datos) == 1.0


def test_weight_trend_descarta_outliers():
    """Un typo plausible (48,0 en una serie 84→83) volteaba el ritmo a +3,9
    kg/sem y el motor decidía sobre él."""
    from app.services.metrics import weight_trend

    today = date(2026, 7, 28)
    pts = [(today - timedelta(days=13 - d), 84.0 - 0.08 * d) for d in range(14)]
    pts[6] = (pts[6][0], 48.0)  # typo
    wt = weight_trend(pts)
    assert wt.weekly_rate_kg is not None and wt.weekly_rate_kg < 0  # sigue bajando


# ------------------------------------------------------- alérgenos/patrones ---

def test_mani_detecta_cacahuete_y_pan_detecta_pasta():
    """El lookup inverso de sinónimos comparaba contra el término raw (r"\\bmani\\b")
    y nunca coincidía: 'maní' no expandía a cacahuete ni 'pan' a trigo/pasta."""
    from app.services.guardrails import option_allergen

    opt = {"title": "Batido con crema de cacahuete",
           "ingredients": [{"food": "Crema de cacahuete 100%", "grams": 20}]}
    assert option_allergen(opt, ["maní"]) is not None

    opt2 = {"title": "Ensalada de pasta",
            "ingredients": [{"food": "Pasta (en crudo)", "grams": 80}]}
    assert option_allergen(opt2, ["pan"]) is not None


def test_patron_vegano_incluye_pescados_del_vegetariano():
    """'bacalao'/'sardina' estaban bloqueados para vegetarianos pero NO para
    veganos (dos listas a mano). Ahora vegano ⊇ vegetariano."""
    from app.services.portion_solver import filter_foods

    foods = [{"canonical_name": "Bacalao", "aliases": [], "allergens": [], "tags": []},
             {"canonical_name": "Sardinas", "aliases": [], "allergens": [], "tags": []},
             {"canonical_name": "Cordero", "aliases": [], "allergens": [], "tags": []},
             {"canonical_name": "Arroz (en crudo)", "aliases": [], "allergens": [], "tags": []}]
    out = {f["canonical_name"] for f in filter_foods(foods, diet_pattern="vegano")}
    assert out == {"Arroz (en crudo)"}


def test_gimnasio_no_restringe_por_material():
    """La rama gym era una allowlist encubierta: con un set de material no vacío
    excluía casi toda la biblioteca. En gimnasio se asume equipamiento completo."""
    from app.services.guardrails import filter_exercises_for_client

    lib = [{"id": 1, "canonical_name": "Press banca", "level_min": 1,
            "equipment": ["barra", "banco", "rack"], "contraindications": []}]
    out = filter_exercises_for_client(
        lib, client_contraindications=set(), excluded_ids=set(),
        equipment_available={"mancuernas"}, level_max=3, training_place="gym")
    assert len(out) == 1


# -------------------------------------------------------- banco de comidas ----

def _mk_meal(name: str, kcal: float):
    return {"slot": 1, "name": name,
            "target": {"kcal": kcal, "protein_g": kcal * 0.3 / 4,
                        "carbs_g": kcal * 0.45 / 4, "fat_g": kcal * 0.25 / 9}}


def test_fallback_respeta_aversiones_como_el_revisor():
    """El banco de emergencia colaba alimentos ODIADOS 'para llegar a 3' y el
    Revisor 0 vetaba el plan entero. Ahora: mejor 1-2 seguras que 3 con veto."""
    from app.services.guardrails import option_allergen
    from app.services.meal_fallback import build_fallback_options

    opts = build_fallback_options(_mk_meal("Comida", 700), allergies=[],
                                  dislikes=["pescado"])
    assert opts, "sin opciones para un simple 'no me gusta el pescado'"
    for o in opts:
        assert option_allergen(o, ["pescado"]) is None


def test_fallback_multialergico_cubre_todas_las_tomas():
    """gluten+lactosa+frutos secos+huevo+marisco+soja + aversión a pescado:
    antes dejaba tomas VACÍAS (el cliente veía una 'toma libre')."""
    from app.services.guardrails import option_allergen
    from app.services.meal_fallback import build_fallback_options

    allg = ["gluten", "lactosa", "frutos secos", "huevo", "marisco", "soja"]
    for name in ("Desayuno", "Comida", "Merienda", "Cena"):
        opts = build_fallback_options(_mk_meal(name, 600), allergies=allg,
                                      dislikes=["pescado"])
        assert opts, f"toma {name} sin opciones seguras"
        for o in opts:
            for a in allg + ["pescado"]:
                assert option_allergen(o, [a]) is None, (name, o["title"], a)


def test_fallback_atwater_exacto_y_porciones_reales():
    """Las opciones nacían con Atwater interno descuadrado (±7 kcal → veto) y
    con porciones de >700 g de un solo alimento en objetivos altos."""
    from app.services.meal_fallback import build_fallback_options

    from app.services.guardrails import _LIQUID_HINTS, _norm_food

    for kcal in (300, 700, 1100, 1400):
        for name in ("Desayuno", "Comida", "Snack"):
            for o in build_fallback_options(_mk_meal(name, kcal)):
                m = o["macros"]
                assert m["kcal"] == 4 * m["protein_g"] + 4 * m["carbs_g"] + 9 * m["fat_g"]
                for ing in o["ingredients"]:
                    liquido = any(h in _norm_food(ing["food"]) for h in _LIQUID_HINTS)
                    assert ing["grams"] <= (1000 if liquido else 700), (name, kcal, ing)


def test_topes_de_porcion_cereal_seco_y_liquidos():
    """690 g de arroz crudo (~2.450 kcal) pasaba el tope genérico; los líquidos
    no tenían ninguno."""
    from app.services.guardrails import GuardrailReport, _check_portions

    r = GuardrailReport()
    _check_portions(r, 1, {"key": "A", "ingredients": [
        {"food": "Arroz (en crudo)", "grams": 400}]})
    assert any("crudo" in v for v in r.violations)

    r2 = GuardrailReport()
    _check_portions(r2, 1, {"key": "A", "ingredients": [
        {"food": "Leche desnatada", "grams": 1200}]})
    assert any("ml" in v for v in r2.violations)


# ------------------------------------------------------------ metrics ---------

def test_macros_obesidad_no_invierten_el_deficit():
    """Suelos por kg de peso TOTAL inflaban las kcal por ENCIMA del TDEE: un
    plan 'de pérdida de grasa' en superávit sin que nadie lo dijera."""
    from app.services.metrics import energy_targets, macro_targets

    et = energy_targets(sex="female", weight_kg=100, height_cm=165, age=40,
                        goal_type="fat_loss", training_days=4,
                        body_fat_pct=45.0, daily_activity="sedentary")
    mp = macro_targets("female", 100, "fat_loss", et.target_kcal, 4, tdee=et.tdee)
    assert mp.kcal <= et.tdee + 1
    assert mp.notes  # y queda constancia para el coach


def test_edad_fuera_de_rango_avisa():
    from app.services.metrics import energy_targets

    et = energy_targets(sex="male", weight_kg=80, height_cm=180, age=-4,
                        goal_type="fat_loss", training_days=3)
    assert any("Edad" in w or "edad" in w for w in et.warnings)


def test_e1rm_ignora_series_maratonianas():
    from app.services.metrics import exercise_e1rm_progress

    sets = [
        {"exercise_id": 1, "weight_kg": 100, "reps": 5, "daily_log_id": 1},
        {"exercise_id": 1, "weight_kg": 60, "reps": 50, "daily_log_id": 2},  # ruido
    ]
    prog = exercise_e1rm_progress(sets)
    assert prog and prog[0].best_set == (100, 5)


# ------------------------------------------------ adaptación (texto de IA) ----

def test_parse_change_entiende_porcentajes():
    """'bajar los carbohidratos un 10%' se aplicaba como −10 g."""
    from app.services.adapt_plan import _apply, _parse_change

    mode, val = _parse_change("bajar los carbohidratos un 10%")
    assert (mode, val) == ("pct", -10.0)
    assert _apply(200, mode, val) == 180

    mode, val = _parse_change("reducir a 150 g")
    assert (mode, val) == ("abs", 150.0)


# ---------------------------------------------- API: concurrencia y estados ---

pytestmark_db = pytest.mark.skipif(not DB, reason="Requiere PostgreSQL")


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


@pytestmark_db
def test_patch_plan_con_base_rev_rancio_da_409(http):
    from app.db import SessionLocal
    from app.models import Client, Plan
    from app.security import new_portal_token

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    c = Client(full_name=f"Rev {uid}", email=f"rev-{uid}@test.local",
               portal_token="p", status="active")
    db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json={"target_kcal": 2000,
                                 "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}},
                training_json={}, education_json={})
    db.add(plan); db.commit()
    pid, nut = plan.id, dict(plan.nutrition_json)
    db.close()

    auth = _auth()
    r1 = http.patch(f"/api/plans/{pid}", headers=auth,
                    json={"nutrition_json": nut, "base_rev": 0})
    assert r1.status_code == 200, r1.text
    # Una segunda pestaña abierta ANTES del guardado anterior: rev rancio → 409.
    r2 = http.patch(f"/api/plans/{pid}", headers=auth,
                    json={"nutrition_json": nut, "base_rev": 0})
    assert r2.status_code == 409


@pytestmark_db
def test_patch_estado_valida_la_maquina(http):
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    c = Client(full_name=f"Est {uid}", email=f"est-{uid}@test.local",
               portal_token="p", status="inactive")
    db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
    db.commit(); cid = c.id; db.close()

    auth = _auth()
    # inactive → active: la reactivación manual que faltaba.
    r = http.patch(f"/api/clients/{cid}", headers=auth, json={"status": "active"})
    assert r.status_code == 200 and r.json()["status"] == "active"
    # active → onboarding: transición ilegal → 409.
    r2 = http.patch(f"/api/clients/{cid}", headers=auth, json={"status": "onboarding"})
    assert r2.status_code == 409


@pytestmark_db
def test_alerta_adaptar_sobrevive_al_envio_del_feedback(http):
    """La alerta 'sin adaptar' moría al abrirse el período siguiente: el ciclo 2
    corría con las kcal viejas sin que nadie lo persiguiera."""
    from app.db import SessionLocal
    from app.models import Client, Period, Plan
    from app.routers.alerts import client_alerts
    from app.security import new_portal_token

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    c = Client(full_name=f"Adap {uid}", email=f"adap-{uid}@test.local",
               portal_token="p", status="active", goal_type="fat_loss")
    db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                goal_type="fat_loss",
                nutrition_json={"target_kcal": 2000,
                                 "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}},
                training_json={}, education_json={})
    db.add(plan); db.flush()
    today = date.today()
    # Revisión 1 ANALIZADA (feedback enviado) y período 2 ya ABIERTO.
    db.add(Period(client_id=c.id, plan_id=plan.id, period_index=1,
                  starts_on=today - timedelta(days=30), ends_on=today - timedelta(days=16),
                  status="analyzed"))
    db.add(Period(client_id=c.id, plan_id=plan.id, period_index=2,
                  starts_on=today - timedelta(days=2), ends_on=today + timedelta(days=12),
                  status="open"))
    db.commit()

    alerts = client_alerts(db, c)
    kinds = {a["kind"] for a in alerts}
    assert "adapt_plan" in kinds, kinds
    db.close()
