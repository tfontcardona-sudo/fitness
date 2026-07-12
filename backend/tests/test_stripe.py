"""Tests del webhook de Stripe (con Stripe simulado).

Verifica las dos rutas de `checkout.session.completed`:
- alta manual (metadata.client_id) → marca a ese cliente como pagado;
- registro personal (sin client_id) → crea el perfil con su plan, pagado.

Requiere PostgreSQL. No llama a Stripe de verdad: se simula construct_event.
"""
from __future__ import annotations

import uuid
import warnings

import pytest

warnings.filterwarnings("ignore")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


def _fake_stripe(event: dict):
    """Devuelve un módulo stripe simulado cuyo Webhook.construct_event → event."""
    class _Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return event

    class _Stripe:
        Webhook = _Webhook

    return lambda: _Stripe


def _completed(session_obj: dict) -> dict:
    return {"type": "checkout.session.completed", "data": {"object": session_obj}}


def _prep(monkeypatch):
    from app.config import settings
    from app.services import stripe_service

    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(settings, "emails_enabled", False)  # nada de SMTP en tests
    return stripe_service


def test_webhook_marks_manual_client_paid(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    db = SessionLocal()
    try:
        c = Client(full_name="Manual Pay", email=f"m-{uuid.uuid4().hex[:8]}@x.com",
                   package_tier="full", status="onboarding", portal_token="p",
                   payment_status="pending")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        event = _completed({"metadata": {"client_id": str(cid), "tier": "full"},
                            "payment_status": "paid"})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res.get("marked_paid") == cid

        db.expire_all()
        c = db.get(Client, cid)
        assert c.payment_status == "paid" and c.paid_at is not None
    finally:
        db.close()


def test_webhook_selfserve_creates_paid_client(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from sqlalchemy import func, select

    email = f"self-{uuid.uuid4().hex[:8]}@x.com"
    event = _completed({
        "metadata": {"tier": "start"},
        "payment_status": "paid",
        "customer_details": {"email": email, "name": "Nuevo Cliente", "phone": "600111222"},
    })
    monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))

    db = SessionLocal()
    try:
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert "created" in res
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        assert c is not None
        assert c.package_tier == "start"
        assert c.payment_status == "paid"
        assert c.status == "onboarding"
        assert c.portal_token and c.portal_token != "pendiente"
    finally:
        db.close()


def test_webhook_selfserve_existing_email_is_idempotent(monkeypatch):
    stripe_service = _prep(monkeypatch)
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    email = f"dup-{uuid.uuid4().hex[:8]}@x.com"
    db = SessionLocal()
    try:
        c = Client(full_name="Ya existe", email=email, package_tier="pro",
                   status="onboarding", portal_token="p", payment_status="pending")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
        cid = c.id

        event = _completed({"metadata": {"tier": "pro"}, "payment_status": "paid",
                            "customer_details": {"email": email, "name": "Ya existe"}})
        monkeypatch.setattr(stripe_service, "_stripe", _fake_stripe(event))
        res = stripe_service.handle_webhook(db, b"{}", "sig")
        assert res.get("marked_paid") == cid and res.get("existing") is True
    finally:
        db.close()
