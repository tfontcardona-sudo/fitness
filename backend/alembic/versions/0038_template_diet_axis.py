"""plan_templates: eje DIETA del caso (comidas, patrón y foco).

Cada plantilla del pool sirve a los tres servicios (dieta, entrenamiento o
pack). Lo que diferencia una dieta de otra es el CASO: cuántas tomas, qué
patrón alimentario y en qué se centra. Se guarda en la plantilla para
construir su dieta de referencia y para que el coach lo vea en el listado.

Revision ID: 0038
Revises: 0037
"""
import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

COLUMNAS = [
    ("meals_per_day", sa.Column("meals_per_day", sa.Integer, nullable=True)),
    ("diet_pattern", sa.Column("diet_pattern", sa.String(20), nullable=True)),
    ("diet_focus", sa.Column("diet_focus", sa.String(200), nullable=True)),
]


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "plan_templates" not in insp.get_table_names():
        return  # 0037 la crea; en BD nueva create_all ya trae las columnas
    existentes = {c["name"] for c in insp.get_columns("plan_templates")}
    for nombre, col in COLUMNAS:
        if nombre not in existentes:
            op.add_column("plan_templates", col)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "plan_templates" not in insp.get_table_names():
        return
    existentes = {c["name"] for c in insp.get_columns("plan_templates")}
    for nombre, _ in COLUMNAS:
        if nombre in existentes:
            op.drop_column("plan_templates", nombre)
