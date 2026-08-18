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
            Plan, PlanEdit, ProgressPhoto, PushSubscription, WorkoutLog,
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


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_products():
    """Los tests de la TIENDA crean productos; sin esto se quedaban en el
    catálogo del coach (y salían en el portal de sus clientes, duplicados en
    cada ejecución). Se borra EXACTAMENTE lo creado durante la suite: todo lo
    que tenga un id mayor que el máximo de antes de empezar."""
    try:
        from sqlalchemy import delete, func, select

        from app.db import SessionLocal
        from app.models import RecommendedProduct
    except Exception:
        yield
        return
    db = SessionLocal()
    try:
        tope = db.scalar(select(func.max(RecommendedProduct.id))) or 0
    except Exception:
        db.rollback()
        tope = None
    finally:
        db.close()

    yield

    if tope is None:
        return
    db = SessionLocal()
    try:
        db.execute(delete(RecommendedProduct).where(RecommendedProduct.id > tope))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture()
def ciclo_quincenal(monkeypatch):
    """Enciende el CICLO QUINCENAL para este test.

    El motor soporta los dos modos y la marca decide (branding.FEATURE_BIWEEKLY):
    Professional trabaja con seguimiento CONTINUO, pero las piezas del ciclo de
    14 días (cierre del cliente, recordatorios, alertas ancladas a la revisión)
    siguen en el motor y se prueban aquí con el interruptor puesto."""
    from app import branding
    from app.services import periods

    monkeypatch.setattr(branding, "FEATURE_BIWEEKLY", True)
    monkeypatch.setattr(branding, "FOLLOWUP_DAYS", 14)
    monkeypatch.setattr(periods, "PERIOD_DAYS", 14)
    return True
