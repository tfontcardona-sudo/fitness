"""SE HAN ACABADO LOS CRÉDITOS: que lo diga el sistema, no el error en inglés.

Hasta aquí, quedarse sin crédito se descubría pulsando «Generar» y leyendo un
502 con el mensaje de Anthropic dentro. El coach perdía la mañana de los planes
sin saber por qué.

Lo que se blinda:
- el error REAL de saldo bajo enciende el cartel (y solo ese: un 400 cualquiera
  de la API no puede mandar a nadie a recargar un crédito que no le falta);
- una llamada que funciona lo apaga SOLA, sin que nadie pulse nada;
- recargar limpia el cartel y reinicia la ventana del informe de coste (si no,
  el gasto del ciclo anterior se restaría dos veces del saldo nuevo);
- el gasto REAL de Anthropic manda sobre la estimación por tokens cuando hay
  clave de administración;
- el aviso del panel sale con destino a la pantalla de créditos.
"""
import os

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


@pytest.fixture(autouse=True)
def _limpia_el_cartel(db):
    """Cada test arranca con el cartel apagado (la fila es única y global)."""
    from app.services import ai_credit

    def _limpia():
        estado = ai_credit.get_state(db)
        estado.sin_credito_desde = None
        estado.ultimo_error = None
        # La fila es ÚNICA y global: dejar puesta la lectura del informe de
        # coste hacía que el siguiente test leyera el gasto real (0) en vez de
        # su estimación, y fallara por algo que no había tocado.
        estado.spent_real_usd = None
        estado.spent_real_at = None
        estado.spent_real_desde = None
        db.commit()
        ai_credit._cartel_encendido = None

    _limpia()
    yield
    _limpia()


def test_solo_el_error_de_saldo_enciende_el_cartel():
    """«billing» a secas sale en errores que no son de saldo: mandar a recargar
    por uno de esos es hacer pagar un crédito que no falta."""
    from app.services.ai_credit import es_error_de_credito

    assert es_error_de_credito(
        "Your credit balance is too low to access the Claude API")
    assert es_error_de_credito("insufficient credit for this request")
    assert not es_error_de_credito("rate_limit_error: too many requests")
    assert not es_error_de_credito("Update your billing address to continue")
    assert not es_error_de_credito(None)


def test_el_error_real_de_la_api_enciende_el_cartel_y_habla_en_cristiano(db):
    """El traductor de errores del cliente de IA es el único sitio por el que
    pasan TODOS los fallos de la API: ahí es donde se sella."""
    from app.services.ai.client import _translate_api_error
    from app.services.ai_credit import get_state, sin_credito

    class _ErrorFalso(Exception):
        pass

    try:
        from anthropic import APIError
    except Exception:  # pragma: no cover — sin librería no hay nada que traducir
        pytest.skip("Sin librería de Anthropic")

    class _SaldoBajo(APIError):
        def __init__(self):
            self.message = ("Your credit balance is too low to access the "
                            "Claude API. Please go to Plans & Billing")
            self.request = None

    traducido = _translate_api_error(_SaldoBajo())
    assert traducido is not None
    # En español y con la salida: nada de leerse el inglés de Anthropic.
    assert "acabado los créditos" in str(traducido)
    assert "console.anthropic.com" in str(traducido)

    db.expire_all()
    assert sin_credito(get_state(db)) is True
    assert "credit balance" in (get_state(db).ultimo_error or "")

    # Un error que NO es de saldo no puede encender el cartel.
    assert _translate_api_error(_ErrorFalso()) is None


def test_una_llamada_que_funciona_apaga_el_cartel_sola(db):
    """No hay que pulsar nada: que la respuesta llegue ES la prueba."""
    from app.services import ai_credit

    ai_credit.marcar_sin_credito("Your credit balance is too low")
    db.expire_all()
    assert ai_credit.get_state(db).sin_credito_desde is not None

    ai_credit.marcar_con_credito()
    db.expire_all()
    estado = ai_credit.get_state(db)
    assert estado.sin_credito_desde is None
    assert estado.ultimo_error is None


def test_el_cartel_apagado_no_toca_la_base_en_cada_llamada(db, monkeypatch):
    """El panel de revisión hace 8-10 llamadas seguidas: comprobar en la base
    «¿hay algo que apagar?» en cada una era abrir 10 sesiones para nada."""
    from app.services import ai_credit

    ai_credit.marcar_con_credito()          # deja el espejo en «apagado»
    llamadas = {"n": 0}

    def _sesion_prohibida(*a, **k):
        llamadas["n"] += 1
        raise AssertionError("no debería abrir sesión")

    monkeypatch.setattr("app.db.SessionLocal", _sesion_prohibida)
    ai_credit.marcar_con_credito()          # no debe tocar la base
    assert llamadas["n"] == 0


def test_recargar_apaga_el_cartel_y_reinicia_la_ventana_del_informe(db):
    """Si la ventana no se reiniciara, la siguiente lectura del informe traería
    el gasto del ciclo anterior y se restaría dos veces del saldo nuevo."""
    from datetime import datetime, timedelta, timezone

    from app.services.ai_credit import anotar_recarga, get_state, remaining_usd

    estado = get_state(db)
    estado.balance_usd = 20.0
    estado.spent_usd = 3.0
    estado.spent_real_usd = 7.5
    estado.spent_real_at = datetime.now(timezone.utc)
    estado.spent_real_desde = datetime.now(timezone.utc) - timedelta(days=10)
    estado.sin_credito_desde = datetime.now(timezone.utc)
    estado.ultimo_error = "credit balance is too low"
    db.commit()

    # Con gasto REAL, el restante sale de él (7,50), no de la estimación (3).
    assert remaining_usd(get_state(db)) == pytest.approx(12.5)

    res = anotar_recarga(db, 50.0)
    db.expire_all()
    estado = get_state(db)
    assert res["balance_usd"] == pytest.approx(62.5)   # 12,50 que quedaban + 50
    assert estado.spent_real_usd == 0.0                # la ventana vuelve a cero
    assert estado.spent_real_desde is not None
    assert estado.sin_credito_desde is None            # recargar ES la prueba
    assert estado.ultimo_error is None
    assert remaining_usd(estado) == pytest.approx(62.5)


def test_el_gasto_real_manda_sobre_la_estimacion(db):
    from datetime import datetime, timezone

    from app.services.ai_credit import gasto_desde_la_recarga, get_state

    estado = get_state(db)
    estado.spent_usd = 4.0
    estado.spent_real_usd = None
    estado.spent_real_at = None
    db.commit()
    assert gasto_desde_la_recarga(get_state(db)) == (4.0, False)

    estado = get_state(db)
    estado.spent_real_usd = 6.25
    estado.spent_real_at = datetime.now(timezone.utc)
    db.commit()
    assert gasto_desde_la_recarga(get_state(db)) == (6.25, True)


def test_sin_clave_de_administracion_el_informe_ni_se_intenta(db, monkeypatch):
    """Sin clave, `refrescar_gasto_real` no debe llamar a nadie ni escribir
    nada: el sistema sigue con la estimación de siempre."""
    from app.services import ai_cost_report

    monkeypatch.setattr(ai_cost_report.settings, "anthropic_admin_key", "")
    ai_cost_report._reset_estrangulador()
    assert ai_cost_report.disponible() is False
    assert ai_cost_report.refrescar_gasto_real(db) is None
    with pytest.raises(ai_cost_report.CostReportError):
        ai_cost_report.coste_desde(__import__("datetime").datetime.now())


def test_el_informe_de_coste_suma_todos_los_tramos_de_todos_los_dias(db, monkeypatch):
    """La Cost API devuelve importes como CADENA y agrupados por día y concepto.
    Sumarlos mal (o quedarse con la primera página) deja el saldo mintiendo."""
    from datetime import datetime, timedelta, timezone

    from app.services import ai_cost_report

    monkeypatch.setattr(ai_cost_report.settings, "anthropic_admin_key", "sk-ant-admin-falsa")
    paginas = [
        {"data": [{"results": [{"amount": "1.50"}, {"amount": "0.25"}]},
                  {"results": [{"amount": "2.00"}]}],
         "has_more": True, "next_page": "page_2"},
        {"data": [{"results": [{"amount": "0.75"}]}], "has_more": False},
    ]
    vistas: list[dict] = []

    class _Respuesta:
        status_code = 200

        def __init__(self, cuerpo):
            self._cuerpo = cuerpo

        def raise_for_status(self):
            return None

        def json(self):
            return self._cuerpo

    class _Cliente:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None, headers=None):
            vistas.append(dict(params or {}))
            return _Respuesta(paginas[len(vistas) - 1])

    import httpx

    monkeypatch.setattr(httpx, "Client", _Cliente)
    ai_cost_report._reset_estrangulador()

    total = ai_cost_report.coste_desde(datetime.now(timezone.utc) - timedelta(days=3))
    assert total == pytest.approx(4.50)
    assert len(vistas) == 2 and vistas[1].get("page") == "page_2"
    # Y se pide con las cabeceras que exige la API de administración.
    assert "starting_at" in vistas[0] and "ending_at" in vistas[0]


def test_el_informe_no_se_pide_mas_de_una_vez_por_minuto(db, monkeypatch):
    """Anthropic recomienda no pasar de una consulta por minuto: la pantalla de
    créditos la pide en cada carga."""
    from app.services import ai_cost_report

    monkeypatch.setattr(ai_cost_report.settings, "anthropic_admin_key", "sk-ant-admin-falsa")
    veces = {"n": 0}

    def _falso(desde, hasta=None):
        veces["n"] += 1
        return 3.25

    monkeypatch.setattr(ai_cost_report, "coste_desde", _falso)
    ai_cost_report._reset_estrangulador()

    assert ai_cost_report.refrescar_gasto_real(db) == 3.25
    assert ai_cost_report.refrescar_gasto_real(db) == 3.25   # estrangulado
    assert veces["n"] == 1
    assert ai_cost_report.refrescar_gasto_real(db, forzar=True) == 3.25
    assert veces["n"] == 2
    ai_cost_report._reset_estrangulador()


def test_una_lectura_vieja_del_informe_deja_de_mandar(db):
    """Si se quita la clave de administración, la última cifra real se queda
    congelada. Sin plazo, el saldo dejaba de bajar para siempre y el coach
    miraba un número que ya no se movía."""
    from datetime import datetime, timedelta, timezone

    from app.services.ai_credit import (REAL_FRESCO_HORAS, gasto_desde_la_recarga,
                                        get_state)

    estado = get_state(db)
    estado.spent_usd = 9.0
    estado.spent_real_usd = 2.0
    estado.spent_real_at = datetime.now(timezone.utc) - timedelta(
        hours=REAL_FRESCO_HORAS + 1)
    db.commit()
    assert gasto_desde_la_recarga(get_state(db)) == (9.0, False)


def test_el_panel_avisa_de_que_no_hay_creditos_y_lleva_a_recargar(db, http):
    """El aviso es de SISTEMA (no de un cliente) y su destino es /creditos."""
    from app.services.ai_credit import marcar_sin_credito

    marcar_sin_credito("Your credit balance is too low")
    r = http.get("/api/alerts", headers=_auth())
    assert r.status_code == 200
    avisos = [a for a in r.json()["alerts"] if a["kind"] == "sin_creditos"]
    assert avisos, "el aviso de crédito agotado no sale en el panel"
    aviso = avisos[0]
    assert aviso["severity"] == "alta"
    assert aviso["to"] == "/creditos"
    assert aviso["client_id"] == 0
    assert "Recargar" in aviso["action"]


def test_el_endpoint_cuenta_el_estado_y_propone_la_ultima_recarga(db, http):
    """Recargar tiene que ser UN toque: el importe de la última ya viene."""
    from app.services.ai_credit import anotar_recarga, marcar_sin_credito

    anotar_recarga(db, 37.0)
    marcar_sin_credito("Your credit balance is too low")

    r = http.get("/api/ai-credit", headers=_auth())
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["sin_credito_desde"] is not None
    assert "credit balance" in (cuerpo["ultimo_error"] or "")
    assert cuerpo["ultima_recarga_usd"] == pytest.approx(37.0)
    assert cuerpo["gasto_es_real"] in (True, False)
    assert isinstance(cuerpo["informe_de_coste"], bool)
