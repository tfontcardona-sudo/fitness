"""BACKTEST del sistema completo de asesorías: 5 clientes × 90 días.

Simula el ciclo real contra la API de verdad (FastAPI TestClient + Postgres),
con la IA sustituida por respuestas deterministas y el tiempo controlado día a
día (freezegun). Cada día se verifican INVARIANTES del workflow y del centro
de alertas; cualquier incumplimiento se registra y el script termina con
código de error.

Qué recorre (por cliente, objetivos distintos):
  alta → anamnesis → generar plan (IA, queda ACTIVO al momento — sin botón
  publicar) → período 1 se abre solo → diario+entreno en el portal → cierre
  quincenal (día 15) → alerta "generar feedback" → feedback (IA) → alertas
  "enviar feedback" + "adaptar" → adaptar (activo + comidas reescaladas) →
  enviar feedback → período siguiente se abre ESE día →
  … × 6 quincenas. Día 45+: alerta de objetivo; un cliente CAMBIA de objetivo
  (regeneración completa + archivo del plan anterior), dos la POSPONEN (y se
  comprueba que reaparece a los 45 días), y uno deja de registrar (alerta de
  inactividad que se apaga al volver).

Uso:  DATABASE_URL=postgresql+psycopg://... python -m scripts.backtest_workflow
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key-for-backtest")
os.environ.setdefault("JWT_SECRET", "backtest-secret")

from unittest.mock import patch

from fastapi.testclient import TestClient
from freezegun import freeze_time
from sqlalchemy import select

from app.db import SessionLocal, engine
from app.deps import get_current_user
from app.main import app
from app.models import Base, Client, Exercise, FeedbackDoc, Period, Plan, User
from app.routers.alerts import client_alerts
from app.services.ai.feedback import FeedbackAIOutput
from app.services.jobs import run_daily_maintenance

START = date(2026, 1, 5)
DAYS = 92
FAILS: list[str] = []
PASSES = [0]


def check(cond: bool, msg: str) -> None:
    if cond:
        PASSES[0] += 1
    else:
        FAILS.append(msg)
        print(f"  ✗ FALLO: {msg}")


# ------------------------------------------------------------ IA simulada ----

def fake_generate_monthly_plan(ctx, ai):
    """Plan determinista coherente con el objetivo y las kcal del backend."""
    db = SessionLocal()
    ex_ids = [e.id for e in db.scalars(select(Exercise).limit(4))]
    db.close()
    kcal = round(ctx.target_kcal)
    meals = ctx.meal_schedule or [
        {"slot": 1, "name": "Desayuno", "time": "08:00"},
        {"slot": 2, "name": "Comida", "time": "14:00"},
        {"slot": 3, "name": "Cena", "time": "21:00"},
    ]
    n = len(meals)
    nutrition = {
        "tdee_kcal": ctx.tdee, "target_kcal": kcal,
        "rationale": f"Plan {ctx.goal_type} sobre TDEE {ctx.tdee}.",
        "macros": {"protein_g": round(ctx.weight_kg * 2.0),
                   "carbs_g": round(kcal * 0.4 / 4), "fat_g": round(ctx.weight_kg * 0.9)},
        "meals": [{"slot": m["slot"], "name": m["name"], "time": m.get("time") or "12:00",
                   "target": {"kcal": round(kcal / n), "protein_g": round(ctx.weight_kg * 2.0 / n),
                              "carbs_g": round(kcal * 0.4 / 4 / n), "fat_g": round(ctx.weight_kg * 0.9 / n)}}
                  for m in meals],
        "supplements": [], "flexibility_rules": ["1 comida libre/semana"], "refeed_or_break": None,
        "meal_bank": {"mode": "flexible_7", "slots": [
            {"slot": m["slot"], "options": [{"key": "A", "title": f"Opción {m['name']}",
             "macros": {"kcal": round(kcal / n), "protein_g": 30, "carbs_g": 40, "fat_g": 15},
             "ingredients": [{"food": "arroz", "grams": 100, "household": "1 taza"}],
             "prep": "Cocinar", "prep_minutes": 10, "tags": []}]} for m in meals]},
    }
    training = {
        "split_name": "Torso/Pierna", "split_rationale": "4 días.",
        "weekly_progression": [
            {"week": w, "intent": i, "load_pct": p, "rir_target": "2", "volume_note": None}
            for w, i, p in ((1, "Base", 70), (2, "Progresión", 75), (3, "Pico", 80), (4, "Deload", 60))
        ],
        "sessions": [
            {"day": d, "name": f"Sesión {s}", "warmup": "Movilidad 5'", "cooldown": None,
             "exercises": [{"exercise_id": ex_ids[j % len(ex_ids)], "sets": 3, "rep_range": "8-10",
                            "rir": "2", "rest_sec": 120, "tempo": None,
                            "start_weight_hint_kg": 40.0 + 5 * j, "progression_rule": None,
                            "technique_cue": None, "biomech_cue": None}
                           for j in range(3)]}
            for s, d in enumerate(("Lunes", "Martes", "Jueves", "Viernes"), start=1)
        ],
        "cardio": {"daily_steps": 9000, "sessions": []},
        "deload_instructions": "Semana 4 suave.",
    }
    education = {"topics": []}

    class FakeGenerated:
        def to_persistable(self):
            return nutrition, training, education, []

    return FakeGenerated()


def fake_feedback_analysis(payload: dict, ai) -> FeedbackAIOutput:
    """Feedback determinista con ajustes que la adaptación puede aplicar."""
    idx = payload.get("periodo_index", 1)
    return FeedbackAIOutput(
        natural_analysis=f"Buen período #{idx}: progreso constante y adherencia sólida.",
        changes_bullets=["Subir proteína 10 g", "Subir cargas 2,5 kg"],
        plan_adjustments=[
            {"area": "dieta", "change": "Subir proteína +10 g", "reason": "Preservar masa magra."},
            {"area": "entreno", "change": "Subir +2.5 kg en básicos", "reason": "RIR alto registrado."},
        ],
        answers=None,
        next_objectives=["Mantener registro diario", "Dormir 7 h"],
        closing_message="Seguimos con el buen trabajo.",
    )


# ----------------------------------------------------------- utilidades ----

ANAMNESIS = {
    "sex": "male", "birth_date": "1990-05-01", "height_cm": 178,
    "start_weight_kg": 86, "goal_weight_kg": 78, "level": "intermediate",
    "training_days": 4, "session_max_min": 75, "training_place": "gym",
    "diet_mode": "flexible_7",
}

GOALS = ["fat_loss", "muscle_gain", "recomp", "maintenance", "injury_recovery"]
TREND = {"fat_loss": -0.08, "muscle_gain": +0.03, "recomp": -0.02,
         "maintenance": 0.0, "injury_recovery": -0.01}


def alerts_by_kind(tc: TestClient, cid: int) -> set[str]:
    r = tc.get("/api/alerts")
    assert r.status_code == 200, r.text
    return {a["kind"] for a in r.json()["alerts"] if a["client_id"] == cid}


def run() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    for i, name in enumerate(["Press banca", "Sentadilla", "Remo", "Peso muerto"], start=1):
        db.add(Exercise(canonical_name=name, movement_pattern="push", muscle_primary="pecho",
                        muscle_secondary=[], equipment=[], level_min=1, aliases=[],
                        contraindications=[], archived=False))
    db.commit()
    coach = User(username="coach", password_hash="x")
    db.add(coach)
    db.commit()
    db.close()

    app.dependency_overrides[get_current_user] = lambda: coach
    tc = TestClient(app)

    patches = [
        patch("app.services.ai.generator.generate_monthly_plan", fake_generate_monthly_plan),
        patch("app.services.ai.feedback.generate_feedback_analysis", fake_feedback_analysis),
        patch("app.services.feedback_service._write_feedback_doc", lambda *a, **k: "backtest/fake.docx"),
        patch("app.services.email_service.EmailService.send", lambda *a, **k: None),
        patch("app.services.ai.client.AIClient._raw_call",
              lambda *a, **k: "Lo conseguido hasta hoy\nProgreso sólido.\n\nSi continúa\nMás progreso.\n\nOpciones\n· Mantenimiento"),
    ]
    for p in patches:
        p.start()

    # CALENTAMIENTO fuera del tiempo congelado: pydantic construye los
    # validadores de cada ruta en su primera petición y freezegun (que
    # sustituye datetime.date) rompe esa construcción. Se recorre TODO el
    # flujo con un cliente desechable y se borra (RGPD) antes de congelar.
    r = tc.post("/api/clients", json={"full_name": "Warmup", "email": "w@bt.com"})
    wid = r.json()["client"]["id"]
    wtok = r.json()["links"]["portal_token"]
    tc.patch(f"/api/clients/{wid}", json=dict(ANAMNESIS, goal_type="fat_loss"))
    r = tc.post(f"/api/clients/{wid}/generate-plan?month_index=1")
    assert r.status_code == 200, f"warmup generate: {r.text[:200]}"
    r = tc.post(f"/api/plans/{r.json()['id']}/publish")
    assert r.status_code == 200, f"warmup publish: {r.text[:200]}"
    tc.get("/api/alerts"); tc.get("/api/clients"); tc.get("/openapi.json")
    tc.get(f"/api/p/{wtok}/state"); tc.get(f"/api/p/{wtok}/training")
    tc.put(f"/api/p/{wtok}/diary", json={"log_date": "2026-01-04", "weight_kg": 85})
    tc.post(f"/api/p/{wtok}/close", json={"closing_weight_kg": 85})  # 422: aún día 1 (vale)
    dbw = SessionLocal()
    wper = dbw.scalar(select(Period).where(Period.client_id == wid))
    assert wper is not None and wper.status == "open", "warmup: publicar debe abrir el período"
    dbw.close()
    tc.post(f"/api/clients/{wid}/goal-review/analysis")
    r = tc.delete(f"/api/clients/{wid}?confirm=Warmup")
    assert r.status_code in (200, 204), f"warmup delete: {r.status_code}"


    clients: list[dict] = []  # {id, token, goal, weight, changed_goal, snoozed_reappear_due}

    with freeze_time(START) as frozen:
        # ------- Día 0: alta + anamnesis + plan (ACTIVO al generarse) --------
        print(f"— Día 0 ({START}): alta de 5 clientes, plan activo al generarse")
        for i, goal in enumerate(GOALS):
            r = tc.post("/api/clients", json={"full_name": f"Cliente {goal}", "email": f"c{i}@bt.com"})
            assert r.status_code in (200, 201), r.text
            cid = r.json()["client"]["id"]
            token = r.json()["links"]["portal_token"]
            body = dict(ANAMNESIS, goal_type=goal)
            if i < 3:  # 3 declaran comidas, 2 lo delegan (null)
                body["meals_per_day"] = 3
                body["meal_schedule"] = [
                    {"slot": 1, "name": "Desayuno", "time": "08:00"},
                    {"slot": 2, "name": "Comida", "time": "14:00"},
                    {"slot": 3, "name": "Cena", "time": "21:00"},
                ]
            r = tc.patch(f"/api/clients/{cid}", json=body)
            assert r.status_code == 200, r.text
            check("create_plan" in alerts_by_kind(tc, cid), f"[{goal}] alerta de crear plan en onboarding")
            r = tc.post(f"/api/clients/{cid}/generate-plan?month_index=1")
            check(r.status_code == 200, f"[{goal}] generar plan: {r.status_code} {r.text[:120]}")
            plan_id = r.json()["id"]
            # SIN botón "Publicar": el plan queda ACTIVO en el momento de generarse
            check(r.json().get("status") == "published", f"[{goal}] plan ACTIVO al generarse")
            aks = alerts_by_kind(tc, cid)
            check(aks == set(), f"[{goal}] sin alertas tras generar (hay: {aks})")
            dbx = SessionLocal()
            per = dbx.scalar(select(Period).where(Period.client_id == cid))
            cl = dbx.get(Client, cid)
            check(per is not None and per.status == "open" and per.starts_on == START,
                  f"[{goal}] período 1 abierto hoy (per={per and (per.status, str(per.starts_on))})")
            check(cl.goal_started_on == START, f"[{goal}] goal_started_on fijado al activarse")
            pl = dbx.get(Plan, plan_id)
            check(pl.goal_type == goal, f"[{goal}] plan archiva su objetivo")
            check(pl.published_at is not None, f"[{goal}] published_at fijado")
            dbx.close()
            clients.append({"id": cid, "token": token, "goal": goal, "weight": 86.0,
                            "changed": False, "snoozed_on": None})

        # ---------------- Días 1..90 ----------------------------------------
        for day in range(1, DAYS + 1):
            today = START + timedelta(days=day)
            frozen.move_to(today)
            dbm = SessionLocal()
            run_daily_maintenance(dbm)
            dbm.close()

            for c in clients:
                cid, tok, goal = c["id"], c["token"], c["goal"]
                # estado del portal (día del período, can_close…)
                r = tc.get(f"/api/p/{tok}/state")
                check(r.status_code == 200, f"[{goal}] d{day} portal /state {r.status_code}")
                st = r.json()
                per = st.get("period")

                # El cliente "maintenance" deja de registrar los días 20-27
                skips = goal == "maintenance" and 20 <= day <= 27
                if per and per.get("status") == "open" and not skips:
                    c["weight"] = round(c["weight"] + TREND[goal], 2)
                    r = tc.put(f"/api/p/{tok}/diary", json={
                        "log_date": today.isoformat(), "weight_kg": c["weight"],
                        "sleep_hours": 7.5, "steps": "9000", "satiety_1_10": 7,
                        "water_liters": 2.5, "diet_adherence": "yes",
                        "energy_1_5": 4, "mood_1_5": 4, "fatigue_1_5": 2,
                    })
                    check(r.status_code == 200, f"[{goal}] d{day} diario {r.status_code} {r.text[:80]}")

                # Alerta de inactividad: aparece con el hueco y se apaga al volver
                if goal == "maintenance" and day == 26:
                    check("no_logs" in alerts_by_kind(tc, cid), f"[{goal}] d{day} alerta sin registros")
                if goal == "maintenance" and day == 29:
                    check("no_logs" not in alerts_by_kind(tc, cid), f"[{goal}] d{day} alerta se apaga al volver")

                # ---- Cierre quincenal cuando el portal lo permite ----
                if per and per.get("can_close") and per.get("status") == "open":
                    r = tc.post(f"/api/p/{tok}/close", json={
                        "closing_weight_kg": c["weight"], "closing_rating": 4,
                        "closing_feelings_json": {"energia": 4, "hambre": 4, "sueno": 4,
                                                  "recuperacion": 4, "animo": 4, "digestiones": 4},
                        "adherence_diet_0_10": 8, "adherence_training_0_10": 9,
                        "free_meals_count": 2, "closing_hardest": "Cenas",
                        "closing_questions": None, "closing_changes": None,
                        "closing_next_goal": None, "closing_waist_cm": None,
                        "closing_hip_cm": None, "closing_arm_cm": None, "closing_thigh_cm": None,
                    })
                    check(r.status_code == 200, f"[{goal}] d{day} cierre {r.status_code} {r.text[:100]}")
                    aks = alerts_by_kind(tc, cid)
                    check("generate_feedback" in aks, f"[{goal}] d{day} alerta generar feedback")
                    # No se abre período nuevo mientras el coach no responda
                    dbx = SessionLocal()
                    n_open = len(list(dbx.scalars(select(Period).where(
                        Period.client_id == cid, Period.status == "open"))))
                    dbx.close()
                    check(n_open == 0, f"[{goal}] d{day} sin período nuevo antes del feedback")

                    # El coach responde AL DÍA SIGUIENTE (flujo realista)
                    c["respond_on"] = today + timedelta(days=1)

                # ---- Respuesta del coach: feedback → adaptar → publicar → enviar
                if c.get("respond_on") == today:
                    c.pop("respond_on")
                    dbx = SessionLocal()
                    period = dbx.scalar(select(Period).where(Period.client_id == cid)
                                        .order_by(Period.period_index.desc()).limit(1))
                    dbx.close()
                    r = tc.post(f"/api/periods/{period.id}/feedback")
                    check(r.status_code == 200, f"[{goal}] d{day} feedback {r.status_code} {r.text[:100]}")
                    fb_id = r.json()["feedback_id"]
                    aks = alerts_by_kind(tc, cid)
                    check({"send_feedback", "adapt_plan"} <= aks,
                          f"[{goal}] d{day} alertas enviar+adaptar (hay {aks})")
                    # Regenerar feedback NO duplica documentos
                    r2 = tc.post(f"/api/periods/{period.id}/feedback")
                    dbx = SessionLocal()
                    n_docs = len(list(dbx.scalars(select(FeedbackDoc).where(
                        FeedbackDoc.period_id == period.id))))
                    dbx.close()
                    check(r2.status_code == 200 and n_docs == 1,
                          f"[{goal}] d{day} feedback regenerado sin duplicar ({n_docs} docs)")
                    # Adaptar: la versión adaptada queda ACTIVA al momento y las
                    # comidas/gramos del banco se REESCALAN a los totales nuevos
                    dbx = SessionLocal()
                    base_pub = dbx.scalar(select(Plan).where(
                        Plan.client_id == cid, Plan.status == "published")
                        .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1))
                    base_m = base_pub.nutrition_json["macros"]
                    base_prot = base_m["protein_g"]
                    # Tras proteína +10 g, las kcal se recomputan COHERENTES
                    # (4/4/9) desde los macros del plan adaptado.
                    kcal_esperadas = round((base_prot + 10) * 4
                                           + base_m["carbs_g"] * 4
                                           + base_m["fat_g"] * 9)
                    dbx.close()
                    r = tc.post(f"/api/clients/{cid}/adapt-plan")
                    check(r.status_code == 200, f"[{goal}] d{day} adaptar {r.status_code} {r.text[:100]}")
                    check(r.json().get("status") == "published",
                          f"[{goal}] d{day} plan adaptado ACTIVO al momento")
                    adapted_id = r.json()["id"]
                    dbx = SessionLocal()
                    anut = dbx.get(Plan, adapted_id).nutrition_json
                    dbx.close()
                    # Proteína +10 g → kcal coherentes (+40) y comidas cuadradas
                    check(anut["macros"]["protein_g"] == base_prot + 10,
                          f"[{goal}] d{day} proteína +10 g aplicada")
                    check(anut["target_kcal"] == kcal_esperadas,
                          f"[{goal}] d{day} kcal coherentes 4/4/9 tras el ajuste "
                          f"({anut['target_kcal']} vs {kcal_esperadas})")
                    meal_prot = sum(m["target"]["protein_g"] for m in anut.get("meals", []))
                    check(meal_prot == anut["macros"]["protein_g"],
                          f"[{goal}] d{day} comidas CUADRAN con el total "
                          f"(P comidas {meal_prot} vs {anut['macros']['protein_g']})")
                    meal_kcal = sum(m["target"]["kcal"] for m in anut.get("meals", []))
                    check(meal_kcal == anut["target_kcal"],
                          f"[{goal}] d{day} kcal de comidas cuadran "
                          f"({meal_kcal} vs {anut['target_kcal']})")
                    check(bool(anut.get("meal_bank", {}).get("slots")),
                          f"[{goal}] d{day} banco de comidas presente tras reescalar")
                    # Idempotencia: re-adaptar a la MISMA revisión → aviso claro, no acumula
                    r = tc.post(f"/api/clients/{cid}/adapt-plan")
                    check(r.status_code == 409 and "ya está adaptado" in r.text,
                          f"[{goal}] d{day} re-adaptar avisa sin acumular ({r.status_code})")
                    dbx = SessionLocal()
                    prot2 = dbx.get(Plan, adapted_id).nutrition_json["macros"]["protein_g"]
                    dbx.close()
                    check(prot2 == base_prot + 10,
                          f"[{goal}] d{day} macros intactos tras re-adaptar (P {prot2})")
                    r = tc.post(f"/api/feedback/{fb_id}/send")
                    check(r.status_code == 200, f"[{goal}] d{day} enviar feedback")
                    # Al enviar: ciclo nuevo abierto HOY y cero alertas
                    dbx = SessionLocal()
                    newp = dbx.scalar(select(Period).where(Period.client_id == cid)
                                      .order_by(Period.period_index.desc()).limit(1))
                    dbx.close()
                    check(newp.status == "open" and newp.starts_on == today,
                          f"[{goal}] d{day} período nuevo abierto hoy ({newp.starts_on})")
                    aks = alerts_by_kind(tc, cid)
                    expected_rest = {"goal_review"} if day >= 45 else set()
                    check(aks - expected_rest == set(),
                          f"[{goal}] d{day} ciclo cerrado sin alertas (hay {aks})")

                # ---- Día 45+: alerta de objetivo y las tres reacciones ----
                if day == 46 and not c["changed"]:
                    aks = alerts_by_kind(tc, cid)
                    check("goal_review" in aks, f"[{goal}] d{day} alerta 45 días de objetivo")
                    if goal == "fat_loss":
                        # CAMBIO de objetivo completo: análisis → cambiar → regenerar
                        r = tc.post(f"/api/clients/{cid}/goal-review/analysis")
                        check(r.status_code == 200 and len(r.json()["text"]) > 40,
                              f"[{goal}] d{day} análisis de etapa")
                        r = tc.post(f"/api/clients/{cid}/change-goal", json={"goal_type": "recomp"})
                        check(r.status_code == 200, f"[{goal}] d{day} cambiar objetivo")
                        check("goal_review" not in alerts_by_kind(tc, cid),
                              f"[{goal}] d{day} alerta fuera tras cambiar")
                        r = tc.post(f"/api/clients/{cid}/generate-plan?month_index=2")
                        check(r.status_code == 200, f"[{goal}] d{day} regenerar plan {r.text[:100]}")
                        new_plan = r.json()["id"]
                        check(r.json().get("status") == "published",
                              f"[{goal}] d{day} plan nuevo ACTIVO al regenerarse")
                        dbx = SessionLocal()
                        np_ = dbx.get(Plan, new_plan)
                        cl = dbx.get(Client, cid)
                        old = dbx.scalar(select(Plan).where(Plan.client_id == cid, Plan.month_index == 1)
                                         .order_by(Plan.version.desc()).limit(1))
                        dbx.close()
                        check(np_.goal_type == "recomp", f"[{goal}] plan nuevo archiva objetivo nuevo")
                        check(old.goal_type == "fat_loss", f"[{goal}] plan antiguo conserva su objetivo")
                        check(cl.goal_started_on == today, f"[{goal}] etapa nueva desde hoy")
                        c["goal"] = "recomp"
                        c["changed"] = True
                        # el portal debe servir el plan NUEVO
                        r = tc.get(f"/api/p/{tok}/training")
                        check(r.status_code == 200 and (r.json().get("sessions") or []),
                              f"[recomp] d{day} portal sirve el plan nuevo")
                    elif goal in ("muscle_gain", "recomp"):
                        r = tc.post(f"/api/clients/{cid}/goal-review/snooze")
                        check(r.status_code == 200, f"[{goal}] d{day} posponer objetivo")
                        check("goal_review" not in alerts_by_kind(tc, cid),
                              f"[{goal}] d{day} alerta fuera tras posponer")
                        c["snoozed_on"] = today

                # La alerta pospuesta REAPARECE 45 días después
                if c.get("snoozed_on") and (today - c["snoozed_on"]).days == 45:
                    check("goal_review" in alerts_by_kind(tc, cid),
                          f"[{c['goal']}] d{day} alerta de objetivo reaparece tras 45 días")
                    c["snoozed_on"] = None

        # ---------------- Cierre: métricas globales -------------------------
        print(f"\n— Día {DAYS}: resumen final")
        dbx = SessionLocal()
        for c in clients:
            cl = dbx.get(Client, c["id"])
            pers = list(dbx.scalars(select(Period).where(Period.client_id == c["id"])
                                    .order_by(Period.period_index)))
            plans = list(dbx.scalars(select(Plan).where(Plan.client_id == c["id"])))
            n_analyzed = sum(1 for p in pers if p.status == "analyzed")
            print(f"  {cl.full_name}: {len(pers)} períodos ({n_analyzed} analizados), "
                  f"{len(plans)} planes, estado {cl.status}, objetivo {cl.goal_type}")
            check(len(pers) >= 5, f"[{c['goal']}] completó ≥5 quincenas ({len(pers)})")
            check(all(pers[i].period_index == i + 1 for i in range(len(pers))),
                  f"[{c['goal']}] índices de período consecutivos")
            # nunca dos períodos abiertos
            check(sum(1 for p in pers if p.status == "open") <= 1,
                  f"[{c['goal']}] como mucho un período abierto")
            # un feedback por período analizado
            for p in pers:
                if p.status == "analyzed":
                    n_docs = len(list(dbx.scalars(select(FeedbackDoc).where(FeedbackDoc.period_id == p.id))))
                    check(n_docs == 1, f"[{c['goal']}] período {p.period_index}: {n_docs} feedbacks (esperado 1)")
        dbx.close()

    for p in patches:
        p.stop()

    print(f"\n{'='*60}\nRESULTADO: {PASSES[0]} comprobaciones OK · {len(FAILS)} fallos")
    for f in FAILS:
        print(f"  ✗ {f}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    run()
