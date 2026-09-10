"""LOS CRÉDITOS: cuánto queda, EN QUÉ se fue y qué se pagó.

El botón decía "quedan 12 $" y nada más. Con eso el coach no puede decidir: si
el mes se le fue en generar planes, en leer anamnesis o en el panel de revisión
son tres conclusiones distintas.

Lo que se blinda aquí:
- cada llamada se apunta con su PROPÓSITO y su cliente, y el propósito viaja
  por contexto (que es lo que evita encadenar un parámetro por veinte firmas);
- una recarga SUMA al saldo en vez de obligar a hacer la cuenta a mano;
- el desglose reparte el gasto por propósito y el extracto lo cuenta llamada a
  llamada.
"""
import os
import uuid

import pytest


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
def db():
    from app.db import SessionLocal

    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def http():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth():
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}


def test_el_proposito_viaja_por_contexto_y_el_cliente_se_hereda():
    """El propósito se afina por dentro (núcleo → comidas) sin volver a pasar el
    cliente: perderlo ahí era dejar el apunte sin dueño."""
    from app.services.ai_credit import proposito, proposito_actual

    assert proposito_actual() == ("otro", None)
    with proposito("plan", 77):
        assert proposito_actual() == ("plan", 77)
        with proposito("comidas"):          # sin cliente: se hereda
            assert proposito_actual() == ("comidas", 77)
        assert proposito_actual() == ("plan", 77)
    assert proposito_actual() == ("otro", None)


def test_un_proposito_inventado_cae_en_otras_llamadas():
    """`purpose` sale de código nuestro, pero un valor fuera de la lista
    convertiría el desglose en mentira."""
    from app.services.ai_credit import etiqueta_de_proposito, proposito, proposito_actual

    with proposito("inventado"):
        assert proposito_actual()[0] == "otro"
    assert etiqueta_de_proposito("inventado") == "Otras llamadas"
    assert etiqueta_de_proposito("revision") == "Panel de revisión"


def test_cada_llamada_queda_apuntada_con_su_proposito(db):
    from sqlalchemy import select

    from app.models import AiUsageEvent
    from app.services.ai_credit import proposito, record_usage

    marca = uuid.uuid4().hex[:8]
    with proposito("revision", None):
        record_usage(f"claude-haiku-{marca}", 1000, 500)
    ev = db.scalars(
        select(AiUsageEvent).where(AiUsageEvent.model == f"claude-haiku-{marca}")
    ).one()
    assert ev.purpose == "revision"
    assert ev.cost_usd > 0


def test_recargar_suma_al_saldo_en_vez_de_pedir_la_cuenta_hecha(http, db):
    """"Me quedaban 12, meto 50, escribo 62" era la cuenta que el coach tenía
    que hacer. Ahora teclea lo que ha PAGADO y el sistema hace la suma."""
    from app.services.ai_credit import get_state, remaining_usd

    # Punto de partida conocido.
    r = http.put("/api/ai-credit", headers=_auth(), json={"balance_usd": 20.0})
    assert r.status_code == 200, r.text
    assert r.json()["remaining_usd"] == 20.0

    r = http.post("/api/ai-credit/topup", headers=_auth(),
                  json={"amount_usd": 50.0, "note": "recarga de prueba"})
    assert r.status_code == 200, r.text
    assert r.json()["remaining_usd"] == 70.0

    db.expire_all()
    assert remaining_usd(get_state(db)) == 70.0

    # …y la recarga queda en el libro, con el saldo que había antes.
    hist = http.get("/api/ai-credit/history", headers=_auth()).json()
    ultima = hist["topups"][0]
    assert ultima["amount_usd"] == 50.0
    assert ultima["balance_before_usd"] == 20.0


def test_una_recarga_de_cero_o_negativa_no_se_admite(http):
    for importe in (0, -10):
        r = http.post("/api/ai-credit/topup", headers=_auth(), json={"amount_usd": importe})
        assert r.status_code == 422, importe


def test_el_desglose_dice_en_que_se_fue_el_dinero(http, db):
    from app.services.ai_credit import desglose, proposito, record_usage

    marca = uuid.uuid4().hex[:6]
    with proposito("plan"):
        record_usage(f"opus-{marca}", 100_000, 20_000)     # caro
    with proposito("lecciones"):
        record_usage(f"haiku-{marca}", 2_000, 300)         # barato
    db.commit()

    partes = {d["purpose"]: d for d in desglose(db, days=1)}
    assert "plan" in partes and "lecciones" in partes
    assert partes["plan"]["label"] == "Generar la planificación"
    # Lo caro va primero: es como se lee para decidir dónde recortar.
    orden = [d["purpose"] for d in desglose(db, days=1)]
    assert orden.index("plan") < orden.index("lecciones")
    assert partes["plan"]["cost_usd"] > partes["lecciones"]["cost_usd"]
    assert 0 <= partes["plan"]["share"] <= 100

    # Y el extracto lo cuenta llamada a llamada.
    hist = http.get("/api/ai-credit/history?days=1", headers=_auth()).json()
    modelos = [e["model"] for e in hist["events"]]
    assert f"opus-{marca}" in modelos
