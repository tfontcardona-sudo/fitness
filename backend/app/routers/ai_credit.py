"""Créditos IA (Anthropic) — saldo local para el botón del sidebar.

GET devuelve saldo/gasto/restante + URL de recarga; PUT fija el saldo tras una
recarga (y pone el gasto a cero, porque el número nuevo YA es el real).
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import utcnow
from app.services.ai_credit import RECHARGE_URL, get_state, remaining_usd
from app.services.audit import log_event

router = APIRouter(
    prefix="/api/ai-credit", tags=["ai-credit"], dependencies=[Depends(get_current_user)]
)


class AiCreditOut(BaseModel):
    balance_usd: float | None
    spent_usd: float
    remaining_usd: float | None
    updated_at: datetime | None
    recharge_url: str


class AiCreditIn(BaseModel):
    balance_usd: float = Field(ge=0, le=100_000)


def _out(state) -> AiCreditOut:
    return AiCreditOut(
        balance_usd=state.balance_usd,
        spent_usd=round(state.spent_usd or 0.0, 4),
        remaining_usd=remaining_usd(state),
        updated_at=state.updated_at,
        recharge_url=RECHARGE_URL,
    )


@router.get("", response_model=AiCreditOut)
def get_ai_credit(db: Session = Depends(get_db)) -> AiCreditOut:
    return _out(get_state(db))


@router.put("", response_model=AiCreditOut)
def set_ai_credit(body: AiCreditIn, db: Session = Depends(get_db)) -> AiCreditOut:
    state = get_state(db)
    state.balance_usd = body.balance_usd
    state.spent_usd = 0.0
    state.updated_at = utcnow()
    log_event(db, "ai_credit", state.id, "ai_credit_set", {"balance_usd": body.balance_usd})
    db.commit()
    db.refresh(state)
    return _out(state)
