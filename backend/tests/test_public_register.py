"""Tests del registro self-serve (POST /api/public/register) y de la anamnesis
pública por token (/api/p/{token}/anamnesis-template y /anamnesis-pdf).

Requiere PostgreSQL. Sin Stripe configurado (url=None) y sin SMTP (emails off).
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


@pytest.fixture()
def http(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "emails_enabled", False)
    with TestClient(app) as c:
        yield c


def test_register_creates_pending_client_and_reuses_on_retry(http):
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Client

    email = f"reg-{uuid.uuid4().hex[:8]}@x.com"
    body = {"full_name": "Cliente Landing", "email": email,
            "phone": "600123123", "tier": "full", "period": "3m"}
    r = http.post("/api/public/register", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["url"] is None  # Stripe sin configurar en tests

    db = SessionLocal()
    try:
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        assert c is not None
        assert c.package_tier == "full" and c.billing_period == "3m"
        assert c.payment_status == "pending" and c.status == "onboarding"
        assert c.portal_token and c.portal_token != "pendiente"
        cid = c.id
    finally:
        db.close()

    # Reintento con otra elección: actualiza la MISMA ficha (no duplica).
    r2 = http.post("/api/public/register", json={**body, "tier": "pro", "period": "1m"})
    assert r2.status_code == 200, r2.text
    db = SessionLocal()
    try:
        rows = db.scalars(select(Client).where(func.lower(Client.email) == email)).all()
        assert len(rows) == 1 and rows[0].id == cid
        assert rows[0].package_tier == "pro" and rows[0].billing_period == "1m"
    finally:
        db.close()


def test_register_conflict_when_already_paid(http):
    from app.db import SessionLocal
    from app.models import Client
    from app.security import new_portal_token

    email = f"paid-{uuid.uuid4().hex[:8]}@x.com"
    db = SessionLocal()
    try:
        c = Client(full_name="Ya Pagado", email=email, package_tier="full",
                   status="active", portal_token="p", payment_status="paid")
        db.add(c)
        db.flush()
        c.portal_token = new_portal_token(c.id)
        db.commit()
    finally:
        db.close()

    r = http.post("/api/public/register", json={
        "full_name": "Ya Pagado", "email": email, "phone": "600111333",
        "tier": "full", "period": "1m"})
    assert r.status_code == 409


def test_public_anamnesis_template_and_upload(http, monkeypatch):
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Client
    from app.routers import clients as clients_router
    from app.services.storage import list_documents

    email = f"anam-{uuid.uuid4().hex[:8]}@x.com"
    r = http.post("/api/public/register", json={
        "full_name": "Anamnesis Publica", "email": email, "phone": "600222444",
        "tier": "start", "period": "6m"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        c = db.scalar(select(Client).where(func.lower(Client.email) == email))
        token, cid = c.portal_token, c.id
    finally:
        db.close()

    # Plantilla (PDF editable) accesible con el token del cliente.
    rt = http.get(f"/api/p/{token}/anamnesis-template")
    assert rt.status_code == 200
    assert rt.content[:5] == b"%PDF-"

    # Subida del PDF rellenado: la lectura IA se simula (no hay clave en tests).
    monkeypatch.setattr(clients_router, "_do_read_anamnesis", lambda cid, db: {"ok": True})
    ru = http.post(f"/api/p/{token}/anamnesis-pdf",
                   files={"file": ("anamnesis.pdf", b"%PDF-1.4 contenido", "application/pdf")})
    assert ru.status_code == 200, ru.text
    assert ru.json()["ok"] is True
    assert any(d for d in list_documents(cid))

    # Un archivo que no es PDF se rechaza con 422.
    rbad = http.post(f"/api/p/{token}/anamnesis-pdf",
                     files={"file": ("foto.png", b"\x89PNG...", "image/png")})
    assert rbad.status_code == 422

    # Cuando el cliente ya no está en onboarding, la subida pública se cierra.
    db = SessionLocal()
    try:
        c = db.get(Client, cid)
        c.status = "active"
        db.commit()
    finally:
        db.close()
    rclosed = http.post(f"/api/p/{token}/anamnesis-pdf",
                        files={"file": ("anamnesis.pdf", b"%PDF-1.4 x", "application/pdf")})
    assert rclosed.status_code == 409


def test_public_landing_shape(http):
    r = http.get("/api/public/landing")
    assert r.status_code == 200
    data = r.json()
    for key in ("name", "color_primary", "partner_store_url", "partner_discount_code",
                "links_photo_url", "logo_url"):
        assert key in data
