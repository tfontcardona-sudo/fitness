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
        # Tandas anteriores: se ve cómo ha ido afinándose el criterio aprendido.
        "history": data.get("history") or [],
    }


@router.get("/patterns")
def get_patterns(db: Session = Depends(get_db)) -> dict:
    """LOS PATRONES: qué campos corrige siempre, qué cambia por qué y qué no
    toca nunca. Contado sobre sus propias ediciones, sin gastar un crédito —
    por eso se puede pedir tantas veces como haga falta."""
    from app.services import coach_patterns

    datos = coach_patterns.resumen(db)
    datos["sugerencia_modelo"] = coach_patterns.sugerencia_de_modelo(db)
    return datos


@router.post("/patterns/model")
def crear_modelo_desde_patrones(db: Session = Depends(get_db)) -> dict:
    """Crea el MODELO de plan que sale de sus patrones: la estructura de un plan
    suyo de verdad, con una nota de qué revisar al aplicarlo (lo que siempre
    acaba cambiando). 0 créditos: es una copia y unas cuentas."""
    from app.models import Plan, PlanTemplate
    from app.services import coach_patterns
    from app.services.audit import log_event

    sug = coach_patterns.sugerencia_de_modelo(db)
    if not sug:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Todavía no hay patrones suficientes: corrige unos cuantos planes "
            "más y el sistema sabrá qué dejarte abierto.")
    base = db.get(Plan, sug["plan_id"])
    if base is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "El plan del que salía el modelo ya no existe.")
    nota = coach_patterns.nota_del_modelo(sug)
    tpl = PlanTemplate(
        title=sug["titulo"],
        summary=(f"{sug['resumen']} · {nota}")[:200] if sug["resumen"] else nota[:200],
        nutrition_json=base.nutrition_json,
        training_json=base.training_json,
        education_json=base.education_json,
    )
    db.add(tpl)
    db.flush()
    log_event(db, "learning", tpl.id, "plan_template_from_patterns",
              {"plan_id": base.id, "abierto": [c["signal"] for c in sug["abierto"]]})
    db.commit()
    db.refresh(tpl)
    return {"id": tpl.id, "title": tpl.title, "summary": tpl.summary,
            "abierto": sug["abierto"], "fijo": sug["fijo"], "nota": nota}


@router.delete("/lessons/{index}")
def delete_lesson(index: int, db: Session = Depends(get_db)) -> dict:
    """Borra UNA lección con la que el coach no está de acuerdo — control
    total: el sistema no puede imponerle un criterio mal aprendido."""
    import json
    from datetime import datetime, timezone

    from app.services.audit import log_event
    from app.services.coach_lessons import _sidecar_path, _slug_marca, load_lessons

    # La lección se borra del sidecar de la marca en la que está trabajando el
    # coach: cada negocio tiene el suyo.
    _slug = _slug_marca(db)
    data = load_lessons(_slug)
    lessons = list(data.get("lessons") or [])
    if not (0 <= index < len(lessons)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa lección ya no existe")
    quitada = lessons.pop(index)
    data["lessons"] = lessons
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _sidecar_path(_slug).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log_event(db, "learning", 0, "coach_lesson_deleted", {"lesson": quitada[:200]})
    db.commit()
    return {"lessons": lessons, "removed": quitada}


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
