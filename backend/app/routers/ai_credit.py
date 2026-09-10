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
from app.services.ai_credit import (
    RECHARGE_URL,
    gasto_desde_la_recarga,
    get_state,
    plans_left,
    remaining_usd,
    ultima_recarga_usd,
    usage_summary,
)
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
    # Consumo EN VIVO (real, de las llamadas ya hechas): no depende de que el
    # coach haya apuntado el saldo.
    spent_today_usd: float = 0.0
    spent_window_usd: float = 0.0
    calls_window: int = 0
    window_days: int = 30
    last_call_at: datetime | None = None
    avg_cost_per_plan_usd: float | None = None
    plans_left: int | None = None
    # SE ACABÓ EL CRÉDITO: lo dice la propia API de Anthropic, no una
    # estimación. Se apaga solo cuando una llamada vuelve a funcionar.
    sin_credito_desde: datetime | None = None
    ultimo_error: str | None = None
    # El gasto que se está restando, y si es la cifra REAL de Anthropic (Cost
    # API con clave de administración) o la estimación por tokens.
    gasto_desde_recarga_usd: float = 0.0
    gasto_es_real: bool = False
    informe_de_coste: bool = False
    # Lo que se pagó la última vez: es lo que propone el botón de recargar.
    ultima_recarga_usd: float | None = None


class AiCreditIn(BaseModel):
    balance_usd: float = Field(ge=0, le=100_000)


def _out(state, db: Session) -> AiCreditOut:
    from app.services import ai_cost_report

    rem = remaining_usd(state)
    usage = usage_summary(db)
    gasto, es_real = gasto_desde_la_recarga(state)
    return AiCreditOut(
        balance_usd=state.balance_usd,
        spent_usd=round(state.spent_usd or 0.0, 4),
        remaining_usd=rem,
        updated_at=state.updated_at,
        recharge_url=RECHARGE_URL,
        spent_today_usd=usage["spent_today_usd"],
        spent_window_usd=usage["spent_window_usd"],
        calls_window=usage["calls_window"],
        window_days=usage["window_days"],
        last_call_at=usage["last_call_at"],
        avg_cost_per_plan_usd=usage["avg_cost_per_plan_usd"],
        plans_left=plans_left(rem, usage["avg_cost_per_plan_usd"]),
        sin_credito_desde=state.sin_credito_desde,
        ultimo_error=state.ultimo_error,
        gasto_desde_recarga_usd=gasto,
        gasto_es_real=es_real,
        informe_de_coste=ai_cost_report.disponible(),
        ultima_recarga_usd=ultima_recarga_usd(db),
    )


@router.get("", response_model=AiCreditOut)
def get_ai_credit(db: Session = Depends(get_db)) -> AiCreditOut:
    # Si hay clave de administración, se pone al día el gasto REAL de Anthropic
    # (estrangulado a una lectura por minuto dentro del propio servicio, que es
    # lo que recomienda Anthropic). Sin clave no hace nada y no cuesta nada.
    from app.services.ai_cost_report import refrescar_gasto_real

    refrescar_gasto_real(db)
    return _out(get_state(db), db)


class AiTopUpIn(BaseModel):
    amount_usd: float = Field(gt=0, le=100_000)
    note: str | None = Field(default=None, max_length=200)


@router.post("/topup", response_model=AiCreditOut)
def topup_ai_credit(body: AiTopUpIn, db: Session = Depends(get_db)) -> AiCreditOut:
    """"He recargado X $": el sistema hace la cuenta.

    Anthropic no publica el saldo por API, así que esto es lo más automático
    que puede ser sin mentir: el coach teclea LO QUE HA PAGADO —la cifra del
    recibo— y el saldo pasa a ser lo que quedaba más lo nuevo. Antes tenía que
    hacer la suma él, y una resta mal hecha dejaba el aviso de saldo bajo
    mintiendo durante semanas."""
    from app.services.ai_credit import anotar_recarga

    res = anotar_recarga(db, body.amount_usd, note=body.note)
    log_event(db, "ai_credit", 0, "ai_credit_topup", res)
    db.commit()
    return _out(get_state(db), db)


@router.get("/history")
def ai_credit_history(days: int = 30, limit: int = 60,
                      db: Session = Depends(get_db)) -> dict:
    """EN QUÉ se ha gastado: desglose por propósito, extracto de las últimas
    llamadas y las recargas pagadas."""
    from app.services.ai_credit import desglose, movimientos, recargas

    return {
        "days": max(1, min(days, 365)),
        "breakdown": desglose(db, days=days),
        "events": movimientos(db, limit=limit),
        "topups": recargas(db),
    }


@router.put("", response_model=AiCreditOut)
def set_ai_credit(body: AiCreditIn, db: Session = Depends(get_db)) -> AiCreditOut:
    """Fija el saldo EXACTO (corrección a mano). Para una recarga normal está
    `/topup`, que suma sin obligar a calcular nada."""
    state = get_state(db)
    state.balance_usd = body.balance_usd
    state.spent_usd = 0.0
    ahora = utcnow()
    state.updated_at = ahora
    # Igual que en una recarga: la cifra nueva ya está limpia, así que el
    # informe de coste vuelve a contar desde aquí (si no, se restaría dos veces).
    state.spent_real_usd = 0.0 if state.spent_real_at is not None else None
    state.spent_real_desde = ahora
    state.sin_credito_desde = None
    state.ultimo_error = None
    log_event(db, "ai_credit", state.id, "ai_credit_set", {"balance_usd": body.balance_usd})
    db.commit()
    db.refresh(state)
    return _out(state, db)
