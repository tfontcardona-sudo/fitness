"""Rellena el portal de un cliente con seguimiento realista para probar el workflow.

Simula lo que el cliente habría hecho desde su móvil durante 2 semanas:
- 14 registros diarios (peso con tendencia a la baja, sueño, pasos, saciedad,
  agua, adherencia, energía/ánimo/fatiga y algún comentario).
- Series de entreno (peso × reps) en los días de entreno, siguiendo las
  sesiones del plan PUBLICADO con progresión de cargas.
- La REVISIÓN QUINCENAL completa (medidas, sensaciones, adherencias, textos)
  y el cierre del período — replicando el endpoint público de cierre, con el
  cliente pasando a "review_pending" para que el coach siga el workflow:
  generar feedback → adaptar planificación → publicar.

CONTINÚA LA HISTORIA entre quincenas: cada período arranca del peso de cierre
del anterior, con una narrativa propia (la nº 2 baja a ritmo más sano tras el
ajuste de calorías, progresa en fuerza y trae puntos a vigilar nuevos: sueño
corto, estrés alto y más comidas libres).

Uso (desde la raíz del proyecto en el servidor):
    docker compose exec api python -m scripts.seed_demo_tracking            # cliente "mohamadou"
    docker compose exec api python -m scripts.seed_demo_tracking "otro nombre"

Se puede ejecutar una vez por quincena: si el último período está cerrado o
analizado, crea y rellena el SIGUIENTE. Si hay uno abierto, lo retro-data para
que el cierre sea válido (exige día >= 14) y lo rellena. Idempotente dentro de
un período: re-ejecutar reemplaza sus registros.
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Client, DailyLog, Period, Plan, WorkoutLog
from app.services.audit import log_event

DAYS = 14
# Días de entreno dentro de las 2 semanas (4 días/semana)
TRAINING_DAY_IDX = [0, 1, 3, 4, 7, 8, 10, 11]

# Narrativa por quincena. La 1: gran arranque (bajada rápida, todo verde).
# La 2 (y siguientes): ritmo sano tras el ajuste, pero con puntos a vigilar
# (sueño corto, estrés en zona roja, 4 comidas libres) para que el análisis
# automático y la adaptación tengan sustancia nueva.
STORIES: dict[int, dict] = {
    1: dict(
        weight_delta=-1.6,
        sleep_range=(6.5, 8.0),
        steps_range=(8000, 11500),
        satiety_range=(5, 8),
        waist=88.5, hip=101.0, arm=36.5, thigh=58.0,
        rating=4,
        feelings={"energia": 4, "hambre": 3, "sueno": 4, "estres": 3, "motivacion": 5, "digestion": 4},
        adherence_diet=8, adherence_training=9, free_meals=2,
        adherence_map={4: "partial", 9: "no", 11: "partial"},
        notes={
            2: "Semana dura en el trabajo, pero he cumplido.",
            6: "Muy buenas sensaciones hoy, con energía.",
            12: "Cena fuera con amigos, me pasé un poco.",
        },
        changes="Me noto menos hinchado y con más energía por las mañanas.",
        hardest="Las cenas del fin de semana y llegar a los pasos en días de oficina.",
        next_goal="Bajar de {goal} kg manteniendo la fuerza.",
        questions="¿Puedo cambiar el cardio de cinta por bicicleta?",
    ),
    2: dict(
        weight_delta=-0.9,  # ~0,45 kg/semana: justo el ritmo que pidió la adaptación
        sleep_range=(5.5, 7.0),  # sueño corto entre semana → punto a vigilar
        steps_range=(7500, 11000),
        satiety_range=(6, 9),  # con las calorías nuevas llega mejor a las comidas
        waist=87.5, hip=100.5, arm=36.6, thigh=57.5,
        rating=4,
        feelings={"energia": 4, "hambre": 4, "sueno": 3, "estres": 2, "motivacion": 4, "digestion": 4},
        adherence_diet=9, adherence_training=8, free_meals=4,
        adherence_map={3: "partial", 8: "partial", 12: "no", 13: "partial"},
        notes={
            1: "Primera semana con las calorías nuevas: llego mucho mejor a la cena.",
            6: "Semana complicada en el trabajo, durmiendo poco.",
            12: "Comida familiar; me salí del plan pero sin descontrol.",
        },
        changes="El ajuste de calorías se nota: sigo bajando pero sin pasar hambre y con fuerza estable.",
        hardest="Dormir 7 horas entre semana: el trabajo me tiene con estrés alto y me cuesta desconectar.",
        next_goal="Consolidar por debajo de {goal} kg y dormir al menos 7 h entre semana.",
        questions="¿Me conviene más entrenar a primera hora en ayunas o por la tarde como hasta ahora?",
    ),
}


def parse_reps(rep_range: str | None) -> tuple[int, int]:
    try:
        lo, hi = str(rep_range or "8-10").replace("–", "-").split("-")[:2]
        return int(lo), int(hi)
    except Exception:
        return 8, 10


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "mohamadou"
    db = SessionLocal()

    client = db.scalar(select(Client).where(Client.full_name.ilike(f"%{name}%")))
    if not client:
        sys.exit(f"No hay ningún cliente cuyo nombre contenga '{name}'.")

    plan = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.status == "published")
        .order_by(Plan.month_index.desc(), Plan.version.desc()).limit(1)
    )
    if not plan:
        sys.exit(f"{client.full_name} no tiene plan PUBLICADO: publica su planificación primero.")

    today = date.today()
    starts_on = today - timedelta(days=DAYS - 1)  # día 14 = hoy → el cierre es válido

    last = db.scalar(
        select(Period).where(Period.client_id == client.id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    if last is None or last.status != "open":
        idx = (last.period_index + 1) if last else 1
        period = Period(client_id=client.id, plan_id=plan.id, period_index=idx,
                        starts_on=starts_on, ends_on=today, status="open")
        db.add(period)
        db.flush()
        log_event(db, "period", period.id, "period_opened", {"index": idx, "seeded": True})
    else:
        # Retro-datar el período abierto para que el cierre (día >= 14) sea válido
        period = last
        period.starts_on = starts_on
        period.ends_on = today
        period.plan_id = plan.id

    story = STORIES.get(period.period_index) or STORIES[2]
    # Determinista pero DISTINTO por quincena: re-ejecutar da los mismos datos
    rng = random.Random(42 + period.period_index)

    # Idempotencia: fuera los registros previos de este período
    old_logs = db.scalars(select(DailyLog.id).where(DailyLog.period_id == period.id)).all()
    if old_logs:
        db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(old_logs)))
        db.execute(delete(DailyLog).where(DailyLog.id.in_(old_logs)))
        db.flush()

    # El peso arranca donde cerró la quincena anterior (continuidad real)
    prev = db.scalar(
        select(Period).where(Period.client_id == client.id,
                             Period.period_index == period.period_index - 1)
    )
    start_w = float(
        (prev.closing_weight_kg if prev and prev.closing_weight_kg else None)
        or client.start_weight_kg or 84.0
    )

    sessions = (plan.training_json or {}).get("sessions") or []
    slo, shi = story["sleep_range"]
    sat_lo, sat_hi = story["satiety_range"]
    total_sets = 0
    last_weight = start_w

    for i in range(DAYS):
        d = starts_on + timedelta(days=i)
        weight = round(start_w + story["weight_delta"] * (i / (DAYS - 1)) + rng.uniform(-0.25, 0.25), 1)
        last_weight = weight
        log = DailyLog(
            period_id=period.id, log_date=d,
            weight_kg=weight,
            sleep_hours=round(rng.uniform(slo, shi) * 2) / 2,
            steps=str(rng.randrange(*story["steps_range"], 250)),
            satiety_1_10=float(rng.randint(sat_lo, sat_hi)),
            water_liters=round(rng.uniform(2.2, 3.0), 1),
            diet_adherence=story["adherence_map"].get(i, "yes"),
            energy_1_5=rng.randint(3, 5),
            mood_1_5=rng.randint(3, 5),
            fatigue_1_5=rng.randint(2, 4),
            free_notes=story["notes"].get(i),
        )
        db.add(log)
        db.flush()

        if sessions and i in TRAINING_DAY_IDX:
            session = sessions[TRAINING_DAY_IDX.index(i) % len(sessions)]
            week2 = i >= 7
            # Progresión acumulada: +2,5 kg por semana de entreno transcurrida
            # (quincena 1: 0 → 2,5 · quincena 2: 5 → 7,5 · ...)
            bump = 2.5 * (2 * (period.period_index - 1) + (1 if week2 else 0))
            for ex in session.get("exercises", []):
                ex_id = ex.get("exercise_id")
                if not ex_id:
                    continue
                base = float(ex.get("start_weight_hint_kg") or 40.0)
                weight_kg = base + bump
                lo, hi = parse_reps(ex.get("rep_range"))
                for set_n in range(1, min(int(ex.get("sets") or 3), 5) + 1):
                    db.add(WorkoutLog(
                        daily_log_id=log.id, exercise_id=ex_id, set_number=set_n,
                        reps=rng.randint(lo, hi), weight_kg=weight_kg,
                    ))
                    total_sets += 1

    # ---- Revisión quincenal + cierre (réplica del endpoint público /close) ----
    goal = round(last_weight - 0.8)
    period.closing_weight_kg = last_weight
    period.closing_waist_cm = story["waist"]
    period.closing_hip_cm = story["hip"]
    period.closing_arm_cm = story["arm"]
    period.closing_thigh_cm = story["thigh"]
    period.closing_rating = story["rating"]
    period.closing_feelings_json = story["feelings"]
    period.adherence_diet_0_10 = story["adherence_diet"]
    period.adherence_training_0_10 = story["adherence_training"]
    period.free_meals_count = story["free_meals"]
    period.closing_changes = story["changes"]
    period.closing_hardest = story["hardest"]
    period.closing_next_goal = story["next_goal"].format(goal=goal)
    period.closing_questions = story["questions"]
    period.status = "closed"
    period.coach_reviewed_at = None  # que el aviso "!" salte en el panel del coach

    if client.status in ("active", "awaiting_feedback", "at_risk"):
        client.status = "review_pending"

    log_event(db, "client", client.id, "period_closed",
              {"period_index": period.period_index, "rating": story["rating"], "seeded": True})
    db.commit()

    print(f"✔ {client.full_name} (id {client.id}) — período #{period.period_index} "
          f"{period.starts_on} → {period.ends_on}")
    print(f"  {DAYS} registros diarios · {total_sets} series de entreno · revisión quincenal CERRADA")
    print(f"  Peso: {start_w} → {last_weight} kg · adherencia dieta "
          f"{story['adherence_diet']}/10 · entreno {story['adherence_training']}/10 · "
          f"{story['free_meals']} comidas libres")
    print("  Siguiente paso del workflow: el panel del coach mostrará "
          f"'Revisión quincenal subida' para {client.full_name.split()[0]} → Generar feedback.")


if __name__ == "__main__":
    main()
