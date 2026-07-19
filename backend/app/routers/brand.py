"""Configuración de marca (H.1) — única fila, aplica a app/portal/docs/emails."""


from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import BrandConfig
from app.schemas.entities import BrandConfigIn, BrandConfigOut
from app.services.audit import log_event
from app.services.storage import (
    PhotoValidationError,
    save_brand_logo,
    save_links_photo,
    save_plans_photo,
    save_video_cover,
)

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


@router.post("/links-photo", response_model=BrandConfigOut)
def upload_links_photo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Foto de fondo de la página pública de enlaces (/dq, link de Instagram)."""
    brand = _brand(db)
    try:
        brand.links_photo_path = save_links_photo(file.file.read(), file.filename or "foto")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_links_photo_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)


@router.post("/plans-photo", response_model=BrandConfigOut)
def upload_plans_photo(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Foto de fondo de la página pública de planes (/planes)."""
    brand = _brand(db)
    try:
        brand.plans_photo_path = save_plans_photo(file.file.read(), file.filename or "foto")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_plans_photo_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)


@router.post("/video-cover", response_model=BrandConfigOut)
def upload_video_cover(file: UploadFile = File(...), db: Session = Depends(get_db)) -> BrandConfigOut:
    """Portada ÚNICA de todos los vídeos de ejercicios (portal y rutina)."""
    brand = _brand(db)
    try:
        brand.video_cover_path = save_video_cover(file.file.read(), file.filename or "portada")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "brand", brand.id, "brand_video_cover_updated", None)
    db.commit()
    db.refresh(brand)
    return BrandConfigOut.model_validate(brand)
