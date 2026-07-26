"""0031: eventos de uso de la IA (consumo en vivo del botón de créditos).

`ai_usage_events`: una fila por llamada a la IA con su coste real, para mostrar
el gasto de hoy / 30 días y estimar los planes que quedan. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ai_usage_events" not in set(insp.get_table_names()):
        op.create_table(
            "ai_usage_events",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("model", sa.String(80), nullable=False),
            sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
            sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_ai_usage_events_created_at", "ai_usage_events", ["created_at"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ai_usage_events" in set(insp.get_table_names()):
        op.drop_index("ix_ai_usage_events_created_at", table_name="ai_usage_events")
        op.drop_table("ai_usage_events")
