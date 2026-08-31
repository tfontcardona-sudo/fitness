"""Optimización: lo que el panel y el portal pedían de más.

Cada test de aquí falla con el código anterior: no comprueba que "va rápido"
(eso no es comprobable), sino la CAUSA concreta — cuántas consultas se hacen y
qué viaja por la red. Son las mismas cifras que hacían lento el panel de un
cliente con un año de historial.

Requiere PostgreSQL.
"""
import os
import uuid
import warnings
from contextlib import contextmanager
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


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@contextmanager
def consultas_que_tocan(tabla: str):
    """Captura las sentencias SQL que mencionan `tabla` mientras dure el bloque."""
    from sqlalchemy import event

    from app.db import engine

    vistas: list[str] = []

    def _antes(conn, cursor, statement, params, context, executemany):  # noqa: ANN001
        if tabla.lower() in statement.lower():
            vistas.append(statement)

    event.listen(engine, "before_cursor_execute", _antes)
    try:
        yield vistas
    finally:
        event.remove(engine, "before_cursor_execute", _antes)


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


# --------------------------------------------------- cliente con historial ----

@pytest.fixture()
def cliente_con_historial():
    """Cliente con 3 revisiones cerradas, cada una con registros y series.

    Es el caso que hacía cuadrático el historial: cada resumen compara con las
    revisiones anteriores."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Client, DailyLog, Exercise, Period, Plan, WorkoutLog

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    ex_ids = list(db.scalars(select(Exercise.id).limit(3)))
    c = Client(full_name="Con historial", email=f"opt-{uid}@test.local",
               portal_token=f"tok-{uid}", status="active", start_weight_kg=80.0)
    db.add(c)
    db.flush()
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json={"target_kcal": 2200,
                                "macros": {"protein_g": 160, "carbs_g": 220, "fat_g": 70},
                                "meals": [{"slot": "desayuno"}, {"slot": "comida"}],
                                "meal_bank": {"mode": "flexible", "slots": [{"x": "y" * 400}]}},
                training_json={"split_name": "Full body",
                               "sessions": [{"day": "lunes", "exercises":
                                             [{"exercise_id": e, "sets": 3,
                                               "rep_range": "8-10"} for e in ex_ids]},
                                            {"day": "miércoles", "exercises":
                                             [{"exercise_id": e, "sets": 3,
                                               "rep_range": "8-10"} for e in ex_ids]},
                                            {"day": "viernes", "exercises":
                                             [{"exercise_id": e, "sets": 3,
                                               "rep_range": "8-10"} for e in ex_ids]}]})
    db.add(plan)
    db.flush()
    hoy = date.today()
    periodos = []
    for i in range(3):
        p = Period(client_id=c.id, plan_id=plan.id, period_index=i + 1,
                   starts_on=hoy - timedelta(days=60 - i * 14),
                   ends_on=hoy - timedelta(days=47 - i * 14),
                   status="closed", closing_weight_kg=80.0 - i)
        db.add(p)
        db.flush()
        for d in range(3):
            dl = DailyLog(period_id=p.id, log_date=p.starts_on + timedelta(days=d),
                          weight_kg=80.0 - i - d * 0.1)
            db.add(dl)
            db.flush()
            for eid in ex_ids:
                db.add(WorkoutLog(daily_log_id=dl.id, exercise_id=eid,
                                  set_number=1, weight_kg=50.0 + i * 2.5, reps=10))
        periodos.append(p)
    db.commit()
    yield db, c, plan, periodos
    db.close()


# ------------------------------------------------------------- biblioteca ----

def test_la_biblioteca_no_arrastra_las_notas_que_nadie_pinta(http):
    """36 KB de los ~141 KB de la lista eran dos notas que ninguna pantalla del
    panel enseña, y la lista viaja dos veces por visita."""
    r = http.get("/api/exercises?include_archived=true", headers=_auth())
    assert r.status_code == 200, r.text
    filas = r.json()
    assert filas, "la biblioteca sembrada no puede estar vacía"
    assert "technique_notes" not in filas[0]
    assert "biomechanics_notes" not in filas[0]
    # …pero el nombre y el vídeo (lo que SÍ se pinta) siguen estando.
    assert "canonical_name" in filas[0] and "video_url" in filas[0]
    # La ficha individual las conserva: el dato no se ha perdido, solo no viaja
    # en la lista.
    uno = http.get(f"/api/exercises/{filas[0]['id']}", headers=_auth()).json()
    assert "technique_notes" in uno


# ------------------------------------------------------------------ planes ----

def test_el_resumen_de_planes_no_arrastra_el_banco_de_comidas(http, cliente_con_historial):
    """El panel repide la lista de versiones tras CADA acción para pintar cuatro
    cifras por versión: el banco de comidas no puede viajar en ella."""
    db, c, plan, _ = cliente_con_historial
    r = http.get(f"/api/clients/{c.id}/plans/summary", headers=_auth())
    assert r.status_code == 200, r.text
    fila = r.json()[0]
    assert fila["id"] == plan.id
    assert fila["target_kcal"] == 2200
    assert fila["protein_g"] == 160
    assert fila["meals_count"] == 2
    assert fila["split_name"] == "Full body"
    assert fila["sessions_count"] == 3
    assert fila["has_nutrition"] and fila["has_training"]
    # Nada del contenido pesado
    assert "nutrition_json" not in fila and "training_json" not in fila
    assert "meal_bank" not in str(fila)


def test_el_plan_que_se_edita_se_pide_entero(http, cliente_con_historial):
    """El resumen no sustituye al plan: la versión que el coach abre y edita
    sigue llegando completa por su propio endpoint."""
    db, c, plan, _ = cliente_con_historial
    r = http.get(f"/api/plans/{plan.id}", headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json()["nutrition_json"]["meal_bank"]["mode"] == "flexible"
    assert http.get("/api/plans/999999999", headers=_auth()).status_code == 404


# ---------------------------------------------------------------- períodos ----

def test_los_periodos_no_hacen_una_consulta_de_feedback_por_revision(
        http, cliente_con_historial):
    db, c, _, periodos = cliente_con_historial
    with consultas_que_tocan("feedback_docs") as vistas:
        r = http.get(f"/api/clients/{c.id}/periods", headers=_auth())
    assert r.status_code == 200, r.text
    assert len(r.json()) == len(periodos)
    assert len(vistas) <= 1, f"{len(vistas)} consultas para {len(periodos)} revisiones"


# ---------------------------------------------------------------- historial ----

def test_el_historial_lee_las_series_una_sola_vez(cliente_con_historial):
    """Cada resumen compara con las revisiones anteriores: sin caché compartida,
    calcular el historial releía las series una vez por revisión (cuadrático)."""
    from app.db import SessionLocal
    from app.routers.clients import client_history

    db, c, _, periodos = cliente_con_historial
    db2 = SessionLocal()
    try:
        with consultas_que_tocan("workout_logs") as vistas:
            h = client_history(c.id, db2)
    finally:
        db2.close()
    assert len(h["periods"]) == len(periodos)
    assert len(vistas) == 1, f"{len(vistas)} barridos de series para {len(periodos)} revisiones"


def test_el_historial_no_descarga_los_planes_enteros(cliente_con_historial):
    """De cada plan se imprimen cuatro escalares; traer la fila entera arrastraba
    los cuatro JSONB de todas las versiones."""
    from app.db import SessionLocal
    from app.routers.clients import client_history

    db, c, plan, _ = cliente_con_historial
    db2 = SessionLocal()
    try:
        with consultas_que_tocan("plans") as vistas:
            h = client_history(c.id, db2)
    finally:
        db2.close()
    assert h["plans"] == [{"id": plan.id, "month_index": 1, "version": 1,
                           "status": "published"}]
    del_plan = [s for s in vistas if "nutrition_json" in s.lower()]
    assert not del_plan, f"el historial sigue pidiendo el contenido del plan: {del_plan}"


def test_el_historial_sigue_dando_las_mismas_cifras(cliente_con_historial):
    """La caché compartida no puede cambiar el resultado: mismas cifras que
    calculando cada revisión por separado."""
    from app.db import SessionLocal
    from app.services.feedback_service import (
        compute_period_summary,
        sets_por_periodo_de_cliente,
    )

    db, c, _, periodos = cliente_con_historial
    db2 = SessionLocal()
    try:
        cache = sets_por_periodo_de_cliente(db2, c.id)
        for p in periodos:
            con = compute_period_summary(db2, p.id, sets_por_periodo=cache)
            sin = compute_period_summary(db2, p.id)
            assert con["strength"] == sin["strength"]
            assert con["weight"] == sin["weight"]
    finally:
        db2.close()


# ------------------------------------------------------- biblioteca de planes ----

def test_elegir_base_no_lee_el_contenido_de_los_planes_descartados(cliente_con_historial):
    """"Copiar de otro cliente" pinta UNA línea por cliente: no puede leer el
    contenido de todos los planes vivos de todos para tirarlos después."""
    from app.db import SessionLocal
    from app.services.plan_library import pool_de_planes

    db, c, plan, _ = cliente_con_historial
    db2 = SessionLocal()
    try:
        with consultas_que_tocan("plans") as vistas:
            pool = pool_de_planes(db2)
    finally:
        db2.close()
    mio = [p for p in pool if p["client_id"] == c.id]
    assert len(mio) == 1 and mio[0]["plan_id"] == plan.id
    assert mio[0]["summary"], "el resumen sigue saliendo de nutrition/training"
    # El BARRIDO (el que cruza con clientes para sacar el nombre) recorre TODOS
    # los planes vivos del sistema: no puede traerse su contenido. El contenido
    # se pide aparte y solo de los elegidos.
    sweep = [s for s in vistas
             if "nutrition_json" in s.lower() and "full_name" in s.lower()]
    assert not sweep, "el barrido de todos los planes sigue trayendo su contenido"
    contenido = [s for s in vistas if "nutrition_json" in s.lower()]
    assert len(contenido) == 1, "el contenido debe pedirse en una sola consulta acotada"


# ------------------------------------------------------------------ portal ----

def test_el_entreno_del_portal_consulta_la_biblioteca_una_vez(cliente_con_historial):
    """Una consulta por SESIÓN: una rutina de 5 días eran 5 viajes a la tabla de
    ejercicios para resolver los mismos nombres."""
    from app.db import SessionLocal
    from app.services.portal import build_training_sessions

    db, c, plan, _ = cliente_con_historial
    db2 = SessionLocal()
    try:
        cliente = db2.get(type(c), c.id)
        with consultas_que_tocan("from exercises") as vistas:
            sesiones = build_training_sessions(db2, cliente)
    finally:
        db2.close()
    assert len(sesiones) == 3
    assert sesiones[0]["exercises"][0]["name"]
    assert len(vistas) <= 1, f"{len(vistas)} consultas a la biblioteca para 3 sesiones"


# -------------------------------------------------------------------- fotos ----

def test_la_miniatura_de_una_foto_pesa_una_fraccion(http, cliente_con_historial):
    """La tira de fotos del período las pinta a 80×96 px descargando el original
    del móvil del cliente."""
    from io import BytesIO

    from PIL import Image

    from app.db import SessionLocal
    from app.models import ProgressPhoto
    from app.services.storage import abs_path, save_photo

    db, c, _, periodos = cliente_con_historial
    buf = BytesIO()
    Image.new("RGB", (2400, 3200), (120, 90, 60)).save(buf, format="JPEG", quality=92)
    grande = buf.getvalue()
    rel = save_photo(c.id, grande)
    db2 = SessionLocal()
    try:
        foto = ProgressPhoto(client_id=c.id, period_id=periodos[0].id,
                             kind="front", file_path=rel)
        db2.add(foto)
        db2.commit()
        fid = foto.id
    finally:
        db2.close()

    entera = http.get(f"/api/clients/{c.id}/photos/{fid}", headers=_auth())
    mini = http.get(f"/api/clients/{c.id}/photos/{fid}?w=200", headers=_auth())
    assert entera.status_code == 200 and mini.status_code == 200
    assert mini.headers["content-type"] == "image/jpeg"
    assert len(mini.content) < len(entera.content) / 5, (
        f"miniatura {len(mini.content)} B vs original {len(entera.content)} B")
    assert Image.open(BytesIO(mini.content)).size[0] <= 200
    assert abs_path(rel).exists()


# ----------------------------------------------------------------- clientes ----

def test_la_lista_ligera_deja_fuera_las_notas_clinicas(http, cliente_con_historial):
    """Hoy y Clientes repiden la lista cada 3 s y no pintan ni una de las notas."""
    from app.db import SessionLocal
    from app.models import Client

    db, c, _, _ = cliente_con_historial
    db2 = SessionLocal()
    try:
        cli = db2.get(Client, c.id)
        cli.medical_notes = "Nota clínica larga " * 40
        cli.injuries_notes = "Lesión de hombro derecha"
        db2.commit()
    finally:
        db2.close()

    entera = {x["id"]: x for x in http.get("/api/clients", headers=_auth()).json()}[c.id]
    ligera = {x["id"]: x for x in http.get("/api/clients?light=1", headers=_auth()).json()}[c.id]
    assert entera["medical_notes"] and entera["injuries_notes"]
    assert ligera["medical_notes"] is None and ligera["injuries_notes"] is None
    # Lo que las dos pantallas SÍ pintan sigue estando.
    assert ligera["full_name"] == entera["full_name"]
    assert ligera["status"] == entera["status"]
    assert ligera["has_published_plan"] == entera["has_published_plan"]
    # Y la FICHA nunca se recorta.
    ficha = http.get(f"/api/clients/{c.id}", headers=_auth()).json()
    assert ficha["medical_notes"] and ficha["injuries_notes"]
