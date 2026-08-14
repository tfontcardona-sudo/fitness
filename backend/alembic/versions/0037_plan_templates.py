"""plan_templates: pool de rutinas/planificaciones por carpetas.

La biblioteca de plantillas del coach: rutinas sembradas de fábrica (20 por
carpeta), subidas (importadas de documentos externos y re-maquetadas a la marca)
o creadas a mano. "Usar con un cliente" copia la plantilla como Plan borrador.

Revision ID: 0037
Revises: 0036
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotente: 0001 hace create_all desde los modelos actuales, así que en
    # una BD NUEVA la tabla ya existe; solo se crea si falta (BDs que migran).
    insp = sa.inspect(op.get_bind())
    if "plan_templates" in insp.get_table_names():
        return
    op.create_table(
        "plan_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category", sa.String(40), nullable=False, index=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("case_note", sa.Text, nullable=True),
        sa.Column("goal_type", sa.String(30), nullable=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("days_per_week", sa.Integer, nullable=True),
        sa.Column("training_place", sa.String(20), nullable=True),
        sa.Column("training_json", JSONB, nullable=True),
        sa.Column("nutrition_json", JSONB, nullable=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("plan_templates")
