"""0017: remache de recursos — timestamps NOT NULL con default e índice garantizado.

La 0016 creaba `recommended_products` con created_at/updated_at anulables (en
contradicción con el modelo, que los declara NOT NULL) y el índice solo se creaba
si la tabla no existía (una BD creada por create_all se quedaba sin él). Este
remache alinea CUALQUIER instalación, venga de donde venga. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "recommended_products" not in insp.get_table_names():
        return  # la 0016 la creará en BDs aún más antiguas; ahí ya nace alineada

    cols = {c["name"]: c for c in insp.get_columns("recommended_products")}
    for col in ("created_at", "updated_at"):
        if cols[col]["nullable"]:
            op.execute(f"UPDATE recommended_products SET {col} = now() WHERE {col} IS NULL")
            op.alter_column(
                "recommended_products", col,
                nullable=False, server_default=sa.text("now()"),
            )

    idx = {ix["name"] for ix in insp.get_indexes("recommended_products")}
    if "ix_recommended_products_order" not in idx:
        op.create_index(
            "ix_recommended_products_order",
            "recommended_products",
            ["active", "sort_order", "id"],
        )


def downgrade() -> None:
    pass
