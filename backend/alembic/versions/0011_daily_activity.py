"""0011: nivel de actividad DIARIA del cliente (NEAT) para afinar el TDEE.

`clients.daily_activity_level`: sedentary|light|active|very_active. Nulo hasta
que se conoce (entonces el TDEE cae al mapeo por días de entreno). Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "daily_activity_level" not in cols:
        op.add_column("clients", sa.Column("daily_activity_level", sa.String(20), nullable=True))


def downgrade() -> None:
    pass
