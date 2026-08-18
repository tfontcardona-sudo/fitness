"""Retira la oferta de captación (1 € el primer mes → suscripción).

Esta marca vende TRES servicios de PAGO ÚNICO: no hay suscripciones ni
promoción de captación. Se limpia lo que quedaba de esa maquinaria:

- `clients.billing_period = 'oferta'` ya no es un valor válido → pasa a 'unico'.
- `clients.stripe_subscription_id` solo servía para anclar la suscripción de la
  oferta al cliente; sin suscripciones, la columna sobra.

Revision ID: 0041
Revises: 0040
"""
from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE clients SET billing_period = 'unico' WHERE billing_period = 'oferta'")
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("stripe_subscription_id")


def downgrade() -> None:
    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("stripe_subscription_id", sa.String(64), nullable=True))
