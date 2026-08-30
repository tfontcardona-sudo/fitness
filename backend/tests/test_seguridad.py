"""Seguridad del arranque y de la configuración (anti-pirateo/robo/copia).

La primera parte prueba la lógica pura de `Settings` (guardián de secretos) sin
base de datos. La segunda (cabeceras, CORS, timing del login) usa TestClient y se
salta sin PostgreSQL.
"""
import pytest

from app.config import Settings


def _db_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _mk(**kw) -> Settings:
    """Settings aislado (sin leer el .env del entorno) para el test."""
    base = dict(
        jwt_secret="x" * 48, portal_token_secret="y" * 48, domain="",
        _env_file=None,
    )
    base.update(kw)
    return Settings(**base)


def test_is_production_depende_del_dominio():
    assert _mk(domain="").is_production is False
    assert _mk(domain="dqr.example").is_production is True


def test_secreto_por_defecto_del_repo_se_detecta():
    s = _mk(jwt_secret="dev-insecure-jwt-secret")
    problemas = s.insecure_secrets()
    assert any("JWT_SECRET" in p for p in problemas)


def test_secreto_de_portal_por_defecto_se_detecta():
    s = _mk(portal_token_secret="dev-insecure-portal-secret")
    assert any("PORTAL_TOKEN_SECRET" in p for p in s.insecure_secrets())


def test_secreto_corto_se_detecta():
    s = _mk(jwt_secret="corto")
    assert any("demasiado corto" in p for p in s.insecure_secrets())


def test_secretos_largos_y_unicos_pasan():
    s = _mk(jwt_secret="a" * 40, portal_token_secret="b" * 40)
    assert s.insecure_secrets() == []


def test_lifespan_bloquea_arranque_en_produccion_con_secreto_inseguro(monkeypatch):
    """En producción (dominio puesto) con un secreto forjable, la app REHÚSA
    arrancar: mejor una caída visible que sesiones falsificables."""
    import anyio

    from app import main

    inseguro = _mk(domain="dqr.example", jwt_secret="dev-insecure-jwt-secret")
    monkeypatch.setattr(main, "settings", inseguro)

    async def _run():
        async with main.lifespan(main.app):
            pass

    try:
        anyio.run(_run)
        assert False, "debería haber lanzado RuntimeError"
    except RuntimeError as e:
        assert "inseguros" in str(e).lower()


def test_lifespan_en_prod_con_secreto_corto_pero_propio_no_bloquea(monkeypatch):
    """Un secreto propio pero corto es débil, NO catastrófico: se avisa pero la
    producción en marcha NO se tira abajo (solo bloquea el valor de ejemplo)."""
    import anyio

    from app import main

    corto = _mk(domain="dqr.example", jwt_secret="corto", portal_token_secret="corto2",
                scheduler_enabled=False, emails_enabled=False, stripe_secret_key="")
    assert corto.blocking_secret_problems() == []  # nada catastrófico
    assert corto.insecure_secrets()                # pero sí hay avisos
    monkeypatch.setattr(main, "settings", corto)

    async def _run():
        async with main.lifespan(main.app):
            pass

    anyio.run(_run)  # no lanza


def test_lifespan_en_dev_solo_avisa(monkeypatch):
    """En dev (sin dominio) un secreto de ejemplo NO bloquea el arranque."""
    import anyio

    from app import main

    dev = _mk(domain="", jwt_secret="dev-insecure-jwt-secret",
              scheduler_enabled=False, emails_enabled=False, stripe_secret_key="")
    monkeypatch.setattr(main, "settings", dev)

    async def _run():
        async with main.lifespan(main.app):
            pass

    anyio.run(_run)  # no lanza


def test_cors_excluye_localhost_en_produccion():
    """En producción el único origen permitido es el dominio; en dev se añaden
    los localhost. Se prueba la misma lógica que arma `_cors_origins`."""
    def origins(s: Settings) -> list[str]:
        o = [s.public_base_url]
        if not s.is_production:
            o += ["http://localhost", "http://localhost:5173"]
        return o

    prod = _mk(domain="dqr.example")
    assert origins(prod) == ["https://dqr.example"]
    assert "http://localhost" not in origins(prod)

    dev = _mk(domain="", base_url="http://localhost")
    assert "http://localhost" in origins(dev)


def test_peticion_de_coach_distingue_token_valido():
    from app import main
    from app.security import create_access_token

    class _Req:
        def __init__(self, auth):
            self.headers = {"authorization": auth} if auth else {}

    assert main._peticion_de_coach(_Req(None)) is False
    assert main._peticion_de_coach(_Req("Bearer basura")) is False
    tok = create_access_token("coach1")
    assert main._peticion_de_coach(_Req(f"Bearer {tok}")) is True


# --------------------------------------------------------------------------- #
#  Integración (requieren PostgreSQL: TestClient levanta la app real)
# --------------------------------------------------------------------------- #
pytest_db = pytest.mark.skipif(not _db_available(), reason="Requiere PostgreSQL")


@pytest_db
def test_cabecera_nosniff_presente():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.headers.get("x-content-type-options") == "nosniff"


@pytest_db
def test_login_usuario_inexistente_devuelve_401_generico():
    """Usuario que no existe → 401 con el MISMO mensaje que contraseña mala
    (no se filtra si la cuenta existe)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        r = client.post("/api/auth/login",
                        json={"username": "no-existe-xyz", "password": "loquesea"})
        assert r.status_code == 401
        assert "incorrectas" in r.json()["detail"].lower()


def test_el_token_del_portal_no_acaba_en_los_logs():
    """El token del portal es una credencial PERMANENTE al historial clínico
    completo del cliente y viaja en la RUTA: el access log de uvicorn lo
    escribía en claro en cada línea, y esos logs se guardaban sin rotación en
    el VPS. Cualquiera con acceso a ellos entraba al portal de todos."""
    import logging

    from app.main import _FiltroTokens, enmascara_tokens

    assert enmascara_tokens("GET /api/p/AbC.123-xyz/state HTTP/1.1 200") == \
        "GET /api/p/***/state HTTP/1.1 200"
    assert enmascara_tokens("/api/clients/7?tab=anamnesis") == "/api/clients/7?tab=anamnesis"
    # El enlace de COBRO lleva el mismo token (es el que el coach manda por
    # WhatsApp) y se quedaba en claro aunque el del portal ya no.
    assert enmascara_tokens("GET /api/pay/AbC.123-xyz HTTP/1.1 302") == \
        "GET /api/pay/*** HTTP/1.1 302"
    # Y no se pasa de listo con rutas que solo EMPIEZAN por esas letras.
    assert enmascara_tokens("/api/payments/summary") == "/api/payments/summary"
    assert enmascara_tokens("/api/plans/12/document") == "/api/plans/12/document"

    registro = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/1.1" %d', ("1.2.3.4", "GET", "/api/p/SECRETO/diary", 200), None)
    _FiltroTokens().filter(registro)
    assert "SECRETO" not in (registro.getMessage())
