"""CRUD de clientes + links de portal + RGPD (supresión y portabilidad)."""


import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, or_, select, update
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
    return [ClientOut.model_validate(c) for c in db.scalars(stmt)]


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
    try:
        rel = save_document(client_id, file.file.read(), file.filename or "anamnesis.pdf")
    except DocumentValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "client", client_id, "document_uploaded", {"path": rel})
    db.commit()
    name = rel.rsplit("/", 1)[-1]
    return {"name": name, "rel_path": rel}


@router.get("/{client_id}/documents")
def get_client_documents(client_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Lista los documentos subidos del cliente."""
    _client_or_404_docs(db, client_id)
    return list_documents(client_id)


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
