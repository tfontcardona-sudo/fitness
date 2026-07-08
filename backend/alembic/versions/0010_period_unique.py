"""0010: integridad de períodos — un solo período abierto por cliente y sin
índices de período duplicados.

Antes de crear los índices únicos, resuelve datos ya inconsistentes (si el bug
de concurrencia hubiera creado duplicados): deja abierto solo el de mayor
`period_index` por cliente y marca los demás abiertos como 'analyzed'; y si
hubiera `(client_id, period_index)` repetidos, renumera los sobrantes al final.
Idempotente.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Un solo período 'open' por cliente: cerrar (analyzed) los duplicados
    #    abiertos, conservando el de mayor period_index.
    bind.execute(sa.text("""
        UPDATE periods p SET status = 'analyzed'
        WHERE p.status = 'open' AND EXISTS (
            SELECT 1 FROM periods q
            WHERE q.client_id = p.client_id AND q.status = 'open'
              AND q.period_index > p.period_index
        )
    """))

    # 2) (client_id, period_index) duplicados: renumerar los sobrantes al final.
    bind.execute(sa.text("""
        WITH d AS (
            SELECT id, client_id,
                   ROW_NUMBER() OVER (PARTITION BY client_id, period_index ORDER BY id) AS rn
            FROM periods
        ),
        mx AS (SELECT client_id, MAX(period_index) AS m FROM periods GROUP BY client_id)
        UPDATE periods p
        SET period_index = mx.m + d.rn - 1
        FROM d JOIN mx ON mx.client_id = d.client_id
        WHERE p.id = d.id AND d.rn > 1
    """))

    insp = sa.inspect(bind)
    existing = {ix["name"] for ix in insp.get_indexes("periods")}
    constraints = {c["name"] for c in insp.get_unique_constraints("periods")}

    if "uq_period_client_index" not in constraints and "uq_period_client_index" not in existing:
        op.create_unique_constraint("uq_period_client_index", "periods", ["client_id", "period_index"])
    if "uq_period_one_open" not in existing:
        op.create_index("uq_period_one_open", "periods", ["client_id"], unique=True,
                        postgresql_where=sa.text("status = 'open'"))


def downgrade() -> None:
    pass
