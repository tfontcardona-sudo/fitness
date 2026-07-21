"""0024: saldo local de créditos de la API de Anthropic.

`ai_credit_state` (fila única): el coach apunta el saldo al recargar y cada
llamada a la IA descuenta su coste estimado. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ai_credit_state" not in insp.get_table_names():
        op.create_table(
            "ai_credit_state",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("balance_usd", sa.Float, nullable=True),
            sa.Column("spent_usd", sa.Float, nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    pass
