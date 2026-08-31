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
    # REGRESIÓN: la plantilla de arranque crasheaba (Brand sin color_secondary)
    # y el registro devolvía "failed" en silencio — el cliente pagaba y nunca
    # recibía su anamnesis. "disabled" (emails off) o "sent" son los válidos.
    assert data["email_status"] in ("disabled", "sent", "already_sent"), data

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
    r2 = http.post("/api/public/register", json={**body, "tier": "full", "period": "1m"})
    assert r2.status_code == 200, r2.text
    db = SessionLocal()
    try:
        rows = db.scalars(select(Client).where(func.lower(Client.email) == email)).all()
        assert len(rows) == 1 and rows[0].id == cid
        assert rows[0].package_tier == "full" and rows[0].billing_period == "1m"
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
        "tier": "nutri", "period": "6m"})
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


def test_seed_rellena_el_whatsapp_del_coach_solo_si_falta():
    """El seed pone el WhatsApp del coach como contacto público SOLO si el campo
    está vacío: lo que el coach escriba en Marca nunca se pisa. (Se restaura el
    valor original: la BD de dev es compartida con el panel.)"""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import BrandConfig
    from app.seeds.run import COACH_WHATSAPP, seed_brand, seed_coach_contact

    with SessionLocal() as db:
        seed_brand(db)  # garantiza la fila de marca en BD recién creada
        brand = db.scalar(select(BrandConfig).limit(1))
        original = brand.contact_phone
        try:
            brand.contact_phone = None
            db.commit()
            assert seed_coach_contact(db) is True
            db.refresh(brand)
            assert brand.contact_phone == COACH_WHATSAPP

            brand.contact_phone = "+34 600 000 000"  # puesto por el coach
            db.commit()
            assert seed_coach_contact(db) is False
            db.refresh(brand)
            assert brand.contact_phone == "+34 600 000 000"
        finally:
            brand.contact_phone = original
            db.commit()


def test_public_landing_shape(http):
    r = http.get("/api/public/landing")
    assert r.status_code == 200
    data = r.json()
    for key in ("name", "color_primary", "partner_store_url", "partner_discount_code",
                "links_photo_url", "logo_url",
                # Contacto público del coach: /planes abre WhatsApp con este
                # teléfono para pedir información (sin precios publicados).
                "contact_phone", "contact_email"):
        assert key in data


def test_el_formulario_publico_tiene_cupo_diario(http, monkeypatch):
    """Sin tope global, quien rota IPs y direcciones podía crear fichas reales
    y vaciar la cuota diaria de correo del coach: a partir de ahí no salen ni
    los accesos al portal, ni los planes, ni los informes de los clientes de
    verdad (y la cuenta puede quedar restringida por spam)."""
    import uuid

    from app.routers import public_site

    from app.config import settings

    # Tope = altas de hoy + 1 (no 0): con el tope a cero el test pasaba aunque
    # el CONTADOR estuviera muerto (0 >= 0 siempre). Así hay que dar un alta de
    # verdad para agotarlo, y el margen se calcula sobre lo que ya lleve la
    # base del día (los demás tests también dan altas públicas).
    # El límite por IP (5/min) es de MÓDULO y lo comparten todos los tests: sin
    # apagarlo, esta llamada se come una ficha del cubo y el 429 aparece en
    # otro test más tarde (gotcha documentado en CLAUDE.md).
    monkeypatch.setattr(public_site.limiter, "enabled", False)
    avisos = []
    monkeypatch.setattr(public_site, "_avisa_cupo_al_coach",
                        lambda db, n: avisos.append(n))

    from app.db import SessionLocal as _SL

    with _SL() as _db:
        ya_hoy = public_site._altas_publicas_de_hoy(_db)
    monkeypatch.setattr(settings, "public_signups_per_day", ya_hoy + 1)
    monkeypatch.setattr(public_site, "MAX_ALTAS_PUBLICAS_DIA", ya_hoy + 1)

    # 1) Un alta legítima: consume el cupo del día.
    primera = http.post("/api/public/register", json={
        "full_name": "Primera Alta", "email": f"cupo1-{uuid.uuid4().hex[:8]}@example.com",
        "phone": "600111000", "tier": "full", "period": "1m",
    })
    assert primera.status_code == 200, primera.text
    assert not avisos, "el cupo no se agota con el alta que aún cabe"

    # 2) La siguiente ya no cabe.
    email_frenado = f"cupo-{uuid.uuid4().hex[:8]}@example.com"
    r = http.post("/api/public/register", json={
        "full_name": "Cupo Agotado", "email": email_frenado,
        "phone": "600111222", "tier": "full", "period": "1m",
    })
    assert r.status_code == 429
    assert "WhatsApp" in r.json()["detail"]
    assert avisos, "el coach tiene que enterarse el mismo día"

    # 3) Y el LEAD no se pierde: queda anotado para darle el alta a mano.
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import AuditLog

    with SessionLocal() as db:
        anotado = db.scalar(
            select(AuditLog).where(AuditLog.event == "public_signup_blocked")
            .order_by(AuditLog.id.desc()).limit(1))
        assert anotado is not None
        assert anotado.detail_json["email"] == email_frenado
        assert anotado.detail_json["phone"] == "600111222"
