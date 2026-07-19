"""0022: foto de fondo propia para la página pública de planes (/planes).

`brand_config.plans_photo_path` (media/…): segunda foto, independiente de la
de la landing /dq. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("brand_config")}
    if "plans_photo_path" not in cols:
        op.add_column("brand_config", sa.Column("plans_photo_path", sa.String(500), nullable=True))


def downgrade() -> None:
    pass
