"""0025: recordatorio de fotos de progreso tras la revisión quincenal.

Dos columnas en `periods`:
- `closing_submitted_at`: cuándo envió el cliente la revisión (para recordar las
  fotos ~15 min después y luego cada 3 h hasta que confirme).
- `photos_confirmed`: el cliente confirmó en el portal que envió sus fotos al
  coach; mientras sea false (tras cerrar), se le recuerda.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("periods")}

    if "closing_submitted_at" not in cols:
        op.add_column("periods",
                      sa.Column("closing_submitted_at", sa.DateTime(timezone=True), nullable=True))
    if "photos_confirmed" not in cols:
        op.add_column("periods",
                      sa.Column("photos_confirmed", sa.Boolean, nullable=False,
                                server_default=sa.text("false")))


def downgrade() -> None:
    for col in ("photos_confirmed", "closing_submitted_at"):
        try:
            op.drop_column("periods", col)
        except Exception:
            pass
