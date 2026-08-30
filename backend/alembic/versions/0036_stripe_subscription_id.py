"""clients.stripe_subscription_id: la suscripción de la oferta, anclada a la ficha.

Permite (1) no crear una SEGUNDA suscripción con el cupón de 1 € al reabrir el
enlace de pago tras un impago (se manda a la factura abierta de la suscripción
existente), y (2) procesar customer.subscription.deleted aunque falte metadata.

Revision ID: 0036
Revises: 0035
"""
from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotente: la 0001 crea el esquema con `create_all` desde los modelos,
    # así que en una instalación NUEVA la columna ya nace puesta y este ALTER
    # reventaba la cadena entera (el contenedor no llegaba a arrancar).
    insp = sa.inspect(op.get_bind())
    if "stripe_subscription_id" not in {c["name"] for c in insp.get_columns("clients")}:
        op.add_column("clients", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "stripe_subscription_id")
