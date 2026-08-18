"""Retira los campos del FORMULARIO DE CIERRE quincenal que ya no rellena nadie.

El cierre desapareció (mig. 0040): el cliente apunta su evolución cuando se
mide, desde el portal, sin cerrar nada. De aquel formulario solo sobreviven los
campos que la pantalla "Evolución" sigue enviando (peso, perímetros, sensaciones
y notas). El resto quedaba a NULL para siempre y, peor, el informe se lo pedía a
la IA como si existiera:

- `closing_rating`, `closing_hardest`, `closing_questions`, `closing_next_goal`,
  `free_meals_count`: preguntas del formulario de cierre.
- `adherence_diet_0_10` / `adherence_training_0_10`: auto-puntuación del
  cliente. La adherencia se deriva ahora de su registro diario, que es dato
  real y no una impresión.
- `coach_reviewed_at`: marcaba la revisión como vista (aviso "!" retirado).
- `closing_submitted_at` / `photos_confirmed`: recordatorio de fotos posterior
  al cierre.

Revision ID: 0043
Revises: 0042
"""
from alembic import op
import sqlalchemy as sa

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

_COLUMNAS = (
    "closing_rating", "closing_hardest", "closing_questions", "closing_next_goal",
    "free_meals_count", "adherence_diet_0_10", "adherence_training_0_10",
    "coach_reviewed_at", "closing_submitted_at", "photos_confirmed",
)


def upgrade() -> None:
    for col in _COLUMNAS:
        op.execute(f"ALTER TABLE periods DROP COLUMN IF EXISTS {col}")


def downgrade() -> None:
    with op.batch_alter_table("periods") as batch:
        batch.add_column(sa.Column("closing_rating", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("closing_hardest", sa.Text(), nullable=True))
        batch.add_column(sa.Column("closing_questions", sa.Text(), nullable=True))
        batch.add_column(sa.Column("closing_next_goal", sa.Text(), nullable=True))
        batch.add_column(sa.Column("free_meals_count", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("adherence_diet_0_10", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("adherence_training_0_10", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("coach_reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("closing_submitted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("photos_confirmed", sa.Boolean(), nullable=True,
                                   server_default=sa.text("false")))
