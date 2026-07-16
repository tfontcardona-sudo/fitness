"""0018: código de descuento por producto recomendado (afiliación de marca).

`recommended_products.discount_code`: el coach lo configura (p. ej. el código de
ESN) y el cliente lo ve destacado y copiable en su portal, para usarlo al pagar
en la web de la marca. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("recommended_products")}
    if "discount_code" not in cols:
        op.add_column(
            "recommended_products",
            sa.Column("discount_code", sa.String(40), nullable=True),
        )


def downgrade() -> None:
    pass
