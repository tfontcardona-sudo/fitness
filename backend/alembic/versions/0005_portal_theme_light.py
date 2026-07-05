"""0005: brand_config.portal_theme 'dark' → 'light' (normalización una vez).

Hasta ahora el portal SIEMPRE se renderizaba crema (claro): el CSS ignoraba
portal_theme, aunque el default del modelo era 'dark'. Al implementar el tema
oscuro "iron obsidiana" (§8.2), honrar el valor guardado habría cambiado de
golpe el aspecto de portales existentes. Esta migración conserva lo que el
cliente VE (crema); el coach activa el oscuro desde Marca cuando quiera.
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # En una BD nueva no hay filas → no-op. En una existente, ningún 'dark'
    # guardado fue una elección visible (el tema nunca se aplicó).
    op.execute(
        sa.text("UPDATE brand_config SET portal_theme = 'light' WHERE portal_theme = 'dark'")
    )


def downgrade() -> None:
    # Sin vuelta atrás con sentido: no sabemos qué filas eran 'dark' antes.
    pass
