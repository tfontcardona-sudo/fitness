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


# Tope de PÍXELES de una foto de progreso (~50 MP: por encima de cualquier móvil
# actual). Corta las "bombas" (pequeñas comprimidas, enormes decodificadas) ANTES
# de decodificar — este endpoint es alcanzable desde el PORTAL del cliente.
MAX_PHOTO_PIXELS = 50_000_000


def save_photo(client_id: int, raw: bytes, sub: str = "photos") -> str:
    """Valida, elimina metadatos re-codificando y guarda. Devuelve la ruta relativa."""
    if len(raw) > MAX_PHOTO_MB * 1024 * 1024:
        raise PhotoValidationError(f"La foto supera {MAX_PHOTO_MB} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        # Rechazo por DIMENSIONES antes de decodificar (Image.open solo lee la
        # cabecera): una imagen de <15 MB comprimidos pero cientos de MP ya no
        # infla la memoria del worker.
        if img.width * img.height > MAX_PHOTO_PIXELS:
            raise PhotoValidationError("La foto es demasiado grande (usa una de menos resolución)")
        img.load()
    except PhotoValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise PhotoValidationError("La foto es demasiado grande") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")

    fmt = img.format
    # convert() en C (sin listas de píxeles en Python) y resuelve la PALETA de los
    # PNG modo "P" — el rebuild por putdata copiaba índices sin paleta (salían
    # corruptos). Mismo criterio que save_resource_image.
    clean = img.convert("RGB") if fmt == "JPEG" else img.convert("RGBA")

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
    """Lista la anamnesis subida del cliente (solo el PDF, más reciente primero).

    Se excluyen los archivos internos (sidecar `_anamnesis_analysis.json` y
    cualquier `_*`) y todo lo que no sea PDF: la web solo debe mostrar la
    anamnesis, y solo hay una por cliente (cada subida reemplaza la anterior).
    """
    folder = storage_root() / "clients" / str(client_id) / "documents"
    if not folder.exists():
        return []
    items = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf" and not f.name.startswith("_"):
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


# --------------------------------------------------------------- media ----
# Archivos PÚBLICOS (foto de la landing, portada y vídeos de ejercicios).
# Viven bajo storage/media y se sirven montados en /api/media (StaticFiles):
# Caddy solo proxyea /api/* al backend, así que /storage/... NO llega en
# producción — todo lo público debe colgar de aquí.

def media_dir(sub: str = "") -> Path:
    p = storage_root() / "media" / sub if sub else storage_root() / "media"
    p.mkdir(parents=True, exist_ok=True)
    return p


# Tope de PÍXELES de una imagen pública (logo, fondos de las páginas): 25 MP
# sobra para cualquier foto de móvil y corta las "bombas" de descompresión.
MAX_PUBLIC_IMAGE_PIXELS = 25_000_000


def _save_public_image(raw: bytes, dest_dir: Path, stem: str, what: str) -> str:
    """Valida una imagen (≤5 MB, ≤25 MP, JPG/PNG/WebP) y la guarda con nombre
    fijo (reemplaza la anterior aunque cambie la extensión). Se re-codifica para
    quitar los metadatos (EXIF con geolocalización, etc.)."""
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError(f"{what} supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        # Rechazo por DIMENSIONES antes de decodificar: Image.open solo lee la
        # cabecera, así que una 'bomba' (pequeña comprimida, enorme en píxeles)
        # se corta aquí sin llegar a ocupar memoria.
        if img.width * img.height > MAX_PUBLIC_IMAGE_PIXELS:
            raise PhotoValidationError(f"{what} es demasiado grande (usa menos resolución)")
        img.load()
    except PhotoValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise PhotoValidationError(f"{what} es demasiado grande") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")
    fmt = img.format
    # convert() re-codifica en C (sin listas de píxeles en memoria) y resuelve la
    # PALETA de los PNG modo "P", que copiada por índices salía negra/corrupta.
    clean = img.convert("RGB") if fmt == "JPEG" else img.convert("RGBA")
    for stale in dest_dir.glob(f"{stem}.*"):
        try:
            stale.unlink()
        except Exception:
            pass
    dest = dest_dir / f"{stem}.{_EXT[fmt]}"
    clean.save(dest, format=fmt, **({"quality": 88} if fmt == "JPEG" else {}))
    return str(dest.relative_to(storage_root()))


def save_links_photo(raw: bytes, filename_hint: str) -> str:
    """Foto de fondo de la página pública de enlaces (/professional)."""
    return _save_public_image(raw, media_dir("brand"), "links-photo", "La foto")


def save_plans_photo(raw: bytes, filename_hint: str) -> str:
    """Foto de fondo de la página pública de planes (/planes)."""
    return _save_public_image(raw, media_dir("brand"), "plans-photo", "La foto")


def media_url(rel_path: str | None) -> str | None:
    """URL pública de un archivo bajo media/ (None si no aplica).

    RELATIVA a propósito. El portal, la landing y la PWA se sirven del MISMO
    origen que la API (Caddy proxya /api), así que "/api/media/…" funciona
    siempre: aunque DOMAIN/BASE_URL estén sin poner o mal puestos, o el cliente
    entre por otro nombre de host. Con URL absoluta, un `.env` incompleto dejaba
    las imágenes subidas sin cargar. Mismo criterio que el frontend
    (api.mediaUrl). Solo se usa en respuestas que
    pinta el navegador; los emails y documentos construyen sus URLs aparte.
    """
    if not rel_path or not rel_path.startswith("media/"):
        return None
    return f"/api/media/{rel_path[len('media/'):]}"


def delete_storage_file(rel: str | None) -> None:
    """Borra un archivo del storage por su ruta relativa (silencioso si falta).
    Se usa al reemplazar/borrar la imagen de un producto para no acumular huérfanos."""
    if not rel:
        return
    try:
        p = abs_path(rel)
        if p.is_file():
            p.unlink()
    except (PhotoValidationError, OSError):
        pass


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
