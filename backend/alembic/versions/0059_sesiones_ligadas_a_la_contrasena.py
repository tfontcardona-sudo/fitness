"""Las sesiones del coach mueren al cambiar su contraseña.

`users.password_changed_at`: lo sella `seed_admins` cuando el `.env` trae una
contraseña distinta para un usuario que ya existe. `get_current_user` rechaza
todo token cuyo `iat` sea anterior. Sin esto, rotar SOLO la contraseña (mismo
usuario) dejaba abiertas durante 72 h las sesiones que ya estaban emitidas.

Nulo = nunca se ha rotado: ningún token se rechaza por esta vía.

Idempotente: una base VACÍA ya crea la columna con `create_all` al definirla
en `models.py` (mismo motivo que 0036/0041/0058).
"""
from alembic import op
import sqlalchemy as sa

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "password_changed_at" in {c["name"] for c in insp.get_columns("users")}:
        return
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "password_changed_at" in {c["name"] for c in insp.get_columns("users")}:
        op.drop_column("users", "password_changed_at")
