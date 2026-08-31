"""CRUD de clientes + links de portal + RGPD (supresión y portabilidad)."""


import io
import json
import re
import statistics
import zipfile
from datetime import date, datetime, timezone

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     Response, UploadFile, status)
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import (
    ChangeRequest,
    Client,
    DailyLog,
    EmailLog,
    FeedbackDoc,
    Period,
    Plan,
    ProgressPhoto,
    PushSubscription,
    User,
    WorkoutLog,
)
from app.schemas.entities import (
    ClientCreate,
    ClientCreatedOut,
    ClientOut,
    ClientStatus,
    ClientUpdate,
    PortalLinkOut,
)
from app.security import new_portal_token
from app.services.audit import log_event
from app.services import packages as pkgs
from app.services.storage import (
    DocumentValidationError,
    abs_path,
    delete_client_tree,
    list_documents,
    save_document,
    storage_root,
)

router = APIRouter(
    prefix="/api/clients", tags=["clients"], dependencies=[Depends(get_current_user)]
)


def _links(client: Client) -> PortalLinkOut:
    base = settings.public_base_url
    return PortalLinkOut(
        portal_token=client.portal_token,
        portal_url=f"{base}/p/{client.portal_token}",
        # La ruta REAL del front es /anamnesis/{token} (App.tsx); la antigua
        # /p/{token}/anamnesis no existía y el enlace copiado moría en el portal.
        anamnesis_url=f"{base}/anamnesis/{client.portal_token}",
    )


def _steps_num(text: str | None) -> float | None:
    """Extrae un nº de pasos de un texto libre ('cardio + 4500' → 4500).

    Robusto ante puntos como separador de miles ('10.000' → 10000, '1.234.567' →
    1234567) y ante tokens no numéricos: nunca lanza (si `float` fallara, se salta
    el token) — antes un '1.234.567' o una fecha '12.05.2026' reventaba la vista
    de seguimiento del coach con un 500."""
    if not text:
        return None
    vals: list[float] = []
    for tok in re.findall(r"\d[\d.]*", text.replace(",", "")):
        cleaned = tok.strip(".")
        # Puntos entre dígitos = separador de miles en castellano: se quitan.
        if "." in cleaned and all(part.isdigit() for part in cleaned.split(".")):
            cleaned = cleaned.replace(".", "")
        try:
            vals.append(float(cleaned))
        except ValueError:
            continue
    return max(vals) if vals else None


def _avg(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def _feelings_score_10(feelings: dict | None) -> float | None:
    """Mediana de las respuestas (1-5) escalada sobre 10 → valoración /10."""
    if not feelings:
        return None
    vals = [float(v) for v in feelings.values() if isinstance(v, (int, float))]
    if not vals:
        return None
    return round(statistics.median(vals) * 2, 1)


# Cuántas revisiones cerradas viajan en el seguimiento (se pide cada 3 s). El
# archivo completo está en la pestaña Historial.
MAX_REVISIONES_EN_SEGUIMIENTO = 4


def _quincenal_entry(db: Session, period: Period, prev: Period | None) -> dict:
    """Datos completos de una revisión quincenal con ANTES/DESPUÉS (día 1 vs 15)."""
    # Solo hace falta el PRIMER peso: traerse todos los diarios de la revisión
    # (~14 filas con sus campos) para leer uno era la consulta más cara de esta
    # respuesta, multiplicada por cada revisión del cliente.
    first_w = db.scalar(
        select(DailyLog.weight_kg)
        .where(DailyLog.period_id == period.id, DailyLog.weight_kg.is_not(None))
        .order_by(DailyLog.log_date).limit(1))
    before_w = first_w if first_w is not None else (prev.closing_weight_kg if prev else None)
    # Primera revisión sin período previo: el "antes" de los perímetros son los
    # INICIALES de la anamnesis (mig. 0041) — antes ese delta no existía.
    cli = db.get(Client, period.client_id) if prev is None else None

    def _antes(attr: str):
        if prev is not None:
            return getattr(prev, attr)
        return getattr(cli, attr.replace("closing_", "initial_"), None) if cli else None

    return {
        "period_index": period.period_index,
        "starts_on": period.starts_on.isoformat(),
        "ends_on": period.ends_on.isoformat(),
        "status": period.status,
        "analyzed": period.status == "analyzed",
        # Peso día 1 → día 15
        "weight_before": before_w,
        "weight_after": period.closing_weight_kg,
        # Perímetros (cinta): período anterior (o los INICIALES de la anamnesis
        # en la primera revisión) → este
        "waist_before": _antes("closing_waist_cm"), "waist_after": period.closing_waist_cm,
        "hip_before": _antes("closing_hip_cm"), "hip_after": period.closing_hip_cm,
        "arm_before": _antes("closing_arm_cm"), "arm_after": period.closing_arm_cm,
        "thigh_before": _antes("closing_thigh_cm"), "thigh_after": period.closing_thigh_cm,
        # Sensaciones + valoración /10
        "feelings": period.closing_feelings_json,
        "feelings_score_10": _feelings_score_10(period.closing_feelings_json),
        "adherence_diet": period.adherence_diet_0_10,
        "adherence_training": period.adherence_training_0_10,
        "free_meals": period.free_meals_count,
        "changes": period.closing_changes, "hardest": period.closing_hardest,
        "next_goal": period.closing_next_goal, "questions": period.closing_questions,
        # §8 (hardening): raíl de decisión determinista (regla + acción), si existe.
        "biweekly_decision": (period.ai_analysis_json or {}).get("biweekly_decision"),
    }


@router.get("/{client_id}/tracking")
def client_tracking(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Seguimiento en tiempo real (el coach hace polling): registros diarios
    (con nº de series) + MEDIA de lo registrado, y REVISIONES QUINCENALES con
    antes/después. Abrir esta pestaña marca las revisiones como vistas (apaga el
    aviso '!' de la lista de clientes)."""
    from datetime import date as _date

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    # Seguimiento autónomo: si hay plan publicado y ningún período abierto, se
    # abre aquí (el coach ya no pulsa "Iniciar seguimiento").
    from app.services.periods import ensure_open_period

    ensure_open_period(db, client_id)

    periods = list(db.scalars(
        select(Period).where(Period.client_id == client_id).order_by(Period.period_index)
    ))
    if not periods:
        return {"has_period": False}
    period = periods[-1]  # el más reciente

    # Marcar como vista la última revisión recibida (apaga el aviso "!")
    for pr in periods:
        if pr.status in ("closed", "analyzed") and pr.coach_reviewed_at is None:
            pr.coach_reviewed_at = datetime.now(timezone.utc)
    db.commit()

    logs = db.scalars(
        select(DailyLog)
        .where(DailyLog.period_id == period.id)
        .order_by(DailyLog.log_date.desc())
    ).all()
    # Series por día en UNA consulta agrupada: antes era un COUNT por CADA día
    # registrado (hasta 14) y esta respuesta se pide cada 3 s mientras la
    # pestaña Seguimiento esté abierta.
    series_por_dia: dict[int, int] = {}
    if logs:
        series_por_dia = {
            fila[0]: int(fila[1]) for fila in db.execute(
                select(WorkoutLog.daily_log_id, func.count())
                .where(WorkoutLog.daily_log_id.in_([lg.id for lg in logs]))
                .group_by(WorkoutLog.daily_log_id))
        }
    daily = []
    for lg in logs:
        n_sets = series_por_dia.get(lg.id, 0)
        daily.append({
            "date": lg.log_date.isoformat(),
            "weight_kg": lg.weight_kg, "sleep_hours": lg.sleep_hours,
            "steps": lg.steps, "satiety_1_10": lg.satiety_1_10, "water_liters": lg.water_liters,
            "diet_adherence": lg.diet_adherence, "free_notes": lg.free_notes,
            "workout_sets": int(n_sets),
        })

    # Media de los datos registrados del período actual
    ok = sum(1 for lg in logs if lg.diet_adherence == "yes")
    partial = sum(1 for lg in logs if lg.diet_adherence == "partial")
    n_adh = sum(1 for lg in logs if lg.diet_adherence in ("yes", "partial", "no"))
    averages = {
        "weight_kg": _avg([lg.weight_kg for lg in logs]),
        "sleep_hours": _avg([lg.sleep_hours for lg in logs]),
        "steps": _avg([_steps_num(lg.steps) for lg in logs]),
        "satiety_1_10": _avg([lg.satiety_1_10 for lg in logs]),
        "water_liters": _avg([lg.water_liters for lg in logs]),
        "workout_sets": _avg([float(d["workout_sets"]) for d in daily]),
        "diet_adherence_pct": round((ok + 0.5 * partial) / n_adh * 100) if n_adh else None,
    }

    from app.services.portal import today_local

    today = today_local()  # fecha de NEGOCIO (settings.tz), no UTC del servidor
    days_elapsed = (min(today, period.ends_on) - period.starts_on).days + 1

    # Revisiones quincenales acumuladas (más reciente primero), con antes/después
    # Solo las ÚLTIMAS revisiones: el histórico completo (que crece sin tope,
    # ~24 al año) se recalculaba y se reenviaba entero 20 veces por minuto,
    # leyendo TODOS los diarios de cada revisión cerrada para sacar un peso.
    # El archivo completo vive en la pestaña Historial.
    quincenals = []
    cerrados = [i for i in range(len(periods) - 1, -1, -1)
                if periods[i].status in ("closed", "analyzed")]
    for i in cerrados[:MAX_REVISIONES_EN_SEGUIMIENTO]:
        quincenals.append(_quincenal_entry(db, periods[i], periods[i - 1] if i > 0 else None))

    from app.services.push import dias_registrados

    return {
        "has_period": True,
        "period": {
            "index": period.period_index,
            "starts_on": period.starts_on.isoformat(),
            "ends_on": period.ends_on.isoformat(),
            "status": period.status,
            "days_elapsed": max(0, days_elapsed),
            "days_total": (period.ends_on - period.starts_on).days + 1,
        },
        "daily": daily,
        "daily_averages": averages,
        # UNA SOLA REGLA de "día registrado" en todo el sistema. Aquí se
        # contaban las FILAS: el autosave del portal crea la del día ANTES de
        # que el cliente teclee nada, así que Seguimiento decía "8 días
        # registrados" mientras el resto del panel —que usa
        # `push.dias_registrados`— contaba 5 y el aviso de "sin registros"
        # saltaba. El mismo dato con dos respuestas distintas.
        "days_logged": len(dias_registrados(db, list(logs))),
        "today_logged": any(lg.log_date == today for lg in logs),
        "quincenals": quincenals,
        "quincenal_pending": period.status == "open",
    }


def _get_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return client


# ------------------------------------------------------------------ alta ----
@router.post("", response_model=ClientCreatedOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientCreate, db: Session = Depends(get_db)) -> ClientCreatedOut:
    """Alta mínima: nombre + email (+ teléfono). El resto lo aporta el cliente
    en el wizard de anamnesis vía el link público que devuelve esta llamada."""
    # La oferta ("oferta": 1 € → 120 €/mes; "oferta2": 2 pagos de 120,50 €) es
    # SOLO del plan Full: un alta train/nutri con oferta cobraría un plan que
    # no existe.
    from app.services import packages as pkgs
    if (body.billing_period in ("oferta", "oferta2")
            and pkgs.normalize(body.package_tier) != "full"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La oferta es solo del plan Full")

    # Email normalizado a minúsculas: así el login (que compara en minúsculas) y
    # la unicidad usan la MISMA clave y no pueden crearse "A@x" y "a@x".
    email = (body.email or "").strip().lower()
    # Comprobación rápida (caso común). La restricción UNIQUE de la BD es la
    # autoridad final: cubre la carrera de doble clic / doble envío del formulario,
    # que si no se traduce a 409 acabaría en un 500 (IntegrityError sin capturar).
    if db.scalar(select(Client).where(func.lower(Client.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")

    client = Client(
        full_name=body.full_name.strip(),
        email=email,
        phone=body.phone,
        package_tier=body.package_tier,
        billing_period=body.billing_period,
        # Nivel elegido en el alta: decide el flujo de planificación (IA para
        # principiante/intermedio; base determinista del coach para avanzado).
        level=body.level,
        status="onboarding",
        portal_token="pendiente",  # se firma con el id real tras el flush
    )
    db.add(client)
    try:
        db.flush()  # asigna el id; aquí salta la violación de email único (carrera)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "client_created", {"by": "coach"})
    db.commit()
    db.refresh(client)

    # Acceso al portal: al dar de alta al cliente se le envía AUTOMÁTICAMENTE por
    # email su acceso (usuario = email + contraseña + enlace de login). El envío
    # NUNCA bloquea el alta: si el email está desactivado o falla, el cliente
    # queda creado igual y el coach puede reenviarlo desde la ficha. Como
    # portal_access_sent_at solo se sella si el email SALE, si aquí no sale, el
    # auto-envío al registrar la anamnesis lo reintentará.
    access_status: str | None = None
    try:
        from app.services.portal_access import send_portal_access

        access_status = send_portal_access(db, client)["status"]
        db.commit()
        db.refresh(client)
    except Exception:
        # Caso muy raro (el commit falla tras un envío correcto): la contraseña
        # emitida no queda guardada, pero como sent_at tampoco se sella, el coach
        # ve "error" y con "Reenviar acceso" (o al subir la anamnesis) se genera
        # una contraseña nueva y válida. Se prefiere esto a bloquear el alta.
        db.rollback()
        access_status = "error"  # que el coach lo vea y pueda reenviarlo

    return ClientCreatedOut(
        client=ClientOut.model_validate(client),
        links=_links(client),
        portal_access=access_status,
    )


# --------------------------------------------------------------- listado ----
# Campos que el LISTADO no envía. Las dos pantallas que lo consumen ("Hoy" y
# "Clientes") lo piden cada 3 segundos y NINGUNA pinta el historial clínico:
# eran ~1 KB por cliente de lesiones, patologías, medicación, hábitos y
# antropometría antigua viajando 40 veces por minuto (medido: 69 KB por
# barrido con 40 fichas, y las notas reales son bastante más largas que las
# del banco de pruebas). La ficha del cliente sigue trayéndolo TODO por su
# propio endpoint, que es donde se lee de verdad.
_LISTA_SIN = {
    "injuries_notes", "medical_notes", "medication_notes", "sport_history",
    "lifestyle_notes", "current_supplements", "meal_schedule", "equipment",
    "excluded_exercise_ids", "food_allergies", "food_dislikes", "food_likes",
}


# OJO: con una respuesta de tipo LISTA la exclusión va bajo "__all__"
# (Pydantic la aplica a cada elemento); con el set suelto no excluye nada.
@router.get("", response_model=list[ClientOut],
            response_model_exclude={"__all__": _LISTA_SIN})
def list_clients(
    db: Session = Depends(get_db),
    status_filter: ClientStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/email"),
    # `light` llegó de otra sesión que atacó lo MISMO por otro camino: un
    # opt-in que vaciaba las notas. Se conserva el parámetro para no romper a
    # quien ya lo manda, pero no hace falta hacer nada con él: la exclusión de
    # arriba (`response_model_exclude`) ya quita esos campos SIEMPRE, que es más
    # seguro — no depende de que cada llamador se acuerde de pedirlo.
    light: bool = Query(default=False, deprecated=True,
                        description="ya no hace falta: el listado nunca lleva "
                                    "las notas largas"),
) -> list[ClientOut]:
    stmt = select(Client).order_by(Client.created_at.desc())
    if status_filter:
        stmt = stmt.where(Client.status == status_filter)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Client.full_name.ilike(like), Client.email.ilike(like)))
    clients = list(db.scalars(stmt))

    # Aviso "!": última revisión quincenal recibida y aún NO vista en Seguimiento.
    pending: dict[int, int] = {}
    reviews: dict[int, int] = {}
    with_plan: set[int] = set()
    if clients:
        ids = [c.id for c in clients]
        rows = db.execute(
            select(Period.client_id, func.max(Period.period_index))
            .where(
                Period.client_id.in_(ids),
                Period.status.in_(("closed", "analyzed")),
                Period.coach_reviewed_at.is_(None),
            )
            .group_by(Period.client_id)
        ).all()
        pending = {cid: idx for cid, idx in rows}
        # Nº de la última revisión recibida (para "Revisión #N pendiente")
        reviews = {cid: idx for cid, idx in db.execute(
            select(Period.client_id, func.max(Period.period_index))
            .where(Period.client_id.in_(ids), Period.status.in_(("closed", "analyzed")))
            .group_by(Period.client_id)
        ).all()}
        # ¿Planificación hecha? (carpetas Activos vs Pendientes de la cartera)
        with_plan = set(db.scalars(
            select(Plan.client_id).where(Plan.client_id.in_(ids), Plan.status == "published").distinct()
        ))

    out = []
    for c in clients:
        item = ClientOut.model_validate(c)
        if c.id in pending:
            item.pending_review = True
            item.pending_review_period = pending[c.id]
        item.review_period_index = reviews.get(c.id)
        item.has_published_plan = c.id in with_plan
        out.append(item)
    return out


@router.get("/{client_id}/macro-recommendation")
def macro_recommendation(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Recomendación de energía/macros calculada por el BACKEND (misma fórmula
    que la generación: tramos individualizados por % graso/experiencia + suelos).
    El editor la muestra como referencia — antes usaba una fórmula TS propia
    (−20% fijo) que podía contradecir a la generación (auditoría)."""
    client = _get_or_404(db, client_id)
    if not all([client.sex, client.height_cm, client.birth_date,
                client.goal_type, client.training_days is not None]):
        return {"available": False}
    from app.services.metrics import age_from_birth, energy_targets
    from app.services.metrics import macro_targets as _mt
    from app.services.periods import reference_weight_kg

    weight = reference_weight_kg(db, client)
    if not weight:
        return {"available": False}
    age = age_from_birth(client.birth_date, date.today())
    et = energy_targets(
        sex=client.sex, weight_kg=weight, height_cm=client.height_cm, age=age,
        goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct, daily_activity=client.daily_activity_level,
        level=client.level, session_min=client.session_max_min,
    )
    mp = _mt(client.sex, weight, client.goal_type, et.target_kcal,
             client.training_days, tdee=et.tdee)
    return {
        "available": True, "weight_kg": weight,
        "tdee": round(et.tdee), "adjustment_pct": et.adjustment_pct,
        "kcal": mp.kcal, "protein_g": mp.protein_g, "carbs_g": mp.carbs_g,
        "fat_g": mp.fat_g, "warnings": et.warnings + mp.notes,
    }


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientOut:
    client = _get_or_404(db, client_id)
    out = ClientOut.model_validate(client)
    from app.services.periods import reference_weight_kg

    out.reference_weight_kg = reference_weight_kg(db, client)
    from app.services.portal import today_local
    from app.services.renewals import is_due

    out.renewal_due = is_due(client, today_local())
    return out


# ---------------------------------------------------- edición con audit ----
@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientUpdate, db: Session = Depends(get_db)) -> ClientOut:
    """Edición por el coach (anamnesis editable con audit trail, H.2)."""
    client = _get_or_404(db, client_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return ClientOut.model_validate(client)

    # Combinación RESULTANTE válida: la oferta (1 € → suscripción) es solo del
    # plan Full. Cubre tanto poner billing "oferta" a un train/nutri como
    # cambiar de plan a un cliente que YA está en la oferta.
    if "billing_period" in changes or "package_tier" in changes:
        from app.services import packages as pkgs
        billing_final = changes.get("billing_period", client.billing_period)
        tier_final = changes.get("package_tier", client.package_tier)
        if billing_final in ("oferta", "oferta2") and pkgs.normalize(tier_final) != "full":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "La oferta es solo del plan Full: cambia "
                "antes la duración si quieres otro plan.")

    # Cambio de ESTADO manual (auditoría del ciclo: `inactive` era una trampa
    # sin salida — la transición "reactivación manual" existía en la máquina
    # pero no tenía ningún llamador). Validado SIEMPRE contra la máquina.
    if "status" in changes:
        new_status = changes["status"]
        if new_status != client.status:
            from app.services.state_machine import can_transition
            if not can_transition(client.status, new_status):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Transición de estado no permitida: {client.status} → {new_status}.")

    diff: dict[str, dict] = {}
    for field, new_value in changes.items():
        old_value = getattr(client, field)
        serialized_new = (
            [item if isinstance(item, dict) else item.model_dump() for item in new_value]
            if field == "meal_schedule" and new_value is not None
            else new_value
        )
        if old_value != serialized_new:
            diff[field] = {"from": _jsonable(old_value), "to": _jsonable(serialized_new)}
        setattr(client, field, serialized_new)

    # "Marcar pagado" a mano (sin webhook de Stripe): sella también paid_at,
    # para que las vistas/consultas por fecha de pago no lo lean como impagado.
    if changes.get("payment_status") == "paid" and client.paid_at is None:
        client.paid_at = datetime.now(timezone.utc)

    if diff:
        log_event(db, "client", client.id, "client_updated", {"fields": diff})
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


def _jsonable(value):
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


# ----------------------------------------------------------------- links ----
@router.get("/{client_id}/portal-link", response_model=PortalLinkOut)
def portal_link(client_id: int, db: Session = Depends(get_db)) -> PortalLinkOut:
    return _links(_get_or_404(db, client_id))


@router.post("/{client_id}/portal-token/regenerate", response_model=PortalLinkOut)
def regenerate_portal_token(client_id: int, db: Session = Depends(get_db)) -> PortalLinkOut:
    """Revoca el token anterior (deja de coincidir en DB) y firma uno nuevo."""
    client = _get_or_404(db, client_id)
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "portal_token_regenerated", None)
    db.commit()
    db.refresh(client)
    return _links(client)


# ------------------------------------------------- RGPD: portabilidad ----
def _periodos_exportables(db: Session, client_id: int) -> list[dict]:
    """Los períodos CON todo lo que el cliente tecleó: su diario día a día y
    sus series de entreno.

    El ZIP de "descargar todo" llevaba ficha, planes y un resumen de seis
    campos por período: se dejaba fuera justo lo que el cliente ha ido
    apuntando durante meses (peso diario, sueño, pasos, agua, saciedad,
    adherencia, notas) y TODAS sus series (peso × reps × RIR). Y como el flujo
    natural de una baja es exportar y luego borrar, ese historial desaparecía
    para siempre.
    """
    periodos = list(db.scalars(
        select(Period).where(Period.client_id == client_id).order_by(Period.period_index)))
    if not periodos:
        return []
    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id.in_([p.id for p in periodos]))
        .order_by(DailyLog.log_date)))
    series_por_log: dict[int, list[dict]] = {}
    if logs:
        from app.models import Exercise

        nombres = {e.id: e.canonical_name for e in db.scalars(select(Exercise))}
        for w in db.scalars(select(WorkoutLog)
                            .where(WorkoutLog.daily_log_id.in_([lg.id for lg in logs]))
                            .order_by(WorkoutLog.id)):
            series_por_log.setdefault(w.daily_log_id, []).append({
                "ejercicio": nombres.get(w.exercise_id) or w.exercise_id,
                "serie": w.set_number, "reps": w.reps,
                "peso_kg": w.weight_kg, "rpe": w.rpe, "notas": w.notes,
            })
    logs_por_periodo: dict[int, list[dict]] = {}
    for lg in logs:
        logs_por_periodo.setdefault(lg.period_id, []).append({
            "fecha": _jsonable(lg.log_date), "peso_kg": lg.weight_kg,
            "sueno_h": lg.sleep_hours, "pasos": lg.steps,
            "saciedad_1_10": lg.satiety_1_10, "agua_l": lg.water_liters,
            "adherencia_dieta": lg.diet_adherence, "energia_1_5": lg.energy_1_5,
            "animo_1_5": lg.mood_1_5, "fatiga_1_5": lg.fatigue_1_5,
            "notas": lg.free_notes, "comidas_elegidas": lg.chosen_options_json,
            "series": series_por_log.get(lg.id, []),
        })
    return [
        {
            "period_index": pe.period_index, "starts_on": _jsonable(pe.starts_on),
            "ends_on": _jsonable(pe.ends_on), "status": pe.status,
            "closing_weight_kg": pe.closing_weight_kg, "metrics": pe.metrics_json,
            "cierre": {
                "cintura_cm": pe.closing_waist_cm, "cadera_cm": pe.closing_hip_cm,
                "brazo_cm": pe.closing_arm_cm, "muslo_cm": pe.closing_thigh_cm,
                "valoracion": pe.closing_rating, "sensaciones": pe.closing_feelings_json,
                "adherencia_dieta_0_10": pe.adherence_diet_0_10,
                "adherencia_entreno_0_10": pe.adherence_training_0_10,
                "lo_mas_dificil": pe.closing_hardest, "dudas": pe.closing_questions,
                "cambios": pe.closing_changes, "siguiente_objetivo": pe.closing_next_goal,
                "comidas_libres": pe.free_meals_count,
                "enviado_el": _jsonable(pe.closing_submitted_at),
            },
            "diario": logs_por_periodo.get(pe.id, []),
        }
        for pe in periodos
    ]



# Tope de ADJUNTOS del ZIP de portabilidad (los datos estructurados van
# siempre). El ZIP se arma en memoria: sin tope, un cliente con muchas fotos
# tumbaba el proceso entero de la API, no solo su descarga.
MAX_EXPORT_ADJUNTOS_BYTES = 200 * 1024 * 1024


def _informes_exportables(db: Session, client_id: int) -> list[dict]:
    """Los informes quincenales del cliente: el análisis de SUS datos."""
    from app.models import FeedbackDoc

    periodos = {p.id: p.period_index for p in db.scalars(
        select(Period).where(Period.client_id == client_id))}
    if not periodos:
        return []
    return [
        {"revision": periodos.get(fb.period_id), "tipo": fb.kind,
         "enviado_el": _jsonable(fb.sent_at), "contenido": fb.content_json}
        for fb in db.scalars(
            select(FeedbackDoc).where(FeedbackDoc.period_id.in_(periodos))
            .order_by(FeedbackDoc.id))
    ]


@router.get("/{client_id}/export")
def export_client_zip(client_id: int, db: Session = Depends(get_db)) -> Response:
    """\"Descargar todo\": ZIP con datos estructurados + fotos + documentos."""
    client = _get_or_404(db, client_id)

    data = {
        "client": json.loads(ClientOut.model_validate(client).model_dump_json()),
        "plans": [
            {
                "month_index": p.month_index, "version": p.version, "status": p.status,
                "nutrition": p.nutrition_json, "training": p.training_json,
                "education": p.education_json, "published_at": _jsonable(p.published_at),
            }
            for p in db.scalars(select(Plan).where(Plan.client_id == client_id).order_by(Plan.month_index, Plan.version))
        ],
        "periods": _periodos_exportables(db, client_id),
        # Los INFORMES QUINCENALES y lo que el cliente ESCRIBIÓ a su coach
        # faltaban. Los dos son suyos: el informe es el análisis de sus propios
        # datos (peso, adherencia, fuerza) y las peticiones son texto que él
        # redactó. Como el flujo natural de una baja es exportar y luego
        # borrar, se perdían para siempre justo cuando se ejercía el derecho
        # que debía conservarlos.
        "informes": _informes_exportables(db, client_id),
        "mensajes_al_coach": [
            {"fecha": _jsonable(cr.created_at), "estado": cr.status,
             "mensaje": cr.message}
            for cr in db.scalars(
                select(ChangeRequest)
                .where(ChangeRequest.client_id == client_id)
                .order_by(ChangeRequest.created_at))
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    buf = io.BytesIO()
    # TOPE del ZIP. Se armaba entero en memoria sin límite: un cliente con
    # muchas fotos de progreso y varios PDFs podía hacer que el proceso se
    # comiera cientos de MB y tumbara la API para TODOS. Lo que no quepa se
    # deja fuera y se DICE en el propio ZIP, con la ruta para pedirlo aparte;
    # los datos estructurados (que son lo que exige la portabilidad) van
    # siempre, pesen lo que pesen los adjuntos.
    omitidos: list[str] = []
    presupuesto = MAX_EXPORT_ADJUNTOS_BYTES

    def _cabe(ruta) -> bool:
        nonlocal presupuesto
        try:
            tam = ruta.stat().st_size
        except OSError:
            return False
        if tam > presupuesto:
            omitidos.append(ruta.name)
            return False
        presupuesto -= tam
        return True

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        photos = db.scalars(select(ProgressPhoto).where(ProgressPhoto.client_id == client_id))
        for ph in photos:
            p = abs_path(ph.file_path)
            if p.exists() and _cabe(p):
                zf.write(p, f"fotos/{p.name}")
        docs_dir = storage_root() / "clients" / str(client_id) / "documents"
        if docs_dir.exists():
            for f in sorted(docs_dir.iterdir()):
                if f.is_file() and _cabe(f):
                    zf.write(f, f"documentos/{f.name}")
        if omitidos:
            data["adjuntos_omitidos"] = {
                "motivo": "el ZIP superaba el tamaño máximo; pídelos aparte al coach",
                "ficheros": omitidos,
            }
        # El JSON se escribe AL FINAL: así puede contar lo que quedó fuera.
        zf.writestr("datos.json", json.dumps(data, ensure_ascii=False, indent=2))

    log_event(db, "client", client.id, "client_exported", None)
    db.commit()
    # El header Content-Disposition viaja en latin-1: normalizamos el nombre a
    # ASCII (sin tildes ni ñ) para no romper la cabecera con nombres como "López".
    import unicodedata

    ascii_name = (
        unicodedata.normalize("NFKD", client.full_name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in ascii_name).strip("_").lower() or "cliente"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="export_{safe_name}.zip"'},
    )


# --------------------------------------------------- RGPD: supresión ----
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    confirm: str = Query(description="Debe coincidir EXACTAMENTE con el nombre completo"),
    suscripcion_cancelada_a_mano: bool = Query(
        default=False,
        description="El coach declara haber cancelado ya la suscripción en Stripe"),
    db: Session = Depends(get_db),
) -> Response:
    """Supresión total RGPD con doble confirmación: modal en UI + nombre
    tecleado verificado aquí. Borra DB + archivos; deja registro anónimo."""
    client = _get_or_404(db, client_id)
    if confirm != client.full_name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La confirmación no coincide con el nombre completo del cliente",
        )

    # ANTES DE BORRAR: cortar el cobro recurrente. Sin esto, Stripe le seguía
    # cobrando cada mes a alguien que ya no existe en el sistema: el cargo
    # entraba como pago huérfano (sin ficha a la que asociarlo) y el coach se
    # enteraba por la reclamación del cliente. Si Stripe no responde NO se
    # borra: se le dice al coach que la cancele allí y repita, porque borrar
    # ahora sería perder el único hilo que queda para pararla.
    if client.stripe_subscription_id and settings.stripe_enabled:
        from app.services.stripe_service import cancelar_suscripcion

        cancelada, detalle = cancelar_suscripcion(client.stripe_subscription_id)
        if not cancelada and not suscripcion_cancelada_a_mano:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"No se pudo cancelar su suscripción de Stripe ({detalle}). "
                "Cancélala en Stripe y vuelve a intentarlo: si se borra ahora, "
                "se le seguiría cobrando todos los meses.",
            )
        if not cancelada:
            # SALIDA DECLARADA. El freno es correcto —borrar dejando el cobro
            # vivo es peor—, pero no puede ser eterno: el filtro de errores solo
            # reconoce unas cuantas formas ("no such subscription", "already
            # canceled"), así que una clave caducada o Stripe caído bloqueaban
            # una obligación LEGAL con plazo (30 días). El coach puede cancelar
            # en Stripe y declararlo aquí; queda en la auditoría con su motivo.
            detalle = f"declarada a mano por el coach (Stripe respondió: {detalle})"
        log_event(db, "client", client_id, "subscription_cancelled",
                  {"motivo": "baja_rgpd", "detalle": detalle})

    period_ids = list(db.scalars(select(Period.id).where(Period.client_id == client_id)))
    if period_ids:
        daily_ids = list(db.scalars(select(DailyLog.id).where(DailyLog.period_id.in_(period_ids))))
        if daily_ids:
            db.execute(delete(WorkoutLog).where(WorkoutLog.daily_log_id.in_(daily_ids)))
            db.execute(delete(DailyLog).where(DailyLog.id.in_(daily_ids)))
        db.execute(delete(FeedbackDoc).where(FeedbackDoc.period_id.in_(period_ids)))
    db.execute(delete(ProgressPhoto).where(ProgressPhoto.client_id == client_id))
    # push_subscriptions.client_id es NOT NULL sin ON DELETE: hay que borrarlas a
    # mano o el commit falla con ForeignKeyViolation (RGPD: borrado completo).
    db.execute(delete(PushSubscription).where(PushSubscription.client_id == client_id))
    # video_calls.client_id también es NOT NULL sin ON DELETE (mig. 0023): sin
    # esta línea, borrar a un cliente Pro con videollamadas revienta el commit.
    from app.models import VideoCall
    videollamadas = list(db.scalars(
        select(VideoCall).where(VideoCall.client_id == client_id)))
    vc_ids = [vc.id for vc in videollamadas]
    # El evento vive TAMBIÉN en Google Calendar, fuera de esta base: borrar la
    # fila no lo quitaba de ahí. La cita seguía en el calendario del coach con
    # el nombre y el email del cliente borrado —dato personal que sobrevive a
    # la supresión— y Google le seguía mandando sus recordatorios nativos de
    # una reunión con alguien que ya no existe. Best-effort: si Google está
    # caído o desconectado, la baja NO se bloquea (el aviso queda en el log).
    for vc in videollamadas:
        _cancel_google_event_safe(db, vc)
    db.execute(delete(VideoCall).where(VideoCall.client_id == client_id))
    # Libro de caja: el movimiento NO se borra (los ingresos del mes no pueden
    # cambiar porque se dé de baja a alguien) pero se ANONIMIZA — se queda sin
    # ficha, sin nombre y sin email, como el registro anónimo de la baja.
    from app.services.payments import anonymize_client
    anonymize_client(db, client_id)
    db.execute(delete(Period).where(Period.client_id == client_id))
    # plan_edits.plan_id tampoco tiene ON DELETE (§13, continuous_learning): CUALQUIER
    # cliente con un plan editado alguna vez desde el panel (lo normal) dejaba
    # filas en plan_edits que bloqueaban el DELETE de plans con
    # ForeignKeyViolation — el borrado RGPD entero fallaba en silencio (solo un
    # 400/500 genérico en el toast, sin decir por qué). Hay que vaciarlas antes.
    from app.models import PlanEdit
    plan_ids = list(db.scalars(select(Plan.id).where(Plan.client_id == client_id)))
    if plan_ids:
        db.execute(delete(PlanEdit).where(PlanEdit.plan_id.in_(plan_ids)))
    db.execute(delete(Plan).where(Plan.client_id == client_id))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id == client_id))
    db.execute(update(EmailLog).where(EmailLog.client_id == client_id).values(client_id=None))
    # AUDITORÍA: cada PATCH de la ficha guarda el ANTES y el DESPUÉS de los
    # campos editados — lesiones, patologías, medicación, alergias, teléfono.
    # Son datos de SALUD (art. 9 RGPD) y se quedaban en `audit_log` para
    # siempre, sin ficha, sin caducidad y sin ninguna pantalla desde la que
    # verlos. Una "supresión total" que deja el historial clínico no lo es.
    # (audit_log no tiene FK a clients, por eso la red estructural del test de
    # borrado no podía cazarlo.)
    from app.models import AuditLog, WhatsAppRound

    db.execute(delete(AuditLog).where(AuditLog.entity == "client",
                                      AuditLog.entity_id == client_id))
    if plan_ids:
        db.execute(delete(AuditLog).where(AuditLog.entity == "plan",
                                          AuditLog.entity_id.in_(plan_ids)))
    if period_ids:
        db.execute(delete(AuditLog).where(AuditLog.entity == "period",
                                          AuditLog.entity_id.in_(period_ids)))
    if vc_ids:
        db.execute(delete(AuditLog).where(AuditLog.entity == "video_call",
                                          AuditLog.entity_id.in_(vc_ids)))
    # SU NOMBRE EN LOS PLANES DE OTROS. Copiar un plan deja un sello legible
    # ("copiado de el plan de Ana Pérez") en `guardrail_flags` del plan DESTINO
    # y en la auditoría de ese plan — filas de OTRO cliente, que la supresión
    # de este no tocaba. El dato personal sobrevivía a la baja en fichas ajenas.
    # Se sustituye por una referencia sin nombre; el sello sigue diciendo que es
    # una copia, que es para lo que sirve.
    _borrado = "un cliente dado de baja"
    if (nombre_borrado := (client.full_name or "").strip()):
        for otro in db.scalars(
                select(Plan).where(Plan.client_id != client_id,
                                   Plan.generated_by == "library",
                                   Plan.guardrail_flags.isnot(None))):
            marcas = list(otro.guardrail_flags or [])
            if any(nombre_borrado in (m or "") for m in marcas):
                otro.guardrail_flags = [
                    (m or "").replace(nombre_borrado, _borrado) for m in marcas]
        for ev in db.scalars(select(AuditLog).where(AuditLog.event == "plan_copied")):
            detalle = ev.detail_json or {}
            origen = str(detalle.get("origen") or "")
            if nombre_borrado in origen:
                ev.detail_json = {**detalle,
                                  "origen": origen.replace(nombre_borrado, _borrado)}

    # Los mensajes de WhatsApp redactados para él viven en un JSON por día,
    # con su id como clave: se quita la suya sin tocar las de los demás.
    for ronda in db.scalars(select(WhatsAppRound)):
        textos = ronda.texts_json or {}
        if str(client_id) in textos:
            nuevos = {k: v for k, v in textos.items() if k != str(client_id)}
            ronda.texts_json = nuevos

    db.delete(client)

    # Registro anónimo de la baja: sin nombre, sin email (PARTE I)
    log_event(db, "client", client_id, "client_deleted", {"anonymous": True})
    db.commit()

    # LOS FICHEROS, AL FINAL. Se borraban ANTES del commit, así que si el
    # commit fallaba —una tabla nueva con FK sin cubrir, un interbloqueo, la
    # conexión caída— la ficha seguía viva y sus fotos, su anamnesis y sus
    # documentos ya no estaban: pérdida irrecuperable en un cliente que NO se
    # ha dado de baja. Al revés el peor caso es un directorio huérfano, que no
    # le hace daño a nadie y queda anotado para barrerlo.
    try:
        delete_client_tree(client_id)
    except Exception:  # noqa: BLE001 — la baja ya está hecha y es lo que cuenta
        import logging

        logging.getLogger("app.rgpd").exception(
            "cliente %s borrado, pero sus ficheros siguen en disco: bórralos a "
            "mano en {STORAGE_PATH}/clients/%s", client_id, client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------- documentos del cliente (anamnesis) ----
# El coach sube aquí la anamnesis oficial (PDF) rellenada por el cliente y la
# conserva asociada a su ficha. Camí A: el PDF es la anamnesis; el coach pasa
# luego los datos clave a la pestaña editable y genera el plan.

def _client_or_404_docs(db: Session, client_id: int) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return c


def ingest_anamnesis_pdf(db: Session, client_id: int, content: bytes,
                         filename: str, *, by: str = "coach") -> dict:
    """Ingesta COMPLETA de la anamnesis en PDF: guarda el archivo (reemplaza el
    anterior), lo lee con IA para pre-rellenar la ficha y envía al cliente su
    acceso al portal la primera vez. Compartida por la subida del coach (ficha)
    y la subida del PROPIO cliente (página pública /anamnesis/{token}).

    Lanza DocumentValidationError si el archivo no es un PDF válido."""
    # VALIDAR ANTES DE BORRAR: la anamnesis es el documento maestro. Antes se
    # borraba la anterior y LUEGO se validaba la nueva — un archivo corrupto o
    # demasiado grande destruía la anamnesis existente y dejaba al cliente sin
    # ninguna. Ahora primero se guarda la nueva (con validación dentro) y solo
    # después se retiran las versiones anteriores.
    from app.services.storage import client_dir
    folder = client_dir(client_id, "documents")
    # El justificante RGPD del formulario digital vive en esta misma carpeta y
    # NO es una anamnesis: barrerlo aquí destruía la prueba legal del
    # consentimiento de forma irreversible (el 409 del formulario impide
    # regenerarlo) e indetectable (list_documents lo excluye a propósito).
    # Los ADJUNTOS (analítica, informes médicos — prefijo "adjunto_") tampoco
    # son anamnesis: el propio PDF pide adjuntar la analítica y subirla por la
    # única vía que existía BORRABA la anamnesis y leía el informe de sangre
    # como si fuera la ficha (auditoría 27-08). Ver upload_client_document(kind).
    previous = [p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() == ".pdf"
                and p.name != "consentimiento_rgpd.pdf"
                and not p.name.startswith("adjunto_")]
    rel = save_document(client_id, content, filename or "anamnesis.pdf")
    # Una sola anamnesis por cliente: fuera las anteriores (la nueva ya está).
    for old in previous:
        try:
            old.unlink()
        except Exception:
            pass
    log_event(db, "client", client_id, "document_uploaded", {"path": rel, "by": by})
    db.commit()
    name = rel.rsplit("/", 1)[-1]

    # Tras subir, intentar leer la anamnesis con IA y pre-rellenar la ficha.
    # Si la lectura falla, la subida sigue siendo válida (no rompe el proceso):
    # el coach podrá pulsar "Leer con IA" o rellenar a mano.
    read_ok = False
    read_error = None
    try:
        _do_read_anamnesis(client_id, db)
        read_ok = True
    except HTTPException as exc:
        read_error = exc.detail if isinstance(exc.detail, str) else (
            exc.detail.get("error") if isinstance(exc.detail, dict) else "Error al leer"
        )
    except Exception as exc:  # nunca dejar caer la subida por un fallo de lectura
        read_error = str(exc)

    # Acceso del cliente al portal: la PRIMERA vez que se registra la anamnesis
    # se le envía por email su acceso (usuario = email + contraseña + enlace de
    # login). Solo una vez (portal_access_sent_at). Nunca bloquea la subida.
    access_status = None
    client = db.get(Client, client_id)
    if client is not None and client.portal_access_sent_at is None:
        try:
            from app.services.portal_access import send_portal_access

            access_status = send_portal_access(db, client)["status"]
            db.commit()
        except Exception:
            db.rollback()
            access_status = "error"  # que el coach lo vea y pueda reenviarlo

    # La llegada de la anamnesis del CLIENTE es EL disparador del trabajo del
    # coach y era un evento silencioso (auditoría del ciclo): push inmediato,
    # distinguiendo si la lectura IA falló (letra manuscrita, PDF sucio…).
    if by == "client" and client is not None:
        try:
            from app.services import push as push_svc

            cuerpo = ("Revísala y genera su planificación."
                      if read_ok else
                      "La lectura automática falló: revísala y rellena la ficha a mano.")
            push_svc.send_to_coach(db, {
                "title": f"📋 {client.full_name} ha enviado su anamnesis",
                "count": 1,
                "body": cuerpo,
                "url": f"/clientes/{client.id}?tab=anamnesis",
                "tag": f"anamnesis-{client.id}",
            })
            db.commit()
        except Exception:
            db.rollback()

    return {"name": name, "rel_path": rel, "read_ok": read_ok,
            "read_error": read_error, "portal_access": access_status}


@router.post("/{client_id}/documents")
def upload_client_document(
    client_id: int,
    file: UploadFile = File(..., description="PDF de la anamnesis rellenada"),
    kind: str = Form("anamnesis"),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un documento (PDF) y lo asocia al cliente.

    `kind="anamnesis"` (por defecto): reemplaza la anamnesis y la lee con IA.
    `kind="adjunto"`: documento ADICIONAL (analítica, informe médico…) — se
    guarda con prefijo `adjunto_`, NO borra la anamnesis y NO se lee con IA.
    Antes no existía hueco para un segundo documento y subir la analítica que
    el propio PDF pide destruía la anamnesis (auditoría 27-08).
    """
    _client_or_404_docs(db, client_id)
    contenido = file.file.read(25 * 1024 * 1024 + 1)
    try:
        if kind == "adjunto":
            nombre = file.filename or "documento.pdf"
            if not nombre.startswith("adjunto_"):
                nombre = f"adjunto_{nombre}"
            rel = save_document(client_id, contenido, nombre)
            log_event(db, "client", client_id, "document_uploaded",
                      {"path": rel, "by": "coach", "kind": "adjunto"})
            db.commit()
            return {"name": rel.rsplit("/", 1)[-1], "rel_path": rel,
                    "read_ok": None, "read_error": None, "portal_access": None}
        return ingest_anamnesis_pdf(db, client_id, contenido,
                                    file.filename or "anamnesis.pdf", by="coach")
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/{client_id}/documents")
def get_client_documents(client_id: int, kind: str | None = None,
                         db: Session = Depends(get_db)) -> list[dict]:
    """Documentos subidos del cliente. Cada uno con su `kind`
    (anamnesis | adjunto); `?kind=anamnesis` filtra solo el cuestionario."""
    _client_or_404_docs(db, client_id)
    docs = list_documents(client_id)
    if kind:
        docs = [d for d in docs if d.get("kind") == kind]
    return docs


@router.get("/{client_id}/anamnesis-analysis")
def get_anamnesis_analysis(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Lo que la lectura de la anamnesis dejó anotado: la síntesis y las
    CONTRADICCIONES detectadas ("declara vegano pero menciona pollo", "quiere
    bajar 17 kg antes del 01/10: ~1,8 %/semana").

    Se calculaban, se guardaban en el sidecar… y no las devolvía ningún
    endpoint: la única forma de verlas era volver a pulsar "Leer con IA", que
    gasta créditos y pisa las correcciones del coach. Justo lo que hay que
    resolver ANTES de generar el plan."""
    import json as _json

    cliente = _client_or_404_docs(db, client_id)

    # LAS CONTRADICCIONES SE RECALCULAN, no se leen del sidecar. Son una función
    # DETERMINISTA de la ficha (`detect_contradictions`), no salida de la IA:
    # no cuestan créditos y se pueden mirar cuando haga falta. Servirlas
    # congeladas desde el momento de la extracción las convertía en una foto
    # fija que mentía en las dos direcciones: seguía avisando de algo que el
    # coach ya había corregido, y callaba si era el propio coach quien
    # introducía la contradicción al editar la ficha. Y todo esto ANTES de
    # generar el plan, que es justo cuando hay que resolverlas.
    contradicciones: list[str] = []
    try:
        from app.services.anamnesis_extraction import detect_contradictions

        perfil = {k: getattr(cliente, k, None) for k in (
            "sex", "birth_date", "height_cm", "start_weight_kg", "goal_type",
            "goal_weight_kg", "goal_deadline", "level", "training_days",
            "session_max_min", "training_place", "lifestyle_notes",
            "sport_history", "injuries_notes", "medical_notes",
            "medication_notes", "food_allergies", "food_dislikes", "food_likes")}
        contradicciones = [c.detail for c in detect_contradictions(perfil)]
    except Exception:  # noqa: BLE001 — nunca rompe la ficha
        contradicciones = []

    def _retrato_en_vivo() -> str | None:
        """Retrato determinista de la ficha ACTUAL (vía formulario, o reserva).
        No cuesta créditos, así que refleja siempre lo último que corrigió el
        coach — que es justo lo que hay que mirar antes de generar."""
        try:
            from app.services.anamnesis_extraction import client_portrait

            return client_portrait({k: getattr(cliente, k, None) for k in (
                "sex", "goal_type", "level", "training_days", "session_max_min",
                "lifestyle_notes", "injuries_notes", "medical_notes",
                "medication_notes", "food_allergies", "food_dislikes")}) or None
        except Exception:  # noqa: BLE001
            return None

    try:
        ruta = _anamnesis_analysis_path(client_id)
        if ruta.exists():
            datos = _json.loads(ruta.read_text(encoding="utf-8"))
            return {
                # El retrato del sidecar es el que se PAGÓ a la IA (vía PDF).
                # Si no lo hay —vía formulario—, se compone al vuelo.
                "deep_analysis": datos.get("deep_analysis") or _retrato_en_vivo(),
                "contradictions": contradicciones,
                "read_at": datos.get("at"),
            }
    except Exception:  # noqa: BLE001 — un sidecar roto no rompe la ficha
        pass
    return {"deep_analysis": _retrato_en_vivo(),
            "contradictions": contradicciones, "read_at": None}


@router.post("/{client_id}/send-portal-access")
def resend_portal_access(client_id: int, db: Session = Depends(get_db)) -> dict:
    """(Re)envía al cliente su acceso al portal por email, regenerando la
    contraseña. Devuelve el status del email y la contraseña en claro (para que
    el coach pueda dársela también él si el email no llega)."""
    client = _client_or_404_docs(db, client_id)
    from app.services.portal_access import send_portal_access

    res = send_portal_access(db, client)
    db.commit()
    return {"status": res["status"], "email": client.email, "password": res["password"]}


# ------------------------------------------------- videollamadas (Pro) ----
# Flujo: el CLIENTE propone día/hora desde su portal al enviar su revisión
# quincenal → el COACH lo ve en su agenda y ACEPTA (crea el evento en Google
# Calendar con Meet e invita al cliente por email) o MODIFICA (lo acuerda por
# WhatsApp y lo agenda a mano). Estados: proposed → accept | modify → scheduled |
# pending_manual → done. Recordatorios el día antes y 1 h antes (coach y cliente).

@router.get("/{client_id}/video-calls")
def list_video_calls(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    _client_or_404_docs(db, client_id)
    rows = db.scalars(
        select(VideoCall).where(VideoCall.client_id == client_id)
        .order_by(VideoCall.period_index.desc())
    ).all()
    return [VideoCallOut.model_validate(r).model_dump(mode="json") for r in rows]


def _cancel_google_event_safe(db: Session, vc) -> None:
    """Cancela el evento de Google si existe. No rompe el flujo local si falla
    (p. ej. Google desconectado): lo importante es que el estado local avance."""
    if not vc.google_event_id:
        return
    from app.services import google_calendar as gcal
    try:
        gcal.cancel_meet_event(db, event_id=vc.google_event_id)
    except gcal.GoogleCalendarError:
        import logging
        logging.getLogger("app.google").warning(
            "no se pudo cancelar el evento de Google de la videollamada %s", vc.id)


def _confirm_meet(db: Session, client: Client, vc, *, start_aware: datetime,
                  duration_min: int) -> None:
    """Crea/actualiza el evento en Google Calendar con Meet, deja la videollamada
    en 'scheduled' y avisa al cliente (email con el enlace + push). NO hace commit.
    Ante un error de Google hace rollback y lanza 502 (mensaje legible)."""
    from zoneinfo import ZoneInfo

    from app.services import email_templates as tpl
    from app.services import google_calendar as gcal
    from app.services import push as push_svc
    from app.services.email_service import EmailService, brand_from_config
    from app.services.portal import format_when_es

    if start_aware.tzinfo is None:
        start_aware = start_aware.replace(tzinfo=ZoneInfo(settings.tz))
    start_naive_local = start_aware.astimezone(ZoneInfo(settings.tz)).replace(tzinfo=None)
    when_label = format_when_es(start_aware)
    brand = brand_from_config(db)
    summary = f"Videollamada de revisión · {client.full_name}".strip()
    description = (
        "Videollamada de revisión quincenal de tu asesoría. "
        "Repasaremos tu progreso, resolveremos dudas y ajustaremos lo que haga falta."
    )
    try:
        if vc.google_event_id:
            ev = gcal.update_meet_event(
                db, event_id=vc.google_event_id,
                start_at=start_naive_local, duration_min=duration_min)
        else:
            ev = gcal.create_meet_event(
                db, summary=summary, description=description,
                start_at=start_naive_local, duration_min=duration_min,
                attendee_email=client.email or None)
    except gcal.GoogleCalendarError as exc:
        db.rollback()
        # El rollback deshace TAMBIÉN el borrado de la credencial que Google
        # acaba de rechazar: sin esto la fila revocada volvía, el panel seguía
        # diciendo "Google conectado" y cada intento de agendar repetía el
        # mismo error sin que el coach viera nunca el botón de reconectar.
        if getattr(exc, "revocado", False) and gcal.olvidar_credencial(db):
            db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    vc.status = "scheduled"
    vc.scheduled_at = start_aware
    vc.scheduled_for = start_aware.date()
    vc.duration_min = duration_min
    vc.meet_url = ev.get("meet_url") or vc.meet_url
    vc.google_event_id = ev.get("event_id") or vc.google_event_id
    vc.google_html_link = ev.get("html_link") or vc.google_html_link
    log_event(db, "client", client.id, "video_call_meet_scheduled",
              {"period_index": vc.period_index, "at": start_aware.isoformat(),
               "event_id": vc.google_event_id})

    # Aviso al cliente: email con el enlace de Meet + push (además de la
    # invitación nativa de Google Calendar). El WhatsApp lo lanza el coach desde
    # la web con un botón.
    if vc.meet_url:
        emailer = EmailService(db)
        _parts = (client.full_name or "").split()
        first_name = _parts[0] if _parts else "hola"
        subject, html = tpl.video_call_scheduled(
            brand, first_name, when_label, vc.meet_url, duration_min)
        emailer.send(to=client.email, subject=subject, html=html,
                     kind="video_call_scheduled", client=client)
        try:
            push_svc.notify_video_call_scheduled(db, client, when_label, vc.meet_url)
        except Exception:  # el push nunca debe tumbar el agendado
            import logging
            logging.getLogger("app.google").exception("push de videollamada fallido")


def _future_local(raw: datetime) -> datetime:
    """Normaliza a la zona del coach y exige que sea futura (si no, 422)."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(settings.tz)
    start_aware = raw.replace(tzinfo=tz) if raw.tzinfo is None else raw.astimezone(tz)
    if start_aware <= datetime.now(tz):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La fecha y hora ya pasaron: revisa el día elegido.")
    return start_aware


class VideoCallMeetIn(BaseModel):
    period_index: int
    start_at: datetime           # fecha y hora (zona del coach si viene sin offset)
    duration_min: int = 30


@router.post("/{client_id}/video-calls/schedule-meet")
def schedule_video_call_meet(client_id: int, body: VideoCallMeetIn,
                             db: Session = Depends(get_db)) -> dict:
    """Agenda a MANO (o resuelve un 'pendiente de agendar'): el coach escribe día,
    hora y duración → se crea el evento en Google Calendar con Meet, se invita al
    cliente por email y se le manda el enlace. Idempotente por (cliente, período).

    Requiere Google conectado. También lo usa el coach para iniciar una
    videollamada sin propuesta previa del cliente.
    """
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut
    from app.services import google_calendar as gcal

    client = _client_or_404_docs(db, client_id)
    if not gcal.is_connected(db):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Conecta tu cuenta de Google en Ajustes para agendar por Meet.")
    if body.duration_min < 5 or body.duration_min > 240:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La duración debe estar entre 5 y 240 minutos.")
    start_aware = _future_local(body.start_at)

    vc = db.scalar(select(VideoCall).where(
        VideoCall.client_id == client_id, VideoCall.period_index == body.period_index))
    if vc is None:
        vc = VideoCall(client_id=client_id, period_index=body.period_index)
        db.add(vc)
    _confirm_meet(db, client, vc, start_aware=start_aware, duration_min=body.duration_min)
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


class VideoCallAcceptIn(BaseModel):
    duration_min: int = 30


@router.post("/{client_id}/video-calls/{call_id}/accept")
def accept_video_call(client_id: int, call_id: int, body: VideoCallAcceptIn,
                      db: Session = Depends(get_db)) -> dict:
    """ACEPTA la propuesta del cliente tal cual: crea el evento en Google Calendar
    con Meet en el día/hora propuestos e invita al cliente."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut
    from app.services import google_calendar as gcal

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    if vc.status not in ("proposed", "pending_manual"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Solo puede aceptarse una propuesta pendiente.")
    if vc.scheduled_at is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "No hay una fecha propuesta que aceptar.")
    client = _client_or_404_docs(db, client_id)
    if not gcal.is_connected(db):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Conecta tu cuenta de Google en Ajustes para agendar por Meet.")
    if body.duration_min < 5 or body.duration_min > 240:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La duración debe estar entre 5 y 240 minutos.")
    start_aware = _future_local(vc.scheduled_at)
    _confirm_meet(db, client, vc, start_aware=start_aware, duration_min=body.duration_min)
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.post("/{client_id}/video-calls/{call_id}/modify")
def modify_video_call(client_id: int, call_id: int, db: Session = Depends(get_db)) -> dict:
    """MODIFICA la propuesta: queda 'pendiente de agendar a mano'. El coach lo
    acuerda con el cliente por WhatsApp y luego escribe el día/hora definitivos
    (schedule-meet). Hasta entonces sale en las alertas con recordatorios."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    if vc.status == "done":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta videollamada ya se realizó.")
    vc.status = "pending_manual"
    log_event(db, "client", client_id, "video_call_modify_requested",
              {"period_index": vc.period_index})
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.post("/{client_id}/video-calls/{call_id}/done")
def video_call_done(client_id: int, call_id: int, db: Session = Depends(get_db)) -> dict:
    """La videollamada se REALIZÓ: se cierra y sale de la agenda/alertas."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    # También desde proposed/pending_manual: sin Google conectado (o si la
    # llamada se hizo por teléfono/WhatsApp) esos estados no tenían NINGUNA
    # salida y su alerta alta sonaba para siempre (auditoría del ciclo).
    if vc.status not in ("scheduled", "proposed", "pending_manual"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Esta videollamada ya está cerrada.")
    prev_status = vc.status
    vc.status = "done"
    log_event(db, "client", client_id, "video_call_done",
              {"period_index": vc.period_index, "from_status": prev_status})
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.post("/{client_id}/video-calls/{call_id}/reschedule")
def video_call_reschedule(client_id: int, call_id: int, db: Session = Depends(get_db)) -> dict:
    """NO se realizó: cancela el evento en Google (avisa a los invitados) y queda
    'pendiente de agendar a mano' para acordar una nueva fecha."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    if vc.status == "done":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Esta videollamada ya se realizó: no puede reagendarse")
    _cancel_google_event_safe(db, vc)
    vc.status = "pending_manual"
    vc.scheduled_for = None
    vc.scheduled_at = None
    vc.meet_url = None
    vc.google_event_id = None
    vc.google_html_link = None
    log_event(db, "client", client_id, "video_call_rescheduled", {"period_index": vc.period_index})
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")



@router.post("/{client_id}/send-onboarding")
def send_onboarding(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía al cliente (por email) el mensaje de arranque combinado: enlace de
    pago de su plan + enlace a la anamnesis (página pública del PDF editable),
    con la instrucción EN MAYÚSCULAS de enviarla rellena. (En Pro el coach lo
    manda por WhatsApp desde la web; este endpoint es la vía email.)"""
    from app.services.onboarding import send_onboarding_email

    client = _client_or_404_docs(db, client_id)
    email_status = send_onboarding_email(db, client)
    db.commit()
    return {"status": email_status, "email": client.email}


@router.get("/{client_id}/history")
def client_history(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Evolución del cliente en el tiempo: peso/adherencia/fuerza por período +
    planes y feedbacks. Para la pestaña Historial (resumida y descargable)."""
    from app.models import FeedbackDoc, Period, Plan
    from app.services.feedback_service import compute_period_summary, sets_por_periodo

    client = _client_or_404_docs(db, client_id)
    periods = list(db.scalars(
        select(Period).where(Period.client_id == client_id).order_by(Period.period_index)
    ))
    # Series de TODAS las revisiones de una vez: el resumen de cada período
    # compara con los anteriores, así que en bucle se releían las mismas series
    # una y otra vez (con 4 revisiones eran 27 consultas; con 8, más del doble
    # y releyendo cuatro veces el mismo histórico).
    cache_sets = sets_por_periodo(db, [p.id for p in periods])
    # Y el feedback de cada revisión, también de una vez (era otra consulta por
    # período dentro del mismo bucle).
    _pids = [p.id for p in periods]
    ultimo_fb: dict[int, tuple[int, object]] = {}
    if _pids:
        for _pid, _fid, _sent in db.execute(
            select(FeedbackDoc.period_id, FeedbackDoc.id, FeedbackDoc.sent_at)
            .where(FeedbackDoc.period_id.in_(_pids))
            .order_by(FeedbackDoc.id.asc())
        ).all():
            ultimo_fb[_pid] = (_fid, _sent)  # el de id más alto gana (orden asc)
    # SOLO los cuatro escalares que se imprimen: traer la fila entera arrastraba
    # los cuatro JSONB de CADA versión (banco de recetas, educativo, hallazgos
    # del panel) para emitir una línea de 40 bytes por plan. En un cliente
    # veterano con 16 versiones eran ~500 KB leídos y parseados para nada.
    plans = db.execute(
        select(Plan.id, Plan.month_index, Plan.version, Plan.status)
        .where(Plan.client_id == client_id)
        .order_by(Plan.month_index, Plan.version)
    ).all()

    current = client.start_weight_kg
    hist = []
    e1rm_series: dict[str, list[float]] = {}  # nombre → e1rm por período (para % total)
    for p in periods:
        try:
            m = compute_period_summary(db, p.id, cache_sets=cache_sets)
        except Exception:
            m = {}
        # Solo actualizamos el peso "actual" con un valor REAL (registrado o de
        # cierre); nunca con el fallback al peso inicial que devuelve el resumen
        # cuando el período no tiene registros (si no, un período abierto sin
        # datos revertiría el peso al inicial).
        real_end = m.get("weight", {}).get("end_kg")
        if real_end is not None:
            current = real_end
        strength = m.get("strength") or []
        for s in strength:
            if s.get("e1rm_kg"):
                e1rm_series.setdefault(s["name"], []).append(s["e1rm_kg"])
        # % de fuerza subido DURANTE el período (media de e1RM vs período anterior)
        gains = [
            s["delta_kg"] / (s["e1rm_kg"] - s["delta_kg"]) * 100
            for s in strength
            if s.get("delta_kg") is not None and (s["e1rm_kg"] - s["delta_kg"]) > 0
        ]
        period_strength_pct = round(sum(gains) / len(gains), 1) if gains else None
        fb_id, fb_sent = ultimo_fb.get(p.id, (None, None))
        hist.append({
            "period_index": p.period_index,
            "starts_on": p.starts_on.isoformat(), "ends_on": p.ends_on.isoformat(),
            "status": p.status,
            "closing_weight_kg": p.closing_weight_kg,
            "weight_delta_kg": m.get("weight", {}).get("delta_kg"),
            "adherence_pct": m.get("adherence", {}).get("diet_pct"),
            "best_e1rm_kg": strength[0]["e1rm_kg"] if strength else None,
            "strength_gain_pct": period_strength_pct,
            "distance_to_goal_kg": m.get("distance_to_goal_kg"),
            # Perímetros (cinta) al cierre de este período
            "waist_cm": p.closing_waist_cm, "hip_cm": p.closing_hip_cm,
            "arm_cm": p.closing_arm_cm, "thigh_cm": p.closing_thigh_cm,
            "feedback_id": fb_id,
            "feedback_sent": bool(fb_sent),
        })

    # % de fuerza subido EN TOTAL (primer vs último e1RM de cada ejercicio)
    total_gains = [
        (serie[-1] - serie[0]) / serie[0] * 100
        for serie in e1rm_series.values() if len(serie) >= 2 and serie[0] > 0
    ]
    total_strength_gain_pct = round(sum(total_gains) / len(total_gains), 1) if total_gains else None

    # Medidas corporales antes/después (primer período con dato → último con dato)
    def _first_last(attr: str) -> tuple[float | None, float | None]:
        vals = [(getattr(p, attr)) for p in periods if getattr(p, attr) is not None]
        return (vals[0], vals[-1]) if vals else (None, None)

    measures = {}
    for label, attr in (("waist", "closing_waist_cm"), ("hip", "closing_hip_cm"),
                        ("arm", "closing_arm_cm"), ("thigh", "closing_thigh_cm")):
        before, after = _first_last(attr)
        measures[label] = {"before": before, "after": after}

    remaining = round(abs(current - client.goal_weight_kg), 1) if (
        current is not None and client.goal_weight_kg is not None) else None

    return {
        "start_weight_kg": client.start_weight_kg,
        "current_weight_kg": current,
        "goal_weight_kg": client.goal_weight_kg,
        "remaining_to_goal_kg": remaining,
        "measures": measures,
        "total_strength_gain_pct": total_strength_gain_pct,
        "periods": hist,
        "plans": [
            {"id": pl.id, "month_index": pl.month_index, "version": pl.version,
             "status": pl.status}
            for pl in plans
        ],
    }


@router.get("/{client_id}/photos")
def list_client_photos(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Fotos de progreso del cliente (las que sube en el portal al cerrar)."""
    _client_or_404_docs(db, client_id)
    rows = db.scalars(
        select(ProgressPhoto).where(ProgressPhoto.client_id == client_id)
        .order_by(ProgressPhoto.taken_at.desc())
    )
    return [
        {"id": p.id, "kind": p.kind, "period_id": p.period_id, "taken_at": p.taken_at.isoformat()}
        for p in rows
    ]


def _miniatura(path, ancho: int) -> bytes | None:
    """Reduce una foto a `ancho` px de lado mayor. Devuelve None si no se puede
    (formato raro, archivo corrupto): el llamador sirve entonces el original.

    `draft()` hace que el JPEG se decodifique ya reducido — sin él, generar la
    miniatura costaría más que servir la foto entera."""
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(path) as img:
            img.draft("RGB", (ancho, ancho))
            img = img.convert("RGB")
            img.thumbnail((ancho, ancho))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=80, optimize=True)
            return buf.getvalue()
    except Exception:  # noqa: BLE001
        return None


@router.get("/{client_id}/photos/{photo_id}")
def get_client_photo(client_id: int, photo_id: int,
                     w: int | None = Query(default=None, ge=32, le=2000,
                                           description="ancho máximo en px (miniatura)"),
                     db: Session = Depends(get_db)):
    """Sirve una foto de progreso (requiere JWT del coach).

    Con `?w=` devuelve una MINIATURA. La tira de fotos del período las pintaba a
    80×96 px descargando el original del móvil del cliente (varios MB cada una):
    ocho fotos eran decenas de megas para ocho sellos de contacto."""
    p = db.get(ProgressPhoto, photo_id)
    if not p or p.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto no encontrada")
    path = abs_path(p.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    ext = path.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "application/octet-stream")
    # La foto de un período cerrado no cambia nunca: que el navegador la guarde.
    cache = {"Cache-Control": "private, max-age=86400"}
    if w:
        mini = _miniatura(path, w)
        if mini is not None:
            return Response(
                content=mini, media_type="image/jpeg",
                headers={"Content-Disposition": f'inline; filename="foto_{photo_id}_w{w}.jpg"',
                         **cache},
            )
    return Response(
        content=path.read_bytes(), media_type=media,
        headers={"Content-Disposition": f'inline; filename="foto_{photo_id}{ext}"', **cache},
    )


@router.get("/{client_id}/documents/{name}")
def download_client_document(client_id: int, name: str, db: Session = Depends(get_db)):
    """Descarga un documento concreto del cliente (PDF)."""
    _client_or_404_docs(db, client_id)
    # Evita traversal: solo nombres simples dentro de la carpeta del cliente
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nombre no válido")
    path = abs_path(f"clients/{client_id}/documents/{name}")
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


# ------------------------------------------- generación de plan con IA (D/F) ----
# Pieza central: a partir de los datos estructurados de la anamnesis del cliente,
# calcula métricas (BMR/TDEE/objetivo), filtra la biblioteca de ejercicios y pide
# a la IA el plan mensual (núcleo + comidas + educativo), bajo guardrails. Lo
# guarda como borrador para que el coach lo revise, publique y descargue.

# Campos estructurados imprescindibles para poder generar.
# NOTA: meals_per_day y meal_schedule son OPCIONALES — si el cliente lo delega
# ("lo decidís vosotros"), la IA elige el número y reparto óptimo de comidas.
_REQUIRED_FIELDS = {
    "sex": "Sexo", "birth_date": "Fecha de nacimiento", "height_cm": "Altura",
    "start_weight_kg": "Peso inicial", "goal_type": "Objetivo", "level": "Nivel",
    "training_days": "Días de entrenamiento", "session_max_min": "Duración de sesión",
    "training_place": "Dónde entrena", "diet_mode": "Modo de dieta",
}


class GeneratePlanIn(BaseModel):
    """Cuerpo opcional del generate-plan: reparto de comidas elegido por el coach
    (claves canónicas: desayuno, media_manana, comida, snack, cena, precama). Si
    viene, sustituye al de la anamnesis y se persiste en el cliente."""
    meals: list[str] | None = None


def _food_catalog_for(db: Session, client: Client) -> list[dict]:
    """§2: catálogo de alimentos (foods) como dicts para el solver, FILTRADO por las
    alergias/aversiones/patrón del cliente (un alérgeno no puede ni entrar al prompt).
    Best-effort: si algo falla, devuelve [] y la generación sigue con gramos de la IA."""
    try:
        from app.models import Food
        from app.services.portion_solver import filter_foods
        rows = db.scalars(select(Food).where(Food.archived.is_(False))).all()
        foods = [{
            "id": f.id, "canonical_name": f.canonical_name, "aliases": f.aliases or [],
            "kcal": f.kcal, "protein_g": f.protein_g, "carbs_g": f.carbs_g, "fat_g": f.fat_g,
            "allergens": f.allergens or [], "tags": f.tags or [],
            "unit_grams": f.unit_grams, "min_grams": f.min_grams, "max_grams": f.max_grams,
        } for f in rows]
        return filter_foods(
            foods,
            allergies=client.food_allergies or [],
            dislikes=client.food_dislikes or [],
            # Patrón ético/religioso REAL del cliente (campo diet_pattern,
            # migración 0032): vegano/halal… se respeta al 100%.
            diet_pattern=client.diet_pattern,
        )
    except Exception:  # noqa: BLE001
        return []


@router.post("/{client_id}/generate-plan")
def generate_client_plan(
    client_id: int,
    month_index: int | None = Query(default=None, ge=1),
    body: GeneratePlanIn | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Genera (con IA real) el plan mensual del cliente y lo guarda como borrador.

    Sin `month_index` el mes se deriva del ciclo real (dos revisiones = un mes):
    antes se reenviaba siempre el del plan anterior y el cliente recibía "Mes 1"
    de por vida."""
    from datetime import date

    from app.models import Exercise, Plan
    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.generator import (
        ClientContext,
        PlanGenerationError,
        generate_monthly_plan,
    )
    from app.services.guardrails import filter_exercises_for_client
    from app.services.metrics import age_from_birth, energy_targets

    client = _client_or_404_docs(db, client_id)

    # 0) Reparto de comidas elegido por el coach en el selector: sustituye al de
    # la anamnesis y se guarda en el cliente (para que persista en futuras
    # regeneraciones). La IA reparte los macros entre estas tomas.
    if body is not None and body.meals:
        from app.services.meal_structure import meal_schedule_from_keys

        sched = meal_schedule_from_keys(body.meals)
        if sched:
            client.meal_schedule = sched
            client.meals_per_day = len(sched)
            db.commit()

    # 1) Validar que la anamnesis estructurada está completa
    missing = []
    for field, label in _REQUIRED_FIELDS.items():
        if getattr(client, field, None) in (None, "", []):
            missing.append(label)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Faltan datos en la anamnesis para generar el plan.",
                "missing": missing,
            },
        )

    # 2) Métricas calculadas por el backend (la IA nunca calcula)
    age = age_from_birth(client.birth_date, date.today())
    # Peso ACTUAL del cliente: helper ÚNICO reference_weight_kg (misma verdad
    # para generación, PATCH del plan, adaptación y editor).
    from app.services.periods import reference_weight_kg

    weight_now = reference_weight_kg(db, client)

    et = energy_targets(
        sex=client.sex, weight_kg=weight_now, height_cm=client.height_cm,
        age=age, goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct, daily_activity=client.daily_activity_level,
        level=client.level, session_min=client.session_max_min,
    )
    # Reparto de macros EN CÓDIGO (hardening §3): la IA lo recibe como contrato.
    # Si los suelos no caben, macro_targets sube las kcal → esa es la kcal objetivo
    # real que se entrega (nunca se rompe un suelo por un plazo).
    from app.services.metrics import macro_targets as _macro_targets
    _mp = _macro_targets(
        client.sex, weight_now, client.goal_type, et.target_kcal, client.training_days,
        tdee=et.tdee,
    )
    macro_plan = {
        "kcal": _mp.kcal, "protein_g": _mp.protein_g, "carbs_g": _mp.carbs_g,
        "fat_g": _mp.fat_g, "fiber_g_min": _mp.fiber_g_min, "water_ml": _mp.water_ml,
    }
    target_kcal_final = _mp.kcal  # puede haber subido respecto a et.target_kcal

    # 3) Biblioteca de ejercicios filtrada (solo aptos para este cliente)
    all_ex = db.scalars(select(Exercise)).all()
    ex_dicts = [{
        "id": e.id, "canonical_name": e.canonical_name, "name": e.canonical_name,
        "movement_pattern": e.movement_pattern,
        "muscle_primary": e.muscle_primary, "muscle_secondary": e.muscle_secondary or [],
        "equipment": e.equipment or [], "level_min": e.level_min,
        "contraindications": e.contraindications or [], "archived": e.archived,
    } for e in all_ex]
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
    # En gimnasio se asume equipamiento estándar completo: no se restringe por
    # equipo (el cliente no tiene por qué listar banco, rack, etc.). En casa o
    # exterior sí se respeta el material declarado.
    equip = set() if client.training_place == "gym" else set(client.equipment or [])
    # Lesiones (texto libre) → etiquetas de contraindicación articular, para que
    # el filtro y el guardrail excluyan DE VERDAD los ejercicios peligrosos.
    from app.services.injuries import injury_contra_tags
    contra_tags = injury_contra_tags(client.injuries_notes, client.medical_notes)
    library = filter_exercises_for_client(
        ex_dicts,
        client_contraindications=contra_tags,
        excluded_ids=set(client.excluded_exercise_ids or []),
        equipment_available=equip,
        level_max=level_map.get(client.level, 2),
        training_place=client.training_place,
    )
    if not library:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No hay ejercicios disponibles con las restricciones del cliente.",
        )

    # Análisis cualitativo guardado al leer la anamnesis con IA (si existe)
    deep_analysis = None
    try:
        import json as _json
        ap = _anamnesis_analysis_path(client_id)
        if ap.exists():
            saved = _json.loads(ap.read_text(encoding="utf-8"))
            deep_analysis = saved.get("deep_analysis") or saved.get("injuries_notes")
    except Exception:
        deep_analysis = None
    if not deep_analysis:
        # Vía FORMULARIO DIGITAL (sin sidecar de lectura IA): retrato
        # determinista del cliente (§5, por fin cableado) — el prompt recibe la
        # misma síntesis priorizada que tendría un cliente llegado por PDF.
        try:
            from app.services.anamnesis_extraction import client_portrait

            perfil = {k: getattr(client, k, None) for k in (
                "sex", "goal_type", "level", "training_days", "session_max_min",
                "lifestyle_notes", "injuries_notes", "medical_notes",
                "medication_notes", "food_allergies", "food_dislikes")}
            deep_analysis = client_portrait(perfil) or None
        except Exception:
            deep_analysis = None

    # Ajustes del ÚLTIMO feedback quincenal → el nuevo plan queda modificado en
    # consecuencia (dieta y entreno) según lo que el cliente registró.
    adj_notes = ""
    last_analyzed = db.scalar(
        select(Period)
        .where(Period.client_id == client_id, Period.status == "analyzed")
        .order_by(Period.period_index.desc())
        .limit(1)
    )
    if last_analyzed and last_analyzed.ai_analysis_json:
        aj = last_analyzed.ai_analysis_json.get("plan_adjustments") or []
        objs = last_analyzed.ai_analysis_json.get("next_objectives") or []
        if aj:
            lines = [f"- [{a.get('area')}] {a.get('change')} (motivo: {a.get('reason')})" for a in aj]
            adj_notes = ("AJUSTES DEL ÚLTIMO FEEDBACK QUINCENAL (aplícalos al nuevo plan de "
                         "dieta y entrenamiento):\n" + "\n".join(lines))
            if objs:
                adj_notes += "\nObjetivos próximos: " + "; ".join(str(o) for o in objs)

    # Historial REAL de seguimiento (peso, adherencia y fuerza por revisión):
    # la IA parte del recorrido completo del cliente, no solo de la anamnesis.
    history_block = None
    try:
        h = client_history(client_id, db)
        reviews = [{k: p.get(k) for k in ("period_index", "closing_weight_kg",
                                          "weight_delta_kg", "adherence_pct",
                                          "strength_gain_pct")}
                   for p in h["periods"] if p["status"] != "open"]
        if reviews:
            history_block = {
                "peso_inicial_kg": h.get("start_weight_kg"),
                "peso_actual_kg": h.get("current_weight_kg"),
                "fuerza_total_pct": h.get("total_strength_gain_pct"),
                "medidas_antes_despues": h.get("measures"),
                "revisiones_quincenales": reviews,
            }
    except Exception:
        history_block = None

    # Notas clínicas TEXTUALES (lesiones, patologías, medicación, suplementos):
    # entran SIEMPRE y de forma explícita, no solo dentro de la síntesis, para
    # que la IA adapte dieta y entrenamiento sin fallo a la salud del cliente.
    clinical_parts: list[str] = []
    for lbl, val in (
        ("LESIONES / MOVILIDAD", client.injuries_notes),
        ("HISTORIA CLÍNICA Y SALUD", client.medical_notes),
        ("MEDICACIÓN", client.medication_notes),
        ("SUPLEMENTACIÓN ACTUAL", client.current_supplements),
    ):
        if val and val.strip():
            clinical_parts.append(f"{lbl}:\n{val.strip()}")
    clinical_notes = "\n\n".join(clinical_parts) or None

    # 4) Construir el contexto y pedir el plan a la IA
    ctx = ClientContext(
        sex=client.sex, age=age, height_cm=client.height_cm,
        weight_kg=weight_now, goal_type=client.goal_type,
        level=client.level, training_days=client.training_days,
        session_max_min=client.session_max_min, training_place=client.training_place,
        diet_mode=client.diet_mode, diet_pattern=client.diet_pattern,
        meals_per_day=client.meals_per_day,
        meal_schedule=client.meal_schedule or [],
        food_allergies=client.food_allergies or [],
        food_dislikes=client.food_dislikes or [],
        food_likes=client.food_likes or [],
        contraindications=contra_tags,
        body_fat_pct=client.body_fat_pct,
        bmr=et.bmr, tdee=et.tdee, target_kcal=target_kcal_final, energy_method=et.method,
        macro_plan=macro_plan,
        exercise_library=library,
        deep_analysis=deep_analysis,
        notes=adj_notes,
        tracking_history=history_block,
        # "Motivo y objetivos" + estilo de vida en palabras del cliente: la IA
        # debe entender qué pide exactamente y planificar para ese fin.
        goal_in_own_words=client.lifestyle_notes,
        clinical_notes=clinical_notes,
        sport_history=client.sport_history,
        goal_weight_kg=client.goal_weight_kg,
        strict_free_meal=bool(client.strict_free_meal_enabled),
        goal_deadline=client.goal_deadline.isoformat() if client.goal_deadline else None,
    )
    # Paquete Start = solo nutrición: la IA no genera entrenamiento (ni el
    # educativo de entreno). Full/Pro generan el plan completo.
    include_training = pkgs.has_training(client.package_tier)
    include_nutrition = pkgs.has_nutrition(client.package_tier)
    # §2 (hardening): catálogo de alimentos FILTRADO (sin alérgenos/aversiones/patrón)
    # para que la IA seleccione por food_id y el solver fije los gramos.
    food_catalog = _food_catalog_for(db, client)
    try:
        generated = generate_monthly_plan(
            ctx, AIClient(), include_training=include_training,
            food_catalog=food_catalog, include_nutrition=include_nutrition)
    except PlanGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no devolvió un plan válido.", "error": str(exc)},
        ) from exc
    except AIGenerationError as exc:
        # Config/clave inválida u error de la API: mensaje accionable, no un 500.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": str(exc)},
        ) from exc

    nutrition, training, education, flags = generated.to_persistable()
    # AVISOS DE LAS MÉTRICAS: "el suelo seguro queda por encima del TDEE: esto
    # es mantenimiento, no déficit", "edad fuera de rango", "los suelos de
    # macros no cabían y se han subido las kcal"… se calculaban y se TIRABAN en
    # este camino (la base sin IA sí los conserva), así que el coach nunca los
    # veía en el plan generado con IA — que es el camino normal.
    flags = list(et.warnings) + list(_mp.notes) + list(flags)

    # Ninguna toma sin contenido: si la IA omitió un slot (o el filtrado de
    # alérgenos lo vació), recibe 3 opciones por defecto escaladas a sus macros —
    # el cliente siempre ve opciones concretas, nunca una "toma libre".
    from app.services.meal_fallback import ensure_bank_slots

    if nutrition is not None:
        ensure_bank_slots(nutrition, allergies=client.food_allergies or [],
                          dislikes=client.food_dislikes or [],
                          diet_pattern=client.diet_pattern)

    # Avisos de COBERTURA (auditoría de perfiles) — no bloquean, pero el coach
    # debe verlos: biblioteca de ejercicios fina o tomas sin opciones seguras.
    coverage_flags: list[str] = []
    _groups = {e.get("muscle_primary") for e in library}
    if len(library) < 15 or len(_groups) < 4:
        coverage_flags.append(
            f"aviso: biblioteca de ejercicios limitada para este cliente "
            f"({len(library)} ejercicios, {len(_groups)} grupos): añade material "
            "o revisa lesiones/exclusiones antes de confiar en el entreno.")
    try:
        from app.services.meal_fallback import _slot_is_empty
        _bank = ((nutrition or {}).get("meal_bank") or {})
        _by_slot = {sl.get("slot"): sl for sl in (_bank.get("slots") or [])}
        if (_bank.get("mode") or "") != "strict":
            for m in (nutrition.get("meals") or []):
                if _slot_is_empty(_by_slot.get(m.get("slot"))):
                    coverage_flags.append(
                        f"aviso: la toma «{m.get('name') or m.get('slot')}» no tiene "
                        "opciones seguras con las alergias/aversiones declaradas: "
                        "añádelas a mano en el editor.")
    except Exception:
        pass
    # (Las notas de `macro_targets` YA entraron arriba, con las de energía: si
    #  se añaden también aquí, el coach ve cada aviso DOS veces en el mismo
    #  plan — dos caminos vivos escritos por sesiones distintas.)
    if coverage_flags:
        flags = list(flags) + coverage_flags

    # Snapshot de los INPUTS con los que se generó (auditoría de ediciones):
    # si el coach corrige la ficha después (altura mal extraída, nivel, días…),
    # la alerta plan_stale_inputs compara contra esto y avisa en vez de callar.
    if nutrition is not None:
        nutrition["gen_inputs"] = {
            "weight_kg": weight_now, "height_cm": client.height_cm,
            "level": client.level, "training_days": client.training_days,
            "training_place": client.training_place, "diet_mode": client.diet_mode,
            "diet_pattern": client.diet_pattern,
        }

    # El TDEE que se persiste y se MUESTRA (déficit/superávit del PDF, del panel
    # del coach y del editor) es el AUTORITATIVO del backend (et.tdee), no el eco
    # que devuelve la IA: si no, el % de ajuste mostrado podía contradecir al que
    # valida el guardrail (p. ej. "Mantenimiento 0%" en un plan de pérdida real).
    if nutrition is not None:
        nutrition["tdee_kcal"] = round(et.tdee)

    # La regeneración YA incorpora los ajustes de la última revisión analizada
    # (van en el prompt): se SELLA applied_adjustments para que la alerta
    # "sin adaptar" se apague y "Adaptar" no vuelva a aplicarlos encima.
    # En un plan SOLO-ENTRENO (DQR Train) no hay nutrición donde sellarlo: el
    # sello va a `training_json`, que es donde lo busca la alerta (y donde lo
    # escribe la adaptación). Sin esto, a un cliente Train el aviso
    # "planificación sin adaptar" no se le apagaba NUNCA por mucho que el coach
    # regenerara, y "Adaptar" volvía a aplicarle encima los mismos ajustes.
    _sello_destino = nutrition if nutrition is not None else training
    if (_sello_destino is not None and last_analyzed
            and (last_analyzed.ai_analysis_json or {}).get("plan_adjustments")):
        _sello_destino["applied_adjustments"] = {
            "period_index": last_analyzed.period_index,
            "items": [{
                "area": a.get("area") or "general",
                "change": a.get("change") or "",
                "reason": a.get("reason") or "",
                "applied": True,
                "detail": "Incorporado al regenerar el plan con IA",
            } for a in last_analyzed.ai_analysis_json["plan_adjustments"]],
        }

    # §9 (hardening): panel de supervisión + reparación determinista + semáforo/ICP.
    # Best-effort: si el panel falla, el plan sale intacto y sin anotación. Puede
    # reconciliar la nutrición a rango (nunca la degrada) y marca ROJO si un
    # bloqueante persiste (el coach lo revisa; no hay auto-envío).
    from app.services.plan_review import review_generated_plan

    try:
        review_ai = AIClient()
    except Exception:  # noqa: BLE001
        review_ai = None
    review_summary = None
    if nutrition is not None:
        # El panel revisa la NUTRICIÓN: en un plan solo-entreno no aplica (el
        # entrenamiento ya pasó por check_training en la generación).
        nutrition, review_summary = review_generated_plan(
            nutrition, client=client, ctx=ctx, ai=review_ai,
            objective_macros=ctx.macro_plan,
            # Resumen del entreno para los roles que juzgan la coherencia
            # dieta↔entreno (antes solo veían la dieta).
            training=training,
        )
    if review_summary and review_summary.get("color") == "rojo":
        flags = list(flags) + [
            "revisión: ROJO — el panel detectó puntos a revisar antes de enviar"
        ]

    # Seguridad ("revisar antes de publicar"): con VIOLACIÓN de guardrail o
    # semáforo ROJO el plan NO se activa solo — queda en borrador, sin email ni
    # push al cliente, hasta que el coach lo revise (editar lo activa, o el
    # botón "Activar" del panel). Un warning no retiene.
    blocking = [f for f in flags if str(f).startswith("violation:")]
    retained = bool(blocking) or bool(review_summary and review_summary.get("color") == "rojo")
    if retained:
        flags = list(flags) + [
            "retenido: guardado como BORRADOR — revisa y activa tú (el cliente no ha sido avisado)"
        ]

    # MEMORIA DE VETOS: lo que hubo que frenar/corregir en esta generación se
    # anota; si un tropiezo se repite, la próxima generación lo lleva en el
    # prompt como advertencia (coach_lessons.vetos_reference).
    try:
        from app.services.coach_lessons import record_ai_vetos

        record_ai_vetos(list(flags))
    except Exception:  # noqa: BLE001
        pass

    # 5) Persistir como borrador (nueva versión del mes). El mes lo decide el
    # ciclo (dos revisiones = un mes) salvo que el llamante lo fije a mano.
    if month_index is None:
        from app.services.periods import current_month_index
        month_index = current_month_index(db, client_id)
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    plan = Plan(
        client_id=client_id, month_index=month_index, version=version, status="draft",
        nutrition_json=nutrition, training_json=training, education_json=education,
        guardrail_flags=flags, generated_by="ai", review_json=review_summary,
        goal_type=client.goal_type,  # snapshot: objetivo que sirve este plan
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_generated_ai", {
        "client_id": client_id, "version": version, "flags": flags,
        "retained": retained,
    })
    # La planificación queda ACTIVA al generarse (no hay botón "Publicar":
    # el envío al cliente va por WhatsApp y el portal se actualiza solo) —
    # SALVO que esté retenida por violación/ROJO (ver arriba).
    if not retained:
        from app.services.plan_activation import activate_plan

        activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": flags or [],
        # El frontend necesita saberlo para un toast HONESTO ("borrador
        # retenido: revísalo") en vez del "Planificación generada" triunfal.
        "retained": retained,
        "nutrition": nutrition, "training": training, "education": education,
        "review": review_summary,  # §9: color/ICP/hallazgos del panel
        # Fechas: el título del plan ("Planificación · julio 2026") las necesita
        # ya al generar, sin esperar a recargar la lista.
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "published_at": plan.published_at.isoformat() if plan.published_at else None,
    }


@router.post("/{client_id}/scaffold-plan")
def scaffold_client_plan(
    client_id: int,
    month_index: int | None = Query(default=None, ge=1),
    body: GeneratePlanIn | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Plan BASE determinista para clientes AVANZADOS — 0 llamadas a la IA.

    Al avanzado la planificación se la hace el COACH, pero no desde cero: aquí
    se prepara un borrador completo con todo lo que el sistema sabe calcular
    sin IA (objetivos y macros de metrics, comidas con target por toma, banco
    de comidas determinista y sesiones montadas desde la biblioteca filtrada).
    Queda SIEMPRE en borrador — editarlo NO lo activa (excepción al PATCH) —
    hasta que el coach pulse Activar. No consume ni un céntimo de créditos."""
    from datetime import date

    from app.models import Exercise, Plan
    from app.services import plan_scaffold
    from app.services.guardrails import filter_exercises_for_client
    from app.services.metrics import age_from_birth, energy_targets
    from app.services.metrics import macro_targets as _macro_targets

    client = _client_or_404_docs(db, client_id)

    # 0) Reparto de comidas elegido por el coach (mismo selector que el flujo
    # IA): sustituye al de la anamnesis y se persiste.
    if body is not None and body.meals:
        from app.services.meal_structure import meal_schedule_from_keys

        sched = meal_schedule_from_keys(body.meals)
        if sched:
            client.meal_schedule = sched
            client.meals_per_day = len(sched)
            db.commit()

    # 1) Anamnesis completa (misma vara de medir que la generación con IA).
    missing = []
    for field, label in _REQUIRED_FIELDS.items():
        if getattr(client, field, None) in (None, "", []):
            missing.append(label)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Faltan datos en la anamnesis para preparar el plan base.",
                "missing": missing,
            },
        )

    # 2) Números del motor determinista (la única verdad, la misma del flujo IA).
    age = age_from_birth(client.birth_date, date.today())
    from app.services.periods import reference_weight_kg

    weight_now = reference_weight_kg(db, client)
    et = energy_targets(
        sex=client.sex, weight_kg=weight_now, height_cm=client.height_cm,
        age=age, goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct, daily_activity=client.daily_activity_level,
        level=client.level, session_min=client.session_max_min,
    )
    _mp = _macro_targets(
        client.sex, weight_now, client.goal_type, et.target_kcal,
        client.training_days, tdee=et.tdee,
    )

    from app.services import packages as pkgs
    include_training = pkgs.has_training(client.package_tier)
    include_nutrition = pkgs.has_nutrition(client.package_tier)

    flags: list[str] = list(et.warnings) + list(_mp.notes)
    nutrition = training = None

    if include_nutrition:
        try:
            nutrition = plan_scaffold.build_nutrition(client, et, _mp)
        except Exception as exc:  # noqa: BLE001 — datos raros en la ficha → 422 accionable
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"No se pudo montar la base de nutrición con la ficha actual: {exc}. "
                "Revisa el horario de comidas en la pestaña Anamnesis.")
        # Banco de comidas determinista (foods + plantillas seguras), igual que
        # el fallback del flujo IA: alérgenos/aversiones/patrón respetados.
        # Modo ESTRICTO: menú cerrado de 7 días rotando las opciones seguras
        # (mismo formato que el flujo IA — el portal y el PDF deciden por
        # bank["mode"]). Modo flexible: banco de opciones por toma.
        if client.diet_mode == "strict":
            bank, avisos = plan_scaffold.build_strict_menu(
                nutrition, allergies=client.food_allergies or [],
                dislikes=client.food_dislikes or [], diet_pattern=client.diet_pattern,
            )
            nutrition["meal_bank"] = bank
            flags.extend(avisos)
            # Comida libre semanal pedida en la anamnesis: pauta determinista
            # (sin números — el criterio calórico ya lo fija el sistema).
            if bank is not None and client.strict_free_meal_enabled:
                bank["free_meal_guidelines"] = (
                    "Tienes UNA comida libre a la semana: elígela con cabeza "
                    "(mejor un día social), disfrútala sin convertirla en un día "
                    "libre entero y retoma el plan en la siguiente comida sin "
                    "compensar ni saltarte nada."
                )
            if bank is None:
                # NUNCA un plan sin banco: con meal_bank=None el portal servía
                # las tomas sin ningún plato y el PDF mutaba EN SILENCIO a
                # formato flexible (auditoría 27-08). Si el menú cerrado no se
                # puede montar con seguridad, se entrega banco flexible con un
                # aviso EXPLÍCITO y el coach decide (editor o Word).
                from app.services.meal_fallback import ensure_bank_slots

                ensure_bank_slots(
                    nutrition, allergies=client.food_allergies or [],
                    dislikes=client.food_dislikes or [],
                    diet_pattern=client.diet_pattern,
                )
                if nutrition.get("meal_bank"):
                    flags.append(
                        "el menú cerrado no se pudo montar con seguridad: este "
                        "borrador lleva banco FLEXIBLE de momento — ajústalo y "
                        "decide si mantener el modo estricto")
        else:
            from app.services.meal_fallback import _slot_is_empty, ensure_bank_slots

            ensure_bank_slots(
                nutrition, allergies=client.food_allergies or [],
                dislikes=client.food_dislikes or [], diet_pattern=client.diet_pattern,
            )
            bank_slots = {s.get("slot"): s for s in (nutrition.get("meal_bank") or {}).get("slots", [])}
            vacias = [m.get("name") or f"toma {m.get('slot')}" for m in nutrition.get("meals", [])
                      if _slot_is_empty(bank_slots.get(m.get("slot")))]
            if vacias:
                flags.append("sin opciones seguras de banco en: " + ", ".join(vacias)
                             + " — añádelas descargando el Word, editándolo y subiéndolo")
        # Mismos sidecars que la generación: snapshot de entradas (alertas de
        # ficha cambiada) y TDEE del motor.
        nutrition["gen_inputs"] = {
            "weight_kg": weight_now, "height_cm": client.height_cm,
            "level": client.level, "training_days": client.training_days,
            "training_place": client.training_place, "diet_mode": client.diet_mode,
            "diet_pattern": client.diet_pattern,
        }
        nutrition["tdee_kcal"] = round(et.tdee)

    if include_training:
        all_ex = db.scalars(select(Exercise)).all()
        ex_dicts = [{
            "id": e.id, "canonical_name": e.canonical_name, "name": e.canonical_name,
            "movement_pattern": e.movement_pattern,
            "muscle_primary": e.muscle_primary, "muscle_secondary": e.muscle_secondary or [],
            "equipment": e.equipment or [], "level_min": e.level_min,
            "contraindications": e.contraindications or [], "archived": e.archived,
            "technique_notes": e.technique_notes, "biomechanics_notes": e.biomechanics_notes,
        } for e in all_ex]
        level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
        equip = set() if client.training_place == "gym" else set(client.equipment or [])
        from app.services.injuries import injury_contra_tags

        contra_tags = injury_contra_tags(client.injuries_notes, client.medical_notes)
        library = filter_exercises_for_client(
            ex_dicts,
            client_contraindications=contra_tags,
            excluded_ids=set(client.excluded_exercise_ids or []),
            equipment_available=equip,
            level_max=level_map.get(client.level, 2),
            training_place=client.training_place,
        )
        if not library:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No hay ejercicios disponibles con las restricciones del cliente.")
        # Misma paridad de avisos que generate-plan: biblioteca fina → flag.
        _groups = {e.get("muscle_primary") for e in library if e.get("muscle_primary")}
        if len(library) < 15 or len(_groups) < 4:
            flags.append(
                f"biblioteca de ejercicios limitada tras el filtro ({len(library)} "
                f"ejercicios, {len(_groups)} grupos): revisa restricciones/material")
        try:
            training = plan_scaffold.build_training(client, library)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
        if len(training["sessions"]) < min(6, max(2, int(client.training_days or 3))):
            flags.append(
                f"solo se pudieron montar {len(training['sessions'])} de "
                f"{client.training_days} días con la biblioteca filtrada — "
                "completa el resto en el editor")

    flags.append("base sin IA: preparada por el sistema — la termina y activa el coach")

    # 3) Persistir como BORRADOR (nueva versión del mes). Nunca se auto-activa.
    if month_index is None:
        from app.services.periods import current_month_index
        month_index = current_month_index(db, client_id)
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    plan = Plan(
        client_id=client_id, month_index=month_index, version=version, status="draft",
        nutrition_json=nutrition, training_json=training, education_json=None,
        guardrail_flags=flags, generated_by="scaffold", review_json=None,
        goal_type=client.goal_type,
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_scaffolded", {
        "client_id": client_id, "version": version, "flags": flags,
    })
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": flags or [],
        "nutrition": nutrition, "training": training, "education": None,
        "review": None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "published_at": None,
    }


@router.post("/{client_id}/adapt-plan")
def adapt_client_plan(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Adapta el plan a la ÚLTIMA REVISIÓN QUINCENAL aplicando de forma
    determinista los ajustes ya calculados por la IA en el feedback (macros de
    dieta + cargas de entreno). NO llama a la IA → funciona siempre. La versión
    adaptada queda ACTIVA al momento (no hay paso de publicar)."""
    from app.services.adapt_plan import AdaptError, adapt_plan_from_feedback

    _client_or_404_docs(db, client_id)
    try:
        plan = adapt_plan_from_feedback(db, client_id)
    except AdaptError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status,
    }


# ------------------------------------------- leer anamnesis PDF con IA (extracción) ----
# La IA lee el PDF subido, extrae los datos estructurados + análisis en
# profundidad, y pre-rellena la ficha del cliente. El coach revisa antes de
# generar. El análisis cualitativo se guarda como sidecar para enriquecer el plan.

def _anamnesis_analysis_path(client_id: int):
    from app.services.storage import client_dir
    return client_dir(client_id, "documents") / "_anamnesis_analysis.json"


def _do_read_anamnesis(client_id: int, db: Session) -> dict:
    """Lee el PDF más reciente del cliente con IA y pre-rellena su ficha.
    Reutilizado por la subida (automático) y por el botón 'Leer con IA'."""
    import json as _json

    from app.services.ai.client import AIClient, AIGenerationError
    from app.services.ai.extraction import extract_anamnesis_from_pdf

    client = _client_or_404_docs(db, client_id)
    # Solo la ANAMNESIS: un adjunto (analítica) subido después no puede
    # convertirse en "el PDF más reciente" que la IA lee como cuestionario.
    from app.services.storage import anamnesis_documents

    docs = anamnesis_documents(client_id)
    if not docs:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Sube primero la anamnesis (PDF) antes de leerla con IA.",
        )
    pdf_bytes = abs_path(docs[0]["rel_path"]).read_bytes()
    try:
        extracted = extract_anamnesis_from_pdf(pdf_bytes, AIClient())
    except AIGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no pudo leer la anamnesis.", "error": str(exc)},
        ) from exc

    data = extracted.model_dump()
    for f in [
        "sex", "birth_date", "phone", "height_cm", "start_weight_kg", "body_fat_pct",
        "initial_waist_cm", "initial_hip_cm", "initial_arm_cm", "initial_thigh_cm",
        "goal_type", "goal_weight_kg", "goal_deadline", "level", "training_days",
        "daily_activity_level", "session_max_min",
        "training_place", "equipment", "diet_mode", "diet_pattern", "meals_per_day",
        "food_likes",
        "food_dislikes", "food_allergies", "injuries_notes", "medical_notes",
        "medication_notes", "current_supplements", "sport_history", "lifestyle_notes",
    ]:
        val = data.get(f)
        if val not in (None, [], ""):
            # El NIVEL elegido por el coach en el alta decide QUIÉN hace el plan
            # (IA vs base del coach): la autopercepción del PDF no lo pisa si ya
            # está fijado — el coach puede corregirlo a mano cuando quiera.
            if f == "level" and client.level:
                continue
            setattr(client, f, val)
    if data.get("meal_schedule"):
        client.meal_schedule = data["meal_schedule"]
    db.flush()
    # Contradicciones deterministas (§5, por fin cableado): plazo imposible,
    # objetivo que choca con su texto, dieta declarada vs alimentos que dice
    # comer. NO se resuelven solas: se enseñan al coach junto a la extracción.
    contradicciones: list[str] = []
    try:
        from app.services.anamnesis_extraction import detect_contradictions

        perfil = {k: getattr(client, k, None) for k in (
            "goal_type", "diet_pattern", "start_weight_kg", "goal_weight_kg",
            "goal_deadline", "lifestyle_notes", "sport_history", "food_likes")}
        contradicciones = [c.detail for c in detect_contradictions(perfil)]
    except Exception:
        contradicciones = []
    data["contradictions"] = contradicciones
    log_event(db, "client", client_id, "anamnesis_read_ai",
              {"source": docs[0]["name"], "contradictions": contradicciones})
    db.commit()
    try:
        _anamnesis_analysis_path(client_id).write_text(
            _json.dumps({
                "deep_analysis": data.get("deep_analysis"),
                "injuries_notes": data.get("injuries_notes"),
                "contradictions": contradicciones,
                "at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass
    return data


@router.post("/{client_id}/read-anamnesis")
def read_anamnesis_with_ai(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Lee el PDF más reciente del cliente con IA y pre-rellena su ficha."""
    data = _do_read_anamnesis(client_id, db)
    return {
        "extracted": data,
        "deep_analysis": data.get("deep_analysis"),
        "contradictions": data.get("contradictions") or [],
        "message": "Anamnesis leída. Revisa los datos antes de generar el plan.",
    }


# ------------------------------------------- etapa del objetivo (45 días) ----
# El objetivo del cliente es una ETAPA: a los 45 días la web sugiere valorarlo.
# "Mantener objetivo" pospone la alerta otros 45 días; "Cambiar objetivo"
# arranca etapa nueva y la planificación se regenera entera para el objetivo
# nuevo (la antigua queda archivada con su objetivo y duración).

GOAL_REVIEW_DAYS = 45

_GOAL_LABEL = {
    "fat_loss": "pérdida de grasa", "muscle_gain": "ganancia muscular",
    "recomp": "recomposición corporal", "maintenance": "mantenimiento",
    "injury_recovery": "recuperación de lesión",
}


@router.post("/{client_id}/goal-review/snooze", response_model=ClientOut)
def snooze_goal_review(client_id: int, db: Session = Depends(get_db)) -> ClientOut:
    """"Mantener objetivo actual": apaga la alerta de los 45 días (se
    reevaluará pasados otros 45)."""
    from datetime import date as _date

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    client.goal_review_snoozed_on = _date.today()
    log_event(db, "client", client.id, "goal_review_snoozed", {"goal": client.goal_type})
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


class GoalChangeIn(BaseModel):
    goal_type: str
    goal_weight_kg: float | None = None


@router.post("/{client_id}/change-goal", response_model=ClientOut)
def change_goal(client_id: int, body: GoalChangeIn, db: Session = Depends(get_db)) -> ClientOut:
    """Cambia el objetivo del cliente y arranca una etapa nueva. El plan
    vigente queda como archivo (conserva su goal_type); el coach regenera
    después la planificación completa para el objetivo nuevo."""
    from datetime import date as _date

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    if body.goal_type not in _GOAL_LABEL:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Objetivo no válido")
    if body.goal_type == client.goal_type:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Ese ya es el objetivo actual del cliente")
    old = client.goal_type
    client.goal_type = body.goal_type
    if body.goal_weight_kg is not None:
        client.goal_weight_kg = body.goal_weight_kg
    client.goal_started_on = _date.today()
    client.goal_review_snoozed_on = None
    log_event(db, "client", client.id, "goal_changed",
              {"from": old, "to": body.goal_type})
    db.commit()
    db.refresh(client)
    return ClientOut.model_validate(client)


@router.post("/{client_id}/goal-review/analysis")
def goal_review_analysis(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Texto PROFESIONAL generado automáticamente para valorar el cambio de
    objetivo: qué se ha conseguido (punto de partida → actual), qué cabe
    esperar si se continúa igual, y opciones de objetivo razonables según su
    estado. IA con respaldo determinista (el botón funciona siempre)."""
    from datetime import date as _date

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    h = client_history(client_id, db)
    days = (_date.today() - client.goal_started_on).days if client.goal_started_on else None
    goal_label = _GOAL_LABEL.get(client.goal_type or "", client.goal_type or "sin objetivo")
    start_w, cur_w = h.get("start_weight_kg"), h.get("current_weight_kg")
    delta_w = round(cur_w - start_w, 1) if (start_w is not None and cur_w is not None) else None
    reviews = [p for p in h["periods"] if p["status"] in ("closed", "analyzed")]
    adhs = [p["adherence_pct"] for p in reviews if p.get("adherence_pct") is not None]
    adh_media = round(sum(adhs) / len(adhs)) if adhs else None

    resumen = {
        "objetivo_actual": goal_label,
        "dias_en_el_objetivo": days,
        "peso_inicial_kg": start_w, "peso_actual_kg": cur_w, "cambio_kg": delta_w,
        "peso_objetivo_kg": h.get("goal_weight_kg"),
        "le_quedan_kg": h.get("remaining_to_goal_kg"),
        "fuerza_total_pct": h.get("total_strength_gain_pct"),
        "medidas": h.get("measures"),
        "revisiones_completadas": len(reviews),
        "adherencia_media_pct": adh_media,
    }

    # Opciones de objetivo razonables según el estado (excluye el actual)
    options = [g for g in _GOAL_LABEL if g != client.goal_type]

    # CACHÉ por contenido (ahorro de créditos): cada clic del botón pagaba una
    # llamada aunque los datos no hubieran cambiado. El análisis se guarda como
    # sidecar con el hash del resumen: mismos datos → mismo texto, 0 créditos.
    import hashlib as _hashlib

    _clave = _hashlib.sha1(
        json.dumps(resumen, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    _cache_file = None
    try:
        from app.services.storage import client_dir

        _cache_file = client_dir(client_id, "documents") / "_goal_review.json"
        if _cache_file.exists():
            _cacheado = json.loads(_cache_file.read_text(encoding="utf-8"))
            if _cacheado.get("key") == _clave and _cacheado.get("text"):
                return {"text": _cacheado["text"], "cached": True}
    except Exception:  # noqa: BLE001 — la caché nunca rompe el botón
        _cache_file = None

    text: str | None = None
    try:
        from app.services.ai.client import AIClient

        ai = AIClient()
        text = ai._raw_call(
            model=settings.model_light,
            max_tokens=1200,  # 200-300 palabras: techo anti-desbocadas
            system=(
                "Eres el asistente de un equipo de asesoramiento fitness de élite. "
                "Escribes en castellano, tono PROFESIONAL, serio y cercano, sin emojis "
                "ni exageraciones. Redactas un análisis breve (200-300 palabras) para "
                "que el coach valore con su cliente un posible cambio de objetivo."
            ),
            user=(
                "Con estos datos reales del cliente, redacta el análisis en 4 bloques con estos "
                "títulos exactos: 'Lo conseguido hasta hoy' (punto de partida → actual, con cifras); "
                "'Si continúa con el objetivo actual' (proyección realista a 4-6 semanas); "
                "'Opciones de objetivo a valorar' (2-3 opciones de esta lista, y para CADA una "
                "di QUÉ GANARÍA el cliente cambiando frente a seguir con su plan y objetivo "
                f"actuales — beneficios concretos, no generalidades: {', '.join(_GOAL_LABEL[g] for g in options)}); "
                "y 'Veredicto' (di con claridad qué es mejor AHORA: mantener el objetivo actual o "
                "cambiar a una opción concreta, y por qué — si el objetivo inicial aún no se ha "
                "alcanzado (mira le_quedan_kg) y el progreso es bueno, valora explícitamente si "
                "compensa cambiar antes de llegar). No inventes datos que no estén aquí.\n\n"
                f"DATOS: {json.dumps(resumen, ensure_ascii=False)}"
            ),
        ).strip()
    except Exception:
        text = None

    if not text:
        # Respaldo determinista con los mismos bloques y tono profesional
        pes = (f"{start_w} kg → {cur_w} kg ({'+' if (delta_w or 0) > 0 else ''}{delta_w} kg)"
               if delta_w is not None else "sin datos de peso suficientes")
        fuerza = (f" La fuerza ha mejorado un {h['total_strength_gain_pct']}% en los básicos."
                  if h.get("total_strength_gain_pct") else "")
        adh = f" Adherencia media a la dieta del {adh_media}%." if adh_media else ""
        dias_txt = f"{days} días" if days is not None else "esta etapa"
        text = (
            f"Lo conseguido hasta hoy\n"
            f"Tras {dias_txt} trabajando {goal_label}, el peso ha pasado de {pes}."
            f"{fuerza}{adh} Se han completado {len(reviews)} revisiones quincenales.\n\n"
            f"Si continúa con el objetivo actual\n"
            f"Manteniendo la adherencia actual, cabe esperar una progresión similar a la de "
            f"las últimas semanas durante las próximas 4-6, con ajustes quincenales del plan.\n\n"
            f"Opciones de objetivo a valorar\n"
            + "\n".join(f"· {_GOAL_LABEL[g].capitalize()}: ganaría {_GOAL_GAIN.get(g, 'un enfoque distinto')} "
                        f"frente a seguir con {goal_label}." for g in options[:3])
            + "\n\nVeredicto\n" + _goal_verdict_fallback(h, goal_label, adh_media)
        )

    if _cache_file is not None and text:
        try:
            _cache_file.write_text(
                json.dumps({"key": _clave, "text": text}, ensure_ascii=False),
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    return {"text": text, "summary": resumen, "options": options}


# Qué GANARÍA el cliente con cada objetivo (respaldo determinista del análisis)
_GOAL_GAIN = {
    "fat_loss": "acelerar la pérdida de grasa y la definición visible",
    "muscle_gain": "aprovechar la mejora de fuerza para construir masa muscular con superávit ligero",
    "recomp": "mantener el peso mientras mejora la composición (músculo arriba, grasa abajo)",
    "maintenance": "consolidar lo logrado, descansar del déficit/superávit y proteger la adherencia",
    "injury_recovery": "priorizar la recuperación de la lesión sin perder lo ganado",
}


def _goal_verdict_fallback(h: dict, goal_label: str, adh_media: int | None) -> str:
    """Veredicto determinista: mantener vs cambiar, contando si el objetivo
    inicial aún no se ha alcanzado."""
    rem = h.get("remaining_to_goal_kg")
    if rem is not None and abs(rem) > 1.5:
        adh_txt = f" y la adherencia media es del {adh_media}%" if adh_media is not None else ""
        return (f"Aún quedan {abs(rem)} kg para el peso objetivo{adh_txt}: salvo estancamiento "
                f"claro o cambio de prioridades del cliente, lo más razonable es MANTENER "
                f"{goal_label} y reevaluar en la próxima revisión quincenal.")
    return ("El objetivo inicial está prácticamente conseguido: es buen momento para cambiar de "
            "etapa. La primera opción de la lista es la transición más natural; coméntala con el "
            "cliente y regenera la planificación al confirmar.")
