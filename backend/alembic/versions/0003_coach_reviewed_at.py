"""0003: periods.coach_reviewed_at — marca cuándo el coach vio la revisión.

Apaga el aviso "!" de la lista de clientes en cuanto el coach abre Seguimiento.
Nullable → no rompe filas existentes.
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("periods", sa.Column("coach_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("periods", "coach_reviewed_at")
