"""Regresiones de la auditoría de PRODUCCIÓN DE PLANIFICACIONES (agosto 2026).

Cubre los arreglos del ciclo generar → revisar → adaptar → aprender:
- adaptar un plan SOLO-ENTRENO no fabrica una dieta vacía;
- el diet break del motor quincenal se APLICA (antes era solo texto);
- las cargas de arranque se calibran con los registros reales del cliente;
- las Novedades hablan en cristiano (sin jerga interna);
- memoria de vetos del validador (no tropezar dos veces);
- el panel caído deja constancia (ámbar degradado), no un falso "sin revisar";
- los revisores IA ven también el resumen del entreno;
- adaptar no avisa al cliente si el feedback de la revisión sigue sin enviar.
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
pytestmark_db = pytest.mark.skipif(not DB, reason="Requiere PostgreSQL")


@pytest.fixture(autouse=True, scope="module")
def _limpia_ejercicios_de_prueba():
    """Los ejercicios que crean estos tests NO pueden quedarse en la biblioteca
    real del coach (conftest solo limpia clientes de dominios de prueba)."""
    yield
    if not DB:
        return
    from sqlalchemy import delete, select

    from app.db import SessionLocal
    from app.models import Exercise, WorkoutLog

    db = SessionLocal()
    try:
        ids = list(db.scalars(select(Exercise.id).where(
            Exercise.canonical_name.like("Press banca test %"))))
        if ids:
            db.execute(delete(WorkoutLog).where(WorkoutLog.exercise_id.in_(ids)))
            db.execute(delete(Exercise).where(Exercise.id.in_(ids)))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _nuevo_cliente_con_plan(db, *, con_dieta=True, con_entreno=True):
    from app.models import Client, Exercise, Plan
    from app.security import new_portal_token

    uid = uuid.uuid4().hex[:8]
    c = Client(full_name=f"Prod {uid}", email=f"prod-{uid}@test.local",
               portal_token="p", status="active", goal_type="fat_loss",
               sex="male", current_weight_kg=80)
    db.add(c); db.flush(); c.portal_token = new_portal_token(c.id)
    # Listas SIEMPRE explícitas (nunca NULL): ExerciseOut las exige y una fila
    # con arrays a NULL rompía el listado de ejercicios de otros tests.
    ex = Exercise(canonical_name=f"Press banca test {uid}", muscle_primary="pecho",
                  movement_pattern="empuje_horizontal", equipment=["barra"],
                  aliases=[], muscle_secondary=[], contraindications=[])
    db.add(ex); db.flush()
    nutrition = None
    if con_dieta:
        nutrition = {"target_kcal": 1800, "tdee_kcal": 2200,
                     "macros": {"protein_g": 160, "carbs_g": 160, "fat_g": 50}}
    training = None
    if con_entreno:
        training = {"split_name": "Torso-Pierna", "sessions": [
            {"day": "Lunes", "name": "Torso", "exercises": [
                {"exercise_id": ex.id, "sets": 3, "reps": "8-10",
                 "start_weight_hint_kg": 40.0},
            ]},
        ]}
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                goal_type="fat_loss", nutrition_json=nutrition,
                training_json=training, education_json=None)
    db.add(plan); db.flush()
    return c, plan, ex


def _periodo_analizado(db, c, plan, analysis):
    from app.models import Period

    today = date.today()
    p = Period(client_id=c.id, plan_id=plan.id, period_index=1,
               starts_on=today - timedelta(days=15),
               ends_on=today - timedelta(days=1),
               status="analyzed", ai_analysis_json=analysis)
    db.add(p); db.flush()
    return p


# ------------------------------------------------ adaptar: solo-entreno ---

@pytestmark_db
def test_adaptar_solo_entreno_no_fabrica_dieta():
    """Un plan solo-entreno adaptado NO debe salir con nutrition_json fabricado
    ({} con macros/rationale → el PDF imprimía una dieta en blanco); el sello de
    Novedades vive en training_json y los ajustes de dieta se marcan como no
    aplicables en vez de perderse en silencio."""
    from app.db import SessionLocal
    from app.services.adapt_plan import adapt_plan_from_feedback

    db = SessionLocal()
    c, plan, _ex = _nuevo_cliente_con_plan(db, con_dieta=False)
    _periodo_analizado(db, c, plan, {"plan_adjustments": [
        {"area": "dieta", "change": "Bajar calorías un 5%", "reason": "x"},
        {"area": "entrenamiento", "change": "Subir +2,5 kg en los básicos", "reason": "y"},
    ]})
    db.commit()

    nuevo = adapt_plan_from_feedback(db, c.id)
    assert nuevo.nutrition_json is None
    aa = (nuevo.training_json or {}).get("applied_adjustments") or {}
    assert aa.get("period_index") == 1
    detalles = {(i.get("area"), i.get("detail")) for i in aa.get("items", [])}
    assert ("dieta", "No aplicado: este plan no incluye dieta") in detalles
    # El ajuste de carga sí se aplicó sobre el entreno real (+2,5 kg).
    ex_row = nuevo.training_json["sessions"][0]["exercises"][0]
    assert ex_row["start_weight_hint_kg"] == 42.5
    db.close()


# ----------------------------------------------------- diet break real ---

@pytestmark_db
def test_diet_break_se_aplica_de_verdad():
    """La decisión diet_break del motor era solo texto: nadie subía las kcal.
    Ahora el plan adaptado queda a mantenimiento (TDEE), y el salto por diseño
    no dispara el tope ±15% de recalibración (no es un desmadre de la IA)."""
    from app.db import SessionLocal
    from app.services.adapt_plan import adapt_plan_from_feedback

    db = SessionLocal()
    c, plan, _ex = _nuevo_cliente_con_plan(db)
    _periodo_analizado(db, c, plan, {
        "plan_adjustments": [],
        "biweekly_decision": {"action": "diet_break",
                              "rationale": "Fatiga alta dos revisiones seguidas"},
    })
    db.commit()

    nuevo = adapt_plan_from_feedback(db, c.id)
    # = TDEE (±: reconcile deja las kcal ≡ Atwater de los macros redondeados).
    assert abs(nuevo.nutrition_json["target_kcal"] - 2200) <= 5
    items = nuevo.nutrition_json["applied_adjustments"]["items"]
    assert any("Diet break" in i["change"] and i["applied"] for i in items)
    # Sin retención: 1800→2200 es +22% pero viene del motor, no de la IA.
    assert nuevo.status == "published"
    db.close()


# ------------------------------------- aprender del feedback del entreno ---

@pytestmark_db
def test_cargas_calibradas_con_los_registros_del_cliente():
    """El plan adaptado arranca donde el cliente lo dejó: el peso sugerido se
    calibra con su ÚLTIMO registro real (mejor serie del último día, a 0,5 kg)."""
    from app.db import SessionLocal
    from app.models import DailyLog, WorkoutLog
    from app.services.adapt_plan import adapt_plan_from_feedback

    db = SessionLocal()
    c, plan, ex = _nuevo_cliente_con_plan(db)
    period = _periodo_analizado(db, c, plan, {"plan_adjustments": []})
    today = date.today()
    d1 = DailyLog(period_id=period.id, log_date=today - timedelta(days=5))
    d2 = DailyLog(period_id=period.id, log_date=today - timedelta(days=2))
    db.add_all([d1, d2]); db.flush()
    db.add_all([
        WorkoutLog(daily_log_id=d1.id, exercise_id=ex.id, set_number=1, reps=8, weight_kg=45),
        WorkoutLog(daily_log_id=d2.id, exercise_id=ex.id, set_number=1, reps=8, weight_kg=47.3),
        WorkoutLog(daily_log_id=d2.id, exercise_id=ex.id, set_number=2, reps=8, weight_kg=46),
    ])
    db.commit()

    nuevo = adapt_plan_from_feedback(db, c.id)
    ex_row = nuevo.training_json["sessions"][0]["exercises"][0]
    assert ex_row["start_weight_hint_kg"] == 47.5  # 47,3 redondeado a 0,5 kg
    items = nuevo.nutrition_json["applied_adjustments"]["items"]
    assert any("calibradas" in i["change"].lower() for i in items)
    db.close()


# --------------------------------------------- novedades en cristiano ---

@pytestmark_db
def test_novedades_sin_jerga_interna():
    """El cliente lee las Novedades: nada de «decisión determinista» ni claves
    de regla («dato_insuficiente») — el veto de kcal se explica en cristiano."""
    from app.db import SessionLocal
    from app.services.adapt_plan import _regla_legible, adapt_plan_from_feedback

    assert _regla_legible({"rule": "dato_insuficiente"}) == \
        "faltan datos de peso para decidir con garantías"
    assert "_" not in _regla_legible({"rule": "una_regla_nueva"})

    db = SessionLocal()
    c, plan, _ex = _nuevo_cliente_con_plan(db)
    _periodo_analizado(db, c, plan, {
        "plan_adjustments": [
            {"area": "dieta", "change": "Bajar calorías a 1600", "reason": "x"}],
        "biweekly_decision": {"action": "hold", "rule": "dato_insuficiente"},
    })
    db.commit()

    nuevo = adapt_plan_from_feedback(db, c.id)
    items = nuevo.nutrition_json["applied_adjustments"]["items"]
    texto = " ".join(f"{i.get('change')} {i.get('detail')} {i.get('reason')}" for i in items)
    assert "determinista" not in texto
    assert "dato_insuficiente" not in texto
    assert "no se tocan en esta revisión" in texto
    db.close()


# ------------------------------------------------- memoria de vetos IA ---

def test_memoria_de_vetos_del_validador(tmp_path, monkeypatch):
    """Lo que el validador frena se recuerda; si se REPITE, entra en el prompt
    de la siguiente generación como advertencia. Un veto único no (ruido)."""
    from app.config import settings
    from app.services.coach_lessons import record_ai_vetos, vetos_reference

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))

    record_ai_vetos(["violation: proteína por debajo del suelo", "aviso: otra cosa"])
    assert vetos_reference() == ""  # una sola vez: aún no es patrón
    record_ai_vetos(["violation: proteína por debajo del suelo"])
    ref = vetos_reference()
    assert "proteína por debajo del suelo" in ref
    assert "no los repitas" in ref
    assert "aviso: otra cosa" not in ref  # los avisos no vetan: no se acumulan


# ------------------------------------------- panel caído deja constancia ---

def test_panel_caido_deja_ambar_degradado(monkeypatch):
    """Si el panel §9 revienta entero, el plan no puede parecer 'aprobado sin
    más': el resumen queda en ÁMBAR con el hallazgo 'Revisión no ejecutada'."""
    from app.services import plan_review

    def _boom(*a, **k):
        raise RuntimeError("panel caído")

    monkeypatch.setattr(plan_review, "review_and_repair", _boom)
    nut = {"target_kcal": 2000, "macros": {}}
    out, summary = plan_review.review_generated_plan(nut, client=None, ctx=None)
    assert out is nut
    assert summary["color"] == "ambar"
    assert summary["degraded_reviewers"] == ["panel"]
    assert any("Revisión no ejecutada" in f["title"] for f in summary["findings"])


def test_plan_text_incluye_resumen_de_entreno():
    """Los roles del panel juzgaban la coherencia dieta↔entreno viendo SOLO la
    dieta: el render del plan lleva ahora el resumen del entrenamiento."""
    from app.services.plan_review import _plan_text

    nut = {"target_kcal": 2000, "tdee_kcal": 2400,
           "macros": {"protein_g": 150, "carbs_g": 200, "fat_g": 60}}
    tr = {"split_name": "Full body", "sessions": [
        {"day": "Lunes", "name": "A", "exercises": [{"sets": 3}, {"sets": 4}]}],
        "weekly_progression": [{"week": 1, "intent": "acumulación"}]}
    texto = _plan_text(nut, tr)
    assert "Entrenamiento: Full body" in texto
    assert "2 ejercicios, 7 series" in texto
    assert "sem 1: acumulación" in texto
    # Sin entreno, el render de siempre.
    assert "Entrenamiento" not in _plan_text(nut)


# ---------------------------------- adaptar no filtra la revisión sin enviar ---

@pytestmark_db
def test_adaptar_no_avisa_si_el_feedback_sigue_sin_enviar(monkeypatch):
    """El push/email de 'plan nuevo' al adaptar solo sale si el feedback de la
    revisión ya se ENVIÓ; con el borrador sin mandar, avisar filtraba la
    revisión por la puerta de atrás."""
    from app.db import SessionLocal
    from app.models import FeedbackDoc
    from app.services import plan_activation
    from app.services.adapt_plan import adapt_plan_from_feedback

    llamadas: list[bool] = []
    real = plan_activation.activate_plan

    def _espia(db, plan, *, notify=True):
        llamadas.append(notify)
        return real(db, plan, notify=False)

    monkeypatch.setattr(plan_activation, "activate_plan", _espia)

    db = SessionLocal()
    # Feedback en borrador (sent_at=None) → notify=False.
    c, plan, _ex = _nuevo_cliente_con_plan(db)
    p = _periodo_analizado(db, c, plan, {"plan_adjustments": []})
    db.add(FeedbackDoc(period_id=p.id, kind="biweekly", content_json={}))
    db.commit()
    adapt_plan_from_feedback(db, c.id)
    assert llamadas[-1] is False

    # Feedback ya ENVIADO → notify=True.
    c2, plan2, _ex2 = _nuevo_cliente_con_plan(db)
    p2 = _periodo_analizado(db, c2, plan2, {"plan_adjustments": []})
    db.add(FeedbackDoc(period_id=p2.id, kind="biweekly", content_json={},
                       sent_at=datetime.now(timezone.utc)))
    db.commit()
    adapt_plan_from_feedback(db, c2.id)
    assert llamadas[-1] is True
    db.close()


@pytestmark_db
def test_la_adaptacion_no_pisa_el_texto_que_lee_el_cliente():
    """`rationale` sale en el PDF como "Por qué este enfoque".

    La adaptación lo machacaba con un volcado interno («- [dieta] … — …», que
    además repite la tabla "Cambios de tu plan" de justo debajo) o con una
    instrucción para el coach («edita manualmente»), y el argumentario real del
    plan se perdía para siempre: del mes 2 en adelante el cliente no volvía a
    leer por qué su plan es como es.
    """
    from app.db import SessionLocal
    from app.services.adapt_plan import adapt_plan_from_feedback

    db = SessionLocal()
    c, plan, _ex = _nuevo_cliente_con_plan(db)
    original = ("Trabajamos con un déficit moderado para que pierdas grasa sin "
                "perder fuerza en los básicos.")
    plan.nutrition_json = {**plan.nutrition_json, "rationale": original}
    _periodo_analizado(db, c, plan, {"plan_adjustments": [
        {"area": "dieta", "change": "Bajar calorías un 5%", "reason": "ritmo lento"},
    ]})
    db.commit()

    nuevo = adapt_plan_from_feedback(db, c.id)
    texto = (nuevo.nutrition_json or {}).get("rationale") or ""
    assert original in texto, "el argumentario del plan no puede desaparecer"
    assert "[dieta]" not in texto and "manualmente" not in texto
    assert "revisión #1" in texto

    # Y sin ajustes tampoco se ensucia con instrucciones para el coach.
    c2, plan2, _ = _nuevo_cliente_con_plan(db)
    plan2.nutrition_json = {**plan2.nutrition_json, "rationale": original}
    _periodo_analizado(db, c2, plan2, {"plan_adjustments": []})
    db.commit()
    nuevo2 = adapt_plan_from_feedback(db, c2.id)
    texto2 = (nuevo2.nutrition_json or {}).get("rationale") or ""
    assert original in texto2 and "manualmente" not in texto2
    db.close()


@pytestmark_db
def test_la_lista_ligera_de_planes_no_arrastra_el_banco_ni_el_educativo():
    """La ficha pedía DOS veces todas las versiones del plan con sus cuatro
    JSONB completos para pintar una línea de kcal y el sello de la adaptación:
    varios MB por apertura en un cliente veterano."""
    import os

    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.security import create_access_token, hash_password
    from app.models import User

    db = SessionLocal()
    c, plan, _ex = _nuevo_cliente_con_plan(db)
    plan.nutrition_json = {
        **plan.nutrition_json,
        "meals": [{"slot": 1, "name": "Desayuno", "time": "08:00",
                   "target": {"kcal": 500}}],
        "meal_bank": {"mode": "flexible_7", "slots": [{"slot": 1, "options": [
            {"key": "A", "title": "Tortilla", "ingredients": [{"food": "Huevo", "grams": 120}],
             "macros": {"kcal": 500, "protein_g": 40, "carbs_g": 40, "fat_g": 15}}]}]},
        "applied_adjustments": {"period_index": 3, "items": []},
    }
    plan.education_json = {"pills": [{"topic": "Sueño", "for_client": "Duerme 8 h"}]}
    # La versión GORDA pasa a ser HISTÓRICA (llega el plan del mes siguiente):
    # es justo la que el panel no pinta nunca entera y la que arrastraba los
    # megas. El recorte se prueba por el camino REAL —el de por defecto—, que
    # es el único que quedó tras la fusión.
    plan.status = "superseded"
    from app.models import Plan as _Plan

    vigente = _Plan(client_id=c.id, month_index=2, version=1, status="published",
                    goal_type="fat_loss", nutrition_json={"target_kcal": 1800},
                    training_json=None, education_json=None)
    db.add(vigente)
    db.commit()
    cid = c.id
    db.close()

    usuario = os.environ.get("ADMIN_1_USER", "coach1")
    db = SessionLocal()
    try:
        from sqlalchemy import select

        if not db.scalar(select(User).where(User.username == usuario)):
            db.add(User(username=usuario, password_hash=hash_password("test")))
            db.commit()
    finally:
        db.close()
    auth = {"Authorization": f"Bearer {create_access_token(usuario)}"}

    with TestClient(app) as http:
        lista = http.get(f"/api/clients/{cid}/plans", headers=auth).json()
        completo = http.get(f"/api/clients/{cid}/plans?todo=true", headers=auth).json()

    # `todo=true` devuelve el histórico TAL CUAL (importar/exportar, depurar).
    viejo = next(p for p in completo if p["month_index"] == 1)
    assert viejo["nutrition_json"]["meal_bank"]["slots"], "el completo sigue entero"
    assert viejo["education_json"]
    # El plan VIGENTE nunca se recorta: el panel lo pinta entero.
    assert next(p for p in lista if p["month_index"] == 2)["nutrition_json"]

    n = next(p for p in lista if p["month_index"] == 1)
    assert "meal_bank" not in n["nutrition_json"] and n["education_json"] is None
    n = n["nutrition_json"]
    assert n["target_kcal"] == 1800 and n["macros"]["protein_g"] == 160
    assert len(n["meals"]) == 1 and n["meals"][0]["name"] == "Desayuno"
    assert n["applied_adjustments"]["period_index"] == 3

    # …y el recorte NO se persiste en la base (es una copia suelta).
    db = SessionLocal()
    try:
        from app.models import Plan

        assert (db.get(Plan, plan.id).nutrition_json or {}).get("meal_bank")
    finally:
        db.close()
