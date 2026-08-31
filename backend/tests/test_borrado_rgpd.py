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
import json
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
        pago = pay_svc.record_payment(
            db, object_id=f"ch_rgpd_{uuid.uuid4().hex[:8]}", kind="charge",
            status="paid", amount_cents=12900, livemode=False, client=cliente,
            billing_period="1m", description="Pago de prueba",
            paid_at=datetime.now(timezone.utc),
        )
        db.commit()
        assert pago is not None and pago.customer_name, (
            "el cobro tiene que nacer CON el nombre, si no la prueba no dice nada")
        pid = plan.id
        perid = period.id
        ex_id = ex.id
        log_id = dl.id
        pago_id = pago.id
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
        # Lo que cuelga de los períodos y los planes, también fuera. Estaba en
        # `TABLAS_QUE_CUELGAN` pero el test no lo miraba: bastaba con que
        # alguien quitara una línea del borrado para que quedaran huérfanas —
        # con el peso diario, las series y el informe del cliente dentro— y
        # esta red de seguridad seguía en verde.
        from app.models import DailyLog, FeedbackDoc, WorkoutLog

        assert not list(db.scalars(select(DailyLog).where(DailyLog.period_id == perid)))
        assert not list(db.scalars(select(FeedbackDoc).where(FeedbackDoc.period_id == perid)))
        assert not list(db.scalars(
            select(WorkoutLog).where(WorkoutLog.daily_log_id == log_id)))

        # El COBRO se conserva (los ingresos del mes no cambian) pero ANONIMIZADO.
        # Antes solo se comprobaba que ya no apuntara a la ficha: una fila con
        # `client_id=None` y el nombre y el email del cliente todavía dentro
        # pasaba el test, y eso es exactamente el dato personal que la
        # supresión tiene que llevarse.
        assert not list(db.scalars(select(Payment).where(Payment.client_id == cid)))
        cobro = db.get(Payment, pago_id)
        assert cobro is not None, "el dinero del mes no puede desaparecer"
        assert cobro.customer_name is None, "el nombre sigue en el libro de caja"
        assert cobro.customer_email is None, "el email sigue en el libro de caja"
        assert cobro.anonymized_at is not None, "sin sello, sale como cobro huérfano"

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
def test_la_baja_se_lleva_tambien_el_historial_clinico_de_la_auditoria(http, auth):
    """Cada PATCH de la ficha guarda en `audit_log` el ANTES y el DESPUÉS de lo
    editado: lesiones, patologías, medicación, alergias, teléfono. Son datos de
    salud (art. 9 RGPD) y se quedaban ahí para siempre — sin ficha, sin
    caducidad y sin ninguna pantalla desde la que verlos. `audit_log` no tiene
    clave foránea a clients, así que la red estructural del otro test no puede
    cazarlo: hace falta esta.
    """
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import AuditLog

    nombre = f"Historial Clinico {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"clin-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]
    r = http.patch(f"/api/clients/{cid}", headers=auth, json={
        "medical_notes": "Hipotiroidismo diagnosticado en 2019",
        "medication_notes": "Eutirox 75 mcg",
    })
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        filas = list(db.scalars(select(AuditLog).where(
            AuditLog.entity == "client", AuditLog.entity_id == cid)))
        assert any("Eutirox" in json.dumps(f.detail_json or {}, ensure_ascii=False)
                   for f in filas), "el test no está mirando donde debe"
    finally:
        db.close()

    assert http.delete(f"/api/clients/{cid}?confirm={nombre}",
                       headers=auth).status_code == 204

    db = SessionLocal()
    try:
        quedan = list(db.scalars(select(AuditLog).where(
            AuditLog.entity == "client", AuditLog.entity_id == cid)))
        assert not [f for f in quedan
                    if "Eutirox" in json.dumps(f.detail_json or {}, ensure_ascii=False)]
    finally:
        db.close()


@needs_db
def test_descargar_todo_incluye_el_diario_y_las_series(http, auth):
    """El ZIP de portabilidad llevaba ficha, planes y seis campos por período:
    dejaba fuera justo lo que el cliente teclea durante meses. Y como una baja
    se exporta ANTES de borrar, ese historial desaparecía para siempre."""
    import io
    import zipfile

    from app.db import SessionLocal
    from app.models import DailyLog, Exercise, Period, Plan, WorkoutLog

    nombre = f"Portabilidad {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"port-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]

    db = SessionLocal()
    try:
        plan = Plan(client_id=cid, month_index=1, version=1, status="published")
        db.add(plan); db.flush()
        hoy = date.today()
        per = Period(client_id=cid, plan_id=plan.id, period_index=1,
                     starts_on=hoy - timedelta(days=14), ends_on=hoy, status="closed",
                     closing_waist_cm=84.0, closing_questions="¿Subo el peso?")
        db.add(per); db.flush()
        lg = DailyLog(period_id=per.id, log_date=hoy, weight_kg=79.4,
                      sleep_hours=7.5, free_notes="Hombro algo cargado")
        db.add(lg); db.flush()
        ex = Exercise(canonical_name=f"Remo port {uuid.uuid4().hex[:6]}",
                      muscle_primary="espalda", movement_pattern="traccion_horizontal",
                      equipment=["barra"], aliases=[], muscle_secondary=[],
                      contraindications=[])
        db.add(ex); db.flush()
        db.add(WorkoutLog(daily_log_id=lg.id, exercise_id=ex.id, set_number=1,
                          reps=10, weight_kg=60, rpe=8))
        db.commit()
        ex_id, ex_nombre = ex.id, ex.canonical_name
    finally:
        db.close()

    r = http.get(f"/api/clients/{cid}/export", headers=auth)
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        datos = json.loads(z.read("datos.json"))
    periodo = datos["periods"][0]
    assert periodo["cierre"]["cintura_cm"] == 84.0
    assert periodo["cierre"]["dudas"] == "¿Subo el peso?"
    dia = periodo["diario"][0]
    assert dia["peso_kg"] == 79.4 and dia["notas"] == "Hombro algo cargado"
    assert dia["series"][0]["ejercicio"] == ex_nombre
    assert dia["series"][0]["reps"] == 10 and dia["series"][0]["peso_kg"] == 60

    http.delete(f"/api/clients/{cid}?confirm={nombre}", headers=auth)
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").delete(Exercise).where(Exercise.id == ex_id))
        db.commit()
    finally:
        db.close()


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


def test_descargar_todo_incluye_los_informes_y_lo_que_escribio_el_cliente(http, auth):
    """El derecho de portabilidad exige entregar TODO lo que se tiene del
    interesado. Faltaban dos cosas suyas: los informes quincenales —que son el
    análisis de sus propios datos— y los mensajes que escribió a su coach desde
    el portal. Y como una baja se exporta ANTES de borrar, se perdían justo al
    ejercer el derecho que debía conservarlos."""
    import io
    import json
    import zipfile
    from datetime import date, timedelta

    from app.db import SessionLocal
    from app.models import ChangeRequest, FeedbackDoc, Period, Plan

    nombre = f"Informes {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"inf-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]

    db = SessionLocal()
    try:
        plan = Plan(client_id=cid, month_index=1, version=1, status="published")
        db.add(plan); db.flush()
        hoy = date.today()
        per = Period(client_id=cid, plan_id=plan.id, period_index=1,
                     starts_on=hoy - timedelta(days=14), ends_on=hoy, status="analyzed")
        db.add(per); db.flush()
        db.add(FeedbackDoc(period_id=per.id, kind="biweekly", content_json={
            "analysis": "Muy buena adherencia; el peso baja al ritmo previsto."}))
        db.add(ChangeRequest(client_id=cid, status="open",
                             message="Me voy de viaje: ¿cómo lo hago con las comidas?"))
        db.commit()
    finally:
        db.close()

    r = http.get(f"/api/clients/{cid}/export", headers=auth)
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        datos = json.loads(zf.read("datos.json"))

    informes = datos.get("informes") or []
    assert informes, "el ZIP no lleva los informes quincenales del cliente"
    assert "adherencia" in json.dumps(informes, ensure_ascii=False)
    assert informes[0]["revision"] == 1

    mensajes = datos.get("mensajes_al_coach") or []
    assert mensajes, "el ZIP no lleva lo que el cliente escribió a su coach"
    assert "de viaje" in mensajes[0]["mensaje"]


def test_una_baja_fallida_no_deja_al_cliente_sin_sus_ficheros(http, auth, monkeypatch):
    """Los archivos se borraban ANTES del commit. Si el commit fallaba —una
    tabla nueva con FK sin cubrir, un interbloqueo, la conexión caída— la ficha
    seguía viva y sus fotos, su anamnesis y sus documentos ya no estaban:
    pérdida irrecuperable en un cliente que NO se ha dado de baja."""
    from app.db import SessionLocal
    from app.models import Client
    from app.services.storage import storage_root

    nombre = f"Commit Roto {uuid.uuid4().hex[:6]}"
    creado = http.post("/api/clients", headers=auth, json={
        "full_name": nombre, "email": f"roto-{uuid.uuid4().hex[:8]}@example.com",
    })
    cid = creado.json()["client"]["id"]

    # Un fichero suyo en disco, como el que deja cualquier anamnesis subida.
    carpeta = storage_root() / "clients" / str(cid) / "documents"
    carpeta.mkdir(parents=True, exist_ok=True)
    fichero = carpeta / "anamnesis.pdf"
    fichero.write_bytes(b"%PDF-1.4 datos del cliente")

    # El commit de la baja revienta.
    from sqlalchemy.orm import Session as _Session

    original = _Session.commit

    def _commit_que_falla(self, *a, **kw):
        raise RuntimeError("interbloqueo simulado")

    monkeypatch.setattr(_Session, "commit", _commit_que_falla)
    try:
        r = http.delete(f"/api/clients/{cid}?confirm={nombre.replace(' ', '%20')}",
                        headers=auth)
    except RuntimeError:
        r = None      # el fallo puede propagarse: da igual, lo que importa es el disco
    monkeypatch.setattr(_Session, "commit", original)

    assert fichero.exists(), "la baja falló y aun así se llevó por delante sus ficheros"
    db = SessionLocal()
    try:
        assert db.get(Client, cid) is not None, "la ficha debería seguir existiendo"
    finally:
        db.close()


def test_el_tope_de_caddy_deja_pasar_los_videos_que_el_backend_admite():
    """Caddy corta los cuerpos de `/api/*` a 30 MB, pero el backend admite
    vídeos de ejercicio de hasta `MAX_VIDEO_MB`. Sin una excepción para esa
    ruta, cualquier vídeo mayor moría en el proxy con un 413 pelado que no
    explica nada, sin llegar nunca al mensaje del backend.

    Prueba estática del Caddyfile: es infraestructura y no hay forma de
    ejercitarla desde pytest, pero el desajuste entre los dos topes sí se puede
    cazar aquí (que es lo que se escapó)."""
    import re
    from pathlib import Path

    from app.services.storage import MAX_VIDEO_MB

    caddy = (Path(__file__).resolve().parents[2] / "frontend" / "Caddyfile")
    texto = caddy.read_text(encoding="utf-8")

    bloque = re.search(r"handle /api/exercises/\*/video \{(.*?)\n\t\}", texto, re.S)
    assert bloque, "el Caddyfile no tiene un tope propio para subir vídeos"
    tope = re.search(r"max_size (\d+)MB", bloque.group(1))
    assert tope, "el bloque de vídeos no declara max_size"
    assert int(tope.group(1)) >= MAX_VIDEO_MB, (
        f"Caddy corta a {tope.group(1)} MB lo que el backend admite hasta "
        f"{MAX_VIDEO_MB} MB")

    # Y ese bloque tiene que ir ANTES del general: Caddy resuelve por orden.
    assert texto.index("handle /api/exercises/*/video") < texto.index("handle /api/* {")


def test_el_nombre_del_borrado_no_sobrevive_en_los_planes_de_otros(http, auth):
    """Copiar un plan deja un sello legible ("copiado de el plan de Ana Pérez")
    en `guardrail_flags` del plan DESTINO y en la auditoría de ese plan: filas
    de OTRO cliente, que la supresión de este no tocaba. El dato personal
    sobrevivía a la baja, en fichas ajenas."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import AuditLog, Client, Plan

    origen_nombre = f"Origen Borrable {uuid.uuid4().hex[:6]}"
    a = http.post("/api/clients", headers=auth, json={
        "full_name": origen_nombre,
        "email": f"orig-{uuid.uuid4().hex[:8]}@example.com"}).json()["client"]["id"]
    b = http.post("/api/clients", headers=auth, json={
        "full_name": f"Destino {uuid.uuid4().hex[:6]}",
        "email": f"dest-{uuid.uuid4().hex[:8]}@example.com"}).json()["client"]["id"]

    db = SessionLocal()
    try:
        # Simula el resultado de copiar el plan de A a B: el sello con su nombre
        # en el plan de B y en la auditoría de ESE plan.
        plan_b = Plan(client_id=b, month_index=1, version=1, status="draft",
                      generated_by="library",
                      guardrail_flags=[f"copiado de el plan de {origen_nombre} — "
                                       "revísalo y actívalo"])
        db.add(plan_b)
        db.flush()
        db.add(AuditLog(entity="plan", entity_id=plan_b.id, event="plan_copied",
                        detail_json={"client_id": b,
                                     "origen": f"el plan de {origen_nombre}",
                                     "avisos": 0}))
        db.commit()
        plan_b_id = plan_b.id
    finally:
        db.close()

    r = http.delete(f"/api/clients/{a}?confirm={origen_nombre.replace(' ', '%20')}",
                    headers=auth)
    assert r.status_code == 204, r.text

    db = SessionLocal()
    try:
        assert db.get(Client, a) is None
        plan_b = db.get(Plan, plan_b_id)
        marcas = " ".join(plan_b.guardrail_flags or [])
        assert origen_nombre not in marcas, f"su nombre sigue en el plan de otro: {marcas}"
        assert "copiado de" in marcas, "el sello tiene que seguir diciendo que es copia"

        ev = db.scalar(select(AuditLog).where(AuditLog.entity == "plan",
                                              AuditLog.entity_id == plan_b_id,
                                              AuditLog.event == "plan_copied"))
        assert ev is not None
        assert origen_nombre not in str(ev.detail_json), (
            f"su nombre sigue en la auditoría de otro: {ev.detail_json}")
    finally:
        db.close()
