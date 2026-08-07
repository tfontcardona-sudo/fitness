"""billing_period a VARCHAR(12): cabe la periodicidad "oferta" (1 € → 120 €/mes).

Revision ID: 0035
Revises: 0034
"""
from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "clients", "billing_period",
        type_=sa.String(12), existing_type=sa.String(4),
        existing_nullable=False, existing_server_default=sa.text("'1m'"),
    )


def downgrade() -> None:
    # "oferta" (6 chars) no cabe en VARCHAR(4): sin este saneo, el ALTER falla
    # con "value too long" en cuanto exista un cliente de la oferta.
    op.execute("UPDATE clients SET billing_period = '1m' WHERE billing_period = 'oferta'")
    op.alter_column(
        "clients", "billing_period",
        type_=sa.String(4), existing_type=sa.String(12),
        existing_nullable=False, existing_server_default=sa.text("'1m'"),
    )
