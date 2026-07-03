"""Endpoints PÚBLICOS del portal (sin JWT — autenticación por token firmado).

Fase 2: el flujo de alta completo del cliente.
  GET  /api/p/{token}              → estado del wizard + marca para tematizar
  POST /api/p/{token}/anamnesis    → envío del formulario (consentimiento RGPD
                                     obligatorio → genera y archiva el PDF)
  POST /api/p/{token}/anamnesis/photos → fotos corporales iniciales (1–4)

Decisión declarada (A.1.7): las fotos se suben DESPUÉS de aceptar el
consentimiento (datos de salud — primero la base legal, luego el dato).
El mínimo de 1 foto lo exige el wizard y, en Fase 3, la generación del plan.
"""



from datetime import datetime, timezone
from typing import Annotated, List
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_client_by_token
from app.models import (
    BrandConfig,
    ChangeRequest,
    Client,
    DailyLog,
    FeedbackDoc,
    Period,
    ProgressPhoto,
    WorkoutLog,
)
from app.schemas.entities import (
    AnamnesisStateOut,
    AnamnesisSubmit,
    ChangeRequestIn,
    ChangeRequestOut,
    DailyLogUpsert,
    FeedbackDocOut,
    PeriodCloseIn,
    PhotoOut,
    PortalBrand,
    PortalPlanOut,
    PortalState,
    TodayView,
)
from app.services import portal as portal_svc
from app.services.audit import log_event
from app.services.consent_pdf import generate_consent_pdf
from app.services.email_service import EmailService, brand_from_config
from app.services import email_templates as tpl
from app.services.storage import PhotoValidationError, save_photo

router = APIRouter(prefix="/api/p", tags=["portal-public"])
limiter = Limiter(key_func=get_remote_address)

MAX_INITIAL_PHOTOS = 4


def _photos_count(db: Session, client_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ProgressPhoto)
            .where(ProgressPhoto.client_id == client_id, ProgressPhoto.period_id.is_(None))
        )
        or 0
    )


def _state(db: Session, client: Client) -> AnamnesisStateOut:
    brand = db.scalar(select(BrandConfig).limit(1)) or BrandConfig()
    return AnamnesisStateOut(
        first_name=client.full_name.split()[0],
        anamnesis_done=client.consent_signed_at is not None,
        photos_count=_photos_count(db, client.id),
        brand_name=brand.name,
        color_primary=brand.color_primary,
        color_bg=brand.color_bg,
        font_family=brand.font_family,
        portal_theme=brand.portal_theme,
    )


@router.get("/{token}", response_model=AnamnesisStateOut)
@limiter.limit("60/minute")
def portal_state(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> AnamnesisStateOut:
    return _state(db, client)


@router.post("/{token}/anamnesis", response_model=AnamnesisStateOut)
@limiter.limit("10/minute")
def submit_anamnesis(
    request: Request,
    body: AnamnesisSubmit,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> AnamnesisStateOut:
    """Recibe el wizard completo. Idempotencia: una vez firmada, 409 (las
    correcciones posteriores las hace el coach con audit trail)."""
    if client.consent_signed_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La anamnesis ya fue enviada; contacta con tu coach para cambios",
        )

    data = body.model_dump()
    data.pop("consent_accepted")
    priority_zones = data.pop("priority_zones", None)
    if priority_zones:
        prefix = f"[Zonas a priorizar] {priority_zones}"
        data["lifestyle_notes"] = (
            f"{prefix}\n{data['lifestyle_notes']}" if data.get("lifestyle_notes") else prefix
        )
    data["current_weight_kg"] = data["start_weight_kg"]

    for field, value in data.items():
        setattr(client, field, value)
    client.consent_signed_at = datetime.now(timezone.utc)

    brand = db.scalar(select(BrandConfig).limit(1)) or BrandConfig()
    pdf_rel = generate_consent_pdf(
        client.id, client.full_name, client.email, brand.name, client.consent_signed_at
    )
    log_event(db, "client", client.id, "anamnesis_submitted", {"diet_mode": client.diet_mode})
    log_event(db, "client", client.id, "consent_pdf_generated", {"path": pdf_rel})
    db.commit()
    db.refresh(client)
    return _state(db, client)


@router.post("/{token}/anamnesis/photos")
@limiter.limit("20/minute")
def upload_initial_photos(
    request: Request,
files: Annotated[List[UploadFile], File(description="1–4 fotos corporales")],    kind: str = Query(default="front", pattern="^(front|side|back|detail)$"),
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    """Fotos iniciales (línea base, period_id NULL). Requiere consentimiento."""
    if client.consent_signed_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Completa primero el formulario y acepta el consentimiento",
        )
    existing = _photos_count(db, client.id)
    if existing + len(files) > MAX_INITIAL_PHOTOS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Máximo {MAX_INITIAL_PHOTOS} fotos iniciales (ya hay {existing})",
        )

    created: list[ProgressPhoto] = []
    for f in files:
        try:
            rel = save_photo(client.id, f.file.read())
        except PhotoValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        photo = ProgressPhoto(client_id=client.id, period_id=None, kind=kind, file_path=rel)
        db.add(photo)
        created.append(photo)

    db.flush()
    log_event(db, "client", client.id, "initial_photos_uploaded", {"count": len(created)})
    db.commit()
    for p in created:
        db.refresh(p)
    return [PhotoOut.model_validate(p) for p in created]


# ============================================================ portal (Fase 6) ====
# Vistas del cliente: estado, HOY, plan, diario, cierre, feedback, ajuste.
# Todas autenticadas por el token firmado (get_client_by_token).

from datetime import date as _date  # noqa: E402


@router.get("/{token}/state", response_model=PortalState)
@limiter.limit("120/minute")
def portal_state_full(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> PortalState:
    """Estado completo para arrancar el portal: período activo y marca."""
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    return PortalState(
        first_name=client.full_name.split()[0],
        status=client.status,
        diet_mode=client.diet_mode,
        has_plan=plan is not None,
        period=portal_svc.period_info(period, _date.today()),
        brand=PortalBrand(**portal_svc.brand_payload(db)),
    )


@router.get("/{token}/today", response_model=TodayView)
@limiter.limit("120/minute")
def portal_today(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> TodayView:
    """Vista HOY: qué como y qué entreno hoy. Lectura en <30 s (G.4)."""
    return TodayView(**portal_svc.build_today_view(db, client, _date.today()))


@router.get("/{token}/training", response_model=dict)
@limiter.limit("120/minute")
def portal_training(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Todas las sesiones del plan (con nombres de ejercicio) para el selector
    de la pantalla de registro de entreno."""
    return {"sessions": portal_svc.build_training_sessions(db, client)}


@router.get("/{token}/plan", response_model=PortalPlanOut)
@limiter.limit("60/minute")
def portal_plan(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> PortalPlanOut:
    """Plan completo navegable (nutrición + entrenamiento + educativo)."""
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no tienes un plan publicado")
    return PortalPlanOut(
        month_index=plan.month_index,
        nutrition=plan.nutrition_json,
        training=plan.training_json,
        education=plan.education_json,
        diet_mode=client.diet_mode,
    )


@router.put("/{token}/diary", response_model=dict)
@limiter.limit("120/minute")
def portal_diary_upsert(
    request: Request,
    body: DailyLogUpsert,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Registro diario con autosave (upsert por fecha). Autocompletado desde el
    plan en el frontend; aquí solo se persiste lo que el cliente confirma."""
    period = portal_svc.active_period(db, client.id)
    if period is None or period.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período abierto")

    log = db.scalar(
        select(DailyLog).where(
            DailyLog.period_id == period.id, DailyLog.log_date == body.log_date
        )
    )
    if log is None:
        log = DailyLog(period_id=period.id, log_date=body.log_date)
        db.add(log)
        db.flush()

    # Upsert PARCIAL: solo se tocan los campos que el cliente envía. Así un
    # guardado de comidas/diario NO borra las series, ni viceversa (autosaves
    # independientes desde distintas pantallas del portal).
    data = body.model_dump(exclude_unset=True)
    for field in (
        "weight_kg", "sleep_hours", "steps", "satiety_1_10", "water_liters",
        "diet_adherence", "diet_notes",
        "energy_1_5", "mood_1_5", "fatigue_1_5", "free_notes",
        "chosen_options_json", "option_feedback_json",
    ):
        if field in data:
            setattr(log, field, data[field])

    # Sets de entrenamiento: se reemplazan SOLO si vienen en la petición.
    if "workout_sets" in data:
        db.query(WorkoutLog).filter(WorkoutLog.daily_log_id == log.id).delete()
        for ws in body.workout_sets:
            db.add(WorkoutLog(
                daily_log_id=log.id, exercise_id=ws.exercise_id, set_number=ws.set_number,
                reps=ws.reps, weight_kg=ws.weight_kg, rpe=ws.rpe, notes=ws.notes,
            ))

    db.commit()
    return {"saved": True, "log_date": body.log_date.isoformat()}


@router.get("/{token}/diary/{log_date}", response_model=dict)
@limiter.limit("120/minute")
def portal_diary_get(
    request: Request,
    log_date: _date,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Recupera el registro de un día (para precargar el formulario)."""
    period = portal_svc.active_period(db, client.id)
    if period is None:
        return {"exists": False}
    log = db.scalar(
        select(DailyLog).where(
            DailyLog.period_id == period.id, DailyLog.log_date == log_date
        )
    )
    if log is None:
        return {"exists": False}
    sets = db.scalars(select(WorkoutLog).where(WorkoutLog.daily_log_id == log.id)).all()
    return {
        "exists": True,
        "weight_kg": log.weight_kg, "sleep_hours": log.sleep_hours,
        "steps": log.steps, "satiety_1_10": log.satiety_1_10, "water_liters": log.water_liters,
        "diet_adherence": log.diet_adherence, "diet_notes": log.diet_notes,
        "energy_1_5": log.energy_1_5, "mood_1_5": log.mood_1_5,
        "fatigue_1_5": log.fatigue_1_5, "free_notes": log.free_notes,
        "chosen_options_json": log.chosen_options_json,
        "workout_sets": [
            {"exercise_id": s.exercise_id, "set_number": s.set_number,
             "reps": s.reps, "weight_kg": s.weight_kg, "rpe": s.rpe}
            for s in sets
        ],
    }


@router.get("/{token}/workout-history", response_model=dict)
@limiter.limit("120/minute")
def portal_workout_history(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Historial de series por ejercicio (sesiones ANTERIORES, excluye hoy), para
    mostrar la referencia 'última vez' en el tracker de entreno (estilo iron)."""
    from datetime import date as _date

    rows = db.execute(
        select(DailyLog.log_date, WorkoutLog.exercise_id, WorkoutLog.set_number,
               WorkoutLog.weight_kg, WorkoutLog.reps)
        .join(WorkoutLog, WorkoutLog.daily_log_id == DailyLog.id)
        .join(Period, Period.id == DailyLog.period_id)
        .where(Period.client_id == client.id)
        .order_by(DailyLog.log_date.desc(), WorkoutLog.set_number)
    ).all()
    today = _date.today()
    hist: dict[int, dict[str, list]] = {}
    for log_date, ex_id, set_number, weight, reps in rows:
        if log_date == today:
            continue
        by_date = hist.setdefault(ex_id, {})
        by_date.setdefault(log_date.isoformat(), []).append(
            {"set": set_number, "weight_kg": weight, "reps": reps}
        )
    out: dict[str, list] = {}
    for ex_id, by_date in hist.items():
        for dt in sorted(by_date.keys(), reverse=True)[:5]:
            out.setdefault(str(ex_id), []).append({"date": dt, "sets": by_date[dt]})
    return {"history": out}


@router.post("/{token}/close", response_model=dict)
@limiter.limit("20/minute")
def portal_close_period(
    request: Request,
    body: PeriodCloseIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Cierre del período (desde día 14). Dispara el pipeline en Fase 7;
    aquí persiste el cierre y pasa el cliente a awaiting→review."""
    period = portal_svc.active_period(db, client.id)
    if period is None or period.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período abierto")

    info = portal_svc.period_info(period, _date.today())
    if not info or not info["can_close"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "El cierre estará disponible a partir del día 14 del período",
        )

    for field in (
        "closing_weight_kg", "closing_rating", "closing_hardest", "closing_questions",
        "closing_waist_cm", "closing_hip_cm", "closing_arm_cm", "closing_thigh_cm",
        "closing_feelings_json", "adherence_diet_0_10", "adherence_training_0_10",
        "free_meals_count", "closing_changes", "closing_next_goal",
    ):
        setattr(period, field, getattr(body, field))
    period.status = "closed"

    # El cliente pasa a esperar la revisión del coach (review_pending)
    if client.status in ("active", "awaiting_feedback", "at_risk"):
        client.status = "review_pending"

    log_event(db, "client", client.id, "period_closed",
              {"period_index": period.period_index, "rating": body.closing_rating})
    db.commit()
    return {"closed": True, "period_index": period.period_index}


@router.post("/{token}/close/photos")
@limiter.limit("20/minute")
def portal_close_photos(
    request: Request,
 files: Annotated[List[UploadFile], File(description="hasta 4 fotos de cierre")],   kind: str = Query(default="front", pattern="^(front|side|back|detail)$"),
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    """Fotos del cierre (asociadas al período actual)."""
    period = portal_svc.active_period(db, client.id)
    if period is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No tienes un período activo")

    existing = db.scalar(
        select(func.count()).select_from(ProgressPhoto)
        .where(ProgressPhoto.client_id == client.id, ProgressPhoto.period_id == period.id)
    ) or 0
    if existing + len(files) > 4:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Máximo 4 fotos por cierre (ya hay {existing})",
        )

    created: list[ProgressPhoto] = []
    for f in files:
        try:
            rel = save_photo(client.id, f.file.read())
        except PhotoValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        photo = ProgressPhoto(client_id=client.id, period_id=period.id, kind=kind, file_path=rel)
        db.add(photo)
        created.append(photo)
    db.flush()
    log_event(db, "client", client.id, "closing_photos_uploaded", {"count": len(created)})
    db.commit()
    for p in created:
        db.refresh(p)
    return [PhotoOut.model_validate(p) for p in created]


@router.get("/{token}/feedback", response_model=list[FeedbackDocOut])
@limiter.limit("60/minute")
def portal_feedback(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> list[FeedbackDocOut]:
    """Historial de feedbacks ENVIADOS del cliente (más reciente primero).

    Solo los que el coach ha enviado (sent_at). Los borradores en revisión no
    se muestran al cliente."""
    periods = db.scalars(select(Period.id).where(Period.client_id == client.id)).all()
    if not periods:
        return []
    docs = db.scalars(
        select(FeedbackDoc)
        .where(FeedbackDoc.period_id.in_(periods), FeedbackDoc.sent_at.isnot(None))
        .order_by(FeedbackDoc.id.desc())
    ).all()
    return [FeedbackDocOut.model_validate(d) for d in docs]


@router.post("/{token}/change-request", response_model=ChangeRequestOut)
@limiter.limit("10/minute")
def portal_change_request(
    request: Request,
    body: ChangeRequestIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> ChangeRequestOut:
    """'Solicitar ajuste': crea un change_request y alerta al coach por email."""
    cr = ChangeRequest(client_id=client.id, message=body.message.strip(), status="open")
    db.add(cr)
    db.flush()
    log_event(db, "client", client.id, "change_request_created", {"id": cr.id})

    # Alerta al coach (G.5)
    from app.config import settings

    coach_to = settings.smtp_from or settings.smtp_user
    if coach_to:
        brand = brand_from_config(db)
        subject, html = tpl.coach_change_request(
            brand, client.full_name, cr.message,
            f"{settings.public_base_url}/clientes/{client.id}",
        )
        EmailService(db).send(to=coach_to, subject=subject, html=html,
                              kind="coach_change_request", client=client)

    db.commit()
    db.refresh(cr)
    return ChangeRequestOut.model_validate(cr)
