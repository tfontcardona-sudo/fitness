"""El crédito agotado deja de ser una sorpresa, y el gasto pasa a ser el REAL.

Hasta aquí el saldo de créditos era una cuenta local: lo que el coach apuntaba
menos una ESTIMACIÓN (tokens × precio de tarifa). Dos huecos:

- Cuando el crédito se acababa de verdad, el sistema no lo decía: cada acción
  de IA fallaba con un 502 y había que leer el mensaje para enterarse. Ahora la
  propia API lo cuenta —el error dice «credit balance is too low»— y eso se
  sella en `sin_credito_desde` (+ `ultimo_error`), enciende el aviso del panel y
  se apaga SOLO en cuanto una llamada vuelve a funcionar.
- Anthropic sí publica el COSTE real por su Cost API (no el saldo). Con una
  clave de administración configurada, `spent_real_usd` guarda esa cifra desde
  la última recarga: el restante deja de ser una estimación y pasa a cuadrar con
  la factura. `spent_real_at` es cuándo se leyó y `spent_real_desde` desde
  cuándo cuenta (la última recarga).
"""
from alembic import op
import sqlalchemy as sa

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None

_COLS = (
    ("sin_credito_desde", sa.DateTime(timezone=True)),
    ("ultimo_error", sa.String(300)),
    ("spent_real_usd", sa.Float()),
    ("spent_real_at", sa.DateTime(timezone=True)),
    ("spent_real_desde", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ai_credit_state" not in set(insp.get_table_names()):
        return
    existentes = {c["name"] for c in insp.get_columns("ai_credit_state")}
    for nombre, tipo in _COLS:
        if nombre not in existentes:
            op.add_column("ai_credit_state", sa.Column(nombre, tipo, nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "ai_credit_state" not in set(insp.get_table_names()):
        return
    existentes = {c["name"] for c in insp.get_columns("ai_credit_state")}
    for nombre, _ in _COLS:
        if nombre in existentes:
            op.drop_column("ai_credit_state", nombre)
