"""0014: motivo del fallo en el registro de emails.

`email_log.error`: guarda la causa cuando un correo no sale (auth de Gmail
rechazada, conexión, SMTP sin configurar…) para diagnosticar la entrega sin
mirar los logs del contenedor. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("email_log")}
    if "error" not in cols:
        op.add_column("email_log", sa.Column("error", sa.String(500), nullable=True))


def downgrade() -> None:
    pass
