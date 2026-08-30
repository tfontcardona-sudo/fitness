"""Salud de los AUTOMATISMOS: que se note cuando dejan de correr.

Los trabajos programados abren períodos, persiguen a quien no registra, cortan
las suscripciones de la oferta ya cobradas y avisan al coach. Si se paran, el
coach tiene que enterarse por el panel, no por el log del contenedor.
"""
import uuid
import warnings
from datetime import datetime, timedelta, timezone

import pytest

warnings.filterwarnings("ignore")


@pytest.fixture()
def sidecar(tmp_path, monkeypatch):
    """Aísla el sidecar de estado en un directorio temporal."""
    from app.config import settings
    from app.services import job_state

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "scheduler_enabled", True)
    return job_state


def test_se_anota_cada_ejecucion_con_su_resultado(sidecar):
    sidecar.record_job("daily_maintenance", ok=True, detalle="3 períodos abiertos")
    estado = sidecar.estado_de_los_trabajos()["daily_maintenance"]
    assert estado["last_ok"] is True
    assert estado["fallos_seguidos"] == 0
    assert "períodos" in estado["detail"]

    sidecar.record_job("daily_maintenance", ok=False, detalle="OperationalError: x")
    estado = sidecar.estado_de_los_trabajos()["daily_maintenance"]
    assert estado["last_ok"] is False and estado["fallos_seguidos"] == 1
    # El último ÉXITO se conserva: es lo que decide si hay que alarmar.
    assert estado["last_success_at"]


def test_sin_datos_todavia_no_se_alarma(sidecar):
    """Un despliegue recién hecho no puede pintar una alerta roja."""
    assert sidecar.automatismos_parados() is None


def test_si_el_mantenimiento_lleva_dias_sin_correr_se_avisa(sidecar):
    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    assert sidecar.automatismos_parados() is None

    # Se falsea el último éxito a hace tres días.
    import json

    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    hace3 = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    datos["daily_maintenance"]["last_success_at"] = hace3
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    motivo = sidecar.automatismos_parados()
    assert motivo and "no se ejecuta" in motivo
    assert "72 h" in motivo or "71 h" in motivo


def test_el_scheduler_apagado_se_canta(sidecar, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "scheduler_enabled", False)
    motivo = sidecar.automatismos_parados()
    assert motivo and "apagados" in motivo


def test_un_fallo_al_anotar_no_rompe_el_trabajo(monkeypatch):
    """El registro es best-effort: si el disco falla, el job sigue su curso."""
    from app.services import job_state

    monkeypatch.setattr(job_state, "_ruta", lambda: (_ for _ in ()).throw(OSError("disco")))
    job_state.record_job("daily_maintenance", ok=True)   # no debe lanzar


# ---------------------------------------------------------------- avisos ----
# Los recordatorios tienen que INSISTIR, no acosar: un aviso que no caduca
# acaba con la app silenciada y con ella los que sí importan.

def _db_disponible() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


necesita_db = pytest.mark.skipif(not _db_disponible(), reason="Requiere PostgreSQL")


@necesita_db
def test_el_recordatorio_de_fotos_caduca():
    """Sin tope salían 5 push al día, para siempre, aunque la revisión se
    cerrara semanas atrás y el cliente estuviera en el ciclo siguiente."""
    import uuid
    from datetime import date

    from app.db import SessionLocal
    from app.models import Client, FeedbackDoc, Period, Plan
    from app.security import new_portal_token
    from app.services.push import photos_pending

    db = SessionLocal()
    try:
        c = Client(full_name="Fotos Caducas", email=f"fc-{uuid.uuid4().hex[:8]}@example.com",
                   portal_token="tmp", status="review_pending")
        db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
        plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
        db.add(plan); db.flush()
        hoy = date.today()
        per = Period(client_id=c.id, plan_id=plan.id, period_index=1,
                     starts_on=hoy - timedelta(days=20), ends_on=hoy - timedelta(days=6),
                     status="closed", photos_confirmed=False,
                     closing_submitted_at=datetime.now(timezone.utc) - timedelta(days=1))
        db.add(per); db.flush()
        db.commit()

        assert photos_pending(db, c) is True

        # a) pasada la ventana, se deja de pedir
        per.closing_submitted_at = datetime.now(timezone.utc) - timedelta(days=10)
        db.commit()
        assert photos_pending(db, c) is False

        # b) y si el informe ya se envió, tampoco (esas fotos eran PARA él)
        per.closing_submitted_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.add(FeedbackDoc(period_id=per.id, kind="biweekly", content_json={},
                           sent_at=datetime.now(timezone.utc)))
        db.commit()
        assert photos_pending(db, c) is False
    finally:
        db.close()


@necesita_db
def test_el_resumen_del_coach_no_se_repite_cada_tres_horas(sidecar, monkeypatch):
    """El móvil del coach vibraba 5 veces al día con el MISMO texto mientras
    hubiera una alerta abierta (y muchas duran semanas)."""
    from app.db import SessionLocal
    from app.services import push as push_svc

    enviados = []
    monkeypatch.setattr(push_svc, "push_configured", lambda: True)
    monkeypatch.setattr(push_svc, "send_to_coach",
                        lambda db, payload: (enviados.append(payload), 1)[1])

    alertas = [{"client_name": "Ana", "action": "Generar feedback",
                "severity": "alta", "key": "1:generate_feedback", "kind": "generate_feedback"}]
    monkeypatch.setattr("app.routers.alerts.client_alerts",
                        lambda db, c, hoy=None: alertas)

    creada = None
    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models import PushSubscription

        tenia = db.scalar(select(PushSubscription.id).where(
            PushSubscription.is_coach.is_(True)).limit(1))
        if not tenia:
            creada = PushSubscription(
                client_id=None, is_coach=True,
                endpoint=f"https://push.test/coach-{uuid.uuid4().hex}",
                p256dh="k", auth="a")
            db.add(creada)
            db.commit()

        # Hora fija DENTRO del horario activo (el job no envía de madrugada).
        cuando = datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc)
        r1 = push_svc.run_coach_digest(db, now=cuando)
        assert len(enviados) == 1, f"el primero sí sale: {r1}"
        push_svc.run_coach_digest(db, now=cuando)
        assert len(enviados) == 1, "el segundo, con lo mismo, no vuelve a sonar"

        # Con una alerta NUEVA sí vuelve a avisar.
        alertas.append({"client_name": "Luis", "action": "Cobrar", "severity": "alta",
                        "key": "2:payment_pending", "kind": "payment_pending"})
        push_svc.run_coach_digest(db, now=cuando)
        assert len(enviados) == 2
    finally:
        # La suscripción de prueba NO puede quedarse: otro test comprueba que
        # sin dispositivos del coach el resumen se salta.
        if creada is not None:
            db.delete(creada)
            db.commit()
        db.close()


# --- Tanda 3: lo que la vigilancia NO miraba ---------------------------------

def test_un_trabajo_secundario_muerto_dias_tambien_se_canta(sidecar):
    """Solo se vigilaba el mantenimiento diario: los recordatorios del cliente,
    el resumen del coach o los avisos de videollamada podían estar caídos
    indefinidamente y el panel seguía diciendo que todo iba bien."""
    import json

    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    sidecar.record_job("push_reminders", ok=True, detalle="ok")
    assert sidecar.automatismos_parados() is None

    # Los push llevan un día entero sin salir (se esperan cada 3 h).
    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["push_reminders"]["last_success_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    motivo = sidecar.automatismos_parados()
    assert motivo and "recordatorios del cliente" in motivo


def test_saltarse_una_vuelta_de_un_secundario_no_alarma(sidecar):
    """Un push perdido (un reinicio, un despliegue) no puede pintar alerta: por
    eso el margen de los secundarios es ancho."""
    import json

    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    sidecar.record_job("coach_digest", ok=True, detalle="ok")
    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["coach_digest"]["last_success_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert sidecar.automatismos_parados() is None


def test_la_huella_del_resumen_no_se_vigila_como_un_trabajo(sidecar):
    """`record_job` se reutiliza para guardar la huella de dedup del resumen del
    coach: no es un automatismo y no puede salir como 'parado'."""
    import json

    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    sidecar.record_job("coach_digest_huella", ok=True, detalle="abc")
    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["coach_digest_huella"]["last_success_at"] = (
        datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    assert sidecar.automatismos_parados() is None


def test_un_trabajo_que_fallo_y_ademas_dejo_de_correr_escala_a_parado(sidecar):
    """La rama de 'terminó con errores' devolvía antes de mirar la antigüedad:
    un mantenimiento que falló y encima se paró se quedaba para siempre en
    'terminó con errores' —que suena a que sigue corriendo— y el aviso no
    escalaba nunca a 'lleva N horas sin ejecutarse'."""
    import json

    sidecar.record_job("daily_maintenance", ok=True, detalle="ok")
    sidecar.record_job("daily_maintenance", ok=False, detalle="OperationalError: x")
    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["daily_maintenance"]["last_success_at"] = (
        datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    motivo = sidecar.automatismos_parados()
    assert motivo and "no se ejecuta" in motivo and "72 h" in motivo
    # …sin perder el porqué: el último intento reventó.
    assert "errores" in motivo


# --- Tanda 3: la huella del resumen del coach --------------------------------

def test_la_huella_del_resumen_distingue_conjuntos_largos_de_alertas(sidecar):
    """Se guardaba la lista de claves EN CRUDO y `record_job` la recorta a 300
    caracteres: con ~10 alertas abiertas dos conjuntos DISTINTOS coincidían en
    los primeros 300 caracteres, se leían como "sin novedades" y el resumen se
    silenciaba justo cuando había algo nuevo que contar."""
    import hashlib

    def huella(alertas):
        return hashlib.sha256(
            "|".join(sorted(str(a) for a in alertas)).encode("utf-8")).hexdigest()

    # Dos conjuntos que comparten un prefijo larguísimo y difieren al final.
    comunes = [f"cliente{i:02d}:renewal_due" for i in range(20)]
    a = huella(comunes)
    b = huella(comunes + ["cliente99:payment_pending"])
    assert a != b

    sidecar.record_job("coach_digest_huella", ok=True, detalle=a)
    guardada = sidecar.estado_de_los_trabajos()["coach_digest_huella"]["detail"]
    # Cabe entera (64 caracteres) y sigue distinguiendo el conjunto nuevo.
    assert guardada == a and guardada != b


# --- Tanda 3: la petición del cliente no puede caer en un agujero ------------

def _db_ok() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_ok(), reason="Requiere PostgreSQL")


@needs_db
def test_la_peticion_se_avisa_aunque_no_haya_plan_ni_el_cliente_este_activo():
    """"Escribir a mi coach" se ofrece a TODO cliente con acceso, pero la alerta
    vivía detrás de los `return` de "sin plan publicado" y de "inactivo": justo
    los dos que más escriben —el que aún no tiene plan y pregunta por él, y el
    que lleva semanas parado— mandaban su mensaje a un agujero."""
    from app.db import SessionLocal
    from app.models import ChangeRequest, Client
    from app.routers.alerts import client_alerts
    from app.security import new_portal_token

    db = SessionLocal()
    creados = []
    try:
        for estado in ("onboarding", "inactive"):
            uid = uuid.uuid4().hex[:8]
            c = Client(full_name=f"Peticion {estado}", email=f"cr-{uid}@test.local",
                       portal_token="tmp", status=estado)
            db.add(c)
            db.flush()
            c.portal_token = new_portal_token(c.id)
            db.add(ChangeRequest(client_id=c.id, message="Me duele la rodilla",
                                 status="open"))
            db.flush()
            creados.append(c)

            kinds = [a["kind"] for a in client_alerts(db, c)]
            assert "change_request" in kinds, (
                f"un cliente {estado} escribe y nadie se entera: {kinds}")
    finally:
        for c in creados:
            db.query(ChangeRequest).filter_by(client_id=c.id).delete()
            db.flush()
            db.delete(c)
        db.commit()
        db.close()


@needs_db
def test_la_racha_del_portal_cuenta_lo_mismo_que_el_motor():
    """La racha tenía su PROPIO predicado en SQL (`is_not(None)`), que da por
    bueno lo que el motor descarta: un `free_notes` vacío o un
    `chosen_options_json` sin nada elegido —filas que el autosave del portal crea
    con solo abrir la pantalla—. La racha premiaba días que para el coach no
    existían, justo lo que la "única verdad" venía a evitar."""
    from datetime import date, timedelta

    from app.db import SessionLocal
    from app.models import Client, DailyLog, Period, Plan
    from app.security import new_portal_token
    from app.services.portal import streak_days
    from app.services.push import dias_con_registro

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    hoy = date.today()
    c = Client(full_name="Racha", email=f"racha-{uid}@test.local",
               portal_token="tmp", status="active")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=5), ends_on=hoy + timedelta(days=8),
               status="open")
    db.add(p)
    db.flush()
    try:
        # Ayer: registro DE VERDAD. Hoy: solo la fila vacía del autosave.
        db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=1),
                        weight_kg=80.0))
        db.add(DailyLog(period_id=p.id, log_date=hoy,
                        free_notes="", chosen_options_json={}))
        db.flush()

        dias = dias_con_registro(db, p.id)
        assert hoy not in dias, "el motor no cuenta la fila vacía del autosave"
        # La racha debe contar lo mismo: 1 (ayer), no 2.
        assert streak_days(db, c.id, hoy) == 1
    finally:
        db.query(DailyLog).filter_by(period_id=p.id).delete()
        db.flush()
        db.delete(p)
        db.flush()
        db.delete(plan)
        db.flush()
        db.delete(c)
        db.commit()
        db.close()


@needs_db
def test_quien_registra_a_diario_pero_no_se_pesa_se_avisa_a_tiempo():
    """Ampliar "día registrado" a series y comidas fue correcto (un DQR Train
    que entrena a diario no puede salir "en riesgo"), pero abrió un punto ciego:
    quien toca su comida cada día cuenta como registrado, va verde en todas las
    pantallas y al cerrar la quincena el motor se encuentra con 0 pesajes,
    responde `dato_insuficiente` y no se puede ajustar nada. Catorce días
    perdidos que el coach descubría cuando ya no tenían arreglo."""
    from datetime import date, timedelta

    from app.db import SessionLocal
    from app.models import Client, DailyLog, Period, Plan
    from app.routers.alerts import client_alerts
    from app.security import new_portal_token

    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]
    hoy = date.today()
    c = Client(full_name="Sin pesajes", email=f"pesa-{uid}@test.local",
               portal_token="tmp", status="active", package_tier="full")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json={}, training_json={})
    db.add(plan)
    db.flush()
    # Día 10 de 14: aún da tiempo a pedirle que se pese.
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=9), ends_on=hoy + timedelta(days=4),
               status="open")
    db.add(p)
    db.flush()
    try:
        # Registra TODOS los días… eligiendo comida, sin pesarse nunca.
        for i in range(10):
            db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=i),
                            chosen_options_json={"1": "A"}))
        db.flush()

        kinds = [a["kind"] for a in client_alerts(db, c, hoy)]
        # No está "sin registros" (registra) pero SÍ se avisa de los pesajes.
        assert "no_logs" not in kinds
        assert "sin_pesajes" in kinds, kinds

        # En cuanto se pesa un par de veces, el aviso desaparece solo.
        for i in (0, 1):
            lg = db.query(DailyLog).filter_by(
                period_id=p.id, log_date=hoy - timedelta(days=i)).one()
            lg.weight_kg = 80.0 - i
        db.flush()
        assert "sin_pesajes" not in [a["kind"] for a in client_alerts(db, c, hoy)]
    finally:
        db.query(DailyLog).filter_by(period_id=p.id).delete()
        db.flush()
        db.delete(p)
        db.flush()
        db.delete(plan)
        db.flush()
        db.delete(c)
        db.commit()
        db.close()
