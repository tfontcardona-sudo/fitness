"""Biblioteca de planificaciones: el pool de planes de clientes + los modelos.

Todo lo de aquí funciona a 0 créditos: copiar, guardar como modelo y aplicar
son operaciones deterministas (los números del destino los pone metrics).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client, Plan, PlanTemplate
from app.services.audit import log_event
from app.services.plan_library import (
    PlanLibraryError,
    copiar_a_cliente,
    guardar_modelo,
    pool_de_planes,
    resumen_plan,
)

router = APIRouter(prefix="/api/plan-library", tags=["plan-library"],
                   dependencies=[Depends(get_current_user)])


@router.get("")
def library(db: Session = Depends(get_db)) -> dict:
    """Todo lo que se puede usar como punto de partida, con su resumen de una
    línea: los MODELOS guardados y el plan vigente de cada cliente."""
    templates = [{
        "id": t.id, "title": t.title, "summary": t.summary,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in db.scalars(select(PlanTemplate).order_by(PlanTemplate.title))]
    return {"templates": templates, "client_plans": pool_de_planes(db)}


class TemplateIn(BaseModel):
    plan_id: int
    title: str = Field(min_length=1, max_length=120)


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn, db: Session = Depends(get_db)) -> dict:
    plan = db.get(Plan, body.plan_id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    try:
        tpl = guardar_modelo(db, plan, body.title)
    except PlanLibraryError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    db.commit()
    return {"id": tpl.id, "title": tpl.title, "summary": tpl.summary}


class TemplateRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@router.patch("/templates/{template_id}")
def rename_template(template_id: int, body: TemplateRename,
                    db: Session = Depends(get_db)) -> dict:
    tpl = db.get(PlanTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modelo no encontrado")
    tpl.title = body.title.strip()[:120]
    log_event(db, "plan_template", tpl.id, "template_renamed", {"title": tpl.title})
    db.commit()
    return {"id": tpl.id, "title": tpl.title, "summary": tpl.summary}


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)) -> None:
    tpl = db.get(PlanTemplate, template_id)
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modelo no encontrado")
    log_event(db, "plan_template", tpl.id, "template_deleted", {"title": tpl.title})
    db.delete(tpl)
    db.commit()


class ApplyIn(BaseModel):
    client_id: int
    # Exactamente uno de los dos: el plan de otro cliente, o un modelo.
    plan_id: int | None = None
    template_id: int | None = None


@router.post("/apply")
def apply_from_library(body: ApplyIn, db: Session = Depends(get_db)) -> dict:
    """Crea un BORRADOR para el cliente a partir de otro plan o de un modelo.

    0 créditos. La estructura viene del origen; kcal, macros, comidas y banco
    se recalculan y reescalan para el DESTINO. Devuelve el plan con los avisos
    de seguridad (alérgenos del destino, ejercicios que no encajan…).
    """
    if (body.plan_id is None) == (body.template_id is None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Elige un plan de un cliente O un modelo.")
    client = db.get(Client, body.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    if body.plan_id is not None:
        origen_plan = db.get(Plan, body.plan_id)
        if origen_plan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan de origen no encontrado")
        if origen_plan.client_id == client.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "Es el plan de este mismo cliente.")
        origen_nombre = db.scalar(
            select(Client.full_name).where(Client.id == origen_plan.client_id)
        ) or "otro cliente"
        nutrition, training, education = (
            origen_plan.nutrition_json, origen_plan.training_json,
            origen_plan.education_json)
        origen = f"el plan de {origen_nombre}"
    else:
        tpl = db.get(PlanTemplate, body.template_id)
        if tpl is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Modelo no encontrado")
        nutrition, training, education = (
            tpl.nutrition_json, tpl.training_json, tpl.education_json)
        origen = f"el modelo «{tpl.title}»"

    try:
        plan, avisos = copiar_a_cliente(
            db, client, nutrition=nutrition, training=training,
            education=education, origen=origen)
    except PlanLibraryError as exc:
        detalle = ({"message": str(exc), "missing": exc.missing}
                   if exc.missing else str(exc))
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detalle) from exc
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": plan.guardrail_flags or [],
        "nutrition": plan.nutrition_json, "training": plan.training_json,
        "education": plan.education_json, "review": None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "published_at": None,
        "warnings": avisos,
        "summary": resumen_plan(plan.nutrition_json, plan.training_json,
                                plan.goal_type),
    }
