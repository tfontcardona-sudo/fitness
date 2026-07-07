"""0007: etapa del objetivo + objetivo archivado en cada plan.

- clients.goal_started_on: cuándo empezó el objetivo actual (alerta 45 días).
- clients.goal_review_snoozed_on: "mantener objetivo" pospone la alerta.
- plans.goal_type: snapshot del objetivo que servía ese plan (para el archivo
  de planificaciones anteriores con su título y duración).
Nullable → no rompe filas existentes. Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    client_cols = {c["name"] for c in insp.get_columns("clients")}
    if "goal_started_on" not in client_cols:
        op.add_column("clients", sa.Column("goal_started_on", sa.Date(), nullable=True))
    if "goal_review_snoozed_on" not in client_cols:
        op.add_column("clients", sa.Column("goal_review_snoozed_on", sa.Date(), nullable=True))
    plan_cols = {c["name"] for c in insp.get_columns("plans")}
    if "goal_type" not in plan_cols:
        op.add_column("plans", sa.Column("goal_type", sa.String(20), nullable=True))
    # Backfill razonable: la etapa actual empieza en el primer plan publicado
    op.get_bind().execute(sa.text(
        "UPDATE clients SET goal_started_on = ("
        "  SELECT MIN(published_at)::date FROM plans"
        "  WHERE plans.client_id = clients.id AND plans.published_at IS NOT NULL"
        ") WHERE goal_started_on IS NULL"
    ))
    op.get_bind().execute(sa.text(
        "UPDATE plans SET goal_type = (SELECT goal_type FROM clients WHERE clients.id = plans.client_id) "
        "WHERE goal_type IS NULL"
    ))


def downgrade() -> None:
    op.drop_column("clients", "goal_started_on")
    op.drop_column("clients", "goal_review_snoozed_on")
    op.drop_column("plans", "goal_type")
