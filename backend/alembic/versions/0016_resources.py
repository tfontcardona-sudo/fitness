"""0016: recursos del portal — productos recomendados + imagen de ejercicio.

- `recommended_products`: catálogo único (single-tenant) que el coach gestiona y
  que el cliente ve en la sección "Recursos" del portal (título + imagen + enlace).
- `exercises.image_url`: miniatura del ejercicio para esa misma sección (si falta
  y el vídeo es de YouTube, la portada se deriva sola).

Idempotente: comprueba existencia antes de crear/añadir (mismo criterio que las
migraciones anteriores).
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "image_url" not in {c["name"] for c in insp.get_columns("exercises")}:
        op.add_column("exercises", sa.Column("image_url", sa.String(500), nullable=True))

    if "recommended_products" not in insp.get_table_names():
        op.create_table(
            "recommended_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("description", sa.String(300), nullable=True),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("category", sa.String(20), nullable=False, server_default="suplemento"),
            sa.Column("image_path", sa.String(500), nullable=True),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_recommended_products_order",
            "recommended_products",
            ["active", "sort_order", "id"],
        )


def downgrade() -> None:
    pass
