"""0015: estado de pago del cliente (Stripe).

`clients.payment_status`: pending | paid. Se marca "paid" cuando Stripe confirma
el cobro. Los clientes YA existentes quedan como 'paid' (estaban activos antes de
enlazar Stripe). `clients.paid_at`: fecha del cobro. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "payment_status" not in cols:
        op.add_column(
            "clients",
            sa.Column("payment_status", sa.String(12), nullable=False,
                      server_default="paid"),
        )
    if "paid_at" not in cols:
        op.add_column("clients", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    pass
