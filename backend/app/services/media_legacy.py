"""Rescate de las imágenes de marca que quedaron en un sitio no servible.

Antes, el logo (y la foto de enlaces, la portada de vídeo y la foto de /planes)
se guardaban bajo `storage/brand/`. Caddy solo proxya `/api/*`, así que esa
carpeta NO se puede servir en producción: la imagen estaba subida y no se veía
en ninguna parte. Ahora todo lo público vive bajo `storage/media/` (montado en
`/api/media`).

Esto lo arregla SOLO al arrancar: mueve lo que quedó en la ruta vieja y deja la
ficha de marca apuntando a la nueva. Sin esto, el dueño tendría que volver a
subir cada imagen a mano — y este sistema no le pide clics que puede dar él.

Idempotente y best-effort: si algo falla, se anota y la aplicación arranca
igual (una imagen sin migrar es exactamente lo que ya pasaba antes).
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandConfig
from app.services.storage import _slug, media_dir, storage_root

log = logging.getLogger("app.media")

# Columna de la ficha de marca → prefijo del nombre de fichero destino.
_IMAGENES: tuple[tuple[str, str], ...] = (
    ("logo_path", "logo"),
    ("links_photo_path", "links-photo"),
    ("video_cover_path", "video-cover"),
    ("plans_photo_path", "plans-photo"),
)


def migrar_imagenes_de_marca(db: Session) -> int:
    """Lleva a `media/` las imágenes de marca que sigan en la ruta vieja.

    Devuelve cuántas se han rescatado (0 en el caso normal, que es que ya estén
    todas en su sitio)."""
    rescatadas = 0
    try:
        marcas = list(db.scalars(select(BrandConfig)))
    except Exception:  # noqa: BLE001 — sin tabla todavía (base recién creada)
        return 0
    root = storage_root()
    destino = media_dir("brand")
    for marca in marcas:
        slug = _slug(getattr(marca, "slug", None) or "dqr")
        for columna, prefijo in _IMAGENES:
            rel = getattr(marca, columna, None)
            if not rel or str(rel).startswith("media/"):
                continue  # vacío o ya servible
            origen = root / str(rel)
            if not origen.is_file():
                # El fichero ya no está: la ruta apunta a un hueco. Se limpia
                # para que la web no pida una imagen que nunca va a llegar.
                setattr(marca, columna, None)
                rescatadas += 1
                continue
            ext = origen.suffix.lower().lstrip(".") or "png"
            nuevo = destino / f"{prefijo}-{slug}.{ext}"
            try:
                for viejo in destino.glob(f"{prefijo}-{slug}.*"):
                    if viejo != nuevo:
                        viejo.unlink(missing_ok=True)
                nuevo.write_bytes(origen.read_bytes())
                origen.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                log.warning("No se pudo rescatar %s de la marca %s", columna, slug)
                continue
            setattr(marca, columna, str(nuevo.relative_to(root)))
            rescatadas += 1
    if rescatadas:
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            return 0
        log.info("Imágenes de marca rescatadas a media/: %s", rescatadas)
        try:
            from app.services import branding

            branding.invalidar()
        except Exception:  # noqa: BLE001
            pass
    return rescatadas
