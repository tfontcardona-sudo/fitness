"""Rellena el portal de un cliente con seguimiento realista para probar el workflow.

Simula lo que el cliente habría hecho desde su móvil durante 2 semanas:
- 14 registros diarios (peso con tendencia a la baja, sueño, pasos, saciedad,
  agua, adherencia, energía/ánimo/fatiga y algún comentario).
- Series de entreno (peso × reps) en los días de entreno, siguiendo las
  sesiones del plan PUBLICADO con progresión de cargas en la 2ª semana.
- La REVISIÓN QUINCENAL completa (medidas, sensaciones, adherencias, textos)
  y el cierre del período — replicando el endpoint público de cierre, con el
  cliente pasando a "review_pending" para que el coach siga el workflow:
  generar feedback → adaptar planificación → publicar.

Uso (desde la raíz del proyecto en el servidor):
    docker compose exec api python -m scripts.seed_demo_tracking            # cliente "mohamadou"
    docker compose exec api python -m scripts.seed_demo_tracking "otro nombre"

Idempotente: si el período ya tiene registros, los reemplaza. Si el período
está abierto pero empezó hace poco, lo retro-data para que el cierre sea válido
(el cierre exige día >= 14).
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
NOTES = {
    2: "Semana dura en el trabajo, pero he cumplido.",
    6: "Muy buenas sensaciones hoy, con energía.",
    12: "Cena fuera con amigos, me pasé un poco.",
}
ADHERENCE = {4: "partial", 9: "no", 11: "partial"}
# Días de entreno dentro de las 2 semanas (4 días/semana)
TRAINING_DAY_IDX = [0, 1, 3, 4, 7, 8, 10, 11]


def parse_reps(rep_range: str | None) -> tuple[int, int]:
    try:
        lo, hi = str(rep_range or "8-10").replace("–", "-").split("-")[:2]
        return int(lo), int(hi)
    except Exception:
        return 8, 10


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "mohamadou"
    rng = random.Random(42)  # determinista: re-ejecutar da los mismos datos
    db = SessionLocal()

    client = db.scalar(select(Client).where(Client.full_name.ilike(f"%{name}%")))
    if not client:
        sys.exit(f"No hay ningún cliente cuyo nombre contenga '{name}'.")

    plan = db.scalar(
        select(Plan).where(Plan.client_id == client.id, Plan.status == "published")
        .order_by(Plan.version.desc()).limit(1)
    )
    if not plan:
        sys.exit(f"{client.full_name} no tiene plan PUBLICADO: publica su planificación primero.")

    today = date.today()
    starts_on = today - timedelta(days=DAYS - 1)  # día 14 = hoy → el cierre es válido

    period = db.scalar(
        select(Period).where(Period.client_id == client.id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    if period is None or period.status != "open":
        idx = (period.period_index + 1) if period else 1
        period = Period(client_id=client.id, plan_id=plan.id, period_index=idx,
                        starts_on=starts_on, ends_on=today, status="open")
        db.add(period)
        db.flush()
        log_event(db, "period", period.id, "period_opened", {"index": idx, "seeded": True})
    else:
        # Retro-datar el período abierto para que el cierre (día >= 14) sea válido
        period.starts_on = starts_on
        period.ends_on = today
        period.plan_id = plan.id

    # Idempotencia: fuera los registros previos de este período
    old_logs = db.scalars(select(DailyLog.id).where(DailyLog.period_id == period.id)).all()
    if old_logs:
        db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(old_logs)))
        db.execute(delete(DailyLog).where(DailyLog.id.in_(old_logs)))
        db.flush()

    sessions = (plan.training_json or {}).get("sessions") or []
    start_w = float(client.start_weight_kg or 84.0)
    total_sets = 0
    last_weight = start_w

    for i in range(DAYS):
        d = starts_on + timedelta(days=i)
        # Peso: tendencia -1.6 kg en 14 días con ruido suave
        weight = round(start_w - 1.6 * (i / (DAYS - 1)) + rng.uniform(-0.25, 0.25), 1)
        last_weight = weight
        log = DailyLog(
            period_id=period.id, log_date=d,
            weight_kg=weight,
            sleep_hours=round(rng.uniform(6.5, 8.0) * 2) / 2,
            steps=str(rng.randrange(8000, 11500, 250)),
            satiety_1_10=float(rng.randint(5, 8)),
            water_liters=round(rng.uniform(2.2, 3.0), 1),
            diet_adherence=ADHERENCE.get(i, "yes"),
            energy_1_5=rng.randint(3, 5),
            mood_1_5=rng.randint(3, 5),
            fatigue_1_5=rng.randint(2, 4),
            free_notes=NOTES.get(i),
        )
        db.add(log)
        db.flush()

        if sessions and i in TRAINING_DAY_IDX:
            session = sessions[TRAINING_DAY_IDX.index(i) % len(sessions)]
            week2 = i >= 7
            for ex in session.get("exercises", []):
                ex_id = ex.get("exercise_id")
                if not ex_id:
                    continue
                base = float(ex.get("start_weight_hint_kg") or 40.0)
                weight_kg = base + (2.5 if week2 else 0.0)
                lo, hi = parse_reps(ex.get("rep_range"))
                for set_n in range(1, min(int(ex.get("sets") or 3), 5) + 1):
                    db.add(WorkoutLog(
                        daily_log_id=log.id, exercise_id=ex_id, set_number=set_n,
                        reps=rng.randint(lo, hi), weight_kg=weight_kg,
                    ))
                    total_sets += 1

    # ---- Revisión quincenal + cierre (réplica del endpoint público /close) ----
    period.closing_weight_kg = last_weight
    period.closing_waist_cm = 88.5
    period.closing_hip_cm = 101.0
    period.closing_arm_cm = 36.5
    period.closing_thigh_cm = 58.0
    period.closing_rating = 4
    period.closing_feelings_json = {
        "energia": 4, "hambre": 3, "sueno": 4, "estres": 3, "motivacion": 5, "digestion": 4,
    }
    period.adherence_diet_0_10 = 8
    period.adherence_training_0_10 = 9
    period.free_meals_count = 2
    period.closing_changes = "Me noto menos hinchado y con más energía por las mañanas."
    period.closing_hardest = "Las cenas del fin de semana y llegar a los pasos en días de oficina."
    period.closing_next_goal = f"Bajar de {round(last_weight - 0.8)} kg manteniendo la fuerza."
    period.closing_questions = "¿Puedo cambiar el cardio de cinta por bicicleta?"
    period.status = "closed"
    period.coach_reviewed_at = None  # que el aviso "!" salte en el panel del coach

    if client.status in ("active", "awaiting_feedback", "at_risk"):
        client.status = "review_pending"

    log_event(db, "client", client.id, "period_closed",
              {"period_index": period.period_index, "rating": 4, "seeded": True})
    db.commit()

    print(f"✔ {client.full_name} (id {client.id}) — período #{period.period_index} "
          f"{period.starts_on} → {period.ends_on}")
    print(f"  {DAYS} registros diarios · {total_sets} series de entreno · revisión quincenal CERRADA")
    print(f"  Peso: {start_w} → {last_weight} kg · adherencia dieta 8/10 · entreno 9/10")
    print("  Siguiente paso del workflow: el panel del coach mostrará "
          f"'Revisión quincenal subida' para {client.full_name.split()[0]} → Generar feedback.")


if __name__ == "__main__":
    main()
