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
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel
from slowapi import Limiter
from app.ratelimit import client_key
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.security import hash_password, verify_password

from app.config import settings
from app.db import get_db
from app.deps import get_client_by_token
from app.models import (
    BrandConfig,
    ChangeRequest,
    Client,
    DailyLog,
    Exercise,
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
    PushKeyOut,
    PushPendingOut,
    PushSubscribeIn,
    PushUnsubscribeIn,
    TodayView,
)
from app.services import portal as portal_svc
from app.services import push as push_svc
from app.services.audit import log_event
from app.services.consent_pdf import generate_consent_pdf
from app.services.email_service import EmailService, brand_from_config
from app.services import email_templates as tpl
from app.services.metrics import epley_1rm, weight_trend
from app.services.storage import PhotoValidationError, abs_path, save_photo

router = APIRouter(prefix="/api/p", tags=["portal-public"])
limiter = Limiter(key_func=client_key)

MAX_INITIAL_PHOTOS = 4

# Hash fijo para igualar el tiempo del login cuando el email no existe/sin clave.
_DUMMY_HASH = hash_password("timing-equalizer-not-a-real-password")


def _first_name(client: Client) -> str:
    """Primer nombre seguro (nunca IndexError con nombre en blanco)."""
    parts = (client.full_name or "").split()
    return parts[0] if parts else (client.email or "Cliente")


class PortalLoginIn(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=dict)
@limiter.limit("15/minute")
def portal_login(request: Request, body: PortalLoginIn, db: Session = Depends(get_db)) -> dict:
    """Login del cliente por email + contraseña. Devuelve su token de portal (el
    mecanismo interno de acceso). Mensaje genérico ante cualquier fallo para no
    revelar si el email existe."""
    email = (body.email or "").strip().lower()
    client = db.scalar(select(Client).where(func.lower(Client.email) == email)) if email else None
    # Tiempo constante: si no hay cliente/hash, se verifica igualmente contra un
    # hash dummy para no filtrar por temporización qué emails son clientes.
    if client is not None and client.portal_password_hash:
        ok = verify_password(body.password or "", client.portal_password_hash)
    else:
        verify_password(body.password or "", _DUMMY_HASH)
        ok = False
    if not ok or client is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos")
    name = (client.full_name or client.email or "").split()
    return {"token": client.portal_token, "first_name": name[0] if name else client.email}


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
        first_name=_first_name(client),
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
    # Seguimiento autónomo: si el cliente entra sin período abierto (p. ej. el
    # anterior se cerró ayer), se abre el siguiente aquí mismo.
    from app.services.periods import ensure_open_period

    ensure_open_period(db, client.id, commit=True)
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    return PortalState(
        first_name=_first_name(client),
        status=client.status,
        diet_mode=client.diet_mode,
        has_plan=plan is not None,
        period=portal_svc.period_info(period, portal_svc.today_local()),
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
    return TodayView(**portal_svc.build_today_view(db, client, portal_svc.today_local()))


@router.get("/{token}/training", response_model=dict)
@limiter.limit("120/minute")
def portal_training(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Todas las sesiones del plan (con nombres de ejercicio) para el selector
    de la pantalla de registro de entreno. Incluye los cambios aplicados en la
    última adaptación del plan ("Novedades de tu plan") y la SEMANA del
    mesociclo que el cliente vive hoy (fase, carga, RIR y el porqué): los pesos
    sugeridos de cada ejercicio ya vienen ajustados a esa semana."""
    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    changes = None
    if plan is not None and plan.status == "published":
        changes = (plan.nutrition_json or {}).get("applied_adjustments") or None
    week = portal_svc.current_training_week(db, plan, portal_svc.today_local())
    if week:
        week = {**week, "started_on": week["started_on"].isoformat()}
    # El cliente ha abierto su rutina: si tenía un plan nuevo sin ver, apaga el
    # aviso (y con él el badge del icono de la PWA en la próxima sincronización).
    if plan is not None and client.plan_notice_pending:
        client.plan_notice_pending = False
        db.commit()
    return {
        "sessions": portal_svc.build_training_sessions(db, client),
        "plan_changes": changes,
        "week": week,
    }


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


@router.get("/{token}/plan.pdf")
@limiter.limit("10/minute")
def portal_plan_pdf(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
):
    """El plan PUBLICADO del cliente en PDF, por su token (sin login).

    Pensado para el botón "Enviar plan por WhatsApp" del coach: el mensaje
    lleva este enlace y el cliente descarga su PDF con un toque."""
    from fastapi import Response

    from app.services.plan_delivery import build_plan_pdf

    period = portal_svc.active_period(db, client.id)
    plan = (
        portal_svc.published_plan_for_period(db, period)
        if period
        else portal_svc.latest_published_plan(db, client.id)
    )
    if plan is None or plan.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aún no tienes un plan publicado")

    content, media_type, filename = build_plan_pdf(db, plan, client)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
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

    # La fecha debe caer DENTRO del período y no ser futura: si no, el cliente
    # podría inflar su adherencia con días que no han pasado o registrar fuera de
    # rango (falsea métricas, feedback y el disparador de "en riesgo").
    upper = min(period.ends_on, portal_svc.today_local())
    if not (period.starts_on <= body.log_date <= upper):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La fecha del registro está fuera de tu período actual",
        )

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
    today = portal_svc.today_local()
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


@router.get("/{token}/progress", response_model=dict)
@limiter.limit("120/minute")
def portal_progress(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Progreso del cliente para que lo vea ÉL en el portal (motivación/retención):
    evolución del peso, medidas y adherencia por período, progreso de fuerza y
    fotos antes/después. Todo derivado de lo que ya registra; no expone nada del
    coach ni otros clientes (autenticado por su token)."""
    # --- Peso: serie diaria del propio diario -------------------------------
    weight_rows = db.execute(
        select(DailyLog.log_date, DailyLog.weight_kg)
        .join(Period, Period.id == DailyLog.period_id)
        .where(Period.client_id == client.id, DailyLog.weight_kg.isnot(None))
        .order_by(DailyLog.log_date)
    ).all()
    series = [{"d": d.isoformat(), "kg": round(w, 1)} for d, w in weight_rows]
    trend = weight_trend([(d, w) for d, w in weight_rows])
    start_kg = client.start_weight_kg if client.start_weight_kg is not None else trend.start_kg
    current_kg = (series[-1]["kg"] if series else None)
    if current_kg is None:
        current_kg = client.current_weight_kg

    # --- Medidas y adherencia por período cerrado ---------------------------
    periods = db.scalars(
        select(Period)
        .where(Period.client_id == client.id, Period.status.in_(("closed", "analyzed")))
        .order_by(Period.period_index)
    ).all()
    measurements: list[dict] = []
    adherence: list[dict] = []
    for p in periods:
        label = p.ends_on.isoformat()
        if any(v is not None for v in (p.closing_waist_cm, p.closing_hip_cm,
                                       p.closing_arm_cm, p.closing_thigh_cm, p.closing_weight_kg)):
            measurements.append({
                "label": label, "weight_kg": p.closing_weight_kg,
                "waist_cm": p.closing_waist_cm, "hip_cm": p.closing_hip_cm,
                "arm_cm": p.closing_arm_cm, "thigh_cm": p.closing_thigh_cm,
            })
        if p.adherence_diet_0_10 is not None or p.adherence_training_0_10 is not None:
            adherence.append({
                "label": label,
                "diet_0_10": p.adherence_diet_0_10,
                "training_0_10": p.adherence_training_0_10,
            })

    # --- Fuerza: mejor e1RM por ejercicio (primera sesión vs mejor) ----------
    strength_rows = db.execute(
        select(DailyLog.log_date, WorkoutLog.exercise_id, WorkoutLog.weight_kg,
               WorkoutLog.reps, Exercise.canonical_name)
        .join(WorkoutLog, WorkoutLog.daily_log_id == DailyLog.id)
        .join(Period, Period.id == DailyLog.period_id)
        .join(Exercise, Exercise.id == WorkoutLog.exercise_id)
        .where(Period.client_id == client.id,
               WorkoutLog.weight_kg.isnot(None), WorkoutLog.reps.isnot(None))
        .order_by(DailyLog.log_date)
    ).all()
    by_ex: dict[int, dict] = {}
    for log_date, ex_id, w, reps, name in strength_rows:
        if not w or not reps:
            continue
        e = epley_1rm(w, reps)
        rec = by_ex.setdefault(ex_id, {"name": name, "first": None,
                                       "first_date": None, "best": 0.0, "sessions": set()})
        rec["sessions"].add(log_date)
        if rec["first"] is None:
            rec["first"], rec["first_date"] = e, log_date
        elif log_date == rec["first_date"] and e > rec["first"]:
            rec["first"] = e  # mejor serie de la primera sesión
        if e > rec["best"]:
            rec["best"] = e
    strength: list[dict] = []
    for rec in by_ex.values():
        if len(rec["sessions"]) < 2 or not rec["first"]:
            continue  # hace falta progreso en ≥2 sesiones para que signifique algo
        strength.append({
            "exercise": rec["name"],
            "first_e1rm": round(rec["first"], 1),
            "best_e1rm": round(rec["best"], 1),
            "gain_pct": round((rec["best"] - rec["first"]) / rec["first"] * 100, 1),
            "sessions": len(rec["sessions"]),
        })
    strength.sort(key=lambda s: s["gain_pct"], reverse=True)
    strength = strength[:5]

    # --- Fotos: primera tanda vs última tanda (antes / después) -------------
    photo_rows = db.scalars(
        select(ProgressPhoto)
        .where(ProgressPhoto.client_id == client.id)
        .order_by(ProgressPhoto.taken_at)
    ).all()
    photos: dict = {"first": [], "last": [], "first_date": None, "last_date": None}
    if photo_rows:
        first_dt = photo_rows[0].taken_at.date()
        last_dt = photo_rows[-1].taken_at.date()
        photos["first_date"] = first_dt.isoformat()
        photos["first"] = [{"id": p.id, "kind": p.kind} for p in photo_rows if p.taken_at.date() == first_dt]
        if last_dt != first_dt:
            photos["last_date"] = last_dt.isoformat()
            photos["last"] = [{"id": p.id, "kind": p.kind} for p in photo_rows if p.taken_at.date() == last_dt]

    return {
        "weight": {
            "start_kg": start_kg, "current_kg": current_kg, "goal_kg": client.goal_weight_kg,
            "delta_kg": trend.delta_kg, "weekly_rate_kg": trend.weekly_rate_kg,
            "series": series,
        },
        "measurements": measurements,
        "adherence": adherence,
        "strength": strength,
        "photos": photos,
    }


@router.get("/{token}/photos/{photo_id}")
@limiter.limit("240/minute")
def portal_photo(
    request: Request,
    photo_id: int,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
):
    """Sirve una foto de progreso del PROPIO cliente (por su token). Comprueba
    que la foto le pertenece antes de entregarla."""
    p = db.get(ProgressPhoto, photo_id)
    if not p or p.client_id != client.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto no encontrada")
    path = abs_path(p.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    ext = path.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
             ".webp": "image/webp"}.get(ext, "application/octet-stream")
    return Response(
        content=path.read_bytes(), media_type=media,
        headers={"Cache-Control": "private, max-age=86400",
                 "Content-Disposition": f'inline; filename="progreso_{photo_id}{ext}"'},
    )


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

    info = portal_svc.period_info(period, portal_svc.today_local())
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


# ------------------------------------------------- Web Push + PWA (§8.1) ----

@router.get("/{token}/manifest.webmanifest")
@limiter.limit("60/minute")
def portal_manifest(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
):
    """Manifest PWA POR CLIENTE: start_url apunta a SU portal (/p/{token}), de
    modo que al instalar la app en el móvil se abre directamente su seguimiento
    sin tener que guardar el enlace. Tematizado con la marca."""
    from fastapi.responses import JSONResponse

    brand = portal_svc.brand_payload(db)
    light = brand.get("portal_theme") == "light"
    # Identidad de la app instalada: "DQR" grande (etiqueta bajo el icono) y
    # "Assessories" como subtítulo (nombre completo en splash/ajustes).
    manifest = {
        "name": "DQR · Assessories",
        "short_name": "DQR",
        "description": "Tu portal de seguimiento: entreno, diario y revisión quincenal.",
        "lang": "es",
        "start_url": f"/p/{client.portal_token}",
        "scope": f"/p/{client.portal_token}",
        "display": "standalone",
        "background_color": "#F6F1E7" if light else "#0C1420",
        "theme_color": brand.get("color_primary", "#E8833A"),
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icons/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JSONResponse(manifest, media_type="application/manifest+json")


@router.get("/{token}/push/public-key", response_model=PushKeyOut)
@limiter.limit("60/minute")
def push_public_key(
    request: Request,
    client: Client = Depends(get_client_by_token),
) -> PushKeyOut:
    """Clave pública VAPID para PushManager.subscribe (o enabled=false si el
    servidor no tiene Web Push configurado)."""
    if not push_svc.push_configured():
        return PushKeyOut(enabled=False)
    return PushKeyOut(enabled=True, public_key=settings.vapid_public_key)


@router.post("/{token}/push/subscribe", response_model=dict)
@limiter.limit("20/minute")
def push_subscribe(
    request: Request,
    body: PushSubscribeIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    """Guarda (upsert por endpoint) la suscripción del dispositivo."""
    if not push_svc.push_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Notificaciones no disponibles en este momento")
    push_svc.save_subscription(
        db, client,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
        user_agent=request.headers.get("user-agent"),
    )
    log_event(db, "client", client.id, "push_subscribed", None)
    db.commit()
    return {"subscribed": True}


@router.post("/{token}/push/unsubscribe", response_model=dict)
@limiter.limit("20/minute")
def push_unsubscribe(
    request: Request,
    body: PushUnsubscribeIn,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> dict:
    removed = push_svc.remove_subscription(db, client, body.endpoint)
    if removed:
        log_event(db, "client", client.id, "push_unsubscribed", None)
    db.commit()
    return {"removed": removed}


@router.get("/{token}/push/pending", response_model=PushPendingOut)
@limiter.limit("120/minute")
def push_pending(
    request: Request,
    client: Client = Depends(get_client_by_token),
    db: Session = Depends(get_db),
) -> PushPendingOut:
    """Pendientes de HOY (diario/entreno/quincenal) + aviso de plan nuevo sin
    ver, para que el portal sincronice el badge del icono al abrirse
    (navigator.setAppBadge). El aviso de plan hace que el badge salga aunque el
    cliente no haya aceptado notificaciones push."""
    from datetime import date as _d

    pending = push_svc.pending_for_client(db, client, _d.today())
    plan_notice = bool(client.plan_notice_pending)
    pending["plan"] = plan_notice
    pending["count"] = pending["count"] + (1 if plan_notice else 0)
    return PushPendingOut(**pending)
