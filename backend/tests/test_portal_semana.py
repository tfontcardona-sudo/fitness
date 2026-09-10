""""TU SEMANA" DEL PORTAL: lo que el cliente hizo, y los consejos que salen de
sus propios datos.

El portal enseñaba lo que toca HOY. Faltaba lo de atrás —días registrados,
series, cómo va el peso, la última sesión con sus kilos— que es lo que hace que
un cliente vuelva en vez de cansarse de una lista de deberes.

Lo que se blinda:
- es DETERMINISTA (ni una llamada a la IA) y cuenta con las MISMAS reglas que
  el panel del coach, para que las dos pantallas no se contradigan;
- los consejos se disparan por datos REALES, no son frases de ánimo al azar;
- sin datos NO se rellena con humo.
"""
import os
import uuid
from datetime import date, timedelta

import pytest


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
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _cliente_con_periodo(db, *, goal="fat_loss"):
    from app.models import Client, Period, Plan
    from app.security import new_portal_token

    hoy = date.today()
    c = Client(full_name="Semana", email=f"sem-{uuid.uuid4().hex[:8]}@test.local",
               portal_token="tmp", status="active", package_tier="full",
               goal_type=goal)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    # Un período SIEMPRE cuelga de un plan (plan_id es NOT NULL).
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                generated_by="ai")
    db.add(plan)
    db.flush()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=10),
               ends_on=hoy + timedelta(days=4), status="open")
    db.add(p)
    db.commit()
    return c, p


def test_sin_datos_no_se_inventa_una_semana(db):
    from app.services.portal_semana import resumen

    c, _ = _cliente_con_periodo(db)
    r = resumen(db, c, date.today())
    assert r["dias_registrados"] == 0
    assert r["series"] == 0
    assert r["ultima_sesion"] is None
    assert r["peso_delta_kg"] is None
    # …pero sí se le dice lo único accionable: que se pese.
    def _sin_tildes(t: str) -> str:
        import unicodedata

        return (unicodedata.normalize("NFKD", t)
                .encode("ascii", "ignore").decode("ascii").lower())

    assert any("pesa" in _sin_tildes(x["texto"]) for x in r["consejos"])


def test_cuenta_los_dias_las_series_y_recuerda_la_ultima_sesion(db):
    from app.models import DailyLog, Exercise, WorkoutLog
    from app.services.portal_semana import resumen

    c, p = _cliente_con_periodo(db)
    hoy = date.today()
    # Completo (listas vacías, no NULL) y se retira al final: la base de pruebas
    # es compartida y un ejercicio a medias ensucia la biblioteca de todos.
    ej = Exercise(canonical_name=f"Press banca {uuid.uuid4().hex[:6]}",
                  muscle_primary="pecho", movement_pattern="empuje_horizontal",
                  equipment=["barra"], level_min=2, aliases=[],
                  muscle_secondary=[], contraindications=[])
    db.add(ej)
    db.flush()

    # Tres días con diario; el más reciente, con series.
    for delta in (4, 2, 1):
        lg = DailyLog(period_id=p.id, log_date=hoy - timedelta(days=delta),
                      weight_kg=80.0 - delta * 0.2)
        db.add(lg)
        db.flush()
        if delta == 1:
            for i, (peso, reps) in enumerate([(60.0, 10), (62.5, 8)], start=1):
                db.add(WorkoutLog(daily_log_id=lg.id, exercise_id=ej.id,
                                  set_number=i, reps=reps, weight_kg=peso))
    db.commit()

    r = resumen(db, c, hoy)
    assert r["dias_registrados"] == 3
    assert r["series"] == 2
    ult = r["ultima_sesion"]
    assert ult is not None
    assert ult["series"] == 2
    # Lo MÁS PESADO del día, con su nombre y sus reps: el recordatorio útil.
    assert ult["top_peso_kg"] == 62.5
    assert ult["top_reps"] == 8
    assert ej.canonical_name in (ult["top_ejercicio"] or "")

    # Limpieza: el ejercicio es del test, no de la biblioteca.
    from sqlalchemy import delete

    db.execute(delete(WorkoutLog).where(WorkoutLog.exercise_id == ej.id))
    db.commit()
    db.execute(delete(Exercise).where(Exercise.id == ej.id))
    db.commit()


def test_el_peso_se_mide_en_la_quincena_no_en_la_semana(db):
    """Con siete días el ruido diario se come la señal y el cliente lee subidas
    que no existen."""
    from app.models import DailyLog
    from app.services.portal_semana import resumen

    c, p = _cliente_con_periodo(db)
    hoy = date.today()
    # Pesajes repartidos por TODA la quincena (uno de ellos fuera de la semana).
    for delta, peso in ((9, 82.0), (5, 81.2), (1, 80.6)):
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=delta),
                        weight_kg=peso))
    db.commit()
    r = resumen(db, c, hoy)
    assert r["peso_delta_kg"] == -1.4     # 80,6 − 82,0, no solo lo de la semana


def test_los_consejos_salen_de_los_datos_y_no_pasan_de_tres(db):
    from app.models import DailyLog
    from app.services.portal_semana import resumen

    c, p = _cliente_con_periodo(db, goal="fat_loss")
    hoy = date.today()
    # Semana completa registrada y bajando de peso: dos motivos de felicitación
    # …y la revisión a la vuelta de la esquina.
    for delta in range(7):
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=delta),
                        weight_kg=82.0 - delta * 0.25, sleep_hours=7))
    db.commit()

    r = resumen(db, c, hoy)
    assert len(r["consejos"]) <= 3, "una lista larga se lee como un muro"
    textos = " ".join(x["texto"] for x in r["consejos"]).lower()
    assert "kg" in textos, "el consejo bueno se sostiene en su cifra"
    assert any(x["tono"] == "bien" for x in r["consejos"])


def test_el_endpoint_del_portal_lo_sirve_sin_login(http, db):
    c, _ = _cliente_con_periodo(db)
    r = http.get(f"/api/p/{c.portal_token}/semana")
    assert r.status_code == 200, r.text
    datos = r.json()
    assert {"dias_registrados", "series", "consejos", "racha"} <= set(datos)


def test_el_logo_de_la_marca_por_fin_se_puede_servir():
    """Se guardaba bajo `brand/`, que Caddy NO sirve: se subía y no se veía en
    ninguna parte. Por eso el logo estaba clavado en el código."""
    import io

    from PIL import Image

    from app.services.storage import media_url, save_brand_logo

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(buf, format="PNG")
    ruta = save_brand_logo(buf.getvalue(), "logo.png", "marca-de-prueba")
    assert ruta.startswith("media/"), "fuera de media/ no hay forma de servirlo"
    assert media_url(ruta) == "/api/media/brand/logo-marca-de-prueba.png"
