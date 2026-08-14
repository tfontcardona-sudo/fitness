"""Pool de rutinas/planificaciones del coach (/api/templates).

Carpetas fijas (services/templates.CATEGORIES) con rutinas sembradas de fábrica,
subidas (PDF/Word externos re-maquetados al diseño de la marca) o creadas a
mano. Todo editable con el editor simple de la página Rutinas. "Usar con un
cliente" crea el perfil (o usa uno existente) con la rutina como plan BORRADOR.
"""
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client, Plan, PlanTemplate
from app.security import new_portal_token
from app.services.audit import log_event
from app.services.templates import (
    CATEGORIES, CATEGORY_GOAL, CATEGORY_KEYS, TemplateError,
    import_template_from_file, resolve_training, template_document,
)

router = APIRouter(prefix="/api/templates", tags=["templates"],
                   dependencies=[Depends(get_current_user)])

MAX_UPLOAD_MB = 15


# ------------------------------------------------------------- schemas ----
class TemplateListItem(BaseModel):
    id: int
    category: str
    title: str
    case_note: str | None = None
    level: str | None = None
    days_per_week: int | None = None
    training_place: str | None = None
    source: str
    has_nutrition: bool = False

    class Config:
        from_attributes = True


class TemplateOut(TemplateListItem):
    training_json: dict | None = None
    nutrition_json: dict | None = None


class TemplateIn(BaseModel):
    """Alta/edición desde el editor simple. Los ejercicios llegan con
    exercise_id (el editor elige de la biblioteca)."""

    category: str | None = None
    title: str | None = Field(default=None, min_length=2, max_length=160)
    case_note: str | None = None
    level: str | None = None
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    training_place: str | None = None
    training_json: dict | None = None


class NewClientIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str | None = None
    package_tier: str = "train"


class UseTemplateIn(BaseModel):
    """O un cliente existente o los datos mínimos para crear uno nuevo."""

    client_id: int | None = None
    new_client: NewClientIn | None = None


class UseTemplateOut(BaseModel):
    client_id: int
    plan_id: int
    created_client: bool


# ------------------------------------------------------------- lectura ----
@router.get("/categories")
def list_categories(db: Session = Depends(get_db)) -> list[dict]:
    counts = dict(db.execute(
        select(PlanTemplate.category, func.count()).group_by(PlanTemplate.category)
    ).all())
    return [{**c, "count": counts.get(c["key"], 0)} for c in CATEGORIES]


@router.get("", response_model=list[TemplateListItem])
def list_templates(
    category: str | None = Query(default=None), db: Session = Depends(get_db),
) -> list[TemplateListItem]:
    q = select(PlanTemplate).order_by(PlanTemplate.title)
    if category:
        q = q.where(PlanTemplate.category == category)
    out = []
    for t in db.scalars(q):
        item = TemplateListItem.model_validate(t)
        item.has_nutrition = bool(t.nutrition_json)
        out.append(item)
    return out


def _get_or_404(db: Session, template_id: int) -> PlanTemplate:
    t = db.get(PlanTemplate, template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rutina no encontrada")
    return t


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)) -> TemplateOut:
    t = _get_or_404(db, template_id)
    out = TemplateOut.model_validate(t)
    out.has_nutrition = bool(t.nutrition_json)
    return out


# ----------------------------------------------------- alta/edición/baja ----
def _apply(t: PlanTemplate, body: TemplateIn, db: Session) -> None:
    if body.category is not None:
        if body.category not in CATEGORY_KEYS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Carpeta desconocida")
        t.category = body.category
    if body.title is not None:
        t.title = body.title.strip()
    if body.case_note is not None:
        t.case_note = body.case_note.strip() or None
    if body.level is not None:
        t.level = body.level if body.level in ("beginner", "intermediate", "advanced") else None
    if body.days_per_week is not None:
        t.days_per_week = body.days_per_week
    if body.training_place is not None:
        t.training_place = body.training_place if body.training_place in ("gym", "home") else "gym"
    if body.training_json is not None:
        try:
            # Normaliza y valida (ids existentes, defaults, sesiones no vacías)
            t.training_json = resolve_training(db, body.training_json)
        except TemplateError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        if body.days_per_week is None:
            t.days_per_week = len(t.training_json.get("sessions", [])) or t.days_per_week


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateIn, db: Session = Depends(get_db)) -> TemplateOut:
    if not body.category or body.category not in CATEGORY_KEYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Falta la carpeta")
    if not body.title:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Falta el título")
    t = PlanTemplate(category=body.category, title="", source="manual",
                     goal_type=CATEGORY_GOAL.get(body.category), training_place="gym")
    _apply(t, body, db)
    if not t.training_json:
        # Esqueleto editable: una sesión vacía no es válida, así que se arranca
        # con la mínima estructura y el editor la completa.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La rutina necesita al menos una sesión con ejercicios")
    db.add(t)
    db.commit()
    db.refresh(t)
    log_event(db, "template", t.id, "template_created", {"category": t.category})
    db.commit()
    out = TemplateOut.model_validate(t)
    out.has_nutrition = bool(t.nutrition_json)
    return out


@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, body: TemplateIn, db: Session = Depends(get_db)) -> TemplateOut:
    t = _get_or_404(db, template_id)
    _apply(t, body, db)
    db.commit()
    db.refresh(t)
    out = TemplateOut.model_validate(t)
    out.has_nutrition = bool(t.nutrition_json)
    return out


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)) -> Response:
    t = _get_or_404(db, template_id)
    db.delete(t)
    log_event(db, "template", template_id, "template_deleted", {"title": t.title})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------- documento con la marca ----
@router.get("/{template_id}/document")
def template_doc(
    template_id: int,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
):
    """La plantilla renderizada con el dossier de la MARCA (mismo motor que los
    planes de clientes): así cualquier plan externo subido sale re-maquetado."""
    t = _get_or_404(db, template_id)
    content, media, filename = template_document(db, t, fmt=format)
    return Response(content=content, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# --------------------------------------------------- usar con un cliente ----
@router.post("/{template_id}/use", response_model=UseTemplateOut)
def use_template(template_id: int, body: UseTemplateIn, db: Session = Depends(get_db)) -> UseTemplateOut:
    """Copia la rutina al perfil de un cliente como plan BORRADOR. Con
    `new_client` crea el perfil en el momento (alta mínima, ficha pre-rellenada
    con lo que la rutina ya sabe: objetivo, nivel, días, lugar)."""
    t = _get_or_404(db, template_id)
    if not t.training_json:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La rutina está vacía")

    created = False
    if body.client_id is not None:
        client = db.get(Client, body.client_id)
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    elif body.new_client is not None:
        email = body.new_client.email.strip().lower()
        if db.scalar(select(Client).where(func.lower(Client.email) == email)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")
        client = Client(
            full_name=body.new_client.full_name.strip(),
            email=email,
            phone=body.new_client.phone,
            package_tier=body.new_client.package_tier,
            billing_period="1m",
            status="onboarding",
            portal_token="pendiente",
            # Pre-relleno con lo que la rutina ya sabe del caso; la anamnesis
            # del cliente lo afinará (y manda sobre esto).
            goal_type=t.goal_type,
            level=t.level,
            training_days=t.days_per_week,
            training_place=t.training_place,
        )
        db.add(client)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")
        client.portal_token = new_portal_token(client.id)
        log_event(db, "client", client.id, "client_created",
                  {"by": "coach", "from_template": t.id})
        created = True
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Indica un cliente existente o los datos del nuevo")

    month = (db.scalar(select(func.max(Plan.month_index)).where(Plan.client_id == client.id)) or 0) + 1
    plan = Plan(
        client_id=client.id, month_index=month, version=1, status="draft",
        training_json=t.training_json, nutrition_json=t.nutrition_json,
        education_json=None, guardrail_flags=[], generated_by="template",
        goal_type=t.goal_type or client.goal_type,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_from_template",
              {"template_id": t.id, "template_title": t.title, "client_id": client.id})
    db.commit()

    # Acceso al portal del cliente NUEVO (mismo comportamiento que el alta
    # normal): nunca bloquea — sin email configurado, el coach lo reenvía luego.
    if created:
        try:
            from app.services.portal_access import send_portal_access

            send_portal_access(db, client)
            db.commit()
        except Exception:
            db.rollback()

    return UseTemplateOut(client_id=client.id, plan_id=plan.id, created_client=created)


# ------------------------------------------------------- importar archivo ----
@router.post("/import", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def import_template(
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TemplateOut:
    """Sube una rutina/planificación YA HECHA (PDF o Word externo): la IA extrae
    el entrenamiento, lo mapea a la biblioteca y queda en la carpeta con el
    diseño de la marca (editable). La dieta de documentos externos NO se
    importa: la nutrición se genera con la anamnesis de cada cliente."""
    from app.services.ai.client import AIGenerationError

    if category not in CATEGORY_KEYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Carpeta desconocida")
    raw = file.file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"El archivo supera {MAX_UPLOAD_MB} MB")
    try:
        t = import_template_from_file(db, filename=file.filename or "",
                                      raw=raw, category=category)
    except TemplateError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except AIGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            f"No se pudo leer el documento con IA: {exc}") from exc
    db.add(t)
    db.commit()
    db.refresh(t)
    log_event(db, "template", t.id, "template_imported",
              {"category": t.category, "filename": file.filename})
    db.commit()
    out = TemplateOut.model_validate(t)
    out.has_nutrition = bool(t.nutrition_json)
    return out
