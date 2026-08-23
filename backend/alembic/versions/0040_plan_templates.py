"""Modelos de planificación reutilizables.

El coach puede congelar un plan como MODELO ("Planificación base"), darle
título, y usarlo como punto de partida para cualquier cliente sin gastar
créditos. Los números nunca viajan: al aplicarlo se recalculan para el
destino (services/plan_library.py).

Idempotente: comprueba la tabla antes de crearla.

Revision ID: 0040
Revises: 0039
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "plan_templates" in insp.get_table_names():
        return
    op.create_table(
        "plan_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("summary", sa.String(200), nullable=True),
        sa.Column("nutrition_json", JSONB(), nullable=True),
        sa.Column("training_json", JSONB(), nullable=True),
        sa.Column("education_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "plan_templates" in insp.get_table_names():
        op.drop_table("plan_templates")
