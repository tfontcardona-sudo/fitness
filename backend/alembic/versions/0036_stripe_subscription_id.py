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
    # Guarda de idempotencia: en una base NUEVA, 0001 crea el esquema
    # completo con `create_all`, así que estas columnas YA existen y el
    # add_column reventaba — y como Alembic corre toda la cadena en una
    # transacción, la base quedaba VACÍA (ni alembic_version) y el
    # contenedor en crashloop. Sin esto no había forma de arrancar de cero
    # ni de recuperarse ante un desastre.
    insp = sa.inspect(op.get_bind())
    existentes = {c["name"] for c in insp.get_columns("clients")}
    if "stripe_subscription_id" not in existentes:
        op.add_column("clients", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "stripe_subscription_id")
