"""Perímetros iniciales de la anamnesis (cintura/cadera/brazo/muslo).

El PDF oficial los pide en la antropometría inicial y no había columna donde
guardarlos: la línea base corporal se perdía y el primer informe quincenal no
podía enseñar el delta de medidas (auditoría de ingesta, 27-08-2026).

Revision ID: 0041
Revises: 0040
"""
import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotente: la 0001 crea el esquema con `create_all` desde los modelos,
    # así que en una instalación NUEVA estas columnas ya nacen puestas y el
    # ALTER reventaba la cadena entera (el contenedor no llegaba a arrancar).
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    for nombre in ("initial_waist_cm", "initial_hip_cm", "initial_arm_cm", "initial_thigh_cm"):
        if nombre not in cols:
            op.add_column("clients", sa.Column(nombre, sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "initial_thigh_cm")
    op.drop_column("clients", "initial_arm_cm")
    op.drop_column("clients", "initial_hip_cm")
    op.drop_column("clients", "initial_waist_cm")
