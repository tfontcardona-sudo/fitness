"""Seguimiento CONTINUO (marca sin ciclo quincenal).

El flujo de Professional: el cliente registra su día a día en el portal, el
informe se pone al día con lo que lleve registrado y el coach lo envía cuando
lo ve listo. No hay cierre quincenal, ni cuenta atrás, ni revisión que reclamar.

Requiere PostgreSQL (como el resto de tests de integración).
"""

from __future__ import annotations

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
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


class _IAGuionizada:
    """IA de mentira: devuelve un informe válido sin llamar a la API."""

    def generate_json(self, *, schema, **_kw):
        return schema.model_validate({
            "natural_analysis": "Análisis de prueba del seguimiento continuo.",
            "changes_bullets": ["Mantener el plan"],
            "answers": "",
            "next_objectives": ["Seguir registrando a diario"],
            "closing_message": "Buen trabajo.",
            "plan_adjustments": [],
        })


def _cliente_con_seguimiento(db, dias_registrados: int):
    """Cliente activo con plan publicado, período abierto y N días registrados."""
    from app.models import Client, DailyLog, Period, Plan
    from app.security import new_portal_token

    c = Client(full_name="Continuo Test", email=f"cont-{uuid.uuid4().hex[:8]}@example.com",
               package_tier="full", billing_period="unico", status="active",
               portal_token="pendiente", sex="female", height_cm=166,
               birth_date=date(1990, 5, 1), start_weight_kg=70.0, current_weight_kg=70.0,
               goal_type="fat_loss", level="beginner", training_days=3,
               training_place="gym", daily_activity_level="light")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)

    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json={"target_kcal": 1800, "tdee_kcal": 2100,
                                "macros": {"protein_g": 120, "carbs_g": 180, "fat_g": 60},
                                "meals": []},
                training_json={"sessions": []}, education_json=None,
                guardrail_flags=[], generated_by="test", goal_type="fat_loss")
    db.add(plan)
    db.flush()

    hoy = date.today()
    period = Period(client_id=c.id, plan_id=plan.id, period_index=1,
                    starts_on=hoy - timedelta(days=dias_registrados - 1),
                    ends_on=hoy + timedelta(days=300), status="open")
    db.add(period)
    db.flush()
    for i in range(dias_registrados):
        db.add(DailyLog(period_id=period.id,
                        log_date=period.starts_on + timedelta(days=i),
                        weight_kg=70.0 - i * 0.1, diet_adherence="yes",
                        sleep_hours=7.5, energy_1_5=4, mood_1_5=4, fatigue_1_5=2))
    db.commit()
    return c, plan, period


def _borrar(db, c):
    from app.models import Client, DailyLog, FeedbackDoc, Period, Plan
    from sqlalchemy import select

    for p in db.scalars(select(Period).where(Period.client_id == c.id)):
        for fb in db.scalars(select(FeedbackDoc).where(FeedbackDoc.period_id == p.id)):
            db.delete(fb)
        for dl in db.scalars(select(DailyLog).where(DailyLog.period_id == p.id)):
            db.delete(dl)
        db.delete(p)
    db.flush()   # los períodos referencian el plan: fuera antes de borrarlo
    for pl in db.scalars(select(Plan).where(Plan.client_id == c.id)):
        db.delete(pl)
    db.delete(db.get(Client, c.id))
    db.commit()


def test_el_periodo_no_vence_ni_pide_cierre(db):
    """Sin ciclo quincenal el seguimiento es continuo: nunca hay que cerrarlo."""
    from app import branding
    from app.services.periods import PERIOD_DAYS
    from app.services.portal import period_info

    assert branding.FEATURE_BIWEEKLY is False
    assert PERIOD_DAYS > 300, "el período de seguimiento no debe vencer cada 14 días"

    c, _plan, period = _cliente_con_seguimiento(db, 20)
    try:
        info = period_info(period, date.today())
        assert info["can_close"] is False, "el cliente nunca ve un cierre que hacer"
    finally:
        _borrar(db, c)


def test_informe_con_pocos_datos_avisa_en_vez_de_inventar(db):
    from app.services.feedback_service import FeedbackError, build_period_feedback

    c, _plan, period = _cliente_con_seguimiento(db, 2)
    try:
        with pytest.raises(FeedbackError) as exc:
            build_period_feedback(db, period.id, ai=_IAGuionizada())
        assert "pocos datos" in str(exc.value)
    finally:
        _borrar(db, c)


def test_informe_continuo_se_genera_con_el_periodo_abierto(db):
    """El informe sale de lo registrado, sin esperar a ningún cierre, y el
    seguimiento sigue abierto (el cliente puede seguir registrando)."""
    from app.services.feedback_service import build_period_feedback

    c, _plan, period = _cliente_con_seguimiento(db, 12)
    try:
        fb = build_period_feedback(db, period.id, ai=_IAGuionizada())
        db.commit()
        assert fb.kind == "continuous"
        assert fb.sent_at is None, "nace en BORRADOR: lo envía el coach"
        assert fb.content_json["logs_at_generation"] == 12
        db.refresh(period)
        assert period.status == "open", "el seguimiento no se cierra al informar"
        assert period.metrics_json, "las métricas quedan guardadas"
    finally:
        _borrar(db, c)


def test_regenerar_tras_enviar_crea_un_informe_nuevo(db):
    """Lo que el cliente ya recibió NO se reescribe por debajo."""
    from datetime import datetime, timezone

    from app.models import DailyLog, FeedbackDoc
    from sqlalchemy import select

    from app.services.feedback_service import build_period_feedback

    c, _plan, period = _cliente_con_seguimiento(db, 10)
    try:
        primero = build_period_feedback(db, period.id, ai=_IAGuionizada())
        primero.sent_at = datetime.now(timezone.utc)
        db.commit()
        id_primero = primero.id

        # El cliente sigue registrando y el coach lo pone al día
        db.add(DailyLog(period_id=period.id, log_date=date.today() + timedelta(days=1),
                        weight_kg=69.0, diet_adherence="yes"))
        db.flush()
        segundo = build_period_feedback(db, period.id, ai=_IAGuionizada())
        db.commit()

        assert segundo.id != id_primero, "el informe enviado no se sobrescribe"
        assert segundo.sent_at is None
        enviados = list(db.scalars(
            select(FeedbackDoc).where(FeedbackDoc.period_id == period.id)))
        assert len(enviados) == 2
    finally:
        _borrar(db, c)


def test_alertas_del_flujo_continuo(db):
    """Las alertas se centran en el ciclo real: generar el informe, ponerlo al
    día cuando hay datos nuevos y enviarlo."""
    from datetime import datetime, timezone

    from app.routers.alerts import client_alerts
    from app.services.feedback_service import build_period_feedback

    c, _plan, period = _cliente_con_seguimiento(db, 12)
    try:
        kinds = {a["kind"] for a in client_alerts(db, c, date.today())}
        assert "generate_feedback" in kinds, "12 días registrados y sin informe"
        assert "period_overdue" not in kinds, "no hay revisión que reclamar"

        fb = build_period_feedback(db, period.id, ai=_IAGuionizada())
        db.commit()
        kinds = {a["kind"] for a in client_alerts(db, c, date.today())}
        assert "send_feedback" in kinds and "generate_feedback" not in kinds

        fb.sent_at = datetime.now(timezone.utc)
        db.commit()
        kinds = {a["kind"] for a in client_alerts(db, c, date.today())}
        assert "send_feedback" not in kinds, "ya está enviado: nada que hacer"
    finally:
        _borrar(db, c)


def test_el_cliente_actualiza_su_evolucion_sin_cerrar_nada(db):
    """La pantalla Evolución del portal: peso y perímetros cuando el cliente se
    mide. Sin cierres, sin fechas límite y sin pisar lo que no manda."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import DailyLog, Period
    from sqlalchemy import select

    c, _plan, period = _cliente_con_seguimiento(db, 8)
    http = TestClient(app)
    try:
        r = http.post(f"/api/p/{c.portal_token}/measurements",
                      json={"weight_kg": 68.4, "waist_cm": 78.5,
                            "feelings_json": {"energia": 4, "hambre": 2}})
        assert r.status_code == 200, r.text
        assert set(r.json()["fields"]) == {"weight_kg", "waist_cm", "feelings_json"}

        db.expire_all()
        p = db.get(Period, period.id)
        assert p.status == "open", "guardar medidas NO cierra el seguimiento"
        assert p.closing_weight_kg == 68.4 and p.closing_waist_cm == 78.5

        # El peso entra también en el diario de hoy: es la serie de la evolución
        hoy_log = db.scalar(select(DailyLog).where(DailyLog.period_id == p.id,
                                                   DailyLog.log_date == date.today()))
        assert hoy_log is not None and hoy_log.weight_kg == 68.4

        # Mandar solo la cadera no borra lo anterior
        r = http.post(f"/api/p/{c.portal_token}/measurements", json={"hip_cm": 96.0})
        assert r.status_code == 200
        db.expire_all()
        p = db.get(Period, period.id)
        assert p.closing_hip_cm == 96.0 and p.closing_waist_cm == 78.5

        # Sin nada que guardar → 422 con mensaje claro
        assert http.post(f"/api/p/{c.portal_token}/measurements", json={}).status_code == 422
    finally:
        _borrar(db, c)
