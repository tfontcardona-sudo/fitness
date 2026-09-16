"""La ESTRUCTURA de la planificación deja de estar clavada a la semana.

Hasta ahora toda rutina era una semana de lunes a domingo con un mesociclo de
4 semanas fijas: había que encajar a la persona dentro del split en vez de al
revés. Estas cinco columnas son lo que el coach decide POR CLIENTE:

  cycle_days           días que dura una vuelta al split (2-10). 7 = la semana
                       de siempre, con los días anclados al calendario.
  mesocycle_blocks     cuántas vueltas al ciclo dura el mesociclo (1-8).
  muscle_priority      grupos a los que se les da MÁS estímulo.
  muscle_deprioritized grupos que se mantienen (nunca por debajo del mínimo
                       productivo: mantener no es abandonar).
  review_days          cada cuántos días cierra su revisión (7-31).

TODAS nulables y TODAS a NULL para quien ya existe: NULL significa "lo de
siempre" (ciclo de 7, 4 bloques, revisión de 14 días), así que ni un cliente
en curso cambia de trato al desplegar esto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

# Idempotente a propósito: `tests/test_migraciones.py` corre la cadena entera
# desde una base VACÍA, y una migración que no se puede repetir deja el
# arranque del VPS a merced de un despliegue cortado a medias.
_COLUMNAS = (
    ("cycle_days", "INTEGER"),
    ("mesocycle_blocks", "INTEGER"),
    ("muscle_priority", "VARCHAR[]"),
    ("muscle_deprioritized", "VARCHAR[]"),
    ("review_days", "INTEGER"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for nombre, tipo in _COLUMNAS:
        bind.execute(sa.text(
            f"ALTER TABLE clients ADD COLUMN IF NOT EXISTS {nombre} {tipo}"))


def downgrade() -> None:
    bind = op.get_bind()
    for nombre, _ in _COLUMNAS:
        bind.execute(sa.text(f"ALTER TABLE clients DROP COLUMN IF EXISTS {nombre}"))
