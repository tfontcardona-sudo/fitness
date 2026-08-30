"""Limpieza de la BD al terminar la suite (§7 de CLAUDE.md).

Los tests de integración escriben en la MISMA base de datos a la que apunta
`DATABASE_URL` (en desarrollo, la del panel del coach) y dejaban clientes de
prueba `@example.com` visibles tras cada `pytest`. Este fixture de sesión borra
al FINAL de la suite todos los clientes cuyo email pertenece a un dominio de
prueba, junto con TODAS sus filas dependientes (mismo orden de FKs que el
endpoint RGPD `DELETE /api/clients/{id}`) y sus archivos en disco.

No toca nada más: ejercicios/alimentos sembrados, marca, admins y clientes
reales (emails normales) quedan intactos.
"""
import pytest

# Dominios que los tests usan para crear clientes sintéticos. Un cliente real
# jamás debería tener uno de estos (example.com/test están reservados por RFC).
_TEST_EMAIL_PATTERNS = ("%@example.com", "%@example.org", "%@test.local", "%@x.com")


@pytest.fixture(scope="session", autouse=True)
def _sin_cupo_de_altas():
    """El tope diario de altas públicas (protección anti-abuso del formulario)
    es GLOBAL por día: la suite crea muchos clientes y, al ejecutarla entera,
    los últimos tests se topaban con el 429. En producción sigue en su valor."""
    from app.config import settings

    previo = getattr(settings, "public_signups_per_day", 25)
    settings.public_signups_per_day = 100000
    yield
    settings.public_signups_per_day = previo


@pytest.fixture(scope="session", autouse=True)
def _sin_cache_del_educativo():
    """La caché del contenido educativo se guarda en un sidecar del storage y
    SOBREVIVE entre ejecuciones: el primer `pytest` la puebla y el siguiente se
    salta la llamada de IA que los tests del pipeline están contando. La suite
    daba resultados distintos según cuántas veces se hubiera corrido antes
    (`test_plan_solo_entrenamiento_sin_dieta` pasaba en limpio y fallaba a la
    segunda). Se apaga en los tests, que es lo que el traspaso ya daba por
    hecho; en producción sigue ahorrando créditos."""
    from app.config import settings

    previo = getattr(settings, "education_cache_enabled", True)
    settings.education_cache_enabled = False
    yield
    settings.education_cache_enabled = previo


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_clients():
    yield
    try:
        from sqlalchemy import delete, or_, select, update

        from app.db import SessionLocal
        from app.models import (
            ChangeRequest, Client, DailyLog, EmailLog, FeedbackDoc, Payment,
            Period, Plan, PlanEdit, ProgressPhoto, PushSubscription, VideoCall,
            WorkoutLog,
        )
        from app.services.storage import delete_client_tree
    except Exception:
        return  # sin DB configurada (tests puros) no hay nada que limpiar

    db = SessionLocal()
    try:
        conds = [Client.email.ilike(p) for p in _TEST_EMAIL_PATTERNS]
        ids = list(db.scalars(select(Client.id).where(or_(*conds))))
        if not ids:
            return
        period_ids = list(db.scalars(select(Period.id).where(Period.client_id.in_(ids))))
        if period_ids:
            daily_ids = list(db.scalars(
                select(DailyLog.id).where(DailyLog.period_id.in_(period_ids))))
            if daily_ids:
                db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(daily_ids)))
                db.execute(delete(DailyLog).where(DailyLog.id.in_(daily_ids)))
            db.execute(delete(FeedbackDoc).where(FeedbackDoc.period_id.in_(period_ids)))
        db.execute(delete(ProgressPhoto).where(ProgressPhoto.client_id.in_(ids)))
        db.execute(delete(PushSubscription).where(PushSubscription.client_id.in_(ids)))
        db.execute(delete(VideoCall).where(VideoCall.client_id.in_(ids)))
        # Movimientos de pago sintéticos: si no se borran, el feed del panel (y
        # los ingresos del mes) se llenan de cobros de prueba tras cada pytest.
        # Por cliente Y por email del pagador: los tests de pago HUÉRFANO crean
        # filas sin client_id que, sin esta segunda condición, quedaban para
        # siempre sumando en "cobrado este mes".
        db.execute(delete(Payment).where(
            or_(Payment.client_id.in_(ids),
                *[Payment.customer_email.ilike(p) for p in _TEST_EMAIL_PATTERNS])))
        db.execute(delete(Period).where(Period.client_id.in_(ids)))
        # plan_edits.plan_id NO tiene ON DELETE (§13, aprendizaje continuo):
        # cualquier plan editado desde el panel dejaba filas que hacían fallar
        # el DELETE de plans con ForeignKeyViolation. Como el `except` de abajo
        # se traga el error y hace rollback, la limpieza ENTERA no se aplicaba
        # y pytest sí dejaba clientes de prueba en el panel (el mismo fallo que
        # ya estaba corregido en el borrado RGPD de routers/clients.py).
        plan_ids = list(db.scalars(select(Plan.id).where(Plan.client_id.in_(ids))))
        if plan_ids:
            db.execute(delete(PlanEdit).where(PlanEdit.plan_id.in_(plan_ids)))
        db.execute(delete(Plan).where(Plan.client_id.in_(ids)))
        db.execute(delete(ChangeRequest).where(ChangeRequest.client_id.in_(ids)))
        db.execute(update(EmailLog).where(EmailLog.client_id.in_(ids)).values(client_id=None))
        db.execute(delete(Client).where(Client.id.in_(ids)))
        db.commit()
        for cid in ids:
            try:
                delete_client_tree(cid)
            except Exception:
                pass  # el disco es secundario; la BD ya quedó limpia
    except Exception as exc:  # noqa: BLE001
        # AVISO VISIBLE: este `except` mudo escondió durante meses que la
        # limpieza fallaba entera (una FK sin ON DELETE) y que pytest sí dejaba
        # clientes de prueba en el panel. Si vuelve a fallar, se ve.
        db.rollback()
        print(f"\n⚠ Limpieza de datos de prueba FALLIDA: {type(exc).__name__}: {exc}\n")
    finally:
        db.close()
