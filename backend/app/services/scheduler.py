"""Scheduler de tareas programadas (APScheduler).

Un único job diario que ejecuta el mantenimiento de la máquina de estados y los
recordatorios. Corre en un BackgroundScheduler (hilo aparte) con la zona horaria
de settings.tz (Europe/Madrid por defecto).

El job abre su PROPIA sesión de base de datos (no comparte la de los requests).
`misfire_grace_time` y `coalesce` evitan ejecuciones acumuladas si el proceso
estuvo caído; `max_instances=1` impide solapamiento. Como el job es idempotente
(jobs.run_daily_maintenance), reejecutar el mismo día es seguro.

El arranque/parada se engancha al lifespan de FastAPI (main.py).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db import SessionLocal
from app.services.jobs import run_daily_maintenance
from app.services.push import run_coach_digest, run_push_reminders, run_video_call_reminders

logger = logging.getLogger("scheduler")

DAILY_HOUR = 6   # 06:00 hora local: tras el cierre natural del día anterior
DAILY_MINUTE = 30

# Recordatorios push: cada 3 h en punto (hora local). El propio job descarta
# las ejecuciones fuera del horario activo 08–22 (push.ACTIVE_FROM/UNTIL), así
# que en la práctica envía a las 09/12/15/18/21 como mucho, y solo a quien
# tenga algo pendiente. El resumen del COACH usa la misma cadencia.
PUSH_EVERY_HOURS = 3

# Recordatorios de VIDEOLLAMADA (día antes + 1 h antes): cada 15 min, para que el
# aviso de "1 h antes" caiga con precisión suficiente. El job es barato (solo
# mira las agendadas) e idempotente (dedup por auditoría).
VC_REMINDER_EVERY_MIN = 15

_scheduler: BackgroundScheduler | None = None


def _daily_job() -> None:
    db = SessionLocal()
    try:
        summary = run_daily_maintenance(db)
        logger.info("mantenimiento diario: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en el mantenimiento diario")
        db.rollback()
    finally:
        db.close()


def _push_job() -> None:
    db = SessionLocal()
    try:
        summary = run_push_reminders(db)
        logger.info("recordatorios push: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en los recordatorios push")
        db.rollback()
    finally:
        db.close()


def _coach_digest_job() -> None:
    db = SessionLocal()
    try:
        summary = run_coach_digest(db)
        logger.info("resumen push del coach: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en el resumen push del coach")
        db.rollback()
    finally:
        db.close()


def _video_call_reminder_job() -> None:
    db = SessionLocal()
    try:
        summary = run_video_call_reminders(db)
        logger.info("recordatorios de videollamada: %s", summary)
    except Exception:  # nunca tumbar el scheduler por un fallo puntual
        logger.exception("fallo en los recordatorios de videollamada")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=settings.tz)
    # OJO: cada CronTrigger lleva SU timezone explícita — sin ella, APScheduler
    # usa la zona del SERVIDOR (UTC en el VPS) y los jobs correrían a deshora
    # (mantenimiento a las 08:30 locales en vez de 06:30, push desplazado).
    sched.add_job(
        _daily_job,
        trigger=CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE, timezone=settings.tz),
        id="daily_maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    sched.add_job(
        _push_job,
        trigger=CronTrigger(hour=f"*/{PUSH_EVERY_HOURS}", minute=0, timezone=settings.tz),
        id="push_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=1800,
    )
    # Resumen de alertas al MÓVIL del coach, misma cadencia (a y 5 para no
    # solapar con los recordatorios de los clientes).
    sched.add_job(
        _coach_digest_job,
        trigger=CronTrigger(hour=f"*/{PUSH_EVERY_HOURS}", minute=5, timezone=settings.tz),
        id="coach_digest",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=1800,
    )
    sched.add_job(
        _video_call_reminder_job,
        trigger=CronTrigger(minute=f"*/{VC_REMINDER_EVERY_MIN}", timezone=settings.tz),
        id="video_call_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=600,
    )
    sched.start()
    logger.info(
        "scheduler iniciado (mantenimiento %02d:%02d, push cada %dh, %s)",
        DAILY_HOUR, DAILY_MINUTE, PUSH_EVERY_HOURS, settings.tz,
    )
    _scheduler = sched
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
