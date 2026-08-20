"""Pagos: comisión de Stripe + payment_intent; clientes: recordatorio de renovación.

- payments.fee_cents: la comisión que Stripe se queda de cada cobro (best-effort,
  NULL si no se pudo consultar). Permite mostrar el NETO real al coach.
- payments.payment_intent: el pi_… del cobro. Ata entre sí checkout/factura/cargo/
  devolución aunque la ficha del cliente se haya borrado (RGPD): la pertenencia de
  un cargo ya no depende solo del email.
- clients.renewal_reminder_sent_at: sello del email de renovación enviado AL
  CLIENTE. Se envía UNA vez por ciclo pagado (se compara contra paid_at).

Idempotente: comprueba las columnas antes de crearlas.

Revision ID: 0038
Revises: 0037
"""
from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    pagos = _cols(insp, "payments")
    if "fee_cents" not in pagos:
        op.add_column("payments", sa.Column("fee_cents", sa.Integer(), nullable=True))
    if "payment_intent" not in pagos:
        op.add_column("payments", sa.Column("payment_intent", sa.String(80), nullable=True))
        op.create_index("ix_payments_payment_intent", "payments", ["payment_intent"])
    clientes = _cols(insp, "clients")
    if "renewal_reminder_sent_at" not in clientes:
        op.add_column("clients", sa.Column(
            "renewal_reminder_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "renewal_reminder_sent_at" in _cols(insp, "clients"):
        op.drop_column("clients", "renewal_reminder_sent_at")
    pagos = _cols(insp, "payments")
    if "payment_intent" in pagos:
        op.drop_index("ix_payments_payment_intent", table_name="payments")
        op.drop_column("payments", "payment_intent")
    if "fee_cents" in pagos:
        op.drop_column("payments", "fee_cents")
