"""0020: página pública de enlaces (Instagram) — foto de fondo + afiliación.

`brand_config.links_photo_path`: foto de fondo de la landing /dq.
`brand_config.partner_store_url` / `partner_discount_code`: tienda del partner
(ESN) y código de descuento del coach que se muestran en la landing.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("brand_config")}
    if "links_photo_path" not in cols:
        op.add_column("brand_config", sa.Column("links_photo_path", sa.String(500), nullable=True))
    if "partner_store_url" not in cols:
        op.add_column("brand_config", sa.Column("partner_store_url", sa.String(300), nullable=True))
    if "partner_discount_code" not in cols:
        op.add_column("brand_config", sa.Column("partner_discount_code", sa.String(40), nullable=True))


def downgrade() -> None:
    pass
