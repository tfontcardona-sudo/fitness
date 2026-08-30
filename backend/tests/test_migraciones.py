"""Las migraciones tienen que poder correr sobre una instalación NUEVA.

La 0001 crea el esquema con `Base.metadata.create_all()` desde los modelos, así
que una base de datos recién creada nace ya con TODAS las columnas de hoy. Por
eso cualquier migración posterior que añada una columna o una tabla debe
comprobar antes si existe: sin esa guarda, `alembic upgrade head` peta en una
instalación limpia y el contenedor no llega a arrancar (le pasó a la 0036 y a
la 0041, que dejaban un despliegue nuevo muerto).

Esta prueba es estática (no toca la BD): revisa el código de las migraciones.
"""

from __future__ import annotations

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
