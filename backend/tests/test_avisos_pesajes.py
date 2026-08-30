"""El punto ciego de "día registrado": quien registra a diario pero no se pesa.

Contar las series de entreno y las comidas elegidas como registro es DELIBERADO
y correcto (un cliente que entrena a diario no puede salir "en riesgo"), pero
dejó un hueco: quien elige su comida cada día cuenta como registrado, va verde
en todas las pantallas y no dispara ningún aviso… y al cerrar la quincena el
motor determinista se encuentra con 0-1 pesajes, responde `dato_insuficiente` y
no hay con qué ajustar el plan. Catorce días perdidos que el coach descubría
cuando ya no tenían arreglo.
"""

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


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest.fixture()
def cliente_en_curso():
    """Cliente con plan publicado y período ABIERTO por el día 10 de 14."""
    from app.db import SessionLocal
    from app.models import Client, DailyLog, Period, Plan
    from app.security import new_portal_token

    db = SessionLocal()
    hoy = date.today()
    uid = uuid.uuid4().hex[:8]
    c = Client(full_name="Registra sin pesarse", email=f"pesa-{uid}@test.local",
               portal_token="tmp", status="active")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                published_at=None, nutrition_json={}, training_json={})
    db.add(plan)
    db.flush()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=9), ends_on=hoy + timedelta(days=4),
               status="open")
    db.add(p)
    db.flush()
    yield db, c, p, hoy
    db.query(DailyLog).filter_by(period_id=p.id).delete()
    db.flush()
    db.delete(p)
    db.flush()
    db.delete(plan)
    db.flush()
    db.delete(c)
    db.commit()
    db.close()


def _kinds(db, client, hoy):
    from app.routers.alerts import client_alerts

    return [a["kind"] for a in client_alerts(db, client, hoy)]


def test_quien_registra_a_diario_pero_no_se_pesa_se_avisa_a_tiempo(cliente_en_curso):
    from app.models import DailyLog

    db, c, p, hoy = cliente_en_curso
    # Registra TODOS los días… eligiendo su comida, sin pesarse nunca.
    for i in range(10):
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=i),
                        chosen_options_json={"1": "A"}))
    db.flush()

    kinds = _kinds(db, c, hoy)
    # No está "sin registros" —registra— pero SÍ se avisa de que faltan pesos.
    assert "no_logs" not in kinds
    assert "sin_pesajes" in kinds, kinds


def test_el_aviso_se_apaga_solo_en_cuanto_se_pesa(cliente_en_curso):
    from app.models import DailyLog

    db, c, p, hoy = cliente_en_curso
    for i in range(10):
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=i),
                        chosen_options_json={"1": "A"},
                        weight_kg=(80.0 - i if i < 2 else None)))
    db.flush()
    assert "sin_pesajes" not in _kinds(db, c, hoy)


def test_no_se_avisa_al_principio_del_periodo(cliente_en_curso):
    """Al día 3 aún no toca: nadie se pesa el primer día y el aviso sería ruido."""
    from app.models import DailyLog, Period

    db, c, p, hoy = cliente_en_curso
    p.starts_on = hoy - timedelta(days=2)   # día 3 de 14
    p.ends_on = hoy + timedelta(days=11)
    db.flush()
    for i in range(3):
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=i),
                        chosen_options_json={"1": "A"}))
    db.flush()
    assert "sin_pesajes" not in _kinds(db, c, hoy)
    assert isinstance(p, Period)


def test_quien_no_registra_nada_recibe_el_aviso_de_siempre(cliente_en_curso):
    """Sin registros el aviso correcto es `no_logs`: no se duplica el mensaje."""
    db, c, p, hoy = cliente_en_curso
    kinds = _kinds(db, c, hoy)
    assert "no_logs" in kinds
    assert "sin_pesajes" not in kinds
