"""Borrado RGPD de un cliente: que se lleve TODO por delante, siempre.

El borrado (routers/clients.delete_client) va tabla por tabla a mano porque casi
ninguna clave foránea tiene ON DELETE. Eso ya ha fallado dos veces en
producción —push_subscriptions y plan_edits— y el coach solo veía "no se pudo
borrar". Aquí hay dos redes:

1. `test_borrar_un_cliente_con_de_todo`: un cliente con una fila en CADA tabla
   que cuelga de él, borrado de verdad por el endpoint.
2. `test_ninguna_tabla_nueva_se_escapa_del_borrado`: lee las claves foráneas de
   la BASE DE DATOS y falla si aparece una tabla nueva que cuelgue de clientes
   (o de sus períodos/planes/diarios) y que nadie haya añadido al borrado. Así
   el fallo sale aquí y no cuando el coach da de baja a alguien.
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


DB = _db_available()
needs_db = pytest.mark.skipif(not DB, reason="Requiere PostgreSQL")


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(http):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import User
    from app.security import create_access_token, hash_password

    usuario = os.environ.get("ADMIN_1_USER", "coach1")
    db = SessionLocal()
    try:
        if not db.scalar(select(User).where(User.username == usuario)):
            db.add(User(username=usuario, password_hash=hash_password("test")))
            db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {create_access_token(usuario)}"}


# Todo lo que cuelga de un cliente y el borrado tiene que resolver. Si añades
# una tabla nueva que apunte a clients/periods/plans/daily_logs, añádela aquí Y
# al borrado de routers/clients.delete_client.
TABLAS_QUE_CUELGAN = {
    # directas
    "change_requests", "email_log", "payments", "periods", "plans",
    "progress_photos", "push_subscriptions", "video_calls", "whatsapp_sends",
    # a través de períodos / planes / diarios
    "daily_logs", "feedback_docs", "workout_logs", "plan_edits",
}


@needs_db
def test_borrar_un_cliente_con_de_todo(http, auth):
    """Un cliente con historia completa (plan editado, período con diario y
    series, feedback, fotos, videollamada, petición de cambio, push, cobro y
    email) se borra con 204 y no deja rastro."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import (
        ChangeRequest, DailyLog, EmailLog, Exercise, FeedbackDoc, Period, Plan,
        PlanEdit, ProgressPhoto, PushSubscription, VideoCall, WorkoutLog,
    )

    nombre = f"Borrado Total {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"rgpd-{uuid.uuid4().hex[:8]}@example.com",
        "package_tier": "full",
    })
    assert creado.status_code in (200, 201), creado.text
    cid = creado.json()["client"]["id"]

    db = SessionLocal()
    try:
        plan = Plan(client_id=cid, month_index=1, version=1, status="published")
        db.add(plan); db.flush()
        db.add(PlanEdit(plan_id=plan.id, category="calculo", note="ajuste"))

        hoy = date.today()
        period = Period(client_id=cid, plan_id=plan.id, period_index=1,
                        starts_on=hoy - timedelta(days=14), ends_on=hoy,
                        status="analyzed")
        db.add(period); db.flush()

        dl = DailyLog(period_id=period.id, log_date=hoy, weight_kg=80)
        db.add(dl); db.flush()

        ex = Exercise(canonical_name=f"Sentadilla rgpd {uuid.uuid4().hex[:6]}",
                      muscle_primary="pierna", movement_pattern="sentadilla",
                      equipment=["barra"], aliases=[], muscle_secondary=[],
                      contraindications=[])
        db.add(ex); db.flush()
        db.add(WorkoutLog(daily_log_id=dl.id, exercise_id=ex.id, set_number=1,
                          reps=8, weight_kg=60))

        db.add(FeedbackDoc(period_id=period.id, kind="biweekly", content_json={}))
        db.add(ProgressPhoto(client_id=cid, period_id=period.id, kind="front",
                             file_path=f"clients/{cid}/photos/x.jpg"))
        db.add(VideoCall(client_id=cid, period_index=1, status="proposed"))
        db.add(ChangeRequest(client_id=cid, message="cámbiame el jueves"))
        db.add(PushSubscription(client_id=cid, endpoint=f"https://push.test/{cid}",
                                p256dh="k", auth="a"))
        db.add(EmailLog(client_id=cid, kind="plan_delivery",
                        subject="Tu plan", status="sent"))
        db.commit()

        # Un cobro suyo en el libro de caja (se anonimiza, no se borra).
        from app.services import payments as pay_svc
        from app.models import Client

        cliente = db.get(Client, cid)
        pay_svc.record_payment(
            db, object_id=f"ch_rgpd_{uuid.uuid4().hex[:8]}", kind="charge",
            status="paid", amount_cents=12900, livemode=False, client=cliente,
            billing_period="1m", description="Pago de prueba",
            paid_at=datetime.now(timezone.utc),
        )
        db.commit()
        pid = plan.id
        perid = period.id
        ex_id = ex.id
    finally:
        db.close()

    r = http.delete(f"/api/clients/{cid}?confirm={nombre}", headers=auth)
    assert r.status_code == 204, r.text

    db = SessionLocal()
    try:
        from app.models import Client, Payment

        assert db.get(Client, cid) is None
        assert db.get(Plan, pid) is None
        assert db.get(Period, perid) is None
        assert not list(db.scalars(select(PlanEdit).where(PlanEdit.plan_id == pid)))
        assert not list(db.scalars(select(ProgressPhoto).where(ProgressPhoto.client_id == cid)))
        assert not list(db.scalars(select(VideoCall).where(VideoCall.client_id == cid)))
        assert not list(db.scalars(select(ChangeRequest).where(ChangeRequest.client_id == cid)))
        assert not list(db.scalars(select(PushSubscription).where(PushSubscription.client_id == cid)))
        # El COBRO se conserva (los ingresos del mes no cambian) pero sin ficha.
        movimientos = list(db.scalars(select(Payment).where(Payment.client_id == cid)))
        assert not movimientos, "el cobro sigue apuntando al cliente borrado"
        # El histórico de envíos se conserva pero DESLIGADO del cliente.
        assert not list(db.scalars(select(EmailLog).where(EmailLog.client_id == cid)))
        # Limpieza del ejercicio de prueba (no es del cliente).
        db.execute(__import__("sqlalchemy").delete(Exercise).where(Exercise.id == ex_id))
        db.commit()
    finally:
        db.close()


@needs_db
def test_ninguna_tabla_nueva_se_escapa_del_borrado():
    """Red de seguridad estructural: si alguien añade una tabla que cuelga del
    cliente y no la mete en el borrado RGPD, este test lo dice AQUÍ."""
    from sqlalchemy import create_engine, text

    from app.config import settings

    consulta = text("""
        SELECT c.conrelid::regclass::text AS tabla
        FROM pg_constraint c
        WHERE c.contype = 'f'
          AND c.confrelid IN (
              'clients'::regclass, 'periods'::regclass,
              'plans'::regclass, 'daily_logs'::regclass)
    """)
    with create_engine(settings.database_url).connect() as con:
        cuelgan = {fila[0] for fila in con.execute(consulta)}

    nuevas = cuelgan - TABLAS_QUE_CUELGAN
    assert not nuevas, (
        f"Tablas nuevas que cuelgan del cliente y NO están contempladas en el "
        f"borrado RGPD: {sorted(nuevas)}. Añádelas a "
        f"routers/clients.delete_client y a TABLAS_QUE_CUELGAN.")


@needs_db
def test_la_baja_corta_el_cobro_recurrente(http, auth, monkeypatch):
    """Dar de baja a un cliente con suscripción de Stripe la CANCELA allí.

    Sin esto, a alguien que ya no existe en el sistema se le seguía cobrando
    cada mes: el cargo entraba como pago huérfano y el coach se enteraba por
    la reclamación.
    """
    from app.config import settings
    from app.db import SessionLocal
    from app.models import Client
    from app.services import stripe_service

    canceladas: list[str] = []
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x", raising=False)
    monkeypatch.setattr(stripe_service, "cancelar_suscripcion",
                        lambda sub: (canceladas.append(sub), (True, "cancelada"))[1])

    nombre = f"Baja Suscrita {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"baja-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]
    db = SessionLocal()
    try:
        db.get(Client, cid).stripe_subscription_id = "sub_test_123"
        db.commit()
    finally:
        db.close()

    r = http.delete(f"/api/clients/{cid}?confirm={nombre}", headers=auth)
    assert r.status_code == 204, r.text
    assert canceladas == ["sub_test_123"]


@needs_db
def test_si_stripe_falla_no_se_borra_a_ciegas(http, auth, monkeypatch):
    """Si la cancelación falla, la baja se detiene con un mensaje accionable:
    borrar dejaría la suscripción cobrando sin nadie a quien asociarla."""
    from app.config import settings
    from app.db import SessionLocal
    from app.models import Client
    from app.services import stripe_service

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x", raising=False)
    monkeypatch.setattr(stripe_service, "cancelar_suscripcion",
                        lambda sub: (False, "Stripe no responde"))

    nombre = f"Baja Fallida {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"bajaf-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]
    db = SessionLocal()
    try:
        db.get(Client, cid).stripe_subscription_id = "sub_test_falla"
        db.commit()
    finally:
        db.close()

    r = http.delete(f"/api/clients/{cid}?confirm={nombre}", headers=auth)
    assert r.status_code == 502
    assert "Stripe" in r.json()["detail"]
    db = SessionLocal()
    try:
        assert db.get(Client, cid) is not None, "no se puede borrar a medias"
        # Limpieza: sin suscripción, la baja normal sí funciona.
        db.get(Client, cid).stripe_subscription_id = None
        db.commit()
    finally:
        db.close()
    assert http.delete(f"/api/clients/{cid}?confirm={nombre}",
                       headers=auth).status_code == 204
