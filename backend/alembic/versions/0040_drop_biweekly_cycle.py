"""Retira el ciclo quincenal: estado `review_pending` y períodos cerrados.

Esta instancia trabaja con SEGUIMIENTO CONTINUO: el período no vence, el
cliente no "cierra" nada y el informe se pone al día encima. Los estados y
períodos que solo existían para el ciclo de 14 días quedaban muertos:

- `clients.status = 'review_pending'` (y el legado 'awaiting_feedback') ya no
  los asigna nadie; un cliente ahí se quedaría colgado sin salida → pasan a
  'active'.
- `periods.status` 'closed'/'analyzed' tampoco los escribe ya nadie. Se dejan
  TAL CUAL: son historia real de los períodos que sí se cerraron y el panel los
  sigue mostrando; solo se deja de producirlos.

Revision ID: 0040
Revises: 0039
"""
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE clients SET status = 'active' "
        "WHERE status IN ('review_pending', 'awaiting_feedback')"
    )


def downgrade() -> None:
    # Sin vuelta atrás: no se puede saber qué clientes estaban esperando
    # revisión, y el estado ya no existe en el código.
    pass
