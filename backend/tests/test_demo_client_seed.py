"""Cliente de demostración de Professional (services/demo_client_seed.py).

Lo crítico a blindar: que esto NUNCA llame a la API real de Anthropic fuera de
producción (la suite usa un AIClient falso a propósito, §7 de CLAUDE.md), que
sea idempotente, y que el cliente que construye trae TODO lo que
`generate_client_plan` exige antes de generar (si falta un campo, la
generación real respondería 422 y el "cliente demo" se quedaría sin plan).
"""
import inspect

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import BrandConfig, Client
from app.services import demo_client_seed as seed


def _limpiar(email: str) -> None:
    """Borra el cliente demo CON sus filas dependientes.

    Con `db.delete(c)` a secas, el ORM anula la FK de los períodos en vez de
    borrarlos y salta un NOT NULL. Y un cliente demo CON período es un estado
    perfectamente normal —se le abre solo en cuanto alguien entra en su
    portal—, así que este test fallaba para cualquiera que lo hubiera abierto,
    sin que nada estuviera roto. Mismo orden de FKs que el borrado RGPD."""
    from app.models import DailyLog, Period, Plan, WorkoutLog

    with SessionLocal() as db:
        c = db.scalar(select(Client).where(Client.email == email))
        if not c:
            return
        periodos = list(db.scalars(select(Period).where(Period.client_id == c.id)))
        for per in periodos:
            logs = list(db.scalars(select(DailyLog).where(DailyLog.period_id == per.id)))
            for lg in logs:
                db.query(WorkoutLog).filter(WorkoutLog.daily_log_id == lg.id).delete()
            db.query(DailyLog).filter(DailyLog.period_id == per.id).delete()
        db.query(Period).filter(Period.client_id == c.id).delete()
        db.query(Plan).filter(Plan.client_id == c.id).delete()
        db.delete(c)
        db.commit()


class _HiloEspia:
    """Sustituye a `threading.Thread`: registra cómo se le llamó y NUNCA deja
    correr el hilo de verdad (comprobarlo dejándolo correr y mirando si al
    final hay cliente sería una carrera con el propio test, no una prueba
    fiable de que se lanzó — o no — la siembra)."""
    instances: list = []

    def __init__(self, *a, **k):
        self.kwargs = k
        _HiloEspia.instances.append(self)

    def start(self) -> None:
        pass


def test_en_dev_tests_no_lanza_ningun_hilo(monkeypatch):
    """La suite corre sin dominio (`is_production` False): esto es lo único
    que impide que un `pytest` normal dispare, en un hilo, una llamada real a
    la IA."""
    _HiloEspia.instances = []
    monkeypatch.setattr(seed.threading, "Thread", _HiloEspia)
    assert settings.is_production is False
    seed.seed_demo_professional_client()
    assert _HiloEspia.instances == []


def test_en_produccion_si_lanza_el_hilo(monkeypatch):
    """Lo simétrico: con `is_production` sí arranca el hilo de la siembra
    (sin dejarlo correr de verdad — eso lo cubren los otros tests, en el hilo
    principal y sin tocar la IA)."""
    _HiloEspia.instances = []
    monkeypatch.setattr(seed.threading, "Thread", _HiloEspia)
    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))
    seed.seed_demo_professional_client()
    assert len(_HiloEspia.instances) == 1
    assert _HiloEspia.instances[0].kwargs.get("target") is seed._seed_sync


def test_ya_existe_detecta_el_cliente_demo():
    _limpiar(seed.DEMO_EMAIL)
    with SessionLocal() as db:
        assert seed._ya_existe(db) is False
        assert seed._crear_cliente_demo(db) is not None
        assert seed._ya_existe(db) is True
    _limpiar(seed.DEMO_EMAIL)


def test_el_cliente_demo_trae_todo_lo_que_pide_generate_plan():
    """Sin esto, `generate_client_plan` respondería 422 y el cliente demo se
    quedaría eternamente sin plan que enseñar."""
    from app.routers.clients import _REQUIRED_FIELDS

    _limpiar(seed.DEMO_EMAIL)
    with SessionLocal() as db:
        client = seed._crear_cliente_demo(db)
        assert client is not None
        for field in _REQUIRED_FIELDS:
            assert getattr(client, field, None) not in (None, "", []), field
        # Marca SELLADA en la ficha, no la que esté activa en el switch en ese
        # momento (regla de siempre: `marca_de_cliente` manda, no el escaparate).
        brand = db.get(BrandConfig, client.brand_id)
        assert brand is not None and brand.slug == "professional-fitness"
        # Acceso ya sellado (no se manda por email: el email es de negocio, no
        # una bandeja real) para que el dueño pueda entrar de verdad al portal.
        assert client.portal_password_hash
        assert client.portal_token and client.portal_token != "pendiente"
    _limpiar(seed.DEMO_EMAIL)


def test_llama_a_generate_client_plan_con_su_firma_real():
    """Guarda contra que la firma de `generate_client_plan` cambie sin que
    esto se entere: es una llamada de una línea, fácil de dejar rota."""
    from app.routers.clients import generate_client_plan

    params = list(inspect.signature(generate_client_plan).parameters)
    assert params == ["client_id", "month_index", "body", "db"]


def test_es_idempotente_no_duplica_el_cliente():
    _limpiar(seed.DEMO_EMAIL)
    with SessionLocal() as db:
        assert seed._crear_cliente_demo(db) is not None
        assert seed._ya_existe(db) is True
    _limpiar(seed.DEMO_EMAIL)
