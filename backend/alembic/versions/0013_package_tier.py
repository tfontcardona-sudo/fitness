"""0013: paquete/plan contratado por el cliente.

`clients.package_tier`: start (solo dieta) | full (dieta+entreno) | pro (full +
contacto directo). Los clientes existentes quedan en 'pro' (el sistema completo
que ya usaban). Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "package_tier" not in cols:
        op.add_column(
            "clients",
            sa.Column(
                "package_tier",
                sa.String(10),
                nullable=False,
                server_default="pro",
            ),
        )


def downgrade() -> None:
    pass
