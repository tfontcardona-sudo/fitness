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


# Extensiones con las que se GUARDA un documento del cliente y su tipo MIME
# para servirlo. Antes solo PDF: el lector universal acepta también Word,
# fotos, hojas y texto, y cada uno se guarda con su extensión real.
DOC_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword", "odt": "application/vnd.oasis.opendocument.text",
    "rtf": "application/rtf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp", "gif": "image/gif",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    "csv": "text/csv", "tsv": "text/tab-separated-values", "txt": "text/plain",
    "md": "text/markdown", "json": "application/json", "log": "text/plain",
}


def media_type_for(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return DOC_MEDIA_TYPES.get(ext, "application/octet-stream")


def save_document(client_id: int, raw: bytes, original_name: str,
                  *, ext: str | None = None) -> str:
    """Guarda un documento del cliente y devuelve la ruta relativa.

    Conserva un nombre legible (saneado) para que el coach lo reconozca, con un
    sufijo aleatorio que evita colisiones. Acepta CUALQUIER formato que el
    lector universal sepa leer (PDF, Word, foto, hoja, texto): la extensión
    se decide por la MAGIA del fichero (`detectar_tipo`), no por el nombre —
    salvo que quien llama ya la conozca (`ext`, p. ej. las fotos normalizadas
    a JPEG o unidas en un PDF).
    """
    if len(raw) > MAX_DOC_MB * 1024 * 1024:
        raise DocumentValidationError(f"El documento supera {MAX_DOC_MB} MB")
    if not raw:
        raise DocumentValidationError("El archivo está vacío")
    if ext is None:
        from app.services.document_reader import ACCEPTED_HUMAN, detectar_tipo

        familia, ext_det = detectar_tipo(raw, original_name)
        if familia == "heic":
            raise DocumentValidationError(
                "Las fotos HEIC del iPhone no se pueden leer: envíala como JPG "
                "(Ajustes → Cámara → Formatos → «Más compatible»).")
        if familia == "desconocido":
            raise DocumentValidationError(
                f"No reconozco el formato del archivo. Se admite {ACCEPTED_HUMAN}.")
        ext = ext_det
    ext = (ext or "pdf").lower().lstrip(".")
    if ext not in DOC_MEDIA_TYPES:
        raise DocumentValidationError(f"Formato .{ext} no admitido")

    import re

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", (original_name or "documento").rsplit(".", 1)[0])[:60]
    stem = stem.strip("_") or "documento"
    name = f"{stem}_{secrets.token_hex(4)}.{ext}"
    dest = client_dir(client_id, "documents") / name
    dest.write_bytes(raw)
    return str(dest.relative_to(storage_root()))


def list_documents(client_id: int) -> list[dict]:
    """Lista los documentos subidos del cliente (más reciente primero): la
    anamnesis (una sola: cada subida reemplaza la anterior) y los adjuntos.

    Se excluyen los archivos internos (sidecars `_*.json`) y el justificante
    RGPD. Desde el lector universal se listan TODOS los formatos admitidos
    (PDF, Word, foto, hoja, texto), cada uno con su `format`.
    """
    folder = storage_root() / "clients" / str(client_id) / "documents"
    if not folder.exists():
        return []
    items: list[dict] = []
    for f in folder.iterdir():
        # El consentimiento RGPD del formulario digital también vive aquí como
        # PDF: NO es la anamnesis y no puede colarse como tal (apagaría el
        # banner del portal y la IA intentaría "leerlo" como cuestionario).
        if f.name == "consentimiento_rgpd.pdf":
            continue
        ext = f.suffix.lower().lstrip(".")
        if f.is_file() and ext in DOC_MEDIA_TYPES and not f.name.startswith("_"):
            st = f.stat()
            items.append({
                "name": f.name,
                # anamnesis | adjunto (analítica, informe médico): sin esto la
                # web daba la anamnesis por recibida al subir una analítica, y
                # "Ver PDF" abría el informe de sangre en vez del cuestionario.
                "kind": "adjunto" if f.name.startswith("adjunto_") else "anamnesis",
                "format": ext,
                "size_kb": round(st.st_size / 1024),
                "uploaded_at": st.st_mtime,
                "rel_path": str(f.relative_to(storage_root())),
            })
    return sorted(items, key=lambda x: x["uploaded_at"], reverse=True)


def anamnesis_documents(client_id: int) -> list[dict]:
    """Solo la ANAMNESIS del cliente: excluye los adjuntos (`adjunto_…` —
    analítica, informes médicos). Es lo que deben mirar los flujos de
    «anamnesis recibida» y la lectura con IA; sin este filtro, subir una
    analítica contaba como anamnesis y la IA leía el informe de sangre como
    si fuera el cuestionario (auditoría 27-08)."""
    return [d for d in list_documents(client_id)
            if not d["name"].startswith("adjunto_")]


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


def _save_public_image(raw: bytes, dest_dir: Path, stem: str, what: str) -> str:
    """Valida una imagen (≤5 MB, JPG/PNG/WebP) y la guarda con nombre fijo
    (reemplaza la anterior aunque cambie la extensión)."""
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError(f"{what} supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")
    for old in dest_dir.glob(f"{stem}.*"):
        try:
            old.unlink()
        except Exception:
            pass
    dest = dest_dir / f"{stem}.{_EXT[img.format]}"
    img.save(dest, format=img.format)
    return str(dest.relative_to(storage_root()))


def save_links_photo(raw: bytes, filename_hint: str) -> str:
    """Foto de fondo de la página pública de enlaces (/dq)."""
    return _save_public_image(raw, media_dir("brand"), "links-photo", "La foto")


def save_video_cover(raw: bytes, filename_hint: str) -> str:
    """Portada ÚNICA para todos los vídeos de ejercicios."""
    return _save_public_image(raw, media_dir("brand"), "video-cover", "La portada")


def save_plans_photo(raw: bytes, filename_hint: str) -> str:
    """Foto de fondo de la página pública de planes (/planes)."""
    return _save_public_image(raw, media_dir("brand"), "plans-photo", "La foto")


MAX_VIDEO_MB = 300
# Formatos de vídeo habituales; el navegador reproduce mp4/webm/mov nativamente.
_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".wmv", ".3gp"}


class VideoValidationError(ValueError):
    """Vídeo no soportado o demasiado grande."""


def save_exercise_video(exercise_id: int, fileobj, original_name: str) -> str:
    """Guarda el vídeo SUBIDO de un ejercicio (reemplaza el anterior). Escribe a
    disco en trozos (los vídeos no caben cómodos en RAM). Devuelve la ruta
    relativa al storage (media/exercises/…)."""
    import shutil

    ext = ("." + original_name.rsplit(".", 1)[-1].lower()) if "." in (original_name or "") else ""
    if ext not in _VIDEO_EXTS:
        raise VideoValidationError(
            "Formato de vídeo no soportado (usa MP4, MOV, WebM, AVI, MKV…)")
    folder = media_dir("exercises")
    for old in folder.glob(f"ex{exercise_id}_*"):
        try:
            old.unlink()
        except Exception:
            pass
    dest = folder / f"ex{exercise_id}_{secrets.token_hex(4)}{ext}"
    written = 0
    limit = MAX_VIDEO_MB * 1024 * 1024
    with dest.open("wb") as out:
        while True:
            chunk = fileobj.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise VideoValidationError(f"El vídeo supera {MAX_VIDEO_MB} MB")
            out.write(chunk)
    if written == 0:
        dest.unlink(missing_ok=True)
        raise VideoValidationError("El archivo está vacío")
    return str(dest.relative_to(storage_root()))


def delete_exercise_video(exercise_id: int) -> None:
    for old in media_dir("exercises").glob(f"ex{exercise_id}_*"):
        try:
            old.unlink()
        except Exception:
            pass


def media_url(rel_path: str | None) -> str | None:
    """URL pública de un archivo bajo media/ (None si no aplica).

    RELATIVA a propósito. El portal, la landing y la PWA se sirven del MISMO
    origen que la API (Caddy proxya /api), así que "/api/media/…" funciona
    siempre: aunque DOMAIN/BASE_URL estén sin poner o mal puestos, o el cliente
    entre por otro nombre de host. Con URL absoluta, un `.env` incompleto dejaba
    los vídeos e imágenes subidos sin cargar (y el botón de vídeo sin salir).
    Mismo criterio que el frontend (api.mediaUrl). Solo se usa en respuestas que
    pinta el navegador; los emails y documentos construyen sus URLs aparte.
    """
    if not rel_path or not rel_path.startswith("media/"):
        return None
    return f"/api/media/{rel_path[len('media/'):]}"


def resources_dir() -> Path:
    p = storage_root() / "resources"
    p.mkdir(parents=True, exist_ok=True)
    return p


# Tope de PÍXELES de una imagen de producto (~25 MP): por debajo del umbral de la
# DecompressionBombError de Pillow (~89-178 MP), que dejaba pasar imágenes de
# <5 MB comprimidos pero cientos de MB descomprimidos.
MAX_RESOURCE_IMAGE_PIXELS = 25_000_000


def save_resource_image(raw: bytes, filename_hint: str = "") -> str:
    """Valida y guarda la imagen de un producto recomendado, quitando metadatos al
    re-codificar. Devuelve la ruta relativa. Nombre aleatorio único: cada subida
    crea un archivo nuevo (la anterior se borra aparte para no dejar huérfanos)."""
    if len(raw) > 5 * 1024 * 1024:
        raise PhotoValidationError("La imagen supera 5 MB")
    try:
        img = Image.open(io.BytesIO(raw))
        # Rechazo por DIMENSIONES antes de decodificar: Image.open solo lee la
        # cabecera, así que una 'bomba' (pequeña comprimida, enorme en píxeles)
        # se corta aquí sin llegar a ocupar memoria.
        if img.width * img.height > MAX_RESOURCE_IMAGE_PIXELS:
            raise PhotoValidationError("La imagen es demasiado grande (usa una de menos resolución)")
        img.load()
    except PhotoValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise PhotoValidationError("La imagen es demasiado grande") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise PhotoValidationError("El archivo no es una imagen válida") from exc
    if img.format not in ALLOWED_FORMATS:
        raise PhotoValidationError("Formato no soportado (usa JPG, PNG o WebP)")

    fmt = img.format
    # Re-codificación SIN metadatos con convert() (en C, sin listas de píxeles en
    # memoria): resuelve además la PALETA de los PNG modo "P" — el rebuild por
    # putdata copiaba los índices sin la paleta y la imagen salía corrupta/negra.
    clean = img.convert("RGB") if fmt == "JPEG" else img.convert("RGBA")

    name = f"{secrets.token_hex(12)}.{_EXT[fmt]}"
    dest = resources_dir() / name
    params = {"quality": 88} if fmt == "JPEG" else {}
    clean.save(dest, format=fmt, **params)
    return str(dest.relative_to(storage_root()))


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
