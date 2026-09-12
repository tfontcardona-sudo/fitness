"""`last_touch_at` — lo último que pasó con un cliente, para ordenar la
cartera "de menos reciente a más reciente" (petición del dueño).

No es solo `Client.updated_at` (que ya se documentaba como "la ficha, no el
cliente registrando"): es el MÁXIMO entre la ficha, el último plan generado o
adaptado, el último registro diario del cliente y su última petición — lo que
pase MÁS TARDE de las cuatro, sea del coach o del propio cliente. Se computa
en LOTE (tres consultas agrupadas para toda la cartera), no una por cliente:
`GET /clients` se pide cada 3 s desde dos pantallas.
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


def _cliente(db, nombre, marca, **over):
    from app.models import Client

    campos = dict(full_name=f"{nombre} {marca}", email=f"{nombre.lower()}-{marca}@test.local",
                  package_tier="full", billing_period="1m", status="active",
                  portal_token=f"tok-{nombre.lower()}-{marca}", payment_status="paid")
    campos.update(over)
    c = Client(**campos)
    db.add(c)
    db.flush()
    return c


def _borra(db, clientes):
    from sqlalchemy import delete

    from app.models import (ChangeRequest, Client, DailyLog, Period, Plan)

    ids = [c.id for c in clientes]
    per_ids = [p.id for p in db.query(Period).filter(Period.client_id.in_(ids))]
    if per_ids:
        db.execute(delete(DailyLog).where(DailyLog.period_id.in_(per_ids)))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id.in_(ids)))
    db.execute(delete(Period).where(Period.client_id.in_(ids)))
    db.execute(delete(Plan).where(Plan.client_id.in_(ids)))
    db.execute(delete(Client).where(Client.id.in_(ids)))
    db.commit()


def _fila(http, client_id):
    r = http.get("/api/clients", headers=_auth())
    assert r.status_code == 200
    return next(x for x in r.json() if x["id"] == client_id)


def test_sin_plan_ni_registros_last_touch_es_la_ficha(http):
    """Un cliente recién dado de alta, sin plan ni un solo registro: lo único
    que ha pasado es su alta (que ya cuenta como "ficha")."""
    from app.db import SessionLocal

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    c = _cliente(db, "Nuevo", marca)
    db.commit()
    try:
        fila = _fila(http, c.id)
        assert fila["last_touch_at"] is not None
        # Sin nada más reciente que aportar, coincide con `updated_at`.
        assert fila["last_touch_at"] == fila["updated_at"]
    finally:
        _borra(db, [c])
        db.close()


def test_un_registro_diario_reciente_manda_sobre_la_ficha_vieja(http):
    """La ficha no se ha tocado en meses pero el cliente registró AYER: eso es
    lo último que pasó, y `last_touch_at` tiene que reflejarlo — no la fecha
    vieja de `updated_at`, que es justo el fallo que esto corrige."""
    from app.db import SessionLocal
    from app.models import Client, DailyLog, Period, Plan

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    hace_meses = datetime.now(timezone.utc) - timedelta(days=180)
    c = _cliente(db, "ConRegistro", marca, updated_at=hace_meses)
    db.flush()
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                goal_type="fat_loss", generated_by="test", created_at=hace_meses,
                nutrition_json={}, training_json={}, education_json={})
    db.add(plan); db.flush()
    ayer = date.today() - timedelta(days=1)
    per = Period(client_id=c.id, plan_id=plan.id, period_index=1, status="open",
                 starts_on=ayer - timedelta(days=5), ends_on=ayer + timedelta(days=9))
    db.add(per); db.flush()
    db.add(DailyLog(period_id=per.id, log_date=ayer, weight_kg=80.0))
    db.commit()
    try:
        fila = _fila(http, c.id)
        tocado = datetime.fromisoformat(fila["last_touch_at"].replace("Z", "+00:00"))
        # Tiene que caer EN el día de ayer (mediodía UTC, ver el backend), no
        # en `updated_at` (hace 180 días).
        assert tocado.date() == ayer
    finally:
        _borra(db, [c])
        db.close()


def test_un_plan_generado_hoy_manda_sobre_un_registro_antiguo(http):
    """El cliente no registra desde hace semanas, pero el coach le acaba de
    generar un plan: eso es trabajo reciente y también cuenta como "tocado"."""
    from app.db import SessionLocal
    from app.models import DailyLog, Period, Plan

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    hace_semanas = datetime.now(timezone.utc) - timedelta(days=40)
    c = _cliente(db, "PlanNuevo", marca, updated_at=hace_semanas)
    db.flush()
    plan_viejo = Plan(client_id=c.id, month_index=1, version=1, status="superseded",
                       goal_type="fat_loss", generated_by="test",
                       created_at=hace_semanas,
                       nutrition_json={}, training_json={}, education_json={})
    db.add(plan_viejo); db.flush()
    per = Period(client_id=c.id, plan_id=plan_viejo.id, period_index=1, status="analyzed",
                 starts_on=date.today() - timedelta(days=40), ends_on=date.today() - timedelta(days=26))
    db.add(per); db.flush()
    db.add(DailyLog(period_id=per.id, log_date=date.today() - timedelta(days=39), weight_kg=80.0))
    plan_nuevo = Plan(client_id=c.id, month_index=2, version=1, status="published",
                       goal_type="fat_loss", generated_by="test",
                       nutrition_json={}, training_json={}, education_json={})
    db.add(plan_nuevo)  # created_at = ahora (default)
    db.commit()
    try:
        fila = _fila(http, c.id)
        tocado = datetime.fromisoformat(fila["last_touch_at"].replace("Z", "+00:00"))
        assert tocado.date() == date.today()
    finally:
        _borra(db, [c])
        db.close()


def test_una_peticion_del_cliente_hoy_manda_sobre_todo_lo_demas(http):
    """El cliente acaba de escribir una duda: eso es interacción SUYA, y tiene
    que contar igual que el trabajo del coach."""
    from app.db import SessionLocal
    from app.models import ChangeRequest

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    hace_meses = datetime.now(timezone.utc) - timedelta(days=90)
    c = _cliente(db, "Pregunta", marca, updated_at=hace_meses)
    db.flush()
    db.add(ChangeRequest(client_id=c.id, status="open", message="¿Puedo cambiar el pollo por pavo?"))
    db.commit()
    try:
        fila = _fila(http, c.id)
        tocado = datetime.fromisoformat(fila["last_touch_at"].replace("Z", "+00:00"))
        assert tocado.date() == date.today()
    finally:
        _borra(db, [c])
        db.close()


def test_el_listado_no_crece_en_consultas_por_estas_tres_fuentes(http):
    """El mismo puñado de consultas para tres clientes con plan+registro+
    petición que para uno vacío: las tres fuentes nuevas son AGRUPADAS, no una
    consulta por cliente (mismo criterio anti-N+1 de siempre en este listado)."""
    import collections

    from sqlalchemy import event

    from app.db import SessionLocal, engine
    from app.models import ChangeRequest, DailyLog, Period, Plan

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    creados = [_cliente(db, f"Lote{i}", marca) for i in range(3)]
    db.flush()
    for c in creados:
        plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                    goal_type="fat_loss", generated_by="test",
                    nutrition_json={}, training_json={}, education_json={})
        db.add(plan); db.flush()
        per = Period(client_id=c.id, plan_id=plan.id, period_index=1, status="open",
                     starts_on=date.today() - timedelta(days=5), ends_on=date.today() + timedelta(days=9))
        db.add(per); db.flush()
        db.add(DailyLog(period_id=per.id, log_date=date.today(), weight_kg=80.0))
        db.add(ChangeRequest(client_id=c.id, status="open", message="hola"))
    db.commit()

    consultas = collections.Counter()

    def _cuenta(conn, cursor, statement, params, context, executemany):
        consultas["n"] += 1

    try:
        event.listen(engine, "before_cursor_execute", _cuenta)
        consultas.clear()
        r = http.get("/api/clients", headers=_auth())
        assert r.status_code == 200
        n_tres = consultas["n"]

        consultas.clear()
        _borra(db, creados[1:])
        creados = creados[:1]
        r = http.get("/api/clients", headers=_auth())
        assert r.status_code == 200
        n_uno = consultas["n"]

        # Con tres clientes de más en la cartera, las consultas NUEVAS no
        # pueden crecer 3x — si crecieran así, alguna volvió a ser por cliente.
        assert n_tres <= n_uno + 2, (n_tres, n_uno)
    finally:
        event.remove(engine, "before_cursor_execute", _cuenta)
        _borra(db, creados)
        db.close()
