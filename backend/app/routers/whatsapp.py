"""Ronda diaria de seguimiento por WhatsApp (panel del coach).

GET  /api/whatsapp/round        mensaje del día ya redactado para cada cliente
                                activo (la IA lo adapta a cada persona).
POST /api/whatsapp/round/sent   marca que a ese cliente ya se le envió hoy.

El envío es ASISTIDO: el panel abre WhatsApp con el texto escrito y el coach
pulsa enviar. Nada sale sin que lo haya visto.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.services import whatsapp_round as wa

router = APIRouter(
    prefix="/api/whatsapp", tags=["whatsapp"], dependencies=[Depends(get_current_user)]
)


class MarkSentIn(BaseModel):
    round_id: int
    client_id: int
    text: str | None = None


@router.get("/round")
def get_round(use_ai: bool = True, force: bool = False,
              db: Session = Depends(get_db)) -> dict:
    """Ronda de hoy. Los textos quedan guardados en la ronda: reabrir no gasta
    IA. `force=true` (Reescribir) regenera; `use_ai=false` usa los de reserva."""
    ai = None
    if use_ai:
        try:
            from app.services.ai.client import AIClient

            ai = AIClient()
        except Exception:  # noqa: BLE001 — sin clave, ronda con textos de reserva
            ai = None
    return wa.build_round(db, ai=ai, force=force)


@router.post("/round/sent")
def mark_sent(body: MarkSentIn, db: Session = Depends(get_db)) -> dict:
    from app.models import WhatsAppRound

    if db.get(WhatsAppRound, body.round_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ronda no encontrada")
    if not wa.mark_sent(db, round_id=body.round_id, client_id=body.client_id, text=body.text):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese cliente ya no existe")
    return {"ok": True}
