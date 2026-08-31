"""Arranque DESDE CERO: `alembic upgrade head` sobre una base vacía.

La suite siempre corre contra una base YA migrada, así que nadie comprobaba el
camino que de verdad importa el día malo: montar el sistema en una máquina
nueva (VPS perdido, restauración sin dump, otro ordenador). Ese camino estaba
ROTO —dos migraciones añadían columnas que 0001 ya crea con `create_all`, y
como Alembic corre toda la cadena en una transacción, la base quedaba vacía
(ni `alembic_version`) y el contenedor de la API en crashloop— y no se veía
porque en producción la cadena ya estaba sellada.
"""
import os
import uuid
import warnings

import pytest

warnings.filterwarnings("ignore")


def _puede_crear_bases() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        eng = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
        with eng.connect() as con:
            con.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _puede_crear_bases(),
                                reason="Requiere PostgreSQL con permiso de CREATE DATABASE")


def test_una_base_vacia_llega_hasta_la_ultima_migracion(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from app.config import settings

    nombre = f"fitness_migra_{uuid.uuid4().hex[:8]}"
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as con:
        con.execute(text(f'CREATE DATABASE "{nombre}"'))
    url = settings.database_url.rsplit("/", 1)[0] + "/" + nombre

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(raiz, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(raiz, "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    # `alembic/env.py` toma la URL de settings (no del .ini): se apunta ahí, que
    # es justo lo que hace el contenedor al arrancar.
    original = settings.database_url
    settings.database_url = url
    try:
        command.upgrade(cfg, "head")

        from alembic.script import ScriptDirectory

        head = ScriptDirectory.from_config(cfg).get_current_head()
        eng = create_engine(url)
        with eng.connect() as con:
            actual = con.execute(text("SELECT version_num FROM alembic_version")).scalar()
            # Y el esquema está de verdad ahí (no una base a medias).
            tablas = {r[0] for r in con.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
        assert actual == head
        assert {"clients", "plans", "periods", "daily_logs", "payments"} <= tablas
        eng.dispose()
    finally:
        settings.database_url = original
        with admin.connect() as con:
            con.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{nombre}'"))
            con.execute(text(f'DROP DATABASE IF EXISTS "{nombre}"'))


# ---------------------------------------------------------------------------
# La otra mitad, ESTÁTICA (no toca la base): que cada migración lleve su guarda.
# Viene de la sesión que trabajó esta misma tanda en paralelo. Las dos pruebas
# se complementan: la de arriba ejecuta la cadena entera sobre una base vacía y
# caza el fallo real; esta lee el código y caza al siguiente que se olvide.
# ---------------------------------------------------------------------------

import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"

# Operaciones que fallan si el objeto ya existe.
_CREADORAS = re.compile(
    r"op\.(add_column|create_table|create_index|create_unique_constraint)\("
)

# Formas válidas de asegurarse antes de crear.
_GUARDAS = ("inspect(", "IF NOT EXISTS", "get_columns", "get_table_names")


def _migraciones() -> list[Path]:
    return sorted(p for p in VERSIONS.glob("[0-9]*.py") if not p.name.startswith("0001"))


def test_hay_migraciones_que_revisar():
    assert len(_migraciones()) > 10, "no se encontraron las migraciones"


def test_toda_migracion_que_crea_algo_comprueba_antes_si_existe():
    sin_guarda: list[str] = []
    for f in _migraciones():
        src = f.read_text(encoding="utf-8")
        if _CREADORAS.search(src) and not any(g in src for g in _GUARDAS):
            sin_guarda.append(f.name)

    assert not sin_guarda, (
        "Estas migraciones crean columnas/tablas sin comprobar si ya existen; "
        "en una instalación NUEVA (donde la 0001 ya las creó desde los modelos) "
        "romperían `alembic upgrade head` y el arranque del contenedor: "
        + ", ".join(sin_guarda)
    )
