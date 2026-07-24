"""0028: base de datos de composición de alimentos (hardening §2).

Tabla `foods` con macros por 100 g, alérgenos y etiquetas (índices GIN), cotas de
ración y gramos por unidad práctica. Idempotente.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "foods" in insp.get_table_names():
        return
    op.create_table(
        "foods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("canonical_name", sa.String(120), nullable=False, unique=True),
        sa.Column("aliases", ARRAY(sa.String), nullable=True),
        sa.Column("group", sa.String(20), nullable=False),
        sa.Column("kcal", sa.Float, nullable=False),
        sa.Column("protein_g", sa.Float, nullable=False),
        sa.Column("carbs_g", sa.Float, nullable=False),
        sa.Column("fat_g", sa.Float, nullable=False),
        sa.Column("fiber_g", sa.Float, nullable=False, server_default="0"),
        sa.Column("allergens", ARRAY(sa.String), nullable=True),
        sa.Column("tags", ARRAY(sa.String), nullable=True),
        sa.Column("unit_grams", sa.Float, nullable=True),
        sa.Column("min_grams", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_grams", sa.Float, nullable=False, server_default="400"),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_foods_canonical_name", "foods", ["canonical_name"], unique=True)
    op.create_index("ix_foods_group", "foods", ["group"])
    op.create_index("ix_foods_archived", "foods", ["archived"])
    op.create_index("ix_foods_allergens", "foods", ["allergens"], postgresql_using="gin")
    op.create_index("ix_foods_tags", "foods", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    pass
