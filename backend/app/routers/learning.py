"""Aprendizaje del coach (§13 en vivo) — transparencia y control.

El sistema destila las correcciones que el coach hace a los planes en
LECCIONES cualitativas que se inyectan en la generación. Aquí el coach puede
VERLAS (nada se aprende a escondidas) y REGENERARLAS a demanda.

GOTCHA: sin `from __future__ import annotations` (gotcha §5.1).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import PlanEdit

router = APIRouter(prefix="/api/learning", tags=["learning"],
                   dependencies=[Depends(get_current_user)])


@router.get("/lessons")
def get_lessons(db: Session = Depends(get_db)) -> dict:
    """Lecciones vigentes + cuántas ediciones capturadas hay en total."""
    from app.services.coach_lessons import MIN_EDITS, load_lessons

    data = load_lessons()
    total = int(db.scalar(select(func.count()).select_from(PlanEdit)) or 0)
    return {
        "lessons": data.get("lessons") or [],
        "updated_at": data.get("updated_at"),
        "source_edits": data.get("source_edits") or 0,
        "total_edits": total,
        "min_edits": MIN_EDITS,
    }


@router.post("/lessons/refresh")
def refresh_lessons(db: Session = Depends(get_db)) -> dict:
    """Re-destila las lecciones AHORA (modelo ligero). Errores → mensaje claro."""
    from app.services.ai.client import AIGenerationError
    from app.services.coach_lessons import distill_lessons

    try:
        data = distill_lessons(db)
    except AIGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            f"La IA no pudo destilar las lecciones: {exc}") from exc
    return {
        "lessons": data.get("lessons") or [],
        "updated_at": data.get("updated_at"),
        "source_edits": data.get("source_edits") or 0,
        "skipped": data.get("skipped"),
    }
