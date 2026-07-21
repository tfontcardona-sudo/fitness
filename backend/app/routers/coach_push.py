"""Push del COACH (web del coach, con JWT): sus dispositivos reciben cada 3 h
el resumen de alertas/pendientes de sus clientes (services/push.run_coach_digest)
para estar al día sin tener la web abierta."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.services.audit import log_event
from app.services.push import (
    push_configured,
    remove_coach_subscription,
    save_coach_subscription,
)

router = APIRouter(prefix="/api/coach/push", tags=["coach-push"],
                   dependencies=[Depends(get_current_user)])


class SubscribeIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/public-key")
def public_key() -> dict:
    return {"enabled": push_configured(), "public_key": settings.vapid_public_key or None}


@router.post("/subscribe")
def subscribe(body: SubscribeIn, request: Request, db: Session = Depends(get_db)) -> dict:
    sub = save_coach_subscription(
        db, body.endpoint, body.p256dh, body.auth,
        user_agent=request.headers.get("user-agent"),
    )
    log_event(db, "brand", 1, "coach_push_subscribed", None)
    db.commit()
    return {"id": sub.id}


@router.post("/unsubscribe")
def unsubscribe(body: SubscribeIn, db: Session = Depends(get_db)) -> dict:
    removed = remove_coach_subscription(db, body.endpoint)
    db.commit()
    return {"removed": removed}
