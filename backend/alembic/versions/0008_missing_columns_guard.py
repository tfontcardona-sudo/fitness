"""0008: red de seguridad para columnas que solo existían vía create_all.

`plans.published_at`, `clients.strict_free_meal_enabled` y
`daily_logs.option_feedback_json` nacieron en el modelo sin ALTER propio: una
BD cuyo 0001 fuera anterior a esas columnas quedaría sin ellas y romperían la
activación del plan, las comidas de HOY y el upsert del diario. Idempotente:
en BD al día no hace nada.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    plan_cols = {c["name"] for c in insp.get_columns("plans")}
    if "published_at" not in plan_cols:
        op.add_column("plans", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    client_cols = {c["name"] for c in insp.get_columns("clients")}
    if "strict_free_meal_enabled" not in client_cols:
        op.add_column(
            "clients",
            sa.Column("strict_free_meal_enabled", sa.Boolean(), nullable=False,
                      server_default=sa.false()),
        )
    log_cols = {c["name"] for c in insp.get_columns("daily_logs")}
    if "option_feedback_json" not in log_cols:
        from sqlalchemy.dialects.postgresql import JSONB

        op.add_column("daily_logs", sa.Column("option_feedback_json", JSONB(), nullable=True))


def downgrade() -> None:
    pass
