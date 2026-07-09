"""0012: aviso de planificación nueva sin ver (para el badge de la PWA).

`clients.plan_notice_pending`: se pone a true al publicar/activar un plan y a
false cuando el cliente abre su rutina. Alimenta el badge del icono de la app
aunque el cliente NO haya aceptado notificaciones push. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("clients")}
    if "plan_notice_pending" not in cols:
        op.add_column(
            "clients",
            sa.Column(
                "plan_notice_pending",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    pass
