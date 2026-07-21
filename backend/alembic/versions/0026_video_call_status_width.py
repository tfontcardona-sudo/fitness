"""0026: ensancha video_calls.status a VARCHAR(20).

El nuevo flujo usa estados más descriptivos ("pending_manual" = 14 caracteres)
que no caben en el VARCHAR(12) original. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    col = {c["name"]: c for c in insp.get_columns("video_calls")}.get("status")
    # Solo altera si sigue siendo el ancho antiguo (evita trabajo redundante).
    length = getattr(col["type"], "length", None) if col else None
    if length is not None and length < 20:
        op.alter_column("video_calls", "status",
                        type_=sa.String(20), existing_nullable=False)


def downgrade() -> None:
    pass
