"""0034: ronda diaria de WhatsApp (pool de 100 mensajes).

`whatsapp_rounds` (qué brief toca cada día) y `whatsapp_sends` (a quién se le
mandó ya hoy). Idempotente.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "whatsapp_rounds" not in tables:
        op.create_table(
            "whatsapp_rounds",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("round_date", sa.Date, nullable=False, unique=True),
            sa.Column("brief_index", sa.Integer, nullable=False),
            sa.Column("brief_key", sa.String(60), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_whatsapp_rounds_round_date", "whatsapp_rounds", ["round_date"])
    # Textos ya redactados de la ronda (cache: la IA escribe UNA vez al día por
    # cliente, no en cada apertura del panel). Idempotente sobre BD ya migrada.
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("whatsapp_rounds")}
    if "texts_json" not in cols:
        op.add_column("whatsapp_rounds", sa.Column("texts_json", JSONB, nullable=True))
    if "whatsapp_sends" not in tables:
        op.create_table(
            "whatsapp_sends",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("round_id", sa.Integer, sa.ForeignKey("whatsapp_rounds.id"), nullable=False),
            sa.Column("client_id", sa.Integer,
                      sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("text", sa.Text, nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("round_id", "client_id", name="uq_wa_send_round_client"),
        )
        op.create_index("ix_whatsapp_sends_round_id", "whatsapp_sends", ["round_id"])
        op.create_index("ix_whatsapp_sends_client_id", "whatsapp_sends", ["client_id"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "whatsapp_sends" in tables:
        op.drop_table("whatsapp_sends")
    if "whatsapp_rounds" in tables:
        op.drop_table("whatsapp_rounds")
