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
    # Idempotente: en una BD nueva, 0001 (create_all) ya trae la columna.
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("periods")}
    if "coach_reviewed_at" not in cols:
        op.add_column("periods", sa.Column("coach_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("periods", "coach_reviewed_at")
