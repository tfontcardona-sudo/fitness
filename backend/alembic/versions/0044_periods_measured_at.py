"""`periods.measured_at`: cuándo actualizó el cliente sus medidas.

La pantalla "Evolución" escribe peso y perímetros sobre el período abierto
tantas veces como el cliente se mida, pero no se guardaba CUÁNDO. El portal y
el panel las fechaban con el inicio del seguimiento — una fecha que puede ser
de hace meses — y ni el cliente ni el coach sabían si estaban al día.

Revision ID: 0044
Revises: 0043
"""
from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("periods", sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True))
    # Retroactivo: lo ya medido se fecha en el inicio del período (es lo único
    # que se sabe de ello) para no dejar la columna a NULL en datos existentes.
    op.execute(
        "UPDATE periods SET measured_at = starts_on::timestamptz "
        "WHERE closing_weight_kg IS NOT NULL OR closing_waist_cm IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("periods", "measured_at")
