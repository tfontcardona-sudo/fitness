"""0033: planes nutri | train | full (antes start | full | pro).

Renombra los planes contratados: `start` (solo dieta) pasa a `nutri` y `pro`
(todo + contacto directo) pasa a `full`, porque el contacto por WhatsApp deja de
ser un extra de gama alta y está en los tres planes. `full` se queda igual.
`train` (solo entrenamiento) es nuevo y aún no tiene clientes. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE clients SET package_tier = 'nutri' WHERE package_tier = 'start'"))
    bind.execute(sa.text("UPDATE clients SET package_tier = 'full' WHERE package_tier = 'pro'"))
    # El default de columna apuntaba al plan viejo 'pro'.
    op.alter_column("clients", "package_tier", server_default=sa.text("'full'"))


def downgrade() -> None:
    bind = op.get_bind()
    # `nutri` vuelve a `start`. `full` NO se puede desdoblar en full/pro (se
    # perdió la distinción al fusionarlos), así que se queda como 'full'.
    bind.execute(sa.text("UPDATE clients SET package_tier = 'start' WHERE package_tier = 'nutri'"))
    bind.execute(sa.text("UPDATE clients SET package_tier = 'full' WHERE package_tier = 'train'"))
    op.alter_column("clients", "package_tier", server_default=sa.text("'pro'"))
