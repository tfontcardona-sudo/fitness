"""Página pública de enlaces (Instagram) y registro self-serve.

- GET  /api/public/landing   → marca + foto de fondo + afiliación (tienda ESN y
                               código de descuento) para la landing /dq.
- POST /api/public/register  → registro personal ANTES del pago: el cliente deja
                               nombre/email/teléfono en /planes; se crea su ficha
                               (pago pendiente), se le envía el email de arranque
                               (pago + anamnesis PDF) y se devuelve la URL de
                               Stripe de su plan × duración para ir directo a pagar.

El webhook de Stripe (stripe_router) marcará el pago; la anamnesis se sube en la
página pública /anamnesis/{token} (portal_public) y se ingiere sola.

OJO: sin `from __future__ import annotations` — con el decorador del rate-limiter
las anotaciones-string no se resuelven y FastAPI trataría el body como query.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import BrandConfig, Client, RecommendedProduct
from app.ratelimit import client_key
from app.schemas.entities import LandingOut, LandingProductOut, PublicRegisterIn
from app.security import new_portal_token
from app.services.audit import log_event
from app.services.onboarding import send_onboarding_email
from app.services.portal import product_image_url
from app.services.storage import media_url
from app.services.stripe_service import StripeError, create_checkout_url, get_plan_prices

router = APIRouter(prefix="/api/public", tags=["public-site"])
limiter = Limiter(key_func=client_key)
_log = logging.getLogger("app.public")


@router.get("/landing", response_model=LandingOut)
@limiter.limit("60/minute")
def public_landing(request: Request, db: Session = Depends(get_db)) -> LandingOut:
    """Datos públicos de la página de enlaces (/dq): marca, foto, afiliación y
    catálogo de productos (comprables con el código único del coach)."""
    brand = db.scalar(select(BrandConfig).limit(1))
    if brand is None:  # BD recién creada sin seed: valores por defecto
        brand = BrandConfig()
    products = db.scalars(
        select(RecommendedProduct)
        .where(RecommendedProduct.active.is_(True))
        .order_by(RecommendedProduct.sort_order, RecommendedProduct.id)
    ).all()
    return LandingOut(
        name=brand.name,
        tagline=brand.tagline,
        color_primary=brand.color_primary,
        color_secondary=brand.color_secondary,
        color_bg=brand.color_bg,
        # El logo servible es el empaquetado en el frontend (/dq-logo.png):
        # /storage/... no pasa por Caddy en producción, así que no se promete.
        logo_url=None,
        links_photo_url=media_url(brand.links_photo_path),
        partner_store_url=brand.partner_store_url,
        partner_discount_code=brand.partner_discount_code,
        products=[LandingProductOut(
            title=p.title, url=p.url, category=p.category,
            image_url=product_image_url(p),
        ) for p in products],
    )


@router.get("/plan-prices")
@limiter.limit("60/minute")
def public_plan_prices(request: Request) -> dict:
    """Importes reales de cada plan × duración (leídos de Stripe, con caché)
    para que /planes muestre el total y el equivalente al mes."""
    return get_plan_prices()


@router.post("/register")
@limiter.limit("5/minute")
def public_register(request: Request, body: PublicRegisterIn,
                    db: Session = Depends(get_db)) -> dict:
    """Registro self-serve: crea la ficha (pago pendiente), envía el email de
    arranque (pago + anamnesis) y devuelve la URL de pago de Stripe."""
    email = body.email.strip().lower()
    client = db.scalar(select(Client).where(func.lower(Client.email) == email))

    if client is not None and client.payment_status == "paid":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe una asesoría activa con ese email. Escríbenos y te ayudamos.")

    if client is None:
        client = Client(
            full_name=body.full_name.strip(),
            email=email,
            phone=body.phone.strip(),
            package_tier=body.tier,
            billing_period=body.period,
            status="onboarding",
            auto_pilot=settings.auto_pilot_default,
            portal_token="pendiente",  # se firma con el id real tras el flush
        )
        db.add(client)
        db.flush()
        client.portal_token = new_portal_token(client.id)
        log_event(db, "client", client.id, "client_created",
                  {"by": "self", "tier": client.package_tier,
                   "billing_period": client.billing_period})
    else:
        # Reintento del mismo cliente (pago pendiente): actualizar su elección
        # y reenviar el arranque en vez de duplicar la ficha.
        client.full_name = body.full_name.strip() or client.full_name
        client.phone = body.phone.strip() or client.phone
        client.package_tier = body.tier
        client.billing_period = body.period
    db.commit()
    db.refresh(client)

    # Email de arranque (pago + anamnesis PDF). No bloquea el registro si falla.
    try:
        email_status = send_onboarding_email(db, client)
        db.commit()
    except Exception:
        db.rollback()
        email_status = "failed"

    # URL de pago de Stripe (checkout ligado a ESTE cliente, como el alta
    # manual). Si Stripe no está disponible, el registro y el email ya valen:
    # el cliente tiene su enlace de pago en el correo y el coach lo ve en la web.
    try:
        pay_url = create_checkout_url(db, client.package_tier,
                                      client.billing_period, client=client)
    except StripeError as exc:
        _log.warning("Registro %s sin URL de pago: %s", client.id, exc)
        pay_url = None

    return {"url": pay_url, "email_status": email_status}
