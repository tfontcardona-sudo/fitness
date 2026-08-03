"""Ronda diaria de WhatsApp: pool de 100, rotación sin repetir y redacción con IA."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services import whatsapp_round as wa
from app.services.whatsapp_pool import POOL, applies_to, brief_for_index

TZ = ZoneInfo("Europe/Madrid")


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


# ---- pool (puro) ----

def test_pool_tiene_100_briefs_unicos():
    assert len(POOL) == 100
    assert len({b.key for b in POOL}) == 100
    # Cada brief dice a quién aplica y en qué franja.
    assert all(b.scope in ("any", "nutri", "train") for b in POOL)
    assert all(b.franja in ("any", "manana", "tarde", "noche") for b in POOL)


def test_rotacion_no_repite_hasta_completar_los_100():
    keys = [brief_for_index(i).key for i in range(100)]
    assert len(set(keys)) == 100          # 100 días sin repetir
    assert brief_for_index(100).key == keys[0]   # el 101 vuelve a empezar


def test_brief_de_dieta_no_aplica_a_cliente_sin_dieta():
    nutri_brief = next(b for b in POOL if b.scope == "nutri")
    train_brief = next(b for b in POOL if b.scope == "train")
    assert applies_to(nutri_brief, has_nutrition=False, has_training=True) is False
    assert applies_to(train_brief, has_nutrition=True, has_training=False) is False
    # Los genéricos valen para todos.
    generic = next(b for b in POOL if b.scope == "any")
    assert applies_to(generic, has_nutrition=False, has_training=True) is True


def test_cliente_recibe_un_brief_que_le_aplica():
    """Un cliente de solo entreno nunca recibe el brief de dieta del día: se le
    da el siguiente que sí le encaja."""
    for i in range(len(POOL)):
        b = wa._brief_for_client(i, has_nutrition=False, has_training=True)
        assert applies_to(b, has_nutrition=False, has_training=True)


def test_franja_horaria():
    d = date(2026, 8, 3)
    assert wa.franja_of(datetime.combine(d, datetime.min.time(), TZ).replace(hour=9)) == "manana"
    assert wa.franja_of(datetime.combine(d, datetime.min.time(), TZ).replace(hour=17)) == "tarde"
    assert wa.franja_of(datetime.combine(d, datetime.min.time(), TZ).replace(hour=22)) == "noche"


# ---- redacción ----

def test_sin_ia_hay_texto_de_reserva():
    brief = POOL[0]
    txt = wa.compose_for_client(brief, {"nombre": "Ana"}, ai=None)
    assert txt and "Ana" in txt


def test_ia_caida_no_deja_al_coach_sin_mensaje():
    class Boom:
        def _raw_call(self, **kw):
            raise RuntimeError("API caída")

    txt = wa.compose_for_client(POOL[0], {"nombre": "Ana"}, ai=Boom())
    assert txt and "Ana" in txt  # cae al texto de reserva, no revienta


def test_prompt_lleva_cliente_franja_y_dia():
    """La IA recibe el contexto del cliente y el momento, para no clonar textos."""
    calls = []

    class FakeAI:
        def _raw_call(self, *, model, system, user):
            calls.append({"system": system, "user": user})
            return "  \"¿Cómo llevas la semana, Ana?\"  "

    now = datetime(2026, 8, 3, 9, 0, tzinfo=TZ)  # lunes por la mañana
    txt = wa.compose_for_client(POOL[0], {"nombre": "Ana", "plan": "DQR Full"},
                                ai=FakeAI(), now=now)
    assert txt == "¿Cómo llevas la semana, Ana?"  # limpia comillas y espacios
    user = calls[0]["user"]
    assert "Ana" in user and "DQR Full" in user
    assert "lunes" in user and "manana" in user
    assert "2-4 frases" in calls[0]["system"]


# ---- rotación persistida y envíos ----

@needs_db
def test_ronda_del_dia_es_estable_y_avanza_al_siguiente():
    from app.db import SessionLocal
    from app.models import WhatsAppRound, WhatsAppSend

    with SessionLocal() as db:
        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        db.commit()

        hoy = date(2026, 8, 3)
        r1 = wa.get_or_create_round(db, today=hoy)
        r2 = wa.get_or_create_round(db, today=hoy)
        assert r1.id == r2.id and r1.brief_index == 0  # reabrir no cambia el mensaje

        r3 = wa.get_or_create_round(db, today=hoy + timedelta(days=1))
        assert r3.brief_index == 1 and r3.brief_key != r1.brief_key

        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        db.commit()


@needs_db
def test_marcar_enviado_es_idempotente():
    from app.db import SessionLocal
    from app.models import Client, WhatsAppRound, WhatsAppSend

    with SessionLocal() as db:
        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        db.commit()
        c = Client(full_name="WA Test", email=f"wa-{uuid.uuid4().hex[:8]}@x.com",
                   portal_token=uuid.uuid4().hex, phone="600000000", status="active")
        db.add(c)
        db.commit()

        rnd = wa.get_or_create_round(db, today=date(2026, 8, 10))
        wa.mark_sent(db, round_id=rnd.id, client_id=c.id, text="hola")
        wa.mark_sent(db, round_id=rnd.id, client_id=c.id, text="hola otra vez")
        n = db.query(WhatsAppSend).filter(WhatsAppSend.round_id == rnd.id).count()
        assert n == 1  # no duplica

        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        db.delete(c)
        db.commit()


@needs_db
def test_build_round_solo_clientes_activos_con_telefono():
    from app.db import SessionLocal
    from app.models import Client, WhatsAppRound, WhatsAppSend

    with SessionLocal() as db:
        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        db.commit()
        activo = Client(full_name="Activo Uno", email=f"act-{uuid.uuid4().hex[:8]}@x.com",
                        portal_token=uuid.uuid4().hex, phone="600111222",
                        status="active", package_tier="train")
        sin_tel = Client(full_name="Sin Tel", email=f"st-{uuid.uuid4().hex[:8]}@x.com",
                         portal_token=uuid.uuid4().hex, status="active")
        inactivo = Client(full_name="Inactivo", email=f"ina-{uuid.uuid4().hex[:8]}@x.com",
                          portal_token=uuid.uuid4().hex, phone="600333444", status="inactive")
        db.add_all([activo, sin_tel, inactivo])
        db.commit()

        out = wa.build_round(db, ai=None, now=datetime(2026, 8, 17, 10, tzinfo=TZ))
        ids = {i["client_id"] for i in out["items"]}
        assert activo.id in ids
        assert sin_tel.id not in ids and inactivo.id not in ids
        item = next(i for i in out["items"] if i["client_id"] == activo.id)
        assert item["text"] and item["already_sent"] is False
        # Cliente de solo entreno → nunca un brief de dieta.
        assert next(b for b in POOL if b.key == item["brief_key"]).scope != "nutri"
        assert out["pool_size"] == 100

        db.query(WhatsAppSend).delete()
        db.query(WhatsAppRound).delete()
        for c in (activo, sin_tel, inactivo):
            db.delete(c)
        db.commit()
