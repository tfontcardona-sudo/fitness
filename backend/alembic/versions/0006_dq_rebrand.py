"""0006: rebrand DQ — azul (#2E5E8C) + naranja (#E8833A) + fondo azul noche.

El coach pidió cambiar la identidad de la web y el portal a los colores de la
marca DQ (azul y naranja sobre crema suave / azul noche). Se actualiza la fila
de brand_config para que la app, el portal, los emails y el manifest PWA usen
la paleta nueva sin pasar por la página de Marca (que sigue permitiendo
personalizarla después).
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # En una BD nueva no hay filas → no-op (los defaults del modelo ya son estos).
    op.execute(sa.text(
        "UPDATE brand_config SET color_primary = '#E8833A', "
        "color_secondary = '#2E5E8C', color_bg = '#0B111C'"
    ))


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE brand_config SET color_primary = '#6EE7B7', "
        "color_secondary = '#34D399', color_bg = '#0A0A0F'"
    ))
