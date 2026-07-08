"""0009: acceso del cliente al portal con usuario (email) y contraseña.

Añade a `clients`:
- `portal_password_hash`: hash bcrypt de la contraseña del portal (nulo hasta
  que se genera al enviar el acceso).
- `portal_access_sent_at`: cuándo se envió por email el acceso (para no
  reenviarlo solo y para que el coach vea el estado).

Idempotente: en una BD que ya las tenga no hace nada.
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "portal_password_hash" not in cols:
        op.add_column("clients", sa.Column("portal_password_hash", sa.String(255), nullable=True))
    if "portal_access_sent_at" not in cols:
        op.add_column("clients", sa.Column("portal_access_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    pass
