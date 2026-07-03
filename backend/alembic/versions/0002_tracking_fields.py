"""0002: seguimiento diario (pasos/saciedad/litros) + revisión quincenal completa.

Añade columnas a daily_logs y periods para reflejar los documentos de seguimiento
del coach (diario y revisión quincenal). Todas nullable → no rompe filas existentes.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_DAILY = [
    ("steps", sa.String(160)),
    ("satiety_1_10", sa.Float()),
    ("water_liters", sa.Float()),
]
_PERIOD = [
    ("closing_feelings_json", JSONB()),
    ("adherence_diet_0_10", sa.Integer()),
    ("adherence_training_0_10", sa.Integer()),
    ("free_meals_count", sa.Integer()),
    ("closing_changes", sa.Text()),
    ("closing_next_goal", sa.Text()),
]


def upgrade() -> None:
    for name, coltype in _DAILY:
        op.add_column("daily_logs", sa.Column(name, coltype, nullable=True))
    for name, coltype in _PERIOD:
        op.add_column("periods", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _ in _PERIOD:
        op.drop_column("periods", name)
    for name, _ in _DAILY:
        op.drop_column("daily_logs", name)
