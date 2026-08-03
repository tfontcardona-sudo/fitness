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

def _clean_rounds(db, dates):
    """Borra SOLO las rondas de esas fechas (BD compartida con el panel de dev:
    un delete-all se llevaría el historial real de rondas del coach)."""
    from app.models import WhatsAppRound, WhatsAppSend

    ids = [r.id for r in db.query(WhatsAppRound).filter(WhatsAppRound.round_date.in_(dates))]
    if ids:
        db.query(WhatsAppSend).filter(WhatsAppSend.round_id.in_(ids)).delete()
        db.query(WhatsAppRound).filter(WhatsAppRound.id.in_(ids)).delete()
    db.commit()


@needs_db
def test_ronda_del_dia_es_estable_y_avanza_al_siguiente():
    from app.db import SessionLocal

    d1, d2 = date(2099, 1, 4), date(2099, 1, 5)
    with SessionLocal() as db:
        _clean_rounds(db, [d1, d2])

        r1 = wa.get_or_create_round(db, today=d1)
        r2 = wa.get_or_create_round(db, today=d1)
        assert r1.id == r2.id and r1.brief_key == r2.brief_key  # reabrir no cambia

        r3 = wa.get_or_create_round(db, today=d2)
        assert r3.brief_index == (r1.brief_index + 1) % 100  # avanza sin saltos
        assert r3.brief_key != r1.brief_key

        _clean_rounds(db, [d1, d2])


@needs_db
def test_marcar_enviado_es_idempotente_y_cliente_borrado_no_revienta():
    from app.db import SessionLocal
    from app.models import Client, WhatsAppSend

    d = date(2099, 1, 10)
    with SessionLocal() as db:
        _clean_rounds(db, [d])
        c = Client(full_name="WA Test", email=f"wa-{uuid.uuid4().hex[:8]}@x.com",
                   portal_token=uuid.uuid4().hex, phone="600000000", status="active")
        db.add(c)
        db.commit()

        rnd = wa.get_or_create_round(db, today=d)
        assert wa.mark_sent(db, round_id=rnd.id, client_id=c.id, text="hola") is True
        assert wa.mark_sent(db, round_id=rnd.id, client_id=c.id, text="otra vez") is True
        n = db.query(WhatsAppSend).filter(WhatsAppSend.round_id == rnd.id).count()
        assert n == 1  # no duplica

        # Cliente inexistente (borrado entre la carga y el clic) → False, no 500.
        assert wa.mark_sent(db, round_id=rnd.id, client_id=99_999_999) is False

        _clean_rounds(db, [d])
        db.delete(c)
        db.commit()


@needs_db
def test_build_round_solo_clientes_activos_con_telefono():
    from app.db import SessionLocal
    from app.models import Client

    now = datetime(2099, 1, 17, 10, tzinfo=TZ)
    with SessionLocal() as db:
        _clean_rounds(db, [now.date()])
        activo = Client(full_name="Activo Uno", email=f"act-{uuid.uuid4().hex[:8]}@x.com",
                        portal_token=uuid.uuid4().hex, phone="600111222",
                        status="active", package_tier="train")
        sin_tel = Client(full_name="Sin Tel", email=f"st-{uuid.uuid4().hex[:8]}@x.com",
                         portal_token=uuid.uuid4().hex, status="active")
        inactivo = Client(full_name="Inactivo", email=f"ina-{uuid.uuid4().hex[:8]}@x.com",
                          portal_token=uuid.uuid4().hex, phone="600333444", status="inactive")
        db.add_all([activo, sin_tel, inactivo])
        db.commit()

        out = wa.build_round(db, ai=None, now=now)
        ids = {i["client_id"] for i in out["items"]}
        assert activo.id in ids
        assert sin_tel.id not in ids and inactivo.id not in ids
        item = next(i for i in out["items"] if i["client_id"] == activo.id)
        assert item["text"] and item["already_sent"] is False
        # Cliente de solo entreno → nunca un brief de dieta.
        assert next(b for b in POOL if b.key == item["brief_key"]).scope != "nutri"
        assert out["pool_size"] == 100

        _clean_rounds(db, [now.date()])
        for c in (activo, sin_tel, inactivo):
            db.delete(c)
        db.commit()


@needs_db
def test_textos_del_dia_se_cachean_y_reescribir_regenera():
    """La IA redacta UNA vez por cliente y día: reabrir el panel no gasta
    llamadas; force=True (Reescribir) sí regenera."""
    from app.db import SessionLocal
    from app.models import Client

    class CountingAI:
        def __init__(self):
            self.calls = 0

        def _raw_call(self, *, model, system, user, temperature=None):
            self.calls += 1
            return f"Mensaje nº {self.calls}"

    now = datetime(2099, 2, 3, 9, tzinfo=TZ)
    with SessionLocal() as db:
        _clean_rounds(db, [now.date()])
        c = Client(full_name="Cache Uno", email=f"ca-{uuid.uuid4().hex[:8]}@x.com",
                   portal_token=uuid.uuid4().hex, phone="600555666", status="active")
        db.add(c)
        db.commit()

        ai = CountingAI()
        out1 = wa.build_round(db, ai=ai, now=now)
        calls_tras_primera = ai.calls
        assert calls_tras_primera >= 1

        out2 = wa.build_round(db, ai=ai, now=now)  # reabrir: 0 llamadas nuevas
        assert ai.calls == calls_tras_primera
        t1 = next(i["text"] for i in out1["items"] if i["client_id"] == c.id)
        t2 = next(i["text"] for i in out2["items"] if i["client_id"] == c.id)
        assert t1 == t2  # mismo texto persistido

        wa.build_round(db, ai=ai, now=now, force=True)  # Reescribir sí regenera
        assert ai.calls > calls_tras_primera

        _clean_rounds(db, [now.date()])
        db.delete(c)
        db.commit()
