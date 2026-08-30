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
    assert motivo and "no se ejecuta" in motivo.lower()
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


def test_un_correo_que_falla_no_consume_el_intento(monkeypatch):
    """`EmailLog` anota los tres desenlaces: `sent`, `failed` (SMTP caído) y
    `disabled` (el cliente los tiene apagados). Los contadores de idempotencia
    los sumaban todos, así que un correo que NI SALIÓ consumía su intento: el
    recordatorio no se reintentaba jamás, y tres días de SMTP caído agotaban el
    tope de avisos de cierre para toda la quincena — el cliente no recibía
    ninguno y en el libro constaban tres."""
    from datetime import date, datetime, timedelta, timezone

    from sqlalchemy import delete

    from app.db import SessionLocal
    from app.models import Client, EmailLog
    from app.services.jobs import (MAX_AVISOS_DE_CIERRE, _already_sent_today,
                                   _enviados_desde, _ya_enviado_desde)

    db = SessionLocal()
    hoy = date.today()
    ahora = datetime.now(timezone.utc)
    c = Client(full_name="Correos Fallidos", email=f"fallo-{uuid.uuid4().hex[:8]}@test.local",
               package_tier="full", billing_period="1m", status="active",
               portal_token=f"tok-{uuid.uuid4().hex[:8]}", payment_status="paid")
    db.add(c)
    db.flush()
    try:
        def _anota(estado: str) -> None:
            db.add(EmailLog(client_id=c.id, kind="closing_due", subject="x",
                            sent_at=ahora, status=estado))
            db.flush()

        # Tres intentos que NO llegaron: ni cuentan como enviados ni gastan tope.
        _anota("failed")
        _anota("disabled")
        _anota("failed")
        assert _already_sent_today(db, c.id, "closing_due", hoy) is False
        assert _enviados_desde(db, c.id, "closing_due", hoy - timedelta(days=20)) == 0
        assert _ya_enviado_desde(db, c.id, "closing_due", hoy - timedelta(days=20)) is False

        # El que SÍ salió sí cuenta.
        _anota("sent")
        assert _already_sent_today(db, c.id, "closing_due", hoy) is True
        assert _enviados_desde(db, c.id, "closing_due", hoy - timedelta(days=20)) == 1
        assert _enviados_desde(db, c.id, "closing_due", hoy - timedelta(days=20)) < MAX_AVISOS_DE_CIERRE
    finally:
        db.execute(delete(EmailLog).where(EmailLog.client_id == c.id))
        db.execute(delete(Client).where(Client.id == c.id))
        db.commit()
        db.close()


def test_la_dedup_del_resumen_del_coach_aguanta_muchas_alertas(tmp_path, monkeypatch):
    """`record_job` guarda el detalle recortado a 300 caracteres. La huella era
    la lista literal de claves de alerta, que los pasa con ~10 alertas
    abiertas: a partir de ahí se comparaba la huella ENTERA contra una guardada
    a medias, nunca coincidían y el resumen se enviaba en cada barrido aunque
    no hubiera cambiado nada — justo el machaqueo que esta dedup evita."""
    from app.config import settings
    from app.services import push as push_svc
    from app.services.job_state import estado_de_los_trabajos, record_job

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(settings, "push_enabled", True)
    monkeypatch.setattr(settings, "vapid_public_key", "pub")
    monkeypatch.setattr(settings, "vapid_private_key", "priv")

    # 12 alertas con claves realistas: la lista literal pasa de 300 caracteres.
    alertas = [{"key": f"cliente-{i}:plan_stale_inputs:2026-08-30", "kind": "x"}
               for i in range(12)]
    literal = "|".join(sorted(str(a["key"]) for a in alertas))
    assert len(literal) > 300, "el caso de prueba tiene que superar el recorte"

    huella = push_svc._huella_de_alertas(alertas)
    record_job("coach_digest_huella", ok=True, detalle=huella)
    guardada = (estado_de_los_trabajos().get("coach_digest_huella") or {}).get("detail")
    assert guardada == huella, "la huella no cabe entera: la dedup no funcionará"

    # Y sigue distinguiendo: si cambia una alerta, cambia la huella.
    otras = alertas[:-1] + [{"key": "cliente-99:no_logs:2026-08-30", "kind": "x"}]
    assert push_svc._huella_de_alertas(otras) != huella


def test_se_vigilan_los_cinco_trabajos_no_solo_el_mantenimiento(sidecar):
    """Solo se miraba el mantenimiento diario. Los otros cuatro registran su
    estado desde siempre y nadie los leía: un `push_reminders` caído tres días
    deja a TODOS los clientes sin un solo aviso durante media quincena, y el
    panel decía que los automatismos iban bien."""
    import json
    from datetime import datetime, timedelta, timezone

    from app.services.job_state import ESPERADO_HORAS, MARGEN_NO_CRITICO

    ahora = datetime.now(timezone.utc)
    for nombre in ESPERADO_HORAS:
        sidecar.record_job(nombre, ok=True, detalle="ok")
    assert sidecar.automatismos_parados() is None, "recién ejecutados: todo bien"

    ruta = sidecar._ruta()
    for nombre, horas in ESPERADO_HORAS.items():
        if nombre in sidecar.CRITICOS:
            continue
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        muerto = ahora - timedelta(hours=horas * MARGEN_NO_CRITICO + 2)
        datos[nombre]["last_success_at"] = muerto.isoformat()
        ruta.write_text(json.dumps(datos), encoding="utf-8")

        motivo = sidecar.automatismos_parados(ahora)
        assert motivo, f"{nombre} lleva días muerto y no se avisa"
        assert "no se ejecuta" in motivo.lower(), motivo

        # Se restaura para no arrastrarlo al siguiente.
        datos[nombre]["last_success_at"] = ahora.isoformat()
        ruta.write_text(json.dumps(datos), encoding="utf-8")


def test_un_trabajo_que_lleva_dias_fallando_lo_dice(sidecar):
    """Tras un fallo, el aviso devolvía siempre la misma frase suave y no
    escalaba nunca: un trabajo roto desde hacía días se leía igual que uno que
    falló una vez."""
    import json
    from datetime import datetime, timedelta, timezone

    ahora = datetime.now(timezone.utc)
    sidecar.record_job("daily_maintenance", ok=False, detalle="boom")
    reciente = sidecar.automatismos_parados(ahora)
    assert reciente and "Falla" in reciente

    ruta = sidecar._ruta()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["daily_maintenance"]["last_success_at"] = (
        ahora - timedelta(days=5)).isoformat()
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    viejo = sidecar.automatismos_parados(ahora)
    assert viejo and "120 h sin completarse" in viejo, viejo
    assert viejo != reciente, "el aviso tiene que escalar, no repetirse igual"
