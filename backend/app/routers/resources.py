"""Recursos del portal (gestión del coach).

Catálogo ÚNICO de productos recomendados (suplementos, material…) que el cliente
ve en la sección "Recursos" del portal, con título, imagen y enlace. La imagen
puede subirse (se guarda en el storage y la sirve la API) o ser una URL externa.

Los vídeos e imágenes de los EJERCICIOS se gestionan por el router de ejercicios
(PATCH /api/exercises/{id} con video_url/image_url); aquí solo van los productos.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, status
from pydantic import BaseModel
from slowapi import Limiter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import RecommendedProduct
from app.ratelimit import client_key
from app.schemas.entities import (
    RecommendedProductIn,
    RecommendedProductOut,
    RecommendedProductUpdate,
)
from app.services.audit import log_event
from app.services.portal import product_image_url
from app.services.storage import (
    PhotoValidationError,
    abs_path,
    delete_storage_file,
    save_resource_image,
)

router = APIRouter(prefix="/api/resources", tags=["resources"])
limiter = Limiter(key_func=client_key)

MAX_IMAGE_BYTES = 5 * 1024 * 1024


# ------------------------------------------- autorrelleno desde la URL ----

class ScrapeIn(BaseModel):
    url: str


@router.post("/products/scrape", dependencies=[Depends(get_current_user)])
@limiter.limit("10/minute")
def scrape_product(request: Request, body: ScrapeIn, db: Session = Depends(get_db)) -> dict:
    """Lee la página del producto y devuelve título, descripción e imagen
    (metadatos OpenGraph) para AUTORRELLENAR el formulario: el coach pega la
    URL y el resto de campos se llenan solos."""
    import ipaddress
    import re as _re
    import socket
    from urllib.parse import urlsplit

    import httpx

    url = (body.url or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "La URL debe empezar por http:// o https://")
    # Guarda SSRF: nunca llamar a hosts internos/privados desde el servidor.
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "URL no permitida")
    except socket.gaierror:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No se pudo resolver la URL")

    try:
        r = httpx.get(url, timeout=8, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; DQRBot/1.0)",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        html = r.text[:400_000]
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            "No se pudo leer la página del producto")

    def meta(*props: str) -> str | None:
        for p in props:
            m = _re.search(
                rf'<meta[^>]+(?:property|name)=["\']{p}["\'][^>]*content=["\']([^"\']+)["\']',
                html, _re.IGNORECASE)
            if not m:  # content antes que property también es válido
                m = _re.search(
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']{p}["\']',
                    html, _re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    title = meta("og:title", "twitter:title")
    if not title:
        m = _re.search(r"<title[^>]*>([^<]+)</title>", html, _re.IGNORECASE)
        title = m.group(1).strip() if m else None
    image = meta("og:image", "og:image:url", "twitter:image")
    description = meta("og:description", "twitter:description", "description")

    def _unescape(s: str | None) -> str | None:
        if not s:
            return s
        import html as _html

        return _html.unescape(s)

    return {
        "title": (_unescape(title) or "")[:160] or None,
        "description": (_unescape(description) or "")[:500] or None,
        "image_url": image if image and image.startswith(("http://", "https://")) else None,
    }


def _out(p: RecommendedProduct) -> RecommendedProductOut:
    return RecommendedProductOut(
        id=p.id,
        title=p.title,
        description=p.description,
        url=p.url,
        category=p.category,
        image_url=product_image_url(p),
        discount_code=p.discount_code,
        has_upload=bool(p.image_path),
        active=p.active,
        sort_order=p.sort_order,
    )


def _get_or_404(db: Session, product_id: int) -> RecommendedProduct:
    p = db.get(RecommendedProduct, product_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return p


@router.get(
    "/products",
    response_model=list[RecommendedProductOut],
    dependencies=[Depends(get_current_user)],
)
def list_products(db: Session = Depends(get_db)) -> list[RecommendedProductOut]:
    """Todos los productos (activos e inactivos), en el orden en que se muestran."""
    rows = db.scalars(
        select(RecommendedProduct).order_by(
            RecommendedProduct.sort_order, RecommendedProduct.id
        )
    ).all()
    return [_out(p) for p in rows]


@router.post(
    "/products",
    response_model=RecommendedProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_product(body: RecommendedProductIn, db: Session = Depends(get_db)) -> RecommendedProductOut:
    # Se añade al final del catálogo (mayor sort_order + 1).
    max_order = db.scalar(select(func.max(RecommendedProduct.sort_order)))
    p = RecommendedProduct(
        title=body.title,
        description=body.description,
        url=body.url,
        category=body.category,
        image_url=body.image_url,
        discount_code=body.discount_code,
        active=body.active,
        sort_order=(max_order or 0) + 1,
    )
    db.add(p)
    db.flush()
    log_event(db, "product", p.id, "product_created", {"title": p.title})
    db.commit()
    db.refresh(p)
    return _out(p)


@router.patch(
    "/products/{product_id}",
    response_model=RecommendedProductOut,
    dependencies=[Depends(get_current_user)],
)
def update_product(
    product_id: int, body: RecommendedProductUpdate, db: Session = Depends(get_db)
) -> RecommendedProductOut:
    p = _get_or_404(db, product_id)
    changes = body.model_dump(exclude_unset=True)
    # PATCH: un null EXPLÍCITO no puede vaciar un campo obligatorio (rompería el
    # NOT NULL con un 500); en esos campos null = "sin cambio".
    NOT_NULLABLE = {"title", "url", "category", "active", "sort_order"}
    changes = {k: v for k, v in changes.items() if not (v is None and k in NOT_NULLABLE)}
    for field, value in changes.items():
        setattr(p, field, value)
    if changes:
        log_event(db, "product", p.id, "product_updated", {"fields": sorted(changes)})
    db.commit()
    db.refresh(p)
    return _out(p)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)],
)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Response:
    p = _get_or_404(db, product_id)
    old_image = p.image_path
    db.delete(p)
    log_event(db, "product", product_id, "product_deleted", None)
    db.commit()
    # El archivo se borra DESPUÉS del commit: si el commit fallara, la fila
    # seguiría existiendo y no puede quedarse apuntando a una imagen ya borrada.
    delete_storage_file(old_image)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/products/{product_id}/image",
    response_model=RecommendedProductOut,
    dependencies=[Depends(get_current_user)],
)
def upload_product_image(
    product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> RecommendedProductOut:
    """Sube (o reemplaza) la imagen del producto. La imagen subida tiene prioridad
    sobre la URL externa al mostrarse en el portal."""
    p = _get_or_404(db, product_id)
    # Lectura ACOTADA: no bufferizar cuerpos enormes en memoria antes de validar
    # el tamaño (un byte de más ya delata que supera el límite).
    raw = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La imagen supera 5 MB")
    try:
        new_rel = save_resource_image(raw, file.filename or "producto")
    except PhotoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    old_rel = p.image_path
    p.image_path = new_rel
    log_event(db, "product", p.id, "product_image_uploaded", None)
    db.commit()
    # La imagen anterior se borra tras el commit: si este fallara, la fila
    # conservaría la ruta antigua y el archivo debe seguir existiendo.
    if old_rel and old_rel != new_rel:
        delete_storage_file(old_rel)
    db.refresh(p)
    return _out(p)


@router.delete(
    "/products/{product_id}/image",
    response_model=RecommendedProductOut,
    dependencies=[Depends(get_current_user)],
)
def delete_product_image(product_id: int, db: Session = Depends(get_db)) -> RecommendedProductOut:
    """Quita la imagen subida (vuelve a usarse la URL externa si la hay)."""
    p = _get_or_404(db, product_id)
    if p.image_path:
        old_rel = p.image_path
        p.image_path = None
        log_event(db, "product", p.id, "product_image_removed", None)
        db.commit()
        delete_storage_file(old_rel)  # tras el commit (ver delete_product)
        db.refresh(p)
    return _out(p)


@router.get("/products/{product_id}/image")
@limiter.limit("240/minute")
def get_product_image(request: Request, product_id: int, db: Session = Depends(get_db)) -> Response:
    """Sirve la imagen subida del producto. PÚBLICA (no es dato sensible: es la
    misma miniatura que se muestra en el portal del cliente, sin login del coach).
    Solo productos ACTIVOS, igual que el portal: un producto oculto no expone su
    imagen a través de una URL adivinable."""
    p = db.get(RecommendedProduct, product_id)
    if not p or not p.active or not p.image_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    path = abs_path(p.image_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado")
    ext = path.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
             ".webp": "image/webp"}.get(ext, "application/octet-stream")
    return Response(
        content=path.read_bytes(),
        media_type=media,
        headers={"Cache-Control": "public, max-age=86400",
                 "Content-Disposition": f'inline; filename="producto_{product_id}{ext}"'},
    )
