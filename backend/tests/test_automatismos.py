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
