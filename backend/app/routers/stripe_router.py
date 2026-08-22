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


@router.get("/api/pay/plan/{tier}/{period}")
@limiter.limit("10/minute")
def pay_plan_link(request: Request, tier: str, period: str,
                  db: Session = Depends(get_db)):
    """Enlace de pago DIRECTO de un plan × duración, para enviarlo por WhatsApp
    a un interesado SIN darlo de alta antes (kit de ventas del panel). Crea una
    Checkout Session self-serve y redirige a Stripe; al pagar, el webhook crea
    su ficha con el plan pagado y le envía portal + anamnesis (mismo circuito
    del registro personal). El enlace es permanente: cada clic abre un pago
    nuevo; las sesiones no pagadas caducan solas en Stripe."""
    from app.config import settings
    from app.services import packages as pkgs

    base = settings.public_base_url.rstrip("/")
    t = pkgs.LEGACY_TIERS.get(tier.strip().lower(), tier.strip().lower())
    # Estricto A PROPÓSITO (sin caer al plan por defecto): un enlace mal escrito
    # no puede acabar cobrando el plan más caro. Ante cualquier duda → /planes.
    # "oferta" (1 € el primer mes → suscripción) solo existe para el plan Full.
    valido = (t in pkgs.TIERS and period in ("1m", "3m", "6m")) or \
             (t == "full" and period == "oferta")
    if not valido:
        return RedirectResponse(f"{base}/planes", status_code=302)

    # Los bots de vista previa (WhatsApp/Facebook/Slack/Discord/Twitter…) y los
    # escáneres de enlaces visitan la URL al renderizar el mensaje: se les da
    # una mini-página con título y descripción SIN crear una sesión de Stripe
    # por cada previsualización. Las HEAD (prefetch) tampoco crean sesión —
    # Starlette ejecuta el handler entero también para HEAD. Un bot con UA de
    # navegador se cuela igualmente: solo genera sesiones huérfanas que caducan
    # solas en Stripe (sin cobro), acotadas por el rate limit.
    ua = (request.headers.get("user-agent") or "").lower()
    es_bot = any(b in ua for b in (
        "whatsapp", "facebookexternalhit", "bot", "crawler", "spider",
        "preview", "curl", "wget", "python-requests"))
    if es_bot or request.method == "HEAD":
        from fastapi.responses import HTMLResponse

        if period == "oferta":
            title = f"{pkgs.label(t)} — primer mes 1 €"
            desc = "Oferta: tu primer mes del plan completo por 1 €. Pago seguro con Stripe."
        else:
            title = f"{pkgs.label(t)} — pago seguro"
            desc = "Asesoría 100 % personalizada. Pago seguro con Stripe."
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{title}</title>"
            f"<meta property='og:title' content='{title}'>"
            f"<meta property='og:description' content='{desc}'>"
            f"</head><body>{desc}</body></html>"
        )

    try:
        url = create_checkout_url(db, t, period)
    except StripeError as exc:
        import logging
        logging.getLogger("app.stripe").warning(
            "pay_plan_link %s %s sin checkout: %s", t, period, exc)
        return RedirectResponse(f"{base}/planes", status_code=302)
    return RedirectResponse(url, status_code=302)


@router.get("/api/pay/{token}")
@limiter.limit("10/minute")
def pay_link(request: Request, client: Client = Depends(get_client_by_token),
             db: Session = Depends(get_db)):
    """Enlace estable de pago del alta manual: redirige a Stripe con el plan y la
    duración de ESE cliente. Lo abre desde el mensaje que le envía el coach.
    Con rate limit (como los otros enlaces públicos de pago): cada apertura sin
    pagar crea una Checkout Session REAL en Stripe."""
    from app.config import settings

    base = settings.public_base_url.rstrip("/")
    # YA PAGADO: el botón del email de arranque vive para siempre — reabrirlo
    # tras pagar NO puede cobrar una segunda vez. Se le lleva a la página de
    # gracias en vez de a un checkout nuevo. EXCEPCIÓN: si su ciclo pagado está
    # a punto de vencer (la ventana la fija `renewals.RENEWAL_WARN_DAYS`, hoy
    # 5 días) o ya venció, el MISMO enlace vuelve a abrir un
    # checkout — es el CTA del email de renovación al cliente.
    if client.payment_status == "paid":
        from app.services.portal import today_local
        from app.services.renewals import is_due

        if not is_due(client, today_local()):
            return RedirectResponse(f"{base}/pago-ok", status_code=302)
    # OFERTA con suscripción YA creada: reabrir el enlace tras un impago no
    # puede montar una SEGUNDA suscripción (doble cobro mensual y otro primer
    # mes a 1 €). Si su suscripción tiene una factura abierta, se le manda ahí
    # (paga lo pendiente y actualiza la tarjeta); si no la hay, la suscripción
    # está al día y no toca cobrar nada.
    if client.billing_period == "oferta" and client.stripe_subscription_id:
        from app.services.stripe_service import open_invoice_url

        pendiente = open_invoice_url(client)
        return RedirectResponse(pendiente or f"{base}/pago-ok", status_code=302)
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
