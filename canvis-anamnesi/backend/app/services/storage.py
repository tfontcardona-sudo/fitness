"""Almacenamiento de archivos (PARTE I).

Estructura: {STORAGE_PATH}/clients/{id}/photos|documents|uploads/ y /brand/.
Fotos: validación de formato/tamaño y eliminación de EXIF (la geolocalización
de una foto corporal es dato sensible — se re-codifica la imagen sin metadatos).
"""

from __future__ import annotations

import io
import secrets
import shutil
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import settings

MAX_PHOTO_MB = 10
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def storage_root() -> Path:
    root = Path(settings.storage_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def brand_dir() -> Path:
    p = storage_root() / "brand"
    p.mkdir(parents=True, exist_ok=True)
    return p


def client_dir(client_id: int, sub: str | None = None) -> Path:
    p = storage_root() / "clients" / str(client_id)
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


class PhotoValidationError(ValueError):
    """Formato no soportado, archivo corrupto o demasiado grande."""


def save_photo(client_id: int, raw: bytes, sub: str = "photos") -> str:
    """Valida, elimina EXIF re-codificando y guarda. Devuelve la ruta relativa."""
    if len(raw) > MAX_PHOTO_MB * 1024 * 1024:
        raise PhotoValidationError(f"La foto supera {MAX_PHOTO_MB} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")

    fmt = img.format
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))  # píxeles sí, metadatos no
    if fmt == "JPEG" and clean.mode not in ("RGB", "L"):
        clean = clean.convert("RGB")

    name = f"{secrets.token_hex(12)}.{_EXT[fmt]}"
    dest = client_dir(client_id, sub) / name
    params = {"quality": 92} if fmt == "JPEG" else {}
    clean.save(dest, format=fmt, **params)
    return str(dest.relative_to(storage_root()))


MAX_DOC_MB = 25
_DOC_EXT = {"application/pdf": "pdf"}


class DocumentValidationError(ValueError):
    """Documento no soportado o demasiado grande."""


def save_document(client_id: int, raw: bytes, original_name: str) -> str:
    """Guarda un documento (PDF) del cliente. Devuelve la ruta relativa.

    Conserva un nombre legible (saneado) para que el coach lo reconozca, con un
    sufijo aleatorio que evita colisiones. Solo acepta PDF (la anamnesis oficial).
    """
    if len(raw) > MAX_DOC_MB * 1024 * 1024:
        raise DocumentValidationError(f"El documento supera {MAX_DOC_MB} MB")
    if raw[:5] != b"%PDF-":
        raise DocumentValidationError("El archivo no es un PDF válido")

    import re

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", (original_name or "documento").rsplit(".", 1)[0])[:60]
    stem = stem.strip("_") or "documento"
    name = f"{stem}_{secrets.token_hex(4)}.pdf"
    dest = client_dir(client_id, "documents") / name
    dest.write_bytes(raw)
    return str(dest.relative_to(storage_root()))


def list_documents(client_id: int) -> list[dict]:
    """Lista los documentos subidos de un cliente (más reciente primero)."""
    folder = storage_root() / "clients" / str(client_id) / "documents"
    if not folder.exists():
        return []
    items = []
    for f in folder.iterdir():
        if f.is_file():
            st = f.stat()
            items.append({
                "name": f.name,
                "size_kb": round(st.st_size / 1024),
                "uploaded_at": st.st_mtime,
                "rel_path": str(f.relative_to(storage_root())),
            })
    return sorted(items, key=lambda x: x["uploaded_at"], reverse=True)


def save_brand_logo(raw: bytes, filename_hint: str) -> str:
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError("El logo supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")
    dest = brand_dir() / f"logo.{_EXT[img.format]}"
    img.save(dest, format=img.format)
    return str(dest.relative_to(storage_root()))


def abs_path(rel: str) -> Path:
    """Ruta absoluta segura dentro del storage (evita path traversal)."""
    p = (storage_root() / rel).resolve()
    if not str(p).startswith(str(storage_root().resolve())):
        raise PhotoValidationError("Ruta fuera del almacenamiento")
    return p


def delete_client_tree(client_id: int) -> None:
    """Supresión RGPD: borra todos los archivos del cliente."""
    p = storage_root() / "clients" / str(client_id)
    if p.exists():
        shutil.rmtree(p)
