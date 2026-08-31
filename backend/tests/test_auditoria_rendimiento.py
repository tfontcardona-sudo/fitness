"""Regresiones de la tanda 7 (optimización).

Fijan lo que se arregló MIDIENDO: consultas por petición y campos que ya no
viajan. Los topes son holgados a propósito —no queremos un test frágil— pero
cazan la vuelta de un N+1 o de un JSON gordo.
"""
import os
import uuid
import warnings
from datetime import date, datetime, timedelta, timezone

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


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


class _Contador:
    """Cuenta las consultas SQL que emite un bloque."""

    def __enter__(self):
        from sqlalchemy import event

        from app.db import engine

        self.n = 0
        self._engine = engine

        def _tick(conn, cursor, statement, params, context, executemany):
            self.n += 1

        self._tick = _tick
        event.listen(engine, "before_cursor_execute", _tick)
        return self

    def __exit__(self, *exc):
        from sqlalchemy import event

        event.remove(self._engine, "before_cursor_execute", self._tick)
        return False


def _cliente_con_revisiones(n_revisiones: int = 6):
    """Cliente con plan, varias revisiones cerradas y sus feedbacks."""
    from app.db import SessionLocal
    from app.models import Client, DailyLog, FeedbackDoc, Period, Plan
    from app.security import new_portal_token

    uid = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        c = Client(full_name=f"Perf {uid}", email=f"perf-{uid}@test.local",
                   portal_token="p", status="active", package_tier="full",
                   goal_type="fat_loss", start_weight_kg=84, current_weight_kg=82,
                   height_cm=178, sex="male", birth_date=date(1990, 1, 1),
                   training_days=3, training_place="gym", diet_mode="flexible_7")
        db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
        plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                    goal_type="fat_loss",
                    nutrition_json={"target_kcal": 2200,
                                    "macros": {"protein_g": 165, "carbs_g": 220, "fat_g": 70},
                                    "meals": [{"slot": 1, "name": "Toma 1", "time": "08:00"}],
                                    "meal_bank": {"mode": "flexible_7", "slots": []}},
                    training_json={"split_name": "Full body", "sessions": [
                        {"day": "lunes", "name": "A", "exercises": []},
                        {"day": "miércoles", "name": "B", "exercises": []},
                    ]},
                    education_json={"pills": []})
        db.add(plan); db.flush()
        hoy = date.today()
        for i in range(1, n_revisiones + 1):
            ini = hoy - timedelta(days=14 * (n_revisiones + 1 - i))
            per = Period(client_id=c.id, plan_id=plan.id, period_index=i,
                         starts_on=ini, ends_on=ini + timedelta(days=13),
                         status="analyzed", closing_weight_kg=84 - i * 0.5)
            db.add(per); db.flush()
            db.add(FeedbackDoc(period_id=per.id, kind="quincenal",
                               content_json={"natural_analysis": "x"},
                               sent_at=datetime.now(timezone.utc)))
            db.add(DailyLog(period_id=per.id, log_date=ini + timedelta(days=1),
                            weight_kg=83.5))
        db.commit()
        return c.id, c.portal_token


def test_la_lista_de_clientes_no_lleva_el_historial_clinico(http):
    """Se pide cada 3 s desde DOS pantallas y ninguna pinta las notas."""
    _cliente_con_revisiones(1)
    r = http.get("/api/clients", headers=_auth())
    assert r.status_code == 200
    fila = r.json()[0]
    for campo in ("injuries_notes", "medical_notes", "medication_notes",
                  "lifestyle_notes", "sport_history", "food_allergies"):
        assert campo not in fila, f"{campo} no puede viajar en el LISTADO"
    # Y lo que las pantallas SÍ usan sigue estando.
    for campo in ("id", "full_name", "status", "package_tier", "payment_status"):
        assert campo in fila


def test_la_biblioteca_de_ejercicios_no_lleva_las_notas_tecnicas(http):
    r = http.get("/api/exercises", headers=_auth())
    assert r.status_code == 200
    filas = r.json()
    if not filas:
        pytest.skip("sin ejercicios sembrados")
    for campo in ("technique_notes", "biomechanics_notes", "contraindications"):
        assert campo not in filas[0], f"{campo} no lo pinta ninguna pantalla"
    for campo in ("id", "canonical_name", "muscle_primary", "movement_pattern", "video_url"):
        assert campo in filas[0]
    # El DETALLE sí las devuelve enteras (es donde se leen).
    d = http.get(f"/api/exercises/{filas[0]['id']}", headers=_auth())
    assert d.status_code == 200 and "technique_notes" in d.json()


def test_los_planes_viejos_no_viajan_enteros(http):
    """El panel solo pinta el vigente (y el borrador retenido): las versiones
    históricas viajaban con su banco de recetas y su educativo en CADA recarga."""
    from app.db import SessionLocal
    from app.models import Plan

    cid, _ = _cliente_con_revisiones(1)
    with SessionLocal() as db:
        vigente = db.scalar(
            __import__("sqlalchemy").select(Plan).where(Plan.client_id == cid))
        vigente_id = vigente.id
        # Una versión ANTIGUA con banco gordo
        viejo = Plan(client_id=cid, month_index=1, version=0, status="superseded",
                     nutrition_json={"target_kcal": 2000, "macros": {},
                                     "meal_bank": {"mode": "flexible_7",
                                                   "slots": [{"slot": 1, "options": [
                                                       {"title": "x" * 200}]}]}},
                     training_json={"split_name": "viejo", "sessions": []},
                     education_json={"pills": [{"topic": "t", "for_client": "y" * 300}]})
        db.add(viejo); db.commit()
        viejo_id = viejo.id

    r = http.get(f"/api/clients/{cid}/plans", headers=_auth())
    assert r.status_code == 200
    por_id = {p["id"]: p for p in r.json()}
    assert por_id[vigente_id]["nutrition_json"].get("meal_bank") is not None, \
        "el plan vigente tiene que venir ENTERO (el panel lo pinta)"
    assert por_id[viejo_id]["education_json"] is None, "una versión vieja no se pinta"
    assert not (por_id[viejo_id]["nutrition_json"] or {}).get("meal_bank"), \
        "el banco de una versión vieja no puede viajar"
    # `todo=true` sigue devolviéndolo entero para quien lo necesite.
    r2 = http.get(f"/api/clients/{cid}/plans?todo=true", headers=_auth())
    assert (r2.json()[-1]["education_json"] or {}).get("pills") is not None


def test_las_revisiones_no_hacen_una_consulta_por_feedback(http):
    """Era 1 + N (una por revisión) solo para saber si ya tienen informe."""
    cid, _ = _cliente_con_revisiones(6)
    http.get(f"/api/clients/{cid}/periods", headers=_auth())  # calentar
    with _Contador() as c:
        r = http.get(f"/api/clients/{cid}/periods", headers=_auth())
    assert r.status_code == 200 and len(r.json()) == 6
    assert all(p["feedback_id"] for p in r.json()), "cada revisión tiene su informe"
    assert c.n <= 6, f"con 6 revisiones no puede hacer {c.n} consultas"


def test_el_historial_no_crece_de_forma_cuadratica(http):
    """Cada revisión releía las series de TODAS las anteriores."""
    cid, _ = _cliente_con_revisiones(6)
    http.get(f"/api/clients/{cid}/history", headers=_auth())
    with _Contador() as c6:
        http.get(f"/api/clients/{cid}/history", headers=_auth())
    cid2, _ = _cliente_con_revisiones(12)
    http.get(f"/api/clients/{cid2}/history", headers=_auth())
    with _Contador() as c12:
        r = http.get(f"/api/clients/{cid2}/history", headers=_auth())
    assert r.status_code == 200
    # Doblar las revisiones no puede más que doblar las consultas (antes,
    # además, cada una releía todo el histórico de series anterior).
    assert c12.n <= c6.n * 2 + 2, f"{c6.n} → {c12.n} con el doble de revisiones"


def test_el_portal_resuelve_la_biblioteca_una_vez(http):
    """La pantalla de Entreno consultaba los ejercicios una vez POR SESIÓN."""
    _cid, token = _cliente_con_revisiones(1)
    http.get(f"/api/p/{token}/training")
    with _Contador() as c:
        r = http.get(f"/api/p/{token}/training")
    assert r.status_code == 200
    assert c.n <= 10, f"{c.n} consultas para pintar el entreno del cliente"


def test_los_tokens_de_producto_se_memorizan_sin_cambiar_el_resultado():
    """El barrido de avisos normalizaba el catálogo entero una vez por cliente:
    era el 100 % del tiempo de /api/alerts. Memorizar no puede cambiar nada."""
    from app.services.product_match import product_covers

    assert product_covers("Creatina monohidrato", "Creatine Monohydrate 500 g")
    assert product_covers("Proteína de suero", "Whey Protein Isolate")
    assert not product_covers("Creatina", "Aceite de pescado Omega 3")
    # Repetido (ahora sale de la caché): mismo veredicto.
    assert product_covers("Creatina monohidrato", "Creatine Monohydrate 500 g")
    assert not product_covers("Creatina", "Aceite de pescado Omega 3")
