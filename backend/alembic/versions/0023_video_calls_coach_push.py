"""0023: videollamadas quincenales (Pro) + push del coach + enlace de reservas.

- `video_calls`: ciclo de la videollamada de revisión de los clientes Pro.
- `push_subscriptions.client_id` pasa a NULLABLE y se añade `is_coach`: los
  dispositivos del COACH también reciben push (resumen de alertas/pendientes).
- `brand_config.meet_url`: enlace de reservas (Google Calendar/Meet) del coach.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "video_calls" not in insp.get_table_names():
        op.create_table(
            "video_calls",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id"), nullable=False, index=True),
            sa.Column("period_index", sa.Integer, nullable=False),
            sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
            sa.Column("scheduled_for", sa.Date, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("client_id", "period_index"),
        )

    push_cols = {c["name"]: c for c in insp.get_columns("push_subscriptions")}
    if "is_coach" not in push_cols:
        op.add_column("push_subscriptions",
                      sa.Column("is_coach", sa.Boolean, nullable=False, server_default="false"))
    if not push_cols.get("client_id", {}).get("nullable", True):
        op.alter_column("push_subscriptions", "client_id", nullable=True)

    brand_cols = {c["name"] for c in insp.get_columns("brand_config")}
    if "meet_url" not in brand_cols:
        op.add_column("brand_config", sa.Column("meet_url", sa.String(300), nullable=True))


def downgrade() -> None:
    pass
