"""Los productos recomendados, por MARCA.

"Recursos" del portal enseña el catálogo de productos del coach (suplementos,
material) a TODOS los clientes. Con dos negocios en la misma máquina eso es una
fuga visible para el cliente: quien entra por un centro de fitness vería los
enlaces de afiliado de la otra marca.

`brand_id` a NULL significa "para todas las marcas" (un producto genérico que
el coach quiera enseñar en las dos). Las filas que ya existían se sellan con la
marca original: eran de ella, y nadie ha decidido compartirlas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "brand_id" in _cols(insp, "recommended_products"):
        return
    op.add_column("recommended_products", sa.Column("brand_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_recommended_products_brand", "recommended_products",
                          "brand_config", ["brand_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_recommended_products_brand_id", "recommended_products", ["brand_id"])
    # La marca original = el primer perfil por id (el que existía antes del switch).
    bind.execute(sa.text(
        "UPDATE recommended_products SET brand_id ="
        " (SELECT id FROM brand_config ORDER BY id LIMIT 1)"
        " WHERE brand_id IS NULL"))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "brand_id" not in _cols(insp, "recommended_products"):
        return
    op.drop_index("ix_recommended_products_brand_id", table_name="recommended_products")
    op.drop_constraint("fk_recommended_products_brand", "recommended_products",
                       type_="foreignkey")
    op.drop_column("recommended_products", "brand_id")
