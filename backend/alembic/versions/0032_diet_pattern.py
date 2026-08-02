"""0032: patrón dietético ético/religioso del cliente (vegano, halal…).

El filtro `_DIET_PATTERN_FORBIDDEN` (guardrails/portion_solver) existía y estaba
probado, pero NO tenía fuente de datos: ningún campo del cliente lo alimentaba.
Con esta columna el patrón viaja a la generación (filter_foods + prompt), al
banco de emergencia, al Revisor 0 y a las alertas en vivo. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "diet_pattern" not in cols:
        op.add_column("clients", sa.Column("diet_pattern", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "diet_pattern")
