"""Pantalla VENDER del panel: catálogo de ofertas y planes con su enlace.

El coach elige aquí qué vender y copia/manda el enlace de pago. El catálogo lo
arma el backend (services/sales_catalog.py) para que:
- el ENLACE lleve siempre el dominio público oficial (antes lo construía el
  navegador con window.location.origin), y
- cada enlace venga con `ready`/`issue`: si a Stripe le falta el precio o el
  cupón, el panel lo dice ANTES de que el coach se lo mande a nadie (hasta
  ahora el cliente acababa en la página de planes sin explicación).

GOTCHA: sin `from __future__ import annotations` (gotcha §5.1 de CLAUDE.md).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Client

router = APIRouter(prefix="/api/sales", tags=["sales"],
                   dependencies=[Depends(get_current_user)])


@router.get("/catalog")
def get_catalog(refresh: bool = False) -> dict:
    """Ofertas y planes vendibles: importes reales, enlace y si está listo."""
    from app.services.sales_catalog import sales_catalog

    return sales_catalog(refresh=refresh)


@router.get("/client-link/{client_id}")
def client_pay_link(client_id: int, db: Session = Depends(get_db)) -> dict:
    """Enlace de pago DE UN CLIENTE ya dado de alta (/api/pay/{token}) con lo
    que va a pasar de verdad al abrirlo: cobrar, o no cobrar porque ya pagó.

    Sin esto el coach mandaba el enlace a ciegas: si el cliente ya había
    pagado, el enlace le llevaba a la página de "pago recibido" y parecía roto.
    """
    from app.config import settings
    from app.services.portal import today_local
    from app.services.renewals import is_due
    from app.services.stripe_service import OFFER_PERIODS

    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")

    base = settings.public_base_url.rstrip("/")
    url = f"{base}/api/pay/{client.portal_token}"
    renovable = is_due(client, today_local())
    if client.payment_status == "paid" and not renovable:
        estado, nota = "pagado", ("Ya ha pagado: este enlace NO le cobra nada "
                                  "(le lleva a la página de pago recibido).")
    elif client.payment_status == "paid" and renovable:
        estado, nota = "renovacion", ("Su ciclo está por vencer: el enlace abre "
                                      "el pago de la renovación.")
    elif client.billing_period in OFFER_PERIODS and client.stripe_subscription_id:
        estado, nota = "suscripcion", ("Tiene la oferta en marcha: el enlace le "
                                       "lleva a pagar solo lo que quede pendiente, "
                                       "sin empezar otra suscripción.")
    else:
        estado, nota = "cobra", "El enlace abre el pago de su plan en Stripe."
    return {
        "url": url, "state": estado, "note": nota,
        "tier": client.package_tier, "period": client.billing_period,
        "payment_status": client.payment_status,
    }
