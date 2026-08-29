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



def _avisa_al_coach(db: Session, que: str, motivo: str) -> None:
    """Push al coach cuando un enlace de pago no ha podido abrir Stripe.
    Best-effort: avisar nunca puede romper la respuesta al cliente."""
    try:
        from app.services.push import notify_coach_pay_link_failed

        notify_coach_pay_link_failed(db, que=que, motivo=motivo)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


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
    # La oferta (1 € → 120 €/mes, u "oferta2" = 2 pagos de 120,50 €) solo
    # existe para el plan Full.
    valido = (t in pkgs.TIERS and period in ("1m", "3m", "6m")) or \
             (t == "full" and period in ("oferta", "oferta2"))
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
    # `?ir=1` = "soy una persona, llévame al pago": el botón de la vista previa
    # de abajo. Sin esta salida, quien cayera en el filtro (una app cuyo
    # user-agent lleve "bot"/"preview") se quedaba en una página muerta.
    quiere_ir = request.query_params.get("ir") == "1"
    if (es_bot or request.method == "HEAD") and not quiere_ir:
        from fastapi.responses import HTMLResponse

        if period == "oferta":
            title = f"{pkgs.label(t)} — primer mes 1 €"
            desc = ("Oferta de 3 meses del plan completo: 1 € el primer mes y "
                    "120 € el segundo y el tercero. Se detiene sola: sin más "
                    "cobros. Pago seguro con Stripe.")
        elif period == "oferta2":
            title = f"{pkgs.label(t)} — 2 pagos de 120,50 €"
            desc = ("La misma oferta de 3 meses en solo 2 pagos de 120,50 € "
                    "(hoy y en un mes). Se detiene sola: sin más cobros. "
                    "Pago seguro con Stripe.")
        else:
            title = f"{pkgs.label(t)} — pago seguro"
            desc = "Asesoría 100 % personalizada. Pago seguro con Stripe."
        # El cuerpo lleva un BOTÓN real al pago (?ir=1): si quien abre esto es
        # una persona y no un robot de vista previa, no se queda atrapada.
        return HTMLResponse(
            "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title>"
            f"<meta property='og:title' content='{title}'>"
            f"<meta property='og:description' content='{desc}'>"
            "</head><body style=\"font-family:system-ui,sans-serif;max-width:34rem;"
            "margin:3rem auto;padding:0 1.25rem;text-align:center\">"
            f"<h1 style='font-size:1.25rem'>{title}</h1><p>{desc}</p>"
            f"<p><a href='{request.url.path}?ir=1' style=\"display:inline-block;"
            "background:#E8833A;color:#fff;text-decoration:none;font-weight:700;"
            "padding:0.9rem 1.5rem;border-radius:0.75rem\">Ir al pago seguro</a></p>"
            "</body></html>"
        )

    try:
        url = create_checkout_url(db, t, period)
    except StripeError as exc:
        import logging
        logging.getLogger("app.stripe").warning(
            "pay_plan_link %s %s sin checkout: %s", t, period, exc)
        # El interesado ya no se queda mirando la página de planes sin saber
        # qué ha pasado (parecía que el enlace estaba roto), y el COACH se
        # entera por push: hasta ahora seguía mandando el mismo enlace muerto.
        _avisa_al_coach(db, f"{pkgs.label(t)} {period}", str(exc))
        return RedirectResponse(f"{base}/planes?pago=error", status_code=302)
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
    # OFERTA (cualquiera de sus dos formas) con suscripción YA creada: reabrir
    # el enlace tras un impago no puede montar una SEGUNDA suscripción (doble
    # cobro mensual y otro primer mes a 1 €, u otros 2 pagos de 120,50 €). Si
    # su suscripción tiene una factura abierta, se le manda ahí (paga lo
    # pendiente y actualiza la tarjeta); si no la hay, está al día.
    if client.billing_period in ("oferta", "oferta2") and client.stripe_subscription_id:
        from app.services.stripe_service import open_invoice_url

        pendiente = open_invoice_url(client)
        return RedirectResponse(pendiente or f"{base}/pago-ok", status_code=302)
    try:
        url = create_checkout_url(db, client.package_tier, client.billing_period,
                                  client=client)
    except StripeError as exc:
        # Un cliente en su navegador no debe ver JSON con detalles internos:
        # a la página de planes, con un aviso de que el pago no se pudo abrir.
        # El detalle, al log; y al coach, un push (antes no se enteraba nadie).
        import logging
        logging.getLogger("app.stripe").warning("pay_link %s sin checkout: %s", client.id, exc)
        _avisa_al_coach(db, f"enlace de {client.full_name or 'un cliente'}", str(exc))
        return RedirectResponse(f"{base}/planes?pago=error", status_code=302)
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
