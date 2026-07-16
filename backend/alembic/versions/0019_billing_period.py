"""0019: duración contratada del plan (mensual/trimestral/semestral).

`clients.billing_period`: 1m | 3m | 6m. Decide qué precio de Stripe usa el
enlace de pago del cliente. Los clientes existentes quedan en '1m' (mensual).
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "billing_period" not in cols:
        op.add_column(
            "clients",
            sa.Column("billing_period", sa.String(4), nullable=False,
                      server_default="1m"),
        )


def downgrade() -> None:
    pass
