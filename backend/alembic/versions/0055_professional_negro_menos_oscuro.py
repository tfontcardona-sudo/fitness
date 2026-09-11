"""Professional: un negro menos oscuro, también en lo que se imprime en negro.

El dueño, tras probarlo: "que sea un tono de negro menos oscuro y más claro".
El fondo casi puro (#0B0B0B) subía de tono en el CSS del frontend
(`--pf-fondo`, ver `index.css`) — este cambio es su reflejo en lo que el
BACKEND pinta con fondo oscuro de verdad: los emails (`email_templates.py`
usa `brand.color_bg` como fondo de la plantilla). `color_secondary` (#161616)
NO se toca: no es un fondo de página, es el color de un botón con texto en
blanco encima (contraste altísimo, sin problema), y es el que reparte
`coloresDeMarca()` hacia el oro claro en toda la interfaz — cambiarlo sin que
lo pida el dueño desharía ese reparto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE brand_config SET color_bg = '#151515' "
                "WHERE slug = 'professional-fitness'"))


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("UPDATE brand_config SET color_bg = '#0B0B0B' "
                "WHERE slug = 'professional-fitness'"))
