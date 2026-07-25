"""0029: aprendizaje continuo (§13) + desbloqueo progresivo (§12).

`plan_edits` (captura de ediciones del coach) y `segment_unlock` (estado de
desbloqueo por segmento). Idempotente.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    if "plan_edits" not in tables:
        op.create_table(
            "plan_edits",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("plan_id", sa.Integer, sa.ForeignKey("plans.id"), nullable=False),
            sa.Column("category", sa.String(30), nullable=False),
            sa.Column("field_path", sa.String(120), nullable=True),
            sa.Column("before_json", JSONB, nullable=True),
            sa.Column("after_json", JSONB, nullable=True),
            sa.Column("note", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_plan_edits_plan_id", "plan_edits", ["plan_id"])
        op.create_index("ix_plan_edits_category", "plan_edits", ["category"])
    if "segment_unlock" not in tables:
        op.create_table(
            "segment_unlock",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("segment", sa.String(80), nullable=False, unique=True),
            sa.Column("clean_streak", sa.Integer, nullable=False, server_default="0"),
            sa.Column("unlocked", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_segment_unlock_segment", "segment_unlock", ["segment"], unique=True)


def downgrade() -> None:
    pass
