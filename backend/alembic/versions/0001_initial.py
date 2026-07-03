"""Migración inicial: crea todas las tablas desde Base.metadata.

Decisión declarada: la migración 0001 usa create_all sobre los modelos como
única fuente de verdad (cero riesgo de divergencia modelo↔migración). Las
migraciones siguientes se autogeneran con `alembic revision --autogenerate`.
"""
from alembic import op

from app.db import Base
import app.models  # noqa: F401 — registra todas las tablas en Base.metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
