"""Gestión de planes y períodos por el coach (soporte de Fases 6–7).

Cierra el ciclo de vida para que el portal tenga datos reales:
- POST /api/clients/{id}/plans         crea un plan (borrador) con el contenido
                                       generado (núcleo + banco + educativo).
- POST /api/plans/{id}/publish         publica el plan → cliente pasa a active,
                                       email de bienvenida/nuevo plan (G.5).
- POST /api/clients/{id}/periods       abre un período sobre un plan publicado.
- GET  /api/clients/{id}/plans         lista de planes del cliente (para la app).
- GET  /api/clients/{id}/change-requests  cola de solicitudes de ajuste.

La generación con IA (Fase 3) produce el contenido; aquí se persiste y publica.
El endpoint de creación acepta el contenido ya ensamblado para no acoplar la
publicación a una llamada de IA en vivo (que puede orquestarse aparte).
"""


from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import ChangeRequest, Client, FeedbackDoc, Period, Plan
from app.schemas.entities import ChangeRequestOut, PeriodCreateIn
from app.services import email_templates as tpl
from app.services.audit import log_event
from app.services.email_service import EmailService, brand_from_config

router = APIRouter(tags=["plans"], dependencies=[Depends(get_current_user)])


class PlanCreateIn(BaseModel):
    month_index: int = 1
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None
    guardrail_flags: list[str] | None = None
    generated_by: str | None = None


class PlanOut(BaseModel):
    id: int
    client_id: int
    month_index: int
    version: int
    status: str
    nutrition_json: dict | None
    training_json: dict | None
    education_json: dict | None
    guardrail_flags: list[str] | None
    goal_type: str | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


def _client_or_404(db: Session, client_id: int) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return c


@router.post("/api/clients/{client_id}/plans", response_model=PlanOut,
             status_code=status.HTTP_201_CREATED)
def create_plan(client_id: int, body: PlanCreateIn, db: Session = Depends(get_db)) -> PlanOut:
    _client_or_404(db, client_id)
    # versión siguiente para ese mes
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == body.month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    client = _client_or_404(db, client_id)
    plan = Plan(
        client_id=client_id, month_index=body.month_index, version=version,
        status="draft", nutrition_json=body.nutrition_json,
        training_json=body.training_json, education_json=body.education_json,
        guardrail_flags=body.guardrail_flags, generated_by=body.generated_by,
        goal_type=client.goal_type,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_created", {"client_id": client_id, "version": version})
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


class PlanUpdateIn(BaseModel):
    """Edición manual del plan por el coach (revisión antes de enviar)."""
    nutrition_json: dict | None = None
    training_json: dict | None = None
    education_json: dict | None = None


def _sanitize_nutrition(nut: dict) -> None:
    """Topes sanos (defensa en profundidad): un valor absurdo tecleado en el
    editor —36.000.000 kcal— no debe llegar a la BD ni corromper el PDF."""
    def clamp(v, hi):
        return min(hi, max(0, v)) if isinstance(v, (int, float)) else v

    if "target_kcal" in nut:
        nut["target_kcal"] = clamp(nut.get("target_kcal"), 8000)
    m = nut.get("macros")
    if isinstance(m, dict):
        for k in ("protein_g", "carbs_g", "fat_g"):
            if k in m:
                m[k] = clamp(m.get(k), 800)
    for meal in nut.get("meals") or []:
        t = meal.get("target") if isinstance(meal, dict) else None
        if isinstance(t, dict):
            t["kcal"] = clamp(t.get("kcal"), 8000)
            for k in ("protein_g", "carbs_g", "fat_g"):
                if k in t:
                    t[k] = clamp(t.get(k), 800)


@router.patch("/api/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, body: PlanUpdateIn, db: Session = Depends(get_db)) -> PlanOut:
    """Guarda los cambios manuales del coach en el plan (núcleo/comidas/educativo).

    No re-ejecuta los guardrails: son ediciones del coach, que revisa bajo su
    criterio (el principio de seguridad aplica a lo que genera la IA, no a la
    corrección manual). El plan editado queda persistido y descargable.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            # Red de seguridad: nutrition_json se reemplaza entero; si el editor
            # manda un objeto sin `applied_adjustments` pero el plan lo tenía,
            # se conserva (si no, el portal y el PDF perderían las "Novedades").
            if field == "nutrition_json" and isinstance(value, dict):
                _sanitize_nutrition(value)  # topes sanos (kcal/macros) antes de guardar
                # Coherencia numérica: target_kcal ≡ macros ≡ suma de comidas. El
                # editor ya la mantiene; esto es la red final para que un retoque
                # manual de una comida no deje el plan descuadrado. Idempotente.
                from app.services.nutrition_scale import reconcile_nutrition

                cli = db.get(Client, plan.client_id)
                w = (cli.current_weight_kg or cli.start_weight_kg) if cli else None
                reconcile_nutrition(value, weight_kg=w)
                # Estructura de comidas: si el coach la cambió en el editor (nº de
                # tomas), la anamnesis del cliente se sincroniza — las próximas
                # regeneraciones/adaptaciones parten de ESTE reparto, no del viejo.
                meals = [m for m in (value.get("meals") or []) if isinstance(m, dict) and m.get("name")]
                if cli is not None and meals:
                    sched = [{"slot": i + 1, "name": m.get("name"), "time": m.get("time") or ""}
                             for i, m in enumerate(meals)]
                    if sched != (cli.meal_schedule or []):
                        cli.meal_schedule = sched
                        cli.meals_per_day = len(sched)
                if ("applied_adjustments" not in value
                        and isinstance(plan.nutrition_json, dict)
                        and plan.nutrition_json.get("applied_adjustments")):
                    value = {**value, "applied_adjustments": plan.nutrition_json["applied_adjustments"]}
            setattr(plan, field, value)
    log_event(db, "plan", plan.id, "plan_edited", {"fields": list(changes.keys())})
    # Editar también ACTIVA: si el coach retoca un borrador (legado), el plan
    # queda vigente al guardar — no existe el paso "Publicar".
    if plan.status == "draft":
        from app.services.plan_activation import activate_plan

        activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.get("/api/clients/{client_id}/plans", response_model=list[PlanOut])
def list_plans(client_id: int, db: Session = Depends(get_db)) -> list[PlanOut]:
    _client_or_404(db, client_id)
    plans = db.scalars(
        select(Plan).where(Plan.client_id == client_id)
        .order_by(Plan.month_index.desc(), Plan.version.desc())
    ).all()
    return [PlanOut.model_validate(p) for p in plans]


@router.post("/api/plans/{plan_id}/publish", response_model=PlanOut)
def publish_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    """LEGADO: activa un borrador antiguo. Los planes nuevos quedan ACTIVOS
    al generarse o adaptarse (services/plan_activation) — sin paso de publicar."""
    from app.services.plan_activation import activate_plan

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/api/clients/{client_id}/periods", response_model=dict,
             status_code=status.HTTP_201_CREATED)
def create_period(client_id: int, body: PeriodCreateIn, db: Session = Depends(get_db)) -> dict:
    _client_or_404(db, client_id)
    plan = db.get(Plan, body.plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado para este cliente")
    if plan.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "El plan debe estar publicado")

    # Invariante: un solo período NO analizado por cliente. La publicación del
    # plan ya abre el primer período sola. Este endpoint es IDEMPOTENTE:
    # - si ya hay uno ABIERTO, lo devuelve (no inserta un duplicado que violaría
    #   uq_period_one_open y daría un 500);
    # - si hay uno CERRADO (revisión entregada, feedback pendiente), NO abre otro
    #   —dejaría dos períodos sin analizar y "huérfano" el cierre sin feedback—:
    #   responde 409 para que el coach genere el feedback primero.
    pending = db.scalar(
        select(Period).where(Period.client_id == client_id, Period.status.in_(("open", "closed")))
        .order_by(Period.period_index.desc()).limit(1)
    )
    if pending is not None:
        if pending.status == "open":
            return {"period_id": pending.id, "period_index": pending.period_index,
                    "starts_on": pending.starts_on.isoformat(),
                    "ends_on": pending.ends_on.isoformat()}
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Hay una revisión pendiente de feedback: genera el feedback antes de abrir un período nuevo",
        )

    last = db.scalar(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc()).limit(1)
    )
    period_index = (last.period_index + 1) if last else 1
    period = Period(
        client_id=client_id, plan_id=plan.id, period_index=period_index,
        starts_on=body.starts_on, ends_on=body.starts_on + timedelta(days=body.days - 1),
        status="open",
    )
    # Savepoint + captura de IntegrityError por si dos peticiones corren a la vez
    # (doble clic): una gana y la otra reutiliza el período abierto que quedó.
    try:
        with db.begin_nested():
            db.add(period)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(Period).where(Period.client_id == client_id, Period.status == "open")
            .order_by(Period.period_index.desc()).limit(1)
        )
        if existing is None:
            raise
        return {"period_id": existing.id, "period_index": existing.period_index,
                "starts_on": existing.starts_on.isoformat(),
                "ends_on": existing.ends_on.isoformat()}
    log_event(db, "period", period.id, "period_opened", {"index": period_index})
    db.commit()
    return {"period_id": period.id, "period_index": period_index,
            "starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat()}


@router.get("/api/clients/{client_id}/change-requests", response_model=list[ChangeRequestOut])
def list_change_requests(client_id: int, db: Session = Depends(get_db)) -> list[ChangeRequestOut]:
    _client_or_404(db, client_id)
    crs = db.scalars(
        select(ChangeRequest).where(ChangeRequest.client_id == client_id)
        .order_by(ChangeRequest.created_at.desc())
    ).all()
    return [ChangeRequestOut.model_validate(c) for c in crs]


@router.post("/api/change-requests/{cr_id}/resolve", response_model=ChangeRequestOut)
def resolve_change_request(cr_id: int, db: Session = Depends(get_db)) -> ChangeRequestOut:
    from datetime import datetime, timezone

    cr = db.get(ChangeRequest, cr_id)
    if not cr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    cr.status = "resolved"
    cr.resolved_at = datetime.now(timezone.utc)
    log_event(db, "client", cr.client_id, "change_request_resolved", {"id": cr.id})
    db.commit()
    db.refresh(cr)
    return ChangeRequestOut.model_validate(cr)


# ------------------------------------------------------- feedback (cierre → informe) ----

class PeriodOut(BaseModel):
    id: int
    plan_id: int | None = None
    period_index: int
    starts_on: date
    ends_on: date
    status: str
    closing_weight_kg: float | None = None
    closing_rating: int | None = None
    closing_hardest: str | None = None
    closing_questions: str | None = None
    closing_waist_cm: float | None = None
    closing_hip_cm: float | None = None
    closing_arm_cm: float | None = None
    closing_thigh_cm: float | None = None
    feedback_id: int | None = None
    # Ajustes propuestos por el feedback IA de esta revisión (área/cambio/motivo):
    # la pestaña Planificación los muestra ANTES de pulsar "Adaptar".
    plan_adjustments: list[dict] | None = None

    model_config = {"from_attributes": True}


@router.get("/api/clients/{client_id}/periods", response_model=list[PeriodOut])
def list_periods(client_id: int, db: Session = Depends(get_db)) -> list[PeriodOut]:
    """Períodos del cliente (con datos de cierre) + si ya tienen feedback."""
    _client_or_404(db, client_id)
    periods = db.scalars(
        select(Period).where(Period.client_id == client_id)
        .order_by(Period.period_index.desc())
    ).all()
    out = []
    for p in periods:
        po = PeriodOut.model_validate(p)
        fb = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == p.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
        po.feedback_id = fb.id if fb else None
        po.plan_adjustments = (p.ai_analysis_json or {}).get("plan_adjustments") or None
        out.append(po)
    return out


@router.get("/api/periods/{period_id}/metrics")
def period_metrics(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Resumen de métricas del período (sin IA): peso, adherencia, fuerza, objetivo."""
    from app.services.feedback_service import FeedbackError, compute_period_summary

    if not db.get(Period, period_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        return compute_period_summary(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/api/periods/{period_id}/feedback")
def generate_feedback(period_id: int, db: Session = Depends(get_db)) -> dict:
    """Genera (con IA) el feedback del período cerrado y lo persiste."""
    from app.services.feedback_service import FeedbackError, build_period_feedback

    period = db.get(Period, period_id)
    if not period:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Período no encontrado")
    try:
        fb = build_period_feedback(db, period_id)
    except FeedbackError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc)},
        ) from exc
    return {
        "feedback_id": fb.id, "period_id": period_id,
        "kind": fb.kind, "content": fb.content_json,
    }


@router.get("/api/feedback/{doc_id}")
def get_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Contenido del feedback (para mostrarlo en la pestaña del coach)."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    return {
        "id": fb.id, "period_id": fb.period_id, "kind": fb.kind,
        "content": fb.content_json,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
    }


class FeedbackEditIn(BaseModel):
    """Edición manual del feedback por el coach (solo el texto)."""
    natural_analysis: str | None = None
    changes_bullets: list[str] | None = None
    answers: str | None = None
    next_objectives: list[str] | None = None
    closing_message: str | None = None


@router.patch("/api/feedback/{doc_id}")
def edit_feedback(doc_id: int, body: FeedbackEditIn, db: Session = Depends(get_db)) -> dict:
    """Guarda los cambios del coach en el texto del feedback y regenera el Word.
    Si ya estaba enviado, el cliente verá la versión editada en su Progreso."""
    from app.services.feedback_service import FeedbackError, update_feedback_text

    if not db.get(FeedbackDoc, doc_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    try:
        fb = update_feedback_text(db, doc_id, body.model_dump(exclude_unset=True))
    except FeedbackError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return {
        "id": fb.id, "content": fb.content_json,
        "sent_at": fb.sent_at.isoformat() if fb.sent_at else None,
    }


def _advance_cycle_after_feedback(db: Session, fb: FeedbackDoc) -> Client | None:
    """Marca el feedback como enviado y avanza el ciclo de la asesoría
    (review_pending → active + abre el siguiente período). NO envía email ni
    hace commit: eso lo decide cada endpoint (WhatsApp vs email)."""
    from datetime import datetime, timezone

    fb.sent_at = datetime.now(timezone.utc)
    period = db.get(Period, fb.period_id)
    client = db.get(Client, period.client_id) if period else None
    if client and client.status == "review_pending":
        client.status = "active"  # cerrado el feedback, arranca el siguiente ciclo
        # El nuevo período de 14 días empieza HOY (día del envío), no cuando
        # alguien vuelva a abrir el portal: el ciclo queda determinista.
        from app.services.periods import ensure_open_period
        ensure_open_period(db, client.id)
    if client:
        log_event(db, "client", client.id, "feedback_sent", {"feedback_id": fb.id})
    return client


def _first_name_of(client: Client) -> str:
    return ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]


@router.post("/api/feedback/{doc_id}/send")
def send_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía el feedback al cliente: lo hace visible en su portal (Progreso),
    avanza el ciclo (review_pending → active, cierra la notificación) y le avisa
    por email. Hasta este punto el feedback es un borrador que solo ve el coach."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    client = _advance_cycle_after_feedback(db, fb)

    if client:
        # Aviso al cliente (si los emails están activos)
        try:
            brand = brand_from_config(db)
            portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
            subject, html = tpl.feedback_ready(
                brand, _first_name_of(client), portal_url,
                has_training=client.package_tier != "start")
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind="feedback_ready", client=client)
        except Exception:
            pass
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat()}


@router.post("/api/feedback/{doc_id}/send-email")
def send_feedback_email(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Entrega el feedback POR EMAIL (paquetes Start/Full): el informe completo
    va en el propio correo y el ciclo avanza igual que con el envío por WhatsApp."""
    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    client = _advance_cycle_after_feedback(db, fb)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    brand = brand_from_config(db)
    subject, html = tpl.feedback_delivery(brand, _first_name_of(client), fb.content_json or {})
    email_status = EmailService(db).send(
        to=client.email, subject=subject, html=html,
        kind="feedback_delivery", client=client,
    )
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat(), "email_status": email_status}


@router.get("/api/feedback/{doc_id}/document")
def download_feedback_document(doc_id: int, db: Session = Depends(get_db)):
    """Descarga el documento Word del feedback."""
    from fastapi import Response

    from app.services.storage import abs_path

    fb = db.get(FeedbackDoc, doc_id)
    if not fb or not fb.docx_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    path = abs_path(fb.docx_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    period = db.get(Period, fb.period_id)
    idx = period.period_index if period else fb.id
    return Response(
        content=path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="feedback_periodo{idx}.docx"'},
    )


# ------------------------------------------- documentos Word del plan (Fase 7) ----

def _doc_brand(db: Session):
    from app.models import BrandConfig
    from app.services.docs.word_base import DocBrand

    cfg = db.scalar(select(BrandConfig).limit(1))
    if cfg is None:
        return DocBrand(name="Tu asesoría", color_primary="#6EE7B7",
                        color_secondary="#8B9DF7", font_family="Inter")
    logo_abs = None
    if cfg.logo_path:
        from app.services.storage import abs_path

        try:
            logo_abs = str(abs_path(cfg.logo_path))
        except Exception:
            logo_abs = None
    return DocBrand(
        name=cfg.name, color_primary=cfg.color_primary,
        color_secondary=cfg.color_secondary, font_family=cfg.font_family,
        tagline=cfg.tagline, contact_email=cfg.contact_email, logo_path=logo_abs,
    )


@router.get("/api/plans/{plan_id}/document")
def download_plan_document(plan_id: int, db: Session = Depends(get_db)):
    """Genera y descarga el plan en PDF (constructor compartido con el enlace
    público del cliente — ver services/plan_delivery)."""
    from fastapi import Response

    from app.services.plan_delivery import build_plan_pdf

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    content, media_type, filename = build_plan_pdf(db, plan, client)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/plans/{plan_id}/send-email")
def send_plan_email(plan_id: int, db: Session = Depends(get_db)) -> dict:
    """Entrega la planificación POR EMAIL (paquetes Start/Full): adjunta el PDF
    del plan y enlaza el portal de seguimiento. Equivale al envío por WhatsApp
    de los paquetes Pro, pero por correo."""
    from app.services.plan_delivery import build_plan_pdf

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # El PDF es un extra: si su generación fallara, el email con el enlace al
    # portal sigue siendo útil, así que no bloqueamos el envío por ello.
    attachments: list[tuple[str, bytes, str]] = []
    try:
        content, _media, filename = build_plan_pdf(db, plan, client)
        attachments.append((filename, content, "application/pdf"))
    except Exception:
        pass

    is_adapted = bool((plan.nutrition_json or {}).get("applied_adjustments"))
    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    _first = ((client.full_name or "").split() or [(client.email or "cliente").split("@")[0]])[0]
    subject, html = tpl.plan_delivery(brand, _first, portal_url, is_adapted, bool(attachments))
    email_status = EmailService(db).send(
        to=client.email, subject=subject, html=html, kind="plan_delivery",
        client=client, attachments=attachments or None,
    )
    log_event(db, "plan", plan.id, "plan_sent_email", {"client_id": client.id, "status": email_status})
    db.commit()
    return {"sent": email_status != "failed", "email_status": email_status,
            "attached_pdf": bool(attachments)}


# ----------------------------------------------- swap de ejercicios (Fase 8, F.5) ----

class SwapProposeOut(BaseModel):
    exercise_id: int
    name: str
    movement_pattern: str
    muscle_primary: str
    equipment: list[str]
    similarity: int


class SwapApplyIn(BaseModel):
    session_index: int
    old_exercise_id: int
    new_exercise_id: int
    permanent: bool = False
    reason: str = ""


@router.get("/api/clients/{client_id}/plans/{plan_id}/swap-options/{exercise_id}",
            response_model=list[SwapProposeOut])
def swap_options(client_id: int, plan_id: int, exercise_id: int,
                 db: Session = Depends(get_db)) -> list[SwapProposeOut]:
    """Propone 2–3 alternativas válidas para sustituir un ejercicio (F.5.1)."""
    from app.services.swap import propose_alternatives

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    alts = propose_alternatives(db, client, exercise_id)
    return [SwapProposeOut(**a.__dict__) for a in alts]


@router.post("/api/clients/{client_id}/plans/{plan_id}/swap", response_model=dict)
def swap_apply(client_id: int, plan_id: int, body: SwapApplyIn,
               db: Session = Depends(get_db)) -> dict:
    """Aplica el swap creando una nueva versión del plan (borrador) (F.5.2–4)."""
    from app.services.swap import apply_swap

    client = _client_or_404(db, client_id)
    plan = db.get(Plan, plan_id)
    if not plan or plan.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    try:
        result = apply_swap(
            db, client=client, plan=plan, session_index=body.session_index,
            old_exercise_id=body.old_exercise_id, new_exercise_id=body.new_exercise_id,
            permanent=body.permanent, reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {
        "new_plan_id": result.new_plan_id, "new_version": result.new_version,
        "group_volume_after": result.group_volume_after,
        "guardrail_flags": result.guardrail_flags,
    }


# ------------------------------------------- plantilla de anamnesis (PDF oficial) ----

@router.get("/api/anamnesis-template")
def download_anamnesis_template():
    """Descarga la plantilla oficial de anamnesis (PDF en blanco) para que el
    coach la envíe por correo al cliente."""
    from pathlib import Path

    from fastapi import Response

    path = Path(__file__).resolve().parent.parent / "assets" / "anamnesis_template.pdf"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plantilla no encontrada")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="anamnesis.pdf"'},
    )
