

===== FILE: backend/app/routers/__init__.py =====



===== FILE: backend/app/routers/auth.py =====

"""Autenticación de coaches (JWT)."""


from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.entities import LoginIn, TokenOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Login de los admins seedados desde el .env. 5 intentos/minuto por IP."""
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        # Mensaje único: no revela si el usuario existe
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    return TokenOut(access_token=create_access_token(user.username))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "username": user.username}


===== FILE: backend/app/routers/brand.py =====

"""Configuración de marca (H.1) — única fila, aplica a app/portal/docs/emails."""


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import BrandConfig
from app.schemas.entities import BrandConfigIn, BrandConfigOut
from app.services.audit import log_event
from app.services.storage import PhotoValidationError, save_brand_logo

router = APIRouter(prefix="/api/brand", tags=["brand"], dependencies=[Depends(get_current_user)])


def _brand(db: Session) -> BrandConfig:
    brand = db.scalar(select(BrandConfig).limit(1))
    if not brand:  # el seed la crea; defensa por si se vació la tabla
        brand = BrandConfig()
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


@router.get("", response_model=BrandConfigOut)
def get_brand(db: Session = Depends(get_db)) -> BrandConfigOut:
    return BrandConfigOut.model_validate(_brand(db))


@router.put("", response_model=BrandConfigOut)
def update_brand(body: BrandConfigIn, db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    for field, value in body.model_dump().items():
        setattr(brand, field, value)
    log_event(db, "brand", brand.id, "brand_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)


@router.post("/logo", response_model=BrandConfigOut)
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    try:
        brand.logo_path = save_brand_logo(file.file.read(), file.filename or "logo")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_logo_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)


===== FILE: backend/app/routers/clients.py =====

"""CRUD de clientes + links de portal + RGPD (supresión y portabilidad)."""


import io
import json
import re
import statistics
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, or_, select, update
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
    """Extrae un nº de pasos de un texto libre ('cardio + 4500' → 4500)."""
    if not text:
        return None
    nums = re.findall(r"\d[\d\.]*", text.replace(",", ""))
    vals = [float(n) for n in nums if n.replace(".", "").isdigit()]
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
    if db.scalar(select(Client).where(Client.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un cliente con ese email")

    client = Client(
        full_name=body.full_name.strip(),
        email=body.email,
        phone=body.phone,
        status="onboarding",
        auto_pilot=settings.auto_pilot_default,
        portal_token="pendiente",  # se firma con el id real tras el flush
    )
    db.add(client)
    db.flush()
    client.portal_token = new_portal_token(client.id)
    log_event(db, "client", client.id, "client_created", {"by": "coach"})
    db.commit()
    db.refresh(client)
    return ClientCreatedOut(client=ClientOut.model_validate(client), links=_links(client))


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
    if clients:
        rows = db.execute(
            select(Period.client_id, func.max(Period.period_index))
            .where(
                Period.client_id.in_([c.id for c in clients]),
                Period.status.in_(("closed", "analyzed")),
                Period.coach_reviewed_at.is_(None),
            )
            .group_by(Period.client_id)
        ).all()
        pending = {cid: idx for cid, idx in rows}

    out = []
    for c in clients:
        item = ClientOut.model_validate(c)
        if c.id in pending:
            item.pending_review = True
            item.pending_review_period = pending[c.id]
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


@router.post("/{client_id}/documents")
def upload_client_document(
    client_id: int,
    file: UploadFile = File(..., description="PDF de la anamnesis rellenada"),
    db: Session = Depends(get_db),
) -> dict:
    """Sube un documento (PDF) y lo asocia al cliente."""
    _client_or_404_docs(db, client_id)
    # Una sola anamnesis por cliente: borrar las anteriores antes de guardar
    from app.services.storage import client_dir
    folder = client_dir(client_id, "documents")
    for old in folder.iterdir():
        if old.is_file() and old.suffix.lower() == ".pdf":
            try:
                old.unlink()
            except Exception:
                pass
    try:
        rel = save_document(client_id, file.file.read(), file.filename or "anamnesis.pdf")
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "client", client_id, "document_uploaded", {"path": rel})
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

    return {"name": name, "rel_path": rel, "read_ok": read_ok, "read_error": read_error}


@router.get("/{client_id}/documents")
def get_client_documents(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lista los documentos subidos del cliente."""
    _client_or_404_docs(db, client_id)
    return list_documents(client_id)


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

# Campos estructurados imprescindibles para poder generar
_REQUIRED_FIELDS = {
    "sex": "Sexo", "birth_date": "Fecha de nacimiento", "height_cm": "Altura",
    "start_weight_kg": "Peso inicial", "goal_type": "Objetivo", "level": "Nivel",
    "training_days": "Días de entrenamiento", "session_max_min": "Duración de sesión",
    "training_place": "Dónde entrena", "diet_mode": "Modo de dieta",
    "meals_per_day": "Comidas al día",
}


@router.post("/{client_id}/generate-plan")
def generate_client_plan(
    client_id: int,
    month_index: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
) -> dict:
    """Genera (con IA real) el plan mensual del cliente y lo guarda como borrador."""
    from datetime import date

    from app.models import Exercise, Plan
    from app.services.ai.client import AIClient
    from app.services.ai.generator import (
        ClientContext,
        PlanGenerationError,
        generate_monthly_plan,
    )
    from app.services.guardrails import filter_exercises_for_client
    from app.services.metrics import age_from_birth, energy_targets

    client = _client_or_404_docs(db, client_id)

    # 1) Validar que la anamnesis estructurada está completa
    missing = []
    for field, label in _REQUIRED_FIELDS.items():
        if getattr(client, field, None) in (None, "", []):
            missing.append(label)
    if not client.meal_schedule:
        missing.append("Horario de comidas")
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
    et = energy_targets(
        sex=client.sex, weight_kg=client.start_weight_kg, height_cm=client.height_cm,
        age=age, goal_type=client.goal_type, training_days=client.training_days,
        body_fat_pct=client.body_fat_pct,
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
    library = filter_exercises_for_client(
        ex_dicts,
        client_contraindications=set(),
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

    # 4) Construir el contexto y pedir el plan a la IA
    ctx = ClientContext(
        sex=client.sex, age=age, height_cm=client.height_cm,
        weight_kg=client.start_weight_kg, goal_type=client.goal_type,
        level=client.level, training_days=client.training_days,
        session_max_min=client.session_max_min, training_place=client.training_place,
        diet_mode=client.diet_mode, meals_per_day=client.meals_per_day,
        meal_schedule=client.meal_schedule or [],
        food_allergies=client.food_allergies or [],
        food_dislikes=client.food_dislikes or [],
        food_likes=client.food_likes or [],
        contraindications=set(),
        body_fat_pct=client.body_fat_pct,
        bmr=et.bmr, tdee=et.tdee, target_kcal=et.target_kcal, energy_method=et.method,
        exercise_library=library,
        deep_analysis=deep_analysis,
        notes=adj_notes,
    )
    try:
        generated = generate_monthly_plan(ctx, AIClient())
    except PlanGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={"message": "La IA no devolvió un plan válido.", "error": str(exc)},
        ) from exc

    nutrition, training, education, flags = generated.to_persistable()

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
    )
    db.add(plan)
    db.flush()
    log_event(db, "plan", plan.id, "plan_generated_ai", {
        "client_id": client_id, "version": version, "flags": flags,
    })
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id, "month_index": plan.month_index, "version": plan.version,
        "status": plan.status, "guardrail_flags": flags or [],
        "nutrition": nutrition, "training": training, "education": education,
    }


@router.post("/{client_id}/adapt-plan")
def adapt_client_plan(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Adapta el plan a la ÚLTIMA REVISIÓN QUINCENAL aplicando de forma
    determinista los ajustes ya calculados por la IA en el feedback (macros de
    dieta + cargas de entreno). NO llama a la IA → funciona siempre. Crea una
    nueva versión en borrador para que el coach la revise y publique."""
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
        "goal_type", "goal_weight_kg", "level", "training_days", "session_max_min",
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


===== FILE: backend/app/routers/exercises.py =====

"""Biblioteca de ejercicios (F.3): filtros, alta de personalizados, edición
(video_url incluido) y archivado sin romper el historial."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Exercise
from app.schemas.entities import ExerciseIn, ExerciseOut, ExerciseUpdate
from app.services.audit import log_event

router = APIRouter(
    prefix="/api/exercises", tags=["exercises"], dependencies=[Depends(get_current_user)]
)


def _get_or_404(db: Session, exercise_id: int) -> Exercise:
    ex = db.get(Exercise, exercise_id)
    if not ex:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ejercicio no encontrado")
    return ex


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    db: Session = Depends(get_db),
    pattern: str | None = Query(default=None, description="movement_pattern exacto"),
    muscle: str | None = Query(default=None, description="músculo primario"),
    equipment: str | None = Query(default=None, description="requiere este equipamiento"),
    level_max: int | None = Query(default=None, ge=1, le=3, description="nivel mínimo ≤"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/aliases"),
    include_archived: bool = Query(default=False),
) -> list[ExerciseOut]:
    stmt = select(Exercise).order_by(Exercise.muscle_primary, Exercise.canonical_name)
    if not include_archived:
        stmt = stmt.where(Exercise.archived.is_(False))
    if pattern:
        stmt = stmt.where(Exercise.movement_pattern == pattern)
    if muscle:
        stmt = stmt.where(Exercise.muscle_primary == muscle)
    if equipment:
        stmt = stmt.where(Exercise.equipment.any(equipment))
    if level_max:
        stmt = stmt.where(Exercise.level_min <= level_max)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            Exercise.canonical_name.ilike(like) | Exercise.aliases.any(q.strip())
        )
    return [ExerciseOut.model_validate(e) for e in db.scalars(stmt)]


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    return ExerciseOut.model_validate(_get_or_404(db, exercise_id))


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(body: ExerciseIn, db: Session = Depends(get_db)) -> ExerciseOut:
    if db.scalar(select(Exercise).where(Exercise.canonical_name == body.canonical_name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un ejercicio con ese nombre")
    ex = Exercise(**body.model_dump())
    db.add(ex)
    db.flush()
    log_event(db, "exercise", ex.id, "exercise_created", {"name": ex.canonical_name})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.patch("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, body: ExerciseUpdate, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(ex, field, value)
    if changes:
        log_event(db, "exercise", ex.id, "exercise_updated", {"fields": sorted(changes)})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/archive", response_model=ExerciseOut)
def archive_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = True
    log_event(db, "exercise", ex.id, "exercise_archived", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/restore", response_model=ExerciseOut)
def restore_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = False
    log_event(db, "exercise", ex.id, "exercise_restored", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


===== FILE: backend/app/routers/plans.py =====

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


from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
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
    plan = Plan(
        client_id=client_id, month_index=body.month_index, version=version,
        status="draft", nutrition_json=body.nutrition_json,
        training_json=body.training_json, education_json=body.education_json,
        guardrail_flags=body.guardrail_flags, generated_by=body.generated_by,
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
            setattr(plan, field, value)
    log_event(db, "plan", plan.id, "plan_edited", {"fields": list(changes.keys())})
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
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    # Las versiones anteriores del mismo mes quedan supersedidas
    for older in db.scalars(
        select(Plan).where(
            Plan.client_id == plan.client_id, Plan.month_index == plan.month_index,
            Plan.status == "published",
        )
    ):
        older.status = "superseded"

    plan.status = "published"
    is_new_month = plan.month_index > 1
    if client.status == "onboarding":
        client.status = "active"

    log_event(db, "plan", plan.id, "plan_published", {"month_index": plan.month_index})

    # Email de bienvenida / nuevo plan (G.5)
    brand = brand_from_config(db)
    portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
    subject, html = tpl.plan_published(
        brand, client.full_name.split()[0], portal_url, is_new_month
    )
    EmailService(db).send(to=client.email, subject=subject, html=html,
                          kind="plan_published", client=client)

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
    db.add(period)
    db.flush()
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


@router.post("/api/feedback/{doc_id}/send")
def send_feedback(doc_id: int, db: Session = Depends(get_db)) -> dict:
    """Envía el feedback al cliente: lo hace visible en su portal (Progreso),
    avanza el ciclo (review_pending → active, cierra la notificación) y le avisa
    por email. Hasta este punto el feedback es un borrador que solo ve el coach."""
    from datetime import datetime, timezone

    fb = db.get(FeedbackDoc, doc_id)
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback no encontrado")
    fb.sent_at = datetime.now(timezone.utc)

    period = db.get(Period, fb.period_id)
    client = db.get(Client, period.client_id) if period else None
    if client and client.status == "review_pending":
        client.status = "active"  # cerrado el feedback, arranca el siguiente ciclo

    if client:
        log_event(db, "client", client.id, "feedback_sent", {"feedback_id": fb.id})
        # Aviso al cliente (si los emails están activos)
        try:
            brand = brand_from_config(db)
            portal_url = f"{settings.public_base_url}/p/{client.portal_token}"
            subject, html = tpl.feedback_ready(brand, client.full_name.split()[0], portal_url)
            EmailService(db).send(to=client.email, subject=subject, html=html,
                                  kind="feedback_ready", client=client)
        except Exception:
            pass
    db.commit()
    return {"sent": True, "sent_at": fb.sent_at.isoformat()}


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
    """Genera y descarga el documento Word del plan (H.3)."""
    from fastapi import Response

    from app.services.docs.plan_doc import generate_plan_doc

    from app.models import Exercise

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan no encontrado")
    client = db.get(Client, plan.client_id)

    # Nombres reales de ejercicios para las tablas de entrenamiento
    training = plan.training_json or {}
    ex_ids = {
        ex.get("exercise_id")
        for sess in training.get("sessions", [])
        for ex in sess.get("exercises", [])
        if ex.get("exercise_id") is not None
    }
    exercise_names: dict[int, str] = {}
    if ex_ids:
        for ex in db.scalars(select(Exercise).where(Exercise.id.in_(ex_ids))):
            exercise_names[ex.id] = ex.canonical_name

    data = generate_plan_doc(
        brand=_doc_brand(db),
        client_name=client.full_name,
        month_index=plan.month_index,
        goal_type=client.goal_type,
        diet_mode=client.diet_mode,
        nutrition=plan.nutrition_json or {},
        training=training,
        education=plan.education_json or {},
        exercise_names=exercise_names,
        food_allergies=client.food_allergies,
        food_dislikes=client.food_dislikes,
    )
    import unicodedata

    ascii_name = unicodedata.normalize("NFKD", client.full_name).encode("ascii", "ignore").decode()
    safe = "".join(c if c.isalnum() else "_" for c in ascii_name).strip("_").lower() or "cliente"

    # Se entrega como PDF convertido en el servidor (LibreOffice) → idéntico al
    # que se verifica y sin depender del Word del cliente. Fallback a .docx si la
    # conversión fallara, para no romper la descarga.
    from app.services.docs.pdf_convert import docx_bytes_to_pdf

    try:
        pdf = docx_bytes_to_pdf(data)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="plan_{safe}_mes{plan.month_index}.pdf"'},
        )
    except Exception as exc:  # noqa: BLE001 — degradación controlada
        import logging
        logging.getLogger("uvicorn.error").warning("Conversión PDF falló, se entrega .docx: %s", exc)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="plan_{safe}_mes{plan.month_index}.docx"'},
        )


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


===== FILE: backend/app/routers/portal_public.py =====

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
