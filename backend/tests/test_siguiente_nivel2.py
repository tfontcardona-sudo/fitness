"""Tests de la ronda "siguiente nivel 2": renovaciones, resumen semanal,
aprendizaje del coach, ahorro de créditos (prompt caching + educativo ligero),
récords del portal, anamnesis digital unificada y pagos (fee + payment_intent +
CSV). Requiere PostgreSQL (se salta sin él)."""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone

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


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


def _make_client(db, *, status="active", **kw):
    from app.models import Client
    from app.security import new_portal_token

    c = Client(full_name="Nivel2 Cliente", email=f"{uuid.uuid4().hex[:8]}@example.com",
               status=status, portal_token="tmp", **kw)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    return c


# ================================================================ renovación ==

def test_renewal_window_y_is_due():
    from types import SimpleNamespace

    from app.services.renewals import is_due, renewal_window

    hoy = date(2026, 8, 20)
    base = dict(payment_status="paid", stripe_subscription_id=None,
                billing_period="1m")
    # Pagado hace 25 días con plan de 30 → vence en 5 días → toca avisar.
    c = SimpleNamespace(**base, paid_at=datetime(2026, 7, 26, tzinfo=timezone.utc))
    ends_on, left = renewal_window(c, hoy)
    assert left == 5 and ends_on == date(2026, 8, 25)
    assert is_due(c, hoy)
    # Recién pagado: no aplica el aviso.
    c2 = SimpleNamespace(**base, paid_at=datetime(2026, 8, 15, tzinfo=timezone.utc))
    assert not is_due(c2, hoy)
    # La oferta (suscripción de Stripe) se cobra sola: nunca avisa.
    c3 = SimpleNamespace(payment_status="paid", stripe_subscription_id="sub_x",
                         billing_period="oferta",
                         paid_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
    assert renewal_window(c3, hoy) is None


def test_recordatorio_de_renovacion_al_cliente_una_vez_por_ciclo(db, monkeypatch):
    """El email de renovación sale UNA vez por ciclo pagado y un pago nuevo lo
    re-arma para el ciclo siguiente."""
    from app.config import settings
    from app.services.email_service import EmailService
    from app.services.email_service import brand_from_config
    from app.services.jobs import _maintain_client

    sent = []
    monkeypatch.setattr(EmailService, "_transport", lambda self, msg: sent.append(msg))
    monkeypatch.setattr(settings, "emails_enabled", True)
    monkeypatch.setattr(settings, "smtp_from", "coach@example.com")
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_user", "coach@example.com")
    monkeypatch.setattr(settings, "smtp_pass", "x")

    hoy = date.today()
    c = _make_client(db, payment_status="paid", billing_period="1m",
                     paid_at=datetime.now(timezone.utc) - timedelta(days=27),
                     emails_enabled=True)
    resumen = {"reminders": 0, "transitions": 0}
    emailer = EmailService(db)
    brand = brand_from_config(db)
    _maintain_client(db, c, hoy, emailer, brand, "http://test", resumen)
    db.commit()
    assert c.renewal_reminder_sent_at is not None
    primera = c.renewal_reminder_sent_at
    # Segunda pasada el mismo ciclo: NO repite.
    _maintain_client(db, c, hoy, emailer, brand, "http://test", resumen)
    db.commit()
    assert c.renewal_reminder_sent_at == primera
    # Ciclo SIGUIENTE (simulado moviendo el reloj atrás): renovó después del
    # último aviso y su nuevo ciclo vuelve a estar por vencer → se re-arma.
    c.renewal_reminder_sent_at = datetime.now(timezone.utc) - timedelta(days=40)
    c.paid_at = datetime.now(timezone.utc) - timedelta(days=27)
    db.commit()
    _maintain_client(db, c, hoy, emailer, brand, "http://test", resumen)
    db.commit()
    assert c.renewal_reminder_sent_at > primera - timedelta(days=1)
    assert c.renewal_reminder_sent_at > c.paid_at


def test_pay_link_reabre_checkout_en_ventana_de_renovacion(http, db, monkeypatch):
    """Con la renovación al caer, el enlace estable de pago vuelve a abrir un
    checkout aunque la ficha diga 'paid' (es el CTA del email de renovación)."""
    from app.config import settings
    from app.services import stripe_service

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    llamado = {}

    def _fake_checkout(dbx, tier, period, client=None):
        llamado["client"] = client.id if client else None
        return "https://stripe.test/checkout"

    monkeypatch.setattr(stripe_service, "create_checkout_url", _fake_checkout)
    import app.routers.stripe_router as sr

    monkeypatch.setattr(sr, "create_checkout_url", _fake_checkout)

    vencido = _make_client(db, payment_status="paid", billing_period="1m",
                           package_tier="full",
                           paid_at=datetime.now(timezone.utc) - timedelta(days=29))
    r = http.get(f"/api/pay/{vencido.portal_token}", follow_redirects=False)
    assert r.status_code == 302 and "stripe.test" in r.headers["location"]

    reciente = _make_client(db, payment_status="paid", billing_period="1m",
                            package_tier="full",
                            paid_at=datetime.now(timezone.utc) - timedelta(days=3))
    r2 = http.get(f"/api/pay/{reciente.portal_token}", follow_redirects=False)
    assert r2.status_code == 302 and r2.headers["location"].endswith("/pago-ok")


# ============================================================ resumen semanal ==

def test_resumen_semanal_construye_la_semana(db):
    from app.models import DailyLog, Period, Plan
    from app.services.portal import today_local
    from app.services.weekly_digest import build_digest

    c = _make_client(db, status="active")
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    hoy = today_local()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=10), ends_on=hoy + timedelta(days=4),
               status="open")
    db.add(p)
    db.flush()
    db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=1),
                    diet_adherence="yes", weight_kg=80.0))
    db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=2),
                    diet_adherence="yes", weight_kg=80.4))
    db.add(DailyLog(period_id=p.id, log_date=hoy - timedelta(days=8),
                    weight_kg=81.2))  # fuera de los 7 días, cuenta para el peso
    db.commit()

    digest = build_digest(db, hoy)
    mio = next(x for x in digest.clients if x.client_id == c.id)
    assert mio.days_logged == 2
    assert mio.weight_delta_kg == pytest.approx(-1.2, abs=0.01)


def test_resumen_semanal_email_idempotente_por_semana(db, monkeypatch):
    from app.config import settings
    from app.services.email_service import EmailService
    from app.services.weekly_digest import run_weekly_digest

    sent = []
    monkeypatch.setattr(EmailService, "_transport", lambda self, msg: sent.append(msg))
    monkeypatch.setattr(settings, "emails_enabled", True)
    monkeypatch.setattr(settings, "smtp_from", "coach@example.com")
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_user", "coach@example.com")
    monkeypatch.setattr(settings, "smtp_pass", "x")
    _make_client(db, status="active")

    r1 = run_weekly_digest(db)
    assert r1["clients"] >= 1
    r2 = run_weekly_digest(db)
    # La segunda pasada de la misma semana NO reenvía el email.
    assert r2["email"] is False and r2["skipped"] == "email ya enviado esta semana"


# ======================================================== aprendizaje coach ==

class _ScriptedAI:
    def __init__(self, payload: dict):
        self._payload = payload
        self.calls = []

    def generate_json(self, *, model, system, user, schema, temperature=None, **_kw):
        self.calls.append({"model": model, "system": system, "user": user})
        return schema.model_validate(self._payload)


def test_lecciones_se_destilan_y_filtran_numeros(db, monkeypatch, tmp_path):
    from app.models import Plan
    from app.services import coach_lessons as cl
    from app.services.continuous_learning import record_edit

    monkeypatch.setattr(cl, "_sidecar_path", lambda: tmp_path / "lecciones.json")
    c = _make_client(db)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="draft")
    db.add(plan)
    db.flush()
    for i in range(6):
        record_edit(db, plan_id=plan.id, category="seleccion_alimentos",
                    note=f"Cambio {i}: quita el pavo del desayuno", commit=False)
    db.commit()

    ai = _ScriptedAI({"lessons": [
        "Prefiere desayunos sin fiambre; usa huevos o lácteos.",
        "Sube la proteína a 180 g en recomposición.",  # numérica → fuera
        "Redacta las notas del plan en tono cercano y breve.",
    ]})
    data = cl.distill_lessons(db, ai=ai)
    assert ai.calls and ai.calls[0]["model"]  # usó el modelo ligero inyectado
    assert "Prefiere desayunos sin fiambre; usa huevos o lácteos." in data["lessons"]
    # La lección con cifras de gramos NO pasa el filtro determinista.
    assert all("180 g" not in x for x in data["lessons"])

    bloque = cl.lessons_reference()
    assert "LECCIONES DEL COACH" in bloque
    assert "sin cambiar ningún número" in bloque.lower() or "SIN cambiar ningún número" in bloque


def test_lecciones_llegan_al_prompt_de_generacion(monkeypatch):
    import app.services.coach_lessons as cl

    monkeypatch.setattr(cl, "load_lessons",
                        lambda: {"lessons": ["Evita el brócoli en las cenas."]})
    bloque = cl.lessons_reference()
    assert "Evita el brócoli" in bloque


# ========================================================== ahorro créditos ==

def test_system_payload_cachea_solo_los_grandes():
    from app.services.ai.client import CACHE_SYSTEM_MIN_CHARS, AIClient

    corto = AIClient._system_payload("hola")
    assert corto == "hola"
    grande = "x" * (CACHE_SYSTEM_MIN_CHARS + 1)
    payload = AIClient._system_payload(grande)
    assert isinstance(payload, list)
    assert payload[0]["cache_control"] == {"type": "ephemeral"}
    lista = [{"type": "text", "text": "ya montado"}]
    assert AIClient._system_payload(lista) is lista


def test_panel_de_revisores_comparte_contexto_cacheado():
    """Los 8-10 roles del panel reciben el MISMO system (bloques con
    cache_control) y solo cambia el user (rol + rúbrica)."""
    from app.services.review_panel import REVIEWER_ROLES, make_ai_reviewer

    class _AI:
        def __init__(self):
            self.calls = []

        def generate_json(self, *, model, system, user, schema, temperature=None, **_kw):
            self.calls.append({"system": system, "user": user})
            return schema.model_validate(
                {"veredicto": "aprobado", "puntuacion_rubrica": 90, "hallazgos": []})

    ai = _AI()
    reviewer = make_ai_reviewer(ai, plan_text="PLAN X", anamnesis_text="ANAM Y",
                                criterios_text="CRITERIO Z")
    reviewer(REVIEWER_ROLES[0])
    reviewer(REVIEWER_ROLES[1])
    s0, s1 = ai.calls[0]["system"], ai.calls[1]["system"]
    assert s0 is s1  # mismo objeto → mismo prefijo → caché
    assert isinstance(s0, list) and len(s0) == 2
    assert all(b.get("cache_control") == {"type": "ephemeral"} for b in s0)
    assert "ANAM Y" in s0[0]["text"] and "CRITERIO Z" in s0[0]["text"]
    assert "PLAN X" in s0[1]["text"]
    assert "rúbrica" in ai.calls[0]["user"].lower()


def test_educativo_usa_modelo_ligero_y_cachea(monkeypatch, tmp_path):
    from app.config import settings
    from app.schemas.ai import EducationOutput
    from app.services.ai import generator as gen

    monkeypatch.setattr(settings, "education_cache_enabled", True)
    import app.services.storage as st

    monkeypatch.setattr(st, "storage_root", lambda: tmp_path)

    payload = {"pills": [{"topic": "RIR", "for_client": "…"}] * 3,
               "biomech_by_pattern": [{"pattern": "empuje", "cues": ["x"], "why": "y"}],
               "faq": []}
    ai = _ScriptedAI(payload)
    e1 = gen._education_with_cache(ai, split_name="Torso/Pierna", variant="full",
                                   user="da igual")
    assert isinstance(e1, EducationOutput)
    assert ai.calls[0]["model"] == settings.model_light
    # Segunda vez con el mismo split: sale de la caché, SIN llamada nueva.
    e2 = gen._education_with_cache(ai, split_name="Torso/Pierna", variant="full",
                                   user="da igual")
    assert len(ai.calls) == 1
    assert e2.pills[0].topic == "RIR"


# ============================================================ portal récords ==

def test_workout_history_incluye_records(http, db):
    from app.models import DailyLog, Exercise, Period, Plan, WorkoutLog

    c = _make_client(db)
    ex = Exercise(canonical_name=f"Press banca {uuid.uuid4().hex[:6]}",
                  muscle_primary="pecho", movement_pattern="empuje_horizontal",
                  equipment=["barra"])
    db.add(ex)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published")
    db.add(plan)
    db.flush()
    hoy = date.today()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=hoy - timedelta(days=10), ends_on=hoy + timedelta(days=4),
               status="open")
    db.add(p)
    db.flush()
    d1 = DailyLog(period_id=p.id, log_date=hoy - timedelta(days=3))
    db.add(d1)
    db.flush()
    db.add(WorkoutLog(daily_log_id=d1.id, exercise_id=ex.id, set_number=1,
                      reps=8, weight_kg=60.0))
    db.add(WorkoutLog(daily_log_id=d1.id, exercise_id=ex.id, set_number=2,
                      reps=5, weight_kg=70.0))
    # Una serie de 20 reps NO cuenta para el récord (mismo criterio que metrics).
    db.add(WorkoutLog(daily_log_id=d1.id, exercise_id=ex.id, set_number=3,
                      reps=20, weight_kg=100.0))
    db.commit()

    try:
        r = http.get(f"/api/p/{c.portal_token}/workout-history")
        assert r.status_code == 200
        rec = r.json()["records"][str(ex.id)]
        # Mejor e1RM: 70×(1+5/30) ≈ 81,67 — no la serie de 20 reps.
        assert rec["weight_kg"] == 70.0 and rec["reps"] == 5
        assert rec["e1rm_kg"] == pytest.approx(81.67, abs=0.05)
    finally:
        # La tabla exercises es COMPARTIDA (el conftest solo limpia clientes):
        # sin esto, el ejercicio de prueba rompía los tests del listado.
        from sqlalchemy import delete

        db.execute(delete(WorkoutLog).where(WorkoutLog.exercise_id == ex.id))
        db.execute(delete(Exercise).where(Exercise.id == ex.id))
        db.commit()


# ======================================================== anamnesis digital ==

def test_consentimiento_no_cuenta_como_anamnesis(db, tmp_path, monkeypatch):
    import app.services.storage as st

    monkeypatch.setattr(st, "storage_root", lambda: tmp_path)
    c = _make_client(db, status="onboarding")
    d = tmp_path / "clients" / str(c.id) / "documents"
    d.mkdir(parents=True)
    (d / "consentimiento_rgpd.pdf").write_bytes(b"%PDF-1.4 consent")
    assert st.list_documents(c.id) == []
    (d / "anamnesis.pdf").write_bytes(b"%PDF-1.4 anamnesis")
    assert [x["name"] for x in st.list_documents(c.id)] == ["anamnesis.pdf"]


def test_quien_ya_mando_su_anamnesis_no_puede_reescribir_la_ficha(http, db, tmp_path,
                                                                  monkeypatch):
    """Ni por la vía PDF ni con el plan ya en marcha.

    El enlace del cuestionario es permanente. Con el criterio antiguo (solo
    `consent_signed_at`), el cliente que la mandó en PDF volvía a su enlace,
    veía el formulario en blanco y podía machacar peso, objetivo, lesiones y
    alergias de una ficha ya revisada — sin diff, sin historial y sin que
    nadie se enterara.
    """
    import app.services.storage as st
    from app.routers.portal_public import _anamnesis_recibida

    monkeypatch.setattr(st, "storage_root", lambda: tmp_path)
    c = _make_client(db, status="onboarding")
    d = tmp_path / "clients" / str(c.id) / "documents"
    d.mkdir(parents=True)
    (d / "anamnesis.pdf").write_bytes(b"%PDF-1.4 anamnesis")
    db.commit()

    assert _anamnesis_recibida(c) is True
    estado = http.get(f"/api/p/{c.portal_token}").json()
    assert estado["anamnesis_done"] is True     # ve "recibida", no el wizard

    body = {
        "sex": "female", "birth_date": "1990-05-01", "height_cm": 160,
        "start_weight_kg": 55.0, "goal_type": "muscle_gain", "level": "beginner",
        "training_days": 3, "session_max_min": 45, "training_place": "home",
        "daily_activity_level": "light", "diet_mode": "flexible_7",
        "consent_accepted": True,
    }
    r = http.post(f"/api/p/{c.portal_token}/anamnesis", json=body)
    assert r.status_code == 409, r.text
    assert http.get(f"/api/p/{c.portal_token}/anamnesis/prefill").status_code == 409

    # Y con el cliente ya activo (plan en marcha), tampoco.
    c2 = _make_client(db, status="active")
    assert http.post(f"/api/p/{c2.portal_token}/anamnesis", json=body).status_code == 409


def test_formulario_digital_apaga_el_banner_y_avisa(http, db):
    from app.routers.portal_public import _needs_anamnesis

    c = _make_client(db, status="onboarding")
    assert _needs_anamnesis(c) is True

    r = http.get(f"/api/p/{c.portal_token}/anamnesis/prefill")
    assert r.status_code == 200

    body = {
        "sex": "male", "birth_date": "1990-05-01", "height_cm": 178,
        "start_weight_kg": 82.5, "goal_type": "fat_loss", "level": "intermediate",
        "training_days": 4, "session_max_min": 60, "training_place": "gym",
        "daily_activity_level": "light", "diet_mode": "flexible_7",
        "food_allergies": ["lactosa"], "consent_accepted": True,
    }
    r2 = http.post(f"/api/p/{c.portal_token}/anamnesis", json=body)
    assert r2.status_code == 200, r2.text
    db.refresh(c)
    assert c.consent_signed_at is not None
    assert c.goal_type == "fat_loss" and c.daily_activity_level == "light"
    assert _needs_anamnesis(c) is False
    # El prefill ya no está disponible (los cambios son cosa del coach).
    assert http.get(f"/api/p/{c.portal_token}/anamnesis/prefill").status_code == 409
    # La alerta del panel la da por recibida (vía formulario).
    from app.routers.alerts import client_alerts

    alertas = client_alerts(db, c)
    txt = " ".join(a["message"] for a in alertas)
    assert "Anamnesis recibida" in txt


def test_actividad_diaria_invalida_da_422(http, db):
    c = _make_client(db, status="onboarding")
    body = {
        "sex": "male", "birth_date": "1990-05-01", "height_cm": 178,
        "start_weight_kg": 82.5, "goal_type": "fat_loss", "level": "intermediate",
        "training_days": 4, "session_max_min": 60, "training_place": "gym",
        "daily_activity_level": "muchísima", "diet_mode": "flexible_7",
        "consent_accepted": True,
    }
    assert http.post(f"/api/p/{c.portal_token}/anamnesis", json=body).status_code == 422


# ================================================================== pagos ==

def test_movimiento_guarda_fee_y_payment_intent(db):
    from app.services import payments as pay_svc

    obj = f"cs_fee_{uuid.uuid4().hex[:10]}"
    pago = pay_svc.record_payment(
        db, object_id=obj, kind="checkout", status="paid", amount_cents=12900,
        fee_cents=412, payment_intent=f"pi_{uuid.uuid4().hex[:10]}",
        paid_at=datetime.now(timezone.utc))
    db.commit()
    assert pago.fee_cents == 412 and pago.payment_intent.startswith("pi_")


def test_cargo_es_nuestro_por_payment_intent(db):
    """Robustez RGPD: sin ficha y sin factura, el cargo se reconoce por su
    payment_intent ya anotado en el libro."""
    from app.services import payments as pay_svc
    from app.services.stripe_service import _cargo_es_nuestro

    pi = f"pi_{uuid.uuid4().hex[:12]}"
    pay_svc.record_payment(
        db, object_id=f"cs_pi_{uuid.uuid4().hex[:8]}", kind="checkout",
        status="paid", amount_cents=9900, payment_intent=pi,
        paid_at=datetime.now(timezone.utc))
    db.commit()
    assert _cargo_es_nuestro(db, {"payment_intent": pi}, None) is True
    assert _cargo_es_nuestro(db, {"payment_intent": "pi_ajeno"}, None) is False


def test_summary_resta_comisiones_del_mes(db):
    from app.services import payments as pay_svc

    antes = pay_svc.summary(db)["month_fee_cents"]
    pay_svc.record_payment(
        db, object_id=f"cs_sumfee_{uuid.uuid4().hex[:8]}", kind="checkout",
        status="paid", amount_cents=10000, fee_cents=350,
        paid_at=datetime.now(timezone.utc))
    db.commit()
    despues = pay_svc.summary(db)["month_fee_cents"]
    assert despues - antes == 350


def test_export_csv_del_libro(http, db):
    from app.services import payments as pay_svc

    pay_svc.record_payment(
        db, object_id=f"cs_csv_{uuid.uuid4().hex[:8]}", kind="checkout",
        status="paid", amount_cents=12900, fee_cents=400,
        customer_name="CSV Cliente", customer_email="csv@x.com",
        paid_at=datetime.now(timezone.utc))
    db.commit()
    # Sin JWT no hay libro (datos económicos).
    assert http.get("/api/payments/export.csv").status_code in (401, 403)
    r = http.get("/api/payments/export.csv", headers=_auth())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    cuerpo = r.text
    assert cuerpo.startswith("﻿")  # BOM para Excel
    assert "CSV Cliente" in cuerpo and "129,00" in cuerpo and "4,00" in cuerpo


def test_subir_pdf_no_borra_el_consentimiento_rgpd(http, db, tmp_path, monkeypatch):
    """CRÍTICO (revisión adversarial): la subida de un PDF de anamnesis barría
    TODOS los PDF de documents/, incluido el justificante RGPD del formulario
    digital — prueba legal irrecuperable (el 409 impide regenerarla)."""
    import app.services.storage as st

    monkeypatch.setattr(st, "storage_root", lambda: tmp_path)
    c = _make_client(db, status="onboarding")
    d = tmp_path / "clients" / str(c.id) / "documents"
    d.mkdir(parents=True)
    (d / "consentimiento_rgpd.pdf").write_bytes(b"%PDF-1.4 consentimiento")
    (d / "anamnesis_vieja.pdf").write_bytes(b"%PDF-1.4 vieja")

    r = http.post(f"/api/p/{c.portal_token}/anamnesis-pdf",
                  files={"file": ("anamnesis.pdf", b"%PDF-1.4 nueva", "application/pdf")})
    assert r.status_code == 200, r.text
    nombres = {p.name for p in d.iterdir()}
    assert "consentimiento_rgpd.pdf" in nombres          # la prueba legal sigue
    assert "anamnesis_vieja.pdf" not in nombres          # la anterior sí se retira
    assert any(n.endswith(".pdf") and "consentimiento" not in n for n in nombres)


def test_quien_ya_envio_el_cuestionario_no_puede_reescribir_su_ficha_por_pdf(
        http, db, tmp_path, monkeypatch):
    """El PDF se LEE con IA y esa lectura PISA los campos de la ficha. Quien ya
    mandó el formulario digital tiene una ficha que el coach puede haber
    revisado y corregido: dejar entrar un PDF por detrás borraba esas
    correcciones en silencio. El formulario ya responde 409 tras enviarse; el
    PDF hacía la misma promesa y no la cumplía."""
    import app.services.storage as st

    monkeypatch.setattr(st, "storage_root", lambda: tmp_path)
    c = _make_client(db, status="onboarding")
    c.consent_signed_at = datetime.now(timezone.utc)   # envió el formulario
    db.commit()

    r = http.post(f"/api/p/{c.portal_token}/anamnesis-pdf",
                  files={"file": ("anamnesis.pdf", b"%PDF-1.4 nueva", "application/pdf")})
    assert r.status_code == 409, r.text
    assert "coach" in r.json()["detail"]


# --- Memoria de vetos: útil, pero SIN datos de nadie -------------------------

def test_la_memoria_de_vetos_no_lleva_datos_del_cliente(tmp_path, monkeypatch):
    """Las advertencias de vetos se inyectan en la generación de TODOS los
    clientes: no pueden llevar las cifras ni los alimentos de uno concreto (ni
    por privacidad ni porque los números los pone el backend, no la IA)."""
    from app.config import settings
    from app.services.coach_lessons import record_ai_vetos, vetos_reference

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))

    reales = [
        "violation: kcal objetivo 1450 por debajo del mínimo 1600 (max BMR/1600)",
        "violation: proteína 120 g < mínimo 144 g (1.8 g/kg)",
        "violation: ⚠ ALÉRGENO lactosa en «yogur griego» (opción 2 del slot 3)",
        "violation: aversión declarada: pescado en «merluza al horno»",
        "contrato: la IA devolvió 2300 kcal (objetivo del backend: 2000) — fijados",
    ]
    record_ai_vetos(reales)      # dos veces: solo lo repetido entra en el prompt
    record_ai_vetos(reales)

    bloque = vetos_reference()
    assert bloque, "los vetos repetidos deberían entrar en el prompt"
    assert not any(ch.isdigit() for ch in bloque), bloque
    for dato in ("lactosa", "yogur", "merluza", "pescado", "1450", "144"):
        assert dato not in bloque, f"se filtró «{dato}» al prompt de otro cliente"
    # Y la lección SÍ se conserva, en genérico.
    assert "alérgeno declarado" in bloque
    assert "por debajo del mínimo" in bloque


def test_los_vetos_ya_guardados_tambien_se_sanean_al_leerlos(tmp_path, monkeypatch):
    """El filtro se aplicaba SOLO al escribir. El sidecar es de larga vida —la
    memoria se acumula durante meses—, así que cualquier clave guardada antes
    de que el filtro existiera (o metida a mano) viajaba tal cual al prompt de
    TODOS los clientes, con las cifras y los alimentos de uno solo."""
    import json

    from app.config import settings
    from app.services.coach_lessons import _vetos_path, vetos_reference

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))

    # Sidecar "antiguo": escrito sin pasar por el filtro.
    p = _vetos_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"conteo": {
        "violation: kcal objetivo 1450 por debajo del mínimo 1600": 4,
        "violation: ⚠ ALÉRGENO lactosa en «yogur griego» (opción 2 del slot 3)": 3,
        "violation: aversión declarada: pescado en «merluza al horno»": 2,
    }}, ensure_ascii=False), encoding="utf-8")

    bloque = vetos_reference()
    assert bloque, "los vetos repetidos deberían entrar en el prompt"
    assert not any(ch.isdigit() for ch in bloque), bloque
    for dato in ("lactosa", "yogur", "merluza", "pescado", "1450", "1600"):
        assert dato not in bloque, f"se filtró «{dato}» al prompt de otro cliente"
    # La lección sobrevive, en genérico.
    assert "alérgeno declarado" in bloque
    assert "por debajo del mínimo" in bloque



def test_el_estado_del_cuestionario_dice_si_hay_consentimiento():
    """Las fotos iniciales EXIGEN consentimiento firmado (son datos de salud) y
    solo lo firma quien pasa por el FORMULARIO. Sin ese dato en el estado, la
    pantalla ofrecía subirlas también a quien entregó su anamnesis en PDF, y el
    backend le respondía 403: una petición imposible de satisfacer."""
    import io
    import uuid
    from datetime import datetime, timezone

    from fastapi.testclient import TestClient
    from PIL import Image
    from sqlalchemy import delete

    from app.db import SessionLocal
    from app.main import app
    from app.models import Client
    from app.security import new_portal_token

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    c = Client(full_name=f"Sin Consentimiento {marca}",
               email=f"sincons-{marca}@test.local", package_tier="full",
               billing_period="1m", status="onboarding", portal_token="tmp",
               payment_status="paid")
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    token, cid = c.portal_token, c.id
    db.close()

    buf = io.BytesIO()
    Image.new("RGB", (60, 90), (120, 120, 120)).save(buf, format="JPEG")
    try:
        with TestClient(app) as http:
            # Sin firmar: el estado lo dice Y el backend rechaza las fotos.
            estado = http.get(f"/api/p/{token}").json()
            assert estado["consent_signed"] is False
            r = http.post(f"/api/p/{token}/anamnesis/photos",
                          files={"files": ("f.jpg", buf.getvalue(), "image/jpeg")})
            assert r.status_code == 403, r.text

            # Firmado (vía formulario): el estado cambia y las fotos entran.
            db = SessionLocal()
            db.get(Client, cid).consent_signed_at = datetime.now(timezone.utc)
            db.commit()
            db.close()

            estado = http.get(f"/api/p/{token}").json()
            assert estado["consent_signed"] is True
            r = http.post(f"/api/p/{token}/anamnesis/photos",
                          files={"files": ("f.jpg", buf.getvalue(), "image/jpeg")})
            assert r.status_code == 200, r.text

            # Y el ÁNGULO viaja: la página sube una foto por ángulo. Cuando
            # todas nacían "front", el primer informe emparejaba el frontal de
            # la revisión con el lateral de la línea base (feedback_service
            # empareja por `kind`).
            r = http.post(f"/api/p/{token}/anamnesis/photos?kind=side",
                          files={"files": ("s.jpg", buf.getvalue(), "image/jpeg")})
            assert r.status_code == 200, r.text
            assert r.json()[0]["kind"] == "side"
    finally:
        db = SessionLocal()
        from app.models import ProgressPhoto

        db.execute(delete(ProgressPhoto).where(ProgressPhoto.client_id == cid))
        db.execute(delete(Client).where(Client.id == cid))
        db.commit()
        db.close()


def test_las_contradicciones_y_el_retrato_siguen_a_la_ficha_corregida():
    """Los dos son funciones DETERMINISTAS de la ficha —no salida de la IA, no
    cuestan créditos— y se servían congelados desde el momento del envío. Eso
    los convertía en una foto fija que mentía en las dos direcciones: seguían
    avisando de algo que el coach ya había corregido, y callaban si era él
    quien introducía la contradicción al editar. Y el retrato congelado ganaba
    al recálculo en vivo, así que las correcciones del coach —la razón de que
    revise la ficha antes de generar— NO llegaban al prompt."""
    import os
    import uuid
    from datetime import date, timedelta

    from fastapi.testclient import TestClient
    from sqlalchemy import delete

    from app.db import SessionLocal
    from app.main import app
    from app.models import Client
    from app.security import create_access_token, new_portal_token

    db = SessionLocal()
    marca = uuid.uuid4().hex[:8]
    # Objetivo imposible: perder 17 kg en un mes. Contradicción determinista.
    c = Client(full_name=f"Contradice {marca}", email=f"contra-{marca}@test.local",
               package_tier="full", billing_period="1m", status="active",
               portal_token="tmp", payment_status="paid", sex="male",
               birth_date=date.today() - timedelta(days=365 * 30), height_cm=178,
               start_weight_kg=95.0, goal_type="fat_loss", goal_weight_kg=78.0,
               goal_deadline=date.today() + timedelta(days=30),
               level="beginner", training_days=3)
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)
    db.commit()
    cid = c.id
    db.close()

    auth = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    try:
        with TestClient(app) as http:
            r = http.get(f"/api/clients/{cid}/anamnesis-analysis", headers=auth).json()
            assert r["contradictions"], "un objetivo imposible tiene que avisar"
            assert r["deep_analysis"], "sin sidecar, el retrato se compone al vuelo"
            assert "perder grasa" in r["deep_analysis"]

            # El COACH corrige el plazo: la contradicción tiene que apagarse.
            db = SessionLocal()
            db.get(Client, cid).goal_deadline = date.today() + timedelta(days=300)
            db.commit()
            db.close()
            r2 = http.get(f"/api/clients/{cid}/anamnesis-analysis", headers=auth).json()
            assert not r2["contradictions"], (
                f"sigue avisando de algo ya corregido: {r2['contradictions']}")

            # Y si el coach cambia el objetivo, el retrato lo refleja.
            db = SessionLocal()
            db.get(Client, cid).goal_type = "muscle_gain"
            db.commit()
            db.close()
            r3 = http.get(f"/api/clients/{cid}/anamnesis-analysis", headers=auth).json()
            assert "ganar músculo" in r3["deep_analysis"], (
                f"el retrato se quedó en el objetivo viejo: {r3['deep_analysis']}")
    finally:
        db = SessionLocal()
        db.execute(delete(Client).where(Client.id == cid))
        db.commit()
        db.close()
