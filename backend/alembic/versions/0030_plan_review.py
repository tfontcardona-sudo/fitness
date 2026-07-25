"""0030: panel de supervisión (§9) — resultado de la revisión por plan.

`plans.review_json`: color del semáforo, ICP, hallazgos y si se escaló, para que
el coach vea la confianza del plan. Idempotente.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("plans")}
    if "review_json" not in cols:
        op.add_column("plans", sa.Column("review_json", JSONB, nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("plans")}
    if "review_json" in cols:
        op.drop_column("plans", "review_json")
