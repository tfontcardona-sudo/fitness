"""Pagos huérfanos: poder darlos por resueltos.

El resumen del libro avisa de "N sin ficha" y el feed sabe filtrarlos, pero no
había NINGUNA acción que apagara el aviso. `adopt_orphans` solo reasocia por
email y dentro de 30 días: un cobro de otro producto de la cuenta, o uno con el
email mal escrito en el checkout, se quedaba contando para siempre. Un aviso
que no se puede resolver deja de ser un aviso — se ignora, y con él se ignoran
los que sí importan.

Con este sello el coach puede decir "este no es de la asesoría" y el contador
lo respeta. Nullable: lo anterior queda tal cual.

Revision ID: 0043
Revises: 0042
"""
from alembic import op
import sqlalchemy as sa

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "dismissed_at" not in _cols(insp, "payments"):
        op.add_column("payments", sa.Column(
            "dismissed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "dismissed_at" in _cols(insp, "payments"):
        op.drop_column("payments", "dismissed_at")
