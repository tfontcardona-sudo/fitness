"""0037: `payments` — libro de caja de Stripe (quién pagó, cuánto y cuándo).

Hasta ahora un cobro solo dejaba `clients.payment_status='paid'` + `paid_at`
(sobrescrito en cada pago, sin importe) y una fila de auditoría sin cifra. Esta
tabla guarda cada MOVIMIENTO tal cual lo dio Stripe — cobro, cobro fallido y
devolución — con importe, moneda y fecha reales, para el feed de pagos del panel.

`seen_at` (NULL = no leído) alimenta el badge tipo app de banco.
Idempotente: se puede reejecutar sin efectos.
"""
import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "payments" in set(insp.get_table_names()):
        return
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stripe_object_id", sa.String(80), nullable=False),
        sa.Column("stripe_event_id", sa.String(80), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="eur"),
        sa.Column("livemode", sa.Boolean, nullable=False, server_default=sa.text("true")),
        # SET NULL: el borrado RGPD de una ficha no puede tumbar el commit ni
        # borrar el movimiento (el endpoint además anonimiza nombre y email).
        sa.Column("client_id", sa.Integer,
                  sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(160), nullable=True),
        sa.Column("customer_email", sa.String(160), nullable=True),
        sa.Column("tier", sa.String(10), nullable=True),
        sa.Column("billing_period", sa.String(12), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        # La idempotencia del libro: el mismo objeto de Stripe en el mismo estado
        # no se anota dos veces (reintento de webhook o sincronización). Va por
        # (objeto, estado) porque una factura puede fallar y cobrarse después:
        # son dos movimientos distintos de la misma factura.
        sa.UniqueConstraint("stripe_object_id", "status", name="uq_payment_object_status"),
    )
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"])
    op.create_index("ix_payments_client_id", "payments", ["client_id"])
    op.create_index("ix_payments_stripe_object_id", "payments", ["stripe_object_id"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "payments" not in set(insp.get_table_names()):
        return
    op.drop_index("ix_payments_stripe_object_id", table_name="payments")
    op.drop_index("ix_payments_client_id", table_name="payments")
    op.drop_index("ix_payments_paid_at", table_name="payments")
    op.drop_table("payments")
