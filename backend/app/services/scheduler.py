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

logger = logging.getLogger("scheduler")

DAILY_HOUR = 6   # 06:00 hora local: tras el cierre natural del día anterior
DAILY_MINUTE = 30

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


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=settings.tz)
    sched.add_job(
        _daily_job,
        trigger=CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE),
        id="daily_maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    sched.start()
    logger.info("scheduler iniciado (job diario %02d:%02d %s)", DAILY_HOUR, DAILY_MINUTE, settings.tz)
    _scheduler = sched
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
