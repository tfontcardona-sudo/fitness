"""Interruptor GLOBAL de mantenimiento.

Fila única (mismo patrón que `ai_credit_state`): cuando `maintenance_enabled`
está activo, TODO el acceso público —portales de cliente (`/api/p/*`), pagos y
compras (`/api/pay/*`), y la landing/catálogo/registro público
(`/api/public/*`: `/dq`, `/planes`, `/oferta`)— responde 503 con
`maintenance_message` en vez de ejecutar nada. El panel del coach (todo lo que
va detrás de login) y el webhook de Stripe NUNCA pasan por este interruptor:
el coach tiene que poder trabajar y volver a activarlo, y los cobros/bajas ya
en marcha no pueden perderse por estar en pausa. Ver `services/mantenimiento.py`.

Arranca SIEMPRE desactivado (`maintenance_enabled=False`): desplegar esta
migración no apaga nada por sí sola.

Idempotente: comprueba la tabla antes de crearla (una base VACÍA la crea ya
con `create_all` al definir `SystemState` en `models.py` — sin la guarda,
`alembic upgrade head` desde cero revienta con "relation already exists").
"""
from alembic import op
import sqlalchemy as sa

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "system_state" in insp.get_table_names():
        return
    op.create_table(
        "system_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("maintenance_message", sa.String(300), nullable=True),
        sa.Column("maintenance_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "system_state" in insp.get_table_names():
        op.drop_table("system_state")
