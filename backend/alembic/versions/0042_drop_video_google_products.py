"""Tira las tablas de las funciones retiradas: videollamadas, Google y tienda.

Sus modelos y endpoints se borraron con el recorte del producto (videollamadas
con Google Meet, tienda de productos recomendados). Las tablas quedaban vivas
sin nadie que las leyera ni escribiera.

Revision ID: 0042
Revises: 0041
"""
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS video_calls")
    op.execute("DROP TABLE IF EXISTS google_credentials")
    op.execute("DROP TABLE IF EXISTS recommended_products")


def downgrade() -> None:
    # Sin vuelta atrás: la funcionalidad ya no existe en el código.
    pass
