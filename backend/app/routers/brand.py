"""La MARCA del sistema: identidad, catálogo y tarifas de cada negocio.

`brand_config` dejó de ser una fila (mig. 0044): hay un PERFIL por marca y uno
está ACTIVO. El switch (`POST /api/brand/{id}/activar`) te mete dentro de la
otra marca: a partir de ahí, el panel, la landing, la página de planes y las
altas nuevas son suyas, y todo lo que edites aquí es suyo también.

Lo que NO cambia al pulsar el switch: los clientes que ya existen. Cada uno
lleva sellada su marca (`clients.brand_id`) y su portal, sus documentos y sus
precios de renovación siguen siendo los de la marca con la que entró.
"""


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import BrandConfig
from app.schemas.entities import BrandConfigIn, BrandConfigOut, BrandProfileOut
from app.services.audit import log_event
from app.services.branding import invalidar as invalidar_marca
from app.services.storage import (
    PhotoValidationError,
    save_brand_logo,
    save_links_photo,
    save_plans_photo,
    save_video_cover,
)

router = APIRouter(prefix="/api/brand", tags=["brand"], dependencies=[Depends(get_current_user)])


def _brand(db: Session) -> BrandConfig:
    """El perfil ACTIVO. Con varias marcas, un `limit(1)` sin orden devolvía
    una cualquiera: el coach editaba a ciegas la marca equivocada."""
    brand = db.scalar(select(BrandConfig).where(BrandConfig.activa.is_(True)).limit(1))
    if brand is None:  # base antigua o sin activa: la primera, y se marca
        brand = db.scalar(select(BrandConfig).order_by(BrandConfig.id).limit(1))
    if brand is None:  # el seed la crea; defensa por si se vació la tabla
        brand = BrandConfig(slug="dqr", activa=True)
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


@router.get("/perfiles", response_model=list[BrandProfileOut])
def list_profiles(db: Session = Depends(get_db)) -> list[BrandProfileOut]:
    """Las marcas que hay y cuál está activa (el selector del switch)."""
    filas = db.scalars(select(BrandConfig).order_by(BrandConfig.id)).all()
    return [BrandProfileOut.model_validate(f) for f in filas]


@router.post("/{brand_id}/activar", response_model=BrandConfigOut)
def activate_profile(brand_id: int, db: Session = Depends(get_db)) -> BrandConfigOut:
    """EL SWITCH: cambia el escaparate a otra marca.

    Cambia el panel, la landing, la página de planes, las tarifas que se cobran
    y la marca con la que nacen las altas nuevas. NO toca a los clientes que ya
    existen: cada uno conserva la suya."""
    nueva = db.get(BrandConfig, brand_id)
    if nueva is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marca no encontrada")
    if nueva.activa:
        return BrandConfigOut.model_validate(nueva)
    # UNA sola activa: se apagan todas antes de encender esta (la base lo exige
    # con un índice único, así que el orden importa).
    db.execute(update(BrandConfig).values(activa=False))
    db.flush()
    nueva.activa = True
    log_event(db, "brand", nueva.id, "brand_activated", {"slug": nueva.slug, "name": nueva.name})
    db.commit()
    db.refresh(nueva)
    invalidar_marca()
    return BrandConfigOut.model_validate(nueva)


@router.get("", response_model=BrandConfigOut)
def get_brand(db: Session = Depends(get_db)) -> BrandConfigOut:
    return BrandConfigOut.model_validate(_brand(db))


@router.put("", response_model=BrandConfigOut)
def update_brand(body: BrandConfigIn, db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    # `exclude_unset`: solo se escribe lo que el panel MANDA. Con el volcado
    # completo, cualquier pantalla que enviara el formulario de siempre borraba
    # los campos que no conoce — al añadir la dirección del centro, guardar los
    # colores desde el panel la dejaba en blanco. Mismo criterio que el upsert
    # parcial del diario del portal (gotcha §5.11). Para vaciar un campo a
    # propósito hay que mandarlo explícitamente a null, que es lo que hace el
    # formulario cuando el coach lo borra.
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    log_event(db, "brand", brand.id, "brand_updated", None)
    db.commit()
    db.refresh(brand)
    invalidar_marca()
    return BrandConfigOut.model_validate(brand)


@router.post("/logo", response_model=BrandConfigOut)
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    brand = _brand(db)
    try:
        brand.logo_path = save_brand_logo(file.file.read(), file.filename or "logo", brand.slug)
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_logo_updated", None)
    db.commit()
    db.refresh(brand)
    invalidar_marca()
    return BrandConfigOut.model_validate(brand)


@router.post("/links-photo", response_model=BrandConfigOut)
def upload_links_photo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Foto de fondo de la página pública de enlaces (/dq, link de Instagram)."""
    brand = _brand(db)
    try:
        brand.links_photo_path = save_links_photo(file.file.read(), file.filename or "foto", brand.slug)
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_links_photo_updated", None)
    db.commit()
    db.refresh(brand)
    invalidar_marca()
    return BrandConfigOut.model_validate(brand)


@router.post("/plans-photo", response_model=BrandConfigOut)
def upload_plans_photo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Foto de fondo de la página pública de planes (/planes)."""
    brand = _brand(db)
    try:
        brand.plans_photo_path = save_plans_photo(file.file.read(), file.filename or "foto", brand.slug)
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_plans_photo_updated", None)
    db.commit()
    db.refresh(brand)
    invalidar_marca()
    return BrandConfigOut.model_validate(brand)


@router.post("/video-cover", response_model=BrandConfigOut)
def upload_video_cover(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Portada ÚNICA de todos los vídeos de ejercicios (portal y rutina)."""
    brand = _brand(db)
    try:
        brand.video_cover_path = save_video_cover(file.file.read(), file.filename or "portada", brand.slug)
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_video_cover_updated", None)
    db.commit()
    db.refresh(brand)
    invalidar_marca()
    return BrandConfigOut.model_validate(brand)
