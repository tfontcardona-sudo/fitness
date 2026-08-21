"""Las migraciones tienen que correr de verdad, en los DOS caminos posibles.

Esto faltaba y salió caro: una migración que añadía una columna que la 0001 ya
creaba dejó la API en bucle de reinicio en una instalación nueva
("column measured_at already exists"), y otra borraba una columna que en una
base de datos nueva no existía. La suite pasaba igual porque los tests corren
sobre una base de datos YA migrada: nadie ejecutaba la cadena entera.

Los dos caminos que hay que cubrir:

  · DE CERO   — instalación nueva. Ojo: la 0001 hace `create_all` desde los
                modelos ACTUALES, así que las tablas nacen con las columnas de
                HOY y las migraciones posteriores tienen que ser idempotentes.
  · EN DOS    — actualización real: parar a mitad de camino y seguir, que es lo
                que le pasa a una instalación que llevaba tiempo sin tocarse.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parent.parent


def _db_url() -> str | None:
    return os.environ.get("DATABASE_URL")


pytestmark = pytest.mark.skipif(not _db_url(), reason="Requiere PostgreSQL")


# Alembic no trae `__main__.py`, así que `python -m alembic` no arranca; y un
# `alembic` a secas dependería del PATH, que no tiene por qué ser el mismo
# intérprete con el que corre pytest (pasó: la suite verde con el venv activado
# y roja llamando a venv/bin/python directamente). Se entra por la API pública.
_ARRANQUE = "import sys; from alembic.config import main; main(argv=sys.argv[1:])"


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    entorno = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-c", _ARRANQUE, *args],
        cwd=BACKEND, env=entorno, capture_output=True, text=True,
    )


def _cambiar_bd(url: str, nombre: str) -> str:
    """Misma URL apuntando a otra base de datos.

    A mano y no con make_url().render_as_string(): ese codifica el `/` del
    parámetro ?host=/var/run/postgresql como %2F, y alembic lee la URL desde
    alembic.ini, donde configparser interpreta el % como interpolación y casca.
    """
    base, _, query = url.partition("?")
    base = base.rsplit("/", 1)[0] + "/" + nombre
    return f"{base}?{query}" if query else base


def _con_base_vacia():
    """Crea una base de datos temporal y la borra al terminar."""
    nombre = f"mig_{uuid.uuid4().hex[:10]}"
    motor = create_engine(_cambiar_bd(_db_url(), "postgres"), isolation_level="AUTOCOMMIT")
    with motor.connect() as c:
        c.execute(text(f'CREATE DATABASE "{nombre}"'))
    return nombre, _cambiar_bd(_db_url(), nombre), motor


def _tirar(motor, nombre: str) -> None:
    with motor.connect() as c:
        c.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{nombre}' AND pid <> pg_backend_pid()"))
        c.execute(text(f'DROP DATABASE IF EXISTS "{nombre}"'))


def test_migra_de_cero_hasta_head():
    """Instalación NUEVA: de una base vacía a la última versión, sin errores."""
    nombre, url, motor = _con_base_vacia()
    try:
        r = _alembic(url, "upgrade", "head")
        assert r.returncode == 0, f"la cadena de migraciones falla de cero:\n{r.stderr[-3000:]}"

        # Y el esquema queda utilizable: la app puede leer sus tablas clave.
        e = create_engine(url)
        with e.connect() as c:
            for tabla in ("clients", "plans", "periods", "daily_logs", "exercises",
                          "plan_templates", "brand_config"):
                c.execute(text(f"SELECT 1 FROM {tabla} LIMIT 1"))
            # La columna del recorte tiene que estar UNA vez, ni cero ni dos.
            n = c.execute(text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name='periods' AND column_name='measured_at'")).scalar()
            assert n == 1
        e.dispose()
    finally:
        _tirar(motor, nombre)


def test_migra_en_dos_tramos_como_una_instalacion_vieja():
    """ACTUALIZACIÓN: una instalación parada en una versión antigua tiene que
    poder ponerse al día sin tocar nada a mano."""
    nombre, url, motor = _con_base_vacia()
    try:
        r = _alembic(url, "upgrade", "0038")
        assert r.returncode == 0, f"no llega a 0038:\n{r.stderr[-2000:]}"

        r = _alembic(url, "upgrade", "head")
        assert r.returncode == 0, f"no sabe actualizarse desde 0038:\n{r.stderr[-3000:]}"
    finally:
        _tirar(motor, nombre)
