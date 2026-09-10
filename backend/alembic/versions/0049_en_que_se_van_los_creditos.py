"""EN QUÉ se gastan los créditos, y el libro de recargas.

`ai_usage_events` guardaba modelo, tokens y coste: se sabía CUÁNTO se gasta,
nunca EN QUÉ. Con eso el coach no puede decidir nada — si el mes se le fue en
generar planes, en leer anamnesis o en el panel de revisión son tres
conclusiones distintas y tres acciones distintas.

- `purpose`: para qué era la llamada (plan, comidas, anamnesis, revisión,
  informe quincenal…). Lo pone el propio sistema al hacerla.
- `client_id`: de quién era, cuando aplica. Con `ON DELETE SET NULL`: la baja
  RGPD borra al cliente y el apunte contable sobrevive sin su nombre.

Y `ai_credit_topups`: cada recarga que el coach paga. Anthropic NO expone el
saldo por API, así que el sistema no puede leerlo solo; lo que sí puede es
sumar lo que se paga y restar lo que se gasta, que es lo que evita la cuenta a
mano de "tenía 12, he metido 50, pongo 62".
"""
from alembic import op
import sqlalchemy as sa

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def _cols(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def _tablas(insp) -> set[str]:
    return set(insp.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols = _cols(insp, "ai_usage_events")
    if "purpose" not in cols:
        op.add_column("ai_usage_events", sa.Column("purpose", sa.String(24), nullable=True))
        op.create_index("ix_ai_usage_events_purpose", "ai_usage_events", ["purpose"])
    if "client_id" not in cols:
        op.add_column("ai_usage_events", sa.Column("client_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_ai_usage_events_client", "ai_usage_events",
                              "clients", ["client_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_ai_usage_events_client_id", "ai_usage_events", ["client_id"])

    if "ai_credit_topups" not in _tablas(insp):
        op.create_table(
            "ai_credit_topups",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("amount_usd", sa.Float(), nullable=False),
            # El saldo que quedaba ANTES de meter esta recarga: sin él, el
            # libro no cuadra si el coach corrige el saldo a mano por su cuenta.
            sa.Column("balance_before_usd", sa.Float(), nullable=True),
            sa.Column("note", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_ai_credit_topups_created_at", "ai_credit_topups", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "ai_credit_topups" in _tablas(insp):
        op.drop_index("ix_ai_credit_topups_created_at", table_name="ai_credit_topups")
        op.drop_table("ai_credit_topups")
    cols = _cols(insp, "ai_usage_events")
    if "client_id" in cols:
        op.drop_index("ix_ai_usage_events_client_id", table_name="ai_usage_events")
        op.drop_constraint("fk_ai_usage_events_client", "ai_usage_events", type_="foreignkey")
        op.drop_column("ai_usage_events", "client_id")
    if "purpose" in cols:
        op.drop_index("ix_ai_usage_events_purpose", table_name="ai_usage_events")
        op.drop_column("ai_usage_events", "purpose")
