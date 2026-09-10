"""TODO aviso lleva a un sitio y dice por qué.

Petición del dueño: al pulsar un aviso, que te lleve al apartado CONCRETO que
está avisando, te lo marque en rojo y te diga el motivo — «y en todas las
infinitas combinaciones que pueden haber de alertas y avisos posibles».

Revisar los avisos de uno en uno no lo garantiza: el día que alguien añada uno
nuevo y se olvide del destino, ese aviso deja al coach en la pestaña sin saber
dónde mirar. Aquí se comprueba la propiedad, no los casos: es IMPOSIBLE que
`_alert` devuelva un aviso sin destino y sin explicación.
"""
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

_PESTANAS = ("resumen", "anamnesis", "planificacion", "seguimiento", "feedback")


class _ClienteFalso:
    id = 42
    full_name = "Cliente de prueba"


def test_ningun_aviso_sale_sin_sitio_al_que_llevar():
    """Un tipo de aviso INVENTADO —el que añadirá alguien mañana— sigue
    marcando el apartado del que habla."""
    from app.routers.alerts import _alert

    for tab in _PESTANAS:
        aviso = _alert(_ClienteFalso(), "un_aviso_que_nadie_ha_registrado", "alta",
                       "Pasa algo aquí", tab, "Arreglarlo")
        assert aviso["target"] == f"tab.{tab}", (
            f"el aviso de la pestaña {tab} no marca nada")
        assert aviso["fix"], "un recuadro rojo sin explicar por qué es un susto"


def test_el_motivo_hace_de_explicacion_cuando_no_hay_una_mejor():
    from app.routers.alerts import _alert

    aviso = _alert(_ClienteFalso(), "otro_sin_registrar", "media",
                   "La dieta lleva lentejas y no las tolera", "planificacion", "Cambiarlas")
    assert aviso["fix"] == "La dieta lleva lentejas y no las tolera"


def test_un_aviso_de_fuera_de_la_ficha_no_necesita_ancla():
    """Los que se arreglan en otra pantalla (créditos, servidor) llevan `to`;
    inventarles un ancla de pestaña los mandaría a una ficha que no toca."""
    from app.routers.alerts import _alert

    aviso = _alert(_ClienteFalso(), "algo_de_sistema", "alta", "Mensaje",
                   "resumen", "Ir", to="/creditos")
    assert aviso["to"] == "/creditos"
    assert aviso["target"] is None


def test_el_destino_propio_manda_sobre_la_red_de_seguridad():
    from app.routers.alerts import _alert

    aviso = _alert(_ClienteFalso(), "no_logs", "media", "Sin registros",
                   "seguimiento", "Escribirle")
    assert aviso["target"] and not aviso["target"].startswith("tab."), (
        "la red de seguridad pisó el destino exacto del aviso")


def test_todos_los_avisos_vivos_del_panel_llevan_a_alguna_parte():
    """Y sobre los avisos REALES que devuelve el sistema ahora mismo."""
    import os

    from fastapi.testclient import TestClient

    from app.main import app
    from app.security import create_access_token

    cabecera = {"Authorization": f"Bearer {create_access_token(os.environ.get('ADMIN_1_USER', 'coach1'))}"}
    with TestClient(app) as c:
        r = c.get("/api/alerts", headers=cabecera)
    assert r.status_code == 200
    for aviso in r.json()["alerts"]:
        assert aviso.get("target") or aviso.get("to"), (
            f"el aviso {aviso['kind']} no lleva a ninguna parte")
        assert aviso.get("fix"), f"el aviso {aviso['kind']} no explica por qué"
