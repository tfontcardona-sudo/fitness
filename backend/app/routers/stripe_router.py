"""Endpoints de pago con Stripe (públicos).

- POST /api/public/checkout   registro personal: crea la sesión de pago del plan
                              elegido y devuelve la URL (la página de planes hace
                              redirect).
- GET  /api/pay/{token}       enlace ESTABLE del alta manual: el cliente lo abre
                              (desde el WhatsApp/email del coach) y va a Stripe.
- POST /api/stripe/webhook    aviso de Stripe al cobrar: marca el pago o crea el
                              perfil del cliente. Verificado por firma.

GOTCHA: sin `from __future__ import annotations` A PROPÓSITO — con él, el
decorador de slowapi hace que FastAPI no resuelva el body Pydantic (422 en query),
igual que pasó en public_site.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_client_by_token
from app.models import Client
from app.ratelimit import client_key
from app.schemas.entities import BillingPeriod, PackageTier
from app.services.stripe_service import StripeError, create_checkout_url, handle_webhook

router = APIRouter(tags=["stripe"])
limiter = Limiter(key_func=client_key)


class CheckoutIn(BaseModel):
    tier: PackageTier
    # Duración elegida: mensual (1m), trimestral (3m) o semestral (6m).
    period: BillingPeriod = "1m"

    @field_validator("tier", mode="before")
    @classmethod
    def _tier_legado(cls, v):
        # Una pestaña de /planes abierta ANTES del deploy envía los nombres
        # antiguos ("start"/"pro"): se traducen en vez de responder 422 en pleno
        # embudo de captación.
        if isinstance(v, str):
            return {"start": "nutri", "pro": "full"}.get(v.strip().lower(), v)
        return v



@router.post("/api/public/checkout")
@limiter.limit("10/minute")
def public_checkout(request: Request, body: CheckoutIn, db: Session = Depends(get_db)) -> dict:
    """Registro personal: crea la sesión de pago del plan elegido → URL de Stripe.
    Con rate limit: es público y cada llamada crea una sesión REAL en Stripe."""
    try:
        return {"url": create_checkout_url(db, body.tier, body.period)}
    except StripeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/api/pay/{token}")
def pay_link(client: Client = Depends(get_client_by_token), db: Session = Depends(get_db)):
    """Enlace estable de pago del alta manual: redirige a Stripe con el plan y la
    duración de ESE cliente. Lo abre desde el mensaje que le envía el coach."""
    from app.config import settings

    base = settings.public_base_url.rstrip("/")
    # YA PAGADO: el botón del email de arranque vive para siempre — reabrirlo
    # tras pagar NO puede cobrar una segunda vez. Se le lleva a la página de
    # gracias en vez de a un checkout nuevo.
    if client.payment_status == "paid":
        return RedirectResponse(f"{base}/pago-ok", status_code=302)
    try:
        url = create_checkout_url(db, client.package_tier, client.billing_period,
                                  client=client)
    except StripeError as exc:
        # Un cliente en su navegador no debe ver JSON con detalles internos:
        # a la página de planes, donde puede escribirnos. El detalle, al log.
        import logging
        logging.getLogger("app.stripe").warning("pay_link %s sin checkout: %s", client.id, exc)
        return RedirectResponse(f"{base}/planes", status_code=302)
    return RedirectResponse(url, status_code=302)


@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Recibe el aviso de cobro de Stripe (verificado por firma) y actúa."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        return handle_webhook(db, payload, sig)
    except StripeError as exc:
        # 400: Stripe reintenta si devolvemos error; útil si el .env aún no está.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
