"""Retira la ronda diaria de WhatsApp (tablas whatsapp_sends / whatsapp_rounds).

Esta instancia entrega TODO por email y no usa la ronda asistida de WhatsApp,
así que las dos tablas quedaban muertas. Se borran para que el esquema refleje
el producto real.

Revision ID: 0039
Revises: 0038
"""
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # El orden importa: `whatsapp_sends` tiene FK a `whatsapp_rounds`.
    op.execute("DROP TABLE IF EXISTS whatsapp_sends")
    op.execute("DROP TABLE IF EXISTS whatsapp_rounds")


def downgrade() -> None:
    # Sin vuelta atrás: la funcionalidad ya no existe en el código.
    pass
