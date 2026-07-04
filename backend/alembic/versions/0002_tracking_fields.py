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


def _existing_columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    # Idempotente: 0001 hace create_all desde los modelos ACTUALES, así que en
    # una BD nueva estas columnas ya existen; solo se añaden si faltan (BDs
    # antiguas que migran de verdad).
    daily_cols = _existing_columns("daily_logs")
    for name, coltype in _DAILY:
        if name not in daily_cols:
            op.add_column("daily_logs", sa.Column(name, coltype, nullable=True))
    period_cols = _existing_columns("periods")
    for name, coltype in _PERIOD:
        if name not in period_cols:
            op.add_column("periods", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _ in _PERIOD:
        op.drop_column("periods", name)
    for name, _ in _DAILY:
        op.drop_column("daily_logs", name)
