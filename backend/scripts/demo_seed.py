"""Datos de DEMOSTRACIÓN para enseñar el producto a un cliente (Professional).

Monta un escenario VIVO e idempotente (re-ejecutar lo reinicia) sin gastar IA.
TRES clientes = TRES fases del ciclo, para enseñar todas las funcionalidades:

  · Marta Serra  — Génesis.99 A MITAD de seguimiento (día 8 de 14): plan
    publicado con 3 opciones por comida + entrenamiento, diario con el peso
    bajando, comidas elegidas y entrenos con series. El portal vivo.
  · Carlos Bosch — Génesis.99 con la REVISIÓN QUINCENAL CERRADA ayer:
    14 días de diario, cierre completo (peso final, perímetros, sensaciones,
    adherencia) y el cliente en review_pending → notificación al coach y
    "Resumen" de métricas listo para enseñar (sin IA).
  · Jordi Puig   — ENTRENO PERSONAL (sesiones presenciales): plan de solo
    entrenamiento, día 5, dos sesiones registradas, pagado en el centro.

(El alta de un cliente NUEVO —la cola de anamnesis— se enseña EN VIVO en la
demo creando a "Laura Vidal" desde el panel: es parte del guión, ver DEMO.md.)

Uso (con la BD migrada y sembrada, p. ej. dentro del contenedor):

    docker compose exec api python scripts/demo_seed.py

Los clientes de demo viven en @demo.local: el script borra y recrea SOLO esos
(nunca toca clientes reales). Imprime al final los enlaces del portal.
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, or_, select, update  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import (  # noqa: E402
    ChangeRequest, Client, DailyLog, EmailLog, Exercise, FeedbackDoc, Period,
    Plan, ProgressPhoto, PushSubscription, VideoCall, WorkoutLog,
)
from app.security import new_portal_token  # noqa: E402

DEMO_DOMAIN = "@demo.local"


# ------------------------------------------------------------------ limpieza --
def wipe_demo_clients(db) -> int:
    """Borra los clientes de demo con TODAS sus filas dependientes (mismo orden
    que la limpieza de la suite de tests)."""
    ids = list(db.scalars(select(Client.id).where(Client.email.ilike(f"%{DEMO_DOMAIN}"))))
    if not ids:
        return 0
    period_ids = list(db.scalars(select(Period.id).where(Period.client_id.in_(ids))))
    if period_ids:
        daily_ids = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id.in_(period_ids))))
        if daily_ids:
            db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(daily_ids)))
            db.execute(delete(DailyLog).where(DailyLog.id.in_(daily_ids)))
        db.execute(delete(FeedbackDoc).where(FeedbackDoc.period_id.in_(period_ids)))
    db.execute(delete(ProgressPhoto).where(ProgressPhoto.client_id.in_(ids)))
    db.execute(delete(PushSubscription).where(PushSubscription.client_id.in_(ids)))
    db.execute(delete(VideoCall).where(VideoCall.client_id.in_(ids)))
    db.execute(delete(Period).where(Period.client_id.in_(ids)))
    db.execute(delete(Plan).where(Plan.client_id.in_(ids)))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id.in_(ids)))
    db.execute(update(EmailLog).where(EmailLog.client_id.in_(ids)).values(client_id=None))
    db.execute(delete(Client).where(Client.id.in_(ids)))
    db.commit()
    return len(ids)


# ------------------------------------------------------------------ nutrición --
def _opt(key: str, title: str, ingredients: list[tuple[str, int, str]],
         prep: str, minutes: int, macros: dict) -> dict:
    return {
        "key": key, "title": title,
        "ingredients": [{"food": f, "grams": g, "household": h} for f, g, h in ingredients],
        "prep": prep, "prep_minutes": minutes, "macros": macros, "tags": [],
    }


def _macros(p: int, c: int, f: int) -> dict:
    """Macros con kcal Atwater EXACTAS (4/4/9): el editor y el Revisor 0 cuadran."""
    return {"kcal": 4 * p + 4 * c + 9 * f, "protein_g": p, "carbs_g": c, "fat_g": f}


def build_nutrition(targets: list[tuple[int, int, int]], tdee: int, bmr: int,
                    rationale: str) -> dict:
    """Plan de nutrición realista y CUADRADO: Σ comidas = día, kcal = 4/4/9,
    3 opciones por toma (método de la casa). `targets` = (P, C, G) por toma."""
    t1, t2, t3, t4 = (_macros(*t) for t in targets)
    meals = [
        {"slot": 1, "name": "Desayuno", "time": "08:00", "target": t1},
        {"slot": 2, "name": "Comida", "time": "14:00", "target": t2},
        {"slot": 3, "name": "Merienda", "time": "18:00", "target": t3},
        {"slot": 4, "name": "Cena", "time": "21:30", "target": t4},
    ]
    slots = [
        {"slot": 1, "fmt": "options", "options": [
            _opt("A", "Yogur griego con avena, arándanos y nueces",
                 [("Yogur griego 0%", 250, "1 tarrina grande"), ("Copos de avena", 45, "5 cucharadas"),
                  ("Arándanos", 80, "1 puñado grande"), ("Nueces", 12, "3 nueces")],
                 "Mezcla y deja reposar 5 minutos.", 5, dict(t1)),
            _opt("B", "Tostadas integrales con pavo y aguacate",
                 [("Pan integral", 70, "2 rebanadas"), ("Fiambre de pavo", 80, "4 lonchas"),
                  ("Aguacate", 45, "1/4 pieza"), ("Tomate", 60, "1/2 tomate")],
                 "Tuesta el pan y monta.", 6, dict(t1)),
            _opt("C", "Tortilla con pan integral y plátano",
                 [("Huevo entero", 60, "1 huevo"), ("Claras de huevo", 180, "5 claras"),
                  ("Pan integral", 50, "1 rebanada y media"), ("Plátano", 100, "1 pieza")],
                 "Tortilla a la plancha con una gota de AOVE.", 8, dict(t1)),
        ], "weekly_examples": ["Yogur con avena", "Tostadas de pavo", "Tortilla y fruta",
                               "Yogur con avena", "Tostadas de pavo", "Tortilla y fruta", "Yogur con avena"]},
        {"slot": 2, "fmt": "options", "options": [
            _opt("A", "Pollo a la plancha con arroz y verduras",
                 [("Pechuga de pollo", 160, "1 filete grande"), ("Arroz blanco", 70, "70 g en crudo"),
                  ("Verduras salteadas", 200, "1 plato"), ("Aceite de oliva virgen extra", 12, "1 cucharada")],
                 "Plancha y salteado; el arroz, hervido.", 20, dict(t2)),
            _opt("B", "Salmón al horno con patata y ensalada",
                 [("Salmón", 150, "1 lomo"), ("Patata", 280, "2 patatas medianas"),
                  ("Ensalada verde", 150, "1 bol"), ("Aceite de oliva virgen extra", 10, "1 cucharada")],
                 "Horno 180º, 15 minutos.", 25, dict(t2)),
            _opt("C", "Garbanzos salteados con atún",
                 [("Garbanzos cocidos", 220, "1 bote pequeño"), ("Atún al natural", 120, "2 latas"),
                  ("Pimiento y cebolla", 120, "1 plato"), ("Aceite de oliva virgen extra", 12, "1 cucharada")],
                 "Saltea todo junto 8 minutos.", 12, dict(t2)),
        ], "weekly_examples": ["Pollo con arroz", "Salmón con patata", "Garbanzos con atún",
                               "Pollo con arroz", "Salmón con patata", "Garbanzos con atún", "Pollo con arroz"]},
        {"slot": 3, "fmt": "options", "options": [
            _opt("A", "Queso fresco batido con fruta",
                 [("Queso fresco batido 0%", 250, "1 tarrina"), ("Manzana", 150, "1 pieza"),
                  ("Almendras", 10, "8 almendras")],
                 "Trocea la fruta y mezcla.", 3, dict(t3)),
            _opt("B", "Sándwich de atún",
                 [("Pan integral", 60, "2 rebanadas"), ("Atún al natural", 80, "1 lata y media"),
                  ("Tomate", 50, "rodajas")],
                 "Monta el sándwich.", 5, dict(t3)),
            _opt("C", "Batido de proteína con plátano",
                 [("Proteína de suero", 25, "1 cazo"), ("Plátano", 120, "1 pieza"),
                  ("Leche semidesnatada", 200, "1 vaso")],
                 "Batidora, 1 minuto.", 2, dict(t3)),
        ], "weekly_examples": ["Queso batido y fruta", "Sándwich de atún", "Batido y plátano",
                               "Queso batido y fruta", "Sándwich de atún", "Batido y plátano", "Queso batido y fruta"]},
        {"slot": 4, "fmt": "options", "options": [
            _opt("A", "Merluza con boniato y brócoli",
                 [("Merluza", 180, "1 lomo grande"), ("Boniato", 200, "1 pieza mediana"),
                  ("Brócoli", 200, "1 plato"), ("Aceite de oliva virgen extra", 12, "1 cucharada")],
                 "Plancha y vapor.", 20, dict(t4)),
            _opt("B", "Tacos de pavo con tortillas integrales",
                 [("Pavo picado", 160, "1 bandeja pequeña"), ("Tortillas integrales", 80, "2 tortillas"),
                  ("Pimiento y cebolla", 150, "1 plato"), ("Aguacate", 40, "1/4 pieza")],
                 "Saltea el pavo con las verduras y monta.", 15, dict(t4)),
            _opt("C", "Revuelto de huevos con champiñones y pan",
                 [("Huevo entero", 120, "2 huevos"), ("Claras de huevo", 100, "3 claras"),
                  ("Champiñones", 200, "1 plato"), ("Pan integral", 50, "1 rebanada y media")],
                 "Revuelto a fuego medio.", 12, dict(t4)),
        ], "weekly_examples": ["Merluza con boniato", "Tacos de pavo", "Revuelto y pan",
                               "Merluza con boniato", "Tacos de pavo", "Revuelto y pan", "Merluza con boniato"]},
    ]
    P = sum(t[0] for t in targets); C = sum(t[1] for t in targets); F = sum(t[2] for t in targets)
    total = _macros(P, C, F)
    return {
        "target_kcal": total["kcal"], "tdee_kcal": tdee, "bmr_kcal": bmr,
        "macros": {"protein_g": P, "carbs_g": C, "fat_g": F},
        "meals": meals,
        "meal_bank": {"mode": "flexible_7", "slots": slots},
        "supplements": [
            {"name": "Creatina monohidrato", "dose": "5 g", "timing": "diaria, con cualquier comida"},
            {"name": "Omega 3", "dose": "2 g", "timing": "con la comida principal"},
        ],
        "rationale": rationale,
    }


def marta_nutrition() -> dict:
    # P130 C175 G60 → 1760 kcal (déficit 20% sobre TDEE 2200)
    return build_nutrition([(30, 45, 12), (45, 60, 20), (20, 30, 8), (35, 40, 20)],
                           tdee=2200, bmr=1450,
                           rationale="Déficit moderado priorizando proteína y adherencia.")


def carlos_nutrition() -> dict:
    # P160 C210 G70 → 2110 kcal (recomp: déficit suave sobre TDEE 2250)
    return build_nutrition([(38, 55, 15), (55, 70, 22), (25, 35, 10), (42, 50, 23)],
                           tdee=2250, bmr=1650,
                           rationale="Recomposición: déficit suave con proteína alta.")


def check_cuadre(nutrition: dict) -> None:
    """El plan de demo debe CUADRAR como uno real (editor y Revisor 0 en paz)."""
    m = nutrition["macros"]
    assert nutrition["target_kcal"] == 4 * m["protein_g"] + 4 * m["carbs_g"] + 9 * m["fat_g"]
    for axis in ("protein_g", "carbs_g", "fat_g", "kcal"):
        suma = sum(mm["target"][axis] for mm in nutrition["meals"])
        objetivo = nutrition["target_kcal"] if axis == "kcal" else m[axis]
        assert suma == objetivo, f"descuadre en {axis}: {suma} != {objetivo}"
    for s in nutrition["meal_bank"]["slots"]:
        target = next(mm["target"] for mm in nutrition["meals"] if mm["slot"] == s["slot"])
        assert len(s["options"]) == 3, f"slot {s['slot']}: deben ser 3 opciones"
        for o in s["options"]:
            assert o["macros"] == target, f"slot {s['slot']} opción {o['key']}: macros ≠ objetivo"


# --------------------------------------------------------------- entrenamiento --
def _ex_id(db, *candidates: str) -> int:
    """ID del primer ejercicio de la biblioteca que exista de la lista (por
    nombre canónico); si ninguno, el primero de la biblioteca (nunca rompe)."""
    for name in candidates:
        ex = db.scalar(select(Exercise).where(Exercise.canonical_name == name))
        if ex:
            return ex.id
    return db.scalars(select(Exercise.id).order_by(Exercise.id)).first()


def marta_training(db) -> dict:
    def e(cands, sets, reps, rir, rest, cue):
        return {"exercise_id": _ex_id(db, *cands), "sets": sets, "rep_range": reps,
                "rir": rir, "rest_sec": rest, "technique_cue": cue}

    return {
        "split_name": "Full body · 3 días",
        "split_rationale": "Tres estímulos semanales por grupo con recuperación amplia: "
                           "máxima eficiencia para 3 días de gimnasio.",
        "sessions": [
            {"day": "Lunes", "name": "Full body A",
             "warmup": "5' bici suave + movilidad de cadera y hombro.",
             "exercises": [
                 e(["Sentadilla con barra", "Sentadilla goblet"], 4, "6-8", 2, 150,
                   "Baja controlando, rodillas siguiendo la punta del pie."),
                 e(["Press banca con barra", "Press banca con mancuernas"], 4, "6-8", 2, 150,
                   "Escápulas retraídas, pies firmes."),
                 e(["Remo con barra", "Remo en máquina"], 3, "8-10", 2, 120,
                   "Tira con los codos, sin balanceo."),
                 e(["Press militar de pie con barra", "Press de hombros con mancuernas sentado"],
                   3, "8-10", 2, 120, "Core firme, sin arquear la lumbar."),
                 e(["Plancha abdominal", "Plancha"], 3, "30-45s", 0, 60,
                   "Cadera alineada, aprieta el glúteo."),
             ],
             "cooldown": "Estiramiento global 5 minutos."},
            {"day": "Miércoles", "name": "Full body B",
             "warmup": "5' remo suave + movilidad torácica.",
             "exercises": [
                 e(["Peso muerto rumano con barra", "Peso muerto rumano con mancuernas"],
                   4, "6-8", 2, 150, "Cadera atrás, espalda neutra."),
                 e(["Jalón al pecho", "Dominadas asistidas"], 4, "8-10", 2, 120,
                   "Pecho arriba, tira hacia la clavícula."),
                 e(["Press inclinado con mancuernas", "Press de pecho en máquina"],
                   3, "8-10", 2, 120, "Recorrido completo sin rebotar."),
                 e(["Zancadas con mancuernas", "Prensa de piernas"], 3, "10-12", 2, 120,
                   "Paso largo, rodilla estable."),
                 e(["Curl de bíceps con barra", "Curl de bíceps con mancuernas"], 2, "10-12", 1, 90,
                   "Codos pegados al cuerpo."),
             ],
             "cooldown": "Estiramiento de isquios y dorsal."},
            {"day": "Viernes", "name": "Full body C",
             "warmup": "5' cinta + activación de glúteo con banda.",
             "exercises": [
                 e(["Prensa de piernas", "Sentadilla búlgara"], 4, "8-10", 2, 150,
                   "Baja profundo sin despegar el sacro."),
                 e(["Press banca con mancuernas", "Flexiones"], 3, "8-10", 2, 120,
                   "Control en la bajada."),
                 e(["Remo en polea baja", "Remo con mancuerna a una mano"], 3, "10-12", 2, 120,
                   "Pausa de un segundo en la contracción."),
                 e(["Elevaciones laterales con mancuernas", "Elevaciones laterales en polea"],
                   3, "12-15", 1, 90, "Sube hasta la altura del hombro, sin impulso."),
                 e(["Curl femoral tumbado", "Curl femoral sentado"], 3, "10-12", 2, 90,
                   "Tempo controlado 2-0-2."),
             ],
             "cooldown": "Estiramiento de cuádriceps y gemelo."},
        ],
        "weekly_progression": [
            {"week": 1, "intent": "Adaptación", "load_pct": 100, "rir_target": "2-3",
             "volume_note": "Aprende los pesos de referencia."},
            {"week": 2, "intent": "Progresión", "load_pct": 102.5, "rir_target": "2",
             "volume_note": "Sube carga si cierras todas las series."},
            {"week": 3, "intent": "Carga", "load_pct": 105, "rir_target": "1-2",
             "volume_note": "Semana fuerte: prioriza técnica."},
            {"week": 4, "intent": "Descarga", "load_pct": 90, "rir_target": "3-4",
             "volume_note": "Mitad de series: recupera para el mes 2."},
        ],
        "cardio": {"daily_steps": 9000,
                   "sessions": [{"type": "liss", "minutes": 30, "times_per_week": 2,
                                 "notes": "Zona 2: cinta inclinada o bici."}]},
        "deload_instructions": "Semana 4: misma rutina con la mitad de series y RIR 3-4.",
    }


def jordi_training(db) -> dict:
    t = marta_training(db)
    t["split_name"] = "Upper/Lower · 4 días"
    t["split_rationale"] = ("Cuatro sesiones presenciales con tu entrenador: dos de torso "
                            "y dos de pierna, con progresión quincenal.")
    return t


# ------------------------------------------------------------------- clientes --
def crear_marta(db) -> Client:
    hoy = date.today()
    c = Client(
        full_name="Marta Serra", email=f"marta{DEMO_DOMAIN}", phone="+34 600 111 222",
        package_tier="full", billing_period="1m", status="active",
        payment_status="paid", paid_at=datetime.now(timezone.utc) - timedelta(days=9),
        sex="female", birth_date=date(1992, 4, 12), height_cm=166,
        start_weight_kg=74.8, current_weight_kg=73.9, body_fat_pct=27.0,
        goal_type="fat_loss", goal_weight_kg=68.0, level="intermediate",
        training_days=3, session_max_min=60, training_place="gym",
        daily_activity_level="light", meals_per_day=4,
        food_allergies=[], food_dislikes=["marisco"], food_likes=["pollo", "yogur", "salmón"],
        lifestyle_notes="Trabajo de oficina; camina a diario; duerme ~7 h.",
        sport_history="2 años de gimnasio con constancia irregular.",
        diet_mode="flexible_7", portal_token="pendiente",
        plan_notice_pending=False,
    )
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)

    nutrition = marta_nutrition()
    check_cuadre(nutrition)
    plan = Plan(
        client_id=c.id, month_index=1, version=1, status="published",
        nutrition_json=nutrition, training_json=marta_training(db),
        education_json=None, guardrail_flags=[], generated_by="demo",
        goal_type="fat_loss",
        published_at=datetime.now(timezone.utc) - timedelta(days=9),
    )
    db.add(plan)
    db.flush()

    starts = hoy - timedelta(days=7)  # día 8 de 14
    period = Period(client_id=c.id, plan_id=plan.id, period_index=1,
                    starts_on=starts, ends_on=starts + timedelta(days=13), status="open")
    db.add(period)
    db.flush()

    pesos = [74.8, 74.6, 74.7, 74.4, 74.2, 74.3, 74.0, 73.9]
    adherencia = ["yes", "yes", "partial", "yes", "yes", "yes", "partial", "yes"]
    for i in range(8):
        d = DailyLog(
            period_id=period.id, log_date=starts + timedelta(days=i),
            weight_kg=pesos[i], sleep_hours=7.0 + (i % 3) * 0.5,
            steps=str(8200 + i * 350), water_liters=2.5,
            diet_adherence=adherencia[i], energy_1_5=4, mood_1_5=4, fatigue_1_5=2,
            chosen_options_json={"1": "A", "2": ["A", "B", "C"][i % 3], "3": "C", "4": ["A", "B"][i % 2]},
        )
        db.add(d)
        db.flush()
        # Lunes/miércoles/viernes: series registradas de la sesión del día
        if i in (0, 2, 4, 7):
            sess = plan.training_json["sessions"][(0, 1, 2, 0)[(0, 2, 4, 7).index(i)]]
            for ex in sess["exercises"][:3]:
                base = 40.0 + (ex["exercise_id"] % 5) * 5
                for set_n in range(1, 4):
                    db.add(WorkoutLog(daily_log_id=d.id, exercise_id=ex["exercise_id"],
                                      set_number=set_n, reps=8,
                                      weight_kg=base + (2.5 if i >= 4 else 0.0), rpe=8.0))
    db.commit()
    return c


def crear_jordi(db) -> Client:
    hoy = date.today()
    c = Client(
        full_name="Jordi Puig", email=f"jordi{DEMO_DOMAIN}", phone="+34 600 333 444",
        package_tier="train", billing_period="1m", status="active",
        payment_status="paid", paid_at=datetime.now(timezone.utc) - timedelta(days=6),
        sex="male", birth_date=date(1988, 9, 3), height_cm=179,
        start_weight_kg=86.0, current_weight_kg=86.4, body_fat_pct=19.0,
        goal_type="muscle_gain", level="intermediate",
        training_days=4, session_max_min=75, training_place="gym",
        daily_activity_level="active", portal_token="pendiente",
        sport_history="Pádel semanal; vuelve al gimnasio tras dos años.",
        plan_notice_pending=False,
    )
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)

    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json=None, training_json=jordi_training(db),
                education_json=None, guardrail_flags=[], generated_by="demo",
                goal_type="muscle_gain",
                published_at=datetime.now(timezone.utc) - timedelta(days=6))
    db.add(plan)
    db.flush()

    starts = hoy - timedelta(days=4)  # día 5 de 14
    period = Period(client_id=c.id, plan_id=plan.id, period_index=1,
                    starts_on=starts, ends_on=starts + timedelta(days=13), status="open")
    db.add(period)
    db.flush()
    for i in (0, 2):
        d = DailyLog(period_id=period.id, log_date=starts + timedelta(days=i),
                     energy_1_5=4, mood_1_5=4)
        db.add(d)
        db.flush()
        sess = plan.training_json["sessions"][i % len(plan.training_json["sessions"])]
        for ex in sess["exercises"][:4]:
            base = 60.0 + (ex["exercise_id"] % 4) * 10
            for set_n in range(1, 5):
                db.add(WorkoutLog(daily_log_id=d.id, exercise_id=ex["exercise_id"],
                                  set_number=set_n, reps=8, weight_kg=base, rpe=7.5))
    db.commit()
    return c


def crear_carlos(db) -> Client:
    """Génesis.99 con la revisión quincenal CERRADA ayer: el coach tiene la
    notificación viva y el "Resumen" de métricas listo (sin IA)."""
    hoy = date.today()
    c = Client(
        full_name="Carlos Bosch", email=f"carlos{DEMO_DOMAIN}", phone="+34 600 555 666",
        package_tier="full", billing_period="1m", status="review_pending",
        payment_status="paid", paid_at=datetime.now(timezone.utc) - timedelta(days=16),
        sex="male", birth_date=date(1985, 1, 22), height_cm=181,
        start_weight_kg=84.6, current_weight_kg=83.4, body_fat_pct=21.0,
        goal_type="recomp", goal_weight_kg=82.0, level="intermediate",
        training_days=4, session_max_min=70, training_place="gym",
        daily_activity_level="light", meals_per_day=4,
        food_allergies=[], food_dislikes=[], food_likes=["arroz", "salmón"],
        lifestyle_notes="Turnos de oficina; entrena al salir del trabajo.",
        sport_history="Años de gimnasio; base técnica sólida.",
        diet_mode="flexible_7", portal_token="pendiente",
        plan_notice_pending=False,
    )
    db.add(c)
    db.flush()
    c.portal_token = new_portal_token(c.id)

    nutrition = carlos_nutrition()
    check_cuadre(nutrition)
    plan = Plan(client_id=c.id, month_index=1, version=1, status="published",
                nutrition_json=nutrition, training_json=jordi_training(db),
                education_json=None, guardrail_flags=[], generated_by="demo",
                goal_type="recomp",
                published_at=datetime.now(timezone.utc) - timedelta(days=16))
    db.add(plan)
    db.flush()

    starts = hoy - timedelta(days=15)          # período COMPLETO: cerró ayer
    ends = starts + timedelta(days=13)
    period = Period(
        client_id=c.id, plan_id=plan.id, period_index=1,
        starts_on=starts, ends_on=ends, status="closed",
        closing_weight_kg=83.4, closing_waist_cm=90.5, closing_hip_cm=99.0,
        closing_arm_cm=36.5, closing_thigh_cm=58.0,
        closing_feelings_json={"energia": 4, "hambre": 2, "sueno": 4,
                               "recuperacion": 4, "animo": 5, "digestiones": 4},
        adherence_diet_0_10=9, adherence_training_0_10=8, free_meals_count=2,
        closing_hardest="Las cenas del fin de semana.",
        closing_changes="Mucha más energía en los entrenos desde la semana 2.",
        closing_next_goal="Bajar de 83 kg manteniendo las cargas.",
        closing_submitted_at=datetime.now(timezone.utc) - timedelta(hours=18),
        photos_confirmed=True,
        coach_reviewed_at=None,  # la notificación del coach sigue VIVA
    )
    db.add(period)
    db.flush()

    pesos = [84.6, 84.4, 84.5, 84.2, 84.0, 84.1, 83.9, 83.8, 83.9, 83.6, 83.5, 83.6, 83.5, 83.4]
    for i in range(14):
        d = DailyLog(
            period_id=period.id, log_date=starts + timedelta(days=i),
            weight_kg=pesos[i], sleep_hours=7.0 + (i % 2) * 0.5,
            steps=str(9000 + (i % 5) * 400), water_liters=2.5,
            diet_adherence=("yes" if i % 5 else "partial"),
            energy_1_5=4 if i > 3 else 3, mood_1_5=4, fatigue_1_5=2,
            chosen_options_json={"1": ["A", "B"][i % 2], "2": ["A", "B", "C"][i % 3],
                                 "3": "C", "4": ["A", "C"][i % 2]},
        )
        db.add(d)
        db.flush()
        if i in (0, 2, 4, 7, 9, 11):
            sess = plan.training_json["sessions"][i % len(plan.training_json["sessions"])]
            for ex in sess["exercises"][:4]:
                base = 55.0 + (ex["exercise_id"] % 4) * 10
                extra = 2.5 * (i // 5)  # progresión visible en el Resumen
                for set_n in range(1, 4):
                    db.add(WorkoutLog(daily_log_id=d.id, exercise_id=ex["exercise_id"],
                                      set_number=set_n, reps=8, weight_kg=base + extra, rpe=8.0))
    db.commit()
    return c


def main() -> None:
    db = SessionLocal()
    try:
        borrados = wipe_demo_clients(db)
        marta = crear_marta(db)
        carlos = crear_carlos(db)
        jordi = crear_jordi(db)
        base = settings.public_base_url.rstrip("/")
        # En desarrollo (docker compose dev) el frontend sirve en el puerto 5173.
        web = f"{base}:5173" if base == "http://localhost" else base
        print(f"[demo] clientes de demo previos borrados: {borrados}")
        print("[demo] escenario creado — tres fases del ciclo:")
        print(f"  1· Marta Serra  — Génesis.99, día 8 de 14 (portal vivo)")
        print(f"      portal: {web}/p/{marta.portal_token}")
        print(f"  2· Carlos Bosch — Génesis.99, revisión CERRADA ayer (notificación + Resumen)")
        print(f"      portal: {web}/p/{carlos.portal_token}")
        print(f"  3· Jordi Puig   — Entreno Personal, día 5 (sesiones presenciales)")
        print(f"      portal: {web}/p/{jordi.portal_token}")
        print(f"[demo] panel del coach: {web}/  · página de planes: {web}/planes")
        print("[demo] el alta EN VIVO (Laura) se hace desde el panel durante la demo (DEMO.md).")
        print("[demo] re-ejecutar este script REINICIA la demo (idempotente).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
