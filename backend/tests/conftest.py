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
def _cleanup_test_clients():
    yield
    try:
        from sqlalchemy import delete, or_, select, update

        from app.db import SessionLocal
        from app.models import (
            ChangeRequest, Client, DailyLog, EmailLog, FeedbackDoc, Period,
            Plan, PlanEdit, ProgressPhoto, PushSubscription, VideoCall, WorkoutLog,
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
        db.execute(delete(Period).where(Period.client_id.in_(ids)))
        # plan_edits (§13) referencia plans sin ON DELETE: fuera primero, o el
        # DELETE de plans revienta si algún test/coach editó un plan.
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
    except Exception:
        db.rollback()
    finally:
        db.close()
