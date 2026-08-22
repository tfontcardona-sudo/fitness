"""Pagos: sello de anonimización (RGPD).

Un cobro cuya ficha se borró por RGPD conserva el dinero pero pierde a la
persona. Sin marcar, esas filas quedaban indistinguibles de un cobro HUÉRFANO
de verdad (uno que hay que investigar), así que el aviso de "cobros sin ficha"
se quedaba encendido para siempre y sin nada que hacer al respecto.

Idempotente: comprueba la columna antes de crearla.

Revision ID: 0039
Revises: 0038
"""
from alembic import op
import sqlalchemy as sa

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "anonymized_at" not in _cols(insp, "payments"):
        op.add_column("payments", sa.Column(
            "anonymized_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "anonymized_at" in _cols(insp, "payments"):
        op.drop_column("payments", "anonymized_at")
