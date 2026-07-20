"""CRUD de clientes + links de portal + RGPD (supresión y portabilidad)."""


import io
import json
import re
import statistics
import zipfile
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
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
        anamnesis_url=f"{base}/p/{client.portal_token}/anamnesis",
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


def _quincenal_entry(db: Session, period: Period, prev: Period | None) -> dict:
    """Datos completos de una revisión quincenal con ANTES/DESPUÉS (día 1 vs 15)."""
    logs = list(db.scalars(
        select(DailyLog).where(DailyLog.period_id == period.id).order_by(DailyLog.log_date)
    ))
    first_w = next((lg.weight_kg for lg in logs if lg.weight_kg is not None), None)
    before_w = first_w if first_w is not None else (prev.closing_weight_kg if prev else None)
    return {
        "period_index": period.period_index,
        "starts_on": period.starts_on.isoformat(),
        "ends_on": period.ends_on.isoformat(),
        "status": period.status,
        "analyzed": period.status == "analyzed",
        # Peso día 1 → día 15
        "weight_before": before_w,
        "weight_after": period.closing_weight_kg,
        # Perímetros (cinta): período anterior → este
        "waist_before": prev.closing_waist_cm if prev else None, "waist_after": period.closing_waist_cm,
        "hip_before": prev.closing_hip_cm if prev else None, "hip_after": period.closing_hip_cm,
        "arm_before": prev.closing_arm_cm if prev else None, "arm_after": period.closing_arm_cm,
        "thigh_before": prev.closing_thigh_cm if prev else None, "thigh_after": period.closing_thigh_cm,
        # Sensaciones + valoración /10
        "feelings": period.closing_feelings_json,
        "feelings_score_10": _feelings_score_10(period.closing_feelings_json),
        "adherence_diet": period.adherence_diet_0_10,
        "adherence_training": period.adherence_training_0_10,
        "free_meals": period.free_meals_count,
        "changes": period.closing_changes, "hardest": period.closing_hardest,
        "next_goal": period.closing_next_goal, "questions": period.closing_questions,
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
    daily = []
    for lg in logs:
        n_sets = db.scalar(
            select(func.count()).select_from(WorkoutLog).where(WorkoutLog.daily_log_id == lg.id)
        ) or 0
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

    today = _date.today()
    days_elapsed = (min(today, period.ends_on) - period.starts_on).days + 1

    # Revisiones quincenales acumuladas (más reciente primero), con antes/después
    quincenals = []
    for i in range(len(periods) - 1, -1, -1):
        pr = periods[i]
        if pr.status in ("closed", "analyzed"):
            quincenals.append(_quincenal_entry(db, pr, periods[i - 1] if i > 0 else None))

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
        "days_logged": len(logs),
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
        status="onboarding",
        auto_pilot=settings.auto_pilot_default,
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
@router.get("", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    status_filter: ClientStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/email"),
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


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientOut:
    return ClientOut.model_validate(_get_or_404(db, client_id))


# ---------------------------------------------------- edición con audit ----
@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientUpdate, db: Session = Depends(get_db)) -> ClientOut:
    """Edición por el coach (anamnesis editable con audit trail, H.2)."""
    client = _get_or_404(db, client_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return ClientOut.model_validate(client)

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
        "periods": [
            {
                "period_index": pe.period_index, "starts_on": _jsonable(pe.starts_on),
                "ends_on": _jsonable(pe.ends_on), "status": pe.status,
                "closing_weight_kg": pe.closing_weight_kg, "metrics": pe.metrics_json,
            }
            for pe in db.scalars(select(Period).where(Period.client_id == client_id).order_by(Period.period_index))
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("datos.json", json.dumps(data, ensure_ascii=False, indent=2))
        photos = db.scalars(select(ProgressPhoto).where(ProgressPhoto.client_id == client_id))
        for ph in photos:
            p = abs_path(ph.file_path)
            if p.exists():
                zf.write(p, f"fotos/{p.name}")
        docs_dir = storage_root() / "clients" / str(client_id) / "documents"
        if docs_dir.exists():
            for f in sorted(docs_dir.iterdir()):
                if f.is_file():
                    zf.write(f, f"documentos/{f.name}")

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
    db.execute(delete(Period).where(Period.client_id == client_id))
    db.execute(delete(Plan).where(Plan.client_id == client_id))
    db.execute(delete(ChangeRequest).where(ChangeRequest.client_id == client_id))
    db.execute(update(EmailLog).where(EmailLog.client_id == client_id).values(client_id=None))
    db.delete(client)

    delete_client_tree(client_id)
    # Registro anónimo de la baja: sin nombre, sin email (PARTE I)
    log_event(db, "client", client_id, "client_deleted", {"anonymous": True})
    db.commit()
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
    # Una sola anamnesis por cliente: borrar las anteriores antes de guardar
    from app.services.storage import client_dir
    folder = client_dir(client_id, "documents")
    for old in folder.iterdir():
        if old.is_file() and old.suffix.lower() == ".pdf":
            try:
                old.unlink()
            except Exception:
                pass
    rel = save_document(client_id, content, filename or "anamnesis.pdf")
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

    return {"name": name, "rel_path": rel, "read_ok": read_ok,
            "read_error": read_error, "portal_access": access_status}


@router.post("/{client_id}/documents")
def upload_client_document(
    client_id: int,
    file: UploadFile = File(..., description="PDF de la anamnesis rellenada"),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un documento (PDF) y lo asocia al cliente."""
    _client_or_404_docs(db, client_id)
    try:
        return ingest_anamnesis_pdf(db, client_id, file.file.read(),
                                    file.filename or "anamnesis.pdf", by="coach")
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/{client_id}/documents")
def get_client_documents(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lista los documentos subidos del cliente."""
    _client_or_404_docs(db, client_id)
    return list_documents(client_id)


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
# Ciclo quincenal: alerta "agendar" al llegar la revisión → el coach la propone
# por WhatsApp (con su enlace de reservas) → apunta la fecha elegida →
# recordatorio el día antes → tras la fecha, confirmar realizada o reagendar.

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


class VideoCallIn(BaseModel):
    period_index: int


class VideoCallSchedule(BaseModel):
    scheduled_for: date


@router.post("/{client_id}/video-calls")
def create_video_call(client_id: int, body: VideoCallIn, db: Session = Depends(get_db)) -> dict:
    """La propuesta se ha ENVIADO (se abrió el WhatsApp con el enlace de
    reservas): queda pendiente de que el cliente elija día. Idempotente."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    _client_or_404_docs(db, client_id)
    vc = db.scalar(select(VideoCall).where(
        VideoCall.client_id == client_id, VideoCall.period_index == body.period_index))
    if vc is None:
        vc = VideoCall(client_id=client_id, period_index=body.period_index, status="pending")
        db.add(vc)
        log_event(db, "client", client_id, "video_call_proposed",
                  {"period_index": body.period_index})
        db.commit()
        db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.patch("/{client_id}/video-calls/{call_id}")
def schedule_video_call(client_id: int, call_id: int, body: VideoCallSchedule,
                        db: Session = Depends(get_db)) -> dict:
    """El cliente eligió día: se apunta la fecha (activa los recordatorios)."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    vc.scheduled_for = body.scheduled_for
    vc.status = "scheduled"
    log_event(db, "client", client_id, "video_call_scheduled",
              {"period_index": vc.period_index, "date": body.scheduled_for.isoformat()})
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.post("/{client_id}/video-calls/{call_id}/done")
def video_call_done(client_id: int, call_id: int, db: Session = Depends(get_db)) -> dict:
    """La videollamada se REALIZÓ: se cierra y la alerta desaparece."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    vc.status = "done"
    log_event(db, "client", client_id, "video_call_done", {"period_index": vc.period_index})
    db.commit()
    db.refresh(vc)
    return VideoCallOut.model_validate(vc).model_dump(mode="json")


@router.post("/{client_id}/video-calls/{call_id}/reschedule")
def video_call_reschedule(client_id: int, call_id: int, db: Session = Depends(get_db)) -> dict:
    """NO se realizó: vuelve a pendiente sin fecha y el ciclo empieza de nuevo
    (agendar por WhatsApp → fecha → recordatorios)."""
    from app.models import VideoCall
    from app.schemas.entities import VideoCallOut

    vc = db.get(VideoCall, call_id)
    if not vc or vc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Videollamada no encontrada")
    vc.status = "pending"
    vc.scheduled_for = None
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
    from app.services.feedback_service import compute_period_summary

    client = _client_or_404_docs(db, client_id)
    periods = list(db.scalars(
        select(Period).where(Period.client_id == client_id).order_by(Period.period_index)
    ))
    plans = list(db.scalars(
        select(Plan).where(Plan.client_id == client_id).order_by(Plan.month_index, Plan.version)
    ))

    current = client.start_weight_kg
    hist = []
    e1rm_series: dict[str, list[float]] = {}  # nombre → e1rm por período (para % total)
    for p in periods:
        try:
            m = compute_period_summary(db, p.id)
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
        fb = db.scalar(
            select(FeedbackDoc).where(FeedbackDoc.period_id == p.id)
            .order_by(FeedbackDoc.id.desc()).limit(1)
        )
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
            "feedback_id": fb.id if fb else None,
            "feedback_sent": bool(fb and fb.sent_at),
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
            {"id": pl.id, "month_index": pl.month_index, "version": pl.version, "status": pl.status}
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


@router.get("/{client_id}/photos/{photo_id}")
def get_client_photo(client_id: int, photo_id: int, db: Session = Depends(get_db)):
    """Sirve una foto de progreso (requiere JWT del coach)."""
    p = db.get(ProgressPhoto, photo_id)
    if not p or p.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto no encontrada")
    path = abs_path(p.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    ext = path.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "application/octet-stream")
    return Response(
        content=path.read_bytes(), media_type=media,
        headers={"Content-Disposition": f'inline; filename="foto_{photo_id}{ext}"'},
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


@router.post("/{client_id}/generate-plan")
def generate_client_plan(
    client_id: int,
    month_index: int = Query(default=1, ge=1),
    body: GeneratePlanIn | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Genera (con IA real) el plan mensual del cliente y lo guarda como borrador."""
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
    # Peso ACTUAL del cliente (último registro del portal o cierre quincenal):
    # tras semanas de seguimiento —o al regenerar por cambio de objetivo— las
    # calorías y macros deben partir del peso real de hoy, no del inicial.
    latest_log_w = db.scalar(
        select(DailyLog.weight_kg)
        .join(Period, DailyLog.period_id == Period.id)
        .where(Period.client_id == client_id, DailyLog.weight_kg.is_not(None))
        .order_by(DailyLog.log_date.desc()).limit(1)
    )
    latest_close_w = db.scalar(
        select(Period.closing_weight_kg)
        .where(Period.client_id == client_id, Period.closing_weight_kg.is_not(None))
        .order_by(Period.period_index.desc()).limit(1)
    )
    weight_now = latest_log_w or latest_close_w or client.current_weight_kg or client.start_weight_kg

    et = energy_targets(
        sex=client.sex, weight_kg=weight_now, height_cm=client.height_cm,
        age=age, goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct, daily_activity=client.daily_activity_level,
    )

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
        diet_mode=client.diet_mode, meals_per_day=client.meals_per_day,
        meal_schedule=client.meal_schedule or [],
        food_allergies=client.food_allergies or [],
        food_dislikes=client.food_dislikes or [],
        food_likes=client.food_likes or [],
        contraindications=contra_tags,
        body_fat_pct=client.body_fat_pct,
        bmr=et.bmr, tdee=et.tdee, target_kcal=et.target_kcal, energy_method=et.method,
        exercise_library=library,
        deep_analysis=deep_analysis,
        notes=adj_notes,
        tracking_history=history_block,
        # "Motivo y objetivos" + estilo de vida en palabras del cliente: la IA
        # debe entender qué pide exactamente y planificar para ese fin.
        goal_in_own_words=client.lifestyle_notes,
        clinical_notes=clinical_notes,
    )
    # Paquete Start = solo nutrición: la IA no genera entrenamiento (ni el
    # educativo de entreno). Full/Pro generan el plan completo.
    include_training = client.package_tier != "start"
    try:
        generated = generate_monthly_plan(ctx, AIClient(), include_training=include_training)
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

    # Ninguna toma sin contenido: si la IA omitió un slot (o el filtrado de
    # alérgenos lo vació), recibe 3 opciones por defecto escaladas a sus macros —
    # el cliente siempre ve opciones concretas, nunca una "toma libre".
    from app.services.meal_fallback import ensure_bank_slots

    ensure_bank_slots(nutrition, allergies=client.food_allergies or [],
                      dislikes=client.food_dislikes or [])

    # El TDEE que se persiste y se MUESTRA (déficit/superávit del PDF, del panel
    # del coach y del editor) es el AUTORITATIVO del backend (et.tdee), no el eco
    # que devuelve la IA: si no, el % de ajuste mostrado podía contradecir al que
    # valida el guardrail (p. ej. "Mantenimiento 0%" en un plan de pérdida real).
    nutrition["tdee_kcal"] = round(et.tdee)

    # La regeneración YA incorpora los ajustes de la última revisión analizada
    # (van en el prompt): se SELLA applied_adjustments para que la alerta
    # "sin adaptar" se apague y "Adaptar" no vuelva a aplicarlos encima.
    if last_analyzed and (last_analyzed.ai_analysis_json or {}).get("plan_adjustments"):
        nutrition["applied_adjustments"] = {
            "period_index": last_analyzed.period_index,
            "items": [{
                "area": a.get("area") or "general",
                "change": a.get("change") or "",
                "reason": a.get("reason") or "",
                "applied": True,
                "detail": "Incorporado al regenerar el plan con IA",
            } for a in last_analyzed.ai_analysis_json["plan_adjustments"]],
        }

    # 5) Persistir como borrador (nueva versión del mes)
    last = db.scalar(
        select(Plan).where(Plan.client_id == client_id, Plan.month_index == month_index)
        .order_by(Plan.version.desc()).limit(1)
    )
    version = (last.version + 1) if last else 1
    plan = Plan(
        client_id=client_id, month_index=month_index, version=version, status="draft",
        nutrition_json=nutrition, training_json=training, education_json=education,
        guardrail_flags=flags, generated_by="ai",
        goal_type=client.goal_type,  # snapshot: objetivo que sirve este plan
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_generated_ai", {
        "client_id": client_id, "version": version, "flags": flags,
    })
    # La planificación queda ACTIVA al generarse (no hay botón "Publicar":
    # el envío al cliente va por WhatsApp y el portal se actualiza solo).
    from app.services.plan_activation import activate_plan

    activate_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": flags or [],
        "nutrition": nutrition, "training": training, "education": education,
        # Fechas: el título del plan ("Planificación · julio 2026") las necesita
        # ya al generar, sin esperar a recargar la lista.
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "published_at": plan.published_at.isoformat() if plan.published_at else None,
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
    docs = list_documents(client_id)
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
        "sex", "birth_date", "height_cm", "start_weight_kg", "body_fat_pct",
        "goal_type", "goal_weight_kg", "level", "training_days", "daily_activity_level",
        "session_max_min",
        "training_place", "equipment", "diet_mode", "meals_per_day", "food_likes",
        "food_dislikes", "food_allergies", "injuries_notes", "medical_notes",
        "medication_notes", "current_supplements", "sport_history", "lifestyle_notes",
    ]:
        val = data.get(f)
        if val not in (None, [], ""):
            setattr(client, f, val)
    if data.get("meal_schedule"):
        client.meal_schedule = data["meal_schedule"]
    db.flush()
    log_event(db, "client", client_id, "anamnesis_read_ai", {"source": docs[0]["name"]})
    db.commit()
    try:
        _anamnesis_analysis_path(client_id).write_text(
            _json.dumps({
                "deep_analysis": data.get("deep_analysis"),
                "injuries_notes": data.get("injuries_notes"),
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

    text: str | None = None
    try:
        from app.services.ai.client import AIClient

        ai = AIClient()
        text = ai._raw_call(
            model=settings.model_light,
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
