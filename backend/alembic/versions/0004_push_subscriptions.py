"""0004: push_subscriptions — dispositivos suscritos a Web Push del portal.

Una fila por dispositivo (endpoint único). Se borra cuando el servicio de push
responde 404/410 (suscripción caducada o revocada por el usuario).
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotente: en una BD nueva, 0001 (create_all) ya crea esta tabla.
    insp = sa.inspect(op.get_bind())
    if "push_subscriptions" in insp.get_table_names():
        return
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index("ix_push_subscriptions_client_id", "push_subscriptions", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_client_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
